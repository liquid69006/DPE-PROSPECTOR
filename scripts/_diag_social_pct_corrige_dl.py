#!/usr/bin/env python3
"""Recalcul social_pct corrige : ratio HLM_habit / RNC_habit (lecture seule).

CORRECTION du bug heuristique precedent :
  - Avant : ratio = HLM_lots_PM / total_PM (incluait dependances)
  - Apres : ratio HLM_habitation / RNC_habitation (logements seulement)

LIMITATION MAJIC :
  Le fichier majic_locaux2_2025.parquet (PM only) ne distingue PAS
  les lots habitation des dependances. On estime via :
    prop_habit = RNC_habit / RNC_total
    HLM_lots_habit_estim = HLM_lots_PM x prop_habit
  (Hypothese : chaque proprietaire PM detient ses lots dans la meme
   proportion habit/total que la SDC globale.)

Pour chaque cle social :
  - rnc_habit, rnc_total, prop_habit
  - majic_pm_total, majic_pm_top_hlm
  - hlm_habit_estim
  - pp_habit_estim = rnc_habit - (majic_pm_total x prop_habit)
  - social_pct_AVANT = HLM_PM / total_PM (ancien)
  - social_pct_CORRIGE = HLM_habit_estim / rnc_habit
  - verdict : < 60% = faux positif probable
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

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
print("RECALCUL social_pct CORRIGE (HLM_habit / RNC_habit)")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

social_cles = [c for c, v in assigns.items()
               if (v or {}).get("type") == "social"]
print(f"\n  Cles tag social : {len(social_cles)}")

CIBLE_28 = "28|RUE|ETIENNE RICHERAND"
if CIBLE_28 not in social_cles:
    print(f"  [warn] {CIBLE_28} pas dans social. On l'ajoute explicitement.")
    social_cles.append(CIBLE_28)


def compute_corrige(cle):
    cp = co_by_cle.get(cle, {})
    a = by_cle.get(cle, {})
    e = enrich_by_cle.get(cle, {})

    rnc_habit = cp.get("nb_lots_habitation") or 0
    rnc_total = cp.get("nb_lots_total") or 0
    majic_pm_total = e.get("majic_lots") or 0
    sirens = e.get("sirens") or []

    # Identifier le top HLM SIREN (premier dans la liste qui matche HLM_NEEDLES)
    top_hlm = None
    hlm_total_pm = 0
    for s in sirens:
        if is_hlm_denom(s.get("denomination")):
            if top_hlm is None:
                top_hlm = s
            hlm_total_pm += s.get("lots") or 0

    # Calcul prop_habit
    if rnc_total > 0:
        prop_habit = rnc_habit / rnc_total
    elif rnc_habit > 0:
        # Si on n'a que rnc_habit, on assume rnc_total = rnc_habit + delta_estim
        # Fallback : utiliser ratio nb_log_bdnb / majic_pm_total comme proxy
        prop_habit = 1.0  # conservatif (tous logement)
    else:
        prop_habit = 1.0

    # Estimation
    hlm_habit_estim = round(hlm_total_pm * prop_habit, 1)
    pm_habit_estim = round(majic_pm_total * prop_habit, 1)
    pp_habit_estim = round(rnc_habit - pm_habit_estim, 1) if rnc_habit > 0 else None

    # Ratios
    social_pct_avant = (round(hlm_total_pm * 100 / majic_pm_total, 1)
                        if majic_pm_total > 0 else None)
    social_pct_corrige = (round(hlm_habit_estim * 100 / rnc_habit, 1)
                          if rnc_habit > 0 else None)

    return {
        "cle": cle,
        "rnc_habit": rnc_habit,
        "rnc_total": rnc_total,
        "prop_habit": prop_habit,
        "majic_pm_total": majic_pm_total,
        "hlm_total_pm": hlm_total_pm,
        "top_hlm_denom": top_hlm.get("denomination") if top_hlm else None,
        "hlm_habit_estim": hlm_habit_estim,
        "pm_habit_estim": pm_habit_estim,
        "pp_habit_estim": pp_habit_estim,
        "social_pct_avant": social_pct_avant,
        "social_pct_corrige": social_pct_corrige,
        "immat": cp.get("numero_immatriculation")
                  or a.get("numero_immatriculation"),
    }


results = [compute_corrige(c) for c in social_cles]

# ============================================================
# Cas 28 ETIENNE RICHERAND en premier (zoom)
# ============================================================
print()
print("=" * 78)
print(f"[ZOOM] 28|RUE|ETIENNE RICHERAND (AA0358655)")
print("=" * 78)
r28 = next((r for r in results if r["cle"] == CIBLE_28), None)
if r28:
    print(f"  RNC : nb_lots_habitation = {r28['rnc_habit']}, "
          f"nb_lots_total = {r28['rnc_total']}")
    print(f"  prop_habit = {r28['rnc_habit']}/{r28['rnc_total']} = "
          f"{r28['prop_habit']:.4f}")
    print(f"  MAJIC PM total                : {r28['majic_pm_total']}")
    print(f"  MAJIC HLM total (top: {r28['top_hlm_denom']}) : "
          f"{r28['hlm_total_pm']}")
    print(f"  estim HLM_habitation_PM       : {r28['hlm_habit_estim']}")
    print(f"  estim PM_habitation total     : {r28['pm_habit_estim']}")
    print(f"  estim PP_habitation manquantes: {r28['pp_habit_estim']}")
    print()
    print(f"  social_pct AVANT (HLM_PM / total_PM)        : "
          f"{r28['social_pct_avant']}%")
    print(f"  social_pct CORRIGE (HLM_habit_est / RNC_habit): "
          f"{r28['social_pct_corrige']}%")

# ============================================================
# Faux positifs (social_pct_corrige < 60%)
# ============================================================
print()
print("=" * 78)
print(f"FAUX POSITIFS PROBABLES (social_pct_corrige < 60%)")
print("=" * 78)

# Filtre : a besoin de rnc_habit > 0 pour calcul
calc_ok = [r for r in results if r["rnc_habit"] > 0]
print(f"\n  Cles avec RNC habit declarees : {len(calc_ok)}/{len(results)}")
no_calc = [r for r in results if r["rnc_habit"] == 0]
print(f"  Cles sans RNC habit (calcul N/A) : {len(no_calc)}")

faux_pos = [r for r in calc_ok
             if r["social_pct_corrige"] is not None
             and r["social_pct_corrige"] < 60]
faux_pos.sort(key=lambda r: r["social_pct_corrige"])

print(f"\n  {len(faux_pos)} faux positifs identifies (tri pct_corrige ASC)")
print()
print(f"  {'cle':32s} {'RNC_h':>5} {'RNC_t':>5} {'PM_tot':>6} {'HLM_PM':>6} "
      f"{'HLM_habE':>8} {'PP_hE':>5} {'%AV':>5} {'%CO':>6} {'verdict'}")
print("  " + "-" * 124)
for r in faux_pos:
    av = r["social_pct_avant"] if r["social_pct_avant"] is not None else 0
    co = r["social_pct_corrige"]
    verdict = ("FAUX POSITIF MAJEUR" if co < 30
                else "FAUX POSITIF" if co < 60
                else "marginal")
    pp_str = f"{r['pp_habit_estim']:>5.0f}" if r['pp_habit_estim'] is not None else "  -  "
    print(f"  {r['cle']:32s} {r['rnc_habit']:>5} {r['rnc_total']:>5} "
          f"{r['majic_pm_total']:>6} {r['hlm_total_pm']:>6} "
          f"{r['hlm_habit_estim']:>8.0f} {pp_str} "
          f"{av:>4.1f}% {co:>5.1f}% {verdict}")

# Cas social conformes (>= 60%)
print()
print("=" * 78)
print(f"SOCIAL CONFIRMES (social_pct_corrige >= 60%)")
print("=" * 78)
ok = [r for r in calc_ok
      if r["social_pct_corrige"] is not None
      and r["social_pct_corrige"] >= 60]
ok.sort(key=lambda r: -r["social_pct_corrige"])
print(f"\n  {len(ok)} cles confirmees")
print(f"  Top 10 (plus haut social_pct_corrige) :")
for r in ok[:10]:
    co = r["social_pct_corrige"]
    print(f"    {r['cle']:34s} HLM_habit={r['hlm_habit_estim']:>5.0f}/"
          f"{r['rnc_habit']:>3} = {co:>5.1f}%")

# Cles sans RNC habit
if no_calc:
    print()
    print("=" * 78)
    print(f"CALCUL N/A (RNC nb_lots_habitation absent)")
    print("=" * 78)
    print(f"\n  {len(no_calc)} cles (probablement copro_non_immat sans RNC)")
    for r in no_calc[:20]:
        a = by_cle.get(r["cle"], {})
        bdnb = a.get("nb_log_bdnb") or 0
        print(f"    {r['cle']:34s} immat={r['immat'] or '-':12s} "
              f"bdnb={bdnb} PM={r['majic_pm_total']} HLM_PM={r['hlm_total_pm']}")
    if len(no_calc) > 20:
        print(f"    ... +{len(no_calc) - 20} autres")

# ============================================================
# RECAP
# ============================================================
print()
print("=" * 78)
print("RECAP")
print("=" * 78)
print(f"  Cles social total                  : {len(results)}")
print(f"  Cles avec RNC habit > 0            : {len(calc_ok)}")
print(f"  Faux positifs probables (<60%)     : {len(faux_pos)}")
print(f"    dont MAJEUR (<30%)               : "
      f"{sum(1 for r in faux_pos if r['social_pct_corrige'] < 30)}")
print(f"  Social confirmes (>=60%)           : {len(ok)}")
print(f"  Calcul N/A (RNC habit manquant)    : {len(no_calc)}")
print(f"\n  Cas 28 ETIENNE RICHERAND :")
if r28:
    print(f"    social_pct AVANT   = {r28['social_pct_avant']}%")
    print(f"    social_pct CORRIGE = {r28['social_pct_corrige']}%")
    if r28["social_pct_corrige"] is not None and r28["social_pct_corrige"] >= 60:
        print(f"    -> RESTE confirme social (pas un faux positif par cette heuristique)")
    else:
        print(f"    -> Detecte comme faux positif")
