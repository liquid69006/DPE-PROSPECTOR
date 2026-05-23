#!/usr/bin/env python3
"""Fix 57/59 BARABAN - phases A+B (81/93 INTOUCHES).

Correction d'une attribution erronee historique : la copro
AH9240847 LES JARDINS MAA (programme neuf 2022, parcelle DZ0002,
bati 4P36-PURP, 126 lots / 61 hab) etait mal attribuee a la cle
'57|RUE|BARABAN' avec bgid EJ2E-JZXH (= bati ancien 93 BARABAN
1952, parcelle DT0073). Cause : adresse_reference RNC declarative
'57 r baraban' (numero postal inexistant en BAN) + faux-matching
make_light par num_voie sur le bati ancien.

Verification distance (coord copro AH9240847 = 45.761271, 4.869007) :
  10 ST VICTORIEN : 13 m (bati neuf 4P36)
  59 BARABAN      : 60 m (bati neuf 4P36)
  57 BARABAN light: 291 m (bati ancien EJ2E - faux match)
  93 BARABAN light: 277 m (bati ancien EJ2E)

Terrain confirme : 81 et 93 BARABAN sont des copros distinctes sans
lien avec AH9240847. AC7467194 SDC SDC 93 BARABAN (21/17 hab, 1952)
reste sur cle 93.

OPS :
- Phase A : copro AH9240847 cle 57 -> 59 + propag immat/61 hab/LAMY
  + taux/classement + extension label 59 vers '57/59 BARABAN / 10 ST VIC'
- Phase B : 57 BARABAN re-point bgid EJ2E -> 4P36 + retire immat +
  propagations + label + devient FA cible chaine 59.

INTOUCHES : 81 BARABAN, 93 BARABAN, 10 ST VICTORIEN.

Effets :
- adresses 1241 -> 1241 (0)
- hr-actifs UI 14 -> 14 (0)
- parc DL UI strictement neutre :
  * bgRnc[EJ2E] : {57: 61, 93: 17} = 78 -> {93: 17} = 17 (retire 57:61)
  * bgRnc[4P36] : {} = 0 -> {59: 61} = 61 (ajoute 59:61)
  * Total inchange (78 = 17 + 61)
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre57baraban_AB.bak"

LABEL_NEUF = "57/59 RUE BARABAN / 10 RUE ST VICTORIEN"
NEW_BGID_NEUF = "bdnb-bg-W624-4P36-PURP"


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
    if md.get("_correctif_57_baraban_AB"):
        sys.exit("  [abort] _correctif_57_baraban_AB deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    co_by_immat = {c.get("numero_immatriculation"): c
                   for c in co if c.get("numero_immatriculation")}

    a57 = by_cle.get("57|RUE|BARABAN")
    a59 = by_cle.get("59|RUE|BARABAN")
    c_maa = co_by_immat.get("AH9240847")
    if not a57 or not a59:
        sys.exit("  [abort] 57 ou 59 BARABAN absent.")
    if not c_maa:
        sys.exit("  [abort] copro AH9240847 absente.")
    if c_maa.get("cle_adresse") != "57|RUE|BARABAN":
        print(f"  [warn] copro cle={c_maa.get('cle_adresse')} != 57|RUE|BARABAN (continue)")

    # ============== PHASE A ==============
    print()
    print("PHASE A - Re-attribuer AH9240847 (cle 57 -> 59)")
    c_maa["cle_adresse"] = "59|RUE|BARABAN"
    print(f"  copro AH9240847 cle_adresse : 57|RUE|BARABAN -> 59|RUE|BARABAN")

    CHAMPS = ["numero_immatriculation","nb_lots_habitation","syndic","_syndic_src"]
    for f in CHAMPS:
        src_v = c_maa.get(f)
        if src_v is None: continue
        old = a59.get(f)
        if old != src_v:
            a59[f] = src_v
            print(f"  59 BARABAN  {f}: {old} -> {src_v}")
    if c_maa.get("taux_rotation_5ans") is not None:
        old = a59.get("taux_rotation")
        a59["taux_rotation"] = c_maa["taux_rotation_5ans"]
        print(f"  59 BARABAN  taux_rotation: {old} -> {c_maa['taux_rotation_5ans']}")
    if c_maa.get("classement_rotation"):
        old = a59.get("classement_rotation")
        a59["classement_rotation"] = c_maa["classement_rotation"]
        print(f"  59 BARABAN  classement_rotation: {old} -> {c_maa['classement_rotation']}")
    a59["_bdnb_match"] = "correctif_59_AH9240847_re_attribute"

    old_label_59 = a59.get("_fusion_auto_label")
    a59["_fusion_auto_label"] = LABEL_NEUF
    srcs59 = list(a59.get("_fusion_auto_sources") or [])
    if "57|RUE|BARABAN" not in srcs59:
        srcs59.insert(0, "57|RUE|BARABAN")
    a59["_fusion_auto_sources"] = srcs59
    print(f"  59 BARABAN  label: '{old_label_59}' -> '{LABEL_NEUF}'")
    print(f"  59 BARABAN  sources: {srcs59}")

    # ============== PHASE B ==============
    print()
    print("PHASE B - 57 BARABAN : clean + re-point bgid + FA")
    old_bgid_57 = a57.get("batiment_groupe_id")
    a57["batiment_groupe_id"] = NEW_BGID_NEUF
    print(f"  RE-POINT bgid : {old_bgid_57[-9:]} -> {NEW_BGID_NEUF[-9:]}")

    for f in ("numero_immatriculation","nb_lots_habitation","taux_rotation",
              "classement_rotation","syndic","_syndic_src"):
        if a57.get(f) is not None:
            print(f"  retire {f}: {a57.get(f)} -> None")
            a57[f] = None

    if a57.pop("_fusion_auto_label", None):
        print(f"  retire label '57/81/93 RUE BARABAN'")
    if a57.pop("_fusion_auto_sources", None):
        print(f"  retire sources [93, 81]")

    a57["_fusion_auto"] = True
    a57["_fusion_cible"] = LABEL_NEUF
    a57["_bdnb_match"] = "correctif_57baraban_re_point_FA"
    print(f"  57 BARABAN  _fusion_auto=True  cible='{LABEL_NEUF}'")

    # Metadata
    md["_correctif_57_baraban_AB"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Correction attribution copro RNC adresse_reference erronee "
                   "+ faux-matching make_light num_voie",
        "phases": {
            "A": "AH9240847 LES JARDINS MAA cle 57 -> 59 + propag",
            "B": "57 BARABAN re-point EJ2E -> 4P36 + FA chaine 59",
        },
        "intouches": ["81|RUE|BARABAN", "93|RUE|BARABAN", "10|RUE|ST VICTORIEN"],
        "old_bgid_57": old_bgid_57,
        "new_bgid_57": NEW_BGID_NEUF,
        "label_neuf": LABEL_NEUF,
        "delta_parc_ui": 0,
        "redistribution": {
            "bg_EJ2E_avant": {"57": 61, "93": 17, "total": 78},
            "bg_EJ2E_apres": {"93": 17, "total": 17},
            "bg_4P36_avant": {"total": 0},
            "bg_4P36_apres": {"59": 61, "total": 61},
        },
        "decouverte": "distance copro AH9240847 vs 57 BAR light = 291m "
                      "(prouve faux matching) ; 10 ST VIC = 13m ; "
                      "59 BAR = 60m (vrais batis du programme neuf)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] Phases A+B appliquees. 81/93 intouches.")


if __name__ == "__main__":
    main()
