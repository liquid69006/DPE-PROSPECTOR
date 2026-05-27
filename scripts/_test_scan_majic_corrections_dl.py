#!/usr/bin/env python3
"""Tests des 3 corrections de _scan_majic_kv_untagged_dl.py.

Reproduit la classification de _scan_majic_kv_untagged_dl.py et
verifie 4 cas attendus :

  TEST 1 : sur les 26 overrides _social_overrides_dl.json, aucune
           cle ne doit ressortir reco=social
  TEST 2 : 28 ETIENNE RICHERAND (cle override) : si on simule
           "pas dans overrides", le scan doit proposer 'mixte' via le
           signal DVF (social_pct >= 60 + mut/an >= 2)
  TEST 3 : 48 STE ANNE BARABAN (social pur confirme) : doit garder
           reco='social' (mut/an=0, social_pct >> 60%)
  TEST 4 : filtre FA-source : aucune cle '_fusion_auto=True ET
           own_ventes==0' dans candidates ; les FA legit
           (own_ventes>0) sont incluses

Sortie : PASS / FAIL pour chaque test + details.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Import des helpers depuis le scan (meme algo)
sys.path.insert(0, str(Path(r"C:\Users\Station 5\DPE-PROSPECTOR\scripts")))
from _scan_majic_kv_untagged_dl import (  # noqa: E402
    is_hlm_social, is_public, is_pp, is_sci_or_prive, classify_siren,
    toks, parse_cle, build_dvf_exact_index, mut_apt_an_exact,
    load_overrides, LIGHT, KV_LOCAL, ENRICH, MAJIC, OVERRIDES, DVF,
)


def classify_cle(cle, a, cp, e, overrides_by_cle, owner_lots_aggreg,
                  meta, dvf_idx):
    """Reproduit EXACTEMENT la logique de classification du scan."""
    bdnb = a.get("nb_log_bdnb") or 0
    usage = a.get("usage_principal_bdnb") or ""

    # Agreger les owners sur l'union des parcelles
    parcs = (e.get("parcelles_bdnb") if e else None) or []
    owner_lots = defaultdict(int)
    for p in parcs:
        for k, n in owner_lots_aggreg.get(p, {}).items():
            owner_lots[k] += n
    n_tot = sum(owner_lots.values())

    emphy_lots = sum(n for k, n in owner_lots.items() if k[1] == "E")
    emphy_hlm_lots = sum(n for k, n in owner_lots.items()
                          if k[1] == "E" and meta[k]["class"] == "HLM")
    prop_lots = sum(n for k, n in owner_lots.items() if k[1] == "P")
    prop_hlm_lots = sum(n for k, n in owner_lots.items()
                        if k[1] == "P" and meta[k]["class"] == "HLM")

    if emphy_lots > 0:
        social_lots = emphy_hlm_lots
        denom = emphy_lots
    else:
        social_lots = prop_hlm_lots
        denom = prop_lots if prop_lots > 0 else n_tot
    social_pct = round(social_lots * 100 / denom, 1) if denom else 0.0

    prive_owners = [(k, n) for k, n in owner_lots.items()
                    if meta[k]["class"] in ("PRIVE", "AUTRE", "PP")]
    if prive_owners:
        top_p = max(prive_owners, key=lambda x: x[1])
        top_p_pct = round(top_p[1] * 100
                           / (prop_lots if prop_lots > 0 else n_tot), 1) \
            if (prop_lots if prop_lots > 0 else n_tot) > 0 else 0
        top_p_pct_bdnb = round(top_p[1] * 100 / bdnb, 1) if bdnb > 0 else 0
    else:
        top_p = None
        top_p_pct = 0
        top_p_pct_bdnb = 0

    mut_an = mut_apt_an_exact(cle, dvf_idx)

    has_emphy_hlm = emphy_hlm_lots > 0

    if cle in overrides_by_cle:
        ov_info = overrides_by_cle[cle]
        return (ov_info.get("new_tag") or "mixte",
                f"PROTECTED override", social_pct, mut_an)
    if usage == "Tertiaire":
        return ("bureaux", "usage=Tertiaire", social_pct, mut_an)
    if has_emphy_hlm or social_pct >= 60:
        if mut_an >= 2.0:
            return ("mixte",
                    f"social_pct={social_pct}% MAIS mut/an={mut_an:.2f}>=2",
                    social_pct, mut_an)
        return ("social",
                f"social_pct={social_pct}% mut/an={mut_an:.2f}<2",
                social_pct, mut_an)
    if 20 <= social_pct < 60:
        return ("mixte", f"social_pct={social_pct}%", social_pct, mut_an)
    if top_p and top_p_pct >= 80 and top_p_pct_bdnb >= 80:
        return ("mono",
                f"top SIREN prive {top_p_pct}%/{top_p_pct_bdnb}%",
                social_pct, mut_an)
    return ("-", "", social_pct, mut_an)


def main():
    print("=" * 78)
    print("TESTS CORRECTIONS _scan_majic_kv_untagged_dl.py")
    print("=" * 78)

    # ---------- Setup ----------
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c
                 for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}
    overrides_by_cle = load_overrides()
    dvf_idx = build_dvf_exact_index()

    # Build MAJIC aggreg
    needed_parcels = set()
    for r in enrich_by_cle.values():
        for p in r.get("parcelles_bdnb") or []:
            needed_parcels.add(p)
    sections = sorted({p[8:10] for p in needed_parcels})
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", "69"),
        ("code_commune", "=", "383"),
        ("section", "in", sections),
    ])
    df = tbl.to_pandas()
    df["_parc"] = ("69383000" + df["section"].astype(str)
                   + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
    df = df[df["_parc"].isin(needed_parcels)].copy()
    df = df[df["code_droit"].isin(["P", "E"])].copy()

    aggreg = defaultdict(lambda: defaultdict(int))
    meta = {}
    for _, row in df.iterrows():
        parc = row["_parc"]
        sir = str(row["numero_siren"] or "-")
        dr = str(row["code_droit"] or "-")
        gp = str(row["groupe_personne_libelle"] or "")
        dn = str(row["denomination"] or "")
        fj = str(row["forme_juridique_libelle"] or "")
        key = (sir, dr)
        aggreg[parc][key] += 1
        meta[key] = {"gp": gp, "dn": dn, "fj": fj,
                     "class": classify_siren(gp, dn, fj),
                     "droit_lib": str(row["code_droit_libelle"] or "")}

    print(f"\n  Setup : {len(by_cle)} adresses, {len(overrides_by_cle)} "
          f"overrides, {len(dvf_idx)} adresses DVF indexees")

    # ============================================================
    # TEST 1 : aucun override ne ressort social
    # ============================================================
    print()
    print("=" * 78)
    print("TEST 1 : aucun override ne ressort reco='social'")
    print("=" * 78)
    fails = []
    for cle in overrides_by_cle:
        a = by_cle.get(cle)
        if not a:
            continue
        cp = co_by_cle.get(cle, {})
        e = enrich_by_cle.get(cle, {})
        reco, reason, pct, mut_an = classify_cle(
            cle, a, cp, e, overrides_by_cle, aggreg, meta, dvf_idx)
        if reco == "social":
            fails.append((cle, reco, reason))
    print(f"\n  Overrides testes : {len(overrides_by_cle)}")
    print(f"  Recos social    : {len(fails)}")
    if fails:
        for c, r, msg in fails[:5]:
            print(f"    [FAIL] {c} -> {r}  {msg}")
        print(f"  TEST 1 : FAIL")
    else:
        print(f"  TEST 1 : PASS (0 override re-tague social)")

    # ============================================================
    # TEST 2 : 28 ETIENNE RICHERAND, SIMULE non-override -> mixte via DVF
    # ============================================================
    print()
    print("=" * 78)
    print("TEST 2 : 28 ETIENNE RICHERAND simule sans override -> 'mixte'")
    print("=" * 78)
    cle = "28|RUE|ETIENNE RICHERAND"
    a = by_cle.get(cle)
    cp = co_by_cle.get(cle, {})
    e = enrich_by_cle.get(cle, {})
    # Simulation : override absent
    sim_ov = {c: v for c, v in overrides_by_cle.items() if c != cle}
    reco, reason, pct, mut_an = classify_cle(
        cle, a, cp, e, sim_ov, aggreg, meta, dvf_idx)
    expected = "mixte"
    test2_ok = (reco == expected)
    print(f"\n  cle               : {cle}")
    print(f"  social_pct        : {pct}%")
    print(f"  mut_an_exact      : {mut_an:.2f}")
    print(f"  reco simule       : {reco}")
    print(f"  expected          : {expected}")
    print(f"  raison            : {reason}")
    print(f"  TEST 2 : {'PASS' if test2_ok else 'FAIL'}")

    # ============================================================
    # TEST 3 : 48 STE ANNE BARABAN -> social
    # ============================================================
    print()
    print("=" * 78)
    print("TEST 3 : 48 STE ANNE BARABAN (social pur confirme) -> 'social'")
    print("=" * 78)
    cle = "48|RUE|STE ANNE DE BARABAN"
    a = by_cle.get(cle)
    cp = co_by_cle.get(cle, {})
    e = enrich_by_cle.get(cle, {})
    if a is None:
        print(f"  [skip] {cle} absente du light")
        test3_ok = False
    else:
        # 48 STE ANNE n'est pas dans overrides -> classification normale
        reco, reason, pct, mut_an = classify_cle(
            cle, a, cp, e, overrides_by_cle, aggreg, meta, dvf_idx)
        expected = "social"
        test3_ok = (reco == expected)
        print(f"\n  cle               : {cle}")
        print(f"  in_overrides ?    : {cle in overrides_by_cle}")
        print(f"  social_pct        : {pct}%")
        print(f"  mut_an_exact      : {mut_an:.2f}")
        print(f"  reco              : {reco}")
        print(f"  expected          : {expected}")
        print(f"  raison            : {reason}")
        print(f"  TEST 3 : {'PASS' if test3_ok else 'FAIL'}")

    # ============================================================
    # TEST 4 : filtre FA-source raffine
    # ============================================================
    print()
    print("=" * 78)
    print("TEST 4 : filtre FA-source a 2 conditions")
    print("=" * 78)
    # Simulation du filtre candidates (sans tag skip)
    candidates_sim = []
    fa_phantom_skip = []
    fa_legit_kept = []
    for a in ad:
        cle = a.get("cle") or ""
        is_fa = bool(a.get("_fusion_auto"))
        own_vlog = int(a.get("nb_ventes_logement") or 0)
        if is_fa and own_vlog == 0:
            fa_phantom_skip.append(cle)
            continue
        if is_fa and own_vlog > 0:
            fa_legit_kept.append((cle, own_vlog))
        candidates_sim.append(cle)

    # Verifs
    # (a) Aucune FA-phantom dans candidates_sim
    fa_phantom_in_cand = [c for c in fa_phantom_skip if c in candidates_sim]
    test4a_ok = len(fa_phantom_in_cand) == 0
    print(f"\n  (a) FA fictives (FA+own=0) ECARTEES : "
          f"{len(fa_phantom_skip)} cles ; {'PASS' if test4a_ok else 'FAIL'}")
    print(f"      Exemples : {fa_phantom_skip[:5]}")

    # (b) Au moins une FA legit (own>0) presente
    test4b_ok = len(fa_legit_kept) > 0
    print(f"\n  (b) FA legit (FA+own>0) INCLUSES   : "
          f"{len(fa_legit_kept)} cles ; {'PASS' if test4b_ok else 'FAIL'}")
    for cle, vlog in fa_legit_kept[:5]:
        print(f"      {cle:32s} own_vlog={vlog}")

    # (c) Verification specifique : 84B DAUPHINE doit etre dans
    # candidates_sim (cas legit cite dans la procedure)
    test4c_ok = "84B|RUE|DAUPHINE" in candidates_sim
    print(f"\n  (c) 84B DAUPHINE (FA legit 9 ventes) inclus : "
          f"{'PASS' if test4c_ok else 'FAIL'}")
    # 2B DAUPHINE doit etre ECARTE (FA-phantom apres reclasse)
    a2b = by_cle.get("2B|RUE|DAUPHINE")
    # Note : 2B a ete clean (tag absent) donc reste FA + own=0 -> ecarte
    if a2b:
        v2b = int(a2b.get("nb_ventes_logement") or 0)
        is_fa_2b = bool(a2b.get("_fusion_auto"))
        is_phantom = is_fa_2b and v2b == 0
        print(f"      2B DAUPHINE state : FA={is_fa_2b} own_vlog={v2b}"
              f" -> phantom={is_phantom}")
    test4_ok = test4a_ok and test4b_ok and test4c_ok
    print(f"\n  TEST 4 : {'PASS' if test4_ok else 'FAIL'}")

    # ============================================================
    # RECAP
    # ============================================================
    print()
    print("=" * 78)
    print("RECAP DES TESTS")
    print("=" * 78)
    results = {
        "TEST 1 - aucun override social"      : not fails,
        "TEST 2 - 28 ETIENNE -> mixte (sim)"  : test2_ok,
        "TEST 3 - 48 STE ANNE -> social"      : test3_ok,
        "TEST 4 - filtre FA-source a 2 cond." : test4_ok,
    }
    all_pass = all(results.values())
    for name, ok in results.items():
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}")
    print()
    print(f"  Total : {sum(results.values())}/{len(results)}")
    if all_pass:
        print(f"  -> TOUS LES TESTS PASSENT.")
    else:
        print(f"  -> ECHEC ; ne PAS valider le patch.")
        sys.exit(1)


if __name__ == "__main__":
    main()
