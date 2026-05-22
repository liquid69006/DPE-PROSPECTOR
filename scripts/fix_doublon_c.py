#!/usr/bin/env python3
"""Fix doublon C - eclatement faux-matching make_light num_voie sur
pair/impair 148-162 AVENUE FELIX FAURE (Dauphine-Lacassagne).

Pattern ECLATEMENT de faux-matching make_light num_voie : un meme bgid
"absorbe" par defaut plusieurs numeros voisins, alors que l'autorite BAN
->BDNB rel_batiment_groupe_adresse revele 3 batis distincts au lieu d'un :
  - DBFL-VSF4 (463 lgts, 1972) = 148 SEUL (mega-tour)
  - 59S6-3RB7  (51 lgts, 1995) = 150/152/154/156/158/160/162 (pair)
  - EBHY-Y74D  (67 lgts, 1992) = 149/151/155 (impair angle 26 LAC neuf)

11 operations :
  - 6 RE-POINT pair    -> 59S6 (150,152,154,156,158,160)
  - 1 RE-POINT impair  -> EBHY (151, ex-DBFL faux)
  - 1 INJECT 149 FF label-only (absente light, presente BAN)
  - 3 chaines fusion restructurees (148, 162, 155, 156)

INTOUCHE :
  - 26 LACASSAGNE : programme 2022 fused 24/26 via copro RNC immat
    6YKR-D8DU (autorite legitime, _bdnb_match=immat).

Pre-conditions : aucune copro RNC sur 149/151/155/156/158/160/162 FF
(verifie par diag_doublon_c.py). Aucun correctif anterieur sur FELIX
FAURE/EBHY/156 dans metadata.

Sortie : light.json modifie + .predoublonc.bak. Parc DL strict logement
30637 -> 30624 (delta -13 : EZPF-8JC4 sort du perimetre, son unique
adresse light 160 FF etait faussement matchee).
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.predoublonc.bak"

# Bgids autoritaires (verifies via BAN -> BDNB rel_batiment_groupe_adresse)
EBHY  = "bdnb-bg-V431-EBHY-Y74D"
S59S6 = "bdnb-bg-AVBW-59S6-3RB7"
DBFL  = "bdnb-bg-AX5E-DBFL-VSF4"

LABEL_PAIR_59S6 = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"
LABEL_IMP_EBHY  = "149/151/155 AVENUE FELIX FAURE"

SOURCES_PAIR = [
    "150|AVENUE|FELIX FAURE","152|AVENUE|FELIX FAURE",
    "154|AVENUE|FELIX FAURE","156|AVENUE|FELIX FAURE",
    "158|AVENUE|FELIX FAURE","160|AVENUE|FELIX FAURE",
]
SOURCES_IMP = ["149|AVENUE|FELIX FAURE","151|AVENUE|FELIX FAURE"]

RE_TO_59S6 = ["150|AVENUE|FELIX FAURE","152|AVENUE|FELIX FAURE",
              "154|AVENUE|FELIX FAURE","156|AVENUE|FELIX FAURE",
              "158|AVENUE|FELIX FAURE","160|AVENUE|FELIX FAURE"]


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

    # Garde-fou : verifier aucun _correctif_doublon_c anterieur
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_doublon_c"):
        sys.exit("  [abort] _correctif_doublon_c deja present dans metadata.")

    nb_ops = 0

    # 1. RE-POINT 6 adresses pair -> 59S6
    for cle in RE_TO_59S6:
        a = by_cle.get(cle)
        if not a:
            print(f"  [skip] {cle} absent du light")
            continue
        old = a.get("batiment_groupe_id")
        a["batiment_groupe_id"] = S59S6
        a["nb_log_bdnb"] = 51
        a["annee_construction"] = 1995
        a["_bdnb_match"] = "correctif_doublon_c_re_point"
        print(f"  [RE-POINT] {cle}  {old[-9:]} -> {S59S6[-9:]}")
        nb_ops += 1

    # 2. RE-POINT 151 -> EBHY
    a151 = by_cle["151|AVENUE|FELIX FAURE"]
    old = a151.get("batiment_groupe_id")
    a151["batiment_groupe_id"] = EBHY
    a151["nb_log_bdnb"] = 67
    a151["annee_construction"] = 1992
    a151["_bdnb_match"] = "correctif_doublon_c_re_point"
    print(f"  [RE-POINT] 151|AVENUE|FELIX FAURE  {old[-9:]} -> {EBHY[-9:]}")
    nb_ops += 1

    # 3. INJECT 149 FF label-only (clone de 155 EBHY)
    a155 = by_cle["155|AVENUE|FELIX FAURE"]
    a149 = {
        "cle": "149|AVENUE|FELIX FAURE",
        "adresse": "149 AVENUE FELIX FAURE",
        "longitude": a155.get("longitude"),
        "latitude": a155.get("latitude"),
        "code_iris": a155.get("code_iris"),
        "_coord_source": "clone_doublon_c",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": None,
        "_syndic_src": None,
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "nb_log_bdnb": 67,
        "annee_construction": 1992,
        "classe_dpe": a155.get("classe_dpe"),
        "type_batiment": "immeuble",
        "type_chauffage": a155.get("type_chauffage"),
        "batiment_groupe_id": EBHY,
        "_bdnb_match": "correctif_doublon_c_inject",
        "_fusion_auto": True,
        "_fusion_cible": LABEL_IMP_EBHY,
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Fige",
        "_taux_logement_src": "copie_sans_dependance",
        "usage_principal_bdnb": "Residentiel collectif",
        "_usage_bdnb_src": "correctif_doublon_c",
    }
    ad.append(a149)
    print(f"  [INJECT] 149|AVENUE|FELIX FAURE -> {EBHY[-9:]} (label-only)")
    nb_ops += 1

    # 4. Restructuration chaines fusion
    #    148 : retire label '148/150/152/154' (devient mono-num)
    a148 = by_cle["148|AVENUE|FELIX FAURE"]
    a148.pop("_fusion_auto_label", None)
    a148.pop("_fusion_auto_sources", None)
    print("  [LABEL]  148|AVENUE|FELIX FAURE  label retire (mono-num desormais)")

    #    162 : nouvelle ancre 59S6
    a162 = by_cle["162|AVENUE|FELIX FAURE"]
    a162["_fusion_auto_label"] = LABEL_PAIR_59S6
    a162["_fusion_auto_sources"] = SOURCES_PAIR
    print(f"  [ANCRE]  162|AVENUE|FELIX FAURE  label='{LABEL_PAIR_59S6}'")

    #    155 : nouvelle ancre EBHY
    a155b = by_cle["155|AVENUE|FELIX FAURE"]
    a155b["_fusion_auto_label"] = LABEL_IMP_EBHY
    a155b["_fusion_auto_sources"] = SOURCES_IMP
    print(f"  [ANCRE]  155|AVENUE|FELIX FAURE  label='{LABEL_IMP_EBHY}'")

    #    156 : ex-ancre -> FA fused 162
    a156 = by_cle["156|AVENUE|FELIX FAURE"]
    a156.pop("_fusion_auto_label", None)
    a156.pop("_fusion_auto_sources", None)
    a156["_fusion_auto"] = True
    a156["_fusion_cible"] = LABEL_PAIR_59S6

    #    150/152/154 : FA cible 162 (ex-cible 148)
    for cle in ["150|AVENUE|FELIX FAURE","152|AVENUE|FELIX FAURE","154|AVENUE|FELIX FAURE"]:
        a = by_cle[cle]
        a["_fusion_auto"] = True
        a["_fusion_cible"] = LABEL_PAIR_59S6

    #    158 : FA cible 162 (ex-cible 156)
    a158 = by_cle["158|AVENUE|FELIX FAURE"]
    a158["_fusion_auto"] = True
    a158["_fusion_cible"] = LABEL_PAIR_59S6

    #    160 : FA cible 162 (ex-ancre orpheline)
    a160 = by_cle["160|AVENUE|FELIX FAURE"]
    a160["_fusion_auto"] = True
    a160["_fusion_cible"] = LABEL_PAIR_59S6

    #    151 : FA cible 155 EBHY
    a151["_fusion_auto"] = True
    a151["_fusion_cible"] = LABEL_IMP_EBHY

    # Metadata correctif
    md["_correctif_doublon_c"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "FELIX FAURE pair 148-162 + impair 149-155 (DL)",
        "pattern": "ECLATEMENT faux-matching make_light num_voie",
        "autorite": "BAN cle_interop -> BDNB rel_batiment_groupe_adresse",
        "ops_count": nb_ops,
        "bgids": {
            "DBFL": "148 seul (mega 463 lgts 1972)",
            "S59S6": "150/152/154/156/158/160/162 (51 lgts 1995)",
            "EBHY": "149/151/155 (67 lgts 1992)",
            "EZPF_orphelin": "sort du perimetre (160 etait faux-match)",
        },
        "intouche": "26 LACASSAGNE (programme 2022 fused 24/26 via "
                    "copro RNC immat 6YKR-D8DU = autorite legitime)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] {nb_ops} operations principales appliquees + 4 chaines reorganisees.")
    print(f"  [OK] light ecrit : {LIGHT.name} ({len(ad)} adresses)")


if __name__ == "__main__":
    main()
