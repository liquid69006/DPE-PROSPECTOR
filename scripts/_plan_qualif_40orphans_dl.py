#!/usr/bin/env python3
"""Plan qualification 40 orphans BDNB DL - lecture seule.

ETAPE 1 : GET KV server
ETAPE 2 : Analyser chaque orphan (usage BDNB + MAJIC + KV actuel)
ETAPE 3 : Trier (social / mono / copro_non_immat / bureaux)
ETAPE 4 : Afficher plan (sans poster)
"""
import json, re, sys, os, urllib.request, unicodedata
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC_PARQ = Path(r"C:\Users\Station 5\majic_locaux2_2025.parquet")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}

BAILLEURS_SOCIAUX = [
    "CDC HABITAT","ALLIADE","GRAND LYON HABITAT","GRANDLYON HABITAT",
    "OPH ","OPH DE","OPHLM","HBM","HLM","HABITAT ET HUMANIS","DYNACITE",
    "EST METROPOLE HABITAT","SCIC HABITAT","ICF HABITAT","RHONE SAONE HABITAT",
    "ADOMA","FONCIERE LOGEMENT","ERILIA","CDC HAB","FRANCE LOGEMENT","SCI 3F",
    "IMMOBILIERE 3F","ALILA","NEXITY DOMAINES","SOLLAR","BATIGERE","NOVEDIS",
    "FREHA","SCIC RHONE-ALPES","SOCIETE LYONNAISE","OPHEOR","OPAC",
    "IMMOBILIERE RHONE ALPES","ICF SUD-EST","FONCIERE VESTA",
    "SA HLM","SA D'HLM","SA DE HLM","FONCIERE D'HABITAT ET HUM",
    "3F RESIDENCES","ACTION SOCIALE","IN'LI","HOSPICES CIVILS",
    "SA DE CONSTRUCTION DE LA VILLE","SEM DE CONSTRUCTION","COMMUNE DE LYON",
    "COMMUNAUTE URBAINE DE LYON","DEPARTEMENT DU RHONE","FONDATION ARALIS",
    "METROPOLE DE LYON",
]
def is_bs(d):
    if not d: return False
    s = str(d).upper()
    return any(k in s for k in BAILLEURS_SOCIAUX)

# --- Normalisation voie commune ---
ARTICLES = re.compile(r"^(?:DU|DE|DES|LA|LE|L'|D')\s+")
def _noacc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")
def norm_voie(s):
    if not s: return ""
    s = _noacc(str(s)).upper().strip()
    s = re.sub(r"\bSAINTE\b","STE", s); s = re.sub(r"\bSAINT\b","ST", s)
    s = s.replace("-"," ").replace("'"," ")
    s = re.sub(r"\s+"," ", s).strip()
    while True:
        new = ARTICLES.sub("", s)
        if new == s: break
        s = new
    return s

def parse_cle(cle):
    m = re.match(r"^(\d+)([A-Z]*)\|([A-Z]+)\|(.+)$", cle)
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None

# ============================================================
# ETAPE 1 : GET KV
# ============================================================
print("=" * 90)
print("ETAPE 1 - GET KV server")
print("=" * 90)
req = urllib.request.Request(ENDPOINT, headers=HDR)
with urllib.request.urlopen(req, timeout=20) as r:
    kv = json.loads(r.read().decode("utf-8"))
assigns = kv.get("assignments") or {}
print(f"  KV server : {len(assigns)} assigns")

# ============================================================
# ETAPE 2 : Charger orphans + MAJIC
# ============================================================
print()
print("=" * 90)
print("ETAPE 2 - Charger 40 orphans + MAJIC")
print("=" * 90)
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ORPHAN_MARKER = "fix_bdnb_orphelin_dl_2026-05-23"
orphans = [a for a in doc["adresses"] if a.get("_injection_bdnb_orphelin") == ORPHAN_MARKER]
print(f"  Orphans dans light : {len(orphans)}")

# MAJIC commune 69383
import pyarrow.parquet as pq
print(f"  Chargement MAJIC ...")
tbl = pq.read_table(str(MAJIC_PARQ), filters=[("departement","=","69"),("code_commune","=","383")])
df = tbl.to_pandas()
df["_num_str"] = df["numero_voirie"].fillna("").astype(str).str.lstrip("0")
df["_indice"]  = df["indice_de_repetition"].fillna("").astype(str).str.strip().str.upper()
TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","BD":"BOULEVARD","PL":"PLACE",
          "PAS":"PASSAGE","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI"}
df["_tv"] = df["nature_voie"].fillna("").map(lambda x: TV_MAP.get(str(x).strip().upper(), ""))
df["_voie"] = df["nom_voie"].fillna("").map(norm_voie)
print(f"  MAJIC DL : {len(df)} lots indexes")

# ============================================================
# ETAPE 3 : Analyse + suggestion
# ============================================================
print()
print("=" * 90)
print("ETAPE 3 - Analyse + classification")
print("=" * 90)

def analyze(a):
    cle = a.get("cle")
    p = parse_cle(cle)
    if not p: return None
    num, suffix, tv, voie = p
    voie_n = norm_voie(voie)
    m = df[(df["_num_str"]==num) & (df["_indice"]==suffix) &
           (df["_tv"]==tv) & (df["_voie"]==voie_n)]
    n_lots = len(m)
    sirens = m["numero_siren"].dropna().value_counts() if n_lots else None
    top_siren = top_lots = pct_top = None
    top_denom = ""
    n_sirens = 0
    pct_bs = 0.0
    if sirens is not None and len(sirens):
        n_sirens = len(sirens)
        top_siren = sirens.index[0]
        top_lots = int(sirens.iloc[0])
        denoms = m[m["numero_siren"]==top_siren]["denomination"].dropna().unique()
        top_denom = denoms[0] if len(denoms) else "?"
        pct_top = (100.0 * top_lots / n_lots) if n_lots else 0.0
        lots_bs = sum(int(sirens.iloc[i]) for i in range(len(sirens))
                      if is_bs(m[m["numero_siren"]==sirens.index[i]]["denomination"].dropna().iloc[0]
                               if len(m[m["numero_siren"]==sirens.index[i]]) else ""))
        pct_bs = (100.0 * lots_bs / n_lots) if n_lots else 0.0

    return {
        "cle": cle, "bdnb": a.get("nb_log_bdnb"), "annee": a.get("annee_construction"),
        "usage": a.get("usage_principal_bdnb"),
        "majic_lots": n_lots, "n_sirens": n_sirens,
        "top_siren": top_siren, "top_lots": top_lots,
        "top_denom": top_denom, "pct_top": pct_top, "pct_bs": pct_bs,
        "kv_cur": assigns.get(cle),
    }

results = []
for a in orphans:
    r = analyze(a)
    if r: results.append(r)

def suggest(r):
    usage = (r["usage"] or "").upper().replace("É","E")
    if "TERTIAIRE" in usage:
        return ("bureaux", "usage Tertiaire BDNB")
    if r["pct_bs"] >= 80.0:
        return ("social", f"{int(r['pct_bs'])}% bailleur social MAJIC")
    if r["majic_lots"] and r["pct_top"] and r["pct_top"] >= 90.0:
        return ("mono", f"1 SIREN {int(r['pct_top'])}% MAJIC ({r['top_denom'][:25]})")
    if r["majic_lots"] == 0:
        return ("copro_non_immat", "0 lot MAJIC PM (100% PP probable, copro PP)")
    return ("copro_non_immat", f"MAJIC {r['majic_lots']} lots / {r['n_sirens']} SIREN (diversifie)")

for r in results:
    r["sugg_type"], r["sugg_just"] = suggest(r)

# Tri par sugg_type puis bdnb desc
SORT_ORDER = {"social":0, "mono":1, "bureaux":2, "copro_non_immat":3}
results.sort(key=lambda r: (SORT_ORDER.get(r["sugg_type"], 9), -(r["bdnb"] or 0)))

# ============================================================
# ETAPE 4 : Affichage plan
# ============================================================
print()
print("=" * 90)
print("ETAPE 4 - Plan qualifications suggerees (NE PAS POSTER ENCORE)")
print("=" * 90)

dist = defaultdict(list)
for r in results:
    dist[r["sugg_type"]].append(r)

for typ in ("social","mono","bureaux","copro_non_immat"):
    items = dist.get(typ, [])
    if not items: continue
    print()
    print("#" * 90)
    print(f"# {typ.upper()} ({len(items)})")
    print("#" * 90)
    for r in items:
        kv_str = f" KV={r['kv_cur']!r}" if r['kv_cur'] else ""
        majic_str = ""
        if r['majic_lots']:
            majic_str = f" MAJIC={r['top_lots']}/{r['majic_lots']}({int(r['pct_top'])}%){r['n_sirens']}s {r['top_denom'][:25]!r}"
        annee = str(r['annee'] or '?')
        print(f"  {r['cle']:36s}  bdnb={r['bdnb']:>3d} an={annee:>5s}{majic_str}{kv_str}")
        print(f"      >>> {typ}  ({r['sugg_just']})")

# Bilan
print()
print("=" * 90)
print("BILAN PLAN")
print("=" * 90)
total = sum(len(v) for v in dist.values())
print(f"  Total analysis : {total}")
for typ in ("social","mono","bureaux","copro_non_immat"):
    n = len(dist.get(typ,[]))
    if n: print(f"    {typ:24s} : {n}")
already_kv = sum(1 for r in results if r["kv_cur"])
print(f"  Deja en KV (override) : {already_kv}")
print(f"  Nouvelles cles a poster : {total - already_kv}")
print()
print(f"  >>> AUCUN POST EFFECTUE - plan pret pour exec ulterieure")
print("=" * 90)
