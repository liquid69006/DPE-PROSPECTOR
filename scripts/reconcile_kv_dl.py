#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconciliation banc d'essai (etape 5 chantier pipeline) -- READ-ONLY.

Compare l'etat KV courant d'un secteur aux recommandations AUTO re-derivees
en mode tag-aveugle (_scan_rows_full_<short>.json produit par
_scan_majic_kv_untagged_dl.py --ignore-kv) + overrides sacres.

Definition (validee Yann, jalon 4) :
  auto_attendu(cle) = override.new_tag   si cle dans overrides
                      sinon reco_full[cle]  ("-" => pas de tag,
                                             absent => hors univers scan)

AUCUNE ecriture KV, AUCUN --apply, AUCUN git. Sortie :
  - data/_reconcile_<short>.json
  - resume stdout ASCII-safe.
"""
import sys, os, json, re, argparse
from pathlib import Path
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SECTEURS = ROOT / "data" / "secteurs.json"


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def raw_reco(r, soc_min, mut_min):
    """Re-derive la reco AUTO d'une row SANS la branche override.

    Replique l'echelle de _scan_majic_kv_untagged_dl.py (L419-446) :
      Tertiaire -> bureaux ; (emphy HLM ou soc>=min) -> social|mixte(mut)
      ; 20<=soc<min -> mixte ; mono (top prive >=80% PM ET BDNB) ; sinon '-'.
    copro_non_immat n'est JAMAIS produit par l'echelle brute (override seul).
    """
    usage = r.get("usage") or ""
    soc = r.get("social_pct") or 0.0
    mut = r.get("mut_an_exact") or 0.0
    has_emphy_hlm = bool(r.get("has_emphy_hlm"))
    tpp = r.get("top_prive_pct") or 0
    tppb = r.get("top_prive_pct_bdnb") or 0
    top_prive = r.get("top_prive") or "-"
    if usage == "Tertiaire":
        return "bureaux"
    if has_emphy_hlm or soc >= soc_min:
        return "mixte" if mut >= mut_min else "social"
    if 20 <= soc < soc_min:
        return "mixte"
    if top_prive != "-" and tpp >= 80 and tppb >= 80:
        return "mono"
    return "-"


def parse_rouge_md(p):
    """Recupere les cles listees sous les sections T* de la pile rouge md."""
    txt = load_json_text(p)
    cles = set()
    for line in (txt or "").splitlines():
        m = re.match(r"^-\s+(.+?)\s*$", line)
        if m:
            cles.add(m.group(1))
    return cles


def load_json_text(p):
    p = Path(p)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secteur", default="dauphine-lacassagne")
    ap.add_argument("--full-scan", default=None,
                    help="chemin _scan_rows_full (defaut: deduit du short)")
    args = ap.parse_args()

    cfgall = load_json(SECTEURS)
    cfg = cfgall[args.secteur]
    short = cfg["short"]
    paths = cfg["paths"]
    seuils = cfg["metier"]["seuils"]
    soc_min = seuils["social_pct_min"]
    mut_min = seuils["mut_apt_per_year_min"]

    kv_path = ROOT / paths["kv_local"]
    ov_path = ROOT / paths["social_overrides"]
    light_dir = (ROOT / paths["light"]).parent
    full_path = Path(args.full_scan) if args.full_scan else \
        light_dir / f"_scan_rows_full_{short}.json"
    verte_path = light_dir / f"_pile_verte_{short}.json"
    orange_path = light_dir / f"_pile_orange_{short}.json"
    rouge_path = light_dir / f"_pile_rouge_{short}.md"

    KV = load_json(kv_path, {})
    assigns = KV.get("assignments", {})
    fusions = KV.get("fusions", {})
    overrides_doc = load_json(ov_path, {})
    overrides = {o["cle"]: o for o in overrides_doc.get("overrides", [])}
    full_rows = (load_json(full_path, {}) or {}).get("rows", [])
    full_by = {r["cle"]: r for r in full_rows}
    verte = load_json(verte_path, {})
    verte_cat = {}
    for cat, lst in (verte.get("par_categorie", {}) or {}).items():
        for cle in lst:
            verte_cat[cle] = cat
    orange = load_json(orange_path, {})
    orange_cles = {e["cle"] for sec in ("a_arbitrer", "a_completer")
                   for e in orange.get(sec, [])}
    rouge_cles = parse_rouge_md(rouge_path)

    # cles touchees par une fusion (source ou cible)
    fusion_cles = set(fusions.keys()) | set(fusions.values())

    # ---- auto_attendu ----
    def auto_attendu(cle):
        if cle in overrides:
            return overrides[cle].get("new_tag") or "mixte"
        r = full_by.get(cle)
        if r is None:
            return None          # hors univers scan
        return r.get("reco")     # peut etre "-"

    # ---- bucketisation des 592 KV ----
    buckets = defaultdict(list)
    detail = {}
    for cle, info in assigns.items():
        kvtype = (info or {}).get("type")
        if not kvtype:
            b = "KV_NULL_TYPE"
        elif cle in fusion_cles:
            b = "FUSION"
        elif cle in rouge_cles:
            b = "PULLED_ROUGE"
        elif cle in orange_cles:
            b = "PULLED_ORANGE"
        elif cle not in full_by:
            b = "KV_ONLY_NO_ENTRY"
        else:
            auto = auto_attendu(cle)
            if cle in overrides:
                b = "OVERRIDE_RESOLVED" if auto == kvtype else "RECO_MISMATCH"
            elif auto == "-" or auto is None:
                b = "KV_ONLY_RECO_DASH"
            elif auto == kvtype:
                b = "MATCH"
            else:
                b = "RECO_MISMATCH"
        buckets[b].append(cle)
        detail[cle] = {"kv": kvtype, "auto": auto_attendu(cle),
                       "reco_full": (full_by.get(cle) or {}).get("reco"),
                       "bucket": b}

    # ---- AUTO_ONLY : untagge KV mais reco_full produit un tag ----
    auto_only = []
    for cle, r in full_by.items():
        if cle in assigns and (assigns[cle] or {}).get("type"):
            continue  # deja tague (non-null) -> pas auto_only
        reco = r.get("reco")
        if reco and reco != "-":
            auto_only.append({"cle": cle, "reco_full": reco,
                              "in_orange": cle in orange_cles})

    # ---- Livrable (a) couverture overrides par la pile verte ----
    ov_cov = []
    ov_loadbearing = []
    for cle, o in overrides.items():
        new_tag = o.get("new_tag")
        in_verte = verte_cat.get(cle)
        covered = (in_verte == new_tag)
        r = full_by.get(cle)
        raw = raw_reco(r, soc_min, mut_min) if r else None
        lb = (raw is not None and raw != new_tag)
        ov_cov.append({"cle": cle, "new_tag": new_tag,
                       "verte_cat": in_verte, "covered": covered,
                       "raw_reco": raw, "load_bearing": lb,
                       "in_scan": r is not None})
        if lb:
            ov_loadbearing.append({"cle": cle, "raw_reco": raw,
                                   "new_tag": new_tag})

    # ---- Livrable (b) where-did-it-go sur les 592 (non-perte) ----
    wdig = Counter()
    wdig_detail = defaultdict(list)
    for cle, info in assigns.items():
        kvtype = (info or {}).get("type")
        if cle in rouge_cles:
            where = "aspire_rouge"
        elif cle in orange_cles:
            where = "aspire_orange"
        elif verte_cat.get(cle) == kvtype:
            where = "verte_meme_cat"
        elif cle in verte_cat:
            where = "verte_autre_cat"
        else:
            where = "absent_verte"
        wdig[where] += 1
        if where in ("verte_autre_cat", "absent_verte"):
            wdig_detail[where].append(
                {"cle": cle, "kv": kvtype, "verte_cat": verte_cat.get(cle)})

    # ---- denominateurs honnetes ----
    n_total = len(assigns)
    n_null = len(buckets["KV_NULL_TYPE"])
    n_fusion = len(buckets["FUSION"])
    n_orange = len(buckets["PULLED_ORANGE"])
    n_rouge = len(buckets["PULLED_ROUGE"])
    perimetre = n_total - n_null - n_fusion - n_orange - n_rouge
    n_match = len(buckets["MATCH"])
    n_ovres = len(buckets["OVERRIDE_RESOLVED"])
    n_noentry = len(buckets["KV_ONLY_NO_ENTRY"])
    n_dash = len(buckets["KV_ONLY_RECO_DASH"])
    n_mismatch = len(buckets["RECO_MISMATCH"])
    rederivable = perimetre - n_noentry - n_dash

    def pct(a, b):
        return round(a * 100.0 / b, 1) if b else 0.0

    # alerte : override aspire (ne devrait pas, §5 entrees sacrees)
    ov_pulled = [c for c in overrides
                 if c in orange_cles or c in rouge_cles]

    out = {
        "secteur": args.secteur, "short": short,
        "sources": {
            "kv_assignments": n_total, "fusions": len(fusions),
            "overrides": len(overrides), "full_scan_rows": len(full_rows),
            "orange_cles": len(orange_cles), "rouge_cles": len(rouge_cles),
        },
        "buckets": {k: len(v) for k, v in sorted(buckets.items())},
        "buckets_cles": {k: sorted(v) for k, v in buckets.items()},
        "perimetre": {
            "total_kv": n_total, "moins_null": n_null,
            "moins_fusion": n_fusion, "moins_pulled_orange": n_orange,
            "moins_pulled_rouge": n_rouge, "perimetre": perimetre,
            "dont_no_entry": n_noentry, "dont_reco_dash": n_dash,
            "rederivable": rederivable,
        },
        "taux": {
            "reproductibilite_strict_pct": pct(n_match, perimetre),
            "repro_avec_overrides_pct": pct(n_match + n_ovres, perimetre),
            "repro_sur_rederivable_pct": pct(n_match + n_ovres, rederivable),
        },
        "auto_only": sorted(auto_only, key=lambda x: x["cle"]),
        "auto_only_count": len(auto_only),
        "auto_only_dist": dict(Counter(a["reco_full"] for a in auto_only)),
        "overrides_couverture": sorted(ov_cov, key=lambda x: x["cle"]),
        "overrides_load_bearing": sorted(ov_loadbearing,
                                         key=lambda x: x["cle"]),
        "where_did_it_go": dict(wdig),
        "where_did_it_go_detail": {k: v for k, v in wdig_detail.items()},
        "alerte_override_pulled": sorted(ov_pulled),
        "reco_full_dist_kv_couvertes": dict(Counter(
            (full_by.get(c) or {}).get("reco")
            for c in assigns if c in full_by)),
    }
    out_path = ROOT / "data" / f"_reconcile_{short}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # ================= RESUME STDOUT (ASCII-safe) =================
    L = "=" * 72
    print(L)
    print(f"RECONCILIATION KV <-> AUTO (tag-aveugle) -- secteur={args.secteur}")
    print(L)
    s = out["sources"]
    print(f"  KV assignments : {s['kv_assignments']}   fusions : {s['fusions']}"
          f"   overrides : {s['overrides']}")
    print(f"  full_scan rows : {s['full_scan_rows']}   orange : "
          f"{s['orange_cles']}   rouge : {s['rouge_cles']}")
    print()
    print("--- BUCKETS (partition des 592 KV) ---")
    order = ["MATCH", "OVERRIDE_RESOLVED", "RECO_MISMATCH",
             "KV_ONLY_RECO_DASH", "KV_ONLY_NO_ENTRY",
             "KV_NULL_TYPE", "FUSION", "PULLED_ORANGE", "PULLED_ROUGE"]
    tot = 0
    for k in order:
        n = len(buckets.get(k, []))
        tot += n
        print(f"   {k:20s} : {n:4d}")
    print(f"   {'TOTAL':20s} : {tot:4d}  (attendu {n_total})")
    print()
    print("--- PERIMETRE & TAUX (denominateurs honnetes) ---")
    p = out["perimetre"]
    print(f"   perimetre = {n_total} - null({n_null}) - fusion({n_fusion})"
          f" - orange({n_orange}) - rouge({n_rouge}) = {perimetre}")
    print(f"     dont KV_ONLY_NO_ENTRY (FA-phantom)  : {n_noentry}")
    print(f"     dont KV_ONLY_RECO_DASH              : {n_dash}")
    print(f"     re-derivable (perimetre - ces 2)    : {rederivable}")
    t = out["taux"]
    print(f"   reproductibilite STRICT   MATCH/perim       : "
          f"{t['reproductibilite_strict_pct']}%  ({n_match}/{perimetre})")
    print(f"   + overrides (MATCH+OVR)/perim               : "
          f"{t['repro_avec_overrides_pct']}%  "
          f"({n_match + n_ovres}/{perimetre})")
    print(f"   sur re-derivable (MATCH+OVR)/rederivable     : "
          f"{t['repro_sur_rederivable_pct']}%  "
          f"({n_match + n_ovres}/{rederivable})")
    print()
    print("--- AUTO_ONLY (tags qu'un rerun ECRIRAIT en KV) ---")
    print(f"   total : {len(auto_only)}   distribution : "
          f"{out['auto_only_dist']}")
    n_ao_orange = sum(1 for a in auto_only if a["in_orange"])
    print(f"   dont deja en pile orange (a arbitrer) : {n_ao_orange}")
    print()
    print("--- OVERRIDES : couverture verte + load-bearing ---")
    n_cov = sum(1 for o in ov_cov if o["covered"])
    print(f"   couverts par pile verte sous new_tag : {n_cov}/"
          f"{len(overrides)}")
    n_inscan = sum(1 for o in ov_cov if o["in_scan"])
    print(f"   presents dans full_scan              : {n_inscan}/"
          f"{len(overrides)}")
    print(f"   LOAD-BEARING (raw_reco != new_tag)   : "
          f"{len(ov_loadbearing)}/{n_inscan}")
    for o in ov_loadbearing:
        print(f"      {o['cle']:30s} raw={o['raw_reco']:14s} -> "
              f"new_tag={o['new_tag']}")
    if ov_pulled:
        print(f"   !! ALERTE override aspire orange/rouge : {ov_pulled}")
    print()
    print("--- (b) NON-PERTE des 592 : where-did-it-go ---")
    for k, v in sorted(wdig.items(), key=lambda x: -x[1]):
        print(f"   {k:18s} : {v}")
    print()
    print(f"[json] ecrit -> {out_path.relative_to(ROOT)}")
    print(L)


if __name__ == "__main__":
    main()
