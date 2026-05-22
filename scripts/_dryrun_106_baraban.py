#!/usr/bin/env python3
"""DRYRUN 106 BARABAN - pattern Cambronne RE-FUSE classique.

ETAT :
- 106|RUE|BARABAN existe en adresses[] (bgid 4XAJ-TVQA, vlog=13, bdnb=61,
  _bdnb_match=num_voie, SCI MAGIT, syndic REGIE CENTRALE IMMOBILIERE)
- Copro AE1293612 SOPHIA existe deja dans coproprietes[] avec
  cle_adresse '61|RUE|ANTOINE CHARIAL' (ORPHELINE -> aucune adresse
  light sur cette cle)
- RNC live AE1293612 : 73 lots total, 60 hab, ref_cad_1=69123383DS0005
  (= meme parcelle BDNB 69383000DS0005 que bgid 4XAJ-TVQA)
- 61 CHARIAL pas reconnue par BAN (anomalie, sans entree postale BAN)

MECANISME : Cambronne RE-FUSE classique
  1. INJECT 61|RUE|ANTOINE CHARIAL en adresses[] (clone-based) :
     - bgid = 4XAJ-TVQA (autorite parcelle confirmee)
     - immat AE1293612 + nb_lots_habit=60 + syndic + taux + classement
     - coord = clone 106 BARABAN
     - dans_majic = False (pas dans MAJIC, adresse postale secondaire)
     - _fusion_auto_label = "61 RUE ANTOINE CHARIAL / 106 RUE BARABAN"
     - _fusion_auto_sources = ['106|RUE|BARABAN']
  2. RE-FUSE 106 BARABAN :
     - bgid conserve (deja correct)
     - _fusion_auto = True
     - _fusion_cible = "61 RUE ANTOINE CHARIAL / 106 RUE BARABAN"

Verifs :
- adresses light +1 (INJECT 61)
- hr-actifs UI 25 -> 24 (106 BARABAN sort : FA, plus hr-ancre)
- 61 CHARIAL devient RNC immat (mais FA-source-non, FA-ancre)
  -> compte comme RNC dans coproByCle apres patch
- parc DL : 4XAJ-TVQA dedup-bgid 61 (bdnb 106) -> 60 (lots_habit 61)
  -> Delta = -1
"""
import json, sys, copy
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]

def to_int(x):
    try: return int(x)
    except Exception: return 0

by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}

a106 = by_cle["106|RUE|BARABAN"]
c_sophia = co_by_immat["AE1293612"]

print("=" * 72)
print("DRYRUN 106 BARABAN -> RE-FUSE vers 61 CHARIAL (SOPHIA AE1293612)")
print("=" * 72)
print()
print("[AVANT]")
print(f"  106|RUE|BARABAN : bgid={a106.get('batiment_groupe_id')}  "
      f"vlog={a106.get('nb_ventes_logement')}  bdnb={a106.get('nb_log_bdnb')}")
print(f"  copro AE1293612 SOPHIA : cle_adresse='{c_sophia.get('cle_adresse')}'  "
      f"lots_tot={c_sophia.get('nb_lots_total')} hab={c_sophia.get('nb_lots_habitation')}")
print(f"  61|RUE|ANTOINE CHARIAL en adresses[] : "
      f"{'PRESENT' if '61|RUE|ANTOINE CHARIAL' in by_cle else 'ABSENT (cible INJECT)'}")
print()

# Construction snapshot APRES
ad_after = copy.deepcopy(ad)
by_after = {(a.get("cle") or ""): a for a in ad_after}

LABEL = "61 RUE ANTOINE CHARIAL / 106 RUE BARABAN"

# 1. INJECT 61|RUE|ANTOINE CHARIAL (clone-based)
a61 = {
    "cle": "61|RUE|ANTOINE CHARIAL",
    "adresse": "61 RUE ANTOINE CHARIAL",
    "longitude": a106.get("longitude"),
    "latitude": a106.get("latitude"),
    "code_iris": a106.get("code_iris"),
    "_coord_source": "clone_106baraban",
    "dans_majic": False,  # ancre RNC non-MAJIC
    "sci_proprietaire": "non",
    "sci_nom": "",
    "sci_siren": "",
    "syndic": c_sophia.get("syndic"),
    "_syndic_src": c_sophia.get("_syndic_src") or "rnc",
    "ventes_par_an": {},
    "nb_ventes_total": 0,
    "nb_log_bdnb": 61,  # bdnb du bati (info utile pour UI hover)
    "annee_construction": a106.get("annee_construction"),
    "classe_dpe": a106.get("classe_dpe"),
    "type_batiment": a106.get("type_batiment"),
    "type_chauffage": a106.get("type_chauffage"),
    "batiment_groupe_id": a106.get("batiment_groupe_id"),
    "_bdnb_match": "correctif_106baraban_inject_ancre_rnc",
    "ventes_par_an_logement": {},
    "nb_ventes_logement": 0,
    "taux_rotation_logement": 0.0,
    "classement_rotation_logement": "Fige",
    "_taux_logement_src": "copie_sans_dependance",
    "usage_principal_bdnb": a106.get("usage_principal_bdnb"),
    "_usage_bdnb_src": "clone_106baraban",
    # Propagation copro RNC
    "numero_immatriculation": "AE1293612",
    "nb_lots_habitation": c_sophia.get("nb_lots_habitation"),
    "taux_rotation": c_sophia.get("taux_rotation_5ans"),
    "classement_rotation": c_sophia.get("classement_rotation"),
    # Etiquetage chaine
    "_fusion_auto_label": LABEL,
    "_fusion_auto_sources": ["106|RUE|BARABAN"],
}
ad_after.append(a61)
by_after["61|RUE|ANTOINE CHARIAL"] = a61

# 2. RE-FUSE 106 BARABAN -> 61 CHARIAL
a106_after = by_after["106|RUE|BARABAN"]
a106_after["_fusion_auto"] = True
a106_after["_fusion_cible"] = LABEL
a106_after["_bdnb_match"] = "correctif_106baraban_re_fuse"

print("[OPERATIONS]")
print(f"  INJECT  61|RUE|ANTOINE CHARIAL  bgid={a61['batiment_groupe_id'][-9:]}  "
      f"immat=AE1293612  nb_lots_habit={a61['nb_lots_habitation']}  label='{LABEL}'")
print(f"  RE-FUSE 106|RUE|BARABAN         _fusion_cible='{LABEL}'  bgid inchange")
print()

# Verifications
print("[VERIFICATIONS]")
print(f"  adresses light : {len(ad)} -> {len(ad_after)}  ({len(ad_after)-len(ad):+d})")

# 106 BARABAN sort des hr-actifs (FA=True)
def count_hr_actifs(adlist, coprolist):
    cm = {(c.get("cle_adresse") or ""): c for c in coprolist}
    n = 0
    for a in adlist:
        cle = a.get("cle") or ""
        if cle in cm: continue
        if a.get("numero_immatriculation"): continue
        if a.get("_fusion_auto"): continue
        if to_int(a.get("nb_ventes_logement")) <= 0: continue
        if to_int(a.get("nb_log_bdnb")) <= 1: continue
        n += 1
    return n

hr_avant = count_hr_actifs(ad, co)
hr_apres = count_hr_actifs(ad_after, co)
print(f"  hr-actifs UI   : {hr_avant} -> {hr_apres}  ({hr_apres-hr_avant:+d})")

# 61 CHARIAL : RNC ? (via immat propage)
a61_check = by_after["61|RUE|ANTOINE CHARIAL"]
print(f"  61 CHARIAL immat : {a61_check.get('numero_immatriculation')}  "
      f"-> RNC visible: {bool(a61_check.get('numero_immatriculation'))}")
# copro SOPHIA cle_adresse reste '61|RUE|ANTOINE CHARIAL' -> match coproByCle
co_by_cle_after = {(c.get("cle_adresse") or ""): c for c in co}
print(f"  61 CHARIAL coproByCle match : {'OUI' if '61|RUE|ANTOINE CHARIAL' in co_by_cle_after else 'NON'}")

# 106 BARABAN sort hr-ancre (FA=True)
a106_check = by_after["106|RUE|BARABAN"]
print(f"  106 BARABAN apres : _fusion_auto={a106_check.get('_fusion_auto')}  "
      f"_fusion_cible='{a106_check.get('_fusion_cible')}'")

# Parc strict logement
def parc_strict(adlist):
    total, seen = 0, set()
    for a in adlist:
        nb = to_int(a.get("nb_lots_habitation"))
        if nb > 0:
            total += nb
            continue
        bg = a.get("batiment_groupe_id") or ""
        if bg and bg in seen: continue
        if bg: seen.add(bg)
        total += to_int(a.get("nb_log_bdnb"))
    return total

p_av = parc_strict(ad)
p_ap = parc_strict(ad_after)
print(f"  parc DL strict : {p_av} -> {p_ap}  ({p_ap-p_av:+d})")
print()
print("  Note : delta -1 vient de la priorite RNC nb_lots_habitation=60")
print("         sur 61 CHARIAL, ALORS QUE 106 BARABAN portait bdnb=61")
print("         dedup-bgid avant patch.")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
