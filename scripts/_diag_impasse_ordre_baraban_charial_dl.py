#!/usr/bin/env python3
"""Diag ensemble 7/9/11 IMP ORDRE + 116/118 BARABAN + 50 CHARIAL DL.

ETAPE 1 : light JSON (by_cle)
ETAPE 2 : BDNB live (rel_parcelle + batiment_groupe_complet l_libelle_adr)
ETAPE 3 : RNC live tabular-api (scan ref_cad parcelles BDNB)
ETAPE 4 : MAJIC parquet (locaux2 par parcelle)

Lecture seule.
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC_PARQ = Path(r"C:\Users\Station 5\majic_locaux2_2025.parquet")

RID_RNC = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID_RNC}/data/"
UA = "Mozilla/5.0 diag/1.0"

CIBLES = [
    "7|IMPASSE|ORDRE",
    "9|IMPASSE|ORDRE",
    "11|IMPASSE|ORDRE",
    "116|RUE|BARABAN",
    "118|RUE|BARABAN",
    "50|RUE|ANTOINE CHARIAL",
]

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)[:120]}

def bdnb_to_rnc(p):
    if len(p)>=8 and p[:2]=="69" and p[5:8]=="000":
        return "69123383"+p[8:]
    return p

# --- Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {a.get("cle"): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}
co_by_cle = defaultdict(list)
for c in co:
    if c.get("cle_adresse"): co_by_cle[c["cle_adresse"]].append(c)

# ============================================================
# ETAPE 1 : light state
# ============================================================
print("=" * 100)
print("DIAG ENSEMBLE 7/9/11 IMP ORDRE + 116/118 BARABAN + 50 CHARIAL")
print("=" * 100)
print()
print("[1] LIGHT state")
print(f"  {'cle':32s}  {'bgid':<14s} {'immat':<11s} {'bdnb':>4s} {'hab':>4s} {'vlog':>4s} flags")
print("  " + "-"*100)
bgids = set()
immats = set()
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:32s} ABSENT"); continue
    bg = (a.get("batiment_groupe_id") or "-")[-13:]
    bgids.add(a.get("batiment_groupe_id"))
    im = a.get("numero_immatriculation") or "-"
    if im != "-": immats.add(im)
    bdnb = a.get("nb_log_bdnb")
    hab = a.get("nb_lots_habitation") or "-"
    vlog = a.get("nb_ventes_logement") or 0
    flags = []
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_cible"): flags.append(f"cible={a['_fusion_cible']!r}")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label'][:30]}'")
    if a.get("_injection_bdnb_orphelin"): flags.append("ORPH_BDNB")
    if a.get("_injection_indice"): flags.append("CHERRYPICK_SUFF")
    syndic = (a.get("syndic") or "")[:30]
    print(f"  {cle:32s} {bg:<14s} {im:<11s} {str(bdnb):>4s} {str(hab):>4s} {vlog:>4d} syndic='{syndic}' {' '.join(flags)}")
    # Aussi check si la cle a une copro RNC
    if cle in co_by_cle:
        for c in co_by_cle[cle]:
            print(f"    + copro RNC : {c.get('numero_immatriculation')} '{c.get('nom_copropriete','')[:35]}' hab={c.get('nb_lots_habitation')} syndic='{c.get('syndic','')[:30]}'")

# ============================================================
# ETAPE 2 : BDNB live
# ============================================================
print()
print("[2] BDNB live - parcelles + l_libelle_adr")
parcs_set = set()
for bg in sorted(bgids):
    if not bg: continue
    url = f"https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}"
    d = http_get(url)
    parcs = [x.get("parcelle_id") for x in (d if isinstance(d, list) else []) if x.get("parcelle_id")]
    parcs_set.update(parcs)
    print(f"  bgid={bg}")
    print(f"    parcelles : {parcs}")
    # l_libelle_adr
    url2 = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet?"
            "select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
            "nb_log,nb_log_rnc,annee_construction,numero_immat_principal&"
            f"batiment_groupe_id=eq.{bg}")
    d2 = http_get(url2)
    if isinstance(d2, list) and d2:
        x = d2[0]
        print(f"    ban_pr='{x.get('libelle_adr_principale_ban')}'")
        print(f"    nb_log={x.get('nb_log')} rnc={x.get('nb_log_rnc')} annee={x.get('annee_construction')} immat={x.get('numero_immat_principal')}")
        print(f"    l_libelle_adr:")
        for a_lbl in (x.get("l_libelle_adr") or []):
            print(f"      {a_lbl!r}")
    time.sleep(0.05)

# ============================================================
# ETAPE 3 : RNC live scan parcelles
# ============================================================
print()
print("[3] RNC live - scan ref_cadastrale_* sur parcelles BDNB")
rnc_hits = []
for p in sorted(parcs_set):
    rnc_p = bdnb_to_rnc(p)
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        d = http_get(url, timeout=20)
        rows = (d or {}).get("data", []) if isinstance(d, dict) else []
        for row in rows:
            im = row.get("numero_immatriculation")
            if not im: continue
            sct = "DEJA-SCT" if im in co_by_immat else "HORS-SCT"
            rnc_hits.append((p, col, im, row.get("nom_usage_copropriete",""),
                            row.get("nombre_total_lots"),
                            row.get("nombre_lots_usage_habitation"),
                            row.get("nom_societe_mandataire") or "",
                            row.get("date_immatriculation"), sct))
        time.sleep(0.05)
print(f"  Total RNC hits sur parcelles BDNB : {len(rnc_hits)}")
for p, col, im, nom, tot, hab, syn, dat, sct in rnc_hits:
    print(f"    {p} ({col})  {im} '{nom[:35]}'  tot={tot} hab={hab}  syndic='{syn[:25]}'  date={dat}  [{sct}]")

# ============================================================
# ETAPE 4 : MAJIC parquet par parcelle
# ============================================================
print()
print("[4] MAJIC locaux2 - lots par parcelle")
import pyarrow.parquet as pq
tbl = pq.read_table(str(MAJIC_PARQ), filters=[("departement","=","69"),("code_commune","=","383")])
df = tbl.to_pandas()
for p in sorted(parcs_set):
    sec = p[8:10]
    try: num = int(p[10:])
    except: continue
    m = df[(df['section']==sec) & (df['numero_parcelle']==num)]
    if m.empty:
        print(f"  Parc {p} : 0 lot MAJIC")
        continue
    m = m.assign(_addr=m['numero_voirie'].fillna('').astype(str).str.lstrip('0')+
                       m['indice_de_repetition'].fillna('').astype(str)+' '+
                       m['nature_voie'].fillna('')+' '+
                       m['nom_voie'].fillna(''))
    print(f"  Parc {p} : {len(m)} lots MAJIC")
    # Adresses
    for ad_s, n in m['_addr'].value_counts().head(8).items():
        print(f"    {n:>3d} x '{ad_s.strip()}'")
    # Top SIRENs
    sirens = m['numero_siren'].dropna().value_counts().head(5)
    for s, n in sirens.items():
        d = m[m['numero_siren']==s]['denomination'].dropna().unique()[:1]
        forme = m[m['numero_siren']==s]['forme_juridique_abregee'].dropna().unique()[:1]
        print(f"      SIREN {s} : {n} lots  forme={list(forme)[0] if len(forme) else '?'}  denom={list(d)[0] if len(d) else '?'}")

# ============================================================
# SYNTHESE
# ============================================================
print()
print("=" * 100)
print(f"SYNTHESE")
print("=" * 100)
print(f"  bgids distincts             : {len(bgids)}  {sorted([b for b in bgids if b])}")
print(f"  parcelles distinctes BDNB   : {len(parcs_set)}  {sorted(parcs_set)}")
print(f"  immats deja-secteur (light) : {sorted(immats)}")
print(f"  copros RNC hit parcelles    : {sorted({h[2] for h in rnc_hits})}")
