#!/usr/bin/env python3
"""Heuristique combinee MAJIC+DVF pour detecter faux positifs social.

LECTURE SEULE. Aucun re-tag.

Pour chaque cle tag social (209) :
  - social_pct_corrige (MAJIC) : HLM_habit_estim / RNC_habit, N/A si pas RNC
  - mutations_Apt_5ans (DVF)   : nb mutations Apt+Maison distinctes sur
    la PARCELLE BDNB (somme si multi-parcelles)
  - mut_par_an = mutations / 5

VERDICT :
  FAUX_POSITIF_CONFIRME : social_pct_corrige < 60%  OU  mut/an >= 2
  SOCIAL_CONFIRME       : social_pct_corrige >= 60%  ET  mut/an < 1
  INCERTAIN             : sinon (a arbitrer)

RECLASSEMENT PROPOSE :
  - garder social         : SOCIAL_CONFIRME ou INCERTAIN avec mut/an < 1
  - mixte                 : FAUX_POSITIF avec immat RNC (copro mixte HLM+prive)
  - copro_non_immat       : FAUX_POSITIF sans immat RNC
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
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT", "OFFICE PUBLIC DE L'HABITAT",
)


def is_hlm_denom(denom):
    if not denom:
        return False
    d = denom.upper()
    return any(n in d for n in HLM_NEEDLES if n.strip())


# ============================================================
print("=" * 78)
print("HEURISTIQUE COMBINEE MAJIC+DVF - faux positifs social DL")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

# Charger DVF + indexer par (section, num_plan)
print("\n  Chargement DVF...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
# Index : (Section, No plan normalise) -> liste mutations Apt+Maison
dvf_by_parc = defaultdict(list)
for m in dvf:
    sec = m.get("Section") or ""
    plan = m.get("No plan") or ""
    if not sec or not plan:
        continue
    # Normaliser plan (DVF peut avoir '113' ou '0113')
    plan_norm = plan.lstrip("0") or "0"
    # Filtrer types : Apt = 2, Maison = 1
    if str(m.get("Code type local") or "").strip() in ("1", "2"):
        dvf_by_parc[(sec, plan_norm)].append(m)
print(f"  DVF parcelles Apt+Maison : {len(dvf_by_parc)}")


def parcelle_to_dvf_key(parc):
    """'69383000EI0113' -> ('EI', '113')"""
    # parc format : 8 + section + plan (4 chars usuellement)
    sec = parc[8:10]
    plan = parc[10:].lstrip("0") or "0"
    return (sec, plan)


def mutations_distinctes_apt(parcs):
    """Nb mutations distinctes Apt+Maison sur l'union de parcelles."""
    seen = set()
    for parc in parcs:
        key = parcelle_to_dvf_key(parc)
        for m in dvf_by_parc.get(key, []):
            sig = (m.get("Date mutation"), m.get("No disposition"),
                   m.get("Valeur fonciere"))
            seen.add(sig)
    return len(seen)


# ============================================================
social_cles = [c for c, v in assigns.items()
               if (v or {}).get("type") == "social"]
print(f"\n  Cles tag social : {len(social_cles)}")

results = []
for cle in social_cles:
    cp = co_by_cle.get(cle, {})
    a = by_cle.get(cle, {})
    e = enrich_by_cle.get(cle, {})

    rnc_habit = cp.get("nb_lots_habitation") or 0
    rnc_total = cp.get("nb_lots_total") or 0
    majic_pm = e.get("majic_lots") or 0
    sirens = e.get("sirens") or []
    parcs = e.get("parcelles_bdnb") or []
    bdnb = a.get("nb_log_bdnb") or 0

    # HLM lots PM
    hlm_pm = 0
    top_hlm_denom = None
    for s in sirens:
        if is_hlm_denom(s.get("denomination")):
            hlm_pm += s.get("lots") or 0
            if top_hlm_denom is None:
                top_hlm_denom = s.get("denomination")

    # social_pct_corrige
    if rnc_habit > 0 and rnc_total > 0:
        prop_habit = rnc_habit / rnc_total
        hlm_habit_estim = round(hlm_pm * prop_habit, 1)
        social_pct_corrige = round(hlm_habit_estim * 100 / rnc_habit, 1)
    elif rnc_habit > 0:
        # Fallback : prop = 1
        hlm_habit_estim = hlm_pm
        social_pct_corrige = round(hlm_pm * 100 / rnc_habit, 1)
    else:
        hlm_habit_estim = None
        social_pct_corrige = None

    # DVF mutations parcelle
    mut_apt = mutations_distinctes_apt(parcs)
    mut_par_an = round(mut_apt / 5, 2)

    # Verdict
    rnc_present = rnc_habit > 0
    pct_low = social_pct_corrige is not None and social_pct_corrige < 60
    mut_high = mut_par_an >= 2.0
    mut_low = mut_par_an < 1.0
    pct_high = social_pct_corrige is not None and social_pct_corrige >= 60

    if pct_low or mut_high:
        verdict = "FAUX_POSITIF_CONFIRME"
    elif pct_high and mut_low:
        verdict = "SOCIAL_CONFIRME"
    else:
        verdict = "INCERTAIN"

    # Reclassement propose
    has_immat = bool(cp.get("numero_immatriculation")
                      or a.get("numero_immatriculation"))
    if verdict == "FAUX_POSITIF_CONFIRME":
        reclass = "mixte" if has_immat else "copro_non_immat"
    elif verdict == "SOCIAL_CONFIRME":
        reclass = "garder social"
    else:  # INCERTAIN
        if mut_par_an < 1:
            reclass = "garder social (incertain mais peu actif)"
        else:
            reclass = "mixte (incertain + decollectivisation moderee)"

    results.append({
        "cle": cle,
        "rnc_habit": rnc_habit,
        "rnc_total": rnc_total,
        "majic_pm": majic_pm,
        "hlm_pm": hlm_pm,
        "hlm_habit_estim": hlm_habit_estim,
        "social_pct_corrige": social_pct_corrige,
        "mut_apt_5ans": mut_apt,
        "mut_par_an": mut_par_an,
        "bdnb": bdnb,
        "parcs_count": len(parcs),
        "has_immat": has_immat,
        "verdict": verdict,
        "reclass": reclass,
    })

# Tri par mutations/an DESC
results.sort(key=lambda r: (-r["mut_par_an"], -(r["rnc_habit"] or 0)))

# ============================================================
# Resume verdicts
# ============================================================
ct = Counter(r["verdict"] for r in results)
ct_recl = Counter(r["reclass"] for r in results)
print()
print("=" * 78)
print("RESUME VERDICTS")
print("=" * 78)
print(f"\n  Verdicts (sur 209 social) :")
for v, n in ct.most_common():
    print(f"    {v:30s} : {n}")
print(f"\n  Reclassements proposes :")
for r, n in ct_recl.most_common():
    print(f"    {r:50s} : {n}")

# Decomposition par verdict
print(f"\n  Cles avec RNC habit > 0 : {sum(1 for r in results if r['rnc_habit'] > 0)}")
print(f"  Cles avec mut_par_an >= 2 : {sum(1 for r in results if r['mut_par_an'] >= 2)}")
print(f"  Cles avec mut_par_an entre 1 et 2 : {sum(1 for r in results if 1 <= r['mut_par_an'] < 2)}")
print(f"  Cles avec mut_par_an < 1 : {sum(1 for r in results if r['mut_par_an'] < 1)}")
print(f"  Cles avec mut_par_an = 0 (HLM pur DVF) : {sum(1 for r in results if r['mut_par_an'] == 0)}")

# ============================================================
# Tableau complet
# ============================================================
print()
print("=" * 78)
print("TABLEAU COMPLET (tri mutations/an DESC, top 60)")
print("=" * 78)
print(f"\n  {'#':>3} {'cle':32s} {'RNC_h':>5} {'PM':>4} {'HLM':>4} "
      f"{'%COR':>7} {'mut5':>5} {'mut/an':>7} {'verdict':22s} {'reclass'}")
print("  " + "-" * 138)
for i, r in enumerate(results[:60], 1):
    pct = (f"{r['social_pct_corrige']:>6.1f}%"
           if r['social_pct_corrige'] is not None else "  N/A ")
    immat_flag = "*" if r["has_immat"] else " "
    print(f"  {i:>3} {r['cle']:32s} {r['rnc_habit']:>5} "
          f"{r['majic_pm']:>4} {r['hlm_pm']:>4} {pct:>7} "
          f"{r['mut_apt_5ans']:>5} {r['mut_par_an']:>6.2f} "
          f"{r['verdict']:22s} {immat_flag}{r['reclass'][:40]}")

if len(results) > 60:
    print(f"\n  ... +{len(results) - 60} autres (cf reste du tableau)")

# ============================================================
# Decomposition par verdict (details)
# ============================================================
faux_pos = [r for r in results if r["verdict"] == "FAUX_POSITIF_CONFIRME"]
social_ok = [r for r in results if r["verdict"] == "SOCIAL_CONFIRME"]
incertain = [r for r in results if r["verdict"] == "INCERTAIN"]

print()
print("=" * 78)
print(f"[1] FAUX POSITIFS CONFIRMES ({len(faux_pos)} cles)")
print("=" * 78)
print(f"  Raisons :")
n_low_pct = sum(1 for r in faux_pos
                 if r["social_pct_corrige"] is not None
                 and r["social_pct_corrige"] < 60)
n_high_mut = sum(1 for r in faux_pos if r["mut_par_an"] >= 2)
n_both = sum(1 for r in faux_pos
              if r["social_pct_corrige"] is not None
              and r["social_pct_corrige"] < 60 and r["mut_par_an"] >= 2)
print(f"    - via social_pct_corrige < 60% seul : {n_low_pct - n_both}")
print(f"    - via mutations/an >= 2 seul         : {n_high_mut - n_both}")
print(f"    - via les DEUX                        : {n_both}")
print()
faux_pos_sorted = sorted(faux_pos,
                          key=lambda r: -r["mut_par_an"])
print(f"  Top 30 (par mutations/an DESC) :")
print(f"  {'#':>3} {'cle':32s} {'%COR':>7} {'mut/an':>7} {'reclass'}")
print("  " + "-" * 90)
for i, r in enumerate(faux_pos_sorted[:30], 1):
    pct = (f"{r['social_pct_corrige']:>6.1f}%"
           if r['social_pct_corrige'] is not None else "  N/A ")
    print(f"  {i:>3} {r['cle']:32s} {pct:>7} {r['mut_par_an']:>6.2f} "
          f"{r['reclass']}")
if len(faux_pos_sorted) > 30:
    print(f"  ... +{len(faux_pos_sorted) - 30} autres")

print()
print("=" * 78)
print(f"[2] SOCIAL CONFIRMES ({len(social_ok)} cles)")
print("=" * 78)
social_ok_sorted = sorted(social_ok, key=lambda r: -r["rnc_habit"])
print(f"  {'#':>3} {'cle':32s} {'RNC_h':>5} {'%COR':>7} {'mut/an':>7}")
print("  " + "-" * 70)
for i, r in enumerate(social_ok_sorted[:20], 1):
    pct = (f"{r['social_pct_corrige']:>6.1f}%"
           if r['social_pct_corrige'] is not None else "  N/A ")
    print(f"  {i:>3} {r['cle']:32s} {r['rnc_habit']:>5} {pct:>7} "
          f"{r['mut_par_an']:>6.2f}")
if len(social_ok_sorted) > 20:
    print(f"  ... +{len(social_ok_sorted) - 20} autres")

print()
print("=" * 78)
print(f"[3] INCERTAINS ({len(incertain)} cles)")
print("=" * 78)
incertain_sorted = sorted(incertain, key=lambda r: -r["mut_par_an"])
print(f"  {'#':>3} {'cle':32s} {'%COR':>7} {'mut/an':>7} {'reclass'}")
print("  " + "-" * 80)
for i, r in enumerate(incertain_sorted[:20], 1):
    pct = (f"{r['social_pct_corrige']:>6.1f}%"
           if r['social_pct_corrige'] is not None else "  N/A ")
    print(f"  {i:>3} {r['cle']:32s} {pct:>7} {r['mut_par_an']:>6.2f} "
          f"{r['reclass']}")
if len(incertain_sorted) > 20:
    print(f"  ... +{len(incertain_sorted) - 20} autres")

# ============================================================
# Cas 28 ETIENNE RICHERAND zoom
# ============================================================
print()
print("=" * 78)
print("ZOOM 28 ETIENNE RICHERAND")
print("=" * 78)
r28 = next((r for r in results if r["cle"] == "28|RUE|ETIENNE RICHERAND"), None)
if r28:
    print(f"  social_pct_corrige : {r28['social_pct_corrige']}")
    print(f"  mut_apt_5ans       : {r28['mut_apt_5ans']}")
    print(f"  mut_par_an         : {r28['mut_par_an']}")
    print(f"  verdict            : {r28['verdict']}")
    print(f"  reclassement       : {r28['reclass']}")
