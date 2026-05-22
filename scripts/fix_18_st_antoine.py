#!/usr/bin/env python3
"""Fix RE-POINT 18 RUE ST ANTOINE - faux-matching make_light num_voie.

Decouvert par enrich_majic Phase 1 + confirme BAN -> BDNB autoritaire
et SKIP_PAIRS du pipeline_bdnb_pivot.py (date 2026-05-20 commit cd74576).

Etat avant :
- 18|RUE|ST ANTOINE light : bgid PFFK-6Z9V-TUP1 (= bgid du 17 ST ANTOINE,
  parc EI0097, bdnb=42, annee=1932)
- _bdnb_match=num_voie (signal classique faux-matching)
- BAN cle_interop 69383_6250_00018 -> bgid BDNB autoritaire
  bdnb-bg-5RMC-KXL7-E97N (bati 4 TERNOIS, parc EI0094, 80 lgts, 1990)
- MAJIC scan EI0094 confirme : 5 adresses dont '18 RUE ST-ANTOINE'
  parmi les 4/6 TERNOIS + 93/93B BELLECOMBE + 18 ST-ANTOINE

OPS :
- RE-POINT 18|RUE|ST ANTOINE : PFFK-6Z9V-TUP1 -> 5RMC-KXL7-E97N
  nb_log_bdnb 42 -> 80, annee 1932 -> 1990
  _fusion_auto=True, _fusion_cible='4/6 RUE TERNOIS / 93 RUE BELLECOMBE / 18 RUE ST ANTOINE'
  _bdnb_match='correctif_18stantoine_re_point'
- Extension label 4 TERNOIS ancre :
  '4/6 RUE TERNOIS' -> '4/6 RUE TERNOIS / 93 RUE BELLECOMBE / 18 RUE ST ANTOINE'
  + sources += ['18|RUE|ST ANTOINE']
  (93 BELLECOMBE absent du secteur DL light : reste dans le label
   texte uniquement, pas dans sources)

Effets :
- adresses 1241 -> 1241 (0)
- hr-actifs UI 21 -> 20 (-1, 18 ST ANTOINE sort en FA)
- parc DL UI strictement neutre (KXL7 garde bdnb 80, PFFK garde bdnb 42
  via 17 ST ANTOINE qui reste)
- 0 copro RNC affectee (aucune sur EI0097 ni EI0094)

Pattern : ECLATEMENT faux-matching make_light (3e instance DL, apres
FELIX FAURE 150-162 et DAUPHINE 4/6/8/13).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre18stantoine.bak"

NEW_BGID = "bdnb-bg-5RMC-KXL7-E97N"
LABEL = "4/6 RUE TERNOIS / 93 RUE BELLECOMBE / 18 RUE ST ANTOINE"


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
    if md.get("_correctif_18_st_antoine"):
        sys.exit("  [abort] _correctif_18_st_antoine deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a18 = by_cle.get("18|RUE|ST ANTOINE")
    a4t = by_cle.get("4|RUE|TERNOIS")
    if not a18:
        sys.exit("  [abort] 18|RUE|ST ANTOINE absent.")
    if not a4t:
        sys.exit("  [abort] 4|RUE|TERNOIS absent.")

    old_bgid = a18.get("batiment_groupe_id")
    a18["batiment_groupe_id"] = NEW_BGID
    a18["nb_log_bdnb"] = 80
    a18["annee_construction"] = 1990
    a18["_bdnb_match"] = "correctif_18stantoine_re_point"
    a18["_fusion_auto"] = True
    a18["_fusion_cible"] = LABEL
    print(f"  [RE-POINT] 18|RUE|ST ANTOINE  {old_bgid[-9:]} -> {NEW_BGID[-9:]}")
    print(f"             nb_log_bdnb 42 -> 80  annee 1932 -> 1990")
    print(f"             _fusion_auto=True  _fusion_cible='{LABEL}'")

    # Extension label 4 TERNOIS
    a4t["_fusion_auto_label"] = LABEL
    srcs = list(a4t.get("_fusion_auto_sources") or [])
    if "18|RUE|ST ANTOINE" not in srcs:
        srcs.append("18|RUE|ST ANTOINE")
    a4t["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]    4|RUE|TERNOIS  label='{LABEL}'")
    print(f"             sources={srcs}")

    md["_correctif_18_st_antoine"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "ECLATEMENT faux-matching make_light num_voie",
        "autorite": "BAN cle_interop 69383_6250_00018 -> BDNB bgid 5RMC-KXL7-E97N + "
                    "MAJIC scan EI0094 confirme 5 adresses (4/6 TERNOIS, 93/93B "
                    "BELLECOMBE, 18 ST-ANTOINE)",
        "ops": "RE-POINT 18|RUE|ST ANTOINE PFFK-6Z9V-TUP1 -> KXL7-E97N + "
               "extension label 4 TERNOIS",
        "old_bgid": old_bgid,
        "new_bgid": NEW_BGID,
        "label": LABEL,
        "delta_parc_ui": 0,
        "source_decouverte": "enrich_majic.py Phase 1 + SKIP_PAIRS pipeline_bdnb_pivot (2026-05-20)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 RE-POINT + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
