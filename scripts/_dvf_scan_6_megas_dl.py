#!/usr/bin/env python3
"""DVF scan lecture seule pour les 6 mega-ensembles DL.

Lit data/secteur_dauphine_lacassagne.json -> mutations_dvf (8852 entries).
Pour chaque ensemble + chaque cle, filtre mutations matching :
  - No voie == num
  - B/T/Q == suffix (B/T/Q ou vide)
  - Voie matche le voie_substring (token overlap, ignore particles)

Affiche par ensemble : total mutations + liste detaille triee par date.
"""
import json, sys, unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
FULL = ROOT / "data" / "secteur_dauphine_lacassagne.json"

ENSEMBLES = [
    {"id": "E1a", "label": "PAVILLON DE FLORE (7/9 + 7B)",
     "cles": ["7|COURS|ALBERT THOMAS", "9|COURS|ALBERT THOMAS"]},
    {"id": "E1b", "label": "PAVILLON DE FLORE II (5/5B + 7B)",
     "cles": ["5|COURS|ALBERT THOMAS", "5B|COURS|ALBERT THOMAS",
              "7B|COURS|ALBERT THOMAS"]},
    {"id": "E2",  "label": "ANTOINE CHARIAL (AUBIGNY+RICHERAND+TERNOIS)",
     "cles": ["27|RUE|AUBIGNY", "29|RUE|AUBIGNY",
              "28|RUE|ETIENNE RICHERAND", "30|RUE|ETIENNE RICHERAND",
              "7|RUE|TERNOIS", "9|RUE|TERNOIS", "11|RUE|TERNOIS",
              "13|RUE|TERNOIS", "15|RUE|TERNOIS", "17|RUE|TERNOIS"]},
    {"id": "E3",  "label": "LA VICTORIENNE (PIONCHON+ST VICTORIEN+ST SIDOINE)",
     "cles": ["4|RUE|CLAUDIUS PIONCHON", "6|RUE|CLAUDIUS PIONCHON",
              "8|RUE|CLAUDIUS PIONCHON",
              "15|RUE|ST VICTORIEN", "17|RUE|ST VICTORIEN",
              "12|RUE|ST SIDOINE", "14|RUE|ST SIDOINE", "16|RUE|ST SIDOINE",
              "18|RUE|ST SIDOINE", "20|RUE|ST SIDOINE"]},
    {"id": "E4",  "label": "LE BARABAN 1 (BARABAN+LOUIS JASSERON)",
     "cles": ["61|RUE|BARABAN", "63|RUE|BARABAN", "65|RUE|BARABAN",
              "67|RUE|BARABAN", "69|RUE|BARABAN",
              "10|RUE|LOUIS JASSERON", "12|RUE|LOUIS JASSERON",
              "14|RUE|LOUIS JASSERON"]},
    {"id": "E5",  "label": "JEAN SORNAY (CHARIAL+PAUL BERT)",
     "cles": ["76|RUE|ANTOINE CHARIAL", "78|RUE|ANTOINE CHARIAL",
              "78B|RUE|ANTOINE CHARIAL", "80|RUE|ANTOINE CHARIAL",
              "80B|RUE|ANTOINE CHARIAL", "82|RUE|ANTOINE CHARIAL",
              "84|RUE|ANTOINE CHARIAL",
              "277|RUE|PAUL BERT", "279|RUE|PAUL BERT"]},
    {"id": "E6",  "label": "LAFAYETTE BARABAN (30/32/34/36/38/40 BARABAN)",
     "cles": ["30|RUE|BARABAN", "32|RUE|BARABAN", "34|RUE|BARABAN",
              "36|RUE|BARABAN", "38|RUE|BARABAN", "40|RUE|BARABAN"]},
]

PARTICLES = {"de","du","la","le","les","des","d'","l'","au","aux"}
SAINT_MAP = {"saint":"ST","sainte":"STE","st":"ST","ste":"STE"}


def strip_accents(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")


def voie_tokens(voie):
    """Normalise 'D'AUBIGNY' -> {'AUBIGNY'} ; 'ST SIDOINE' -> {'ST','SIDOINE'} ; 'SAINT-SIDOINE' -> {'ST','SIDOINE'}."""
    out = set()
    for tok in voie.replace("-", " ").split():
        wl = strip_accents(tok).lower().rstrip(".")
        if not wl: continue
        if wl in PARTICLES: continue
        if wl in SAINT_MAP:
            out.add(SAINT_MAP[wl])
        else:
            out.add(strip_accents(tok).upper())
    return out


def cle_to_filter(cle):
    """'5B|COURS|ALBERT THOMAS' -> (num='5', suff='B', voie_set={'ALBERT','THOMAS'})."""
    num, _type, voie = cle.split("|", 2)
    suff = ""
    if num and num[-1].isalpha():
        suff = num[-1].upper()
        num = num[:-1]
    return num, suff, voie_tokens(voie)


def fmt_money(s):
    try:
        f = float(s.replace(",", "."))
        return f"{f:>10,.0f}".replace(",", " ")
    except Exception:
        return f"{s:>10}"


def fmt_surface(s):
    try:
        f = float(str(s).replace(",", "."))
        return f"{f:>5.1f}"
    except Exception:
        return f"{str(s):>5}"


def main():
    print(f"[load] {FULL}")
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    mutations = doc.get("mutations_dvf") or []
    print(f"[mutations DVF] total = {len(mutations)}")

    grand_total = 0
    grand_lines = []

    for ens in ENSEMBLES:
        print()
        print("=" * 110)
        print(f"  {ens['id']}  {ens['label']}")
        print("=" * 110)

        # Build filters par cle
        cle_filters = {cle: cle_to_filter(cle) for cle in ens["cles"]}
        # Map mutation -> set de cles matchees (peut matcher plusieurs cles si ambiguite)
        by_cle = defaultdict(list)
        for m in mutations:
            nv = str(m.get("No voie", "")).strip()
            btq = str(m.get("B/T/Q", "")).strip().upper()
            voie = str(m.get("Voie", "")).strip()
            v_toks = voie_tokens(voie)
            for cle, (n, s, vs) in cle_filters.items():
                if nv != n: continue
                if btq != s: continue
                # egalite stricte des tokens normalises (sinon BARABAN match STE-ANNE DE BARABAN)
                if vs == v_toks:
                    by_cle[cle].append(m)
                    break

        total = sum(len(v) for v in by_cle.values())
        grand_total += total
        print(f"  Total mutations DVF dans cet ensemble : {total}")

        if total == 0:
            print("  (aucune)")
            continue

        # Liste detaillee par cle
        for cle in ens["cles"]:
            muts = by_cle.get(cle, [])
            if not muts: continue
            print()
            print(f"  -- {cle}  ({len(muts)} mutation(s)) --")
            # Trie par date
            def date_key(m):
                d = m.get("Date mutation", "")
                # JJ/MM/AAAA -> AAAA-MM-JJ
                try:
                    j, mo, a = d.split("/")
                    return f"{a}-{mo}-{j}"
                except Exception:
                    return d
            muts.sort(key=date_key)
            print(f"     {'date':10s} | {'valeur':>12s} | {'nature':14s} | {'surf C1':>7s} | {'lot1':>5s} | adr")
            print("     " + "-" * 100)
            for m in muts:
                date = m.get("Date mutation", "")
                val  = m.get("Valeur fonciere", "")
                nat  = (m.get("Nature mutation","") or "")[:14]
                surf = m.get("Surface Carrez du 1er lot", "") or m.get("Surface reelle bati", "")
                lot1 = m.get("1er lot", "")
                nv = m.get("No voie","")
                btq = m.get("B/T/Q","")
                tv  = m.get("Type de voie","")
                v   = m.get("Voie","")
                adr_str = f"{nv}{btq} {tv} {v}".strip()
                print(f"     {date:10s} | {fmt_money(val):>12s} | {nat:14s} | "
                      f"{fmt_surface(surf):>7s} | {str(lot1):>5s} | {adr_str[:48]}")

    print()
    print("=" * 110)
    print(f"GRAND TOTAL : {grand_total} mutations DVF sur les 6 ensembles")
    print("=" * 110)


if __name__ == "__main__":
    main()
