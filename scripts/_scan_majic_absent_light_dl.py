#!/usr/bin/env python3
"""Scan adresses MAJIC presentes dans le perimetre DL mais absentes du light.

Lecture seule.

Methode :
  1. Extraire les voies du perimetre DL depuis light.adresses (set de (TYPE, VOIE))
  2. Filtrer MAJIC (commune 69383) sur ces voies
  3. Normaliser MAJIC en cle_adresse 'NUM|TYPE|VOIE'
     - nature_voie : 'AV'->'AVENUE', 'CRS'->'COURS', 'PAS'->'PASSAGE', 'PL'->'PLACE'
     - nom_voie : strip articles 'DU/DE/LA/LE/DES/D/L', strip hyphens, SAINT->ST
     - numero_voirie : strip leading zeros, append B/T/Q indice si present
  4. Croiser avec light.adresses (cles)
  5. Identifier les MAJIC absents du light
  6. Filtrer : garder uniquement nb_lots_MAJIC >= 3
  7. Trier par nb_lots desc, afficher 20 premiers + stats SIREN
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = Path(r'C:\Users\Station 5\majic_locaux2_2025.parquet')

import pyarrow.parquet as pq

# --- Normalisation ---
TV_MAP = {
    "RUE": "RUE", "AVENUE": "AVENUE", "AV": "AVENUE",
    "COURS": "COURS", "CRS": "COURS",
    "PASSAGE": "PASSAGE", "PAS": "PASSAGE",
    "PLACE": "PLACE", "PL": "PLACE",
    "BOULEVARD": "BOULEVARD", "BD": "BOULEVARD",
    "IMPASSE": "IMPASSE", "IMP": "IMPASSE",
    "ROUTE": "ROUTE", "RTE": "ROUTE",
    "ALLEE": "ALLEE", "ALL": "ALLEE",
    "QUAI": "QUAI",
}

ARTICLES = re.compile(r"^(?:DU|DE|DES|LA|LE|L'|D')\s+")

def norm_voie(s):
    if not s: return ""
    s = str(s).upper().strip()
    # accents -> ASCII
    s = (s.replace("É","E").replace("È","E").replace("Ê","E")
           .replace("À","A").replace("Â","A").replace("Î","I").replace("Ô","O")
           .replace("Û","U").replace("Ç","C"))
    # SAINTE/SAINT -> STE/ST
    s = re.sub(r"\bSAINTE\b", "STE", s)
    s = re.sub(r"\bSAINT\b",  "ST",  s)
    # Hyphens/apostrophes -> espace
    s = s.replace("-", " ").replace("'", " ")
    # Compresser blancs
    s = re.sub(r"\s+", " ", s).strip()
    # Strip articles initiaux (potentiellement repetes)
    while True:
        new = ARTICLES.sub("", s)
        if new == s: break
        s = new
    return s

def norm_num(num_voirie, indice):
    if num_voirie is None: return None
    s = str(num_voirie).strip().lstrip("0")
    if not s: return None
    if indice:
        s = s + str(indice).strip().upper()
    return s

# --- Light : voies du perimetre + cles existantes ---
print("=" * 90)
print("SCAN MAJIC absent light - perimetre Dauphine-Lacassagne")
print("=" * 90)
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
light_cles = set()
light_voies = set()  # (TYPE, VOIE)
for a in ad:
    cle = a.get("cle") or ""
    parts = cle.split("|")
    if len(parts) != 3: continue
    light_cles.add(cle)
    if parts[1] and parts[2]:
        light_voies.add((parts[1], parts[2]))
print(f"  Light : {len(ad)} adresses, {len(light_cles)} cles uniques, {len(light_voies)} voies (TYPE, VOIE) distinctes")

# --- MAJIC DL ---
print()
print("Chargement MAJIC commune 69383 ...")
tbl = pq.read_table(str(MAJIC), filters=[("departement","=","69"),("code_commune","=","383")])
df = tbl.to_pandas()
print(f"  MAJIC commune 69383 : {len(df)} lots, {df[['section','numero_parcelle']].drop_duplicates().shape[0]} parcelles")

# Normalisation par lot
def row_to_cle(r):
    num = norm_num(r["numero_voirie"], r["indice_de_repetition"])
    if not num: return None
    tv = TV_MAP.get(str(r["nature_voie"] or "").strip().upper(), "")
    vo = norm_voie(r["nom_voie"])
    if not tv or not vo: return None
    if (tv, vo) not in light_voies:
        return None  # voie hors perimetre DL
    return f"{num}|{tv}|{vo}"

print()
print("Normalisation + cle_adresse + filtre voies DL...")
df["_cle"] = df.apply(row_to_cle, axis=1)
df_dl = df[df["_cle"].notna()].copy()
print(f"  MAJIC dans perimetre DL : {len(df_dl)} lots, {df_dl['_cle'].nunique()} adresses uniques")

# --- Agreg par adresse ---
print()
print("Agregation par adresse MAJIC...")
def agg_adresse(g):
    sirens = g["numero_siren"].dropna().value_counts()
    if len(sirens):
        top_siren = sirens.index[0]
        top_lots = int(sirens.iloc[0])
        denom = g[g["numero_siren"]==top_siren]["denomination"].dropna().unique()
        top_denom = denom[0] if len(denom) else "?"
        forme = g[g["numero_siren"]==top_siren]["forme_juridique_abregee"].dropna().unique()
        top_forme = forme[0] if len(forme) else "?"
    else:
        top_siren = None; top_lots = 0; top_denom = "?"; top_forme = "?"
    return {
        "nb_lots": len(g),
        "nb_sirens_pm": int(sirens.shape[0]),
        "top_siren": top_siren,
        "top_lots": top_lots,
        "top_denom": top_denom,
        "top_forme": top_forme,
        "parcelles": list(set((g["section"]+g["numero_parcelle"].astype(str)).unique()))[:3],
    }

majic_by_cle = {}
for cle, g in df_dl.groupby("_cle"):
    majic_by_cle[cle] = agg_adresse(g)

print(f"  {len(majic_by_cle)} adresses MAJIC agregees")

# --- Diff : MAJIC absent light ---
absent = [(cle, majic_by_cle[cle]) for cle in majic_by_cle if cle not in light_cles]
print()
print(f"Diff MAJIC vs light :")
print(f"  MAJIC adresses (perimetre DL) : {len(majic_by_cle)}")
print(f"  Light cles correspondantes    : {len([c for c in majic_by_cle if c in light_cles])}")
print(f"  MAJIC ABSENT du light         : {len(absent)}")

# Filtre nb_lots >= 3
filtered = [(c, a) for c, a in absent if a["nb_lots"] >= 3]
print(f"  Filtres nb_lots >= 3          : {len(filtered)}  (exclus {len(absent)-len(filtered)} micro-parcelles)")

# Tri par nb_lots desc
filtered.sort(key=lambda x: -x[1]["nb_lots"])

print()
print("=" * 90)
print(f"TOP 20 - MAJIC absents du light (nb_lots desc) :")
print("=" * 90)
print(f"  {'#':3s} {'cle':36s} {'lots':>4s} {'PM':>3s}  {'top_lots':>4s} {'forme':>5s}  parcelles    top_denom")
print("  " + "-"*120)
for i, (cle, a) in enumerate(filtered[:20], 1):
    parc_str = ",".join(a["parcelles"][:2])
    print(f"  {i:3d} {cle:36s} {a['nb_lots']:>4d} {a['nb_sirens_pm']:>3d}  "
          f"{a['top_lots']:>4d} {(a['top_forme'] or '?')[:5]:>5s}  {parc_str:<14s}  "
          f"{(a['top_denom'] or '?')[:48]}")

# Stats supplementaires
print()
print("=" * 90)
print("Stats supplementaires :")
print("=" * 90)
buckets = defaultdict(int)
for cle, a in filtered:
    n = a["nb_lots"]
    if n < 5: buckets["3-4 lots"] += 1
    elif n < 10: buckets["5-9 lots"] += 1
    elif n < 20: buckets["10-19 lots"] += 1
    elif n < 50: buckets["20-49 lots"] += 1
    else: buckets[">=50 lots"] += 1
print(f"  Distribution nb_lots (filtre >=3) :")
for k in ["3-4 lots","5-9 lots","10-19 lots","20-49 lots",">=50 lots"]:
    print(f"    {k:12s} : {buckets[k]}")

# Voies les plus touchees
voies_cnt = defaultdict(int)
for cle, _ in filtered:
    parts = cle.split("|")
    voies_cnt[f"{parts[1]} {parts[2]}"] += 1
print()
print(f"  Top 10 voies touchees (n adresses absentes light) :")
for v, n in sorted(voies_cnt.items(), key=lambda x: -x[1])[:10]:
    print(f"    {n:3d}  {v}")

# Sauvegarde plan complet pour examen
OUT = ROOT / "data" / "_scan_majic_absent_light_dl.txt"
with OUT.open("w", encoding="utf-8") as f:
    f.write(f"# Scan MAJIC adresses absentes light DL - {len(filtered)} cas (>= 3 lots)\n")
    f.write(f"# Tri par nb_lots desc\n\n")
    for i, (cle, a) in enumerate(filtered, 1):
        f.write(f"{i}. {cle}\n")
        f.write(f"   -> nb_lots_MAJIC : {a['nb_lots']}  | nb_SIRENs PM : {a['nb_sirens_pm']}\n")
        f.write(f"   -> top SIREN : {a['top_siren']} - {a['top_denom']} ({a['top_lots']} lots, {a['top_forme']})\n")
        f.write(f"   -> parcelles : {','.join(a['parcelles'])}\n\n")
print()
print(f"  Liste complete sauvegardee : {OUT.name} ({len(filtered)} cas)")
print()
print("=" * 90)
print(">>> SCAN TERMINE - lecture seule")
print("=" * 90)
