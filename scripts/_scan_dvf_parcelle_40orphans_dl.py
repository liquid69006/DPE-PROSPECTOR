#!/usr/bin/env python3
"""Scan DVF par PARCELLE BDNB sur 40 orphans DL (lecture seule).

Pour chaque cle marquee _bdnb_match=bdnb_orphelin :
  1. Recupere parcelle BDNB via API live (rel_batiment_groupe_parcelle)
  2. Cherche dans DVF toutes les mutations sur (section + No plan) de cette parcelle
  3. Aggrege par mutation (date + dispo + valeur)
  4. Affiche cles avec >=1 mutation, tri par nb_mutations desc

DVF schema utilise : 'Section' (ex 'DS'), 'No plan' (ex 100 -> '0100'),
'Code commune' (ex '383' pour Lyon 3e), 'Nature mutation', 'Type local',
'Valeur fonciere', 'Date mutation', 'Surface reelle bati', etc.
"""
import json, sys, re, urllib.request, time
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
UA = "Mozilla/5.0 diag/1.0"

ORPHAN_MARKER = "fix_bdnb_orphelin_dl_2026-05-23"

# --- 1. Load 40 orphans ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
orphans = [a for a in doc["adresses"] if a.get("_injection_bdnb_orphelin") == ORPHAN_MARKER]
print(f"Orphans dans light : {len(orphans)}")

# --- 2. Fetch parcelles via BDNB API (cache locally) ---
PARC_CACHE_FILE = ROOT / "data" / "_parc_cache_orphans40.json"
PARC_CACHE = {}
if PARC_CACHE_FILE.exists():
    PARC_CACHE = json.loads(PARC_CACHE_FILE.read_text(encoding="utf-8"))
    print(f"Cache parcelles charge : {len(PARC_CACHE)} entrees")

def bdnb_parc(bg):
    if bg in PARC_CACHE: return PARC_CACHE[bg]
    url = f"https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            rs = json.loads(r.read())
        parcs = [x.get("parcelle_id") for x in rs if x.get("parcelle_id")]
    except Exception as e:
        parcs = []
    PARC_CACHE[bg] = parcs
    time.sleep(0.05)
    return parcs

print("Recuperation parcelles BDNB pour 40 orphans (cache si dispo)...")
for o in orphans:
    bg = o.get("batiment_groupe_id")
    if bg:
        o["_parcs"] = bdnb_parc(bg)
    else:
        o["_parcs"] = []

# Save cache
PARC_CACHE_FILE.write_text(json.dumps(PARC_CACHE, ensure_ascii=False, indent=2), encoding="utf-8")

# --- 3. Index DVF par (section + No plan) en commune 383 ---
print("Chargement DVF + index par parcelle...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
# parcelle key = section.zfill(2) + No_plan.zfill(4) (ex 'DS0100')
dvf_by_parc = defaultdict(list)
for m in dvf:
    cc = str(m.get("Code commune","") or "").strip()
    if cc != "383": continue  # Lyon 3e
    sec = str(m.get("Section","") or "").strip().upper()
    plan = str(m.get("No plan","") or "").strip()
    if not sec or not plan: continue
    try:
        plan_int = int(plan)
    except:
        continue
    key = f"{sec}{plan_int:04d}"  # ex DS0100
    dvf_by_parc[key].append(m)
print(f"  {sum(len(v) for v in dvf_by_parc.values())} mutations DVF Lyon 3e, {len(dvf_by_parc)} parcelles distinctes")

# --- 4. Pour chaque orphan : chercher mutations par parcelle ---
def parse_parcelle_id(p):
    """'69383000DS0100' -> 'DS0100'."""
    if not p or len(p) < 14: return None
    return p[8:]

def fnum(v):
    if v is None: return None
    s = str(v).strip().replace(" ","").replace(",",".")
    try: return float(s)
    except: return None

results = []
for o in orphans:
    cle = o.get("cle")
    parcs = o.get("_parcs") or []
    if not parcs: continue
    all_muts = []
    for p in parcs:
        key = parse_parcelle_id(p)
        if not key: continue
        all_muts.extend(dvf_by_parc.get(key, []))
    if not all_muts: continue
    # Agreger par mutation (date + dispo + valeur)
    by_mut = defaultdict(list)
    for m in all_muts:
        k = (m.get("Date mutation"), m.get("No disposition"), m.get("Valeur fonciere"))
        by_mut[k].append(m)
    results.append({
        "cle": cle,
        "bdnb": o.get("nb_log_bdnb"),
        "annee": o.get("annee_construction"),
        "parcs": [parse_parcelle_id(p) for p in parcs if parse_parcelle_id(p)],
        "by_mut": by_mut,
        "n_mut": len(by_mut),
    })

results.sort(key=lambda r: -r["n_mut"])
total_muts = sum(r["n_mut"] for r in results)

# --- 5. Display ---
print()
print("=" * 100)
print(f"SCAN DVF PAR PARCELLE - 40 orphans DL : {len(results)} avec mutations / {len(orphans)} total")
print(f"  Total mutations distinctes : {total_muts}")
print("=" * 100)

for r in results:
    print()
    parc_str = ",".join(r["parcs"])
    bdnb_str = str(r["bdnb"] or '?')
    annee_str = str(r["annee"] or '?')
    print(f"  {r['cle']:36s}  bdnb={bdnb_str} an={annee_str} parc={parc_str}  mutations={r['n_mut']}")
    for k in sorted(r["by_mut"].keys()):
        date, dispo, val = k
        v = fnum(val)
        lst = r["by_mut"][k]
        types = sorted(set((m.get("Type local","") or "").strip() or "(vide)" for m in lst))
        natures = sorted(set((m.get("Nature mutation","") or "").strip() for m in lst))
        surf = sum(int(m.get("Surface reelle bati","0") or 0) for m in lst)
        pieces = sum(int(m.get("Nombre pieces principales","0") or 0) for m in lst)
        # Adresses DVF
        addrs = set()
        for m in lst:
            no = str(m.get("No voie","") or "").strip().lstrip("0")
            bt = str(m.get("B/T/Q","") or "").strip().upper()
            tv = (m.get("Type de voie","") or "").strip()
            vo = (m.get("Voie","") or "").strip()
            if no:
                addrs.add(f"{no}{bt} {tv} {vo}".strip())
        v_str = f"{v:>10,.0f}".replace(",", " ") if v else "         ?"
        print(f"      {date}  val={v_str} EUR  nat={natures[0]:<15s}  type={'+'.join(types):<30s}  n_lots={len(lst)} surf={surf}m2 pieces={pieces}")
        for ad in sorted(addrs)[:3]:
            print(f"        adresse DVF : {ad!r}")

# --- Bilan ---
print()
print("=" * 100)
print(f"BILAN scan DVF par parcelle")
print("=" * 100)
print(f"  Orphans scannes               : {len(orphans)}")
print(f"  Orphans avec mutations DVF    : {len(results)}")
print(f"  Total mutations distinctes    : {total_muts}")
print()
# Stats types
from collections import Counter
all_types = Counter()
all_natures = Counter()
for r in results:
    for k, lst in r["by_mut"].items():
        for m in lst:
            all_types[(m.get("Type local","") or "").strip() or "(vide)"] += 1
            all_natures[(m.get("Nature mutation","") or "").strip()] += 1
print(f"  Distribution types_local (toutes mutations) :")
for t, n in sorted(all_types.items(), key=lambda x: -x[1]):
    print(f"    {t:25s} : {n}")
print()
print(f"  Distribution natures (toutes mutations) :")
for nat, n in sorted(all_natures.items(), key=lambda x: -x[1]):
    print(f"    {nat:25s} : {n}")

print()
print(f"  Cache parcelles sauvegarde : {PARC_CACHE_FILE.name} ({len(PARC_CACHE)} entrees)")
print("=" * 100)
