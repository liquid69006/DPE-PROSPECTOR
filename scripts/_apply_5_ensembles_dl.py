#!/usr/bin/env python3
"""Apply 5 fixes ensembles immobiliers DL (LIGHT only, dry-run + apply).

FIX 1 #2  RE-FUSE 15+13 RICHERAND -> 36 ST ANTOINE (AB1367051 LE LAFAYETTE, 266 lots)
FIX 2 #4  RE-FUSE 125 DAUPHINE     -> 228 FELIX FAURE (AB5933841 LE THESEE-THETIS, 114)
FIX 3 #3  RE-FUSE 7 METALLURGIE    -> 180 FELIX FAURE (AA1827179 LE CLOS JARDIN, 114)
FIX 4 #5  REBIND  93 BELLECOMBE    -> 4 TERNOIS (94->4, ETIQUETAGE multi-parcelle Fondary)
FIX 5 #1  Uniformize label 3/5/7 MAURICE FLANDIN (5 cible->3, label 3 etendu)

Tous fixes parc-impactants utilisent bgid switch + propag immat sur copro (enrichit
snapshot lots_tot None -> RNC live) pour que algo UI bgRncLots+bgBdnbResid materialise
le switch BDNB->RNC sur l'ancre + suppression du bgid hr.

Conventions :
- Adresses hr-actif : _fusion_auto=True + _fusion_cible=<cle> + bgid switch +
  _bdnb_match='correctif_5ensdl_*'
- Adresses ancre : _fusion_auto_label=<LABEL> + _fusion_auto_sources=[...]
- Copro entries : enrichis depuis RNC live (nom + lots_tot) si snapshot None
- Backup : data/secteur_dauphine_lacassagne_light.json.pre5ensdl.bak
- Metadata marker : doc.metadata._correctif_5_ensembles_dl
"""
import json, sys, shutil, argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre5ensdl.bak"


def to_int(x):
    try: return int(x)
    except Exception: return 0


# -------------------------------------------------------------------------
# Specs des 5 fixes (cle = cle_adresse hr-actif a re-fuser ; ancre = pivot)
# -------------------------------------------------------------------------
LABEL_F1 = "36 RUE ST ANTOINE / 13/15 RUE ETIENNE RICHERAND"
LABEL_F2 = "228/230 AV FELIX FAURE / 125 RUE DAUPHINE"
LABEL_F3 = "180 AV FELIX FAURE / 7 RUE METALLURGIE"
LABEL_F4 = "4/6 RUE TERNOIS / 93 RUE BELLECOMBE / 18 RUE ST ANTOINE"
LABEL_F5 = "3/5/7 RUE MAURICE FLANDIN"

FIXES = [
    {
        "id": 1, "tag": "f1_lafayette",
        "ancre_cle": "36|RUE|ST ANTOINE",
        "ancre_immat": "AB1367051",
        "ancre_nom": "LE LAFAYETTE",
        "ancre_lots_tot": 266,
        "label": LABEL_F1,
        "re_fuses": [
            {"cle": "15|RUE|ETIENNE RICHERAND", "bgid_change": True},
            {"cle": "13|RUE|ETIENNE RICHERAND", "bgid_change": True,
             "old_cible": "15|RUE|ETIENNE RICHERAND"},
        ],
        "kv_delete": ["15|RUE|ETIENNE RICHERAND"],
        "preuve": "RNC live AB1367051 adresse_complementaire_1='15 r etienne richerand'",
    },
    {
        "id": 2, "tag": "f2_thesee",
        "ancre_cle": "228|AVENUE|FELIX FAURE",
        "ancre_immat": "AB5933841",
        "ancre_nom": "LE THESEE-THETIS",
        "ancre_lots_tot": 114,
        "label": LABEL_F2,
        "re_fuses": [
            {"cle": "125|RUE|DAUPHINE", "bgid_change": True},
        ],
        "ancre_existing_label_cles": ["230|AVENUE|FELIX FAURE"],  # 230 deja fauto
        "kv_delete": ["125|RUE|DAUPHINE"],
        "preuve": "RNC live AB5933841 adresse_complementaire_1='125 r du dauphine'",
    },
    {
        "id": 3, "tag": "f3_clos_jardin",
        "ancre_cle": "180|AVENUE|FELIX FAURE",
        "ancre_immat": "AA1827179",
        "ancre_nom": "LE CLOS JARDIN",
        "ancre_lots_tot": 114,
        "label": LABEL_F3,
        "re_fuses": [
            {"cle": "7|RUE|METALLURGIE", "bgid_change": True},
        ],
        "kv_delete": ["7|RUE|METALLURGIE"],
        "preuve": "Terrain user + parcelle DO/0010 commune (pattern Cambronne)",
    },
    {
        "id": 4, "tag": "f4_rebind_bellecombe",
        "ancre_cle": "4|RUE|TERNOIS",
        "ancre_immat": None,           # pas d'immat (ETIQUETAGE pur)
        "ancre_nom": None,
        "ancre_lots_tot": None,
        "label": LABEL_F4,
        "re_fuses": [
            {"cle": "93|RUE|BELLECOMBE", "bgid_change": False,
             "old_cible": "94|RUE|BELLECOMBE"},
        ],
        "ancre_existing_label_cles": ["18|RUE|ST ANTOINE"],   # 18 deja label etendu
        "kv_delete": [],
        "preuve": "Terrain user (label 18 ST ANTOINE deja inclut 93 BELLECOMBE)",
    },
    {
        "id": 5, "tag": "f5_flandin_label",
        "ancre_cle": "3|RUE|MAURICE FLANDIN",
        "ancre_immat": None,
        "ancre_nom": None,
        "ancre_lots_tot": None,
        "label": LABEL_F5,
        "re_fuses": [
            {"cle": "5|RUE|MAURICE FLANDIN", "bgid_change": False,
             "old_cible": "3|RUE|MAURICE FLANDIN"},
            {"cle": "7|RUE|MAURICE FLANDIN", "bgid_change": False,
             "old_cible": "3/5/7 RUE MAURICE FLANDIN"},
        ],
        "kv_delete": [],
        "preuve": "Coherence labels (5 cible='3', 7 cible='3/5/7' - uniformiser ancre)",
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply changes (default: dry-run)")
    args = ap.parse_args()

    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad  = doc["adresses"]
    co  = doc["coproprietes"]
    md  = doc.setdefault("metadata", {})
    by_cle = {(a.get("cle") or ""): a for a in ad}
    co_by_immat = {c.get("numero_immatriculation"): c for c in co
                   if c.get("numero_immatriculation")}

    if md.get("_correctif_5_ensembles_dl") and not args.apply:
        print("  [info] marker _correctif_5_ensembles_dl deja present.")

    print("=" * 110)
    print(f"5 ENSEMBLES DL  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 110)

    total_delta = 0
    log = []  # actions appliquees (pour metadata)

    for fx in FIXES:
        print()
        print(f"--- FIX {fx['id']}  [{fx['tag']}]  ancre={fx['ancre_cle']}  "
              f"immat={fx['ancre_immat'] or '-'}")
        print(f"    preuve : {fx['preuve']}")

        a_anc = by_cle.get(fx["ancre_cle"])
        if not a_anc:
            print(f"    [SKIP] ancre absente : {fx['ancre_cle']}")
            continue
        bg_anc = a_anc.get("batiment_groupe_id") or ""

        # Verif immat coherent
        co_entry = None
        if fx["ancre_immat"]:
            if a_anc.get("numero_immatriculation") != fx["ancre_immat"]:
                print(f"    [warn] ancre immat={a_anc.get('numero_immatriculation')} "
                      f"!= attendu {fx['ancre_immat']}")
            co_entry = co_by_immat.get(fx["ancre_immat"])
            if not co_entry:
                print(f"    [SKIP] copro entry {fx['ancre_immat']} absente")
                continue

        # Calcul delta par fix : pour chaque re_fuse avec bgid_change,
        # le bgid de l'hr est absorbe. Pour l'ancre, switch BDNB->RNC si lots fournis.
        delta_fix = 0
        bdnb_anc = to_int(a_anc.get("nb_log_bdnb"))

        # Bgids absorbed (uniques)
        bgids_absorbed = set()
        for rf in fx["re_fuses"]:
            if not rf.get("bgid_change"): continue
            a_rf = by_cle.get(rf["cle"])
            if not a_rf: continue
            bg_rf = a_rf.get("batiment_groupe_id") or ""
            if bg_rf and bg_rf != bg_anc:
                bgids_absorbed.add(bg_rf)
        # Estimation : chaque bgid absorbe contribue son bdnb (1 fois meme si 2 adresses)
        # On prend le bdnb max par bgid (devrait etre identique entre adresses meme bgid)
        bdnb_per_bg_abs = {}
        for rf in fx["re_fuses"]:
            if not rf.get("bgid_change"): continue
            a_rf = by_cle.get(rf["cle"])
            if not a_rf: continue
            bg_rf = a_rf.get("batiment_groupe_id") or ""
            if bg_rf in bgids_absorbed:
                bdnb_per_bg_abs[bg_rf] = max(bdnb_per_bg_abs.get(bg_rf, 0),
                                              to_int(a_rf.get("nb_log_bdnb")))
        delta_dedup = -sum(bdnb_per_bg_abs.values())

        # Switch BDNB->RNC sur ancre
        delta_switch = 0
        if fx["ancre_immat"] and fx["ancre_lots_tot"]:
            # actuel : si copro lots None -> fallback BDNB
            cur_lots = co_entry.get("nombre_total_lots")
            cur_eff = cur_lots if cur_lots else bdnb_anc
            delta_switch = fx["ancre_lots_tot"] - cur_eff
        delta_fix = delta_dedup + delta_switch
        total_delta += delta_fix
        print(f"    delta : dedup={delta_dedup} (bgids absorbes={sorted(bgids_absorbed)})  "
              f"switch BDNB->RNC={delta_switch}  -> {delta_fix:+d} log")

        if not args.apply:
            # Dry-run : on affiche juste ce qu'on ferait
            for rf in fx["re_fuses"]:
                a_rf = by_cle.get(rf["cle"])
                if not a_rf:
                    print(f"      [DRY] {rf['cle']} ABSENT - skip"); continue
                bg_rf = a_rf.get("batiment_groupe_id") or ""
                print(f"      [DRY] RE-FUSE  {rf['cle']:38s}  "
                      f"bgid {('...'+bg_rf[-9:]) if bg_rf else '-'} "
                      f"{'-> ...'+bg_anc[-9:] if rf.get('bgid_change') else '(inchange)'}  "
                      f"cible='{fx['ancre_cle']}'")
                if rf.get("old_cible"):
                    print(f"            (ex-cible='{rf['old_cible']}')")
            print(f"      [DRY] LABEL ancre {fx['ancre_cle']:38s}  "
                  f"label='{fx['label']}'")
            if fx["ancre_immat"] and fx["ancre_lots_tot"]:
                print(f"      [DRY] PROPAG copro {fx['ancre_immat']}  "
                      f"nom='{fx['ancre_nom']}'  nombre_total_lots={fx['ancre_lots_tot']} "
                      f"(actuel : nom={co_entry.get('nom_usage_copropriete')}, "
                      f"lots={co_entry.get('nombre_total_lots')})")
            continue

        # ---------- APPLY ----------
        for rf in fx["re_fuses"]:
            a_rf = by_cle.get(rf["cle"])
            if not a_rf:
                print(f"      [WARN] {rf['cle']} ABSENT - skip"); continue
            bg_rf_before = a_rf.get("batiment_groupe_id") or ""
            a_rf["_fusion_auto"] = True
            a_rf["_fusion_cible"] = fx["ancre_cle"]
            a_rf["_bdnb_match"] = f"correctif_5ensdl_{fx['tag']}_re_fuse"
            if rf.get("bgid_change"):
                a_rf["batiment_groupe_id"] = bg_anc
            print(f"      [RE-FUSE] {rf['cle']:38s}  "
                  f"bgid {('...'+bg_rf_before[-9:]) if bg_rf_before else '-'} "
                  f"-> {('...'+bg_anc[-9:]) if rf.get('bgid_change') else '(inchange)'}  "
                  f"cible='{fx['ancre_cle']}'")
            log.append({"op": "RE-FUSE", "cle": rf["cle"], "cible": fx["ancre_cle"],
                        "bgid_change": rf.get("bgid_change", False),
                        "old_cible": rf.get("old_cible")})

        # Label ancre
        a_anc["_fusion_auto_label"] = fx["label"]
        srcs = list(a_anc.get("_fusion_auto_sources") or [])
        # Sources cibles : les hr fauto + (si applicable) les anciennes hr deja fauto
        all_srcs = [rf["cle"] for rf in fx["re_fuses"]]
        all_srcs += list(fx.get("ancre_existing_label_cles") or [])
        for s in all_srcs:
            if s not in srcs: srcs.append(s)
        a_anc["_fusion_auto_sources"] = srcs
        print(f"      [LABEL]   {fx['ancre_cle']:38s}  label='{fx['label']}'  sources={srcs}")
        log.append({"op": "LABEL", "cle": fx["ancre_cle"], "label": fx["label"],
                    "sources": srcs})

        # Propagation copro snapshot (enrichissement lots/nom)
        if fx["ancre_immat"] and co_entry is not None:
            patched = []
            if fx["ancre_nom"] and not co_entry.get("nom_usage_copropriete"):
                co_entry["nom_usage_copropriete"] = fx["ancre_nom"]
                patched.append(f"nom='{fx['ancre_nom']}'")
            if fx["ancre_lots_tot"] and not co_entry.get("nombre_total_lots"):
                co_entry["nombre_total_lots"] = fx["ancre_lots_tot"]
                patched.append(f"nombre_total_lots={fx['ancre_lots_tot']}")
            # nb_lots_habitation : fallback sur lots_tot si hab inconnu
            if fx["ancre_lots_tot"] and not co_entry.get("nombre_lots_usage_habitation"):
                co_entry["nombre_lots_usage_habitation"] = fx["ancre_lots_tot"]
                co_entry["_lots_habit_src"] = "rnc_total_fallback_5ensdl"
                patched.append(f"nb_lots_habit_fallback={fx['ancre_lots_tot']}")
            if patched:
                print(f"      [PROPAG]  copro {fx['ancre_immat']}  {' / '.join(patched)}")
                log.append({"op": "PROPAG_COPRO", "immat": fx["ancre_immat"],
                            "patched": patched})

    # Final write + marker
    if args.apply:
        md["_correctif_5_ensembles_dl"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern": "5 ensembles immobiliers DL terrain user (RE-FUSE Cambronne/Fondary + ETIQUETAGE/REBIND)",
            "fixes": [
                {"id": f["id"], "tag": f["tag"], "ancre": f["ancre_cle"],
                 "immat": f["ancre_immat"], "lots_tot_rnc": f["ancre_lots_tot"],
                 "preuve": f["preuve"], "label": f["label"]}
                for f in FIXES
            ],
            "log": log,
            "delta_parc_estime_total": total_delta,
        }
        # Backup AVANT ecriture (mais APRES dry-run)
        if BAK.exists():
            print(f"  [warn] backup existant -> ecrase: {BAK.name}")
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(ad)} adresses, {len(co)} coproprietes)")

    print()
    print("=" * 110)
    print(f"TOTAL DELTA PARC estime (5 fixes) : {total_delta:+d} log")
    print("=" * 110)


if __name__ == "__main__":
    main()
