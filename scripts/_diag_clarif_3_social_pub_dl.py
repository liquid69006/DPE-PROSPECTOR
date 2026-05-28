#!/usr/bin/env python3
"""Clarification 2 points apres ultime scan :
   1. Ecart cache local 592 vs KV live cloud (requiert DPE_JWT)
   2. Tag actuel exact des 3 social/public (117 BARABAN, 141 DAUPHINE,
      24 FREDERIC MISTRAL) : deja reclassees mixte ?

LECTURE SEULE.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

JWT = os.environ.get("DPE_JWT") or ""

CIBLES_3 = ["117|RUE|BARABAN", "141|RUE|DAUPHINE",
            "24|RUE|FREDERIC MISTRAL"]


# ============================================================
print("=" * 78)
print("CLARIFICATION : ecart cache/cloud + tag actuel des 3 social/public")
print("=" * 78)

# Local
kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns_local = kv_local.get("assignments") or {}
print(f"\n[LOCAL] _kv_assign_dl.json : {len(assigns_local)} assignments")

# Cloud (si JWT dispo)
assigns_cloud = None
if JWT:
    print(f"\n[CLOUD] GET via DPE_JWT...")
    req = urllib.request.Request(
        f"{API}/secteur-assignments/{AGENCE}",
        headers={"Authorization": f"Bearer {JWT}", "User-Agent": UA,
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        assigns_cloud = body.get("assignments") or {}
        print(f"  status=200  assignments={len(assigns_cloud)}")
    except urllib.error.HTTPError as e:
        print(f"  [err] HTTP {e.code} : {e.read().decode('utf-8','replace')[:100]}")
    except Exception as e:
        print(f"  [err] {e}")
else:
    print(f"\n[CLOUD] env DPE_JWT absente -> impossible de comparer")
    print(f"        Pour comparer : pose ton JWT puis relance ce script.")

# ============================================================
# POINT 1 : ecart cache local vs cloud
# ============================================================
print()
print("=" * 78)
print("POINT 1 : ecart cache local vs cloud")
print("=" * 78)

if assigns_cloud is None:
    print("\n  (Impossible sans JWT live)")
else:
    print(f"\n  Local : {len(assigns_local)}  |  Cloud : {len(assigns_cloud)}")
    cles_local = set(assigns_local)
    cles_cloud = set(assigns_cloud)
    only_local = cles_local - cles_cloud
    only_cloud = cles_cloud - cles_local
    common = cles_local & cles_cloud
    diff_type = []
    for c in common:
        tl = (assigns_local.get(c) or {}).get("type")
        tc = (assigns_cloud.get(c) or {}).get("type")
        if tl != tc:
            diff_type.append((c, tl, tc))
    print(f"  Only local  : {len(only_local)}")
    print(f"  Only cloud  : {len(only_cloud)}")
    print(f"  Common, tag diff : {len(diff_type)}")

    if only_local:
        print(f"\n  Cles uniquement local (premier 15) :")
        for c in sorted(only_local)[:15]:
            print(f"    {c:34s} local_tag={(assigns_local.get(c) or {}).get('type')}")
        if len(only_local) > 15:
            print(f"    ... +{len(only_local) - 15} autres")
    if only_cloud:
        print(f"\n  Cles uniquement cloud (premier 15) :")
        for c in sorted(only_cloud)[:15]:
            print(f"    {c:34s} cloud_tag={(assigns_cloud.get(c) or {}).get('type')}")
        if len(only_cloud) > 15:
            print(f"    ... +{len(only_cloud) - 15} autres")
    if diff_type:
        print(f"\n  Cles avec tag different (premier 15) :")
        for c, tl, tc in diff_type[:15]:
            print(f"    {c:34s} local='{tl}' cloud='{tc}'")
        if len(diff_type) > 15:
            print(f"    ... +{len(diff_type) - 15} autres")

# ============================================================
# POINT 2 : tag actuel exact des 3 social/public
# ============================================================
print()
print("=" * 78)
print("POINT 2 : tag actuel exact des 3 cles 'social/public' detectees")
print("=" * 78)

# Charger overrides
overrides_by_cle = {}
if OVERRIDES.exists():
    ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    overrides_by_cle = {o["cle"]: o for o in ov.get("overrides", [])}

print(f"\n  Overrides _social_overrides_dl.json : {len(overrides_by_cle)} cles")

for cle in CIBLES_3:
    print(f"\n  --- {cle} ---")
    # Local
    vl = assigns_local.get(cle)
    print(f"    [LOCAL]  {vl}")
    # Cloud
    if assigns_cloud is not None:
        vc = assigns_cloud.get(cle)
        print(f"    [CLOUD]  {vc}")
        sync = (vl == vc)
        print(f"    [SYNC]   local == cloud ? {sync}")
    # Override
    ov = overrides_by_cle.get(cle)
    if ov:
        print(f"    [OVERRIDE]")
        print(f"      previous_tag       : {ov.get('previous_tag')}")
        print(f"      new_tag            : {ov.get('new_tag')}")
        print(f"      qualif_source      : {ov.get('qualif_source')}")
        print(f"      social_pct_corrige : {ov.get('social_pct_corrige')}")
        print(f"      mut_apt_per_year   : {ov.get('mut_apt_per_year')}")
        print(f"      reason             : {ov.get('reason')}")
    else:
        print(f"    [OVERRIDE] (absente)")

# ============================================================
# Synthese
# ============================================================
print()
print("=" * 78)
print("SYNTHESE")
print("=" * 78)
n_in_ov = sum(1 for c in CIBLES_3 if c in overrides_by_cle)
print(f"  Cles ciblees                          : {len(CIBLES_3)}")
print(f"  Dont presentes dans overrides         : {n_in_ov}")
n_currently_mixte = sum(1 for c in CIBLES_3
                         if (assigns_local.get(c) or {}).get("type") == "mixte")
print(f"  Dont actuellement tag='mixte' (local) : {n_currently_mixte}")

print()
print("  Si elles sont DEJA 'mixte' dans le cloud :")
print("    -> c'est NORMAL qu'elles passent le filtre Sans ventes")
print("       (mixte = type valide pour Sans ventes UI)")
print("    -> NE PAS les re-tagger 'social' : le reclass DVF decollect")
print("       les a SORTIES du social a juste titre.")
print("    -> Mon ultime scan a fausse positivement signale ces 3 cles")
print("       comme 'a re-tagger social' a cause de l'heuristique HLM")
print("       dominant MAJIC (qui est precisement le faux positif corrige).")
