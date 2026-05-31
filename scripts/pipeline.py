#!/usr/bin/env python3
"""Orchestrateur pipeline de qualification - READ-ONLY (dry-run par defaut).

Agrege les sorties en 3 PILES (PIPELINE.md §7 etape 4) :
  VERTE  : adresses certifiees auto (tag KV clair OU reco scan), par categorie.
  ORANGE : a arbitrer = { a_arbitrer : bgid confirmed + noms ambigus + zones
           grises ZG1/ZG2 ; a_completer : bgid live_required/indetermine }.
  ROUGE  : anomalies donnees (T1 FA+ventes sans ancrage, T2 tag KV orphelin,
           T3 cle malformee, T4 override orphelin). Attendue PETITE (<10).

Produit 4 fichiers : _pile_verte_<short>.json, _pile_orange_<short>.json,
_pile_orange_<short>.md, _pile_rouge_<short>.md. Prepare (sans poser) le tag
KV `a_arbitrer` ; --apply present mais NON utilise a ce jalon (jalon 4).

Ordre : charge contexte -> _scan --json (sous-process, reco + metriques) ->
lit sorties detecteurs A/B -> trie 3 piles -> ecrit.

Usage : python scripts/pipeline.py --secteur <slug> [--apply]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from secteur_config import load_secteur, slugs

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
# Zones grises (memes seuils que _scan ; bornes "borderline" en dur)
ZG_MIXTE_LOW = 50      # social_pct dans [50, social_pct_min) + mut < seuil
ZG_MONO_LOW = 75       # top_prive_pct dans [75, 80) avec couverture BDNB >= 75


def maps_link(lat, lon, adresse):
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps?q={lat},{lon}"
    return "https://www.google.com/maps?q=" + (adresse or "").replace(" ", "+")


def parse_cle(cle):
    p = (cle or "").split("|")
    if len(p) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", p[0].strip().upper())
    return (int(m.group(1)), p[1], p[2]) if m else None


def load_json(path, default=None):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return default


# ---------- contexte ----------
def load_context(cfg):
    light = json.loads(cfg.light.read_text(encoding="utf-8"))
    by_cle = {(a.get("cle") or ""): a for a in light["adresses"]}
    kv = json.loads(cfg.kv_local.read_text(encoding="utf-8"))
    enrich = {r["cle"]: r for r in (load_json(cfg.enrich_majic, {}) or {}).get("results", [])}
    ov = load_json(cfg.social_overrides, {}) or {}
    override_cles = {x.get("cle") for x in ov.get("overrides", []) if x.get("cle")}
    # M2 : cles nom_ambigu tranchees non-social (liste vide si fichier/chemin
    # absent -> repli gracieux, secteur-agnostique).
    nom_resolus = set()
    if getattr(cfg, "nom_ambigu_resolus", None):
        nom_resolus = {x.get("cle") for x in (load_json(cfg.nom_ambigu_resolus, []) or [])
                       if x.get("cle")}
    detA = load_json(cfg.light.parent / f"_detect_bgid_suspects_{cfg.short}.json")
    detB = load_json(cfg.light.parent / f"_detect_noms_ambigus_{cfg.short}.json")
    if detA is None or detB is None:
        sys.exit("  [abort] sorties detecteurs absentes - lance d'abord "
                 "_detect_bgid_suspects.py et _detect_noms_ambigus.py "
                 f"(--secteur {cfg.slug}).")
    co_cles = [c.get("cle_adresse") or "" for c in light.get("coproprietes", [])]
    return {
        "adresses": light["adresses"], "by_cle": by_cle, "co_cles": co_cles,
        "assignments": kv.get("assignments", {}), "enrich": enrich,
        "override_cles": override_cles, "nom_resolus": nom_resolus,
        "detA": detA, "detB": detB,
    }


def run_scan_json(cfg):
    """Lance _scan --json en sous-process -> rows[] (reco + metriques)."""
    out = cfg.light.parent / f"_scan_rows_{cfg.short}.json"
    subprocess.run([sys.executable, str(SCRIPT_DIR / "_scan_majic_kv_untagged_dl.py"),
                    "--secteur", cfg.slug, "--json", str(out)],
                   check=True, capture_output=True, text=True)
    return {r["cle"]: r for r in (load_json(out, {}) or {}).get("rows", [])}


# ---------- piles ----------
def build_pile_orange(ctx, by_cle, scan_rows, cfg):
    a_arbitrer, a_completer = [], []

    def coords(cle):
        a = by_cle.get(cle, {})
        return a.get("latitude"), a.get("longitude"), a.get("adresse") or cle.replace("|", " ")

    # bgid suspects
    for s in ctx["detA"].get("suspects", []):
        cle = s["cle"]
        lat, lon, adr = coords(cle)
        base = {"cle": cle, "adresse": adr, "lat": lat, "lon": lon,
                "current_kv_tag": (ctx["assignments"].get(cle) or {}).get("type"),
                "maps": maps_link(lat, lon, adr)}
        if s.get("verdict") == "confirmed":
            base.update({"type": "bgid_confirmed", "source": "detect_bgid",
                         "data": {k: s.get(k) for k in
                                  ("bgid_light", "bgid_ban", "signaux",
                                   "bgid_group_voisins", "cross_rnc", "score")}})
            a_arbitrer.append(base)
        elif s.get("verdict") in ("live_required", "live_indetermine"):
            base.update({"type": "bgid_" + s["verdict"], "source": "detect_bgid",
                         "data": {"signaux": s.get("signaux"),
                                  "bgid_light": s.get("bgid_light")}})
            a_completer.append(base)

    # noms ambigus
    for n in ctx["detB"].get("ambigus", []):
        cle = n["cle"]
        kv_tag = (ctx["assignments"].get(cle) or {}).get("type")
        # M1 : cle deja DECIDEE (tag KV pose, hors piles en attente) -> ne pas
        # re-arbitrer (ex. 227 FELIX FAURE=cible_0vente, 14 FLANDIN=bureaux).
        if kv_tag and kv_tag not in ("a_arbitrer", "a_completer"):
            continue
        # M2 : cle untagged mais explicitement tranchee non-social (liste resolus).
        if cle in ctx.get("nom_resolus", set()):
            continue
        lat, lon, adr = coords(cle)
        a_arbitrer.append({
            "cle": cle, "adresse": adr, "lat": lat, "lon": lon,
            "current_kv_tag": kv_tag,
            "maps": maps_link(lat, lon, adr),
            "type": "nom_ambigu", "source": "detect_noms_ambigus",
            "data": {**{k: n.get(k) for k in
                        ("siren", "denomination", "forme_juridique",
                         "groupe_personne", "lots", "total_lots_pm",
                         "pct_proprio", "mot_declencheur")},
                     "nb_log_bdnb": by_cle.get(cle, {}).get("nb_log_bdnb")},
        })

    # zones grises (depuis scan rows), hors cles deja en orange / overrides
    deja = {c["cle"] for c in a_arbitrer} | {c["cle"] for c in a_completer}
    for cle, r in scan_rows.items():
        if cle in deja or cle in ctx["override_cles"]:
            continue
        lat, lon, adr = coords(cle)
        sp, mut = r.get("social_pct") or 0, r.get("mut_an_exact") or 0
        tpp, tpb = r.get("top_prive_pct") or 0, r.get("top_prive_pct_bdnb") or 0
        zg = None
        if ZG_MIXTE_LOW <= sp < cfg.social_pct_min and mut < cfg.mut_apt_per_year_min:
            zg = ("zone_grise_mixte", {"social_pct": sp, "mut_an_exact": mut,
                                       "hlm_owners": r.get("hlm_owners") or []})
        elif ZG_MONO_LOW <= tpp < 80 and tpb >= ZG_MONO_LOW:
            zg = ("zone_grise_mono", {"top_prive_pct": tpp, "top_prive_pct_bdnb": tpb,
                                      "top_prive": r.get("top_prive")})
        if zg:
            a_arbitrer.append({
                "cle": cle, "adresse": adr, "lat": lat, "lon": lon,
                "current_kv_tag": (ctx["assignments"].get(cle) or {}).get("type"),
                "maps": maps_link(lat, lon, adr),
                "type": zg[0], "source": "zone_grise", "data": zg[1]})
    return a_arbitrer, a_completer


def build_pile_verte(ctx, orange_cles, rouge_cles, scan_rows):
    """Adresses certifiees : tag KV clair OU reco scan, hors orange/rouge."""
    verte = {}
    for a in ctx["adresses"]:
        cle = a.get("cle") or ""
        if not cle or cle in orange_cles or cle in rouge_cles:
            continue
        tag = (ctx["assignments"].get(cle) or {}).get("type")
        cat = tag
        if not cat:
            reco = (scan_rows.get(cle) or {}).get("reco")
            cat = reco if reco and reco != "-" else None
        # Copro privee normale (ni tag KV, ni reco) = production normale, RAS.
        verte.setdefault(cat or "copro_privee", []).append(cle)
    return verte


def build_pile_rouge(ctx):
    rouge = {"T1_fa_ventes_sans_ancrage": [], "T2_tag_kv_orphelin": [],
             "T3_cle_malformee": [], "T4_override_orphelin": []}
    by_cle = ctx["by_cle"]
    # T1 : FA=True + ventes>0 sans _fusion_cible
    for a in ctx["adresses"]:
        if (a.get("_fusion_auto") and int(a.get("nb_ventes_logement") or 0) > 0
                and not a.get("_fusion_cible")):
            rouge["T1_fa_ventes_sans_ancrage"].append(a.get("cle"))
    # T2 : tag KV absent du light
    for cle in ctx["assignments"]:
        if cle not in by_cle:
            rouge["T2_tag_kv_orphelin"].append(cle)
    # T3 : cle malformee (num non extractible) cote light, KV ou coproprietes
    for cle in set(by_cle) | set(ctx["assignments"]) | set(ctx["co_cles"]):
        if cle and parse_cle(cle) is None:
            rouge["T3_cle_malformee"].append(cle)
    # T4 : override absent du light
    for cle in ctx["override_cles"]:
        if cle not in by_cle:
            rouge["T4_override_orphelin"].append(cle)
    return rouge


def count_sans_pm_majic(ctx):
    """Info (PAS anomalie) : adresses avec parcelle mais sans lot PM MAJIC."""
    n = 0
    for r in ctx["enrich"].values():
        if (r.get("parcelles_bdnb") and r.get("status") in ("no_majic", "no_parcelle")):
            n += 1
    return n


# ---------- rendu .md ----------
def write_orange_md(path, cfg, a_arbitrer, a_completer):
    L = [f"# Pile orange — {cfg.slug}", "",
         f"**À arbitrer : {len(a_arbitrer)}** · **À compléter : {len(a_completer)}**", ""]
    by_type = {}
    for c in a_arbitrer:
        by_type.setdefault(c["type"], []).append(c)
    for t, items in by_type.items():
        L.append(f"## À arbitrer — {t} ({len(items)})")
        for c in items:
            L.append(f"- **{c['adresse']}** ([carte]({c['maps']})) — {c['source']}")
        L.append("")
    L.append(f"## À compléter (validation live/terrain requise) — {len(a_completer)}")
    for c in a_completer:
        L.append(f"- {c['adresse']} ([carte]({c['maps']})) — {c['type']}")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


def write_rouge_md(path, cfg, rouge, sans_pm):
    total = sum(len(v) for v in rouge.values())
    L = [f"# Pile rouge — anomalies données — {cfg.slug}", "",
         f"**Total anomalies : {total}** (cible < 10)", "",
         f"_Info (pas une anomalie) : {sans_pm} adresses avec parcelle mais "
         f"sans propriétaire personne-morale MAJIC — normal (PP RGPD-invisibles)._", ""]
    for k, v in rouge.items():
        L.append(f"## {k} — {len(v)}")
        for cle in v:
            L.append(f"- {cle}")
        L.append("")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", default="dauphine-lacassagne",
                        help="slug secteur (defaut: dauphine-lacassagne)")
    parser.add_argument("--apply", action="store_true",
                        help="(jalon 4) poserait le tag KV a_arbitrer ; NON utilise ici")
    args = parser.parse_args()
    cfg = load_secteur(args.secteur)

    print("=" * 78)
    print(f"PIPELINE {cfg.short.upper()}  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 78)

    ctx = load_context(cfg)
    print(f"  light={len(ctx['adresses'])} kv={len(ctx['assignments'])} "
          f"enrich={len(ctx['enrich'])} overrides={len(ctx['override_cles'])}")
    print("  scan --json (sous-process)...")
    scan_rows = run_scan_json(cfg)
    print(f"  scan rows={len(scan_rows)}")

    a_arbitrer, a_completer = build_pile_orange(ctx, ctx["by_cle"], scan_rows, cfg)
    rouge = build_pile_rouge(ctx)
    rouge_cles = {c for v in rouge.values() for c in v}
    orange_cles = {c["cle"] for c in a_arbitrer} | {c["cle"] for c in a_completer}
    verte = build_pile_verte(ctx, orange_cles, rouge_cles, scan_rows)
    sans_pm = count_sans_pm_majic(ctx)

    n_verte = sum(len(v) for v in verte.values())
    n_rouge = sum(len(v) for v in rouge.values())
    from collections import Counter
    types_arb = Counter(c["type"] for c in a_arbitrer)

    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = cfg.light.parent
    (d / f"_pile_verte_{cfg.short}.json").write_text(json.dumps({
        "metadata": {"secteur": cfg.slug, "short": cfg.short, "generated_at": stamp,
                     "total": n_verte, "par_categorie": {k: len(v) for k, v in verte.items()}},
        "par_categorie": verte}, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / f"_pile_orange_{cfg.short}.json").write_text(json.dumps({
        "metadata": {"secteur": cfg.slug, "short": cfg.short, "generated_at": stamp,
                     "total_a_arbitrer": len(a_arbitrer), "total_a_completer": len(a_completer),
                     "a_arbitrer_par_type": dict(types_arb),
                     "total_exclus_overrides": len(ctx["override_cles"])},
        "a_arbitrer": a_arbitrer, "a_completer": a_completer},
        ensure_ascii=False, indent=2), encoding="utf-8")
    write_orange_md(d / f"_pile_orange_{cfg.short}.md", cfg, a_arbitrer, a_completer)
    write_rouge_md(d / f"_pile_rouge_{cfg.short}.md", cfg, rouge, sans_pm)

    # Tag KV a_arbitrer : prepare (dry-run) ; --apply reserve au jalon 4.
    print()
    print(f"  PILE VERTE  : {n_verte}  {dict(sorted(((k, len(v)) for k, v in verte.items()), key=lambda x: -x[1]))}")
    print(f"  PILE ORANGE : a_arbitrer={len(a_arbitrer)} {dict(types_arb)} | a_completer={len(a_completer)}")
    print(f"  PILE ROUGE  : {n_rouge}  {dict((k, len(v)) for k, v in rouge.items())}")
    print(f"  (info) adresses sans PM MAJIC (normal) : {sans_pm}")
    if args.apply:
        print("  [apply] NON IMPLEMENTE a ce jalon (tag a_arbitrer pose au jalon 4).")
    else:
        print(f"  [dry-run] poserait a_arbitrer sur {len(a_arbitrer)} cles (non applique).")
    print(f"  ecrit : _pile_verte/orange/rouge_{cfg.short}.*")


if __name__ == "__main__":
    main()
