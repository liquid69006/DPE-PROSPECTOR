#!/usr/bin/env python3
"""Diagnostic 2 copros cle malformee restantes DL :
  - AB9784521 BRICKS sur '|AVENUE|LACASSAGNE'
  - AD6934400 9 rue St Eusebe sur '|RUE|ST EUSEBE'

Methode : RNC live -> adresse_reference + ref_cad_1
  -> parser num de l'adresse_reference (autorite)
  -> verifier presence dans light + cohrerence parcelle BDNB

PS : pour 9 St Eusebe, le nom de copro dit deja '9 rue St Eusebe'
donc on s'attend a 9|RUE|ST EUSEBE. Pour BRICKS LACASSAGNE,
inconnu (le nom 'BRICKS' n'indique pas de num).
"""
import json, sys, re, urllib.parse, urllib.request, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc["adresses"]
co  = doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co
               if c.get("numero_immatriculation")}

RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
CACHE_BG = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"
cache_bg  = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}
cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8")) if CACHE_RNC.exists() else {}

def rnc_by_immat(immat):
    url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": immat})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read()).get("data", [])
    except Exception as e:
        return []

def ban(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("features", [])
    except Exception:
        return []

def bdnb_by_cle(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return [r2["batiment_groupe_id"] for r2 in json.loads(r.read())]
    except Exception: return []

def bdnb_parcelles_by_id(bg):
    if bg in cache_bg:
        return cache_bg[bg]
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            rows = json.loads(r.read())
        parcs = [x.get("parcelle_id") for x in rows if x.get("parcelle_id")]
    except Exception:
        parcs = []
    cache_bg[bg] = parcs
    return parcs

def bdnb_to_rnc(p):
    if p and p[:2] == "69" and p[5:8] == "000":
        return "69123383" + p[8:]
    return p

def parse_num(adr_ref):
    if not adr_ref: return None
    m = re.match(r"^\s*(\d+)\s*([A-Z]?)\s+", adr_ref.upper())
    if m:
        return m.group(1) + (m.group(2) if m.group(2) in ("B","T","Q") else "")
    return None

TARGETS = [
    ("AB9784521", "BRICKS", "|AVENUE|LACASSAGNE", "LACASSAGNE"),
    ("AD6934400", "9 rue St Eusebe", "|RUE|ST EUSEBE", "ST EUSEBE"),
]

print("=" * 76)
print("DIAGNOSTIC 2 copros cle malformee restantes DL")
print("=" * 76)

for immat, nom, cle_actuelle, voie_court in TARGETS:
    print()
    print("#" * 76)
    print(f"# {immat}  '{nom}'  cle actuelle '{cle_actuelle}'")
    print("#" * 76)

    # 1. Snapshot copro local
    c = co_by_immat.get(immat)
    print()
    print("[1] Copro snapshot :")
    if not c:
        print("  ABSENTE coproprietes[].")
    else:
        for k in ("nom_copropriete","cle_adresse","syndic","_syndic_src","adresse",
                  "nb_lots_total","nb_lots_habitation"):
            v = c.get(k)
            if v not in (None,""):
                print(f"    {k}: {str(v)[:120]}")

    # 2. RNC live (autorite finale)
    print()
    print("[2] RNC live :")
    rows = rnc_by_immat(immat)
    if not rows:
        print("  AUCUNE row RNC live !")
        continue
    row = rows[0]
    for k in ("numero_immatriculation","nom_usage_copropriete","date_immatriculation",
              "adresse_reference","adresse_complementaire_1","adresse_complementaire_2",
              "code_postal_reference","nombre_total_lots","nombre_lots_usage_habitation",
              "nombre_lots_habitation_bureaux_commerces","nombre_lots_stationnement",
              "reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3",
              "nom_personne_morale","type_mandat","mandat_en_cours"):
        v = row.get(k)
        if v not in (None,"",0):
            print(f"    {k}: {str(v)[:120]}")

    adr_ref = row.get("adresse_reference") or ""
    num = parse_num(adr_ref)
    print(f"\n    -> num parse adresse_reference : '{num}'")

    # 3. BAN -> BDNB pour cle attendue
    new_cle = f"{num}|{cle_actuelle[1:]}" if num else None
    print()
    print(f"[3] Verifier cle attendue '{new_cle}' :")
    if not new_cle:
        print("  num non parseable -> investigation manuelle requise")
        continue
    # presence dans light
    a_target = by_cle.get(new_cle)
    if a_target:
        print(f"  PRESENTE light : bgid={a_target.get('batiment_groupe_id')}  "
              f"vlog={a_target.get('nb_ventes_logement')} bdnb={a_target.get('nb_log_bdnb')} "
              f"immat={a_target.get('numero_immatriculation') or '-'}")
        for k in ("_fusion_auto","_fusion_cible","_fusion_auto_label",
                  "_fusion_auto_sources","syndic","_syndic_src","_bdnb_match",
                  "sci_proprietaire","sci_nom"):
            v = a_target.get(k)
            if v not in (None,"",[],{}):
                print(f"      {k}: {v}")
    else:
        print("  ABSENTE light -> il faut INJECT")

    # 4. BAN -> BDNB cle interop
    print()
    print(f"[4] BAN -> BDNB pour '{num} {voie_court} 69003 Lyon' :")
    feats = ban(f"{num} {voie_court} 69003 Lyon")
    bgs_ban = []
    if feats:
        p = feats[0]["properties"]
        cle = p.get("id","")
        bgs_ban = bdnb_by_cle(cle)
        print(f"    BAN id={cle}  label='{p.get('label','')}'")
        print(f"    BDNB bgid(s)={bgs_ban}")

    # 5. Croiser parcelle RNC vs parcelle BDNB(bgid_target)
    ref_cad_rnc = row.get("reference_cadastrale_1") or ""
    print()
    print(f"[5] Croiser parcelles :")
    print(f"    parcelle RNC reference_cadastrale_1 : {ref_cad_rnc}")
    if a_target and a_target.get("batiment_groupe_id"):
        bg = a_target["batiment_groupe_id"]
        parcs_bdnb = bdnb_parcelles_by_id(bg)
        parcs_rnc = [bdnb_to_rnc(p) for p in parcs_bdnb]
        print(f"    bgid light '{bg[-9:]}' parcelles BDNB = {parcs_bdnb}")
        print(f"      -> en RNC format = {parcs_rnc}")
        match = ref_cad_rnc in parcs_rnc
        print(f"    MATCH parcelle ? {'OUI' if match else 'NON'}")
    if bgs_ban:
        # Comparer aussi avec bgid autoritaire BAN
        for bg in bgs_ban:
            parcs_bdnb = bdnb_parcelles_by_id(bg)
            parcs_rnc = [bdnb_to_rnc(p) for p in parcs_bdnb]
            print(f"    bgid BAN autoritaire '{bg[-9:]}' parcelles = {parcs_rnc}")
            match2 = ref_cad_rnc in parcs_rnc
            print(f"      MATCH parcelle ? {'OUI' if match2 else 'NON'}")
    time.sleep(0.1)

print()
print("=" * 76)
print("Caches mis a jour")
CACHE_BG.write_text(json.dumps(cache_bg, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  _bgid_parcelle_dl : {len(cache_bg)} entrees")
