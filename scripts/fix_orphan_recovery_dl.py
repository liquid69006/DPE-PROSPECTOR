#!/usr/bin/env python3
"""Rattachement additif des 8 ventes orphelines DVF du bloc [A] (DL).

MODE ADDITIF STRICT : on ne touche JAMAIS ventes_par_an / nb_ventes_total
(brut). On ne modifie QUE les champs *_logement (strict, filtre habitation) :
  - ventes_par_an_logement
  - nb_ventes_logement
  - taux_rotation_logement
  - classement_rotation_logement
  - _taux_logement_src = 'orphan_suffix_btq_recovery'

VERIF ANTI-DOUBLON (etape 0) - generalisee aux 8 cles :
Pour chaque DVF row trouvee par le match elargi (numof, voie_toks), on
calcule sa cle officielle make_light = (num + B/T/Q, voie_toks). Si elle
matche une AUTRE cle light deja existante -> DOUBLON (la mutation est
deja attribuee a une autre adresse, on ne doit PAS l'ajouter ici).

Sortie :
  - true_orphans : mutations dont la cle officielle == orphan_cle
                    -> rattachables (make_light a manque la jointure)
  - doublons     : mutations attribuees a une autre cle light existante
                    -> exclues du patch (deja comptees ailleurs)
  - free_orphans : mutations dont la cle officielle n'existe nulle part
                    dans light -> potentiellement rattachables au plus
                    proche, mais ABANDONNES (on ne cree pas de nouvelle
                    cle ici)

VEFA detection : par dedup (Date, No disposition, Valeur fonciere), une
mutation = 1 vente, meme si plusieurs rows DVF (multi-lots). On flag
'VEFA candidate' si nombre de lots dans la mutation > 1 (suggere vente
en bloc / programme neuf, traitement special cherrypick_vefa_*).

Usage :
  python scripts/fix_orphan_recovery_dl.py        # DRY-RUN + STOP
  python scripts/fix_orphan_recovery_dl.py apply  # APPLY (apres validation)
"""
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre_orphan_recovery.bak"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
VEFA_PENDING = ROOT / "data" / "_vefa_pending_dl.json"

ANS = ("2021", "2022", "2023", "2024", "2025")
ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else ""


def is_logement(m):
    return str(m.get("Code type local") or "").strip() in ("1", "2")


def yr(m):
    d = m.get("Date mutation") or ""
    return d[-4:] if len(d) >= 4 else "?"


def mut_id(m):
    """Identifiant mutation : (Date, No disposition, Valeur fonciere).
    Une mutation a 1 ligne par lot - dedup necessaire."""
    return (m.get("Date mutation"), m.get("No disposition"),
            m.get("Valeur fonciere"))


def parse_light_num(raw_num):
    """'252B' -> ('252', 'B') ; '42' -> ('42', '') ; '20T' -> ('20', 'T')."""
    m = re.match(r"^(\d+)([A-Z]*)$", (raw_num or "").upper())
    if not m:
        return None, ""
    return m.group(1), m.group(2)


def classer_annuel(t):
    """Memes seuils que fix_taux_logement.py."""
    if t is None:
        return ""
    if t >= 5:
        return "Très actif"
    if t >= 2.5:
        return "Actif"
    if t >= 1:
        return "Modéré"
    return "Figé"


def taux_annuel(n_log, denom):
    if not denom or denom <= 0:
        return None
    return round(n_log / denom / 5 * 1000) / 10


# ---------- Cles a traiter ----------
ORPHAN_CLES = [
    "7B|RUE|PROFESSEUR PAUL SISLEY",
    "42|RUE|ST MAXIMIN",
    "10|PASSAGE|MEYNIS",
    "20T|RUE|GUILLOUD",
    "21A|RUE|STE ANNE DE BARABAN",
    "97B|RUE|DAUPHINE",
    "5B|RUE|MEYNIS",
    "252B|RUE|PAUL BERT",
]


def main():
    apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")
    mode = "APPLY" if apply else "DRY-RUN"

    print("=" * 78)
    print(f"FIX ORPHAN RECOVERY DL  (mode = {mode})")
    print("=" * 78)

    # ---------- Load ----------
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}
    dvf = json.loads(DVF.read_text(encoding="utf-8"))

    print(f"\n  light : {len(ad)} adresses, {len(co_by_cle)} copros")
    print(f"  dvf   : {len(dvf)} mutations brutes")

    # ---------- Index light par id-tuple ----------
    # id = (num_with_suffix_upper, voie_toks). On ignore le TYPE_VOIE
    # pour la jointure (DVF/light parfois divergents : PASSAGE vs PAS).
    light_index = {}  # (num_with_suffix, voie_toks) -> cle light
    for cle in by_cle:
        p = cle.split("|")
        if len(p) != 3:
            continue
        raw_num = p[0].upper()
        vt = toks(p[2])
        if not vt:
            continue
        # premier wins ; collision possible si 2 cles light meme id
        light_index.setdefault((raw_num, vt), cle)

    # ---------- Index DVF logement par (numof, voie_toks) ----------
    dvf_log_by_key = defaultdict(list)
    for m in dvf:
        if not is_logement(m):
            continue
        nv = numof(m.get("No voie"))
        vt = toks(m.get("Voie") or "")
        if not nv or not vt:
            continue
        dvf_log_by_key[(nv, vt)].append(m)

    # ---------- ETAPE 0 : verif anti-doublon par cle ----------
    print()
    print("=" * 78)
    print("[ETAPE 0] Verif anti-doublon (toutes les 8 cles)")
    print("=" * 78)

    results = []  # par cle : dict avec true_orphans / doublons / free_orphans
    for cle in ORPHAN_CLES:
        a = by_cle.get(cle)
        if not a:
            print(f"\n  [SKIP] {cle} : absente du light")
            continue
        p = cle.split("|")
        raw_num_orphan = p[0].upper()
        voie_toks_orphan = toks(p[2])
        num_base, suffix = parse_light_num(raw_num_orphan)
        orphan_id = (raw_num_orphan, voie_toks_orphan)

        rows = dvf_log_by_key.get((num_base, voie_toks_orphan), [])

        # Groupes par id-tuple officiel (= num+B/T/Q, voie_toks)
        by_official = defaultdict(list)
        for row in rows:
            row_btq = (row.get("B/T/Q") or "").strip().upper()
            row_num_suf = numof(row.get("No voie")) + row_btq
            row_voie_toks = toks(row.get("Voie") or "")
            official_id = (row_num_suf, row_voie_toks)
            by_official[official_id].append(row)

        # Dedup par mut_id, par official_id
        true_orphan_muts = {}        # mut_id -> row (gardee, 1er rep)
        doublons_muts = {}           # mut_id -> (row, autre_cle_light)
        free_orphan_muts = {}        # mut_id -> row
        for official_id, official_rows in by_official.items():
            # dedup
            dedup = {}
            for row in official_rows:
                mid = mut_id(row)
                dedup.setdefault(mid, row)
            # classifie
            if official_id == orphan_id:
                # TRUE orphans : la mutation appartient bien a cette cle
                true_orphan_muts.update(dedup)
            else:
                # cherche dans light_index
                other_cle = light_index.get(official_id)
                if other_cle:
                    for mid, row in dedup.items():
                        doublons_muts[mid] = (row, other_cle)
                else:
                    free_orphan_muts.update(dedup)

        # Affichage par cle
        print(f"\n  --- {cle}  (nb_log={a.get('nb_log_bdnb') or 0}) ---")
        print(f"      DVF rows logement matchant (numof={num_base},"
              f" voie={voie_toks_orphan}) : {len(rows)}")
        print(f"      TRUE_ORPHANS (rattachables, official_id == orphan_id)"
              f" : {len(true_orphan_muts)} mutations distinctes")
        print(f"      DOUBLONS (deja attribues a autre light cle) : "
              f"{len(doublons_muts)} mutations distinctes")
        if doublons_muts:
            cle_dist = Counter(c for _, c in doublons_muts.values())
            for c, n in cle_dist.most_common():
                # verif doublon : light[c] a-t-il deja ces mutations comptees ?
                light_other = by_cle.get(c, {})
                vpa_other = light_other.get("ventes_par_an_logement") or {}
                nlog_other = light_other.get("nb_ventes_logement") or 0
                # count par annee des doublons
                doublons_year = Counter(yr(row) for mid, (row, cle2) in doublons_muts.items() if cle2 == c)
                cohere = ""
                for y in ANS:
                    nb_dvf = doublons_year.get(y, 0)
                    nb_light = vpa_other.get(y, 0)
                    if nb_dvf > 0:
                        cohere += f" {y}:{nb_dvf}/{nb_light}"
                print(f"        -> {c:34s} : {n} mutations  light_nb_log={nlog_other} "
                      f"(dvf_doublons/light_par_an : {cohere.strip()})")
        if free_orphan_muts:
            print(f"      FREE_ORPHANS (cle officielle n'existe pas dans light)"
                  f" : {len(free_orphan_muts)} mutations - non rattachees")

        results.append({
            "cle": cle, "a": a, "num_base": num_base, "suffix": suffix,
            "voie_toks": voie_toks_orphan,
            "true_orphans": true_orphan_muts,
            "doublons": doublons_muts,
            "free_orphans": free_orphan_muts,
        })

    # ---------- ETAPE 1 : Dry-run rattachement ----------
    print()
    print("=" * 78)
    print("[ETAPE 1] Dry-run rattachement (true_orphans uniquement)")
    print("=" * 78)

    to_patch = []
    excluded_cles = []
    vefa_pending_records = []   # collecte les VEFA mises en attente
    for r in results:
        cle = r["cle"]
        a = r["a"]
        true_muts = r["true_orphans"]
        if not true_muts:
            excluded_cles.append((cle, "0 true orphans (toutes doublons ou free)"))
            print(f"\n  [EXCLU] {cle} : 0 true orphan -> non patche")
            continue

        # VEFA detection : compter rows par mut_id
        rows_per_mut = defaultdict(int)
        rows_by_mut_examples = defaultdict(list)
        for row in dvf:
            if not is_logement(row):
                continue
            if mut_id(row) in true_muts:
                rows_per_mut[mut_id(row)] += 1
                if len(rows_by_mut_examples[mut_id(row)]) < 5:
                    rows_by_mut_examples[mut_id(row)].append(row)
        vefa_candidates = [mid for mid, n in rows_per_mut.items() if n > 1]

        # OPTION B : on EXCLUT les VEFA du count et on les met en pending
        non_vefa_muts = {mid: row for mid, row in true_muts.items()
                         if mid not in vefa_candidates}
        # Log VEFA pending
        for mid in vefa_candidates:
            ex = rows_by_mut_examples.get(mid, [])
            rep = ex[0] if ex else {}
            vefa_pending_records.append({
                "cle_light": cle,
                "date_mutation": mid[0],
                "no_disposition": mid[1],
                "valeur_fonciere": mid[2],
                "nb_lots_dvf": rows_per_mut[mid],
                "annee": yr(rep),
                "type_local_rep": rep.get("Type local"),
                "lots_dvf": [r.get("Type local") for r in ex],
                "raison": "VEFA candidate (multi-lots same mutation) - "
                          "traitement cherrypick_vefa_* ulterieur",
            })

        # ventes_par_an_logement AVANT / APRES (sans VEFA)
        before = a.get("ventes_par_an_logement") or {}
        before_n = a.get("nb_ventes_logement") or 0
        add_per_year = Counter(yr(row) for mid, row in non_vefa_muts.items())
        after = dict(before)
        for y in ANS:
            after[y] = (before.get(y) or 0) + add_per_year.get(y, 0)
        # garde uniquement annees > 0 (cohere avec make_light)
        after = {y: v for y, v in after.items() if v > 0}
        after_n = sum(after.values())

        # denom pour taux : copro lots prioritaire sinon nb_log_bdnb
        cp = co_by_cle.get(cle)
        denom = (cp.get("nb_lots_habitation") if cp
                 and (cp.get("nb_lots_habitation") or 0) > 0 else None)
        if denom is None:
            denom = a.get("nb_log_bdnb") if (a.get("nb_log_bdnb") or 0) > 0 \
                else None
        t_old = taux_annuel(before_n, denom)
        t_new = taux_annuel(after_n, denom)
        c_old = classer_annuel(t_old)
        c_new = classer_annuel(t_new)

        print(f"\n  +++ {cle}  (nb_log_bdnb={a.get('nb_log_bdnb')}, "
              f"denom={denom}) +++")
        print(f"      AVANT : ventes_par_an_logement={dict(before)}, "
              f"nb_ventes_logement={before_n}, taux={t_old}, classe='{c_old}'")
        print(f"      MUTATIONS true_orphans ({len(true_muts)} distinctes) :")
        for mid, row in sorted(true_muts.items()):
            d, nd, vf = mid
            tl = row.get("Type local") or ""
            n_rows = rows_per_mut[mid]
            if n_rows > 1:
                print(f"        [VEFA-PENDING] {d}  No disp={nd}  vf={vf}  "
                      f"type='{tl[:12]}'  rows={n_rows}  -> _vefa_pending_dl.json")
            else:
                print(f"        [ADD]          {d}  No disp={nd}  vf={vf}  "
                      f"type='{tl[:12]}'  rows={n_rows}")
        if vefa_candidates:
            print(f"      *** {len(vefa_candidates)} VEFA candidates EXCLUES du compte "
                  f"(loggees dans _vefa_pending_dl.json) ***")
        print(f"      MUTATIONS A AJOUTER non-VEFA : {len(non_vefa_muts)}")
        print(f"      APRES : ventes_par_an_logement={after}, "
              f"nb_ventes_logement={after_n}, taux={t_new}, classe='{c_new}'")
        if c_old != c_new:
            print(f"      *** CHANGEMENT CLASSE : '{c_old}' -> '{c_new}' ***")
        print(f"      _taux_logement_src = 'orphan_suffix_btq_recovery'")

        # Si apres exclusion VEFA il ne reste 0 mutations, on EXCLUE la cle aussi
        if len(non_vefa_muts) == 0:
            excluded_cles.append((cle,
                f"toutes mutations sont VEFA ({len(vefa_candidates)} pending), "
                f"rien a ajouter"))
            print(f"      ==> EXCLU du patch (toutes mut = VEFA pending)")
            continue

        to_patch.append({
            "cle": cle, "after_vpa": after, "after_n": after_n,
            "t_new": t_new, "c_new": c_new,
            "c_old": c_old, "t_old": t_old,
            "non_vefa_count": len(non_vefa_muts),
            "vefa_count": len(vefa_candidates),
        })

    # ---------- ETAPE 2 : Backup ----------
    print()
    print("=" * 78)
    print("[ETAPE 2] Backup")
    print("=" * 78)
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  ecrit {BAK.name}  ({BAK.stat().st_size:,} octets)")

    # ---------- Summary ----------
    print()
    print("=" * 78)
    print("SOMMAIRE")
    print("=" * 78)
    print(f"  Cles a patcher       : {len(to_patch)}")
    print(f"  Cles exclues         : {len(excluded_cles)}")
    for c, raison in excluded_cles:
        print(f"    - {c}  ({raison})")
    total_new_mut = sum(r["after_n"] for r in to_patch) - sum(
        (by_cle[r["cle"]].get("nb_ventes_logement") or 0) for r in to_patch
    )
    print(f"  Mutations a ajouter  : {total_new_mut} (non-VEFA uniquement, additif strict)")
    vefa_total = len(vefa_pending_records)
    if vefa_total:
        print(f"  VEFA pending         : {vefa_total} mutations multi-lots "
              f"-> {VEFA_PENDING.name}")

    # ---------- ETAPE 3 : STOP ou APPLY ----------
    if not apply:
        print()
        print("=" * 78)
        print(f"DRY-RUN : STOP. Lance avec 'apply' pour ecrire le light.")
        print(f"Backup deja en place : {BAK.name}")
        print(f"VEFA pending : {vefa_total} sera ecrit dans {VEFA_PENDING.name}")
        print("=" * 78)
        return

    # APPLY
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_orphan_recovery_dl"):
        sys.exit("  [abort] _correctif_orphan_recovery_dl deja present.")

    for r in to_patch:
        a = by_cle[r["cle"]]
        a["ventes_par_an_logement"] = r["after_vpa"]
        a["nb_ventes_logement"] = r["after_n"]
        a["taux_rotation_logement"] = r["t_new"]
        a["classement_rotation_logement"] = r["c_new"]
        a["_taux_logement_src"] = "orphan_suffix_btq_recovery"

    md["_correctif_orphan_recovery_dl"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": ("Rattachement additif DVF orphelines (suffix B/T/Q ou "
                    "ortho), VEFA exclues et mises en pending"),
        "cles_patches": [r["cle"] for r in to_patch],
        "cles_exclues": [{"cle": c, "raison": raison}
                          for c, raison in excluded_cles],
        "mutations_ajoutees_total": total_new_mut,
        "vefa_pending": vefa_total,
        "vefa_pending_file": str(VEFA_PENDING.relative_to(ROOT)),
        "verification": ("anti-doublon official_id == orphan_id, exclu si "
                         "official_id matche autre cle light ; VEFA "
                         "(mut multi-lots) exclues, traitement "
                         "cherrypick_vefa_* ulterieur"),
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\n  [OK] light ecrit avec {len(to_patch)} cles patchees.")

    # Ecrit le fichier VEFA pending
    vefa_doc = {
        "_meta": {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "secteur": "dauphine-lacassagne",
            "source": "fix_orphan_recovery_dl.py apply",
            "purpose": ("VEFA candidates EXCLUES du nb_ventes_logement du "
                         "batch orphan_suffix_btq_recovery. A traiter "
                         "ulterieurement par cherrypick_vefa_* (verifier "
                         "valeur fonciere / surface Carrez, decision "
                         "5lots / neutralise / vraie multi-vente)."),
        },
        "candidates": vefa_pending_records,
    }
    VEFA_PENDING.write_text(json.dumps(vefa_doc, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print(f"  [OK] VEFA pending ecrit : {VEFA_PENDING.name} "
          f"({len(vefa_pending_records)} candidates)")


if __name__ == "__main__":
    main()
