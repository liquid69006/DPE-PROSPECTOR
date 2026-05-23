#!/usr/bin/env python3
"""Fix 10 RUE ST VICTORIEN -> RE-POINT vers bati 59 RUE BARABAN
(Dauphine-Lacassagne). Pattern ECLATEMENT faux-matching make_light
num_voie (5e instance DL apres FELIX FAURE 150-162, DAUPHINE 4/6/8/13,
18 ST ANTOINE, 7 FLANDIN).

Configuration confirmee :
- BAN cle_interop 69383_6580_00010 -> BDNB autoritaire bgid
  4P36-PURP (= MEME bati que 59 BARABAN, parcelle DZ0002)
- Light avait erronement attribue bgid 3PC2-EVUG (= bati 7 ST VICTORIEN
  TELEPERFORMANCE Tertiaire, parcelle DY0039)
- BDNB pivot 4P36-PURP l_libelle_adr = ['59 Rue Baraban',
  '10 rue saint victorien'] = preuve directe meme bati
- MAJIC parcelle DZ0002 : 72 lots PM dont 30 sur 10 ST VIC + 25 sur
  59 BAR + 17 sur 57 BAR ; dominance CDC HABITAT (30), ALLIADE HABITAT
  (21), FONCIERE DU TOREY (17) = bailleurs institutionnels residentiels
- Aucune copro RNC sur parcelle DZ0002 couvrant 4P36-PURP

7 ST VICTORIEN reste sur bgid 3PC2-EVUG (vrai bati TELEPERFORMANCE
Tertiaire isole, parcelle DY0039 - intouche).

OPS :
- RE-POINT 10|RUE|ST VICTORIEN : 3PC2-EVUG -> 4P36-PURP
  _fusion_auto=True, _fusion_cible='59 RUE BARABAN / 10 RUE ST VICTORIEN'
- Creation label 59 BARABAN ancre :
  '59 RUE BARABAN / 10 RUE ST VICTORIEN' + sources=[10 ST VICTORIEN]

Effets : adresses 1241->1241 (0) ; hr-actifs UI 14->14 (10 ST VIC etait
bdnb=None donc deja non hr-actif) ; parc DL UI strictement neutre
(les 2 bgids Tertiaire ne contribuent pas au parc residentiel).

Note : l'usage BDNB 'Tertiaire' sur 4P36-PURP semble erronne vu la
dominance CDC HABITAT/ALLIADE HABITAT cote MAJIC (bailleurs sociaux).
A qualifier KV 'social' plus tard (hors scope de ce fix).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre59baraban.bak"

LABEL = "59 RUE BARABAN / 10 RUE ST VICTORIEN"
NEW_BGID = "bdnb-bg-W624-4P36-PURP"


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
    if md.get("_correctif_59_baraban_10_victorien"):
        sys.exit("  [abort] _correctif_59_baraban_10_victorien deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a59 = by_cle.get("59|RUE|BARABAN")
    a10 = by_cle.get("10|RUE|ST VICTORIEN")
    if not a59:
        sys.exit("  [abort] 59|RUE|BARABAN absent.")
    if not a10:
        sys.exit("  [abort] 10|RUE|ST VICTORIEN absent.")
    if a59["batiment_groupe_id"] != NEW_BGID:
        print(f"  [warn] 59 BARABAN bgid={a59['batiment_groupe_id']} != {NEW_BGID} (continue)")

    # RE-POINT 10 ST VICTORIEN
    old = a10["batiment_groupe_id"]
    a10["batiment_groupe_id"] = NEW_BGID
    a10["_bdnb_match"] = "correctif_10stvictorien_re_point"
    a10["_fusion_auto"] = True
    a10["_fusion_cible"] = LABEL
    print(f"  [RE-POINT] 10 ST VICTORIEN  {old[-9:]} -> {NEW_BGID[-9:]}")
    print(f"             +FA cible='{LABEL}'")

    # Label 59 BARABAN ancre
    a59["_fusion_auto_label"] = LABEL
    srcs = list(a59.get("_fusion_auto_sources") or [])
    if "10|RUE|ST VICTORIEN" not in srcs:
        srcs.append("10|RUE|ST VICTORIEN")
    a59["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]    59 BARABAN  label='{LABEL}'  sources={srcs}")

    md["_correctif_59_baraban_10_victorien"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "ECLATEMENT faux-matching make_light num_voie (5e DL)",
        "autorite": "BAN cle_interop 69383_6580_00010 -> bgid 4P36-PURP "
                    "+ BDNB pivot l_libelle_adr ['59 Baraban', '10 St Victorien']",
        "ops": "RE-POINT 10 ST VIC 3PC2-EVUG -> 4P36-PURP + creation label 59 BAR",
        "old_bgid_10_st_vic": old,
        "new_bgid": NEW_BGID,
        "label": LABEL,
        "delta_parc_ui": 0,
        "note": "Usage BDNB 'Tertiaire' suspect (CDC HABITAT/ALLIADE HABITAT "
                "dominent MAJIC = residentiel social) - qualif KV 'social' "
                "envisageable terrain.",
        "intouche": "7 ST VICTORIEN reste sur bgid 3PC2-EVUG (vrai bati "
                    "TELEPERFORMANCE Tertiaire isole, parcelle DY0039)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] 1 RE-POINT + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
