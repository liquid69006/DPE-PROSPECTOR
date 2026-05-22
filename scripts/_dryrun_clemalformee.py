#!/usr/bin/env python3
"""DRYRUN REBIND cle_adresse - 3 copros malformees DL.

Pattern REBIND : 3 copros RNC dans coproprietes[] ont cle_adresse
malformee '|TYPE|VOIE' (bug make_light DL extraction num). Apres
investigation parcellaire, leur vrai numero a ete identifie. On
patche la cle_adresse + on propage immat/nb_lots/syndic vers
l'adresse correspondante (qui existe deja comme hr-actif).

3 copros :
  - AD9757634  |RUE|PAUL BERT     -> 272|RUE|PAUL BERT (EDEN PART DIEU 71 lots)
  - AD5250634  |COURS|LAFAYETTE   -> 310|COURS|LAFAYETTE (35 lots)
  - AC6769996  |RUE|DAUPHINE      -> 75|RUE|DAUPHINE (26 lots)

Verifications :
- hr-actifs avant : 272 PAUL BERT, 310 LAFAYETTE, 75 DAUPHINE
- hr-actifs apres : ces 3 SORTENT (coproByCle match) -> 25 hr-actifs
- adresses gagnent immat + nb_lots_habitation + syndic + taux_rotation
- parc DL : effet sur dedup-bgid + comptage RNC

Champs propages (depuis copro RNC) :
  numero_immatriculation, nb_lots_habitation, taux_rotation,
  classement_rotation, syndic, _syndic_src.
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

# 3 REBIND : ancien cle -> (immat, nouvelle cle)
REBIND = [
    ("AD9757634", "|RUE|PAUL BERT",     "272|RUE|PAUL BERT"),
    ("AD5250634", "|COURS|LAFAYETTE",   "310|COURS|LAFAYETTE"),
    ("AC6769996", "|RUE|DAUPHINE",      "75|RUE|DAUPHINE"),
]

# AVANT
print("=" * 76)
print("DRYRUN REBIND cle_adresse 3 copros malformees DL")
print("=" * 76)
print()
print("[1] Etat AVANT - copros cibles :")
co_by_immat = {c.get("numero_immatriculation"): c for c in co}
for immat, old_cle, new_cle in REBIND:
    c = co_by_immat.get(immat)
    if not c:
        print(f"  [ERR] copro {immat} non trouvee")
        continue
    print(f"  - {immat}  cle_adresse='{c.get('cle_adresse')}'  nom='{c.get('nom_copropriete')[:38]}'")
    print(f"      nb_lots_total={c.get('nb_lots_total')} nb_lots_hab={c.get('nb_lots_habitation')}  "
          f"syndic={(c.get('syndic') or '-')[:30]}")
    if c.get("cle_adresse") != old_cle:
        print(f"      ! ATTENTION cle actuelle '{c.get('cle_adresse')}' != attendu '{old_cle}'")

print()
print("[2] Etat AVANT - hr-actifs cibles :")
ad_by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}
for immat, old_cle, new_cle in REBIND:
    a = ad_by_cle.get(new_cle)
    if not a:
        print(f"  [ERR] adresse {new_cle} non trouvee dans light")
        continue
    has_copro = new_cle in co_by_cle
    is_hr = (not has_copro) and (not a.get("numero_immatriculation")) and (not a.get("_fusion_auto"))
    is_hr_actif = is_hr and to_int(a.get("nb_ventes_logement")) > 0 and to_int(a.get("nb_log_bdnb")) > 1
    print(f"  - {new_cle:24s} bdnb={a.get('nb_log_bdnb')} vlog={a.get('nb_ventes_logement')}  "
          f"hr_ancre={is_hr} hr_actif={is_hr_actif}")
    print(f"      immat actuel={a.get('numero_immatriculation') or '-'}  "
          f"nb_lots_hab actuel={a.get('nb_lots_habitation') or '-'}  "
          f"syndic actuel={(a.get('syndic') or '-')[:30]}")

print()

# Simulation
ad_after = copy.deepcopy(ad)
co_after = copy.deepcopy(co)
co_by_immat_after = {c.get("numero_immatriculation"): c for c in co_after}
ad_by_cle_after = {(a.get("cle") or ""): a for a in ad_after}

CHAMPS_PROP = [
    "numero_immatriculation",
    "nb_lots_habitation",
    "taux_rotation",
    "classement_rotation",
    "syndic",
    "_syndic_src",
]

ops = []
for immat, old_cle, new_cle in REBIND:
    c = co_by_immat_after.get(immat)
    a = ad_by_cle_after.get(new_cle)
    if not c or not a:
        ops.append((immat, "SKIP", "manquant"))
        continue

    # Patch cle_adresse copro
    c_old = c.get("cle_adresse")
    c["cle_adresse"] = new_cle

    # Propager champs vers adresse
    prop_log = {}
    for f in CHAMPS_PROP:
        # Mapping particulier : taux_rotation provient de
        # taux_rotation_5ans cote copro ; classement_rotation idem
        if f == "taux_rotation":
            val = c.get("taux_rotation_5ans")
        elif f == "classement_rotation":
            val = c.get("classement_rotation")
        else:
            val = c.get(f)
        if val is None or val == "":
            continue
        if a.get(f) != val:
            prop_log[f] = (a.get(f), val)
            a[f] = val
    # Marqueur traçabilite
    a["_bdnb_match"] = "immat_rebind_clemalformee"
    ops.append((immat, "REBIND", {
        "copro_cle": (c_old, new_cle),
        "addr_props": prop_log,
    }))

# Affichage ops
print("[3] OPERATIONS simulees :")
for immat, kind, det in ops:
    print(f"  - {immat} [{kind}]")
    if isinstance(det, dict):
        print(f"      copro cle_adresse : '{det['copro_cle'][0]}' -> '{det['copro_cle'][1]}'")
        if det["addr_props"]:
            print(f"      adresse propagations :")
            for f, (old, new) in det["addr_props"].items():
                old_s = str(old)[:50] if old is not None else "(absent)"
                new_s = str(new)[:50]
                print(f"        {f}: {old_s} -> {new_s}")

# Verifications APRES
print()
print("[4] Verification APRES - les 3 adresses sont-elles RNC ?")
co_by_cle_after = {(c.get("cle_adresse") or ""): c for c in co_after}
for immat, old_cle, new_cle in REBIND:
    a = ad_by_cle_after.get(new_cle)
    has_copro = new_cle in co_by_cle_after
    is_hr = (not has_copro) and (not a.get("numero_immatriculation"))
    print(f"  - {new_cle:24s} copro_match={has_copro} immat_set={a.get('numero_immatriculation') or '-'}  "
          f"-> {'RNC' if (has_copro and a.get('numero_immatriculation')) else 'KO'}")

# hr-actifs avant/apres count
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

print()
print("[5] hr-actifs UI :")
print(f"  AVANT : {count_hr_actifs(ad, co)}")
print(f"  APRES : {count_hr_actifs(ad_after, co_after)}")

# Parc strict logement (dedup bgid + priorite nb_lots_habit propage)
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

print()
print("[6] Parc DL strict logement :")
p_av = parc_strict(ad)
p_ap = parc_strict(ad_after)
print(f"  AVANT : {p_av}")
print(f"  APRES : {p_ap}")
print(f"  DELTA : {p_ap - p_av:+d}")
print()
print("  Note : delta correspond aux propagations nb_lots_habitation")
print("  (avant : bdnb_dedup ; apres : RNC lots_habit autoritaire)")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
