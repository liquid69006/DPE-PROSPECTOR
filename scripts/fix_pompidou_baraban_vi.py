#!/usr/bin/env python3
"""Fix 48/50/52 AVENUE GEORGES POMPIDOU -> RE-FUSE vers 46 (SDC BARABAN VI
AB9345703) - Dauphine-Lacassagne.

Pattern Fondary RE-FUSE multi-bgid sur UNE seule parcelle DZ0092 - 4e
instance DL apres :
- 139 DAUPHINE -> TERRASSES DU PRESIDENT (DN0039)
- 21 PIONCHON  -> allee des poetes (DX0035)
- 44 TURBIL    -> LE PATIO DE L'ISLE (DP0051)

Configuration terrain confirmee :
- Parcelle BDNB DZ0092 (= RNC 69123383DZ0092) heberge 4 batis distincts
  (annee 1984) : 46/48/50/52 POMPIDOU
  * FS5T-27SZ-1D73 (46, 19 lgts BDNB, nb_log_rnc=74, immat AB9345703)
  * ZNN2-SAMJ-S68B (48, 18 lgts BDNB, sans immat)
  * 3489-YWPJ-BBCH (50, 18 lgts BDNB, sans immat)
  * 71B2-4HSV-Y9VP (52, 18 lgts BDNB, sans immat)
- AB9345703 SDC BARABAN VI (FONCIA SAINT LOUIS, 230 lots tot, 76 hab,
  77 stationnement, ancree cle 46 POMPIDOU dans snapshot)
- nb_log_rnc=74 sur FS5T ~ 19+18+18+18=73 BDNB cumules sur les 4 batis
  -> AB9345703 couvre les 4 batis (deduction confirmee par terrain)
- RNC nombre_adresses_complementaires=0 + nombre_parcelles=0 :
  declaratif RNC incomplete, mais terrain valide rattachement

INTOUCHE : 3 RUE DE NAZARETH (parcelle DZ0027 distincte, bati SM7M-83DM
distinct, copro AB1702901 SDC BARABAN 3 propre, programme 1976). Le
groupe immobilier "BARABAN" comprend les 2 SDC mais juridiquement
distincts.

OPS :
- RE-FUSE 48|AVENUE|GEORGES POMPIDOU : _fusion_auto=True,
  _fusion_cible='46/48/50/52 AVENUE GEORGES POMPIDOU'
- RE-FUSE 50|AVENUE|GEORGES POMPIDOU : idem
- RE-FUSE 52|AVENUE|GEORGES POMPIDOU : idem
- Creation label 46 (label vide) : '46/48/50/52 AVENUE GEORGES POMPIDOU'
  + sources=[48,50,52]

Effets : adresses 1241->1241 (0) ; hr-actifs UI 19->17 (-2, 48 et 52
sortent ; 50 etait vlog=0 deja hors hr-actif) ; parc DL UI strictement
neutre (FS5T garde RNC 74, ZNN2/YWPJ/4HSV gardent fallback BDNB 18
chacun via leurs adresses light qui restent presentes en FA).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.prepompidoubaravi.bak"

LABEL = "46/48/50/52 AVENUE GEORGES POMPIDOU"
SOURCES = ["48|AVENUE|GEORGES POMPIDOU",
           "50|AVENUE|GEORGES POMPIDOU",
           "52|AVENUE|GEORGES POMPIDOU"]


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
    if md.get("_correctif_pompidou_baraban_vi"):
        sys.exit("  [abort] _correctif_pompidou_baraban_vi deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a46 = by_cle.get("46|AVENUE|GEORGES POMPIDOU")
    if not a46:
        sys.exit("  [abort] 46 POMPIDOU absent.")
    if a46.get("numero_immatriculation") != "AB9345703":
        print(f"  [warn] 46 POMPIDOU immat={a46.get('numero_immatriculation')} "
              f"!= AB9345703 (continue)")
    for src in SOURCES:
        if not by_cle.get(src):
            sys.exit(f"  [abort] {src} absent du light.")

    # 1. RE-FUSE 48/50/52
    for cle in SOURCES:
        a = by_cle[cle]
        a["_fusion_auto"] = True
        a["_fusion_cible"] = LABEL
        a["_bdnb_match"] = "correctif_pompidou_baraban_vi_re_fuse"
        print(f"  [RE-FUSE] {cle}  _fusion_cible='{LABEL}'")

    # 2. Creation label 46
    a46["_fusion_auto_label"] = LABEL
    srcs = list(a46.get("_fusion_auto_sources") or [])
    for s in SOURCES:
        if s not in srcs:
            srcs.append(s)
    a46["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]   46|AVENUE|GEORGES POMPIDOU  label='{LABEL}'")
    print(f"             sources={srcs}")

    md["_correctif_pompidou_baraban_vi"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Fondary RE-FUSE multi-bgid une parcelle (DZ0092) "
                   "- 4e instance DL",
        "autorite": "BDNB nb_log_rnc=74 sur FS5T-27SZ-1D73 ~= 73 lgts BDNB "
                    "cumules 4 batis (19+18+18+18) + AB9345703 SDC BARABAN VI "
                    "ancree cle 46 + terrain confirme",
        "ops": "RE-FUSE 48/50/52 POMPIDOU vers 46 + creation label ancre",
        "snapshot_immat": "AB9345703 SDC BARABAN VI (230/76 hab, FONCIA SAINT "
                          "LOUIS, cle 46 POMPIDOU)",
        "batis_bdnb": {
            "46": "FS5T-27SZ-1D73",
            "48": "ZNN2-SAMJ-S68B",
            "50": "3489-YWPJ-BBCH",
            "52": "71B2-4HSV-Y9VP",
        },
        "label": LABEL,
        "delta_parc_ui": 0,
        "intouche": "3 RUE DE NAZARETH (DZ0027, SM7M-83DM, AB1702901 SDC "
                    "BARABAN 3, programme 1976) - copro distincte legitime",
        "terrain_confirme": "Ensemble immobilier BARABAN VI = 4 batis "
                            "1984 sur DZ0092 ; le groupe BARABAN comprend "
                            "aussi BARABAN 3 (3 NAZARETH, autre SDC).",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] 3 RE-FUSE + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
