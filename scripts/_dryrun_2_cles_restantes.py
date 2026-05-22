#!/usr/bin/env python3
"""DRYRUN REBIND 2 copros cle malformee restantes DL :
  - AB9784521 BRICKS    : |AVENUE|LACASSAGNE -> 20|AVENUE|LACASSAGNE
  - AD6934400 9 St Eusebe : |RUE|ST EUSEBE  -> 9|RUE|ST EUSEBE

Identification :
- BRICKS    : bdnb=97 lgts 20 LACASSAGNE (bgid 8MZ7-KS1W, 2018) =
              match exact nb_lots_habitation=97 (preuve forte).
              Cohabitation avec BRICKS 1 AD5268305 (cle composite
              '20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE') heritee
              de fix-multiparcelles-dl-lot2.
              20 LACASSAGNE reste FA->BRICKS1 ; gagne juste immat
              propre AB9784521 (97 hab residentiel principal).
- 9 ST EUSEBE : nom copro 'AD6934400 9 rue St Eusebe' +
                adresse_complementaire_1 RNC 'r saint-eusebe' avec
                num 9 = preuve directe. 9|RUE|ST EUSEBE existe en
                hr-actif (bdnb=18 vlog=5 bgid PG6T-JXF4).
                REBIND propre + propagation 25 hab (RNC autoritaire).

Effets attendus :
- copros : 2 cle_adresse patches (pas d'INJECT)
- adresses : 2 propagations immat/lots/syndic
- hr-actifs UI : -1 (9 ST EUSEBE sort, 20 LACASSAGNE etait deja FA)
- parc DL UI :
  - 20 LACASSAGNE bgid 8MZ7 : BDNB 97 -> RNC 97 (delta 0)
  - 9 ST EUSEBE bgid PG6T : BDNB 18 -> RNC 25 (delta +7)
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

REBIND = [
    ("AB9784521", "|AVENUE|LACASSAGNE", "20|AVENUE|LACASSAGNE"),
    ("AD6934400", "|RUE|ST EUSEBE",     "9|RUE|ST EUSEBE"),
]

CHAMPS_PROP = [
    "numero_immatriculation","nb_lots_habitation","taux_rotation",
    "classement_rotation","syndic","_syndic_src",
]

print("=" * 72)
print("DRYRUN REBIND 2 copros cle malformee restantes DL")
print("=" * 72)

# AVANT
print()
print("[AVANT] :")
co_by_immat = {c.get("numero_immatriculation"): c for c in co
               if c.get("numero_immatriculation")}
by_cle = {(a.get("cle") or ""): a for a in ad}
for immat, old, new in REBIND:
    c = co_by_immat.get(immat)
    a = by_cle.get(new)
    print(f"  {immat} '{c.get('nom_copropriete') if c else '?'}' :")
    print(f"    copro.cle_adresse actuel = '{c.get('cle_adresse') if c else '?'}'")
    print(f"    adresse cible '{new}' :")
    if not a:
        print(f"      ABSENTE ! INJECT requis")
    else:
        print(f"      bgid={a.get('batiment_groupe_id')}  bdnb={a.get('nb_log_bdnb')}  "
              f"vlog={a.get('nb_ventes_logement')}  immat={a.get('numero_immatriculation') or '-'}")
        if a.get("_fusion_auto"):
            print(f"      _fusion_auto=True  _fusion_cible='{a.get('_fusion_cible')}'")
print()

# Simulation
ad_after = copy.deepcopy(ad)
co_after = copy.deepcopy(co)
co_by_immat_aft = {c.get("numero_immatriculation"): c for c in co_after
                   if c.get("numero_immatriculation")}
by_after = {(a.get("cle") or ""): a for a in ad_after}

print("[OPS simulees] :")
for immat, old, new in REBIND:
    c = co_by_immat_aft[immat]
    a = by_after[new]
    c_old_cle = c.get("cle_adresse")
    c["cle_adresse"] = new
    prop = {}
    for f in CHAMPS_PROP:
        if f == "taux_rotation":
            val = c.get("taux_rotation_5ans")
        elif f == "classement_rotation":
            val = c.get("classement_rotation")
        else:
            val = c.get(f)
        if val is None or val == "":
            continue
        if a.get(f) != val:
            prop[f] = (a.get(f), val)
            a[f] = val
    a["_bdnb_match"] = "immat_rebind_clemalformee"
    print(f"  {immat} : copro cle '{c_old_cle}' -> '{new}'")
    for f, (old_v, new_v) in prop.items():
        print(f"    propag {f}: {old_v} -> {new_v}")

# Verifs
print()
print("[VERIFICATIONS] :")
co_by_cle_aft = {(c.get("cle_adresse") or ""): c for c in co_after}
for immat, old, new in REBIND:
    a = by_after.get(new)
    print(f"  {new}: copro_match={'OUI' if new in co_by_cle_aft else 'NON'}  "
          f"immat={a.get('numero_immatriculation')}")

# Parc + hr-actifs
def parc_ui(adlist, colist):
    cm = {(c.get("cle_adresse") or ""): c for c in colist}
    bgRnc, bgBd = {}, {}
    for a in adlist:
        cle = a.get("cle") or ""; bg = a.get("batiment_groupe_id") or ""
        if not bg: continue
        c = cm.get(cle)
        if c:
            lots = to_int(c.get("nb_lots_habitation"))
            if lots > 0:
                bgRnc.setdefault(bg, {})[cle] = lots
        else:
            bdnb = to_int(a.get("nb_log_bdnb"))
            if bdnb > 0 and bg not in bgBd:
                bgBd[bg] = bdnb
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

p_av = parc_ui(ad, co); p_ap = parc_ui(ad_after, co_after)
hr_av = count_hr(ad, co); hr_ap = count_hr(ad_after, co_after)
print(f"  parc DL UI    : {p_av} -> {p_ap}  ({p_ap-p_av:+d})")
print(f"  hr-actifs UI  : {hr_av} -> {hr_ap}  ({hr_ap-hr_av:+d})")

# Verifications copros restantes malformees
print()
print("[Copros cle malformee restantes apres patch] :")
n_reste = 0
for c in co_after:
    cle = c.get("cle_adresse") or ""
    if cle.startswith("|"):
        print(f"  - '{cle}' {c.get('numero_immatriculation')} '{c.get('nom_copropriete','')[:40]}'")
        n_reste += 1
if n_reste == 0:
    print("  AUCUNE - piste A entierement traitee !")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
