#!/usr/bin/env python3
"""Analyse READ-ONLY des sorties enrich_majic_full montchat.

Recompte les PROPRIETAIRES par parcelle DIRECTEMENT depuis le parquet, en
EXCLUANT syndics/gerants/mandataires/gestionnaires/usufruitiers/nu-proprietaires
(le playbook DL filtre ces non-proprietaires ; enrich_majic_full NE filtre PAS).
=> classif MONO/COPRO/angle-mort robuste, conforme arbre B2.

Aucune ecriture (sauf stdout). ASCII-safe. Pas de KV, pas de commit.
"""
import json, sys, re
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from secteur_config import load_secteur

MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

# cles AMBIGU du dry-run B2 (diag_mancheB2_montchat.md, 76 lignes)
AMBIGU_B2 = [
 "10|RUE|HARMONIE","12|RUE|HARMONIE","134|ROUTE|GENAS","138|ROUTE|GENAS",
 "101|AVENUE|LACASSAGNE","40|ROUTE|GENAS","177|COURS|DOCTEUR LONG","179|COURS|DOCTEUR LONG",
 "86|ROUTE|GENAS","88|ROUTE|GENAS","150|ROUTE|GENAS","2|BOULEVARD|PINEL",
 "200|ROUTE|GENAS","25B|COURS|DOCTEUR LONG","8|RUE|DOCTEUR REBATEL","70|ROUTE|GENAS",
 "162|ROUTE|GENAS","8|IMPASSE|LINDBERG","125|RUE|DAUPHINE","123|RUE|DAUPHINE",
 "100|COURS|DOCTEUR LONG","160|ROUTE|GENAS","27|RUE|BALME","124|RUE|DAUPHINE",
 "2|RUE|RUCHE","22|RUE|BALME","67|AVENUE|LACASSAGNE","28|RUE|ROUX SOIGNAT",
 "106|COURS|DOCTEUR LONG","110|COURS|DOCTEUR LONG","170|ROUTE|GENAS","26|RUE|HARMONIE",
 "48|ROUTE|GENAS","132|RUE|DAUPHINE","84|ROUTE|GENAS","14|RUE|CHARLES RICHARD",
 "82|COURS|DOCTEUR LONG","5|COURS|DOCTEUR LONG","110|RUE|DAUPHINE","16|RUE|RUCHE",
 "20|ROUTE|GENAS","14|COURS|DOCTEUR LONG","10|RUE|ST ISIDORE","10B|RUE|ST ISIDORE",
 "11|RUE|PROFESSEUR FLORENCE","20B|COURS|RICHARD VITTON","43|COURS|DOCTEUR LONG",
 "37|AVENUE|ACACIAS","7|RUE|LOUIS","16|IMPASSE|SABLON","6|IMPASSE|LINDBERG",
 "2|ROUTE|GENAS","55|COURS|DOCTEUR LONG","25|RUE|DOCTEUR BONHOMME","37|AVENUE|CHATEAU",
 "12|RUE|EGLISE","4|RUE|SPORTS","6|RUE|PALAIS D ETE","5|RUE|JULIEN","13|RUE|CAPITAINE",
 "12|RUE|JULES MASSENET","14|RUE|ALFRED DE MUSSET","27|RUE|BONNAND","2|IMPASSE|LUTIN",
 "1|AVENUE|CHATEAU","17|RUE|CAPITAINE","3|RUE|EGLISE","32|RUE|JULES MASSENET",
 "91B|RUE|BALME","38|AVENUE|ACACIAS","67B|AVENUE|LACASSAGNE","45B|RUE|JEANNE D ARC",
 "66B|COURS|RICHARD VITTON","23B|RUE|FEUILLAT","9B|RUE|VILLEBOIS MAREUIL","13B|RUE|CAPITAINE",
]

NON_PROPRIO = re.compile(r"SYNDIC|GERANT|MANDATAIRE|GESTIONNAIRE|USUFRUIT|NU.?PROPRI", re.I)


def main():
    cfg = load_secteur("montchat")
    light = json.loads(cfg.light.read_text(encoding="utf-8"))
    ad = light["adresses"]
    co = light["coproprietes"]
    ad_by_cle = {a.get("cle") or "": a for a in ad}
    co_cles = set(c.get("cle_adresse") or "" for c in co)
    cache = json.loads(cfg.cache_bg.read_text(encoding="utf-8"))
    enr = json.loads(cfg.enrich_majic.read_text(encoding="utf-8"))
    results = enr.get("results", [])
    res_by_cle = {r.get("cle") or "": r for r in results}

    # ---- recompte proprietaires PM par parcelle (filtre syndic) depuis parquet ----
    import pyarrow.parquet as pq
    tbl = pq.read_table(MAJIC, filters=[("departement","=",cfg.dep),
                                        ("code_commune","in",cfg.code_commune)])
    df = tbl.to_pandas()
    pref = cfg.pref_by_commune()
    # owners par parcelle BDNB-key
    owners_by_parc = defaultdict(set)   # parckey -> set(siren proprietaires reels)
    lots_by_parc = Counter()
    for cc, sec, plan, sir, droit in zip(df["code_commune"], df["section"],
            df["numero_parcelle"], df["numero_siren"], df["code_droit_libelle"]):
        try:
            key = f"{pref[str(cc)]}{sec}{str(int(plan)).zfill(4)}"
        except Exception:
            continue
        lots_by_parc[key] += 1
        if sir is None: continue
        if droit and NON_PROPRIO.search(str(droit)): continue
        owners_by_parc[key].add(sir)

    print("="*78)
    print("ANALYSE ENRICH MONTCHAT (owner count = parquet, filtre syndic)")
    print("="*78)

    # ---- 1. 69385 ----
    print("\n--- 1. VIGILANCE 69385 ---")
    pref_counter = Counter()
    p385 = {}
    for bg, parcs in cache.items():
        for p in (parcs or []):
            pref_counter[p[:8]] += 1
            if p.startswith("69385"):
                p385.setdefault(bg, []).append(p)
    print("prefixes parcelle (cache):")
    for pr, n in pref_counter.most_common(10):
        print("   ", pr, n)
    if p385:
        print("ALERTE: parcelles 69385 SORTIES:")
        for bg, ps in p385.items(): print("   bgid", bg, "->", ps)
    else:
        print("RAS: aucune parcelle 69385.")

    # ---- 2. couverture ----
    print("\n--- 2. COUVERTURE CACHE ---")
    bgl = set(a.get("batiment_groupe_id") for a in ad if a.get("batiment_groupe_id"))
    resolved = sum(1 for b in bgl if cache.get(b))
    empty = sum(1 for b in bgl if b in cache and not cache.get(b))
    missing = sum(1 for b in bgl if b not in cache)
    print("bgids light distincts:", len(bgl))
    print("  avec parcelle       :", resolved, "(%.1f%%)" % (100*resolved/len(bgl)))
    print("  cache mais vide     :", empty)
    print("  absents cache       :", missing)

    # ---- 3. classif fermes ----
    print("\n--- 3. CLASSIF (perimetre hors-RNC restant post-B2a) ---")
    st = Counter(r.get("status") for r in results)
    print("enrich status:", dict(st))
    hr = [r for r in results if not r["in_copro"] and not r["has_immat"] and not r["is_fa"]]
    print("perimetre hors-RNC (!in_copro & !has_immat & !is_fa):", len(hr))

    def classify(r):
        parcs = r.get("parcelles_bdnb") or []
        if not parcs: return "ANGLE", 0
        owners = owners_by_parc.get(parcs[0], set())
        n = len(owners)
        if n == 0: return "ANGLE", 0
        if n == 1:
            ratio = r.get("ratio_pm_bdnb", 0) or 0
            # mono = 1 proprio PM + ratio lots/log >=0.9
            if ratio >= 0.9: return "MONO", 1
            return "MONO_weak", 1   # 1 seul proprio mais sous-couverture parcelle
        return "COPRO", n

    cls = Counter()
    detail = []
    for r in hr:
        c, n = classify(r)
        cls[c] += 1
        detail.append((r, c, n))
    print("  MONO (1 proprio PM + ratio>=0.9):", cls["MONO"])
    print("  MONO_weak (1 proprio, ratio<0.9):", cls["MONO_weak"])
    print("  COPRO (>=2 proprios PM)         :", cls["COPRO"])
    print("  ANGLE-MORT (0 proprio PM)       :", cls["ANGLE"])
    print("  [ref] is_mono flag enrich (hr)  :", sum(1 for r in hr if r.get("is_mono")))

    # ---- 4. les 76 ambigus apres parcelle ----
    print("\n--- 4. AMBIGUS B2 (76) -> jointure parcelle reelle ---")
    residu=[]; basc_mono=[]; basc_copro=[]
    for cle in AMBIGU_B2:
        r = res_by_cle.get(cle); a = ad_by_cle.get(cle, {})
        sci = a.get("sci_nom") or ""
        if r is None:
            residu.append((cle, a.get("nb_log_bdnb"), a.get("batiment_groupe_id"),
                           a.get("nb_ventes_logement"), sci, "NO_RESULT")); continue
        parcs = r.get("parcelles_bdnb") or []
        owners = owners_by_parc.get(parcs[0], set()) if parcs else set()
        n = len(owners)
        if n == 0:
            residu.append((cle, r.get("bdnb"), r.get("bgid"), r.get("vlog"), sci,
                           r.get("status") if not parcs else "no_PM_parcelle"))
        elif n == 1:
            basc_mono.append((cle, r.get("bdnb"), sci, r.get("ratio_pm_bdnb")))
        else:
            basc_copro.append((cle, r.get("bdnb"), n, sci))
    print("AMBIGUS B2:", len(AMBIGU_B2))
    print("  -> 1 proprio PM (bascule MONO):", len(basc_mono))
    print("  -> >=2 proprios PM (bascule COPRO):", len(basc_copro))
    print("  -> RESTENT 0-PM reel:", len(residu))
    n_sci = sum(1 for c in AMBIGU_B2 if ad_by_cle.get(c,{}).get("sci_nom"))
    n_sci_basc = sum(1 for x in basc_mono if x[2])
    n_sci_res = sum(1 for x in residu if x[4])
    print("  ambigus portant sci_nom:", n_sci)
    print("    dont bascules MONO via parcelle:", n_sci_basc)
    print("    dont restant 0-PM (sci_nom sans PM parcelle):", n_sci_res)

    print("\n  -- RESIDU 0-PM REEL (cle | nlog | bgid | vlog | status | sci) --")
    for cle,nl,bg,vl,sci,status in sorted(residu, key=lambda x:-((x[1] or 0))):
        print("   %-28s nlog=%-4s bgid=%-22s vlog=%-3s %-14s sci=%s"%(cle,nl,bg,vl,status,sci or "-"))
    print("\n  -- BASCULE MONO (1 proprio PM) --")
    for cle,nl,sci,ratio in basc_mono:
        print("   %-28s nlog=%-4s ratio=%-6s sci=%s"%(cle,nl,ratio,sci or "-"))
    print("\n  -- BASCULE COPRO (>=2 proprios PM) --")
    for cle,nl,n,sci in basc_copro:
        print("   %-28s nlog=%-4s nproprio=%s sci=%s"%(cle,nl,n,sci or "-"))


if __name__ == "__main__":
    main()
