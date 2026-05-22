#!/usr/bin/env python3
"""Fix REBIND cle_adresse - 9 RUE ST EUSEBE (DL).

Suite a fix_clemalformee (3 cas precedents), il restait 2 copros cle
malformee :
  - AD6934400 '9 rue St Eusebe' : |RUE|ST EUSEBE -> 9|RUE|ST EUSEBE  (TRAITE ici)
  - AB9784521 'BRICKS'           : |AVENUE|LACASSAGNE -> ??           (NON TRAITE)

Pourquoi BRICKS reste avec cle malformee ?
- BRICKS (AB9784521, 186/97hab) et BRICKS 1 (AD5268305, 188/98hab) sont
  2 copros tres similaires. AD5268305 BRICKS 1 a deja ete attribuee
  au bati 20 LACASSAGNE (bgid 8MZ7-KS1W, bdnb=97) via une adresse
  light composite '20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE'
  (creee par fix-multiparcelles-dl-lot2).
- REBIND AB9784521 -> 20|AVENUE|LACASSAGNE creerait un double-comptage
  de 97 lots habit sur le bati 8MZ7 (qui contribue deja 98 via BRICKS 1).
- Sans enquete terrain confirmant si BRICKS et BRICKS 1 sont (a) le
  meme bati avec re-immat, (b) phases 1+2 distinctes, ou (c) 1 SDC +
  1 ASL : on garde le statu quo (cle malformee = visibilite preservee
  en UI sans corruption parc).

9 RUE ST EUSEBE - cas simple :
- AD6934400 nom_copropriete = '9 rue St Eusebe' (le numero est dans
  le nom et dans adresse_complementaire_1='9 r saint-eusebe')
- 9|RUE|ST EUSEBE existe en light : hr-actif vlog=5 bdnb=18 bgid PG6T
- REBIND + propagation immat/lots/syndic ; parc DL UI +7 (BDNB 18 ->
  RNC 25 autoritaire) ; hr-actifs UI 23->22.
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre9eusebe.bak"

CHAMPS_PROP = [
    "numero_immatriculation","nb_lots_habitation","taux_rotation",
    "classement_rotation","syndic","_syndic_src",
]


def main():
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc["coproprietes"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_9eusebe"):
        sys.exit("  [abort] _correctif_9eusebe deja present.")

    co_by_immat = {c.get("numero_immatriculation"): c for c in co
                   if c.get("numero_immatriculation")}
    by_cle = {(a.get("cle") or ""): a for a in ad}

    immat = "AD6934400"
    old_cle = "|RUE|ST EUSEBE"
    new_cle = "9|RUE|ST EUSEBE"

    c = co_by_immat.get(immat)
    a = by_cle.get(new_cle)
    if not c:
        sys.exit(f"  [abort] copro {immat} absente")
    if not a:
        sys.exit(f"  [abort] adresse {new_cle} absente")
    if c.get("cle_adresse") != old_cle:
        print(f"  [warn] cle actuelle '{c.get('cle_adresse')}' != attendu '{old_cle}'")

    c["cle_adresse"] = new_cle
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

    print(f"  [REBIND] {immat}  '{old_cle}' -> '{new_cle}'")
    for f, (old_v, new_v) in prop.items():
        print(f"    propag {f}: {old_v} -> {new_v}")

    md["_correctif_9eusebe"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "REBIND cle_adresse (variante adresse_complementaire_1)",
        "autorite": "RNC live AD6934400 nom_copro '9 rue St Eusebe' + "
                    "adresse_complementaire_1='9 r saint-eusebe'",
        "ops": "REBIND cle copro + propagation immat/lots/syndic",
        "immat": immat,
        "lots_tot": c.get("nb_lots_total"),
        "lots_habit": c.get("nb_lots_habitation"),
        "syndic": c.get("syndic"),
        "delta_parc_ui": 7,
        "non_traite": {
            "immat": "AB9784521",
            "nom": "BRICKS",
            "raison": "Collision potentielle BRICKS vs BRICKS 1 (AD5268305) "
                      "sur meme bati 8MZ7-KS1W via cle composite "
                      "'20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE'. "
                      "REBIND creerait double-comptage 97 lots. Enquete "
                      "terrain requise (BRICKS = re-immat AD5268305 ? "
                      "phases distinctes ? SDC+ASL ?).",
        },
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 REBIND applique.")


if __name__ == "__main__":
    main()
