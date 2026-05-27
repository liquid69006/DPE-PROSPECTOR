#!/usr/bin/env python3
"""Diag detaille des 11 cles DAUPHINE zone grise (lecture seule).

Clés : 25B, 27B, 29B, 31B, 33B, 35B, 53A, 53B, 55A, 55C, 55D RUE DAUPHINE
Tag actuel : 'social'. Signal agrege : 9 mut Apt 5ans sur parcelle(s)
commune(s) = 1.80/an cumule.

Pour chaque cle :
  1. mut Apt 5 ans a l'ADRESSE EXACTE (pas la parcelle agregee)
  2. ventilation par annee
  3. social_pct_corrige si RNC dispo
  4. top owner MAJIC
  5. bgid/parcelles partagees ?

Verdict par cle (pas en bloc).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

CIBLES = [
    "25B|RUE|DAUPHINE",
    "27B|RUE|DAUPHINE",
    "29B|RUE|DAUPHINE",
    "31B|RUE|DAUPHINE",
    "33B|RUE|DAUPHINE",
    "35B|RUE|DAUPHINE",
    "53A|RUE|DAUPHINE",
    "53B|RUE|DAUPHINE",
    "55A|RUE|DAUPHINE",
    "55C|RUE|DAUPHINE",
    "55D|RUE|DAUPHINE",
]

ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}
HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT",
)


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def is_hlm_denom(denom):
    if not denom:
        return False
    d = denom.upper()
    return any(n in d for n in HLM_NEEDLES if n.strip())


# ============================================================
print("=" * 78)
print("DIAG 11 DAUPHINE ZONE GRISE (lecture seule)")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

# DVF index
print("\n  Chargement DVF...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))

# Build DVF index keyed by exact (num, B/T/Q, voie_toks), logement only
dvf_exact = defaultdict(list)
for m in dvf:
    nv = (m.get("No voie") or "").strip()
    if not nv:
        continue
    try:
        nv_int = int(nv)
    except (TypeError, ValueError):
        continue
    btq = (m.get("B/T/Q") or "").strip().upper()
    vt = toks(m.get("Voie") or "")
    if not vt:
        continue
    if str(m.get("Code type local") or "").strip() in ("1", "2"):
        dvf_exact[(nv_int, btq, vt)].append(m)


def parse_cle(cle):
    parts = cle.split("|")
    if len(parts) != 3:
        return None
    raw = parts[0].strip().upper()
    m = re.match(r"^(\d+)([A-Z]*)$", raw)
    if not m:
        return None
    return int(m.group(1)), m.group(2), toks(parts[2])


def dedup(rows):
    seen = set()
    out = []
    for m in rows:
        sig = (m.get("Date mutation"), m.get("No disposition"),
               m.get("Valeur fonciere"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(m)
    return out


# ============================================================
# Pour chaque cle, analyse
# ============================================================
results = []
print()
print(f"  {'cle':24s} {'bgid':35s} {'tag':10s} {'FA':5s} {'cible'}")
print("  " + "-" * 100)
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:24s} ABSENT light")
        continue
    bg = a.get("batiment_groupe_id") or ""
    tg = ((assigns.get(cle) or {}).get("type")) or ""
    fa = a.get("_fusion_auto")
    cible = a.get("_fusion_cible") or "-"
    print(f"  {cle:24s} {bg:35s} {tg:10s} {str(fa or '-'):5s} {cible}")

# Verifier bgids et parcelles
bgs = {by_cle.get(c, {}).get("batiment_groupe_id") for c in CIBLES
       if by_cle.get(c)}
print(f"\n  Bgids distincts : {len(bgs)} ({sorted(b[-9:] if b else '-' for b in bgs)})")

parcs_par_cle = {}
for cle in CIBLES:
    e = enrich_by_cle.get(cle)
    if e:
        parcs_par_cle[cle] = e.get("parcelles_bdnb") or []

# ============================================================
# Detail par cle
# ============================================================
print()
print("=" * 78)
print("Detail par cle (mutations Apt+Maison ADRESSE EXACTE)")
print("=" * 78)

for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        continue
    cp = co_by_cle.get(cle, {})
    e = enrich_by_cle.get(cle, {})
    parsed = parse_cle(cle)
    if not parsed:
        continue
    num, suffix, vt = parsed
    rows = dedup(dvf_exact.get((num, suffix, vt), []))

    # Ventilation annuelle
    yr_cnt = Counter()
    for m in rows:
        d = m.get("Date mutation") or ""
        yr = d.split("/")[-1] if "/" in d else ""
        if yr:
            yr_cnt[yr] += 1
    mut_5 = len(rows)
    mut_an = round(mut_5 / 5, 2)

    # social_pct_corrige
    rnc_habit = cp.get("nb_lots_habitation") or 0
    rnc_total = cp.get("nb_lots_total") or 0
    sirens = e.get("sirens") or []
    hlm_pm = sum(s.get("lots") or 0 for s in sirens
                  if is_hlm_denom(s.get("denomination")))
    majic_pm = e.get("majic_lots") or 0

    if rnc_habit > 0 and rnc_total > 0:
        prop = rnc_habit / rnc_total
        hlm_habit_estim = round(hlm_pm * prop, 1)
        pct_cor = round(hlm_habit_estim * 100 / rnc_habit, 1)
    elif rnc_habit > 0:
        pct_cor = round(hlm_pm * 100 / rnc_habit, 1)
    else:
        pct_cor = None

    # Top owner
    top_owner = "-"
    top_owner_lots = 0
    if sirens:
        top = sirens[0]
        top_owner = (top.get("denomination") or "?")[:32]
        top_owner_lots = top.get("lots") or 0

    # Verdict per cle
    if mut_an >= 2.0:
        verdict = "MIXTE (mut>=2/an)"
    elif pct_cor is not None and pct_cor < 60:
        verdict = "MIXTE (pct<60%)"
    elif mut_an >= 1.0:
        verdict = "INCERTAIN (mut 1-2/an)"
    elif mut_an > 0:
        verdict = "GARDER SOCIAL (peu actif)"
    else:
        verdict = "GARDER SOCIAL (0 vente propre)"

    # Detection signaux MAJIC non-HLM
    has_majic = majic_pm > 0
    has_hlm = hlm_pm > 0
    non_hlm_pm = majic_pm - hlm_pm

    print(f"\n  --- {cle} ---")
    print(f"      bgid       : ...{(a.get('batiment_groupe_id') or '')[-9:]}")
    print(f"      tag actuel : {((assigns.get(cle) or {}).get('type'))}")
    print(f"      FA         : {a.get('_fusion_auto')} cible={a.get('_fusion_cible')}")
    print(f"      RNC habit  : {rnc_habit}  RNC total : {rnc_total}  "
          f"nb_log_bdnb : {a.get('nb_log_bdnb') or 0}")
    print(f"      mut Apt 5ans (cle exacte) : {mut_5}")
    print(f"      mut /an    : {mut_an}")
    if yr_cnt:
        yr_str = " ".join(f"{y}:{n}" for y, n in sorted(yr_cnt.items()))
        print(f"      ventilation: {yr_str}")
    pct_str = f"{pct_cor:.1f}%" if pct_cor is not None else "N/A"
    print(f"      social_pct_corrige : {pct_str}")
    print(f"      MAJIC PM total/HLM : {majic_pm}/{hlm_pm}  "
          f"(non-HLM PM: {non_hlm_pm})")
    print(f"      Top owner  : {top_owner} ({top_owner_lots} lots, "
          f"HLM={is_hlm_denom(top_owner)})")
    print(f"      VERDICT    : {verdict}")

    results.append({
        "cle": cle,
        "mut_5": mut_5,
        "mut_an": mut_an,
        "pct_cor": pct_cor,
        "top_owner": top_owner,
        "verdict": verdict,
        "yr_cnt": dict(yr_cnt),
    })

# ============================================================
# Tableau recap
# ============================================================
print()
print("=" * 110)
print("TABLEAU RECAP par cle")
print("=" * 110)
print(f"  {'cle':24s} {'mut5':>4} {'mut/an':>7} {'%COR':>7} {'top owner':32s} {'verdict'}")
print("  " + "-" * 108)
for r in results:
    pct = f"{r['pct_cor']:.1f}%" if r["pct_cor"] is not None else "N/A "
    print(f"  {r['cle']:24s} {r['mut_5']:>4} {r['mut_an']:>6.2f} {pct:>7} "
          f"{r['top_owner']:32s} {r['verdict']}")

# Compte verdicts
ct_v = Counter(r["verdict"] for r in results)
print()
print(f"  Verdicts :")
for v, n in ct_v.most_common():
    print(f"    {v:30s} : {n}")
