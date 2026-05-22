#!/usr/bin/env python3
"""Diagnostic 106 BARABAN -> 61 CHARIAL SOPHIA AE1293612 (DL).

Etapes :
 1. 61 CHARIAL present dans light ?
 2. AE1293612 SOPHIA deja dans coproprietes[] ?
 3. RNC live AE1293612 : adresses + parcelles + lots + syndic
 4. Autorite BAN -> BDNB pour 61 CHARIAL + verif bgid

Mecanisme suggere selon resultat.
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
print("DIAGNOSTIC 106 RUE BARABAN -> AE1293612 SOPHIA")
print("=" * 76)

# 0. Etat 106 BARABAN
print()
print("[0] Etat actuel 106 BARABAN :")
a106 = by_cle.get("106|RUE|BARABAN")
if a106:
    for k in ("cle","batiment_groupe_id","nb_log_bdnb","nb_ventes_logement",
              "nb_ventes_total","sci_proprietaire","sci_nom","syndic",
              "_syndic_src","_bdnb_match","_fusion_auto","_fusion_cible"):
        if a106.get(k) not in (None,""):
            print(f"  {k}: {a106[k]}")

# 1. 61 CHARIAL present ?
print()
print("[1] 61 ANTOINE CHARIAL dans light ?")
chrl_candidates = []
for cle_candidate in ("61|RUE|ANTOINE CHARIAL",
                      "61|RUE|CHARIAL",
                      "61|R|ANTOINE CHARIAL"):
    if cle_candidate in by_cle:
        chrl_candidates.append((cle_candidate, by_cle[cle_candidate]))
# Plus large : toutes adresses contenant '61' + 'CHARIAL'
for a in ad:
    cle = a.get("cle") or ""
    if "CHARIAL" in cle and cle.startswith("61|"):
        if (cle, a) not in chrl_candidates:
            chrl_candidates.append((cle, a))
if not chrl_candidates:
    print("  ABSENTE light. Pattern Suffren INJECTION necessaire.")
else:
    for cle, a in chrl_candidates:
        print(f"  PRESENTE : cle='{cle}'")
        print(f"    bgid={a.get('batiment_groupe_id')}  bdnb={a.get('nb_log_bdnb')}  "
              f"vlog={a.get('nb_ventes_logement')}  immat={a.get('numero_immatriculation') or '-'}")
        flags=[]
        if a.get("_fusion_auto"): flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
        if a.get("_fusion_auto_sources"): flags.append(f"src={a['_fusion_auto_sources']}")
        if a.get("_fusion_cible"): flags.append(f"cible='{a['_fusion_cible']}'")
        if flags: print(f"    {' '.join(flags)}")

# 1b. Voisins CHARIAL pour orientation
print()
print("[1b] Adresses CHARIAL light voisines (numeros) :")
chrl_all = sorted([(int(a.get("cle","0").split("|")[0]) if a.get("cle","0").split("|")[0].isdigit() else 0, a)
                   for a in ad if "CHARIAL" in (a.get("cle") or "")],
                  key=lambda x: x[0])
for n, a in chrl_all:
    if 55 <= n <= 75:
        bg = a.get("batiment_groupe_id") or ""
        bg9 = bg[-9:] if bg else "-"
        flags=[]
        if a.get("_fusion_auto"): flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
        immat = a.get("numero_immatriculation")
        if immat: flags.append(f"immat={immat}")
        print(f"  {a.get('cle'):26s} bgid=...{bg9} bdnb={a.get('nb_log_bdnb')} vlog={a.get('nb_ventes_logement')} {' '.join(flags)}")

# 2. AE1293612 SOPHIA dans coproprietes ?
print()
print("[2] AE1293612 SOPHIA dans coproprietes[] ?")
c_sophia = co_by_immat.get("AE1293612")
if c_sophia:
    print(f"  PRESENTE dans coproprietes[]")
    for k in ("numero_immatriculation","nom_copropriete","cle_adresse","syndic",
              "_syndic_src","adresse","nb_lots_total","nb_lots_habitation",
              "nb_lots_habitation_rnc","nb_log_bdnb","nb_ventes_2021_2025",
              "ventes_par_an","taux_rotation_5ans","classement_rotation"):
        if c_sophia.get(k) not in (None,""):
            v = c_sophia[k]
            if isinstance(v,(dict,list)):
                v = json.dumps(v, ensure_ascii=False)[:80]
            print(f"    {k}: {v}")
else:
    print("  ABSENTE coproprietes[]. INJECT copro + ATTRIBUTION necessaire.")

# 3. RNC live AE1293612 (autorite finale)
print()
print("[3] RNC live AE1293612 (tabular-api 3ea8e2c3) :")
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": "AE1293612"})
try:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.loads(r.read()).get("data", [])
except Exception as e:
    print(f"  ! erreur RNC live : {e}")
    rows = []
print(f"  {len(rows)} row(s) returned")
for i, row in enumerate(rows):
    print(f"\n  ROW {i+1} :")
    interest = ["numero_immatriculation","nom_usage_copropriete","date_premiere_immatriculation",
                "date_immatriculation","adresse_reference","code_postal_reference","commune_reference",
                "code_insee_commune_reference","nombre_total_lots",
                "nombre_lots_usage_habitation","nombre_lots_stationnement",
                "nombre_lots_tertiaire","reference_cadastrale_1","reference_cadastrale_2",
                "reference_cadastrale_3","nom_personne_morale","type_mandat","etat_descriptif_division",
                "annee_construction"]
    for k in interest:
        v = row.get(k)
        if v not in (None,""):
            v_s = str(v)[:120]
            print(f"    {k}: {v_s}")

# 4. BAN -> BDNB pour 61 CHARIAL (autorite bgid)
print()
print("[4] BAN -> BDNB pour 61 ANTOINE CHARIAL :")
def ban(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("features", [])
    except Exception:
        return []

def bdnb_by_cle_interop(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            rows = json.loads(r.read())
        return [r["batiment_groupe_id"] for r in rows]
    except Exception:
        return []

for q in ["61 rue antoine charial 69003 Lyon",
          "106 rue baraban 69003 Lyon"]:
    feats = ban(q)
    if feats:
        p = feats[0]["properties"]
        cle = p.get("id","")
        bgs = bdnb_by_cle_interop(cle)
        print(f"  '{q}'")
        print(f"     BAN cle={cle}  label='{p.get('label','')}'")
        print(f"     BDNB bgid(s)={bgs}")
        time.sleep(0.1)

# 5. Synthese
print()
print("=" * 76)
print("MECANISME SUGGERE - dependant des resultats ci-dessus :")
print("=" * 76)
if not chrl_candidates:
    print("  61 CHARIAL absent + SOPHIA " + ("hors-snapshot" if not c_sophia else "deja snapshot") + " :")
    if not c_sophia:
        print("    -> pattern Suffren INJECTION+ATTRIBUTION (cf fix-suffren-barthelemy-garibaldi)")
        print("       INJECT copro AE1293612 dans coproprietes[] (cle 61|RUE|ANTOINE CHARIAL)")
        print("       INJECT adresse 61|RUE|ANTOINE CHARIAL dans adresses[] (clone-based bgid)")
        print("       RE-FUSE 106|RUE|BARABAN vers cette nouvelle ancre")
    else:
        print("    -> pattern Cambronne RE-FUSE pur (61 reste a INJECT en adresse mais copro existe)")
else:
    print("  61 CHARIAL present + SOPHIA " + ("present" if c_sophia else "absent") + " :")
    if c_sophia:
        print("    -> pattern Cambronne RE-FUSE direct : 106 BARABAN -> 61 CHARIAL")
    else:
        print("    -> INJECT copro AE1293612 (61 deja en adresse) + RE-FUSE 106")
