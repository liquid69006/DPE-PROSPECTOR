#!/usr/bin/env python3
"""Apply EMERGENCE LAFAYETTE DL : RE-FUSE 215 BONNEL + 2/4/6 VILLETTE
-> 224 COURS LAFAYETTE (AC7454556 SDC EMERGENCE LAFAYETTE 172 lots).

Preuve : BDNB rel_batiment_groupe_adresse pour bgid JGAH-NP8T-HYRQ
liste 5 cle_interop BAN :
  - 69383_4095_00224 -> 224 Cours Lafayette
  - 69383_1020_00215 -> 215 Rue de Bonnel
  - 69383_7480_00002 -> 2 Rue de la Villette
  - 69383_7480_00004 -> 4 Rue de la Villette
  - 69383_7480_00006 -> 6 Rue de la Villette

Pattern ECLATEMENT faux-matching make_light :
- 215 BONNEL : bgid 7PX7-EGXC-YLCW (=222 LAFAYETTE) via match='gps'
- 2 VILLETTE : bgid HZS6-TQY1-5MFV (=1 VILLETTE) via match='num_voie'
- 4 VILLETTE : bgid LKF1-7KPH-2P9U via match='num_voie'
- 6 VILLETTE : meme bgid 7KPH (fauto vers 4 VILLETTE) - cible a changer

OPS :
- 4 RE-FUSE adresses : bgid switch -> JGAH-NP8T-HYRQ,
  _fusion_auto=True, _fusion_cible='224|COURS|LAFAYETTE',
  _bdnb_match='correctif_emergence_lafayette_re_point',
  _ilot='X' (224 LAFAYETTE est hors polygones KML)
- Label 224 LAFAYETTE : '224 CRS LAFAYETTE / 215 RUE BONNEL / 2/4/6 RUE VILLETTE'
- Pas de propag copro (AC7454556 deja correctement populated dans snapshot :
  nb_lots_total=172, nb_lots_habitation=91, syndic=GALYO)

EFFETS attendus :
- 1354 adresses inchange (4 deviennent FA invisibles UI)
- bgids EGXC/TQY1/7KPH conservent leurs autres adresses (222 LAFAYETTE,
  1 VILLETTE, 5 VILLETTE) -> pas de dedup parc bgid
- Delta parc UI : 0 (RNC habit 91 < BDNB resid 135 -> UI garde BDNB 135 ;
  bgids absorbes conservent occupants -> pas de dedup)
- Hr-actifs UI : -4 (215 BONNEL + 2/4/6 VILLETTE sortent en FA)
- Visibilite terrain : ensemble EMERGENCE LAFAYETTE complet (5 adresses
  BAN regroupees sur l'ancre AC7454556)
"""
import json, sys, shutil, argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.preemergence.bak"

ANCRE = "224|COURS|LAFAYETTE"
ANCRE_BGID_TARGET = "bdnb-bg-JGAH-NP8T-HYRQ"   # bgid de 224 LAFAYETTE (cible)
ANCRE_IMMAT = "AC7454556"
ANCRE_NOM   = "SDC EMERGENCE LAFAYETTE"
ANCRE_ILOT  = "X"
LABEL = "224 CRS LAFAYETTE / 215 RUE BONNEL / 2/4/6 RUE VILLETTE"

# (cle, bgid actuel attendu, old_cible attendu)
RE_FUSES = [
    {"cle": "215|RUE|BONNEL",    "bgid_ex": "bdnb-bg-7PX7-EGXC-YLCW", "old_cible": None},
    {"cle": "2|RUE|VILLETTE",    "bgid_ex": "bdnb-bg-HZS6-TQY1-5MFV", "old_cible": None},
    {"cle": "4|RUE|VILLETTE",    "bgid_ex": "bdnb-bg-LKF1-7KPH-2P9U", "old_cible": None},
    {"cle": "6|RUE|VILLETTE",    "bgid_ex": "bdnb-bg-LKF1-7KPH-2P9U", "old_cible": "4|RUE|VILLETTE"},
]


def to_int(x):
    try: return int(x)
    except Exception: return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply (default: dry-run)")
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

    if md.get("_correctif_emergence_lafayette") and not args.apply:
        print("  [info] marker _correctif_emergence_lafayette deja present.")

    print("=" * 110)
    print(f"EMERGENCE LAFAYETTE DL  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print(f"  ancre : {ANCRE}  bgid={ANCRE_BGID_TARGET}  immat={ANCRE_IMMAT}")
    print("=" * 110)

    # Pre-checks
    a_anc = by_cle.get(ANCRE)
    if not a_anc:
        sys.exit(f"  [abort] ancre absente : {ANCRE}")
    if a_anc.get("batiment_groupe_id") != ANCRE_BGID_TARGET:
        print(f"  [warn] ancre bgid={a_anc.get('batiment_groupe_id')} != attendu {ANCRE_BGID_TARGET}")
    if a_anc.get("numero_immatriculation") != ANCRE_IMMAT:
        print(f"  [warn] ancre immat={a_anc.get('numero_immatriculation')} != attendu {ANCRE_IMMAT}")
    if a_anc.get("_ilot") != ANCRE_ILOT:
        print(f"  [warn] ancre _ilot={a_anc.get('_ilot')!r} != attendu {ANCRE_ILOT!r}")

    co_entry = co_by_immat.get(ANCRE_IMMAT)
    if co_entry:
        print(f"  copro snapshot : nom={co_entry.get('nom_copropriete')!r}  "
              f"lots_tot={co_entry.get('nb_lots_total')}  hab={co_entry.get('nb_lots_habitation')}  "
              f"syndic={co_entry.get('syndic')!r}  (deja populated, pas de propag)")

    bdnb_anc = to_int(a_anc.get("nb_log_bdnb"))
    print(f"  ancre bdnb={bdnb_anc}  (RNC habit {co_entry.get('nb_lots_habitation') if co_entry else '?'})")
    print()

    log = []
    bgids_visites = {}  # bgid_ex -> [cles absorbees]

    for rf in RE_FUSES:
        cle = rf["cle"]
        a = by_cle.get(cle)
        if not a:
            print(f"  [SKIP] {cle:30s} ABSENT du light")
            continue
        bg_cur = a.get("batiment_groupe_id") or ""
        if bg_cur != rf["bgid_ex"]:
            print(f"  [warn] {cle:30s} bgid actuel={bg_cur} != attendu {rf['bgid_ex']}")
        cur_cible = a.get("_fusion_cible")
        if rf["old_cible"] and cur_cible != rf["old_cible"]:
            print(f"  [warn] {cle:30s} cible actuelle={cur_cible!r} != attendue {rf['old_cible']!r}")
        bdnb_rf = to_int(a.get("nb_log_bdnb"))
        ilot_cur = a.get("_ilot")
        bgids_visites.setdefault(bg_cur, []).append(cle)
        print(f"  [{ 'RE-FUSE' if args.apply else 'DRY' }]  {cle:30s}  bgid ...{bg_cur[-9:]} -> "
              f"...{ANCRE_BGID_TARGET[-9:]}  bdnb={bdnb_rf}  ilot {ilot_cur!r} -> {ANCRE_ILOT!r}")

        if not args.apply: continue

        a["batiment_groupe_id"] = ANCRE_BGID_TARGET
        a["_fusion_auto"] = True
        a["_fusion_cible"] = ANCRE
        a["_bdnb_match"]   = "correctif_emergence_lafayette_re_point"
        a["_ilot"] = ANCRE_ILOT
        log.append({"op": "RE-FUSE", "cle": cle,
                    "bgid_from": bg_cur, "bgid_to": ANCRE_BGID_TARGET,
                    "old_cible": cur_cible})

    # Label sur ancre
    if args.apply:
        a_anc["_fusion_auto_label"] = LABEL
        srcs = list(a_anc.get("_fusion_auto_sources") or [])
        for rf in RE_FUSES:
            if rf["cle"] in by_cle and rf["cle"] not in srcs:
                srcs.append(rf["cle"])
        a_anc["_fusion_auto_sources"] = srcs
        print(f"  [LABEL]   {ANCRE:30s}  label='{LABEL}'")
        print(f"            sources={srcs}")
        log.append({"op": "LABEL", "cle": ANCRE, "label": LABEL, "sources": srcs})
    else:
        print(f"  [DRY]     LABEL  {ANCRE:30s}  label='{LABEL}'")

    # Delta parc estime
    print()
    print("  --- Delta parc estime ---")
    # Pour chaque bgid_ex visite, voir si tous ses adresses light s'en vont
    bgids_par_cle = {}
    for a in ad:
        bg = a.get("batiment_groupe_id") or ""
        if bg: bgids_par_cle.setdefault(bg, []).append(a.get("cle"))
    delta_dedup = 0
    for bg_ex, cles_qui_partent in bgids_visites.items():
        all_cles = bgids_par_cle.get(bg_ex, [])
        restantes = [c for c in all_cles if c not in cles_qui_partent]
        # bdnb du bgid (= bdnb de n'importe quelle adresse du bgid, normalement uniforme)
        bdnb_bg = 0
        for c in all_cles:
            a = by_cle.get(c)
            if a and a.get("nb_log_bdnb"):
                bdnb_bg = max(bdnb_bg, to_int(a.get("nb_log_bdnb")))
        if not restantes and bdnb_bg:
            print(f"    bgid ...{bg_ex[-9:]} : SUPPRIME (toutes absorbees), bdnb={bdnb_bg} -> -{bdnb_bg}")
            delta_dedup -= bdnb_bg
        else:
            print(f"    bgid ...{bg_ex[-9:]} : conserve via {restantes} (bdnb_bg={bdnb_bg}) -> 0")
    # Switch BDNB->RNC sur ancre (RNC habit 91 vs BDNB 135 -> RNC perd, UI garde BDNB)
    rnc_habit = co_entry.get("nb_lots_habitation") if co_entry else None
    delta_switch = 0
    if rnc_habit and rnc_habit > bdnb_anc:
        delta_switch = rnc_habit - bdnb_anc
        print(f"    switch BDNB({bdnb_anc}) -> RNC habit({rnc_habit}) : +{delta_switch}")
    else:
        print(f"    switch BDNB({bdnb_anc}) vs RNC habit({rnc_habit}) : RNC <= BDNB -> 0")
    total = delta_dedup + delta_switch
    print(f"    => TOTAL delta : {total:+d} log")

    # Final write + marker
    if args.apply:
        md["_correctif_emergence_lafayette"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern": "ECLATEMENT faux-matching make_light (proximity-snap GPS + num_voie sur cote BAN secondaire) - bgid JGAH-NP8T-HYRQ regroupe 5 cle_interop BAN",
            "preuve": "BDNB rel_batiment_groupe_adresse pour bgid NP8T-HYRQ liste 224 LAF + 215 BON + 2/4/6 VIL",
            "ancre": ANCRE,
            "immat": ANCRE_IMMAT,
            "label": LABEL,
            "ops": "4 RE-FUSE (bgid switch + cible + ilot=X)",
            "log": log,
            "delta_parc_estime": total,
            "particularite": "ancre hors polygones KML (_ilot=X), preserve sur adresses fusees",
            "snapshot_immat": "AC7454556 SDC EMERGENCE LAFAYETTE 172/91, syndic GALYO (deja populated)",
        }
        if BAK.exists():
            print(f"  [warn] backup existant -> ecrase: {BAK.name}")
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(ad)} adresses, {len(co)} coproprietes)")


if __name__ == "__main__":
    main()
