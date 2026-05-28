#!/usr/bin/env python3
"""enrich_majic.py - Phase 1 : enrichissement secteur via MAJIC locaux2.

Pour chaque hr-actif du secteur, balaye majic_locaux2_2025.parquet sur
la parcelle BDNB (via cache _bgid_parcelle_<sct>.json) et extrait :
  - Toutes adresses postales uniques sur la parcelle
  - SIRENs proprietaires + nb lots detenus + % du total
  - Detection 'mono' (1 SIREN >= 95% lots) - vraie monopropriete PM
  - Detection 'ensemble multi-facades' (N adresses postales > 1)
  - Detection 'faux-matching make_light' (adresse cible absente des
    adresses MAJIC du bati BDNB sur cette parcelle)

Usage :
  python enrich_majic.py --secteur dauphine_lacassagne [--mode hr_actifs]
  python enrich_majic.py --secteur motte_picquet

Modes :
  --mode hr_actifs (default) : seulement les hr-actifs UI
  --mode all                 : toutes les adresses du secteur (futur)

Lecture seule : ecrit data/_enrich_majic_<sct>.json (rapport).
"""
import argparse, json, sys, time
from pathlib import Path
from collections import defaultdict, Counter

from secteur_config import load_secteur, slugs  # source unique de verite

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(__file__).resolve().parent.parent
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"


def parc_to_majic(bdnb_p):
    """69383000DX0035 -> (dep='69', cmm='383', sec='DX', plan=35)."""
    if not bdnb_p or len(bdnb_p) < 14:
        return None
    dep = bdnb_p[:2]
    cmm = bdnb_p[2:5]
    sec = bdnb_p[8:10].strip()
    plan_raw = bdnb_p[10:].lstrip("0") or "0"
    try:
        plan = int(plan_raw)
    except Exception:
        return None
    return dep, cmm, sec, plan


def fmt_addr(row):
    """numero_voirie + indice + nature_voie + nom_voie -> adresse postale."""
    nv = (row.get("numero_voirie") or "").lstrip("0") or "0"
    ind = (row.get("indice_de_repetition") or "").strip()
    nat = (row.get("nature_voie") or "").strip()
    voie = (row.get("nom_voie") or "").strip()
    return f"{nv}{ind} {nat} {voie}".strip()


def query_majic(table_path, dep, cmm, sec, plan):
    """Retourne pandas.DataFrame des lots MAJIC sur la parcelle."""
    import pyarrow.parquet as pq
    tbl = pq.read_table(table_path, filters=[
        ("departement", "=", dep),
        ("code_commune", "=", cmm),
        ("section", "=", sec),
        ("numero_parcelle", "=", plan),
    ])
    return tbl.to_pandas()


def analyse_parcelle(df, cible_cle):
    """Renvoie un dict d'analyse MAJIC d'une parcelle.

    cible_cle : 'NUM|TYPE|VOIE' pour detection 'faux-matching' (cible
    absente des adresses MAJIC du bati ?)
    """
    if df is None or df.empty:
        return {"lots_total": 0, "adresses": [], "sirens": [],
                "mono": False, "multi_facades": False,
                "cible_dans_majic": False}

    df = df.copy()
    df["addr"] = df.apply(fmt_addr, axis=1)

    adr_counts = df["addr"].value_counts().to_dict()
    adresses = [{"adresse": a, "lots": int(n)}
                for a, n in adr_counts.items()]

    # SIRENs propriétaires
    sub = df[df["numero_siren"].notna()].copy()
    total_lots = int(len(df))
    sirens = []
    if not sub.empty:
        for sir, grp in sub.groupby("numero_siren"):
            denom = (grp["denomination"].iloc[0] or "").strip()
            forme = (grp["forme_juridique_libelle"].iloc[0] or "").strip()
            droits = grp["code_droit_libelle"].value_counts().to_dict()
            n = int(len(grp))
            sirens.append({
                "siren": sir,
                "denomination": denom,
                "forme_juridique": forme,
                "lots": n,
                "pct_lots": round(100.0 * n / total_lots, 1),
                "droits": droits,
            })
        sirens.sort(key=lambda s: -s["lots"])

    # Détection mono : 1 SIREN >= 95 % des lots (tolérance arrondi)
    is_mono = (len(sirens) == 1 and sirens[0]["pct_lots"] >= 95.0
               and sirens[0]["lots"] == total_lots)

    # Ensemble multi-facades : > 1 adresse postale unique
    multi_facades = len(adresses) > 1

    # Cible présente parmi les adresses MAJIC ?
    cible_in_majic = False
    cible_num, cible_voie = None, None
    if cible_cle and cible_cle.count("|") == 2:
        n, typv, voie = cible_cle.split("|")
        cible_num = n.lstrip("0") or "0"
        cible_voie = voie.strip()
        for a in adr_counts.keys():
            parts = a.split(" ", 2)
            if len(parts) >= 2:
                num_a = parts[0].rstrip("B").rstrip("T")  # tolere suffixe
                num_c = cible_num.rstrip("B").rstrip("T")
                if (num_a == num_c) and (cible_voie in a.upper()):
                    cible_in_majic = True
                    break

    return {
        "lots_total": total_lots,
        "adresses": adresses,
        "sirens": sirens,
        "mono": is_mono,
        "multi_facades": multi_facades,
        "cible_dans_majic": cible_in_majic,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", required=True,
                        choices=slugs() + ["dauphine_lacassagne", "motte_picquet"],
                        help="slug secteur (tiret ; underscore accepte en back-compat)")
    parser.add_argument("--mode", default="hr_actifs",
                        choices=["hr_actifs", "all"])
    parser.add_argument("--limit", type=int, default=0,
                        help="Limite N adresses (0 = pas de limite)")
    args = parser.parse_args()

    sct = args.secteur                          # forme brute conservee (affichage/payload)
    cfg = load_secteur(sct)
    short = cfg.short
    light_path = cfg.light
    cache_bg_path = cfg.cache_bg
    out_path = ROOT / "data" / f"_enrich_majic_{short}.json"

    print("=" * 80)
    print(f"  enrich_majic.py PHASE 1 - {sct} ({args.mode})")
    print("=" * 80)
    print(f"  light       : {light_path.name}")
    print(f"  cache parc  : {cache_bg_path.name}")
    print(f"  output      : {out_path.name}")
    print()

    doc = json.loads(light_path.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc["coproprietes"]
    cache_bg = json.loads(cache_bg_path.read_text(encoding="utf-8"))

    co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

    def to_int(x):
        try: return int(x)
        except Exception: return 0

    # Selection
    if args.mode == "hr_actifs":
        targets = []
        for a in ad:
            cle = a.get("cle") or ""
            if cle in co_by_cle: continue
            if a.get("numero_immatriculation"): continue
            if a.get("_fusion_auto"): continue
            if to_int(a.get("nb_ventes_logement")) <= 0: continue
            if to_int(a.get("nb_log_bdnb")) <= 1: continue
            targets.append(a)
        targets.sort(key=lambda a: (-to_int(a.get("nb_ventes_logement")),
                                    -to_int(a.get("nb_log_bdnb"))))
    else:
        targets = list(ad)

    if args.limit:
        targets = targets[:args.limit]

    print(f"  Cibles : {len(targets)} adresses")
    print()

    # Sweep
    results = []
    t_total = time.time()
    n_mono = n_multifac = n_faux_match = n_hors_majic = n_hors_cache = 0

    for i, a in enumerate(targets, 1):
        cle = a.get("cle")
        bg = a.get("batiment_groupe_id") or ""
        vlog = to_int(a.get("nb_ventes_logement"))
        bdnb = to_int(a.get("nb_log_bdnb"))
        parcs = cache_bg.get(bg, [])
        rec = {
            "cle": cle, "bgid": bg, "vlog": vlog, "bdnb": bdnb,
            "sci_light": a.get("sci_nom"),
            "parcelles_bdnb": parcs,
        }
        if not parcs:
            rec["status"] = "hors_cache_parcelle"
            n_hors_cache += 1
            results.append(rec); continue

        # Pour Phase 1 : 1ere parcelle uniquement
        p0 = parcs[0]
        tup = parc_to_majic(p0)
        if not tup:
            rec["status"] = "parcelle_format_invalide"
            results.append(rec); continue
        dep, cmm, sec, plan = tup
        rec["majic_query"] = {"dep": dep, "code_commune": cmm,
                              "section": sec, "numero_parcelle": plan}
        try:
            df = query_majic(MAJIC, dep, cmm, sec, plan)
        except Exception as e:
            rec["status"] = f"err_majic:{e}"
            results.append(rec); continue

        ana = analyse_parcelle(df, cle)
        rec.update(ana)
        if ana["lots_total"] == 0:
            rec["status"] = "0_lot_majic"
            n_hors_majic += 1
        else:
            rec["status"] = "ok"
            if ana["mono"]: n_mono += 1
            if ana["multi_facades"]: n_multifac += 1
            if not ana["cible_dans_majic"]: n_faux_match += 1
        results.append(rec)

        # Affichage console compact
        if ana["lots_total"] > 0:
            tag = []
            if ana["mono"]: tag.append("MONO")
            if ana["multi_facades"]: tag.append(f"MF({len(ana['adresses'])})")
            if not ana["cible_dans_majic"]: tag.append("FAUX-MATCH")
            tag_s = " ".join(tag) or "-"
            adrs = ", ".join([f"{a['adresse']}({a['lots']})"
                              for a in ana["adresses"][:3]])
            if len(ana["adresses"]) > 3:
                adrs += f", +{len(ana['adresses'])-3}"
            sir_top = ""
            if ana["sirens"]:
                s0 = ana["sirens"][0]
                sir_top = f" {s0['denomination'][:18]}({s0['lots']}/{ana['lots_total']})"
            print(f"  [{i:2d}] {cle:32s} parc={p0[8:]}  "
                  f"lots={ana['lots_total']:3d} adr={len(ana['adresses'])} "
                  f"sir={len(ana['sirens']):2d}{sir_top:25s}  {tag_s}  | {adrs}")
        else:
            print(f"  [{i:2d}] {cle:32s} parc={p0[8:]}  0 lots MAJIC")

    elapsed = time.time() - t_total
    print()
    print("=" * 80)
    print("RESUME")
    print("=" * 80)
    print(f"  Total cibles            : {len(targets)}")
    print(f"  OK (>=1 lot MAJIC)      : {sum(1 for r in results if r.get('status')=='ok')}")
    print(f"  0 lot MAJIC             : {n_hors_majic}")
    print(f"  Hors cache parcelle     : {n_hors_cache}")
    print()
    print(f"  Detection MONO (1 SIREN=100%) : {n_mono}")
    print(f"  Detection MULTI-FACADES (N>1) : {n_multifac}")
    print(f"  Cible ABSENTE adresses MAJIC  : {n_faux_match}  (probable faux-matching make_light)")
    print()
    print(f"  Sweep time : {elapsed:.1f}s ({elapsed/max(1,len(targets))*1000:.0f}ms/cible)")
    print()

    # Sauvegarde
    payload = {
        "secteur": sct,
        "mode": args.mode,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_cibles": len(targets),
        "stats": {
            "ok": sum(1 for r in results if r.get("status") == "ok"),
            "zero_lot_majic": n_hors_majic,
            "hors_cache_parcelle": n_hors_cache,
            "mono_detecte": n_mono,
            "multi_facades": n_multifac,
            "cible_absente_majic": n_faux_match,
        },
        "results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"  Rapport ecrit : {out_path.name}")


if __name__ == "__main__":
    main()
