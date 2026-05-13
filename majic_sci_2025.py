"""
majic_sci_2025.py
─────────────────────────────────────────────────────────────────
Extrait les SCI propriétaires dans les zones Dauphiné-Lacassagne
et Montchat depuis le fichier MAJIC 2025 (locaux, parquet).

Workflow :
  1. Lecture fichier parquet MAJIC 2025 (locaux)
  2. Filtre : code_insee 69383 (Lyon 3e) + forme_juridique 6540 (SCI)
  3. Déduplication par (section + numero_parcelle + siren)
  4. Géocodage BAN pour obtenir les coordonnées GPS
  5. Filtrage par polygone exact (Dauphiné / Montchat)
  6. Enrichissement API Recherche Entreprises (dirigeants, siège)
  7. Export JSON + CSV

Usage :
  python majic_sci_2025.py --fichier majic_locaux2_2025.parquet
"""

import argparse
import csv
import json
import time
import urllib.request
import urllib.parse
from collections import Counter
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq
from shapely.geometry import Point, Polygon

# ── Zones ─────────────────────────────────────────────────────────
ZONES = {
    "Dauphiné-Lacassagne": Polygon([
        [4.860882903977199,  45.763666847297316],
        [4.860095318969854,  45.74943467306812],
        [4.871239646832663,  45.74553255509332],
        [4.87391743586096,   45.7506712028316],
        [4.869743235317657,  45.75278697910744],
        [4.87364178110758,   45.75449053288179],
        [4.87525633037356,   45.754847723046254],
        [4.87616205313347,   45.75490267517603],
        [4.876634604137479,  45.75833707592611],
        [4.873773912182969,  45.758707127819065],
        [4.874885840542078,  45.76058202973891],
        [4.871798156197514,  45.761682107375805],
        [4.870115856267233,  45.76371663644693],
        [4.860882903977199,  45.763666847297316],
    ]),
    "Montchat": Polygon([
        [4.8696556919393,    45.752807471686765],
        [4.873968991938966,  45.750648569367286],
        [4.8712261737505,    45.74554776311837],
        [4.878425233301357,  45.74309361037359],
        [4.878697742930143,  45.74276386559836],
        [4.884055610780678,  45.74164596308222],
        [4.892083206597164,  45.739037436828085],
        [4.89467820901416,   45.74349477437073],
        [4.89646416496484,   45.746809758539996],
        [4.896869278651252,  45.74891686986501],
        [4.8975505195815,    45.751589171037665],
        [4.8984527035141525, 45.752963814591624],
        [4.896685159480938,  45.75343915074612],
        [4.893941783846714,  45.75400441009205],
        [4.892339947067768,  45.75409433718764],
        [4.887625722940868,  45.75431055205931],
        [4.8851585260613035, 45.75424631868333],
        [4.883096391355906,  45.75438763201271],
        [4.878401352518125,  45.75499142129863],
        [4.877296637497693,  45.75499142129863],
        [4.875437033880047,  45.754901495648596],
        [4.874092963938381,  45.75461887123453],
        [4.8696556919393,    45.752807471686765],
    ]),
}

BAN_URL = "https://api-adresse.data.gouv.fr/search"
ENT_URL = "https://recherche-entreprises.api.gouv.fr/search"
PAUSE   = 0.15

# ─────────────────────────────────────────────────────────────────
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "DPE-Prospector/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def construire_adresse(row):
    num  = (str(row.get("numero_voirie") or "")).strip().lstrip("0")
    nat  = (row.get("nature_voie") or "").strip()
    voie = (row.get("nom_voie") or "").strip()
    # code_insee 69383 = Lyon 3e = code postal 69003
    insee = (row.get("code_insee") or "").strip()
    cp    = "69003" if insee == "69383" else insee
    return f"{num} {nat} {voie} {cp}".strip()

def geocoder_ban_batch(adresses):
    """
    Géocode une liste d'adresses en une seule requête POST CSV vers l'API BAN batch.
    Retourne trois listes parallèles : lons, lats, zones.
    """
    import io
    # Construire le CSV en mémoire
    buf = io.StringIO()
    buf.write("adresse\n")
    for a in adresses:
        buf.write(a.replace('"', '') + "\n")
    csv_bytes = buf.getvalue().encode("utf-8")

    # Requête multipart
    boundary = "----BAN_BATCH_BOUNDARY"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="data"; filename="adresses.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode() + csv_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BAN_URL}/csv/",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "DPE-Prospector/1.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        result_csv = r.read().decode("utf-8")

    # Parser la réponse CSV
    import csv as csvmod
    reader = csvmod.DictReader(io.StringIO(result_csv))
    lons, lats, zones_col = [], [], []
    for row in reader:
        try:
            lon = float(row.get("longitude") or row.get("result_longitude") or 0)
            lat = float(row.get("latitude") or row.get("result_latitude") or 0)
            score = float(row.get("result_score") or 0)
        except (ValueError, TypeError):
            lon = lat = 0.0
            score = 0.0
        if score > 0.4 and lon != 0:
            zone = dans_zone(lon, lat)
        else:
            lon = lat = None
            zone = None
        lons.append(lon)
        lats.append(lat)
        zones_col.append(zone)
    return lons, lats, zones_col

def dans_zone(lon, lat):
    if lon is None:
        return None
    pt = Point(lon, lat)
    for nom, poly in ZONES.items():
        if poly.contains(pt):
            return nom
    return None

def enrichir_siren(siren):
    if not siren or not str(siren).isdigit() or len(str(siren)) != 9:
        return "", [], True
    try:
        data = get_json(f"{ENT_URL}?q={siren}&page=1&per_page=1")
        results = data.get("results", [])
        if not results:
            return "", [], True
        info  = results[0]
        siege = (info.get("siege") or {}).get("adresse", "")
        actif = info.get("etat_administratif") == "A"
        dirs  = info.get("dirigeants", []) or []
        gerants = []
        for d in dirs:
            if d.get("type_dirigeant") == "personne physique":
                gerants.append({
                    "nom":    f"{d.get('prenoms','')} {d.get('nom','')}".strip(),
                    "qualite": d.get("qualite", "")
                })
        return siege, gerants, actif
    except Exception:
        return "", [], True

# ─────────────────────────────────────────────────────────────────
def main(fichier):
    print("=" * 60)
    print("  MAJIC 2025 — SCI Prospector Lyon 3e")
    print("=" * 60)

    # 1. Lecture parquet
    print("\n  1. Lecture fichier parquet...")
    df  = pq.ParquetFile(fichier).read().to_pandas()
    df3 = df[(df["code_insee"] == "69383") & (df["forme_juridique"] == "6540")].copy()
    millesime = int(df3["millesime"].iloc[0]) if len(df3) else 2025
    print(f"     {len(df3)} locaux SCI — Lyon 3e — millésime {millesime}")

    # 2. Dédupliquer par parcelle + siren (1 ligne par immeuble/SCI)
    df3["cle"] = df3["section"].astype(str) + df3["numero_parcelle"].astype(str) + df3["numero_siren"].astype(str)
    df_dedup   = df3.drop_duplicates(subset=["cle"]).copy()
    print(f"     {len(df_dedup)} parcelles uniques après déduplication")

    # 3. Géocodage BAN batch (toutes les adresses en une seule requête)
    print(f"\n  2. Géocodage BAN batch ({len(df_dedup)} adresses en une requête)...")
    adresses = df_dedup.apply(construire_adresse, axis=1).tolist()
    lons, lats, zones_col = geocoder_ban_batch(adresses)
    df_dedup["lon"]  = lons
    df_dedup["lat"]  = lats
    df_dedup["zone"] = zones_col
    print(f"     Géocodage terminé")

    df_zone = df_dedup[df_dedup["zone"].notna()].copy()
    print(f"\n     {len(df_zone)} SCI dans nos zones")
    for zone, nb in Counter(df_zone["zone"]).items():
        print(f"       {zone} : {nb}")

    # 4. Enrichissement dirigeants
    sirens = df_zone["numero_siren"].unique()
    print(f"\n  3. Enrichissement dirigeants ({len(sirens)} SIREN)...")
    cache = {}
    for i, siren in enumerate(sirens):
        cache[siren] = enrichir_siren(str(siren))
        time.sleep(PAUSE)
        if (i + 1) % 50 == 0:
            print(f"     {i+1}/{len(sirens)} enrichis...")

    # 5. Construire résultats
    resultats = []
    for _, row in df_zone.iterrows():
        siren  = str(row["numero_siren"])
        siege, gerants, actif = cache.get(siren, ("", [], True))
        resultats.append({
            "zone":         row["zone"],
            "parcelle":     f"{row['section']}{str(int(row['numero_parcelle'])).zfill(4)}",
            "adresse_bien": construire_adresse(row),
            "sci_nom":      row["denomination"],
            "sci_siren":    siren,
            "code_droit":   row["code_droit"],
            "millesime":    millesime,
            "sci_active":   "oui" if actif else "non",
            "siege_social": siege,
            "gerants":      gerants,
        })

    # Stats finales
    actives = sum(1 for r in resultats if r["sci_active"] == "oui")
    print(f"\n  Résultats finaux :")
    print(f"    Total SCI  : {len(resultats)}")
    print(f"    Actives    : {actives}")
    print(f"    Inactives  : {len(resultats) - actives}")

    # 6. Export JSON (pour DPE Prospector)
    import os
    os.makedirs("data", exist_ok=True)
    out_json = "data/dauphine-lacassagne-sci.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "millesime":    millesime,
            "derniere_maj": datetime.now().isoformat(),
            "sci":          resultats,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Export JSON → {out_json}")

    # 7. Export CSV lisible
    max_dir = max((len(r["gerants"]) for r in resultats), default=0)
    headers = ["zone", "adresse_bien", "sci_nom", "sci_siren",
               "sci_active", "siege_social"]
    for i in range(1, max_dir + 1):
        headers += [f"dirigeant_{i}", f"qualite_{i}"]

    out_csv = "sci_lyon3_2025.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in resultats:
            row = {
                "zone":         r["zone"],
                "adresse_bien": r["adresse_bien"],
                "sci_nom":      r["sci_nom"],
                "sci_siren":    r["sci_siren"],
                "sci_active":   r["sci_active"],
                "siege_social": r["siege_social"],
            }
            for i, g in enumerate(r["gerants"], 1):
                if i > max_dir:
                    break
                row[f"dirigeant_{i}"] = g["nom"]
                row[f"qualite_{i}"]   = g["qualite"]
            writer.writerow(row)
    print(f"  Export CSV  → {out_csv}")
    print("=" * 60)

# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fichier", required=True,
                        help="Chemin vers majic_locaux2_2025.parquet")
    args = parser.parse_args()
    main(args.fichier)
