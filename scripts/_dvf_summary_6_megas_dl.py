#!/usr/bin/env python3
"""Resume DVF 6 mega-ensembles DL : totaux + top 5 + derniere vente.

Reutilise la meme logique de filtrage que _dvf_scan_6_megas_dl.py
mais affiche un resume agrege.
"""
import json, sys, unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
FULL = ROOT / "data" / "secteur_dauphine_lacassagne.json"

ENSEMBLES = [
    {"id": "E1a", "label": "PAVILLON DE FLORE (7/9)",
     "ancre": "7 ALBERT THOMAS (AB0219808, 244/90)",
     "cles": ["7|COURS|ALBERT THOMAS", "9|COURS|ALBERT THOMAS"]},
    {"id": "E1b", "label": "PAVILLON DE FLORE II (5/5B/7B)",
     "ancre": "5 ALBERT THOMAS (AB0222935, 170/61)",
     "cles": ["5|COURS|ALBERT THOMAS", "5B|COURS|ALBERT THOMAS",
              "7B|COURS|ALBERT THOMAS"]},
    {"id": "E2",  "label": "ANTOINE CHARIAL (RICHERAND+AUBIGNY+TERNOIS)",
     "ancre": "28 ETIENNE RICHERAND (AA0358655, 306/211)",
     "cles": ["27|RUE|AUBIGNY", "29|RUE|AUBIGNY",
              "28|RUE|ETIENNE RICHERAND", "30|RUE|ETIENNE RICHERAND",
              "7|RUE|TERNOIS", "9|RUE|TERNOIS", "11|RUE|TERNOIS",
              "13|RUE|TERNOIS", "15|RUE|TERNOIS", "17|RUE|TERNOIS"]},
    {"id": "E3",  "label": "LA VICTORIENNE (PIONCHON+VICTORIEN+SIDOINE)",
     "ancre": "12 ST SIDOINE (AB2206571, 498/165)",
     "cles": ["4|RUE|CLAUDIUS PIONCHON", "6|RUE|CLAUDIUS PIONCHON",
              "8|RUE|CLAUDIUS PIONCHON",
              "15|RUE|ST VICTORIEN", "17|RUE|ST VICTORIEN",
              "12|RUE|ST SIDOINE", "14|RUE|ST SIDOINE", "16|RUE|ST SIDOINE",
              "18|RUE|ST SIDOINE", "20|RUE|ST SIDOINE"]},
    {"id": "E4",  "label": "LE BARABAN 1 (BARABAN+JASSERON)",
     "ancre": "61 BARABAN (AB2515468, 466/149)",
     "cles": ["61|RUE|BARABAN", "63|RUE|BARABAN", "65|RUE|BARABAN",
              "67|RUE|BARABAN", "69|RUE|BARABAN",
              "10|RUE|LOUIS JASSERON", "12|RUE|LOUIS JASSERON",
              "14|RUE|LOUIS JASSERON"]},
    {"id": "E5",  "label": "JEAN SORNAY (CHARIAL+PAUL BERT)",
     "ancre": "76 ANTOINE CHARIAL (AA1694256, 349/111)",
     "cles": ["76|RUE|ANTOINE CHARIAL", "78|RUE|ANTOINE CHARIAL",
              "78B|RUE|ANTOINE CHARIAL", "80|RUE|ANTOINE CHARIAL",
              "80B|RUE|ANTOINE CHARIAL", "82|RUE|ANTOINE CHARIAL",
              "84|RUE|ANTOINE CHARIAL",
              "277|RUE|PAUL BERT", "279|RUE|PAUL BERT"]},
    {"id": "E6",  "label": "LAFAYETTE BARABAN (30-40 BARABAN)",
     "ancre": "30 BARABAN (AB3379567, 293/95)",
     "cles": ["30|RUE|BARABAN", "32|RUE|BARABAN", "34|RUE|BARABAN",
              "36|RUE|BARABAN", "38|RUE|BARABAN", "40|RUE|BARABAN"]},
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
    num, _type, voie = cle.split("|", 2)
    suff = ""
    if num and num[-1].isalpha():
        suff = num[-1].upper(); num = num[:-1]
    return num, suff, voie_tokens(voie)


def date_iso(d):
    """'08/01/2024' -> '2024-01-08'."""
    try:
        j, mo, a = d.split("/")
        return f"{a}-{mo}-{j}"
    except Exception:
        return d


def fmt_eur(s):
    try:
        f = float(str(s).replace(",", "."))
        return f"{f:>11,.0f} EUR".replace(",", " ")
    except Exception:
        return f"{s:>11} EUR"


def is_logement(m):
    """Heuristique : vente est-elle d'un logement ?
       Nature='Vente' (pas 'Adjudication' commerciale) + au moins 1 lot avec Surface Carrez > 0
       OU surface reelle bati > 0 et lot1 present. Tolerant - on inclut tout
       'Vente' avec lot1 par defaut, exclut explicitement vol/parking si possible.
    """
    nat = (m.get("Nature mutation","") or "").strip()
    if not nat: return False
    # Adjudication peut etre logement aussi - on garde
    # Critere : avoir au moins une surface Carrez OU une surface reelle bati
    for n in (1,2,3,4,5):
        c = m.get(f"Surface Carrez du {n}er lot" if n==1 else f"Surface Carrez du {n}eme lot", "")
        try:
            if float(str(c).replace(",", ".")) > 0: return True
        except Exception: pass
    sb = m.get("Surface reelle bati", "")
    try:
        if float(str(sb).replace(",", ".")) > 0: return True
    except Exception: pass
    # Si pas de surface mais lot1 present -> probable vente (lot cadastral)
    if str(m.get("1er lot","")).strip():
        # Filtre simple : exclure si valeur < 5000 (likely vol/parking/cave)
        try:
            v = float(str(m.get("Valeur fonciere","")).replace(",", "."))
            if v >= 30000: return True   # seuil logement raisonnable
        except Exception: pass
    return False


def main():
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    mutations = doc.get("mutations_dvf") or []

    print(f"[load] {len(mutations)} mutations DVF total")
    print()

    rows_per_ens = {}
    for ens in ENSEMBLES:
        cle_filters = {cle: cle_to_filter(cle) for cle in ens["cles"]}
        by_cle = defaultdict(list)
        for m in mutations:
            nv  = str(m.get("No voie","")).strip()
            btq = str(m.get("B/T/Q","")).strip().upper()
            v   = str(m.get("Voie","")).strip()
            v_toks = voie_tokens(v)
            for cle, (n, s, vs) in cle_filters.items():
                if nv == n and btq == s and vs == v_toks:
                    by_cle[cle].append(m); break
        rows_per_ens[ens["id"]] = by_cle

    # ---------- RESUME GLOBAL ----------
    print("=" * 100)
    print("RESUME DVF PAR ENSEMBLE -- 6 mega-ensembles DL")
    print("=" * 100)
    print()
    print(f"  {'ID':>4s} | {'Ensemble':45s} | {'tot':>5s} | {'log':>5s} | {'derniere vente':>14s}")
    print("  " + "-" * 90)
    grand_log = grand_tot = 0
    for ens in ENSEMBLES:
        by = rows_per_ens[ens["id"]]
        all_m = [m for muts in by.values() for m in muts]
        log_m = [m for m in all_m if is_logement(m)]
        last = max((date_iso(m.get("Date mutation","")) for m in all_m), default="-")
        grand_tot += len(all_m); grand_log += len(log_m)
        print(f"  {ens['id']:>4s} | {ens['label'][:45]:45s} | {len(all_m):>5d} | "
              f"{len(log_m):>5d} | {last:>14s}")
    print("  " + "-" * 90)
    print(f"  {'TOT':>4s} | {'(6 ensembles cumules)':45s} | {grand_tot:>5d} | "
          f"{grand_log:>5d} |")
    print()

    # ---------- TOP 5 ADRESSES par ensemble ----------
    print("=" * 100)
    print("TOP 5 ADRESSES (par ensemble) -- nb ventes logement")
    print("=" * 100)
    for ens in ENSEMBLES:
        by = rows_per_ens[ens["id"]]
        print()
        print(f"  {ens['id']}  {ens['label']}  (ancre : {ens['ancre']})")
        ranked = []
        for cle in ens["cles"]:
            muts = by.get(cle, [])
            log_muts = [m for m in muts if is_logement(m)]
            tot_v = sum((float(str(m.get("Valeur fonciere","0")).replace(",", "."))
                         for m in log_muts), 0.0)
            last = max((date_iso(m.get("Date mutation","")) for m in log_muts), default="-")
            if muts:
                ranked.append((cle, len(log_muts), len(muts), tot_v, last))
        ranked.sort(key=lambda x: -x[1])
        if not ranked:
            print("    (aucune vente)"); continue
        print(f"    {'cle':36s} | {'log':>4s} | {'tot':>4s} | {'cumule EUR':>14s} | {'derniere':>10s}")
        print("    " + "-" * 80)
        for r in ranked[:5]:
            cle, nlog, ntot, total, last = r
            print(f"    {cle:36s} | {nlog:>4d} | {ntot:>4d} | "
                  f"{total:>14,.0f} | {last:>10s}".replace(",", " "))

    # ---------- DERNIERE VENTE par ensemble (avec contexte) ----------
    print()
    print("=" * 100)
    print("DERNIERE VENTE LOGEMENT par ensemble (avec valeur + surface + adresse)")
    print("=" * 100)
    for ens in ENSEMBLES:
        by = rows_per_ens[ens["id"]]
        all_log = [(cle, m) for cle, muts in by.items() for m in muts if is_logement(m)]
        if not all_log:
            print(f"  {ens['id']}  (aucune vente logement)")
            continue
        all_log.sort(key=lambda cm: date_iso(cm[1].get("Date mutation","")), reverse=True)
        cle, m = all_log[0]
        date = m.get("Date mutation","")
        val  = fmt_eur(m.get("Valeur fonciere",""))
        surf = m.get("Surface Carrez du 1er lot","") or m.get("Surface reelle bati","")
        lot1 = m.get("1er lot","")
        adr = f"{m.get('No voie','')}{m.get('B/T/Q','')} {m.get('Type de voie','')} {m.get('Voie','')}".strip()
        print(f"  {ens['id']}  {date}  {val}  surf={surf:>5}  lot1={lot1}  {adr}  [cle={cle}]")


if __name__ == "__main__":
    main()
