#!/usr/bin/env python3
"""Fix groupe 5 ensembles immobiliers DL confirmes terrain.

[1] 3/5/7 FLANDIN  : ECLATEMENT faux-matching make_light (RE-POINT 7
                     FLANDIN bgid NUCS-XLRZ -> K6JM-Z1H3, autorite BAN)
                     + restructuration chaines 3 et 6 FLANDIN
[2] 13/15 RICHERAND : STATU QUO (deja etiquete '13/15 RICHERAND')
[3] 6/8 ST EUSEBE   : Cambronne RE-FUSE + nettoyage incoherence 8
                     (etait FA->2 ST EUSEBE incoherent ; 8 a sa copro
                     AG4913810 propre)
[4] 12 MOISS / 11 LACASS  : Fondary multi-bgid 1-parc 5e instance DL
                            (parc DR0098 - LA SCALA AB8822587)
[5] 21 ST ANT / 270 LAFAYETTE : Fondary multi-bgid 1-parc 6e instance
                                 (parc EI0098 - JARDIN LAFAYETTE AA8713760)

Effets : parc DL UI strictement neutre (toutes ancres deja
representees) ; hr-actifs UI 17 -> 14 (-3 : 6 ST EUSEBE, 12 MOISS,
21 ST ANT sortent en FA) ; adresses inchangees.
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre5ensembles.bak"


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
    if md.get("_correctif_5_ensembles_terrain"):
        sys.exit("  [abort] _correctif_5_ensembles_terrain deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}

    # === CAS 1 : 3/5/7 FLANDIN ===
    LABEL_1 = "3/5/7 RUE MAURICE FLANDIN"
    a3 = by_cle["3|RUE|MAURICE FLANDIN"]
    a7 = by_cle["7|RUE|MAURICE FLANDIN"]
    a6 = by_cle["6|RUE|MAURICE FLANDIN"]
    NEW_BGID_FL = a3["batiment_groupe_id"]

    print()
    print("[1] 3/5/7 FLANDIN")
    old = a7["batiment_groupe_id"]
    a7["batiment_groupe_id"] = NEW_BGID_FL
    a7["nb_log_bdnb"] = a3.get("nb_log_bdnb")
    a7["annee_construction"] = a3.get("annee_construction")
    a7["_bdnb_match"] = "correctif_7flandin_re_point"
    a7["_fusion_auto"] = True
    a7["_fusion_cible"] = LABEL_1
    print(f"  [RE-POINT] 7 FLANDIN  {old[-9:]} -> {NEW_BGID_FL[-9:]}  +FA cible='{LABEL_1}'")
    srcs3 = list(a3.get("_fusion_auto_sources") or [])
    if "7|RUE|MAURICE FLANDIN" not in srcs3:
        srcs3.append("7|RUE|MAURICE FLANDIN")
    a3["_fusion_auto_label"] = LABEL_1
    a3["_fusion_auto_sources"] = srcs3
    print(f"  [LABEL]    3 FLANDIN ancre  label='{LABEL_1}'  sources={srcs3}")
    srcs6 = list(a6.get("_fusion_auto_sources") or [])
    if "7|RUE|MAURICE FLANDIN" in srcs6:
        srcs6.remove("7|RUE|MAURICE FLANDIN")
    if srcs6:
        a6["_fusion_auto_sources"] = srcs6
    else:
        a6["_fusion_auto_sources"] = None
        a6.pop("_fusion_auto_label", None)
    print(f"  [LABEL]    6 FLANDIN  sources -> {a6.get('_fusion_auto_sources')}")

    # === CAS 2 : STATU QUO ===
    print()
    print("[2] 13/15 RICHERAND  -  STATU QUO")

    # === CAS 3 : 6/8 ST EUSEBE ===
    LABEL_3 = "6/8 RUE ST EUSEBE"
    a6e = by_cle["6|RUE|ST EUSEBE"]
    a8e = by_cle["8|RUE|ST EUSEBE"]
    a2e = by_cle["2|RUE|ST EUSEBE"]

    print()
    print("[3] 6/8 ST EUSEBE")
    a6e["_fusion_auto"] = True
    a6e["_fusion_cible"] = LABEL_3
    a6e["_bdnb_match"] = "correctif_6_8_steusebe_re_fuse"
    print(f"  [RE-FUSE]  6 ST EUSEBE  _fusion_cible='{LABEL_3}'")
    a8e.pop("_fusion_auto", None)
    a8e.pop("_fusion_cible", None)
    a8e["_fusion_auto_label"] = LABEL_3
    a8e["_fusion_auto_sources"] = ["6|RUE|ST EUSEBE"]
    print(f"  [DETACH+ANCRE] 8 ST EUSEBE  : retire FA->2 ; devient ancre label='{LABEL_3}'")
    srcs2 = list(a2e.get("_fusion_auto_sources") or [])
    if "8|RUE|ST EUSEBE" in srcs2:
        srcs2.remove("8|RUE|ST EUSEBE")
    a2e["_fusion_auto_sources"] = srcs2
    old_label_2 = a2e.get("_fusion_auto_label","")
    new_label_2 = old_label_2.replace("2/8 RUE ST EUSEBE","2 RUE ST EUSEBE")
    a2e["_fusion_auto_label"] = new_label_2
    print(f"  [CORRIGE]  2 ST EUSEBE label '{old_label_2}' -> '{new_label_2}', sources={srcs2}")

    # === CAS 4 : 12 MOISS / 11 LACASS ===
    LABEL_4 = "11 AVENUE LACASSAGNE / 12 RUE MOISSONNIER"
    a12 = by_cle["12|RUE|MOISSONNIER"]
    a11 = by_cle["11|AVENUE|LACASSAGNE"]
    print()
    print("[4] 12 MOISS -> 11 LACASS")
    a12["_fusion_auto"] = True
    a12["_fusion_cible"] = LABEL_4
    a12["_bdnb_match"] = "correctif_12moiss_11lacass_re_fuse"
    print(f"  [RE-FUSE]  12 MOISSONNIER  _fusion_cible='{LABEL_4}'")
    srcs11 = list(a11.get("_fusion_auto_sources") or [])
    if "12|RUE|MOISSONNIER" not in srcs11:
        srcs11.append("12|RUE|MOISSONNIER")
    a11["_fusion_auto_label"] = LABEL_4
    a11["_fusion_auto_sources"] = srcs11
    print(f"  [LABEL]    11 LACASSAGNE  label='{LABEL_4}'  sources={srcs11}")

    # === CAS 5 : 21 ST ANT / 270 LAFAYETTE ===
    LABEL_5 = "270 COURS LAFAYETTE / 21 RUE ST ANTOINE"
    a21 = by_cle["21|RUE|ST ANTOINE"]
    a270 = by_cle["270|COURS|LAFAYETTE"]
    print()
    print("[5] 21 ST ANTOINE -> 270 LAFAYETTE")
    a21["_fusion_auto"] = True
    a21["_fusion_cible"] = LABEL_5
    a21["_bdnb_match"] = "correctif_21stant_270laf_re_fuse"
    print(f"  [RE-FUSE]  21 ST ANTOINE  _fusion_cible='{LABEL_5}'")
    srcs270 = list(a270.get("_fusion_auto_sources") or [])
    if "21|RUE|ST ANTOINE" not in srcs270:
        srcs270.append("21|RUE|ST ANTOINE")
    a270["_fusion_auto_label"] = LABEL_5
    a270["_fusion_auto_sources"] = srcs270
    print(f"  [LABEL]    270 LAFAYETTE  label='{LABEL_5}'  sources={srcs270}")

    # Metadata
    md["_correctif_5_ensembles_terrain"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ensembles": {
            "1_3_5_7_flandin": "ECLATEMENT faux-matching make_light "
                               "(7 FLANDIN re-pointe vers bati 3/5)",
            "2_13_15_richerand": "STATU QUO (deja etiquete)",
            "3_6_8_st_eusebe": "Cambronne RE-FUSE 6->8 (AG4913810) + "
                               "detach 8 de chaine 2 ST EUSEBE",
            "4_12_moiss_11_lacass": "Fondary 5e (DR0098 - AB8822587 LA SCALA)",
            "5_21_st_ant_270_laf": "Fondary 6e (EI0098 - AA8713760 JARDIN LAFAYETTE)",
        },
        "delta_parc_ui": 0,
        "delta_hr_actifs": -3,
        "patterns": "ECLATEMENT + Cambronne + 2 Fondary multi-bgid 1-parc",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] 4 fix + 1 statu quo appliques.")


if __name__ == "__main__":
    main()
