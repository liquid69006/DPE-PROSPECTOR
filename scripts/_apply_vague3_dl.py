#!/usr/bin/env python3
"""Apply Vague 3 DL : 10 mega-ensembles E19-E28 + 8 REBIND univoques
(dry-run + --apply). Inclut REBIND-COPRO pattern pour 2 cles malformees
(BRICKS 2 + SDC LE SISLEY) similaire a E13 SAINT MARC I.
"""
import json, sys, shutil, argparse, unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
FULL  = ROOT / "data" / "secteur_dauphine_lacassagne.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.prev3.bak"


def to_int(x):
    try: return int(x)
    except: return 0


# (id, tag, label, ancre_cle, immat, re_fuses, extra_sources, injects, kv_delete)
# Pour REBIND univoques : 1 re_fuse seul + label minimal
FIXES_STANDARD = [
    {"id":"E19","tag":"jardin_clair",
     "label":"24-26-28 RUE METALLURGIE / 12 RUE CARRY",
     "ancre":"24|RUE|METALLURGIE","immat":"AB3965985",
     "re_fuses":[
        {"cle":"12|RUE|CARRY","bgid_change":True,"old_cible":"6|RUE|CARRY"},
        {"cle":"26|RUE|METALLURGIE","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[],
     "injects":[{"cle":"28|RUE|METALLURGIE","clone_from":"24|RUE|METALLURGIE",
                 "fcible":"24|RUE|METALLURGIE"}],
     "kv_delete":["26|RUE|METALLURGIE"]},
    {"id":"E20","tag":"saint_germain",
     "label":"23 RUE TURBIL / 258-260-262 RUE PAUL BERT",
     "ancre":"23|RUE|TURBIL","immat":"AB2926236",
     "re_fuses":[
        {"cle":"260|RUE|PAUL BERT","bgid_change":True,"old_cible":"264B|RUE|PAUL BERT"},
        {"cle":"262|RUE|PAUL BERT","bgid_change":True,"old_cible":"264B|RUE|PAUL BERT"},
     ],
     "extra_sources":[],
     "injects":[{"cle":"258|RUE|PAUL BERT","clone_from":"23|RUE|TURBIL",
                 "fcible":"23|RUE|TURBIL"}],
     "kv_delete":[]},
    {"id":"E21","tag":"clos_saint_marc",
     "label":"38-40 RUE ST MAXIMIN",
     "ancre":"38|RUE|ST MAXIMIN","immat":"AA9435975",
     "re_fuses":[
        {"cle":"40|RUE|ST MAXIMIN","bgid_change":True,"old_cible":"39|RUE|ST MAXIMIN"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
    {"id":"E22","tag":"terrasses_villas_st_max",
     "label":"1 RUE ROSSAN / 10-12 RUE ST MAXIMIN",
     "ancre":"1|RUE|ROSSAN","immat":"AB2460335",
     "re_fuses":[
        {"cle":"10|RUE|ST MAXIMIN","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":["12|RUE|ST MAXIMIN"],
     "injects":[], "kv_delete":["10|RUE|ST MAXIMIN"]},
    {"id":"E23","tag":"77_alb_thomas_sisley",
     "label":"77 COURS ALBERT THOMAS / 49-51 RUE PROFESSEUR PAUL SISLEY",
     "ancre":"77|COURS|ALBERT THOMAS","immat":"AC1055698",
     "re_fuses":[
        {"cle":"49|RUE|PROFESSEUR PAUL SISLEY","bgid_change":True,
         "old_cible":"16|RUE|GUILLOUD"},
     ],
     "extra_sources":["51|RUE|PROFESSEUR PAUL SISLEY"],
     "injects":[], "kv_delete":[]},
    {"id":"E24","tag":"duo_ii",
     "label":"113 RUE BARABAN (SDC LE DUO II) / 111 RUE BARABAN / 64 RUE ANTOINE CHARIAL",
     "ancre":"113|RUE|BARABAN","immat":"AD5133418",
     "re_fuses":[
        {"cle":"64|RUE|ANTOINE CHARIAL","bgid_change":True,
         "old_cible":"66|RUE|ANTOINE CHARIAL"},
     ],
     "extra_sources":[],
     "injects":[{"cle":"111|RUE|BARABAN","clone_from":"113|RUE|BARABAN",
                 "fcible":"113|RUE|BARABAN"}],
     "kv_delete":[]},
    # E25 SDC LE SISLEY : SPECIAL (REBIND-COPRO cle malformee)
    # E26
    {"id":"E26","tag":"tuiliers",
     "label":"16 RUE TUILIERS (SDC TUILIERS) / 14 RUE ST MAXIMIN",
     "ancre":"16|RUE|TUILIERS","immat":"AE0762401",
     "re_fuses":[
        {"cle":"14|RUE|ST MAXIMIN","bgid_change":True,"old_cible":"1|RUE|ROSSAN"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
    # E27 SPECIAL : 25 ST ANTOINE detach AC3226362 + RE-FUSE -> 272 LAFAYETTE
    # E28 STANDARD : 38+40 LAC (skip 42 per user)
    {"id":"E28","tag":"lac_38_40",
     "label":"38-40 AVENUE LACASSAGNE (LES JARDINS DU CHATEAU)",
     "ancre":"38|AVENUE|LACASSAGNE","immat":"AB8378317",
     "re_fuses":[
        {"cle":"40|AVENUE|LACASSAGNE","bgid_change":True,
         "old_cible":"38|AVENUE|LACASSAGNE"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
    # ============ VAGUE 3a REBIND univoques (8) ============
    # 20 LAC -> BRICKS 2 (REBIND-COPRO inside via special_bricks2)
    {"id":"R51","tag":"51_st_ant_310_laf",
     "label":"310 COURS LAFAYETTE / 51 RUE ST ANTOINE",
     "ancre":"310|COURS|LAFAYETTE","immat":"AD5250634",
     "re_fuses":[
        {"cle":"51|RUE|ST ANTOINE","bgid_change":True,"old_cible":"50|RUE|ST ANTOINE"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
    {"id":"R31","tag":"31_st_ant_richerand",
     "label":"8 RUE ETIENNE RICHERAND (LE RICHERAND) / 31 RUE ST ANTOINE",
     "ancre":"8|RUE|ETIENNE RICHERAND","immat":"AA8338717",
     "re_fuses":[
        {"cle":"31|RUE|ST ANTOINE","bgid_change":True,"old_cible":"35|RUE|ST ANTOINE"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
    {"id":"R137","tag":"137_charial_eusebe",
     "label":"12 RUE ST EUSEBE (SDC ESPACE EMERAUDE BAT B) / 137 RUE ANTOINE CHARIAL",
     "ancre":"12|RUE|ST EUSEBE","immat":"AA2028389",
     "re_fuses":[
        {"cle":"137|RUE|ANTOINE CHARIAL","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[], "injects":[],
     "kv_delete":["137|RUE|ANTOINE CHARIAL"]},
    {"id":"R18","tag":"18_dahlias_rebatel",
     "label":"26 RUE DOCTEUR REBATEL (SDC SQUARE REBATEL) / 18 RUE DAHLIAS",
     "ancre":"26|RUE|DOCTEUR REBATEL","immat":"AC9718610",
     "re_fuses":[
        {"cle":"18|RUE|DAHLIAS","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[], "injects":[],
     "kv_delete":["18|RUE|DAHLIAS"]},
    {"id":"R10R","tag":"10_riboud_flandin",
     "label":"21 RUE MAURICE FLANDIN (SDC 21 MAURICE FLANDIN) / 10 RUE RIBOUD",
     "ancre":"21|RUE|MAURICE FLANDIN","immat":"AC9634627",
     "re_fuses":[
        {"cle":"10|RUE|RIBOUD","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[], "injects":[],
     "kv_delete":["10|RUE|RIBOUD"]},
    {"id":"R338","tag":"338_pb_239_ff",
     "label":"239 AVENUE FELIX FAURE / 338 RUE PAUL BERT",
     "ancre":"239|AVENUE|FELIX FAURE","immat":"AA8508269",
     "re_fuses":[
        {"cle":"338|RUE|PAUL BERT","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[], "injects":[],
     "kv_delete":["338|RUE|PAUL BERT"]},
    {"id":"R3E","tag":"3_eusebe_1_eusebe",
     "label":"1 RUE ST EUSEBE (1/3 RUE SAINT EUSEBE) / 3 RUE ST EUSEBE",
     "ancre":"1|RUE|ST EUSEBE","immat":"AA8431108",
     "re_fuses":[
        {"cle":"3|RUE|ST EUSEBE","bgid_change":True,"old_cible":"2|RUE|ST EUSEBE"},
     ],
     "extra_sources":[], "injects":[], "kv_delete":[]},
]


def special_bricks2(doc, ad_by_cle, co_by_immat, args, log):
    """REBIND-COPRO BRICKS 2 (AG1556893) cle malformee '24||ET 24 BIS AVENUE LACASSAGNE'
       -> '24|AVENUE|LACASSAGNE' + INJECT propre + RE-FUSE 20 LACASSAGNE."""
    print()
    print(f"--- BRICKS 2 SPECIAL (REBIND-COPRO + INJECT propre + RE-FUSE 20 LAC)")
    OLD = "24||ET 24 BIS AVENUE LACASSAGNE"
    NEW = "24|AVENUE|LACASSAGNE"
    IMMAT = "AG1556893"
    LABEL = "24-24B AVENUE LACASSAGNE (BRICKS 2) / 20 AVENUE LACASSAGNE"

    co = co_by_immat.get(IMMAT)
    if not co: print(f"  [SKIP] copro {IMMAT} absente"); return 0
    print(f"  copro snapshot : nom={co.get('nom_copropriete')!r}  lots_tot={co.get('nb_lots_total')}  hab={co.get('nb_lots_habitation')}")

    src_old = ad_by_cle.get(OLD)
    bg_anc = (src_old or {}).get("batiment_groupe_id") or "bdnb-bg-WLXU-6YKR-D8DU"

    if args.apply:
        co["cle_adresse"] = NEW
        co["_cle_adresse_ex"] = OLD
        log.append({"op":"REBIND-COPRO","immat":IMMAT,"old_cle":OLD,"new_cle":NEW})
        print(f"  [REBIND-COPRO] {IMMAT} {OLD!r} -> {NEW!r}")

        if NEW not in ad_by_cle:
            src = src_old or {}
            new = {
                "cle":NEW,"adresse":"24 AVENUE LACASSAGNE",
                "longitude":src.get("longitude"),"latitude":src.get("latitude"),
                "code_iris":src.get("code_iris"),"_coord_source":f"clone_{OLD}",
                "dans_majic":False,"sci_proprietaire":"non","sci_nom":"","sci_siren":"",
                "syndic":src.get("syndic"),"_syndic_src":src.get("_syndic_src"),
                "ventes_par_an":{},"nb_ventes_total":0,
                "nb_log_bdnb":src.get("nb_log_bdnb"),
                "annee_construction":src.get("annee_construction"),
                "classe_dpe":src.get("classe_dpe"),
                "type_batiment":src.get("type_batiment"),
                "type_chauffage":src.get("type_chauffage"),
                "batiment_groupe_id":bg_anc,
                "_bdnb_match":"correctif_v3_bricks2_inject_ancre",
                "ventes_par_an_logement":{},"nb_ventes_logement":0,
                "taux_rotation_logement":0.0,"classement_rotation_logement":"Fige",
                "_taux_logement_src":"copie_inject",
                "usage_principal_bdnb":src.get("usage_principal_bdnb"),
                "_ilot":src.get("_ilot"),
                "numero_immatriculation":IMMAT,
                "nb_lots_habitation":co.get("nb_lots_habitation"),
                "taux_rotation":co.get("taux_rotation_5ans"),
                "classement_rotation":co.get("classement_rotation"),
                "_fusion_auto":None,"_fusion_cible":None,
            }
            doc["adresses"].append(new); ad_by_cle[NEW] = new
            print(f"  [INJECT-ANCRE] {NEW} bgid=...{bg_anc[-9:]} immat={IMMAT}")
            log.append({"op":"INJECT-ANCRE","cle":NEW,"immat":IMMAT})

        # RE-FUSE old malformed
        if OLD in ad_by_cle:
            a_old = ad_by_cle[OLD]
            a_old["_fusion_auto"] = True
            a_old["_fusion_cible"] = NEW
            a_old["_bdnb_match"] = "correctif_v3_bricks2_old_malformed"
            a_old["numero_immatriculation"] = None
            a_old["_detach_immat_ex"] = IMMAT
            print(f"  [RE-FUSE] {OLD!r} -> {NEW} (malformed, immat detach)")
            log.append({"op":"RE-FUSE-MALFORMED","cle":OLD,"new":NEW,"detach":IMMAT})

    # RE-FUSE 20 LAC
    delta = 0
    a20 = ad_by_cle.get("20|AVENUE|LACASSAGNE")
    if a20:
        bg_cur = a20.get("batiment_groupe_id") or ""
        bdnb20 = to_int(a20.get("nb_log_bdnb"))
        cur_cible = a20.get("_fusion_cible")
        print(f"  [{'RE-FUSE' if args.apply else 'DRY'}] 20|AVENUE|LACASSAGNE  bgid ...{bg_cur[-9:]} -> ...{bg_anc[-9:]}  ex-cible='{cur_cible}'  bdnb={bdnb20}")
        if args.apply:
            a20["_fusion_auto"] = True
            a20["_fusion_cible"] = NEW
            a20["_bdnb_match"] = "correctif_v3_20lac_rebind"
            a20["batiment_groupe_id"] = bg_anc
            log.append({"op":"RE-FUSE","cle":"20|AVENUE|LACASSAGNE","cible":NEW,"old_cible":cur_cible})
            # Check bgid dedup
            bg_global = defaultdict(list)
            for a in doc["adresses"]:
                bgg = a.get("batiment_groupe_id") or ""
                if bgg: bg_global[bgg].append(a.get("cle") or "")
            if not bg_global.get(bg_cur) and bdnb20:
                delta -= bdnb20
                print(f"  bgid ...{bg_cur[-9:]} SUPPRIME -> -{bdnb20}")

    # Label
    if args.apply and NEW in ad_by_cle:
        a_new = ad_by_cle[NEW]
        a_new["_fusion_auto_label"] = LABEL
        srcs = list(a_new.get("_fusion_auto_sources") or [])
        for s in ["20|AVENUE|LACASSAGNE", OLD]:
            if s in ad_by_cle and s not in srcs: srcs.append(s)
        a_new["_fusion_auto_sources"] = srcs
        print(f"  [LABEL] {NEW} label='{LABEL}'")
        log.append({"op":"LABEL","cle":NEW,"label":LABEL,"sources":srcs})
    return delta


def special_sisley(doc, ad_by_cle, co_by_immat, args, log):
    """REBIND-COPRO SDC LE SISLEY (AC7505134) cle malformee
       -> 30 SISLEY existant + RE-FUSE 32 SISLEY + INJECT 30B SISLEY."""
    print()
    print(f"--- E25 SDC LE SISLEY SPECIAL (REBIND-COPRO + RE-FUSE 30/32 + INJECT 30B)")
    OLD = "30||30B R DU PROFESSEUR PAUL SISLEY"
    NEW = "30|RUE|PROFESSEUR PAUL SISLEY"
    IMMAT = "AC7505134"
    LABEL = "30-30B-32 RUE PROFESSEUR PAUL SISLEY (SDC LE SISLEY)"

    co = co_by_immat.get(IMMAT)
    if not co: print(f"  [SKIP] copro {IMMAT} absente"); return 0
    print(f"  copro snapshot : nom={co.get('nom_copropriete')!r}  lots_tot={co.get('nb_lots_total')}  hab={co.get('nb_lots_habitation')}")

    a30 = ad_by_cle.get(NEW)
    if not a30: print(f"  [SKIP] {NEW} absent"); return 0
    bg_anc = a30.get("batiment_groupe_id") or ""

    if args.apply:
        # REBIND copro malformed -> propre
        co["cle_adresse"] = NEW
        co["_cle_adresse_ex"] = OLD
        log.append({"op":"REBIND-COPRO","immat":IMMAT,"old_cle":OLD,"new_cle":NEW})
        print(f"  [REBIND-COPRO] {IMMAT} {OLD!r} -> {NEW!r}")

        # 30 SISLEY devient ancre : retirer fauto, ajouter immat
        a30["_fusion_auto"] = None
        a30["_fusion_cible"] = None
        a30["numero_immatriculation"] = IMMAT
        a30["nb_lots_habitation"] = co.get("nb_lots_habitation")
        a30["taux_rotation"] = co.get("taux_rotation_5ans")
        a30["classement_rotation"] = co.get("classement_rotation")
        a30["syndic"] = co.get("syndic")
        a30["_bdnb_match"] = "correctif_v3_sisley_promote_ancre"
        print(f"  [PROMOTE] {NEW} -> ancre (immat={IMMAT}, fauto cleared)")
        log.append({"op":"PROMOTE","cle":NEW,"immat":IMMAT})

    # RE-FUSE 32 SISLEY
    delta = 0
    a32 = ad_by_cle.get("32|RUE|PROFESSEUR PAUL SISLEY")
    if a32:
        bg_cur = a32.get("batiment_groupe_id") or ""
        bdnb32 = to_int(a32.get("nb_log_bdnb"))
        cur_cible = a32.get("_fusion_cible")
        print(f"  [{'RE-FUSE' if args.apply else 'DRY'}] 32 SISLEY  bgid ...{bg_cur[-9:]} -> ...{bg_anc[-9:]}  ex-cible='{cur_cible}'  bdnb={bdnb32}")
        if args.apply:
            a32["_fusion_auto"] = True
            a32["_fusion_cible"] = NEW
            a32["_bdnb_match"] = "correctif_v3_32sisley_rebind"
            a32["batiment_groupe_id"] = bg_anc
            log.append({"op":"RE-FUSE","cle":"32|RUE|PROFESSEUR PAUL SISLEY","cible":NEW,"old_cible":cur_cible})
            # Dedup check
            bg_global = defaultdict(list)
            for a in doc["adresses"]:
                bgg = a.get("batiment_groupe_id") or ""
                if bgg: bg_global[bgg].append(a.get("cle") or "")
            if not bg_global.get(bg_cur) and bdnb32:
                delta -= bdnb32
                print(f"  bgid ...{bg_cur[-9:]} SUPPRIME -> -{bdnb32}")

    # INJECT 30B SISLEY
    INJ = "30B|RUE|PROFESSEUR PAUL SISLEY"
    if INJ in ad_by_cle:
        print(f"  [SKIP-INJECT] {INJ} deja present")
    elif args.apply:
        src = a30
        new = {
            "cle":INJ,"adresse":"30B RUE PROFESSEUR PAUL SISLEY",
            "longitude":src.get("longitude"),"latitude":src.get("latitude"),
            "code_iris":src.get("code_iris"),"_coord_source":f"clone_{NEW}",
            "dans_majic":False,"sci_proprietaire":"non","sci_nom":"","sci_siren":"",
            "syndic":src.get("syndic"),"_syndic_src":src.get("_syndic_src"),
            "ventes_par_an":{},"nb_ventes_total":0,
            "nb_log_bdnb":None,
            "annee_construction":src.get("annee_construction"),
            "classe_dpe":src.get("classe_dpe"),
            "type_batiment":src.get("type_batiment"),
            "type_chauffage":src.get("type_chauffage"),
            "batiment_groupe_id":bg_anc,
            "_bdnb_match":"correctif_v3_sisley_inject_30b_label",
            "ventes_par_an_logement":{},"nb_ventes_logement":0,
            "taux_rotation_logement":0.0,"classement_rotation_logement":"Fige",
            "_taux_logement_src":"copie_inject",
            "usage_principal_bdnb":src.get("usage_principal_bdnb"),
            "_ilot":src.get("_ilot"),
            "_fusion_auto":True,"_fusion_cible":NEW,
        }
        doc["adresses"].append(new); ad_by_cle[INJ] = new
        print(f"  [INJECT] {INJ} label-only"); log.append({"op":"INJECT","cle":INJ})

    # Label
    if args.apply:
        a30["_fusion_auto_label"] = LABEL
        srcs = list(a30.get("_fusion_auto_sources") or [])
        for s in ["32|RUE|PROFESSEUR PAUL SISLEY", INJ, OLD]:
            if s in ad_by_cle and s not in srcs: srcs.append(s)
        a30["_fusion_auto_sources"] = srcs
        print(f"  [LABEL] {NEW} label='{LABEL}'")
        log.append({"op":"LABEL","cle":NEW,"label":LABEL,"sources":srcs})
    return delta


def special_25_st_antoine(doc, ad_by_cle, co_by_immat, args, log):
    """E27 LA COUR LAFAYETTE : 25 ST ANTOINE detach AC3226362 + RE-FUSE -> 272 LAFAYETTE.
       Pattern DETACH (similaire 7B ALBERT THOMAS)."""
    print()
    print(f"--- E27 LA COUR LAFAYETTE SPECIAL (DETACH 25 ST ANT + RE-FUSE -> 272 LAFAYETTE)")
    cle25 = "25|RUE|ST ANTOINE"
    NEW_CIB = "272|COURS|LAFAYETTE"
    DETACH_IMMAT = "AC3226362"
    bg_anc = (ad_by_cle.get(NEW_CIB) or {}).get("batiment_groupe_id") or ""
    a25 = ad_by_cle.get(cle25)
    if not a25: print(f"  [SKIP] {cle25} absent"); return 0
    cur_immat = a25.get("numero_immatriculation")
    bg_cur = a25.get("batiment_groupe_id") or ""
    bdnb25 = to_int(a25.get("nb_log_bdnb"))
    print(f"  [{'APPLY' if args.apply else 'DRY'}] {cle25}  bgid ...{bg_cur[-9:]} -> ...{bg_anc[-9:]}  detach immat {cur_immat} (-> None)  cible='{NEW_CIB}'  bdnb={bdnb25}")

    delta = 0
    if args.apply:
        a25["batiment_groupe_id"] = bg_anc
        a25["_fusion_auto"] = True
        a25["_fusion_cible"] = NEW_CIB
        a25["_bdnb_match"] = "correctif_v3_25stant_detach_refuse"
        if cur_immat == DETACH_IMMAT:
            a25["numero_immatriculation"] = None
            a25["_detach_immat_ex"] = DETACH_IMMAT
        log.append({"op":"DETACH+RE-FUSE","cle":cle25,"cible":NEW_CIB,"detach":DETACH_IMMAT})

        # Label sur 272
        a272 = ad_by_cle[NEW_CIB]
        a272["_fusion_auto_label"] = "272 COURS LAFAYETTE (LA COUR LAFAYETTE) / 25 RUE ST ANTOINE"
        srcs = list(a272.get("_fusion_auto_sources") or [])
        if cle25 not in srcs: srcs.append(cle25)
        a272["_fusion_auto_sources"] = srcs
        print(f"  [LABEL] {NEW_CIB} label etendu")
        log.append({"op":"LABEL","cle":NEW_CIB,"sources":srcs})

        # Dedup check
        bg_global = defaultdict(list)
        for a in doc["adresses"]:
            bgg = a.get("batiment_groupe_id") or ""
            if bgg: bg_global[bgg].append(a.get("cle") or "")
        # Si UT3G-U7D2 plus aucune adresse (les 26/28/30 ST ANT ont deja migre via E18)
        cles_restantes_bg_cur = [c for c in bg_global.get(bg_cur, []) if c != cle25]
        # Comme on a deja apply, bg_global reflete l etat post-apply
        if not bg_global.get(bg_cur) and bdnb25:
            delta -= bdnb25
            print(f"  bgid ...{bg_cur[-9:]} SUPPRIME -> -{bdnb25}")
    return delta


def process_standard_fix(fx, doc, ad_by_cle, co_by_immat, args, log):
    """Process standard FIX (RE-FUSE + INJECT + LABEL + dedup)."""
    print()
    print(f"--- {fx['id']} [{fx['tag']}]  ancre={fx['ancre']}  immat={fx['immat']}")
    a_anc = ad_by_cle.get(fx["ancre"])
    if not a_anc:
        print(f"  [SKIP] ancre absente"); return 0
    bg_anc = a_anc.get("batiment_groupe_id") or ""
    co = co_by_immat.get(fx["immat"])
    if co:
        print(f"  copro snapshot : nom={co.get('nom_copropriete')!r}  lots_tot={co.get('nb_lots_total')}  hab={co.get('nb_lots_habitation')}")

    bgids_visites = defaultdict(list)
    for rf in fx.get("re_fuses", []):
        cle = rf["cle"]
        a = ad_by_cle.get(cle)
        if not a:
            print(f"  [SKIP] {cle} absent"); continue
        bg_cur = a.get("batiment_groupe_id") or ""
        cur_cible = a.get("_fusion_cible")
        bgids_visites[bg_cur].append(cle)
        print(f"  [{'RE-FUSE' if args.apply else 'DRY'}] {cle:38s}  bgid ...{bg_cur[-9:]} -> "
              f"{'...'+bg_anc[-9:] if rf['bgid_change'] else '(inchange)'}  ex-cible='{cur_cible}'")
        if args.apply:
            a["_fusion_auto"] = True
            a["_fusion_cible"] = fx["ancre"]
            a["_bdnb_match"] = f"correctif_v3_{fx['tag']}_re_fuse"
            if rf["bgid_change"]: a["batiment_groupe_id"] = bg_anc
            log.append({"op":"RE-FUSE","cle":cle,"cible":fx["ancre"],"old_cible":cur_cible})

    for inj in fx.get("injects", []):
        cle = inj["cle"]
        if cle in ad_by_cle:
            print(f"  [SKIP-INJECT] {cle} deja present"); continue
        src = ad_by_cle.get(inj["clone_from"])
        if not src:
            print(f"  [SKIP-INJECT] clone_from {inj['clone_from']} absent"); continue
        print(f"  [{'INJECT' if args.apply else 'DRY'}] {cle:38s} clone_from={inj['clone_from']}  cible='{inj['fcible']}'")
        if args.apply:
            new = {
                "cle":cle,"adresse":cle.replace("|"," "),
                "longitude":src.get("longitude"),"latitude":src.get("latitude"),
                "code_iris":src.get("code_iris"),
                "_coord_source":f"clone_{inj['clone_from']}",
                "dans_majic":False,"sci_proprietaire":"non","sci_nom":"","sci_siren":"",
                "syndic":src.get("syndic"),"_syndic_src":src.get("_syndic_src"),
                "ventes_par_an":{},"nb_ventes_total":0,
                "nb_log_bdnb":None,
                "annee_construction":src.get("annee_construction"),
                "classe_dpe":src.get("classe_dpe"),
                "type_batiment":src.get("type_batiment"),
                "type_chauffage":src.get("type_chauffage"),
                "batiment_groupe_id":src.get("batiment_groupe_id"),
                "_bdnb_match":f"correctif_v3_{fx['tag']}_inject_label",
                "ventes_par_an_logement":{},"nb_ventes_logement":0,
                "taux_rotation_logement":0.0,"classement_rotation_logement":"Fige",
                "_taux_logement_src":"copie_inject",
                "usage_principal_bdnb":src.get("usage_principal_bdnb"),
                "_ilot":src.get("_ilot"),
                "_fusion_auto":True,"_fusion_cible":inj["fcible"],
            }
            doc["adresses"].append(new); ad_by_cle[cle] = new
            log.append({"op":"INJECT","cle":cle,"fcible":inj["fcible"]})

    if args.apply:
        a_anc["_fusion_auto_label"] = fx["label"]
        srcs = list(a_anc.get("_fusion_auto_sources") or [])
        all_s = [rf["cle"] for rf in fx.get("re_fuses",[])] + fx.get("extra_sources",[])
        for inj in fx.get("injects",[]): all_s.append(inj["cle"])
        for s in all_s:
            if s in ad_by_cle and s not in srcs: srcs.append(s)
        a_anc["_fusion_auto_sources"] = srcs
        print(f"  [LABEL] {fx['ancre']} label='{fx['label']}'")
        log.append({"op":"LABEL","cle":fx["ancre"],"label":fx["label"],"sources":srcs})

    delta = 0
    bg_global = defaultdict(list)
    for a in doc["adresses"]:
        bgg = a.get("batiment_groupe_id") or ""
        if bgg: bg_global[bgg].append(a.get("cle") or "")
    for bg_ex, cles_p in bgids_visites.items():
        if bg_ex == bg_anc: continue
        all_cles = bg_global.get(bg_ex, [])
        restantes = [c for c in all_cles if c not in cles_p]
        bdnb_bg = max([to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in all_cles if c in ad_by_cle], default=0)
        # If apply : bg_global reflects post-apply state, so "restantes" already excludes the moved cles
        if not all_cles and bdnb_bg == 0:
            # Compute bdnb from sources that were moved
            for c in cles_p:
                bdnb_bg = max(bdnb_bg, to_int(ad_by_cle[c].get("nb_log_bdnb")))
        if not restantes and not all_cles:
            # All adresses moved away
            for c in cles_p:
                bdnb_bg = max(bdnb_bg, to_int(ad_by_cle[c].get("nb_log_bdnb")))
            if bdnb_bg:
                delta -= bdnb_bg
                print(f"  bgid ...{bg_ex[-9:]} SUPPRIME -> -{bdnb_bg}")
    return delta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not LIGHT.exists(): sys.exit("light absent")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_vague3_dl") and not args.apply:
        print("  [info] marker deja present.")

    by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
    co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]
                   if c.get("numero_immatriculation")}

    print("=" * 110)
    print(f"VAGUE 3 DL ({'APPLY' if args.apply else 'DRY-RUN'})  -- {len(FIXES_STANDARD)} std + 3 special")
    print("=" * 110)

    total = 0; log = []

    for fx in FIXES_STANDARD:
        total += process_standard_fix(fx, doc, by_cle, co_by_immat, args, log)

    # 3 specials
    total += special_bricks2(doc, by_cle, co_by_immat, args, log)
    total += special_sisley(doc, by_cle, co_by_immat, args, log)
    total += special_25_st_antoine(doc, by_cle, co_by_immat, args, log)

    if args.apply:
        md["_correctif_vague3_dl"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern":"Vague 3 DL : 10 mega-ensembles E19-E28 + 8 REBIND univoques + 3 special (BRICKS2 REBIND-COPRO, SISLEY REBIND-COPRO+PROMOTE, 25 ST ANT DETACH)",
            "fixes":[{"id":f["id"],"tag":f["tag"],"ancre":f["ancre"],
                      "immat":f["immat"],"label":f["label"]} for f in FIXES_STANDARD],
            "specials":["BRICKS2 (AG1556893 REBIND-COPRO + INJECT 24 LAC + RE-FUSE 20 LAC)",
                        "SDC LE SISLEY (AC7505134 REBIND-COPRO + PROMOTE 30 SISLEY + RE-FUSE 32 + INJECT 30B)",
                        "LA COUR LAFAYETTE 25 ST ANT (DETACH AC3226362 + RE-FUSE 272 LAFAYETTE)"],
            "log":log,
            "delta_parc_dedup":total,
        }
        if BAK.exists(): print(f"  [warn] backup existant -> ecrase");
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(doc['adresses'])} adresses)")

    print()
    print("=" * 110)
    print(f"TOTAL DELTA dedup : {total:+d} log")
    print("=" * 110)


if __name__ == "__main__":
    main()
