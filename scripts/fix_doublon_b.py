#!/usr/bin/env python3
"""Fix doublon B - faux-matchings make_light num_voie sur RUE DAUPHINE
(Dauphine-Lacassagne). Pattern ECLATEMENT identique au doublon C.

DECOUVERTE clef : 75JZ-QX89 (103 lgts, 1949) = HBM legitime
7/9/11/13 RUE DAUPHINE (impair). Le pivot l_libelle_adr ne montrait
que les variantes B-suffixes ('7B/9B/11B/13B' BAN principales) ; les
numeros sans-B sont resolus par rel_batiment_groupe_adresse vers le
MEME 75JZ. -> 11 DAUPH correctement sur 75JZ (qualif KV 'social' = HBM).

Faux-matching reel concerne 4 numeros : 4, 6, 8, 13 DAUPHINE.

7 modifs (4 RE-POINT + 3 LABEL) :
  - 4 DAUPH  : 75JZ -> 936T-G73D  (81 lgts 1985, ancre '4/6' conservee)
  - 6 DAUPH  : 75JZ -> 936T-G73D  (FA->4)
  - 8 DAUPH  : L1N7 -> 6G9Q-X4H2  (Tertiaire ; nettoyage _fusion_cible
              '1|RUE|ST MAXIMIN' incoherent)
  - 13 DAUPH : RMZ8 -> 75JZ       (HBM ; ex-ancre '13/15' degradee FA)
  - 10 DAUPH : retire label '8/10' (mono-num)
  - 11 DAUPH : etend label '7/9/11' -> '7/9/11/13 RUE DAUPHINE'
  - 15 DAUPH : retire FA + _fusion_cible (RMZ8 mono-num)

INTOUCHE : 7, 9, 11 DAUPH (deja correct sur 75JZ), 2 ST THEODORE (deja
ancre 936T-G73D), 12 DAUPH (bug RNC '120 DAUPHINE', a investiguer).

Parc DL strict logement : 30624 -> 30624 (strictement neutre).
Tous les bgids cibles deja presents dans le light (via d'autres adresses).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.predoublonb.bak"

S75JZ = "bdnb-bg-L2AS-75JZ-QX89"
S936T = "bdnb-bg-BJ9A-936T-G73D"
S6G9Q = "bdnb-bg-CPR3-6G9Q-X4H2"


def main():
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    by_cle = {a.get("cle") or "": a for a in ad}
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_doublon_b"):
        sys.exit("  [abort] _correctif_doublon_b deja present dans metadata.")

    # 1. RE-POINT 4 -> 936T
    a4 = by_cle["4|RUE|DAUPHINE"]
    old = a4["batiment_groupe_id"]
    a4["batiment_groupe_id"] = S936T
    a4["nb_log_bdnb"] = 81
    a4["annee_construction"] = 1985
    a4["_bdnb_match"] = "correctif_doublon_b_re_point"
    print(f"  [RE-POINT] 4|RUE|DAUPHINE   {old[-9:]} -> {S936T[-9:]}  (103/1949 -> 81/1985)")

    # 2. RE-POINT 6 -> 936T
    a6 = by_cle["6|RUE|DAUPHINE"]
    old = a6["batiment_groupe_id"]
    a6["batiment_groupe_id"] = S936T
    a6["nb_log_bdnb"] = 81
    a6["annee_construction"] = 1985
    a6["_bdnb_match"] = "correctif_doublon_b_re_point"
    print(f"  [RE-POINT] 6|RUE|DAUPHINE   {old[-9:]} -> {S936T[-9:]}  (FA->4)")

    # 3. RE-POINT 8 -> 6G9Q (Tertiaire) + nettoyage incoherence
    a8 = by_cle["8|RUE|DAUPHINE"]
    old = a8["batiment_groupe_id"]
    a8["batiment_groupe_id"] = S6G9Q
    a8["nb_log_bdnb"] = None
    a8["annee_construction"] = None
    a8["_bdnb_match"] = "correctif_doublon_b_re_point"
    a8.pop("_fusion_auto", None)
    a8.pop("_fusion_cible", None)
    a8["usage_principal_bdnb"] = "Tertiaire"
    a8["_usage_bdnb_src"] = "correctif_doublon_b"
    print(f"  [RE-POINT] 8|RUE|DAUPHINE   {old[-9:]} -> {S6G9Q[-9:]}  (Tertiaire ; cible '1 ST MAXIMIN' retiree)")

    # 4. RE-POINT 13 -> 75JZ + degradation ancre
    a13 = by_cle["13|RUE|DAUPHINE"]
    old = a13["batiment_groupe_id"]
    a13["batiment_groupe_id"] = S75JZ
    a13["nb_log_bdnb"] = 103
    a13["annee_construction"] = 1949
    a13["_bdnb_match"] = "correctif_doublon_b_re_point"
    a13.pop("_fusion_auto_label", None)
    a13.pop("_fusion_auto_sources", None)
    a13["_fusion_auto"] = True
    a13["_fusion_cible"] = "7/9/11/13 RUE DAUPHINE"
    print(f"  [RE-POINT] 13|RUE|DAUPHINE  {old[-9:]} -> {S75JZ[-9:]}  (1/1974 -> 103/1949 ; ex-ancre '13/15' -> FA)")

    # 5. 10 DAUPH : retire label '8/10' (8 detache)
    a10 = by_cle["10|RUE|DAUPHINE"]
    a10.pop("_fusion_auto_label", None)
    a10.pop("_fusion_auto_sources", None)
    print("  [LABEL]    10|RUE|DAUPHINE  label '8/10' retire (mono-num)")

    # 6. 11 DAUPH : etend label '7/9/11' -> '7/9/11/13'
    a11 = by_cle["11|RUE|DAUPHINE"]
    a11["_fusion_auto_label"] = "7/9/11/13 RUE DAUPHINE"
    srcs = list(a11.get("_fusion_auto_sources") or [])
    if "13|RUE|DAUPHINE" not in srcs:
        srcs.append("13|RUE|DAUPHINE")
    a11["_fusion_auto_sources"] = srcs
    print("  [LABEL]    11|RUE|DAUPHINE  '7/9/11' -> '7/9/11/13 RUE DAUPHINE' +sources=[13]")

    # 7. 15 DAUPH : retire FA + _fusion_cible
    a15 = by_cle["15|RUE|DAUPHINE"]
    a15.pop("_fusion_auto", None)
    a15.pop("_fusion_cible", None)
    print("  [LABEL]    15|RUE|DAUPHINE  retire FA + _fusion_cible (RMZ8 mono-num)")

    # Metadata correctif
    md["_correctif_doublon_b"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "RUE DAUPHINE pair 4/6/8 + impair 13 (DL)",
        "pattern": "ECLATEMENT faux-matching make_light num_voie",
        "autorite": "BAN cle_interop -> BDNB rel_batiment_groupe_adresse",
        "ops_count": 7,
        "bgids": {
            "75JZ": "HBM 7/9/11/13 (103 lgts 1949 R-coll, KV 11=social)",
            "936T": "pair 4/6 + 2/8 ST-THEODORE (81 lgts 1985)",
            "6G9Q": "8 DAUPH + 3/9 ST-THEODORE (Tertiaire)",
            "L1N7_retire_8": "10 + 1 ST-MAXIMIN (14 lgts 1975)",
            "RMZ8_retire_13": "15 DAUPH SEUL (1 lgt Tertiaire 1974)",
        },
        "lecon": "pivot l_libelle_adr peut afficher uniquement les "
                 "variantes BAN principales (ex 7B/9B/11B/13B pour 75JZ) ; "
                 "autorite reelle multi-adresses = rel_batiment_groupe_adresse "
                 "requete par cle_interop_adr de chaque numero.",
        "intouche": [
            "7, 9, 11 DAUPH (deja sur 75JZ correct)",
            "2 ST THEODORE (deja ancre 936T-G73D)",
            "12 DAUPH (copro RNC AC8890550 nom '120 DAUPHINE' = bug RNC, separe)",
        ],
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] 7 modifs appliquees.")
    print(f"  [OK] light ecrit : {LIGHT.name} ({len(ad)} adresses)")


if __name__ == "__main__":
    main()
