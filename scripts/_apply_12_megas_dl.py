#!/usr/bin/env python3
"""Apply 12 mega-ensembles DL E7-E18 (terrain user, dry-run + apply).

11 fixes standards + 1 fix special (E13 SAINT MARC I avec REBIND copro
cle malformee + INJECT adresse propre).

Conventions identiques aux fixes precedents : RE-FUSE (bgid switch + fcible),
REBIND (fcible change + bgid switch), SAME-BG (deja meme bgid, no-op),
INJECT (clone adresse label-only).
"""
import json, sys, shutil, argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre12megas.bak"

# (id, label, ancre cle, ancre immat, re_fuses, extra_sources, injects, kv_delete)
# bgid_change=True force bgid switch. REBIND = bgid_change=True (gerer fcible deja True).
FIXES = [
    {"vague":"E7","tag":"jardins_babylone",
     "label_ancre":"27-29-31 RUE STE ANNE DE BARABAN / 33 RUE CLAUDIUS PIONCHON",
     "ancre_cle":"27|RUE|STE ANNE DE BARABAN", "ancre_immat":"AA1700848",
     "re_fuses":[
        {"cle":"33|RUE|CLAUDIUS PIONCHON","bgid_change":True,"old_cible":"29|RUE|CLAUDIUS PIONCHON"},
     ],
     "extra_sources":["29|RUE|STE ANNE DE BARABAN","31|RUE|STE ANNE DE BARABAN"],
     "kv_delete":[]},
    {"vague":"E8","tag":"177_felix_faure",
     "label_ancre":"177 / 177B / 177T AVENUE FELIX FAURE",
     "ancre_cle":"177|AVENUE|FELIX FAURE", "ancre_immat":"AB3274529",
     "re_fuses":[
        {"cle":"177T|AVENUE|FELIX FAURE","bgid_change":True,"old_cible":"179|AVENUE|FELIX FAURE"},
     ],
     "extra_sources":["177B|AVENUE|FELIX FAURE"],
     "kv_delete":["177B|AVENUE|FELIX FAURE","177T|AVENUE|FELIX FAURE"]},
    {"vague":"E9","tag":"lacassagne_david",
     "label_ancre":"9-11 RUE DAVID / 2-6-8-10-12 RUE METALLURGIE",
     "ancre_cle":"9|RUE|DAVID", "ancre_immat":"AB3954260",
     "re_fuses":[
        {"cle":"2|RUE|METALLURGIE","bgid_change":True,"old_cible":"1|RUE|METALLURGIE"},
     ],
     "extra_sources":["11|RUE|DAVID","6|RUE|METALLURGIE","8|RUE|METALLURGIE",
                      "10|RUE|METALLURGIE","12|RUE|METALLURGIE"],
     "kv_delete":[]},
    {"vague":"E10","tag":"hermitage",
     "label_ancre":"25-27-29-31 RUE GUILLOUD",
     "ancre_cle":"27|RUE|GUILLOUD", "ancre_immat":"AB3360401",
     "re_fuses":[
        {"cle":"31|RUE|GUILLOUD","bgid_change":True,"old_cible":"35|RUE|GUILLOUD"},
     ],
     "extra_sources":["25|RUE|GUILLOUD"],
     "injects":[
        {"cle":"29|RUE|GUILLOUD","clone_from":"27|RUE|GUILLOUD","fcible":"27|RUE|GUILLOUD"},
     ],
     "kv_delete":[]},
    {"vague":"E11","tag":"carre_st_antoine",
     "label_ancre":"3-5 RUE ETIENNE RICHERAND / 35 RUE ST ANTOINE",
     "ancre_cle":"35|RUE|ST ANTOINE", "ancre_immat":"AC6493506",
     "re_fuses":[
        {"cle":"5|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[],
     "injects":[
        {"cle":"3|RUE|ETIENNE RICHERAND","clone_from":"35|RUE|ST ANTOINE","fcible":"35|RUE|ST ANTOINE"},
     ],
     "kv_delete":["5|RUE|ETIENNE RICHERAND"]},
    {"vague":"E12","tag":"horizon_monplaisir",
     "label_ancre":"66 AVENUE LACASSAGNE / 64-64B AVENUE LACASSAGNE / 7 RUE BARA",
     "ancre_cle":"66|AVENUE|LACASSAGNE", "ancre_immat":"AE8227266",
     "re_fuses":[
        {"cle":"64|AVENUE|LACASSAGNE","bgid_change":True,"old_cible":None},
        {"cle":"64B|AVENUE|LACASSAGNE","bgid_change":True,"old_cible":"64|AVENUE|LACASSAGNE"},
     ],
     "extra_sources":[],
     "injects":[
        {"cle":"7|RUE|BARA","clone_from":"66|AVENUE|LACASSAGNE","fcible":"66|AVENUE|LACASSAGNE"},
     ],
     "kv_delete":["64|AVENUE|LACASSAGNE","64B|AVENUE|LACASSAGNE"]},
    # E13 SAINT MARC I : SPECIAL (REBIND copro + INJECT propre adresse + RE-FUSE)
    # Traite separement plus bas via special_e13().
    {"vague":"E14","tag":"victorines",
     "label_ancre":"14 RUE ST VICTORIEN / 2 RUE LOUIS JASSERON",
     "ancre_cle":"14|RUE|ST VICTORIEN", "ancre_immat":"AC3805199",
     "re_fuses":[
        {"cle":"2|RUE|LOUIS JASSERON","bgid_change":True,"old_cible":"3|RUE|LOUIS JASSERON"},
     ],
     "extra_sources":[],
     "kv_delete":[]},
    {"vague":"E15","tag":"closerie_tilleuls_ii",
     "label_ancre":"5-7-9-11-13 RUE FRANCOIS GILLET",
     "ancre_cle":"7|RUE|FRANCOIS GILLET", "ancre_immat":"AA4868378",
     "re_fuses":[
        {"cle":"9|RUE|FRANCOIS GILLET","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":["11|RUE|FRANCOIS GILLET"],
     "injects":[
        {"cle":"5|RUE|FRANCOIS GILLET","clone_from":"7|RUE|FRANCOIS GILLET","fcible":"7|RUE|FRANCOIS GILLET"},
        {"cle":"13|RUE|FRANCOIS GILLET","clone_from":"7|RUE|FRANCOIS GILLET","fcible":"7|RUE|FRANCOIS GILLET"},
     ],
     "kv_delete":["9|RUE|FRANCOIS GILLET"]},
    {"vague":"E16","tag":"pavillon_dauphin",
     "label_ancre":"89-93 RUE DAUPHINE / 14 RUE CARRY",
     "ancre_cle":"89|RUE|DAUPHINE", "ancre_immat":"AC9350984",
     "re_fuses":[
        {"cle":"14|RUE|CARRY","bgid_change":True,"old_cible":"6|RUE|CARRY"},
     ],
     "extra_sources":["93|RUE|DAUPHINE"],
     "kv_delete":[]},
    {"vague":"E17","tag":"jardins_president_ext",
     "label_ancre":"57 RUE ETIENNE RICHERAND / 36 AVENUE GEORGES POMPIDOU / 3 RUE TEINTURIERS",
     "ancre_cle":"57|RUE|ETIENNE RICHERAND", "ancre_immat":"AA1888700",
     "re_fuses":[
        {"cle":"3|RUE|TEINTURIERS","bgid_change":True,"old_cible":None},
     ],
     "extra_sources":[],
     "injects":[
        {"cle":"36|AVENUE|GEORGES POMPIDOU","clone_from":"57|RUE|ETIENNE RICHERAND","fcible":"57|RUE|ETIENNE RICHERAND"},
     ],
     "kv_delete":["3|RUE|TEINTURIERS"]},
    {"vague":"E18","tag":"jardins_charial",
     "label_ancre":"22-24-26-28-30 RUE ST ANTOINE / 14-16-18-20-22-24 RUE ETIENNE RICHERAND",
     "ancre_cle":"22|RUE|ST ANTOINE", "ancre_immat":"AA1601434",
     "re_fuses":[
        {"cle":"14|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":None},
        {"cle":"18|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":"19|RUE|ETIENNE RICHERAND"},
        {"cle":"20|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":"19|RUE|ETIENNE RICHERAND"},
        {"cle":"22|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":"21|RUE|ETIENNE RICHERAND"},
        {"cle":"24|RUE|ETIENNE RICHERAND","bgid_change":True,"old_cible":"28|RUE|ETIENNE RICHERAND"},
        {"cle":"24|RUE|ST ANTOINE","bgid_change":True,"old_cible":"22|RUE|ST ANTOINE"},
        {"cle":"26|RUE|ST ANTOINE","bgid_change":True,"old_cible":"22|RUE|ST ANTOINE"},
        {"cle":"28|RUE|ST ANTOINE","bgid_change":True,"old_cible":"22|RUE|ST ANTOINE"},
        {"cle":"30|RUE|ST ANTOINE","bgid_change":True,"old_cible":"25|RUE|ST ANTOINE"},
     ],
     "extra_sources":["16|RUE|ETIENNE RICHERAND"],
     "kv_delete":["14|RUE|ETIENNE RICHERAND"]},
]


def to_int(x):
    try: return int(x)
    except: return 0


def special_e13(doc, ad_by_cle, co_by_immat, args, log):
    """E13 SAINT MARC I : REBIND copro cle_adresse + INJECT propre adresse
    '42|RUE|ST MAXIMIN' + RE-FUSE 44/46/48/50 ST MAXIMIN dessus.
    """
    print()
    print(f"--- E13 [saint_marc_i] SPECIAL (REBIND copro cle malformee + INJECT 42 + RE-FUSE 4)")
    OLD_CLE = "42A||50 RUE ST MAXIMIN"
    NEW_CLE = "42|RUE|ST MAXIMIN"
    IMMAT   = "AA2505634"
    LABEL   = "42-44-46-48-50 RUE ST MAXIMIN"

    # 1. REBIND copro
    co_entry = co_by_immat.get(IMMAT)
    if not co_entry:
        print(f"  [SKIP] copro {IMMAT} absente"); return 0
    old_cle_co = co_entry.get("cle_adresse")
    print(f"  copro snapshot : nom='{co_entry.get('nom_copropriete')}'  "
          f"lots_tot={co_entry.get('nb_lots_total')}  hab={co_entry.get('nb_lots_habitation')}")
    print(f"  copro cle_adresse actuelle : {old_cle_co!r}")
    if args.apply:
        co_entry["cle_adresse"] = NEW_CLE
        co_entry["_cle_adresse_ex"] = old_cle_co
        print(f"  [REBIND-COPRO] copro {IMMAT}  cle_adresse {OLD_CLE!r} -> {NEW_CLE!r}")
        log.append({"op":"REBIND-COPRO","immat":IMMAT,"old_cle":OLD_CLE,"new_cle":NEW_CLE})

    # 2. INJECT propre adresse '42|RUE|ST MAXIMIN' (cloner depuis l'ancien malformee)
    src = ad_by_cle.get(OLD_CLE)
    if not src:
        print(f"  [WARN] adresse malformee {OLD_CLE!r} absente light - INJECT clone-vide")
        src = {}
    bg_anc = src.get("batiment_groupe_id") or "bdnb-bg-YTYU-45YJ-XXXX"
    if NEW_CLE in ad_by_cle:
        print(f"  [SKIP-INJECT] {NEW_CLE} deja present")
    elif args.apply:
        new = {
            "cle": NEW_CLE, "adresse": "42 RUE ST MAXIMIN",
            "longitude": src.get("longitude"), "latitude": src.get("latitude"),
            "code_iris": src.get("code_iris"),
            "_coord_source": f"clone_{OLD_CLE}",
            "dans_majic": False, "sci_proprietaire":"non","sci_nom":"","sci_siren":"",
            "syndic": src.get("syndic"), "_syndic_src": src.get("_syndic_src"),
            "ventes_par_an":{}, "nb_ventes_total":0,
            "nb_log_bdnb": src.get("nb_log_bdnb"),
            "annee_construction": src.get("annee_construction"),
            "classe_dpe": src.get("classe_dpe"),
            "type_batiment": src.get("type_batiment"),
            "type_chauffage": src.get("type_chauffage"),
            "batiment_groupe_id": bg_anc,
            "_bdnb_match":"correctif_12megas_saint_marc_i_inject_ancre",
            "ventes_par_an_logement":{},"nb_ventes_logement":0,
            "taux_rotation_logement":0.0,"classement_rotation_logement":"Fige",
            "_taux_logement_src":"copie_inject",
            "usage_principal_bdnb": src.get("usage_principal_bdnb"),
            "_ilot": src.get("_ilot"),
            "numero_immatriculation": IMMAT,
            "nb_lots_habitation": co_entry.get("nb_lots_habitation"),
            "taux_rotation": co_entry.get("taux_rotation_5ans"),
            "classement_rotation": co_entry.get("classement_rotation"),
            "_fusion_auto": None, "_fusion_cible": None,
        }
        doc["adresses"].append(new)
        ad_by_cle[NEW_CLE] = new
        print(f"  [INJECT-ANCRE] {NEW_CLE}  bgid=...{bg_anc[-9:]}  immat={IMMAT}")
        log.append({"op":"INJECT-ANCRE","cle":NEW_CLE,"immat":IMMAT,"bgid":bg_anc})

    # 3. RE-FUSE l'ancienne adresse malformee vers la nouvelle (pour propre)
    if OLD_CLE in ad_by_cle and args.apply:
        a_old = ad_by_cle[OLD_CLE]
        a_old["_fusion_auto"] = True
        a_old["_fusion_cible"] = NEW_CLE
        a_old["_bdnb_match"] = "correctif_12megas_saint_marc_i_old_malformed"
        a_old["numero_immatriculation"] = None
        a_old["_detach_immat_ex"] = IMMAT
        print(f"  [RE-FUSE] {OLD_CLE!r} -> {NEW_CLE} (ancienne malformee, immat detache)")
        log.append({"op":"RE-FUSE-MALFORMED","cle":OLD_CLE,"new":NEW_CLE,"detach_immat":IMMAT})

    # 4. RE-FUSE 44/46/48/50 ST MAXIMIN
    sources = ["44|RUE|ST MAXIMIN","46|RUE|ST MAXIMIN","48|RUE|ST MAXIMIN","50|RUE|ST MAXIMIN"]
    delta_dedup = 0
    bgids_visites = {}
    for c in sources:
        a = ad_by_cle.get(c)
        if not a:
            print(f"  [SKIP] {c} absent light"); continue
        bg_cur = a.get("batiment_groupe_id") or ""
        bdnb_rf = to_int(a.get("nb_log_bdnb"))
        bgids_visites.setdefault(bg_cur, []).append(c)
        print(f"  [{'RE-FUSE' if args.apply else 'DRY'}] {c:36s} bgid ...{bg_cur[-9:]} -> ...{bg_anc[-9:]}  bdnb={bdnb_rf}")
        if args.apply:
            a["batiment_groupe_id"] = bg_anc
            a["_fusion_auto"] = True
            a["_fusion_cible"] = NEW_CLE
            a["_bdnb_match"] = "correctif_12megas_saint_marc_i_re_fuse"
            log.append({"op":"RE-FUSE","cle":c,"cible":NEW_CLE,"old_bgid":bg_cur})

    # 5. Label sur nouvelle ancre
    if args.apply and NEW_CLE in ad_by_cle:
        a_new = ad_by_cle[NEW_CLE]
        a_new["_fusion_auto_label"] = LABEL
        srcs = list(a_new.get("_fusion_auto_sources") or [])
        for s in sources + [OLD_CLE]:
            if s in ad_by_cle and s not in srcs: srcs.append(s)
        a_new["_fusion_auto_sources"] = srcs
        print(f"  [LABEL] {NEW_CLE}  label='{LABEL}'  sources={srcs}")
        log.append({"op":"LABEL","cle":NEW_CLE,"label":LABEL,"sources":srcs})

    # Delta parc
    bg_to_cles_global = {}
    for a in doc["adresses"]:
        bgg = a.get("batiment_groupe_id") or ""
        if bgg: bg_to_cles_global.setdefault(bgg, []).append(a.get("cle") or "")
    for bg_ex, cles_p in bgids_visites.items():
        if bg_ex == bg_anc: continue
        all_cles_bg = bg_to_cles_global.get(bg_ex, [])
        restantes = [c for c in all_cles_bg if c not in cles_p]
        bdnb_bg = max([to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in all_cles_bg
                       if c in ad_by_cle], default=0)
        if not restantes and bdnb_bg:
            delta_dedup -= bdnb_bg
            print(f"    bgid ...{bg_ex[-9:]} SUPPRIME bdnb={bdnb_bg} -> -{bdnb_bg}")
        else:
            print(f"    bgid ...{bg_ex[-9:]} conserve via {restantes[:3]}{'...' if len(restantes)>3 else ''}")
    print(f"  DELTA E13 dedup : {delta_dedup}")
    return delta_dedup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not LIGHT.exists(): sys.exit("light absent")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc["coproprietes"]
    md = doc.setdefault("metadata", {})
    by_cle = {(a.get("cle") or ""): a for a in ad}
    co_by_immat = {c.get("numero_immatriculation"): c for c in co
                   if c.get("numero_immatriculation")}

    if md.get("_correctif_12_megas_dl") and not args.apply:
        print("  [info] marker _correctif_12_megas_dl deja present.")

    print("=" * 110)
    print(f"12 MEGAS DL E7-E18  ({'APPLY' if args.apply else 'DRY-RUN'})  -- {len(FIXES)} fixes std + E13 special")
    print("=" * 110)

    total_delta = 0
    log = []

    for fx in FIXES:
        print()
        print(f"--- {fx['vague']} [{fx['tag']}]  ancre={fx['ancre_cle']}  immat={fx['ancre_immat']}")
        a_anc = by_cle.get(fx["ancre_cle"])
        if not a_anc:
            print(f"  [SKIP] ancre absente"); continue
        bg_anc = a_anc.get("batiment_groupe_id") or ""
        co_entry = co_by_immat.get(fx["ancre_immat"])
        if co_entry:
            print(f"  copro snapshot : nom='{co_entry.get('nom_copropriete')}'  "
                  f"lots_tot={co_entry.get('nb_lots_total')}  hab={co_entry.get('nb_lots_habitation')}")

        bdnb_anc = to_int(a_anc.get("nb_log_bdnb"))
        bgids_visites = {}

        for rf in fx.get("re_fuses", []):
            cle = rf["cle"]
            a = by_cle.get(cle)
            if not a:
                print(f"  [SKIP] {cle:36s} ABSENT du light"); continue
            bg_cur = a.get("batiment_groupe_id") or ""
            cur_cible = a.get("_fusion_cible")
            tag = "RE-FUSE" if args.apply else "DRY"
            print(f"  [{tag:7s}] {cle:36s}  bgid ...{bg_cur[-9:]} -> "
                  f"{'...'+bg_anc[-9:] if rf['bgid_change'] else '(inchange)'}  "
                  f"cible='{fx['ancre_cle']}'  ex-cible='{cur_cible}'")
            bgids_visites.setdefault(bg_cur, []).append(cle)
            if not args.apply: continue
            a["_fusion_auto"] = True
            a["_fusion_cible"] = fx["ancre_cle"]
            a["_bdnb_match"] = f"correctif_12megas_{fx['tag']}_re_fuse"
            if rf["bgid_change"]: a["batiment_groupe_id"] = bg_anc
            log.append({"op":"RE-FUSE","cle":cle,"cible":fx["ancre_cle"],
                        "old_cible":cur_cible,"bgid_change":rf["bgid_change"]})

        for inj in fx.get("injects", []):
            cle = inj["cle"]
            if cle in by_cle:
                print(f"  [SKIP-INJECT] {cle} deja present"); continue
            src = by_cle.get(inj["clone_from"])
            if not src:
                print(f"  [SKIP-INJECT] clone_from {inj['clone_from']} absent"); continue
            tag = "INJECT" if args.apply else "DRY"
            print(f"  [{tag:7s}] {cle:36s}  clone_from={inj['clone_from']}  cible='{inj['fcible']}'")
            if not args.apply: continue
            new = {
                "cle": cle, "adresse": cle.replace("|", " "),
                "longitude": src.get("longitude"), "latitude": src.get("latitude"),
                "code_iris": src.get("code_iris"),
                "_coord_source": f"clone_{inj['clone_from']}",
                "dans_majic": False, "sci_proprietaire":"non","sci_nom":"","sci_siren":"",
                "syndic": src.get("syndic"), "_syndic_src": src.get("_syndic_src"),
                "ventes_par_an":{}, "nb_ventes_total":0,
                "nb_log_bdnb": None, "annee_construction": src.get("annee_construction"),
                "classe_dpe": src.get("classe_dpe"),
                "type_batiment": src.get("type_batiment"),
                "type_chauffage": src.get("type_chauffage"),
                "batiment_groupe_id": src.get("batiment_groupe_id"),
                "_bdnb_match": f"correctif_12megas_{fx['tag']}_inject_label",
                "ventes_par_an_logement":{},"nb_ventes_logement":0,
                "taux_rotation_logement":0.0,"classement_rotation_logement":"Fige",
                "_taux_logement_src":"copie_inject",
                "usage_principal_bdnb": src.get("usage_principal_bdnb"),
                "_ilot": src.get("_ilot"),
                "_fusion_auto":True, "_fusion_cible": inj["fcible"],
            }
            ad.append(new); by_cle[cle] = new
            log.append({"op":"INJECT","cle":cle,"fcible":inj["fcible"]})

        if args.apply:
            a_anc["_fusion_auto_label"] = fx["label_ancre"]
            srcs = list(a_anc.get("_fusion_auto_sources") or [])
            all_sources = [rf["cle"] for rf in fx.get("re_fuses",[])] + fx.get("extra_sources",[])
            for inj in fx.get("injects",[]): all_sources.append(inj["cle"])
            for s in all_sources:
                if s not in srcs and by_cle.get(s): srcs.append(s)
            a_anc["_fusion_auto_sources"] = srcs
            print(f"  [LABEL]   {fx['ancre_cle']:36s}  label='{fx['label_ancre']}'")
            log.append({"op":"LABEL","cle":fx["ancre_cle"],"label":fx["label_ancre"],"sources":srcs})

        bg_to_cles_global = {}
        for a in ad:
            bgg = a.get("batiment_groupe_id") or ""
            if bgg: bg_to_cles_global.setdefault(bgg, []).append(a.get("cle") or "")
        delta_dedup = 0
        for bg_ex, cles_p in bgids_visites.items():
            if bg_ex == bg_anc: continue
            all_cles_bg = bg_to_cles_global.get(bg_ex, [])
            restantes = [c for c in all_cles_bg if c not in cles_p]
            bdnb_bg = max([to_int(by_cle[c].get("nb_log_bdnb")) for c in all_cles_bg
                           if c in by_cle], default=0)
            if not restantes and bdnb_bg:
                delta_dedup -= bdnb_bg
                print(f"    bgid ...{bg_ex[-9:]} SUPPRIME bdnb={bdnb_bg} -> -{bdnb_bg}")
        total_delta += delta_dedup
        print(f"    DELTA {fx['vague']} dedup : {delta_dedup}")

    # E13 special
    delta_e13 = special_e13(doc, by_cle, co_by_immat, args, log)
    total_delta += delta_e13

    if args.apply:
        md["_correctif_12_megas_dl"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern":"12 mega-ensembles E7-E18 terrain user (post-audit eclatements top 30)",
            "fixes":[{"id":f["vague"],"tag":f["tag"],"ancre":f["ancre_cle"],
                      "immat":f["ancre_immat"],"label":f["label_ancre"]} for f in FIXES],
            "e13_special":"REBIND copro AA2505634 cle malformee '42A||50 RUE ST MAXIMIN' -> '42|RUE|ST MAXIMIN' + INJECT propre ancre",
            "log":log,
            "delta_parc_dedup_total":total_delta,
        }
        if BAK.exists():
            print(f"  [warn] backup existant -> ecrase: {BAK.name}")
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(doc['adresses'])} adresses, {len(doc['coproprietes'])} coproprietes)")

    print()
    print("=" * 110)
    print(f"TOTAL DELTA dedup : {total_delta:+d} log")
    print("=" * 110)


if __name__ == "__main__":
    main()
