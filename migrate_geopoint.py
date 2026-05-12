"""
Migration geopoint — DPE Prospector
Ajoute le champ geopoint (_geopoint) aux DPE existants dans data/*.json
en rappelant l'API ADEME. Même logique de retry que migrate_etages.py.
"""

import json
import time
import requests
from pathlib import Path

API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets/meg-83tjwtg8dyz4vv7h1dqe/lines"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; DPE-Monitor/2.0)"}

def fetch_dpe_details(numero_dpe: str) -> dict:
    url = f"{API_BASE}?numero_dpe_eq={numero_dpe}&size=1"
    for tentative in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                attente = 30 * (tentative + 1)
                print(f"      ⏳ Rate limit, attente {attente}s...")
                time.sleep(attente)
                continue
            r.raise_for_status()
            results = r.json().get("results", [])
            return results[0] if results else {}
        except Exception as e:
            if tentative < 3:
                time.sleep(10)
                continue
            print(f"      ⚠️  Erreur API ({numero_dpe}): {e}")
            return {}
    return {}

def migrer_fichier(data_file: Path):
    print(f"\n{'─'*60}")
    print(f"📄 {data_file.name}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    dpes     = data.get("dpe", [])
    modifies = 0
    ignores  = 0
    erreurs  = 0

    for i, dpe in enumerate(dpes):
        numero = dpe.get("numero_dpe", "")

        # Déjà renseigné
        if dpe.get("geopoint") is not None:
            ignores += 1
            continue

        details = fetch_dpe_details(numero)
        if not details:
            erreurs += 1
            time.sleep(1.0)
            continue

        geopoint = details.get("_geopoint")
        dpe["geopoint"] = geopoint
        if geopoint:
            modifies += 1
            print(f"   📍 {numero} : {geopoint}")

        time.sleep(1.0)

        if (i + 1) % 20 == 0:
            print(f"   ... {i+1}/{len(dpes)} traités ({modifies} avec coords)")

    data["dpe"] = dpes
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ {modifies} coords ajoutées / {ignores} déjà renseignés / {erreurs} erreurs")
    return modifies

def main():
    print("=" * 60)
    print("📍 Migration geopoint — DPE Prospector")
    print("=" * 60)

    data_dir = Path("data")
    fichiers = sorted(data_dir.glob("*.json"))
    print(f"   {len(fichiers)} fichier(s) à traiter")

    total = 0
    for fichier in fichiers:
        total += migrer_fichier(fichier)

    print(f"\n{'='*60}")
    print(f"✅ Migration terminée — {total} coordonnées ajoutées")
    print("=" * 60)

if __name__ == "__main__":
    main()
