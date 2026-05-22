#!/usr/bin/env python3
"""Fix REBIND cle_adresse - 3 copros malformees DL (bug make_light DL
extraction num). 3 hr-actifs basculent en RNC + propagation immat.

Pattern nouveau : REBIND cle_adresse. Quand make_light n'a pas su
extraire le numero d'une copro RNC, sa cle_adresse devient '|TYPE|VOIE'
(num vide). L'investigation parcellaire (croisement
rel_batiment_groupe_parcelle BDNB <-> reference_cadastrale_X RNC live)
identifie la vraie adresse. On patche cle_adresse + on propage
immat/nb_lots/syndic/taux/classement vers l'adresse light qui existe
deja (hr-actif).

3 cas DL :
  - AD9757634  |RUE|PAUL BERT     -> 272|RUE|PAUL BERT (EDEN PART DIEU 71/35)
  - AD5250634  |COURS|LAFAYETTE   -> 310|COURS|LAFAYETTE (35/11)
  - AC6769996  |RUE|DAUPHINE      -> 75|RUE|DAUPHINE (26/10)

hr-actifs UI 28 -> 25 ; parc DL 30624 -> 30628 (+4, RNC autoritaire).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.preclemalformee.bak"

REBIND = [
    ("AD9757634", "|RUE|PAUL BERT",     "272|RUE|PAUL BERT"),
    ("AD5250634", "|COURS|LAFAYETTE",   "310|COURS|LAFAYETTE"),
    ("AC6769996", "|RUE|DAUPHINE",      "75|RUE|DAUPHINE"),
]

CHAMPS_PROP = [
    "numero_immatriculation",
    "nb_lots_habitation",
    "taux_rotation",
    "classement_rotation",
    "syndic",
    "_syndic_src",
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
    if md.get("_correctif_clemalformee_dl"):
        sys.exit("  [abort] _correctif_clemalformee_dl deja present.")

    co_by_immat = {c.get("numero_immatriculation"): c for c in co}
    ad_by_cle = {(a.get("cle") or ""): a for a in ad}

    nb_ops = 0
    details = []

    for immat, old_cle, new_cle in REBIND:
        c = co_by_immat.get(immat)
        a = ad_by_cle.get(new_cle)
        if not c:
            print(f"  [ERR] copro {immat} absente -> skip")
            continue
        if not a:
            print(f"  [ERR] adresse {new_cle} absente -> skip")
            continue
        if c.get("cle_adresse") != old_cle:
            print(f"  [WARN] {immat} cle actuelle '{c.get('cle_adresse')}' "
                  f"!= attendu '{old_cle}' (patch quand meme)")

        # 1. Patch cle_adresse copro
        c["cle_adresse"] = new_cle

        # 2. Propagation copro -> adresse
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
        details.append({
            "immat": immat, "old_cle": old_cle, "new_cle": new_cle,
            "propagations": list(prop.keys()),
        })
        nb_ops += 1
        print(f"  [REBIND] {immat}  '{old_cle}' -> '{new_cle}'  "
              f"+ propag {list(prop.keys())}")

    md["_correctif_clemalformee_dl"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "REBIND cle_adresse (bug make_light DL extraction num)",
        "autorite": "BDNB rel_batiment_groupe_parcelle + RNC live reference_cadastrale_X",
        "ops_count": nb_ops,
        "details": details,
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] {nb_ops} REBIND appliques.")


if __name__ == "__main__":
    main()
