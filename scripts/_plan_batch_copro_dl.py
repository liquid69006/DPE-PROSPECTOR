#!/usr/bin/env python3
"""Plan batch copro_non_immat DL - lecture seule.

1. GET KV server
2. Identifier hr-ancres non qualifiees
3. Sanity check : 0 tertiaire + 0 100% bailleur social
4. Afficher plan (cles a poster copro_non_immat) + stats

Aucun POST.
"""
import json, sys, os, urllib.request
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
OUT = ROOT / "data" / "_plan_batch_copro_dl.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

BAILLEURS_SOCIAUX = [
    "CDC HABITAT","ALLIADE HABITAT","GRAND LYON HABITAT","GRANDLYON HABITAT",
    "OPH ","OPH DE","OPHLM","HBM","HLM","HABITAT ET HUMANIS","DYNACITE",
    "EST METROPOLE HABITAT","SCIC HABITAT","ICF HABITAT","RHONE SAONE HABITAT",
    "ADOMA","FONCIERE LOGEMENT","ERILIA","CDC HAB","FRANCE LOGEMENT","SCI 3F",
    "IMMOBILIERE 3F","ALILA","NEXITY DOMAINES","SOLLAR","BATIGERE","NOVEDIS",
    "FREHA","SCIC RHONE-ALPES","SOCIETE LYONNAISE","OPHEOR","OPAC",
    "IMMOBILIERE RHONE ALPES","ICF SUD-EST",
    "SA HLM","SA D'HLM","SA DE HLM",
    "FONCIERE D'HABITAT ET HUM","3F RESIDENCES","ACTION SOCIALE","IN'LI",
    "FONCIERE VESTA","HOSPICES CIVILS","SA DE CONSTRUCTION DE LA VILLE",
    "SEM DE CONSTRUCTION","COMMUNE DE LYON","COMMUNAUTE URBAINE DE LYON",
    "DEPARTEMENT DU RHONE",
]
def is_bs(d):
    if not d: return False
    s = str(d).upper()
    return any(k in s for k in BAILLEURS_SOCIAUX)
def to_int(x):
    try: return int(x)
    except: return 0
def usage_class(u):
    if not u: return "Inconnu"
    s = str(u).upper().replace("É", "E")
    if "TERTIAIRE" in s: return "Tertiaire"
    if "RESIDENTIEL" in s: return "Residentiel"
    return "Inconnu"

# --- ETAPE 1 : GET KV ---
print("=" * 90)
print("ETAPE 1 - GET KV server")
print("=" * 90)
req = urllib.request.Request(ENDPOINT, headers={
    "Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    kv = json.loads(r.read().decode("utf-8"))
assignments = kv.get("assignments") or {}
print(f"  Assignments : {len(assignments)}")
print(f"  Fusions     : {len(kv.get('fusions') or {})}")
print(f"  Noms        : {len(kv.get('noms') or {})}")

# --- ETAPE 2 : hr-ancres non qualifiees ---
print()
print("=" * 90)
print("ETAPE 2 - hr-ancres non qualifiees")
print("=" * 90)
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
iris_name = {x["code_iris"]: x.get("nom_iris", "?") for x in (doc.get("iris") or [])}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

hr_ancres = []
for a in ad:
    cle = a.get("cle") or ""
    if cle in co_by_cle: continue
    if a.get("numero_immatriculation"): continue
    if a.get("_fusion_auto"): continue
    hr_ancres.append(a)

hr_nq = [a for a in hr_ancres if (a.get("cle") or "") not in assignments]
print(f"  hr-ancres total          : {len(hr_ancres)}")
print(f"  hr-ancres deja en KV     : {len(hr_ancres) - len(hr_nq)}")
print(f"  hr-ancres NON qualifiees : {len(hr_nq)}")

# --- ETAPE 3 : Sanity check (0 tertiaire, 0 100% bailleur social) ---
print()
print("=" * 90)
print("ETAPE 3 - Sanity check categories A (tertiaire) + B (100% bailleur social)")
print("=" * 90)
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich.get("results") or []}

A_tert, B_social = [], []
for a in hr_nq:
    cle = a.get("cle") or ""
    if usage_class(a.get("usage_principal_bdnb")) == "Tertiaire":
        A_tert.append(cle); continue
    e = enrich_by_cle.get(cle, {}) or {}
    lots = e.get("majic_lots", 0)
    if lots <= 0: continue
    sirens = e.get("sirens") or []
    lots_bs = sum(s.get("lots", 0) for s in sirens if is_bs(s.get("denomination", "")))
    pct_bs = (100.0 * lots_bs / lots) if lots else 0.0
    if pct_bs >= 100.0: B_social.append((cle, sirens))

print(f"  Cat A - Tertiaires non qualifies : {len(A_tert)}")
for cle in A_tert: print(f"    ANOMALIE - {cle}")
print(f"  Cat B - 100% bailleur social non qualifies : {len(B_social)}")
for cle, sirens in B_social:
    top = max(sirens, key=lambda s: s.get("lots", 0))
    print(f"    ANOMALIE - {cle:32s} {top.get('denomination','?')[:40]} ({top.get('lots',0)} lots)")

if A_tert or B_social:
    print()
    print("  >>> ATTENTION : anomalies trouvees. A traiter avant batch copro_non_immat.")
else:
    print()
    print("  >>> OK : 0 tertiaire + 0 100% bailleur social non qualifie.")

# --- ETAPE 4 : Plan copro_non_immat ---
print()
print("=" * 90)
print("ETAPE 4 - Plan batch copro_non_immat (le reste)")
print("=" * 90)

# Reste = hr_nq - A - B (mais on ne devrait pas en avoir)
exclus = set(A_tert) | {c for c, _ in B_social}
plan = [a for a in hr_nq if (a.get("cle") or "") not in exclus]
plan.sort(key=lambda a: (a.get("code_iris") or "?", a.get("cle") or ""))

print(f"  Cibles plan copro_non_immat : {len(plan)}")

# Distribution par IRIS + usage
by_iris = defaultdict(lambda: {"resid": 0, "inconnu": 0})
by_usage = defaultdict(int)
no_majic, divers, mono_majic_low = 0, 0, 0
for a in plan:
    u = usage_class(a.get("usage_principal_bdnb"))
    by_usage[u] += 1
    iris = a.get("code_iris") or "?"
    if u == "Residentiel": by_iris[iris]["resid"] += 1
    else: by_iris[iris]["inconnu"] += 1
    e = enrich_by_cle.get(a.get("cle") or "", {}) or {}
    sirens = e.get("sirens") or []
    if e.get("majic_lots", 0) <= 0: no_majic += 1
    elif len(sirens) >= 2: divers += 1
    else: mono_majic_low += 1

print()
print(f"  Distribution usage :")
for u, n in sorted(by_usage.items(), key=lambda x: -x[1]):
    print(f"    {u:12s} : {n}")
print()
print(f"  Profils MAJIC PM :")
print(f"    sans MAJIC PM   : {no_majic}  (100% personnes physiques)")
print(f"    diversifie 2+ SIREN PM : {divers}")
print(f"    MAJIC mono <90% : {mono_majic_low}")
print()
print(f"  Distribution par IRIS :")
for iris in sorted(by_iris.keys()):
    s = by_iris[iris]
    nom = iris_name.get(iris, "?")
    n = s["resid"] + s["inconnu"]
    print(f"    {iris} {nom[:30]:30s} : {n}  (resid={s['resid']}, inconnu={s['inconnu']})")

# Sauvegarde plan
OUT.write_text(json.dumps({
    "n_plan": len(plan),
    "filtre": "hr-ancres non qualifiees (apres exclusion tertiaire + 100% bailleur social)",
    "plan": [{"cle": a.get("cle"), "type": "copro_non_immat"} for a in plan],
    "kv_actuel_size": len(assignments),
    "kv_apres_post_size": len(assignments) + len(plan),
}, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print(f"  Plan sauvegarde : {OUT.name}")
print(f"  KV size apres POST : {len(assignments)} -> {len(assignments) + len(plan)}")

print()
print("=" * 90)
print(f">>> PLAN PRET ({len(plan)} cles) - AUCUN POST EFFECTUE")
print("=" * 90)
