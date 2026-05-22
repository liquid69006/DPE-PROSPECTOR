#!/usr/bin/env python3
"""DRYRUN 139 DAUPHINE -> RE-FUSE vers 238/240 FELIX FAURE.

Pattern Fondary RE-FUSE multi-bgid meme parcelle :
- Parcelle DN0039 heberge 2 batis BDNB distincts :
  HQ5A-SU4G (139 DAUPH 20 lgts 1991, mono-adresse BAN)
  MU33-65VW (238/240 FF 29 lgts 1992, immat_principal AB1862135)
- 1 seule copropriete RNC physique couvre les 3 adresses :
  AB1862135 LES TERRASSES DU PRESIDENT (snapshot 2019, 169 lots,
  cle '238|AVENUE|FELIX FAURE') = meme entite re-immatriculee
  AJ6692420 (RNC live 2026-03-16, mandat expire)

Le RNC AJ6692420 explicite l'autorite multi-adresses :
  adresse_reference        : 238 Avenue Felix Faure
  adresse_complementaire_1 : 240 Avenue Felix Faure
  adresse_complementaire_2 : 139 Rue du Dauphine

MECANISME :
  1. RE-FUSE 139|RUE|DAUPHINE : _fusion_auto=True,
     _fusion_cible label etendu
  2. 238 FF ancre : etendre label '238/240 AV FELIX FAURE'
     -> '238/240 AV FELIX FAURE / 139 RUE DAUPHINE'
     + sources += ['139|RUE|DAUPHINE']

PAS d'INJECT copro, PAS de modif snapshot RNC (AB1862135 reste
l'autorite snapshot ; la re-immat AJ6692420 est un sujet separe).
Le bati HQ5A-SU4G garde sa contribution BDNB 20 (fallback car
139 reste sans copro). Algo UI : delta parc strictement neutre.
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
a139 = by_cle["139|RUE|DAUPHINE"]
a238 = by_cle["238|AVENUE|FELIX FAURE"]

LABEL = "238/240 AVENUE FELIX FAURE / 139 RUE DAUPHINE"

print("=" * 72)
print("DRYRUN 139 DAUPHINE -> RE-FUSE vers 238/240 FELIX FAURE")
print("=" * 72)
print()
print("[AVANT]")
print(f"  139 DAUPH : bgid={a139['batiment_groupe_id'][-9:]}  "
      f"bdnb={a139.get('nb_log_bdnb')} vlog={a139.get('nb_ventes_logement')}  "
      f"SCI={a139.get('sci_nom')}  immat={a139.get('numero_immatriculation') or '-'}")
print(f"  238 FF    : bgid={a238['batiment_groupe_id'][-9:]}  "
      f"immat={a238.get('numero_immatriculation')}  "
      f"lots_hab={a238.get('nb_lots_habitation')}  "
      f"label='{a238.get('_fusion_auto_label')}'  "
      f"src={a238.get('_fusion_auto_sources')}")
print()

# Simulation
ad_after = copy.deepcopy(ad)
by_after = {(a.get("cle") or ""): a for a in ad_after}

a139_aft = by_after["139|RUE|DAUPHINE"]
a139_aft["_fusion_auto"] = True
a139_aft["_fusion_cible"] = LABEL
a139_aft["_bdnb_match"] = "correctif_139dauph_re_fuse"

a238_aft = by_after["238|AVENUE|FELIX FAURE"]
old_label = a238_aft.get("_fusion_auto_label")
old_srcs  = list(a238_aft.get("_fusion_auto_sources") or [])
a238_aft["_fusion_auto_label"] = LABEL
if "139|RUE|DAUPHINE" not in old_srcs:
    old_srcs.append("139|RUE|DAUPHINE")
a238_aft["_fusion_auto_sources"] = old_srcs

print("[OPS]")
print(f"  [RE-FUSE] 139|RUE|DAUPHINE  _fusion_cible='{LABEL}'")
print(f"  [LABEL]   238|AVENUE|FELIX FAURE :")
print(f"      label '{old_label}' -> '{LABEL}'")
print(f"      sources += ['139|RUE|DAUPHINE']  -> {a238_aft['_fusion_auto_sources']}")
print()

# Verifs
print("[VERIFICATIONS]")
print(f"  139 DAUPH _fusion_auto : {a139_aft.get('_fusion_auto')}  (attendu True)")
print(f"  139 DAUPH _fusion_cible : '{a139_aft.get('_fusion_cible')}'")

# Algo UI exact
def parc_ui(adlist, colist):
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in colist}
    bgRncLots, bgBdnbResid = {}, {}
    for a in adlist:
        cle = a.get("cle") or ""
        bg = a.get("batiment_groupe_id") or ""
        if not bg: continue
        c = co_by_cle.get(cle)
        if c:
            lots = to_int(c.get("nb_lots_habitation"))
            if lots > 0:
                bgRncLots.setdefault(bg, {})[cle] = lots
        else:
            bdnb = to_int(a.get("nb_log_bdnb"))
            if bdnb > 0 and bg not in bgBdnbResid:
                bgBdnbResid[bg] = bdnb
    total = 0
    for bg in set(list(bgRncLots.keys()) + list(bgBdnbResid.keys())):
        total += sum(bgRncLots[bg].values()) if bg in bgRncLots else bgBdnbResid.get(bg, 0)
    return total

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
print(f"  parc DL UI       : {p_av} -> {p_ap}  ({p_ap-p_av:+d})")
print(f"  hr-actifs UI     : {hr_av} -> {hr_ap}  ({hr_ap-hr_av:+d})")
print(f"  adresses light   : {len(ad)} -> {len(ad_after)}  ({len(ad_after)-len(ad):+d})")
print()

# Inventaire bgid HQ5A + MU33 apres
print("[INVENTAIRE bgids cibles APRES]")
for label, bg in [("HQ5A (139 DAUPH)", "bdnb-bg-6PR8-HQ5A-SU4G"),
                  ("MU33 (238/240 FF)", "bdnb-bg-PJUP-MU33-65VW")]:
    cles = [a.get("cle") for a in ad_after if a.get("batiment_groupe_id") == bg]
    print(f"  {label:24s} : {cles}")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
