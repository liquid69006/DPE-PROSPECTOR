#!/usr/bin/env python3
"""Diag E1 revise - 31/33 RICHERAND + 40/42 AUBIGNY (FONCIERE VESTA bailleur social).

Etape 1 : etat light de chaque cle
Etape 2 : verifier ou est attachee la copro OPH AG9619537 (securite anti-perte)
Etape 3 : MAJIC parcelle EH0089 (Foncière Vesta) + DY0067 (OPH GUY ARNOUD)
Etape 4 : proposition RE-FUSE + label + delta parc
Etape 5 : KV 33 RICHERAND mono -> social
Lecture seule.
"""
import json, sys, os, urllib.parse, urllib.request, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = Path(r'C:\Users\Station 5\majic_locaux2_2025.parquet')

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
KV_ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

try:
    import pyarrow.parquet as pq
    HAS_PQ = MAJIC.exists()
except Exception: HAS_PQ = False

def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

def rnc_live(immat):
    url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": immat})
    code, j = http_get(url, timeout=20)
    rows = j.get("data") or []
    return rows[0] if rows else None

# --- Load light + KV ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)
co_by_immat = {c.get("numero_immatriculation"): c
               for c in co if c.get("numero_immatriculation")}

code, kv = http_get(KV_ENDPOINT, {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA})
assigns = kv.get("assignments") or {}
print("=" * 90)
print("DIAG E1 REVISE - 31/33 RICHERAND + 40/42 AUBIGNY (FONCIERE VESTA bailleur social)")
print(f"  light : {len(ad)} ad, {len(co)} copros")
print(f"  KV server : {len(assigns)} assigns")
print("=" * 90)


# ============================================================
# ETAPE 1 - Etat light des cles concernees
# ============================================================
print()
print("#" * 90)
print("# [1] Etat light - 31/33 RICHERAND + 40/42 AUBIGNY (+ 39/41/43/47 AUBIGNY OPH)")
print("#" * 90)

CIBLES = [
    "29|RUE|ETIENNE RICHERAND",   # OPH cote impair haut
    "31|RUE|ETIENNE RICHERAND",   # terrain dit dans l'ensemble Vesta
    "33|RUE|ETIENNE RICHERAND",   # ancre actuelle Vesta
    "39|RUE|AUBIGNY",             # OPH GUY ARNOUD?
    "40|RUE|AUBIGNY",             # actuellement bgid YD2U (faux OPH)
    "41|RUE|AUBIGNY",             # OPH
    "42|RUE|AUBIGNY",             # FA -> 40 actuellement
    "43|RUE|AUBIGNY",             # OPH
    "47|RUE|AUBIGNY",             # OPH (le plus de lots MAJIC = 64 lots)
]

print()
print(f"  {'cle':32s}  bgid           bdnb  lots_hab  immat       syndic                  flags")
print("  " + "-"*116)
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:32s}  ABSENT light"); continue
    bg = (a.get("batiment_groupe_id") or "-")[-9:]
    flags = []
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_cible"): flags.append(f"cible={a['_fusion_cible']}")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label'][:30]}'")
    if a.get("_fusion_auto_sources"): flags.append(f"src={a['_fusion_auto_sources']}")
    im = a.get("numero_immatriculation") or "-"
    syndic = (a.get("syndic") or "-")[:22]
    # Verifier si la cle est dans co (= copro RNC)
    if cle in co_by_cle:
        flags.append("COPRO")
        for c in co_by_cle[cle]:
            if c.get("numero_immatriculation") and c.get("numero_immatriculation") != im:
                flags.append(f"co_immat={c['numero_immatriculation']}")
    print(f"  {cle:32s}  {bg:<13s}  {a.get('nb_log_bdnb')!s:>4s}  "
          f"{a.get('nb_lots_habitation')!s:>5s}     {im:<10s}  {syndic:<22s}  {' '.join(flags)}")


# ============================================================
# ETAPE 2 - Cle porteuse OPH AG9619537 ?
# ============================================================
print()
print("#" * 90)
print("# [2] OU est attachee la copro OPH AG9619537 (GUY ARNOUD) ?")
print("#" * 90)
IMMAT_OPH = "AG9619537"
print()
copro_oph = co_by_immat.get(IMMAT_OPH)
if copro_oph:
    print(f"  AG9619537 trouve dans light.coproprietes :")
    for k, v in copro_oph.items():
        print(f"    {k}: {repr(v)[:80]}")
else:
    print(f"  AG9619537 ABSENT de light.coproprietes")

print()
print(f"  RNC live AG9619537 :")
rnc_oph = rnc_live(IMMAT_OPH)
if rnc_oph:
    keys_interest = ["nom_usage_copropriete","nom_societe_mandataire",
                     "adresse_reference","reference_cadastrale_1","reference_cadastrale_2",
                     "nombre_total_lots","nombre_lots_usage_habitation",
                     "nombre_lots_habitation_bureaux_commerces","date_immatriculation"]
    for k in keys_interest:
        v = rnc_oph.get(k)
        if v is not None: print(f"    {k}: {v}")
else:
    print(f"    AG9619537 NOT FOUND tabular-api")


# ============================================================
# ETAPE 3 - MAJIC parcelle EH0089 (Vesta) et DY0067 (OPH)
# ============================================================
print()
print("#" * 90)
print("# [3] MAJIC parcelles EH0089 (Vesta) + DY0067 (OPH GUY ARNOUD)")
print("#" * 90)
if not HAS_PQ:
    print("  (pyarrow indisponible)")
else:
    for parc, label in [("69383000EH0089", "VESTA"), ("69383000DY0067", "OPH")]:
        sec = parc[8:10]
        plan = int(parc[10:])
        tbl = pq.read_table(str(MAJIC), filters=[
            ("departement","=","69"),("code_commune","=","383"),
            ("section","=",sec),("numero_parcelle","=",plan)])
        df = tbl.to_pandas()
        print()
        print(f"  Parcelle {parc} ({label}) : {len(df)} lots")
        df['addr'] = (df['numero_voirie'].fillna('').astype(str).str.lstrip('0')
                      + df['indice_de_repetition'].fillna('').astype(str)
                      + ' ' + df['nature_voie'].fillna('') + ' '
                      + df['nom_voie'].fillna(''))
        adr_counts = df['addr'].value_counts().to_dict()
        for adr, n in list(adr_counts.items())[:10]:
            print(f"    {n:3d}  '{adr.strip()}'")
        sirens = df['numero_siren'].dropna().value_counts().head(5).to_dict()
        for s, n in sirens.items():
            denoms = df[df['numero_siren']==s]['denomination'].dropna().unique()[:1]
            print(f"      SIREN {s} : {n} lots  ({list(denoms)[0] if len(denoms) else '?'})")


# ============================================================
# ETAPE 4 - Proposition RE-FUSE + delta parc
# ============================================================
print()
print("#" * 90)
print("# [4] Proposition RE-FUSE + delta parc")
print("#" * 90)
print()
a_33 = by_cle.get("33|RUE|ETIENNE RICHERAND")
a_31 = by_cle.get("31|RUE|ETIENNE RICHERAND")
a_40 = by_cle.get("40|RUE|AUBIGNY")
a_42 = by_cle.get("42|RUE|AUBIGNY")

bgid_33 = a_33 and a_33.get("batiment_groupe_id")
bgid_31 = a_31 and a_31.get("batiment_groupe_id")
bgid_40 = a_40 and a_40.get("batiment_groupe_id")
bgid_42 = a_42 and a_42.get("batiment_groupe_id")
print(f"  bgids actuels :")
print(f"    33 RICH : {bgid_33}")
print(f"    31 RICH : {bgid_31}")
print(f"    40 AUB  : {bgid_40}")
print(f"    42 AUB  : {bgid_42}")
print()
print(f"  ANCRE proposee : 33|RUE|ETIENNE RICHERAND (bgid D61Z, parcelle EH0089 VESTA)")
print(f"  Operations a appliquer :")
ops = []
bdnb_perdu = 0
for cle, a, bgid_actuel in [
    ("31|RUE|ETIENNE RICHERAND", a_31, bgid_31),
    ("40|RUE|AUBIGNY", a_40, bgid_40),
    ("42|RUE|AUBIGNY", a_42, bgid_42),
]:
    if not a:
        print(f"    SKIP {cle} (absent light)"); continue
    if bgid_actuel != bgid_33:
        ops.append(f"RE-POINT {cle} bgid {bgid_actuel} -> {bgid_33}")
        # Doublon BDNB potentiel : si la cle a un bdnb > 0 ET le bgid cible existe,
        # alors apres dedup bgid l'UI compte 1 fois seulement.
        bdnb_cle = a.get("nb_log_bdnb") or 0
        bdnb_perdu += bdnb_cle if bdnb_cle else 0
    fa_cible = a.get("_fusion_cible")
    if fa_cible != "33|RUE|ETIENNE RICHERAND":
        ops.append(f"FA cible {cle} : '{fa_cible}' -> '33|RUE|ETIENNE RICHERAND'")
    if not a.get("_fusion_auto"):
        ops.append(f"FA flag {cle} : True")
for o in ops: print(f"    - {o}")
print(f"    - LABEL 33 RICH : '31/33 RUE ETIENNE RICHERAND / 40/42 RUE AUBIGNY'")
print(f"    - SOURCES 33 RICH : ['31|RUE|ETIENNE RICHERAND', '40|RUE|AUBIGNY', '42|RUE|AUBIGNY']")
print()
# Cleanup 40 AUBIGNY label actuel
if a_40 and a_40.get("_fusion_auto_label"):
    print(f"    - CLEANUP {a_40.get('cle','?')}._fusion_auto_label : '{a_40.get('_fusion_auto_label')}' -> retire")
    print(f"    - CLEANUP {a_40.get('cle','?')}._fusion_auto_sources : {a_40.get('_fusion_auto_sources')} -> retire")
print()
print(f"  Delta parc UI estime : ~ -{bdnb_perdu} lgts (dedup bgid post-RE-POINT)")
print(f"    -> ATTENTION : si 40 AUBIGNY bdnb=64 etait du OPH, le retire amputera le bgid YD2U")
print(f"       de 64 lgts. Verifier que YD2U garde une autre ancre (39/41/43/47 AUBIGNY).")


# ============================================================
# ETAPE 5 - KV
# ============================================================
print()
print("#" * 90)
print("# [5] KV - 33 RICHERAND mono -> social")
print("#" * 90)
print()
kv_33 = assigns.get("33|RUE|ETIENNE RICHERAND")
print(f"  KV avant : 33|RUE|ETIENNE RICHERAND -> {kv_33}")
print(f"  KV apres : 33|RUE|ETIENNE RICHERAND -> {{type:'social'}}")
# Side effects : 31 RICH, 40 AUB, 42 AUB en KV ?
print()
print(f"  KV des autres cles a verifier :")
for cle in ["31|RUE|ETIENNE RICHERAND","40|RUE|AUBIGNY","42|RUE|AUBIGNY"]:
    v = assigns.get(cle)
    print(f"    {cle:32s} : {v}")
print()
print("=" * 90)
print(">>> DIAG TERMINE - lecture seule")
print("=" * 90)
