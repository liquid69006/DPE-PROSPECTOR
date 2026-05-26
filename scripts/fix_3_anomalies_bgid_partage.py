#!/usr/bin/env python3
"""Fix 3 anomalies bgid partage suspect (DL) - 0 vente sur cle + bgid voisin
qui vend, signature classique de faux-matching make_light.

Anomalies traitees en une passe (backup .pre3anomalies.bak) :

  #4  13|RUE|ST VICTORIEN  (60 log, bgid 9SJM-2V31-SHKZ)
      -> RE-FUSE vers 14|RUE|ST VICTORIEN (AC3805199 LES VICTORINES, 188/60).
      Terrain : 13 = entree parking, pas de bati residentiel.
      BDNB pivot 2V31-SHKZ : nb_adresses_BAN=2 = 14 ST VIC + 2 LOUIS JASSERON
      uniquement (BAN ne connait pas 13). Label fantome existant
      '13/15 RUE ST VICTORIEN' (sources=['15|RUE|ST VICTORIEN']) - 15 aussi
      fantome - on remplace par RE-FUSE propre.

  #15 11|RUE|BARA  (36 log, bgid ED7P-8YCZ-L6UX = bgid 12 BARA)
      -> RE-POINT bgid 8YCZ-L6UX -> V87R-V5K9-57SP.
      BAN autoritaire : 11 BARA -> bgid V87R-V5K9-57SP (vraie petite maison
      30 log, 1926, copro_non_immat, 3 BAN = 68 LACASSAGNE / 2 REBATEL /
      11 BARA, parcelle BK/0016). make_light l'a faussement snappe sur le
      bgid 8YCZ de 12 BARA (AA7362809 LE JARDIN BARA, 36 log, 1976).
      NB : 68 LACASSAGNE et 2 REBATEL existent dans light mais sur d'autres
      bgids voisins (TAU6-UC13 fused->66 LACASSAGNE ; Q47U-658U fused->14
      BARA). Le bati V87R-V5K9-57SP reste donc sous-expose - on ne touche
      pas a 68 LACASSAGNE ni a 2 REBATEL (consigne user, eviter risque
      double-comptage).

  #19 2|RUE|RIBOUD  (31 log, bgid YAR9-LWKG-N28H)
      -> RE-FUSE vers 2B|RUE|RIBOUD (AB0217901 '2 BIS RUE RIBOUD', 69/30,
      syndic LYMMOBILIER).
      Bati YAR9-LWKG-N28H : nb_adresses_BAN=2 = 2B RIBOUD + 26 M.FLANDIN
      (BAN ne connait pas 2 RIBOUD sans bis). 2 RIBOUD est artefact
      make_light proximity-snap. Meme bgid, meme immat, meme syndic.

OPS :
  1. RE-FUSE 13|RUE|ST VICTORIEN :
     - _fusion_auto=True, _fusion_cible=LABEL_ST_VIC
     - _bdnb_match='correctif_3anomalies_re_fuse'
     - retrait du _fusion_auto_label fantome existant ('13/15 ...')
     - retrait du _fusion_auto_sources fantome existant ([15|...])
  2. Extension label 14|RUE|ST VICTORIEN :
     - _fusion_auto_label = LABEL_ST_VIC
     - _fusion_auto_sources += ['13|RUE|ST VICTORIEN']
  3. RE-POINT 11|RUE|BARA :
     - batiment_groupe_id : bdnb-bg-ED7P-8YCZ-L6UX -> bdnb-bg-V87R-V5K9-57SP
     - nb_log_bdnb : 36 -> 30
     - annee_construction : 1976 -> 1926
     - _bdnb_match='correctif_3anomalies_re_point'
     - NO FA (bati orphelin cote ce secteur, 11 BARA reste hr-actif isole)
  4. RE-FUSE 2|RUE|RIBOUD :
     - _fusion_auto=True, _fusion_cible=LABEL_RIBOUD
     - _bdnb_match='correctif_3anomalies_re_fuse'
  5. Extension label 2B|RUE|RIBOUD :
     - _fusion_auto_label = LABEL_RIBOUD
     - _fusion_auto_sources = ['2|RUE|RIBOUD']

EFFETS attendus :
  - hr-actifs UI : -2 (13 ST VIC + 2 RIBOUD sortent en FA ; 11 BARA reste
    isole hr-actif sur nouveau bgid)
  - parc DL UI : 11 BARA passe 36 -> 30 (-6, BDNB autoritaire vrai bati) ;
    13 ST VIC RE-FUSE = parc neutre (bgid 2V31-SHKZ deja comptabilise via
    14 ancre) ; 2 RIBOUD RE-FUSE = parc neutre (bgid YAR9 deja via 2B).
    Net : -6 attendu (mais a confirmer par algo UI exact bgRncLots).
  - Aucune copro RNC affectee, aucune cle injectee, aucune cle supprimee.
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre3anomalies.bak"

NEW_BGID_11BARA = "bdnb-bg-V87R-V5K9-57SP"
LABEL_ST_VIC = "14 RUE ST VICTORIEN / 2 RUE LOUIS JASSERON / 13 RUE ST VICTORIEN"
LABEL_RIBOUD = "2B RUE RIBOUD / 2 RUE RIBOUD"


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
    if md.get("_correctif_3_anomalies_bgid"):
        sys.exit("  [abort] _correctif_3_anomalies_bgid deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}

    # --- requis ---
    a13 = by_cle.get("13|RUE|ST VICTORIEN")
    a14 = by_cle.get("14|RUE|ST VICTORIEN")
    a11 = by_cle.get("11|RUE|BARA")
    a2r = by_cle.get("2|RUE|RIBOUD")
    a2br = by_cle.get("2B|RUE|RIBOUD")
    for cle, a in (("13|RUE|ST VICTORIEN", a13),
                   ("14|RUE|ST VICTORIEN", a14),
                   ("11|RUE|BARA", a11),
                   ("2|RUE|RIBOUD", a2r),
                   ("2B|RUE|RIBOUD", a2br)):
        if not a:
            sys.exit(f"  [abort] {cle} absent du light.")

    # --- [1] RE-FUSE 13 ST VICTORIEN -> 14 ST VICTORIEN ---
    print()
    print("  [1] RE-FUSE 13|RUE|ST VICTORIEN -> 14|RUE|ST VICTORIEN")
    old_label = a13.get("_fusion_auto_label")
    old_sources = a13.get("_fusion_auto_sources")
    a13["_fusion_auto"] = True
    a13["_fusion_cible"] = LABEL_ST_VIC
    a13["_bdnb_match"] = "correctif_3anomalies_re_fuse"
    # retrait des champs label/sources fantomes (deplaces vers ancre 14)
    a13.pop("_fusion_auto_label", None)
    a13.pop("_fusion_auto_sources", None)
    print(f"      _fusion_auto=True  _fusion_cible='{LABEL_ST_VIC}'")
    print(f"      _bdnb_match=correctif_3anomalies_re_fuse")
    print(f"      retire label fantome '{old_label}'  sources={old_sources}")

    # --- [2] Extension label 14 ST VICTORIEN ---
    print()
    print("  [2] LABEL 14|RUE|ST VICTORIEN")
    a14["_fusion_auto_label"] = LABEL_ST_VIC
    srcs = list(a14.get("_fusion_auto_sources") or [])
    if "13|RUE|ST VICTORIEN" not in srcs:
        srcs.append("13|RUE|ST VICTORIEN")
    a14["_fusion_auto_sources"] = srcs
    print(f"      _fusion_auto_label='{LABEL_ST_VIC}'")
    print(f"      _fusion_auto_sources={srcs}")

    # --- [3] RE-POINT 11 BARA bgid ---
    print()
    print("  [3] RE-POINT 11|RUE|BARA bgid")
    old_bgid = a11.get("batiment_groupe_id")
    a11["batiment_groupe_id"] = NEW_BGID_11BARA
    a11["nb_log_bdnb"] = 30
    a11["annee_construction"] = 1926
    a11["_bdnb_match"] = "correctif_3anomalies_re_point"
    print(f"      bgid {old_bgid[-9:]} -> {NEW_BGID_11BARA[-9:]}")
    print(f"      nb_log_bdnb 36 -> 30  annee 1976 -> 1926")
    print(f"      _bdnb_match=correctif_3anomalies_re_point")
    print(f"      (68 LACASSAGNE / 2 REBATEL intacts, consigne user)")

    # --- [4] RE-FUSE 2 RIBOUD -> 2B RIBOUD ---
    print()
    print("  [4] RE-FUSE 2|RUE|RIBOUD -> 2B|RUE|RIBOUD")
    a2r["_fusion_auto"] = True
    a2r["_fusion_cible"] = LABEL_RIBOUD
    a2r["_bdnb_match"] = "correctif_3anomalies_re_fuse"
    print(f"      _fusion_auto=True  _fusion_cible='{LABEL_RIBOUD}'")
    print(f"      _bdnb_match=correctif_3anomalies_re_fuse")

    # --- [5] Extension label 2B RIBOUD ---
    print()
    print("  [5] LABEL 2B|RUE|RIBOUD")
    a2br["_fusion_auto_label"] = LABEL_RIBOUD
    srcs2 = list(a2br.get("_fusion_auto_sources") or [])
    if "2|RUE|RIBOUD" not in srcs2:
        srcs2.append("2|RUE|RIBOUD")
    a2br["_fusion_auto_sources"] = srcs2
    print(f"      _fusion_auto_label='{LABEL_RIBOUD}'")
    print(f"      _fusion_auto_sources={srcs2}")

    # --- metadata ---
    md["_correctif_3_anomalies_bgid"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "ECLATEMENT bgid partage suspect (3 cas) - faux-matching make_light",
        "autorite": ("BDNB pivot batiment_groupe_complet.l_libelle_adr + "
                     "BAN cle_interop autoritaire + diag_3_anomalies_bgid_partage.py"),
        "ops": [
            "RE-FUSE 13|RUE|ST VICTORIEN -> 14|RUE|ST VICTORIEN (LABEL_ST_VIC)",
            "RE-POINT 11|RUE|BARA bgid 8YCZ-L6UX -> V87R-V5K9-57SP (36->30 lgts, 1976->1926)",
            "RE-FUSE 2|RUE|RIBOUD -> 2B|RUE|RIBOUD (LABEL_RIBOUD)",
        ],
        "details": {
            "13_st_victorien": {
                "raison": "entree parking, pas de bati residentiel ; "
                          "bgid 2V31-SHKZ nb_adresses_BAN=2 (14 + 2 LJ uniquement)",
                "ancre": "14|RUE|ST VICTORIEN AC3805199 'LES VICTORINES' 188/60",
                "label_fantome_retire": old_label,
            },
            "11_bara": {
                "raison": "BAN autoritaire : 11 BARA -> V87R-V5K9-57SP "
                          "(vrai bati 30 log 1926, copro_non_immat) ; "
                          "make_light l'avait snappe sur 8YCZ-L6UX (12 BARA, 36 log 1976)",
                "vrai_bati": "68 LACASSAGNE / 2 REBATEL / 11 BARA, parcelle BK/0016, 30 log 1926",
                "intouches": ["68|AVENUE|LACASSAGNE", "2|RUE|DOCTEUR REBATEL"],
            },
            "2_riboud": {
                "raison": "bgid YAR9 nb_adresses_BAN=2 (2B + 26 M.FLANDIN uniquement) ; "
                          "2 sans bis n'existe pas en BAN",
                "ancre": "2B|RUE|RIBOUD AB0217901 '2 BIS RUE RIBOUD' 69/30 LYMMOBILIER",
            },
        },
        "delta_parc_ui_attendu": "-6 (11 BARA 36->30) ; 13 ST VIC + 2 RIBOUD parc-neutres",
        "delta_hr_actifs_ui_attendu": "-2 (13 ST VIC + 2 RIBOUD sortent en FA)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 2 RE-FUSE + 1 RE-POINT + 2 extensions label appliques.")


if __name__ == "__main__":
    main()
