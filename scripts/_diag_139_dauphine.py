#!/usr/bin/env python3
"""Diagnostic 139 DAUPHINE -> AJ6692420 TERRASSES DU PRESIDENT (DL).

Pattern attendu : Fondary multi-parcelles (cf fix-fondary-croixnivert).
Le RNC declare 238 Felix Faure comme adresse principale, mais le bati
porte aussi 139 DAUPHINE sur une autre parcelle. Mecanisme :
INJECT (ou re-attribuer) ancre 238 FF si absente + RE-FUSE 139 DAUPH.

Etapes :
 1. 238 FELIX FAURE present dans light ? immat ? bgid ?
 2. AJ6692420 deja dans coproprietes ? RNC live (parcelles)
 3. bgid de 139 DAUPH vs 238 FF (memes ou distincts ?)
 4. Authorite BAN -> BDNB pour 238 FF
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc["adresses"]
co  = doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

print("=" * 76)
print("DIAGNOSTIC 139 RUE DAUPHINE -> AJ6692420 TERRASSES DU PRESIDENT")
print("=" * 76)

# 0. Etat 139 DAUPHINE
print()
print("[0] Etat actuel 139 DAUPHINE :")
a139 = by_cle.get("139|RUE|DAUPHINE")
for k in ("cle","batiment_groupe_id","nb_log_bdnb","nb_ventes_logement",
          "nb_ventes_total","sci_proprietaire","sci_nom","syndic",
          "_syndic_src","_bdnb_match","_fusion_auto","_fusion_cible",
          "longitude","latitude"):
    if a139 and a139.get(k) not in (None,""):
        print(f"  {k}: {a139[k]}")

# 1. 238 FELIX FAURE present ?
print()
print("[1] 238 AVENUE FELIX FAURE dans light :")
ff238_cands = []
for cle_try in ("238|AVENUE|FELIX FAURE","238|AV|FELIX FAURE"):
    if cle_try in by_cle:
        ff238_cands.append((cle_try, by_cle[cle_try]))
for a in ad:
    cle = a.get("cle") or ""
    if cle.startswith("238|") and "FELIX FAURE" in cle:
        if (cle, a) not in ff238_cands:
            ff238_cands.append((cle, a))

if not ff238_cands:
    print("  ABSENTE light.")
else:
    for cle, a in ff238_cands:
        print(f"  PRESENTE : '{cle}'")
        for k in ("batiment_groupe_id","nb_log_bdnb","nb_ventes_logement",
                  "nb_ventes_total","numero_immatriculation","nb_lots_habitation",
                  "syndic","_syndic_src","_bdnb_match","_fusion_auto",
                  "_fusion_cible","_fusion_auto_label","_fusion_auto_sources",
                  "longitude","latitude","dans_majic"):
            if a.get(k) not in (None,""):
                v = a[k]
                if isinstance(v,(dict,list)):
                    v = json.dumps(v, ensure_ascii=False)[:100]
                print(f"    {k}: {v}")

# 1b. Voisins FELIX FAURE pour orientation
print()
print("[1b] Adresses FELIX FAURE light voisines (230-250) :")
ff_all = sorted([(int(a.get("cle","0").split("|")[0]) if a.get("cle","0").split("|")[0].isdigit() else 0, a)
                 for a in ad if "FELIX FAURE" in (a.get("cle") or "")],
                key=lambda x: x[0])
for n, a in ff_all:
    if 230 <= n <= 250:
        bg = a.get("batiment_groupe_id") or ""
        bg9 = bg[-9:] if bg else "-"
        flags=[]
        if a.get("_fusion_auto"): flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
        immat = a.get("numero_immatriculation")
        if immat: flags.append(f"immat={immat}")
        copro_match = "COPRO" if a.get("cle") in co_by_cle else ""
        print(f"  {a.get('cle'):28s} bgid=...{bg9} bdnb={a.get('nb_log_bdnb')} "
              f"vlog={a.get('nb_ventes_logement')} {copro_match} {' '.join(flags)}")

# 2. AJ6692420 dans coproprietes ?
print()
print("[2] AJ6692420 TERRASSES DU PRESIDENT dans coproprietes[] :")
c_tdp = co_by_immat.get("AJ6692420")
if c_tdp:
    print("  PRESENTE dans coproprietes[]")
    for k in ("numero_immatriculation","nom_copropriete","cle_adresse","syndic",
              "_syndic_src","adresse","nb_lots_total","nb_lots_habitation",
              "nb_lots_habitation_rnc","nb_log_bdnb","nb_ventes_2021_2025",
              "ventes_par_an","taux_rotation_5ans","classement_rotation"):
        if c_tdp.get(k) not in (None,""):
            v = c_tdp[k]
            if isinstance(v,(dict,list)):
                v = json.dumps(v, ensure_ascii=False)[:80]
            print(f"    {k}: {v}")
else:
    print("  ABSENTE coproprietes[].")

# 3. RNC live AJ6692420 - parcelles + adresses
print()
print("[3] RNC live AJ6692420 - autorite :")
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": "AJ6692420"})
try:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.loads(r.read()).get("data", [])
except Exception as e:
    print(f"  ! erreur RNC live : {e}")
    rows = []
print(f"  {len(rows)} row(s)")
for i, row in enumerate(rows):
    print(f"\n  ROW {i+1} :")
    interest = ["numero_immatriculation","nom_usage_copropriete",
                "date_immatriculation","adresse_reference","code_postal_reference",
                "commune_reference","nombre_total_lots","nombre_lots_usage_habitation",
                "nombre_lots_stationnement","nombre_lots_tertiaire",
                "reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3",
                "nom_personne_morale","type_mandat","annee_construction"]
    for k in interest:
        v = row.get(k)
        if v not in (None,""):
            print(f"    {k}: {str(v)[:120]}")

# 4. BAN -> BDNB pour 139 DAUPH + 238 FF + autres adresses RNC
print()
print("[4] BAN -> BDNB pour adresses cles :")
def ban(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("features", [])
    except Exception: return []

def bdnb_by_cle(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            rows = json.loads(r.read())
        return [r["batiment_groupe_id"] for r in rows]
    except Exception: return []

for q in ["139 rue du dauphine 69003 Lyon",
          "238 avenue felix faure 69003 Lyon",
          "240 avenue felix faure 69003 Lyon",
          "236 avenue felix faure 69003 Lyon"]:
    feats = ban(q)
    if feats:
        p = feats[0]["properties"]
        cle = p.get("id","")
        bgs = bdnb_by_cle(cle)
        print(f"  '{q}'")
        print(f"     BAN id={cle}  label='{p.get('label','')}'")
        print(f"     BDNB bgid(s)={bgs}")
        time.sleep(0.08)

# 5. Cache parcelle BDNB pour bgid 139 DAUPH + bgid 238 FF si trouve
print()
print("[5] Parcelles BDNB des bgids cibles :")
CACHE_BG = ROOT / "data" / "_bgid_parcelle_dl.json"
cache_bg = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}

if a139:
    bg139 = a139.get("batiment_groupe_id")
    print(f"  bgid 139 DAUPHINE ({bg139[-9:]}) parcelles BDNB : {cache_bg.get(bg139, '?? pas en cache')}")

if ff238_cands:
    bg238 = ff238_cands[0][1].get("batiment_groupe_id")
    if bg238:
        print(f"  bgid 238 FF ({bg238[-9:]}) parcelles BDNB : {cache_bg.get(bg238, '?? pas en cache')}")
    else:
        print(f"  238 FF n'a pas de bgid")

# 6. Synthese
print()
print("=" * 76)
print("MECANISME SUGGERE :")
print("=" * 76)
ff238_present = bool(ff238_cands)
ff238_immat = None
ff238_bg = None
if ff238_present:
    ff238_immat = ff238_cands[0][1].get("numero_immatriculation")
    ff238_bg = ff238_cands[0][1].get("batiment_groupe_id")

if ff238_present and ff238_immat == "AJ6692420":
    print("  238 FF deja ancre RNC AJ6692420 -> RE-FUSE direct 139 DAUPH vers 238 FF")
elif ff238_present and ff238_immat:
    print(f"  238 FF deja ancre RNC {ff238_immat} (autre immat) -> COLLISION possible")
    print(f"  Verifier que AJ6692420 != {ff238_immat} ; possible double ancre sur 238 FF")
elif ff238_present and not ff238_immat:
    print("  238 FF present mais sans immat (hr-ancre ou FA) :")
    print("  -> propager AJ6692420 + 169 lots vers 238 FF (REBIND ancre RNC)")
    print("  -> RE-FUSE 139 DAUPH avec label '238 FF / 139 DAUPH'")
else:
    print("  238 FF absent light -> Pattern Suffren+Cambronne hybride :")
    print("  INJECT 238 FF clone-based (bgid a determiner via BAN->BDNB)")
    print("  + propagation AJ6692420 + RE-FUSE 139 DAUPH vers 238 FF")
