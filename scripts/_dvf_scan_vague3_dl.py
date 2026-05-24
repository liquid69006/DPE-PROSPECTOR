#!/usr/bin/env python3
"""Scan DVF pour ensembles E19-E28 (vague 3 DL) - lecture seule.

Affiche par ensemble :
  - Nb ventes logement total
  - Top 3 adresses les plus actives
  - Derniere vente + valeur
  - Prix median au m2 (Carrez)

Tri par nb ventes decroissant.
"""
import json, sys, statistics, unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
FULL = ROOT / "data" / "secteur_dauphine_lacassagne.json"

ENSEMBLES = [
    {"id":"E19","label":"LE JARDIN CLAIR",
     "ancre":"24 METALLURGIE (AB3965985 151/49)",
     "cles":["24|RUE|METALLURGIE","26|RUE|METALLURGIE","28|RUE|METALLURGIE",
             "12|RUE|CARRY"]},
    {"id":"E20","label":"LE SAINT GERMAIN",
     "ancre":"23 TURBIL (AB2926236 122/56)",
     "cles":["23|RUE|TURBIL","258|RUE|PAUL BERT","260|RUE|PAUL BERT","262|RUE|PAUL BERT"]},
    {"id":"E21","label":"LE CLOS SAINT MARC",
     "ancre":"38 ST MAXIMIN (AA9435975 167/51)",
     "cles":["38|RUE|ST MAXIMIN","40|RUE|ST MAXIMIN"]},
    {"id":"E22","label":"TERRASSES ET VILLAS ST MAX",
     "ancre":"1 ROSSAN (AB2460335 138/53)",
     "cles":["1|RUE|ROSSAN","10|RUE|ST MAXIMIN","12|RUE|ST MAXIMIN"]},
    {"id":"E23","label":"77 ALBERT THOMAS / SISLEY",
     "ancre":"77 ALB THOMAS (AC1055698 49/48)",
     "cles":["77|COURS|ALBERT THOMAS","49|RUE|PROFESSEUR PAUL SISLEY",
             "51|RUE|PROFESSEUR PAUL SISLEY"]},
    {"id":"E24","label":"SDC LE DUO II",
     "ancre":"113 BARABAN (AD5133418 97/42)",
     "cles":["113|RUE|BARABAN","111|RUE|BARABAN","64|RUE|ANTOINE CHARIAL"]},
    {"id":"E25","label":"SDC LE SISLEY",
     "ancre":"30 SISLEY (AC7505134 87/43)",
     "cles":["30|RUE|PROFESSEUR PAUL SISLEY","30B|RUE|PROFESSEUR PAUL SISLEY",
             "32|RUE|PROFESSEUR PAUL SISLEY"]},
    {"id":"E26","label":"SDC TUILIERS",
     "ancre":"16 TUILIERS (AE0762401 109/55)",
     "cles":["16|RUE|TUILIERS","14|RUE|ST MAXIMIN"]},
    {"id":"E27","label":"LA COUR LAFAYETTE",
     "ancre":"272 LAFAYETTE (AC3212578 209/78)",
     "cles":["272|COURS|LAFAYETTE","25|RUE|ST ANTOINE"]},
    {"id":"E28","label":"LES JARDINS DU CHATEAU",
     "ancre":"38 LACASSAGNE (AB8378317 220/71)",
     "cles":["38|AVENUE|LACASSAGNE","40|AVENUE|LACASSAGNE"]},
]

PARTICLES = {"de","du","la","le","les","des","d'","l'","au","aux"}
SAINT_MAP = {"saint":"ST","sainte":"STE","st":"ST","ste":"STE"}


def strip_accents(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")


def voie_tokens(voie):
    out = set()
    for tok in voie.replace("-", " ").split():
        wl = strip_accents(tok).lower().rstrip(".")
        if not wl: continue
        if wl in PARTICLES: continue
        if wl in SAINT_MAP: out.add(SAINT_MAP[wl])
        else: out.add(strip_accents(tok).upper())
    return out


def cle_to_filter(cle):
    num, _t, voie = cle.split("|", 2)
    suff = ""
    if num and num[-1].isalpha(): suff = num[-1].upper(); num = num[:-1]
    return num, suff, voie_tokens(voie)


def date_iso(d):
    try:
        j, mo, a = d.split("/")
        return f"{a}-{mo}-{j}"
    except Exception:
        return d


def to_float(s):
    try: return float(str(s).replace(",", "."))
    except Exception: return 0.0


def main():
    print(f"[load] {FULL}")
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    mutations = doc.get("mutations_dvf") or []
    print(f"[mutations DVF] {len(mutations)} total\n")

    results = []
    for ens in ENSEMBLES:
        cle_filters = {c: cle_to_filter(c) for c in ens["cles"]}
        by_cle = defaultdict(list)
        for m in mutations:
            nv  = str(m.get("No voie","")).strip()
            btq = str(m.get("B/T/Q","")).strip().upper()
            v   = str(m.get("Voie","")).strip()
            v_toks = voie_tokens(v)
            for cle, (n, s, vs) in cle_filters.items():
                if nv == n and btq == s and vs == v_toks:
                    by_cle[cle].append(m)
                    break

        all_m = [m for muts in by_cle.values() for m in muts]
        if not all_m:
            results.append({**ens,"n_log":0,"by_cle":{},"last":"-","last_val":0,
                            "median_eur_m2":None}); continue

        # Filtre logement : surface > 0 ou valeur >= 30k
        log_m = []
        for m in all_m:
            surf = to_float(m.get("Surface Carrez du 1er lot")) or to_float(m.get("Surface reelle bati"))
            val  = to_float(m.get("Valeur fonciere"))
            if surf > 0 or val >= 30000:
                log_m.append(m)

        # Dedup mutations par (date, valeur, voie complete) pour calcul eur/m2
        # On somme les surfaces Carrez de tous les rows partageant cette dedup_key
        dedup = defaultdict(lambda: {"val":0.0,"surf_sum":0.0,"date":""})
        for m in log_m:
            key = (m.get("Date mutation",""), str(m.get("Valeur fonciere","")),
                   str(m.get("No voie","")), str(m.get("B/T/Q","")),
                   str(m.get("Voie","")))
            d = dedup[key]
            d["val"] = max(d["val"], to_float(m.get("Valeur fonciere")))
            d["date"] = m.get("Date mutation","")
            # surfaces - peut etre Carrez 1 + 2 + 3 ... ou reelle bati
            s1 = to_float(m.get("Surface Carrez du 1er lot"))
            s2 = to_float(m.get("Surface Carrez du 2eme lot"))
            s3 = to_float(m.get("Surface Carrez du 3eme lot"))
            sr = to_float(m.get("Surface reelle bati"))
            # On prend la max entre Carrez total ou reelle bati pour cette ligne
            surf_line = max(s1 + s2 + s3, sr)
            # Comme une mutation peut avoir plusieurs rows, on prend le max trouve
            d["surf_sum"] = max(d["surf_sum"], surf_line)

        eur_m2_samples = []
        for k, d in dedup.items():
            if d["surf_sum"] >= 10 and d["val"] >= 30000:
                em2 = d["val"] / d["surf_sum"]
                if 500 < em2 < 25000:   # filtre plausibilite logement Lyon 3e
                    eur_m2_samples.append(em2)

        median_em2 = statistics.median(eur_m2_samples) if eur_m2_samples else None

        # Derniere vente
        log_m.sort(key=lambda m: date_iso(m.get("Date mutation","")), reverse=True)
        last = log_m[0]
        last_date = last.get("Date mutation","")
        last_val  = to_float(last.get("Valeur fonciere"))
        last_adr  = (f"{last.get('No voie','')}{last.get('B/T/Q','')} "
                     f"{last.get('Type de voie','')} {last.get('Voie','')}").strip()

        # Top 3 adresses
        log_by_cle = defaultdict(int)
        for cle, muts in by_cle.items():
            log_by_cle[cle] = sum(1 for m in muts
                                  if to_float(m.get("Surface Carrez du 1er lot")) > 0
                                  or to_float(m.get("Surface reelle bati")) > 0
                                  or to_float(m.get("Valeur fonciere")) >= 30000)
        top3 = sorted(log_by_cle.items(), key=lambda kv: -kv[1])[:3]

        results.append({
            **ens,"n_log":len(log_m),"n_tot":len(all_m),
            "top3":top3,
            "last_date":last_date,"last_val":last_val,"last_adr":last_adr,
            "median_em2":median_em2,
            "n_em2_samples":len(eur_m2_samples),
            "n_dedup_mutations":len(dedup),
        })

    # Tri par nb log decroissant
    results.sort(key=lambda r: -r.get("n_log", 0))

    # Affichage
    print("=" * 110)
    print("DVF VAGUE 3 - 10 ENSEMBLES (tri par n_ventes_log decroissant)")
    print("=" * 110)
    print()
    print(f"  {'ID':>4s} | {'Label':30s} | {'log':>4s} | {'tot':>4s} | "
          f"{'derniere':>10s} | {'derniere val':>11s} | {'median EUR/m2':>13s} | {'n_em2':>5s}")
    print("  " + "-" * 100)
    grand_log = grand_tot = 0
    for r in results:
        em2_str = f"{r.get('median_em2'):>11,.0f}".replace(",", " ") if r.get("median_em2") else "    -"
        last_val_str = f"{r.get('last_val',0):>9,.0f} EUR".replace(",", " ") if r.get("last_val") else "      -"
        print(f"  {r['id']:>4s} | {r['label'][:30]:30s} | {r.get('n_log',0):>4d} | "
              f"{r.get('n_tot',0):>4d} | {date_iso(r.get('last_date','-')):>10s} | "
              f"{last_val_str:>11s} | {em2_str:>11s} EUR | {r.get('n_em2_samples',0):>5d}")
        grand_log += r.get("n_log", 0); grand_tot += r.get("n_tot", 0)
    print("  " + "-" * 100)
    print(f"  {'TOT':>4s} | (cumule)                       | {grand_log:>4d} | {grand_tot:>4d} |")
    print()

    print("=" * 110)
    print("DETAIL par ensemble (top 3 adresses + derniere vente + ancre)")
    print("=" * 110)
    for r in results:
        print()
        print(f"  {r['id']}  {r['label']}  (ancre : {r['ancre']})")
        print(f"     Total : {r.get('n_log',0)} log ({r.get('n_tot',0)} mutations DVF)")
        if not r.get("n_log"):
            print(f"     (aucune vente)")
            continue
        em2 = r.get('median_em2')
        print(f"     Derniere vente : {date_iso(r.get('last_date','-'))}  "
              f"{r.get('last_val',0):,.0f} EUR  {r.get('last_adr','')[:48]}".replace(",", " "))
        if em2:
            print(f"     Prix median Carrez : {em2:,.0f} EUR/m2  "
                  f"({r.get('n_em2_samples')} echantillons dedup)".replace(",", " "))
        else:
            print(f"     Prix median Carrez : - (pas d'echantillon valable)")
        print(f"     Top 3 adresses :")
        for cle, n in r.get("top3", []):
            print(f"       {cle:36s}  {n:>3d} ventes")


if __name__ == "__main__":
    main()
