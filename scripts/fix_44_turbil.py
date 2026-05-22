#!/usr/bin/env python3
"""Fix 44 RUE TURBIL -> RE-FUSE vers 153 RUE BARABAN (LE PATIO DE L'ISLE
AB0535203) - Dauphine-Lacassagne.

Pattern Fondary RE-FUSE multi-bgid sur UNE seule parcelle DP0051
(3e instance DL apres 139 DAUPHINE -> TERRASSES DU PRESIDENT et
21 PIONCHON -> allee des poetes).

Configuration confirmee (5 preuves convergentes) :
1. RNC live AB0535203 LE PATIO DE L'ISLE (SOC ADMIN & GESTION IMMEUB
   ROLIN BAINSON, 120 lots / 43 hab) declare explicitement
   '44 r turbil 69003 LYON' dans adresse_complementaire_1
2. Parcelle BDNB DP0051 identique pour les 2 batis :
   - UN53-G1LZ-2P34 (44 TURBIL, 27 lgts, 2005)
   - HD5Z-A5ZB-RL1N (153 BARABAN, 16 lgts, 2005,
     immat_principal AB0535203)
3. 27+16 BDNB = 43 ~= 43 RNC hab (match exact)
4. Periode construction identique (2005)
5. Terrain utilisateur confirme : meme ensemble immobilier

Particularite : RNC AB0535203 nombre_parcelles=0 (aucune ref_cad
declaree). Snapshot a reussi a attribuer via adresse_reference
'153 r baraban'. Methode alternative make_light.

OPS :
- RE-FUSE 44|RUE|TURBIL : _fusion_auto=True,
  _fusion_cible='153 RUE BARABAN / 44 RUE TURBIL'
- Creation label 153 BARABAN ancre (label vide actuellement) :
  '153 RUE BARABAN / 44 RUE TURBIL' + sources=['44|RUE|TURBIL']

PAS d'INJECT copro (AB0535203 deja ancree cle 153 BARABAN).

Effets :
- adresses 1241 -> 1241 (0)
- hr-actifs UI 20 -> 19 (-1, 44 TURBIL sort en FA)
- parc DL UI strictement neutre (G1LZ garde fallback BDNB 27,
  A5ZB garde RNC 43)
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre44turbil.bak"

LABEL = "153 RUE BARABAN / 44 RUE TURBIL"


def main():
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_44_turbil"):
        sys.exit("  [abort] _correctif_44_turbil deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a44 = by_cle.get("44|RUE|TURBIL")
    a153 = by_cle.get("153|RUE|BARABAN")
    if not a44:
        sys.exit("  [abort] 44|RUE|TURBIL absent.")
    if not a153:
        sys.exit("  [abort] 153|RUE|BARABAN absent.")
    if a153.get("numero_immatriculation") != "AB0535203":
        print(f"  [warn] 153 BARABAN immat={a153.get('numero_immatriculation')} "
              f"!= AB0535203 (continue)")

    # 1. RE-FUSE 44 TURBIL
    a44["_fusion_auto"] = True
    a44["_fusion_cible"] = LABEL
    a44["_bdnb_match"] = "correctif_44turbil_re_fuse"
    print(f"  [RE-FUSE] 44|RUE|TURBIL  _fusion_cible='{LABEL}'")

    # 2. Maj ancre 153 BARABAN (label vierge -> nouveau)
    a153["_fusion_auto_label"] = LABEL
    srcs = list(a153.get("_fusion_auto_sources") or [])
    if "44|RUE|TURBIL" not in srcs:
        srcs.append("44|RUE|TURBIL")
    a153["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]   153|RUE|BARABAN  label='{LABEL}'  sources={srcs}")

    md["_correctif_44_turbil"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Fondary RE-FUSE multi-bgid une parcelle (DP0051) "
                   "- 3e instance DL",
        "autorite": "RNC live AB0535203 adresse_complementaire_1='44 r turbil' "
                    "+ BDNB rel_parcelle DP0051 = UN53-G1LZ-2P34 + HD5Z-A5ZB-RL1N",
        "ops": "RE-FUSE 44|RUE|TURBIL vers 153 BARABAN + creation label",
        "snapshot_immat": "AB0535203 LE PATIO DE L'ISLE (120/43 hab, SOC ADMIN "
                          "& GESTION IMMEUB ROLIN BAINSON, cle 153 BARABAN)",
        "label": LABEL,
        "delta_parc_ui": 0,
        "particularite_rnc": "nombre_parcelles=0 cote RNC live (aucune ref_cad "
                             "declaree) ; snapshot a utilise adresse_reference "
                             "pour rattacher AB0535203 a cle 153 BARABAN",
        "terrain_confirme": "44 TURBIL et 153 BARABAN = meme ensemble immobilier "
                            "(annee 2005, 43 hab cumules)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 RE-FUSE + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
