#!/usr/bin/env python3
"""Apply 3 vagues de fixes 6 mega-ensembles DL (LIGHT only, dry-run + apply).

VAGUE 1 (gains massifs) :
  E3 LA VICTORIENNE   : RE-FUSE 15+17 ST VICTORIEN -> 12 ST SIDOINE (AB2206571)
  E4 LE BARABAN 1     : RE-FUSE 10/12/14 JASSERON -> 61 BARABAN (AB2515468)
  E5 JEAN SORNAY      : RE-FUSE 84 CHARIAL -> 76 CHARIAL (AA1694256)
  E6 LAFAYETTE BARABAN: RE-FUSE 34/36/38 BARABAN -> 30 BARABAN (AB3379567) + INJECT 40

VAGUE 2 (corrections fines) :
  E2 ANTOINE CHARIAL  : RE-FUSE 27/29 AUBIGNY + 7/9 TERNOIS -> 28 RICHERAND (AA0358655)
  E1a PAVILLON FLORE  : RE-FUSE 9 ALBERT THOMAS -> 7 (AB0219808)
  E1b PAVILLON FLORE II: RE-FUSE 7B ALBERT THOMAS -> 5 (AB0222935) + detach AG8595613
                          (terrain : 7B = AB0222935 PAVILLON DE FLORE II)

VAGUE 3 (nettoyage) :
  Detache AG8595613 LE DAUPHINE de 7B ALBERT THOMAS (faux match make_light) -
  integre a VAGUE 2 E1b.
"""
import json, sys, shutil, argparse, copy
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre6megas.bak"

# ---------- Fixes specs ----------
FIXES = [
    # =================== VAGUE 1 ===================
    {"vague": 1, "id": "E3", "tag": "victorienne",
     "label_ancre": "12 RUE ST SIDOINE / 4-6-8 RUE CLAUDIUS PIONCHON / "
                    "14-16-18-20 RUE ST SIDOINE / 15-17 RUE ST VICTORIEN",
     "ancre_cle": "12|RUE|ST SIDOINE",
     "ancre_immat": "AB2206571",
     "re_fuses": [
         {"cle": "15|RUE|ST VICTORIEN",  "bgid_change": True, "old_cible": "13|RUE|ST VICTORIEN"},
         {"cle": "17|RUE|ST VICTORIEN",  "bgid_change": True, "old_cible": "16|RUE|ST VICTORIEN"},
     ],
     # cles deja sur le meme bgid (a integrer aux sources/label sans operations bgid)
     "extra_sources": ["4|RUE|CLAUDIUS PIONCHON","6|RUE|CLAUDIUS PIONCHON","8|RUE|CLAUDIUS PIONCHON",
                       "14|RUE|ST SIDOINE","16|RUE|ST SIDOINE","18|RUE|ST SIDOINE","20|RUE|ST SIDOINE"],
     "kv_delete": []},
    {"vague": 1, "id": "E4", "tag": "baraban1",
     "label_ancre": "61-63-65-67-69 RUE BARABAN / 10-12-14 RUE LOUIS JASSERON",
     "ancre_cle": "61|RUE|BARABAN",
     "ancre_immat": "AB2515468",
     "re_fuses": [
         {"cle": "10|RUE|LOUIS JASSERON", "bgid_change": True, "old_cible": "13|RUE|LOUIS JASSERON"},
         {"cle": "12|RUE|LOUIS JASSERON", "bgid_change": True, "old_cible": "13|RUE|LOUIS JASSERON"},
         {"cle": "14|RUE|LOUIS JASSERON", "bgid_change": True, "old_cible": "13|RUE|LOUIS JASSERON"},
     ],
     "extra_sources": ["63|RUE|BARABAN","65|RUE|BARABAN","67|RUE|BARABAN","69|RUE|BARABAN"],
     "kv_delete": []},
    {"vague": 1, "id": "E5", "tag": "jean_sornay",
     "label_ancre": "76-78-78B-80-80B-82-84 RUE ANTOINE CHARIAL / 277-279 RUE PAUL BERT",
     "ancre_cle": "76|RUE|ANTOINE CHARIAL",
     "ancre_immat": "AA1694256",
     "re_fuses": [
         {"cle": "84|RUE|ANTOINE CHARIAL", "bgid_change": True, "old_cible": "86|RUE|ANTOINE CHARIAL"},
     ],
     "extra_sources": ["78|RUE|ANTOINE CHARIAL","78B|RUE|ANTOINE CHARIAL","80|RUE|ANTOINE CHARIAL",
                       "80B|RUE|ANTOINE CHARIAL","82|RUE|ANTOINE CHARIAL",
                       "277|RUE|PAUL BERT","279|RUE|PAUL BERT"],
     "kv_delete": ["80B|RUE|ANTOINE CHARIAL"]},
    {"vague": 1, "id": "E6", "tag": "lafayette_baraban",
     "label_ancre": "30-32-34-36-38-40 RUE BARABAN",
     "ancre_cle": "30|RUE|BARABAN",
     "ancre_immat": "AB3379567",
     "re_fuses": [
         {"cle": "34|RUE|BARABAN", "bgid_change": True, "old_cible": "30|RUE|BARABAN"},
         {"cle": "36|RUE|BARABAN", "bgid_change": True, "old_cible": "37|RUE|BARABAN"},
         {"cle": "38|RUE|BARABAN", "bgid_change": True, "old_cible": "37|RUE|BARABAN"},
     ],
     "extra_sources": ["32|RUE|BARABAN"],
     "injects": [
         {"cle": "40|RUE|BARABAN", "clone_from": "30|RUE|BARABAN", "fcible": "30|RUE|BARABAN"},
     ],
     "kv_delete": []},
    # =================== VAGUE 2 ===================
    {"vague": 2, "id": "E2", "tag": "antoine_charial",
     "label_ancre": "28-30 RUE ETIENNE RICHERAND / 27-29 RUE AUBIGNY / "
                    "7-9-11-13-15-17 RUE TERNOIS",
     "ancre_cle": "28|RUE|ETIENNE RICHERAND",
     "ancre_immat": "AA0358655",
     "re_fuses": [
         {"cle": "27|RUE|AUBIGNY", "bgid_change": True, "old_cible": None},
         {"cle": "29|RUE|AUBIGNY", "bgid_change": True, "old_cible": "27|RUE|AUBIGNY"},
         {"cle": "7|RUE|TERNOIS",  "bgid_change": True, "old_cible": None},
         {"cle": "9|RUE|TERNOIS",  "bgid_change": True, "old_cible": "23|RUE|RIBOUD"},
     ],
     "extra_sources": ["30|RUE|ETIENNE RICHERAND","11|RUE|TERNOIS","13|RUE|TERNOIS",
                       "15|RUE|TERNOIS","17|RUE|TERNOIS"],
     "kv_delete": ["11|RUE|TERNOIS"]},
    {"vague": 2, "id": "E1a", "tag": "pavillon_flore",
     "label_ancre": "7-9 COURS ALBERT THOMAS",
     "ancre_cle": "7|COURS|ALBERT THOMAS",
     "ancre_immat": "AB0219808",
     "re_fuses": [
         {"cle": "9|COURS|ALBERT THOMAS", "bgid_change": True, "old_cible": "7|COURS|ALBERT THOMAS"},
     ],
     "extra_sources": [],
     "kv_delete": []},
    {"vague": 2, "id": "E1b", "tag": "pavillon_flore_ii",
     "label_ancre": "5-5B-7B COURS ALBERT THOMAS",
     "ancre_cle": "5|COURS|ALBERT THOMAS",
     "ancre_immat": "AB0222935",
     "re_fuses": [
         # 7B est sur bgid TH3A (= 7 ALBERT THOMAS), avec immat AG8595613 (LE DAUPHINE faux match).
         # On le bouge vers bgid 26FA (= 5) + detach AG8595613 + cible -> 5.
         {"cle": "7B|COURS|ALBERT THOMAS", "bgid_change": True,
          "old_cible": None, "detach_immat": "AG8595613"},
     ],
     "extra_sources": ["5B|COURS|ALBERT THOMAS"],
     "kv_delete": []},
]


def to_int(x):
    try: return int(x)
    except Exception: return 0


def get_bgid_of(by_cle, cle):
    a = by_cle.get(cle)
    return a.get("batiment_groupe_id") if a else None


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

    if md.get("_correctif_6_megas_dl") and not args.apply:
        print("  [info] marker _correctif_6_megas_dl deja present.")

    print("=" * 110)
    print(f"6 MEGAS DL  ({'APPLY' if args.apply else 'DRY-RUN'})  -- 3 vagues, {len(FIXES)} fixes")
    print("=" * 110)

    total_delta = 0
    log = []

    for fx in FIXES:
        print()
        print(f"--- V{fx['vague']} {fx['id']} [{fx['tag']}]  ancre={fx['ancre_cle']}  immat={fx['ancre_immat']}")
        a_anc = by_cle.get(fx["ancre_cle"])
        if not a_anc:
            print(f"  [SKIP] ancre absente"); continue
        bg_anc = a_anc.get("batiment_groupe_id") or ""
        if a_anc.get("numero_immatriculation") != fx["ancre_immat"]:
            print(f"  [warn] ancre immat actuelle = {a_anc.get('numero_immatriculation')} "
                  f"!= attendu {fx['ancre_immat']}")
        co_entry = co_by_immat.get(fx["ancre_immat"])
        if co_entry:
            print(f"  copro snapshot : nom={co_entry.get('nom_copropriete')!r}  "
                  f"lots_tot={co_entry.get('nb_lots_total')}  hab={co_entry.get('nb_lots_habitation')}")

        bdnb_anc = to_int(a_anc.get("nb_log_bdnb"))
        rnc_h    = to_int(co_entry.get("nb_lots_habitation")) if co_entry else 0
        rnc_t    = to_int(co_entry.get("nb_lots_total")) if co_entry else 0

        # ---- RE-FUSE ----
        bgids_visites = {}   # bgid_ex -> [cles partantes]
        for rf in fx["re_fuses"]:
            cle = rf["cle"]
            a = by_cle.get(cle)
            if not a:
                print(f"  [SKIP] {cle:38s} ABSENT du light")
                continue
            bg_cur = a.get("batiment_groupe_id") or ""
            cur_cible = a.get("_fusion_cible")
            cur_immat = a.get("numero_immatriculation")
            bdnb_rf = to_int(a.get("nb_log_bdnb"))
            tag = "RE-FUSE" if args.apply else "DRY"
            extra = []
            if rf.get("detach_immat"):
                if cur_immat == rf["detach_immat"]:
                    extra.append(f"detach immat={rf['detach_immat']}")
                else:
                    print(f"  [warn] {cle} immat={cur_immat} != detach attendu {rf['detach_immat']}")
            print(f"  [{tag:7s}] {cle:38s}  bgid ...{bg_cur[-9:]} -> "
                  f"{'...'+bg_anc[-9:] if rf['bgid_change'] else '(inchange)'}  "
                  f"cible='{fx['ancre_cle']}'  ex-cible='{cur_cible}'  {';'.join(extra)}")
            bgids_visites.setdefault(bg_cur, []).append(cle)
            if not args.apply: continue
            # apply
            a["_fusion_auto"] = True
            a["_fusion_cible"] = fx["ancre_cle"]
            a["_bdnb_match"] = f"correctif_6megas_{fx['tag']}_re_fuse"
            if rf["bgid_change"]:
                a["batiment_groupe_id"] = bg_anc
            if rf.get("detach_immat") and cur_immat == rf["detach_immat"]:
                a["numero_immatriculation"] = None
                # Suppression du lien copro mais on garde la trace
                a["_detach_immat_ex"] = rf["detach_immat"]
            log.append({"op": "RE-FUSE", "cle": cle, "cible": fx["ancre_cle"],
                        "bgid_change": rf["bgid_change"], "old_cible": cur_cible,
                        "detach_immat": rf.get("detach_immat")})

        # ---- INJECT ----
        for inj in fx.get("injects", []):
            cle = inj["cle"]
            if cle in by_cle:
                print(f"  [SKIP-INJECT] {cle} deja present")
                continue
            src = by_cle.get(inj["clone_from"])
            if not src:
                print(f"  [SKIP-INJECT] clone_from {inj['clone_from']} absent")
                continue
            tag = "INJECT" if args.apply else "DRY"
            print(f"  [{tag:7s}] {cle:38s}  clone_from={inj['clone_from']}  cible='{inj['fcible']}'")
            if not args.apply: continue
            new = {
                "cle": cle, "adresse": cle.replace("|", " "),
                "longitude": src.get("longitude"), "latitude": src.get("latitude"),
                "code_iris": src.get("code_iris"),
                "_coord_source": f"clone_{inj['clone_from']}",
                "dans_majic": False, "sci_proprietaire": "non", "sci_nom": "", "sci_siren": "",
                "syndic": src.get("syndic"), "_syndic_src": src.get("_syndic_src"),
                "ventes_par_an": {}, "nb_ventes_total": 0,
                "nb_log_bdnb": None, "annee_construction": src.get("annee_construction"),
                "classe_dpe": src.get("classe_dpe"),
                "type_batiment": src.get("type_batiment"),
                "type_chauffage": src.get("type_chauffage"),
                "batiment_groupe_id": src.get("batiment_groupe_id"),
                "_bdnb_match": f"correctif_6megas_{fx['tag']}_inject_label",
                "ventes_par_an_logement": {}, "nb_ventes_logement": 0,
                "taux_rotation_logement": 0.0,
                "classement_rotation_logement": "Fige",
                "_taux_logement_src": "copie_inject",
                "usage_principal_bdnb": src.get("usage_principal_bdnb"),
                "_ilot": src.get("_ilot"),
                "_fusion_auto": True, "_fusion_cible": inj["fcible"],
            }
            ad.append(new)
            by_cle[cle] = new
            log.append({"op": "INJECT", "cle": cle, "fcible": inj["fcible"]})

        # ---- Label sur ancre ----
        if args.apply:
            a_anc["_fusion_auto_label"] = fx["label_ancre"]
            srcs = list(a_anc.get("_fusion_auto_sources") or [])
            all_sources = [rf["cle"] for rf in fx["re_fuses"]] + fx.get("extra_sources", [])
            for inj in fx.get("injects", []): all_sources.append(inj["cle"])
            for s in all_sources:
                if s not in srcs and by_cle.get(s):
                    srcs.append(s)
            a_anc["_fusion_auto_sources"] = srcs
            print(f"  [LABEL]   {fx['ancre_cle']:38s}  label='{fx['label_ancre']}'")
            print(f"            sources={srcs}")
            log.append({"op": "LABEL", "cle": fx["ancre_cle"], "label": fx["label_ancre"], "sources": srcs})

        # ---- Delta parc ----
        # Dedup : pour chaque bgid visite, regarde s'il garde des adresses hors-cet-ensemble
        bg_to_cles_global = {}
        for a in ad:
            bgg = a.get("batiment_groupe_id") or ""
            if bgg: bg_to_cles_global.setdefault(bgg, []).append(a.get("cle") or "")

        delta_dedup = 0
        for bg_ex, cles_p in bgids_visites.items():
            if bg_ex == bg_anc: continue
            cles_total = bg_to_cles_global.get(bg_ex, [])
            restantes = [c for c in cles_total if c not in cles_p]
            bdnb_bg = max([to_int(by_cle[c].get("nb_log_bdnb")) for c in cles_total if c in by_cle], default=0)
            if not restantes and bdnb_bg:
                delta_dedup -= bdnb_bg
                print(f"    bgid ...{bg_ex[-9:]} : SUPPRIME -> -{bdnb_bg}")
            else:
                print(f"    bgid ...{bg_ex[-9:]} : conserve via {restantes[:3]}{'...' if len(restantes)>3 else ''} -> 0")

        # Switch BDNB->RNC : effectif actuel = max(snapshot lh, bdnb_anc) ; final = max(snapshot lh, rnc_h, bdnb_anc)
        # Comme snapshot est deja patch (lots_hab populated), pas de switch supplementaire normalement
        cur_eff = max(rnc_h, bdnb_anc)
        # Si snapshot lh < rnc tot (e.g. 61 < 170), on PROPAGE lots_hab = rnc_t pour reveler le parc reel
        # Mais on ne fait pas ca automatiquement - on log juste
        delta_switch = 0
        # Note : sur les 6 fixes, copro deja populated avec lots_hab realiste
        # E1b a snapshot 170/61 - si user veut "170 lots" -> propag a faire en post-fix
        print(f"    DELTA : dedup={delta_dedup}  switch=0  (rnc_h={rnc_h} rnc_t={rnc_t} bdnb_anc={bdnb_anc} eff={cur_eff}) => {delta_dedup:+d} log")
        total_delta += delta_dedup

    if args.apply:
        md["_correctif_6_megas_dl"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern": "6 mega-ensembles terrain user post-audit_eclatements_dl",
            "fixes": [{"vague": f["vague"], "id": f["id"], "tag": f["tag"],
                       "ancre": f["ancre_cle"], "immat": f["ancre_immat"],
                       "label": f["label_ancre"]} for f in FIXES],
            "log": log,
            "delta_parc_dedup_total": total_delta,
            "note": "Les switchs BDNB->RNC sont deja en place via snapshot lots_hab populated."
                    " VAGUE 3 (detach AG8595613 sur 7B) integree a E1b.",
        }
        if BAK.exists():
            print(f"  [warn] backup existant -> ecrase: {BAK.name}")
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(ad)} adresses, {len(co)} coproprietes)")

    print()
    print("=" * 110)
    print(f"TOTAL DELTA dedup : {total_delta:+d} log (les switchs BDNB->RNC dependent algo UI ; "
          f"snapshot deja populated)")
    print("=" * 110)


if __name__ == "__main__":
    main()
