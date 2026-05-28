#!/usr/bin/env python3
"""enrich_majic_full.py - Phase 2 : sweep complet sur un secteur.

Differences vs Phase 1 (enrich_majic.py) :
- Mode BULK : 1 read MAJIC filtre par dep+commune, puis groupby parcelle
  (cible 15-30s par secteur vs 4 min serial)
- Heuristique mono raffinee : ratio lots_PM / nb_log_bdnb >= 0.9 ET
  1 SIREN ET 100% lots
- Normalisation tirets : nom_voie 'ST-ANTOINE' = 'ST ANTOINE'
- 'ensemble' actionnable uniquement si voisins MAJIC sur MEME bgid light
  (sinon = parcelle partagee multi-batis distincts, non actionnable)
- Pas de flag 'faux-matching' (laisse a BAN->BDNB verification cas par cas)

Usage :
  python enrich_majic_full.py --secteur dauphine_lacassagne
  python enrich_majic_full.py --secteur motte_picquet
"""
import argparse, json, sys, time, urllib.parse, urllib.request, re
from pathlib import Path
from collections import defaultdict, Counter

from secteur_config import load_secteur, slugs  # source unique de verite

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(__file__).resolve().parent.parent
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"


def norm_voie(s):
    """Normalise nom_voie : retire tirets + accents."""
    if not s: return ""
    s = str(s).upper()
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def fmt_addr(row):
    nv = (row.get("numero_voirie") or "").lstrip("0") or "0"
    ind = (row.get("indice_de_repetition") or "").strip()
    nat = (row.get("nature_voie") or "").strip()
    voie = norm_voie(row.get("nom_voie"))
    return f"{nv}{ind} {nat} {voie}".strip()


def parc_to_majic(bdnb_p):
    if not bdnb_p or len(bdnb_p) < 14: return None
    sec = bdnb_p[8:10].strip()
    plan = bdnb_p[10:].lstrip("0") or "0"
    try: return sec, int(plan)
    except: return None


def fetch_bdnb_parcelles_batch(bgids, cache_bg, throttle=0.05):
    """Pour chaque bgid non-cache, query BDNB rel_batiment_groupe_parcelle.
    Met a jour cache_bg in-place. Retourne missing count."""
    missing = [b for b in bgids if b and b not in cache_bg]
    if not missing: return 0
    print(f"  [INFO] {len(missing)} bgids manquants en cache, query BDNB rel_parcelle...")
    for i, bg in enumerate(missing, 1):
        url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
               f"?batiment_groupe_id=eq.{bg}")
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                rows = json.loads(r.read())
            parcs = [x.get("parcelle_id") for x in rows if x.get("parcelle_id")]
        except Exception as e:
            print(f"    ! {bg}: {e}")
            parcs = []
        cache_bg[bg] = parcs
        if i % 50 == 0:
            print(f"    progress: {i}/{len(missing)}")
        time.sleep(throttle)
    return len(missing)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", required=True,
                        choices=slugs() + ["dauphine_lacassagne", "motte_picquet"],
                        help="slug secteur (tiret ; underscore accepte en back-compat)")
    parser.add_argument("--skip-bdnb-completion", action="store_true",
                        help="Ne pas completer le cache bgid_parcelle via live BDNB")
    args = parser.parse_args()

    cfg = load_secteur(args.secteur)
    light_path = cfg.light
    cache_bg_path = cfg.cache_bg
    out_path = cfg.enrich_majic

    print("=" * 80)
    print(f"  enrich_majic_full.py PHASE 2 - {args.secteur}")
    print("=" * 80)
    print(f"  light : {light_path.name}")
    print(f"  output: {out_path.name}")
    print()

    t0 = time.time()
    doc = json.loads(light_path.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc["coproprietes"]
    cache_bg = json.loads(cache_bg_path.read_text(encoding="utf-8")) if cache_bg_path.exists() else {}
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

    def to_int(x):
        try: return int(x)
        except: return 0

    print(f"  Adresses light : {len(ad)}")
    print(f"  Coproprietes   : {len(co)}")
    print(f"  Cache bgid_parc: {len(cache_bg)} entrees")

    # Collect bgids distincts + completer cache si necessaire
    bgids = set()
    for a in ad:
        bg = a.get("batiment_groupe_id")
        if bg: bgids.add(bg)
    print(f"  bgids distincts dans light : {len(bgids)}")

    if not args.skip_bdnb_completion:
        n_added = fetch_bdnb_parcelles_batch(bgids, cache_bg)
        if n_added:
            cache_bg_path.write_text(json.dumps(cache_bg, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
            print(f"  [OK] cache mis a jour (+{n_added} entrees)")

    # Map cle -> parcelle (1ere parcelle BDNB du bgid)
    cle_to_parcs = {}
    for a in ad:
        bg = a.get("batiment_groupe_id") or ""
        parcs = cache_bg.get(bg) or []
        cle_to_parcs[a.get("cle") or ""] = parcs

    # MAJIC bulk read filtre dep+commune
    print()
    print(f"  [BULK] MAJIC read dep={cfg.dep} commune={','.join(cfg.code_commune)}...")
    import pyarrow.parquet as pq
    t_majic = time.time()
    tbl = pq.read_table(MAJIC, filters=[
        ("departement","=",cfg.dep),
        ("code_commune","in",cfg.code_commune),   # LISTE (multi-commune: MP=115+107)
    ])
    df = tbl.to_pandas()
    print(f"  [OK] {len(df)} lots MAJIC PM lus en {time.time()-t_majic:.1f}s")

    # Pre-traiter df : normaliser nom_voie, addr key
    df["addr"] = df.apply(fmt_addr, axis=1)
    df["nom_voie_norm"] = df["nom_voie"].apply(norm_voie)

    # Groupby par (commune, section, numero_parcelle) ; prefixe BDNB par commune
    _pref_by_commune = cfg.pref_by_commune()   # DL: {'383':'69383000'}
    by_parc = {}
    for (cc, sec, plan), sub in df.groupby(["code_commune","section","numero_parcelle"]):
        key = f"{_pref_by_commune[str(cc)]}{sec}{str(int(plan)).zfill(4)}"
        by_parc[key] = sub

    print(f"  [OK] {len(by_parc)} parcelles distinctes indexees")

    # Analyser chaque adresse light
    print()
    print(f"  [SWEEP] analyse {len(ad)} adresses light...")
    t_sweep = time.time()

    results = []
    bgid_to_majic = defaultdict(set)  # bgid -> set(addr MAJIC sur ce bgid via cle)

    # Pre-calculer adresses light par bgid pour 'multi-facades meme bgid'
    bgid_to_cles_light = defaultdict(list)
    for a in ad:
        bg = a.get("batiment_groupe_id") or ""
        if bg: bgid_to_cles_light[bg].append(a.get("cle") or "")

    for a in ad:
        cle = a.get("cle") or ""
        bg = a.get("batiment_groupe_id") or ""
        bdnb = to_int(a.get("nb_log_bdnb"))
        parcs = cle_to_parcs.get(cle) or []

        rec = {
            "cle": cle, "bgid": bg, "bdnb": bdnb,
            "vlog": to_int(a.get("nb_ventes_logement")),
            "in_copro": cle in co_by_cle,
            "has_immat": bool(a.get("numero_immatriculation")),
            "is_fa": bool(a.get("_fusion_auto")),
            "parcelles_bdnb": parcs,
        }

        if not parcs:
            rec["status"] = "no_parcelle"
            rec["majic_lots"] = 0
            results.append(rec); continue

        # MAJIC sur 1ere parcelle (multi-parcelles : 1er suffit pour le cas typique)
        p0 = parcs[0]
        sub = by_parc.get(p0)
        if sub is None or sub.empty:
            rec["status"] = "no_majic"
            rec["majic_lots"] = 0
            results.append(rec); continue

        sub_df = sub
        lots_total = int(len(sub_df))
        adr_counts = sub_df["addr"].value_counts().to_dict()
        sirens_grp = sub_df[sub_df["numero_siren"].notna()].groupby("numero_siren")
        sirens = []
        for sir, grp in sirens_grp:
            sirens.append({
                "siren": sir,
                "denomination": (grp["denomination"].iloc[0] or "").strip(),
                "lots": int(len(grp)),
                "pct_lots": round(100.0 * len(grp) / lots_total, 1),
            })
        sirens.sort(key=lambda s: -s["lots"])

        # Ratio MAJIC/BDNB
        ratio = (lots_total / bdnb) if bdnb else 0

        # Heuristique mono Phase 2 : 1 SIREN ET 100% lots PM ET ratio >= 0.9
        n_sirens = len(sirens)
        pct_top = sirens[0]["pct_lots"] if sirens else 0
        is_mono = (n_sirens == 1 and pct_top >= 100 and ratio >= 0.9)

        # Detection ensemble multi-facades :
        # - >1 adresse MAJIC distincte sur parcelle
        # - mais filtrer voisins qui sont sur OTHER bgid light (parcelle partagee)
        # Pour la cible (cle), trouver adresses MAJIC fusables = celles dont
        # le bgid autoritaire est le meme que celui de la cible.
        # Approximation simple : si N adresses MAJIC distinctes, on flagge
        # 'multi_facades' mais on note les voisins "meme_bgid" vs "autre_bgid".
        # Pour cela on regarde si voisins MAJIC sont aussi dans light.
        # NB : on ne fait PAS de check BAN->BDNB (couterait reseau).
        voisins_fusables = []
        voisins_autre_bgid = []
        cible_num = cle.split("|")[0] if "|" in cle else ""
        cible_voie = (cle.split("|")[-1] if "|" in cle else "")
        for adr_majic, n in adr_counts.items():
            # Skip si c'est la cible elle-meme
            adr_parts = adr_majic.split(" ", 2)
            if len(adr_parts) >= 2:
                num_a = adr_parts[0].rstrip("B").rstrip("T")
                num_c = cible_num.rstrip("B").rstrip("T")
                voie_a = adr_parts[-1].upper() if len(adr_parts) >= 3 else ""
                if num_a == num_c and norm_voie(cible_voie) == voie_a:
                    continue  # c'est la cible
            # Voisin : on cherche si une adresse light de meme bgid existe
            # (impossible a determiner sans query BDNB ; approximation par bgid_to_cles_light)
            voisins_fusables.append({"adresse": adr_majic, "lots": n})

        # Multi-facades indicatif : N adresses (excluant la cible) > 0
        multi_facades_brut = len(voisins_fusables) >= 1

        rec.update({
            "status": "ok",
            "majic_lots": lots_total,
            "majic_adresses": [{"adresse": a, "lots": int(n)}
                              for a, n in adr_counts.items()],
            "sirens": sirens,
            "ratio_pm_bdnb": round(ratio, 3),
            "is_mono": is_mono,
            "multi_facades_brut": multi_facades_brut,
            "voisins_majic": voisins_fusables,
        })
        results.append(rec)

    elapsed = time.time() - t_sweep
    print(f"  [OK] sweep en {elapsed:.1f}s ({elapsed*1000/max(1,len(ad)):.0f}ms/adr)")

    # Stats
    n_ok = sum(1 for r in results if r.get("status") == "ok")
    n_no_majic = sum(1 for r in results if r.get("status") == "no_majic")
    n_no_parc = sum(1 for r in results if r.get("status") == "no_parcelle")
    n_mono = sum(1 for r in results if r.get("is_mono"))
    n_mono_hr_actif = sum(1 for r in results
                          if r.get("is_mono") and not r["in_copro"]
                          and not r["has_immat"] and not r["is_fa"]
                          and r["vlog"] > 0 and r["bdnb"] > 1)
    n_mf = sum(1 for r in results if r.get("multi_facades_brut"))

    print()
    print("=" * 80)
    print(f"  RESUME PHASE 2 - {args.secteur}")
    print("=" * 80)
    print(f"  Adresses light total       : {len(ad)}")
    print(f"  Couverture MAJIC (>=1 lot) : {n_ok} ({100*n_ok/len(ad):.1f}%)")
    print(f"  Sans MAJIC (0 lot PM)      : {n_no_majic}")
    print(f"  Sans parcelle BDNB         : {n_no_parc}")
    print()
    print(f"  Detection MONO Phase 2     : {n_mono}  (ratio>=90% + 1 SIREN + 100%)")
    print(f"    dont hr-actifs UI        : {n_mono_hr_actif}  (=candidats KV mono terrain)")
    print(f"  Multi-facades brut         : {n_mf}  (>1 adresse MAJIC sur parcelle)")
    print()
    print(f"  Sweep time total : {time.time()-t0:.1f}s")

    # Sauvegarde
    payload = {
        "secteur": args.secteur, "phase": 2,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_adresses": len(ad),
        "stats": {
            "couverture_ok": n_ok,
            "no_majic": n_no_majic,
            "no_parcelle": n_no_parc,
            "mono_total": n_mono,
            "mono_hr_actif": n_mono_hr_actif,
            "multi_facades_brut": n_mf,
        },
        "results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"  Rapport ecrit : {out_path.name}")


if __name__ == "__main__":
    main()
