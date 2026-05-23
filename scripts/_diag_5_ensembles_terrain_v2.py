#!/usr/bin/env python3
"""Diag 5 ensembles immobiliers confirmes terrain DL v2 - dry-run.

ENSEMBLES :
  1. 33 ETIENNE RICHERAND + 40 AUBIGNY (FONCIERE VESTA)
  2. 24 GABILLOT + 233 PAUL BERT (BOUVIER)
  3. 2/4/6 VILLETTE + 215 BONNEL (multi-adresses)
  4. 4/6 MILIEU (JUNE)
  5. 2 ST PHILIPPE + 20 DAUPHINE

Pour chaque ensemble :
  [1] Light state (bgid, immat, _fusion_auto, syndic, parcelle)
  [2] Parcelles BDNB
  [3] RNC live scan parcelle
  [4] Detail RNC live immat secteur
  [5] MAJIC parcelles (si parquet disponible)
  [6] Synthese mecanisme + delta parc

Aucune modification.
"""
import json, sys, urllib.parse, urllib.request, urllib.error, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = Path(r'C:\Users\Station 5\majic_locaux2_2025.parquet')
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

# --- Try import pyarrow (optionnel) ---
HAS_PQ = False
try:
    import pyarrow.parquet as pq
    HAS_PQ = MAJIC.exists()
except Exception:
    HAS_PQ = False

# --- Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad, co = doc["adresses"], doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)
co_by_immat = {c.get("numero_immatriculation"): c
               for c in co if c.get("numero_immatriculation")}


def bdnb_to_rnc(p):
    if p[:2] == "69" and p[5:8] == "000":
        return "69123383" + p[8:]
    return p

def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "diag-script/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)[:80]}

def bdnb_parc(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    d = http_get(url)
    if isinstance(d, dict) and "_error" in d: return []
    return [p.get("parcelle_id") for p in d if p.get("parcelle_id")]

def scan_rnc_parc(rnc_p):
    """Scan ref_cad_1/2/3 sur tabular-api."""
    seen = {}
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        d = http_get(url, timeout=20)
        rows = (d or {}).get("data", []) if isinstance(d, dict) else []
        for row in rows:
            im = row.get("numero_immatriculation")
            if im and im not in seen:
                seen[im] = row
        time.sleep(0.05)
    return list(seen.values())

def rnc_live(immat):
    url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": immat})
    d = http_get(url, timeout=20)
    rows = (d or {}).get("data", []) if isinstance(d, dict) else []
    return rows[0] if rows else None

def majic_p(parc):
    if not HAS_PQ or not parc: return None
    sec = parc[8:10]
    try:
        plan = int(parc[10:])
    except: return None
    try:
        tbl = pq.read_table(str(MAJIC), filters=[
            ("departement","=","69"),("code_commune","=","383"),
            ("section","=",sec),("numero_parcelle","=",plan)])
        df = tbl.to_pandas()
    except Exception as e:
        return None
    if df.empty: return None
    df['addr'] = (df['numero_voirie'].fillna('').astype(str).str.lstrip('0')
                  + df['indice_de_repetition'].fillna('').astype(str)
                  + ' ' + df['nature_voie'].fillna('') + ' '
                  + df['nom_voie'].fillna(''))
    return df


ENSEMBLES = [
    {"id":1, "label":"33 RICHERAND + 40 AUBIGNY (FONCIERE VESTA)",
     "cles":["33|RUE|ETIENNE RICHERAND","40|RUE|AUBIGNY"]},
    {"id":2, "label":"24 GABILLOT + 233 PAUL BERT (BOUVIER)",
     "cles":["24|RUE|GABILLOT","233|RUE|PAUL BERT"]},
    {"id":3, "label":"2/4/6 VILLETTE + 215 BONNEL",
     "cles":["2|RUE|VILLETTE","4|RUE|VILLETTE","6|RUE|VILLETTE","215|RUE|BONNEL"]},
    {"id":4, "label":"4/6 MILIEU (JUNE)",
     "cles":["4|RUE|MILIEU","6|RUE|MILIEU"]},
    {"id":5, "label":"2 ST PHILIPPE + 20 DAUPHINE",
     "cles":["2|RUE|ST PHILIPPE","20|RUE|DAUPHINE"]},
]

print("=" * 90)
print(f"DIAG 5 ENSEMBLES TERRAIN DL v2 - dry-run lecture seule")
print(f"  pyarrow disponible : {HAS_PQ}")
print(f"  MAJIC parquet      : {MAJIC.name} ({'present' if MAJIC.exists() else 'ABSENT'})")
print("=" * 90)

for E in ENSEMBLES:
    print()
    print("#" * 90)
    print(f"# Ensemble [{E['id']}] {E['label']}")
    print("#" * 90)

    # 1. Light state
    print()
    print("[1] Light state :")
    bgs_set, parcs_set, immats_set = set(), set(), set()
    cles_status = []  # liste de (cle, dict_info) pour later
    for cle in E["cles"]:
        a = by_cle.get(cle)
        if not a:
            print(f"  {cle:32s} ABSENT light");
            cles_status.append((cle, None)); continue
        bg = a.get("batiment_groupe_id") or ""
        if bg: bgs_set.add(bg)
        flags = []
        if a.get("_fusion_auto"): flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
        if a.get("_fusion_auto_sources"): flags.append(f"src={a['_fusion_auto_sources']}")
        if a.get("_fusion_cible"): flags.append(f"cible='{a['_fusion_cible']}'")
        if a.get("numero_immatriculation"):
            flags.append(f"immat={a['numero_immatriculation']}")
            immats_set.add(a['numero_immatriculation'])
        if cle in co_by_cle:
            flags.append("COPRO")
            for c in co_by_cle[cle]:
                if c.get("numero_immatriculation"): immats_set.add(c['numero_immatriculation'])
        if a.get("parcelle_dvf"):
            parcs_set.add(a["parcelle_dvf"])
        bdnb_v = a.get('nb_log_bdnb')
        vlog_v = a.get('nb_ventes_logement')
        lots_v = a.get('nb_lots_habitation')
        print(f"  {cle:32s} bgid=...{bg[-9:]}  bdnb={bdnb_v}  vlog={vlog_v}  "
              f"lots_hab={lots_v or '-'}  syndic='{(a.get('syndic') or '-')[:25]}'  "
              f"parc={a.get('parcelle_dvf') or '-'}  {' '.join(flags)}")
        cles_status.append((cle, a))

    # 2. Parcelles BDNB (rel_batiment_groupe_parcelle)
    print()
    print(f"[2] Parcelles BDNB (live API rel_bgid_parcelle) :")
    bgs_parcs = {}
    for bg in sorted(bgs_set):
        parcs = bdnb_parc(bg)
        bgs_parcs[bg] = parcs
        parcs_set.update(parcs)
        print(f"  ...{bg[-9:]} -> {parcs}")

    # 3. RNC live scan parcelles
    print()
    print(f"[3] RNC live scan parcelle(s) (ref_cad_1/2/3) :")
    rnc_hits = {}
    for parc in sorted(parcs_set):
        rnc_p = bdnb_to_rnc(parc)
        hits = scan_rnc_parc(rnc_p)
        if hits:
            print(f"  {rnc_p} ({parc}) : {len(hits)} hit(s)")
            for h in hits:
                im = h.get("numero_immatriculation")
                if im and im not in rnc_hits: rnc_hits[im] = h
                in_sct = " [DEJA-SCT]" if im in co_by_immat else " [HORS-SCT]"
                tot = h.get("nombre_total_lots")
                hab = h.get("nombre_lots_usage_habitation") or h.get("nombre_lots_habitation_bureaux_commerces")
                print(f"    {im} '{(h.get('nom_usage_copropriete','') or '')[:38]}'  "
                      f"tot={tot} hab={hab}{in_sct}")
        else:
            print(f"  {rnc_p} ({parc}) : 0 hit")

    # 4. Detail RNC live des immats deja-secteur
    print()
    print(f"[4] Detail RNC live immats deja-secteur ({len(immats_set)}) :")
    for im in sorted(immats_set):
        r = rnc_live(im)
        if not r:
            print(f"  {im} : NOT FOUND tabular-api"); continue
        print(f"  {im} '{(r.get('nom_usage_copropriete','') or '')[:40]}'  ({'DEJA-SCT' if im in co_by_immat else 'HORS-SCT'})")
        if r.get("adresse_reference"):
            print(f"    adr_ref='{r['adresse_reference'][:70]}'")
        for k in ("adresse_complementaire_1","adresse_complementaire_2",
                  "adresse_complementaire_3","adresse_complementaire_4"):
            v = r.get(k)
            if v: print(f"    {k}='{v}'")
        print(f"    lots_tot={r.get('nombre_total_lots')} hab={r.get('nombre_lots_usage_habitation')}  "
              f"nb_parcelles={r.get('nombre_parcelles')}")
        for k in ("reference_cadastrale_1","reference_cadastrale_2",
                  "reference_cadastrale_3","reference_cadastrale_4"):
            v = r.get(k)
            if v: print(f"    {k}='{v}'")

    # 5. MAJIC parcelles
    print()
    print(f"[5] MAJIC parcelle(s) :")
    if not HAS_PQ:
        print("  (pyarrow/parquet indisponible - skip)")
    else:
        for parc in sorted(parcs_set):
            df = majic_p(parc)
            if df is None or df.empty:
                print(f"  {parc} : 0 lot"); continue
            adr_counts = df['addr'].value_counts().to_dict()
            sirens = df['numero_siren'].dropna().value_counts().to_dict()
            print(f"  {parc} : {len(df)} lots / {len(adr_counts)} adresses / {len(sirens)} SIRENs")
            for adr, n in list(adr_counts.items())[:5]:
                print(f"    {n:3d}  '{adr.strip()}'")
            for s, n in list(sirens.items())[:3]:
                print(f"      SIREN {s} : {n} lots")

    # 6. Synthese
    print()
    print(f"[6] SYNTHESE Ensemble [{E['id']}] :")
    print(f"  bgids distincts            : {len(bgs_set)}  {sorted(bgs_set)}")
    print(f"  parcelles distinctes (BDNB) : {len(parcs_set)}  {sorted(parcs_set)}")
    print(f"  immats secteur impliques   : {sorted(immats_set)}")
    print(f"  RNC live hits parcelles    : {list(rnc_hits.keys())}")

print()
print("=" * 90)
print(">>> DIAG TERMINE - dry-run lecture seule")
print("=" * 90)
