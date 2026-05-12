"""
Migration des étages — DPE Prospector
Relit tous les DPE existants dans data/*.json,
rappelle l'API ADEME pour récupérer les champs d'étage complets,
et met à jour etage_str sans créer de doublons ni supprimer de données.

Usage : python migrate_etages.py
"""

import json
import re
import time
import requests
from pathlib import Path

API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets/meg-83tjwtg8dyz4vv7h1dqe/lines"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; DPE-Monitor/2.0)"}

# ══════════════════════════════════════════════════════════════
#  FONCTION EXTRAIRE_ETAGE (identique à dpe_monitor.py)
# ══════════════════════════════════════════════════════════════

def parser_texte_etage(texte: str):
    if not texte:
        return None
    t = texte.upper()
    if any(x in t for x in ["RDC", "REZ DE CHAUSSEE", "REZ-DE-CHAUSSEE", "REZ DE CHAUSSÉE"]):
        return "RDC"
    patterns = [
        r"[Ee]tage\s*:\s*(\d+)[eè]?",
        r"(\d+)\s*[eè][rm]?[eè]?\s*[Ee]tage",
        r"[Ee][Tt][Aa][Gg][Ee]\s*:\s*(\d+)",
        r"(\d+)\s*[Ee][Mm]?[Ee]?\s*[Ee][Tt][Aa][Gg][Ee]",
    ]
    for p in patterns:
        m = re.search(p, texte, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            return "RDC" if n == 0 else f"{n}e"
    return None

def extraire_etage(dpe: dict) -> str:
    # 1. compl_ref_logement
    result = parser_texte_etage(dpe.get("compl_ref_logement") or "")
    if result:
        return result
    # 2. label_brut_avec_complement
    result = parser_texte_etage(dpe.get("label_brut_avec_complement") or "")
    if result:
        return result
    # 3. complement_adresse_logement
    result = parser_texte_etage(dpe.get("complement_adresse_logement") or "")
    if result:
        return result
    # 4. compl_etage_appartement
    compl_etage = dpe.get("compl_etage_appartement")
    if compl_etage is not None:
        try:
            n = int(compl_etage)
            if n > 0:
                return f"{n}e"
        except (ValueError, TypeError):
            result = parser_texte_etage(str(compl_etage))
            if result:
                return result
    # 5. numero_etage_appartement — seulement si > 0
    etage_num = dpe.get("numero_etage_appartement")
    if etage_num is not None and etage_num != 0:
        return f"{etage_num}e"
    return "—"

# ══════════════════════════════════════════════════════════════
#  RÉCUPÉRATION API ADEME PAR NUMÉRO DPE
# ══════════════════════════════════════════════════════════════

def fetch_dpe_details(numero_dpe: str) -> dict:
    """Récupère les détails d'un DPE depuis l'API ADEME."""
    url = f"{API_BASE}?numero_dpe_eq={numero_dpe}&size=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else {}
    except Exception as e:
        print(f"      ⚠️  Erreur API ({numero_dpe}): {e}")
        return {}

# ══════════════════════════════════════════════════════════════
#  MIGRATION
# ══════════════════════════════════════════════════════════════

def migrer_fichier(data_file: Path):
    print(f"\n{'─'*60}")
    print(f"📄 {data_file.name}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    dpes       = data.get("dpe", [])
    modifies   = 0
    inchanges  = 0
    erreurs    = 0

    for i, dpe in enumerate(dpes):
        numero    = dpe.get("numero_dpe", "")
        ancien    = dpe.get("etage_str", "—")
        type_bat  = dpe.get("type_batiment", "")

        # Inutile de chercher l'étage pour les immeubles collectifs
        if type_bat == "immeuble":
            inchanges += 1
            continue

        # Sauter les DPE qui ont déjà un étage renseigné (pas "—" et pas "RDC" douteux)
        # On ne retraite que ceux avec "—" (information manquante) ou "RDC" (potentiellement faux)
        if ancien not in ["—", "RDC"]:
            inchanges += 1
            continue

        # Récupérer les détails depuis l'API
        details = fetch_dpe_details(numero)
        if not details:
            erreurs += 1
            continue

        # Calculer le nouvel étage
        nouvel = extraire_etage(details)

        if nouvel != ancien:
            dpe["etage_str"] = nouvel
            modifies += 1
            print(f"   ✏️  {numero} : '{ancien}' → '{nouvel}'")
        else:
            inchanges += 1

        # Pause pour ne pas surcharger l'API
        time.sleep(0.15)

        # Affichage progression tous les 20
        if (i + 1) % 20 == 0:
            print(f"   ... {i+1}/{len(dpes)} traités ({modifies} modifiés)")

    # Sauvegarder
    data["dpe"] = dpes
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ {modifies} modifiés / {inchanges} inchangés / {erreurs} erreurs")
    return modifies

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🔧 Migration étages — DPE Prospector")
    print("=" * 60)

    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ Dossier data/ introuvable")
        return

    fichiers = sorted(data_dir.glob("*.json"))
    if not fichiers:
        print("❌ Aucun fichier JSON dans data/")
        return

    print(f"   {len(fichiers)} fichier(s) à traiter")
    total_modifies = 0

    for fichier in fichiers:
        total_modifies += migrer_fichier(fichier)

    print(f"\n{'='*60}")
    print(f"✅ Migration terminée — {total_modifies} étages mis à jour")
    print("=" * 60)

if __name__ == "__main__":
    main()
