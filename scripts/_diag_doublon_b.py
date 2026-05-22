#!/usr/bin/env python3
"""Diagnostic doublon B: 4+11 DAUPHINE (bgid 75JZ).

Hypothese a verifier :
- 75JZ pivot l_libelle_adr = ['7B/9B/11B/13B Rue Du Dauphine'] : annexe
  B-suffixes IMPAIRS uniquement (cour/arriere).
- 4 (pair, ancre fuse 6) et 11 (impair sans B, ancre fuse 7+9) tous
  deux faux-matches make_light num_voie.
- 11 qualifie 'social' dans KV -> probable HBM annees 50.

Pour chaque numero 1-15 DAUPHINE :
  - cle BAN cle_interop_adr
  - bgid autoritaire BDNB (rel_batiment_groupe_adresse)
  - copro RNC eventuelle (cle_adresse)
  - bati BDNB complet (nb_log, annee, lib_principal)
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc["adresses"]
co  = doc["coproprietes"]
by_cle = {a.get("cle") or "": a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)

print("=" * 76)
print("DIAGNOSTIC doublon B - 4+11 RUE DAUPHINE (bgid 75JZ)")
print("=" * 76)
print()

# 1. Toutes les cles DAUPHINE dans le light
print("[1] Toutes les cles DAUPHINE dans light :")
dauph = [(a.get("cle"), a) for a in ad if "|DAUPHINE" in (a.get("cle") or "")]
def num_of(cle):
    p = cle.split("|")[0] if cle else ""
    try: return int(p)
    except: return 999
dauph.sort(key=lambda x: num_of(x[0]))
for cle, a in dauph:
    bg = a.get("batiment_groupe_id","") or "-"
    flags = []
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
    if a.get("_fusion_auto_sources"): flags.append(f"src={a['_fusion_auto_sources']}")
    if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
    has_copro = " [COPRO]" if cle in co_by_cle else ""
    print(f"  {cle:24s} bgid=...{bg[-9:]} bdnb={a.get('nb_log_bdnb')} "
          f"vlog={a.get('nb_ventes_logement')} match={a.get('_bdnb_match')}{has_copro}")
    if flags:
        print(f"      {' '.join(flags)}")

# 2. Copros RNC sur cles DAUPHINE
print()
print("[2] Coproprietes RNC sur cles DAUPHINE :")
for cle_co in sorted(co_by_cle):
    if "|DAUPHINE" not in cle_co: continue
    for c in co_by_cle[cle_co]:
        print(f"  {cle_co:24s} {c.get('numero_immatriculation')}  "
              f"lots_tot={c.get('nb_lots_total')} lots_hab={c.get('nb_lots_habitation')}  "
              f"'{(c.get('nom_copropriete') or '')[:50]}'")

# 3. Resolution BAN -> BDNB pour numeros 1-15 DAUPHINE + qq B-suffixes
print()
print("[3] Resolution BAN -> BDNB autoritaire (numeros 1 a 15 DAUPHINE)")

def ban_lookup(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("features", [])
    except Exception as e:
        return []

def bdnb_by_cle_interop(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            rows = json.loads(r.read())
        return [r.get("batiment_groupe_id") for r in rows]
    except Exception as e:
        return []

numeros_pair = ["2","4","6","8","10","12","14"]
numeros_impair = ["1","3","5","7","9","11","13","15"]
b_suffixes = ["7B","9B","11B","13B"]

resolution = {}
for n in numeros_pair + numeros_impair + b_suffixes:
    q = f"{n} rue du dauphine 69003 Lyon"
    feats = ban_lookup(q)
    if not feats:
        print(f"  {n:4s} -> BAN aucune piste")
        continue
    p = feats[0]["properties"]
    cle_ban = p.get("id","")
    label_ban = p.get("label","")
    bgs = bdnb_by_cle_interop(cle_ban)
    resolution[n] = {"cle_ban": cle_ban, "label_ban": label_ban, "bgs": bgs}
    bgs_short = [b[-9:] for b in bgs]
    print(f"  {n:4s} BAN={cle_ban}  '{label_ban[:35]}'  -> bgid(s) {bgs_short}")
    time.sleep(0.08)

# 4. Pour chaque bgid distinct decouvert, requete bati complet
all_bg = set()
for r in resolution.values():
    for b in r["bgs"]:
        all_bg.add(b)
print()
print(f"[4] Batis BDNB distincts decouverts : {len(all_bg)}")
if all_bg:
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
           "numero_immat_principal,nb_adresse_valid_ban"
           "&batiment_groupe_id=in." + urllib.parse.quote("(" + ",".join(sorted(all_bg)) + ")"))
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            rows = json.loads(r.read())
    except Exception as e:
        rows = []
        print(f"  ERR: {e}")
    for row in rows:
        bg = row.get("batiment_groupe_id","")
        print(f"\n  ...{bg[-9:]}  ({bg})")
        print(f"     nb_log={row.get('nb_log')}  nb_log_rnc={row.get('nb_log_rnc')}  "
              f"annee={row.get('annee_construction')}  usage={(row.get('usage_principal_bdnb_open') or '')[:25]}")
        print(f"     immat={row.get('numero_immat_principal') or '-'}  "
              f"nb_adr_ban={row.get('nb_adresse_valid_ban')}")
        print(f"     lib_principal='{row.get('libelle_adr_principale_ban','')}'")
        for x in (row.get("l_libelle_adr") or []):
            print(f"       . {x}")

# 5. metadata correctif anterieur
print()
print("[5] Verification correctif anterieur DAUPHINE/75JZ")
md = doc.get("metadata", {})
corr_keys = [k for k in md.keys() if k.startswith("_correctif")]
print(f"  metadata._correctif_* presents : {len(corr_keys)}")
for k in corr_keys:
    v = md[k]
    if isinstance(v, dict):
        scope = v.get("scope","")
        if "DAUPHINE" in scope.upper() or "75JZ" in scope.upper():
            print(f"  ! {k}: {v}")
    elif isinstance(v, str):
        if "DAUPHINE" in v.upper() or "75JZ" in v.upper():
            print(f"  ! {k}: {v[:200]}")
