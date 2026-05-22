#!/usr/bin/env python3
"""DRYRUN 21 PIONCHON -> RE-FUSE vers 24/26 CITE (allée des poetes).

CONFIRMATIONS :
- AA0823708 'allee des poetes' (372/126 hab, SAGNIMORTE) declare
  explicitement 21B r claudius pionchon dans adresse_complementaire_1.
- Parcelle BDNB DX0035 identique entre 21 PIONCHON, 24 CITE, 26 CITE :
  3 batis distincts sur 1 parcelle.
- SCI CAMAC partagee (21 PIONCHON et 24 CITE) = meme groupe bailleur.
- 22 + 28 CITE sont copros distinctes (AD8652125 + AF4379210) sur
  autres parcelles -> NON inclus dans 'allee des poetes'.

OPS :
- RE-FUSE 21|RUE|CLAUDIUS PIONCHON : _fusion_auto=True,
  _fusion_cible='24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON'
- Etendre label 24 CITE ancre :
  '24/26 RUE CITE' -> '24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON'
  + sources += ['21|RUE|CLAUDIUS PIONCHON']

PAS d'INJECT copro (AA0823708 deja ancree sur 24 CITE).
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
a21 = by_cle["21|RUE|CLAUDIUS PIONCHON"]
a24 = by_cle["24|RUE|CITE"]
a26 = by_cle["26|RUE|CITE"]

LABEL = "24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON"

print("=" * 76)
print("DRYRUN 21 PIONCHON -> RE-FUSE vers 24/26 CITE (allee des poetes)")
print("=" * 76)
print()
print("[AVANT]")
print(f"  21 PIONCHON : bgid={a21['batiment_groupe_id'][-9:]}  "
      f"bdnb={a21.get('nb_log_bdnb')} vlog={a21.get('nb_ventes_logement')}  "
      f"SCI={a21.get('sci_nom')}  immat=-")
print(f"  24 CITE     : bgid={a24['batiment_groupe_id'][-9:]}  "
      f"immat={a24.get('numero_immatriculation')}  "
      f"lots_hab={a24.get('nb_lots_habitation')}  "
      f"label='{a24.get('_fusion_auto_label')}'  "
      f"src={a24.get('_fusion_auto_sources')}")
print(f"  26 CITE     : bgid={a26['batiment_groupe_id'][-9:]}  "
      f"_fa={a26.get('_fusion_auto')}  cible='{a26.get('_fusion_cible')}'")

# Simulation
ad_after = copy.deepcopy(ad)
by_after = {(a.get("cle") or ""): a for a in ad_after}

a21_aft = by_after["21|RUE|CLAUDIUS PIONCHON"]
a21_aft["_fusion_auto"] = True
a21_aft["_fusion_cible"] = LABEL
a21_aft["_bdnb_match"] = "correctif_21pionchon_re_fuse"

a24_aft = by_after["24|RUE|CITE"]
old_label = a24_aft.get("_fusion_auto_label")
old_srcs  = list(a24_aft.get("_fusion_auto_sources") or [])
a24_aft["_fusion_auto_label"] = LABEL
if "21|RUE|CLAUDIUS PIONCHON" not in old_srcs:
    old_srcs.append("21|RUE|CLAUDIUS PIONCHON")
a24_aft["_fusion_auto_sources"] = old_srcs

print()
print("[OPS]")
print(f"  [RE-FUSE] 21|RUE|CLAUDIUS PIONCHON  _fusion_cible='{LABEL}'")
print(f"  [LABEL]   24|RUE|CITE :")
print(f"      label '{old_label}' -> '{LABEL}'")
print(f"      sources += ['21|RUE|CLAUDIUS PIONCHON']  -> {a24_aft['_fusion_auto_sources']}")

# Algo UI exact pour parc
def parc_ui(adlist, colist):
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in colist}
    bgRnc, bgBd = {}, {}
    for a in adlist:
        cle = a.get("cle") or ""; bg = a.get("batiment_groupe_id") or ""
        if not bg: continue
        c = co_by_cle.get(cle)
        if c:
            lots = to_int(c.get("nb_lots_habitation"))
            if lots > 0: bgRnc.setdefault(bg,{})[cle] = lots
        else:
            bdnb = to_int(a.get("nb_log_bdnb"))
            if bdnb > 0 and bg not in bgBd: bgBd[bg] = bdnb
    t = 0
    for bg in set(list(bgRnc.keys())+list(bgBd.keys())):
        t += sum(bgRnc[bg].values()) if bg in bgRnc else bgBd.get(bg, 0)
    return t

def count_hr(adlist, colist):
    cm = {(c.get("cle_adresse") or ""): c for c in colist}
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

p_av, p_ap = parc_ui(ad, co), parc_ui(ad_after, co)
hr_av, hr_ap = count_hr(ad, co), count_hr(ad_after, co)
print()
print("[VERIFICATIONS]")
print(f"  21 PIONCHON _fusion_auto : {a21_aft.get('_fusion_auto')}  (attendu True)")
print(f"  24 CITE label etendu     : '{a24_aft.get('_fusion_auto_label')}'")
print(f"  parc DL UI   : {p_av} -> {p_ap}  ({p_ap-p_av:+d})")
print(f"  hr-actifs UI : {hr_av} -> {hr_ap}  ({hr_ap-hr_av:+d})")
print(f"  adresses     : {len(ad)} -> {len(ad_after)}  ({len(ad_after)-len(ad):+d})")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
