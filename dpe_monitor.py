"""
DPE Prospector v6 — Script unifié multi-agences
Gère polygones GPS (Lyon/Paris) et codes postaux (Normandie)
Source : API Open Data ADEME
"""

import os
import json
import re
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION DES AGENCES
#  Injectée via le secret GitHub ZONES_JSON
#  (voir exemple dans zones_example.json)
# ══════════════════════════════════════════════════════════════

ZONES_JSON = os.getenv("ZONES_JSON", "[]")
try:
    AGENCES = json.loads(ZONES_JSON)
except json.JSONDecodeError as e:
    print(f"❌ ZONES_JSON invalide : {e}")
    AGENCES = []

# ── Email ─────────────────────────────────────────────────────
EMAIL_EXPEDITEUR   = os.getenv("EMAIL_EXPEDITEUR", "")
EMAIL_FROM         = "alerte_dpe@outlook.com"
EMAIL_MOT_DE_PASSE = os.getenv("EMAIL_MOT_DE_PASSE", "")

# ── API ADEME ─────────────────────────────────────────────────
API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets/meg-83tjwtg8dyz4vv7h1dqe/lines"

# ══════════════════════════════════════════════════════════════
#  GÉOGRAPHIE
# ══════════════════════════════════════════════════════════════

def point_dans_polygone(lat, lng, polygone) -> bool:
    """Ray casting algorithm."""
    n, dedans, j = len(polygone), False, len(polygone) - 1
    for i in range(n):
        lat_i, lng_i = polygone[i]
        lat_j, lng_j = polygone[j]
        if ((lng_i > lng) != (lng_j > lng)) and \
           (lat < (lat_j - lat_i) * (lng - lng_i) / (lng_j - lng_i) + lat_i):
            dedans = not dedans
        j = i
    return dedans


def affecter_zone(dpe: dict, zones_config: list) -> str:
    """
    Affecte un DPE à une zone.
    zones_config : liste de dicts avec 'nom', optionnel 'polygone' ou 'codes_postaux'
    """
    geopoint = dpe.get("_geopoint", "")
    code_postal = dpe.get("code_postal_ban", "")

    # Déterminer si l'agence utilise des polygones ou des codes postaux
    agence_utilise_polygones = any("polygone" in zone for zone in zones_config)

    for zone in zones_config:
        # Mode polygone GPS — si la zone a un polygone, on l'utilise exclusivement
        if "polygone" in zone:
            if not geopoint:
                # Pas de coordonnées GPS → on ne peut pas vérifier → on ignore ce DPE
                continue
            try:
                lat, lng = map(float, geopoint.split(","))
                if point_dans_polygone(lat, lng, zone["polygone"]):
                    return zone["nom"]
            except Exception:
                continue
        # Mode codes postaux — pour les agences sans polygones (ex: Bagot)
        elif not agence_utilise_polygones and "codes_postaux" in zone:
            if code_postal in zone["codes_postaux"]:
                return zone["nom"]  # Le nom de la zone = le code postal

    return "Autre"

# ══════════════════════════════════════════════════════════════
#  COLLECTE API ADEME
# ══════════════════════════════════════════════════════════════

def recuperer_dpe_bruts(codes_postaux: list, date_depuis: str) -> list:
    """Récupère tous les DPE pour une liste de codes postaux."""
    tous = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DPE-Monitor/2.0)"}

    for cp in codes_postaux:
        url = f"{API_BASE}?size=100&code_postal_ban_eq={cp}&date_reception_dpe_gte={date_depuis}"
        while url:
            try:
                r = requests.get(url, timeout=30, headers=headers)
                r.raise_for_status()
                data = r.json()
            except requests.RequestException as e:
                print(f"    ⚠️  Erreur API ({cp}) : {e}")
                break
            resultats = data.get("results", [])
            if not resultats:
                break
            tous.extend(resultats)
            url = data.get("next")
        print(f"   → {cp} : {len([d for d in tous if d.get('code_postal_ban') == cp])} DPE")

    return tous

# ══════════════════════════════════════════════════════════════
#  EXTRACTION ÉTAGE / DIGICODE
# ══════════════════════════════════════════════════════════════

def extraire_etage(dpe: dict) -> str:
    """
    Priorité de recherche de l'étage :
    1. compl_ref_logement   ex: "Etage : 2ème ;"
    2. label_brut_avec_complement  ex: "1 Rue X 69003 Lyon Etage : 2ème ;"
    3. complement_adresse_logement (champ historique)
    4. numero_etage_appartement (entier, 0=RDC) — utilisé SEULEMENT si > 0
       car 0 peut signifier "non renseigné" autant que RDC
    """

    def parser_texte_etage(texte: str) -> str:
        """Extrait l'étage depuis un texte libre."""
        if not texte:
            return None
        t = texte.upper()
        # RDC explicite
        if any(x in t for x in ["RDC", "REZ DE CHAUSSEE", "REZ-DE-CHAUSSEE", "REZ DE CHAUSSÉE", "REZ-DE-CHAUSSÉE"]) or "REZ" in t and "CHAUSS" in t:
            return "RDC"
        # Format "Etage : 2ème" ou "2ème étage" ou "2e étage" ou "2ème ;"
        patterns = [
            r"[Eé][Tt][Aa][Gg][Ee]\s*:\s*(\d+)",   # Etage : 2 / ETAGE : 2
            r"[Eé]tage\s+(\d+)",                    # Etage 2 / étage 2
            r"[Eé][Tt][Aa][Gg][Ee]\s*(\d+)",        # ETAGE2 / ETAGE 2
            r"(\d+)[^\d]{0,8}[eé]tage",             # 3ème étage / 2eme etage
            r";?\s*[Eé]t(?:age)?\s*(\d+)\b",        # ; Etage 2 / ; Et 2
        ]
        for p in patterns:
            m = re.search(p, texte, re.IGNORECASE)
            if m:
                n = int(m.group(1))
                return "RDC" if n == 0 else f"{n}e"
        return None

    # 1. compl_ref_logement (champ le plus fiable)
    ref_log = dpe.get("compl_ref_logement") or ""
    result = parser_texte_etage(ref_log)
    if result:
        return result

    # 2. label_brut_avec_complement
    label = dpe.get("label_brut_avec_complement") or ""
    result = parser_texte_etage(label)
    if result:
        return result

    # 3. complement_adresse_logement (champ historique)
    complement = dpe.get("complement_adresse_logement") or ""
    result = parser_texte_etage(complement)
    if result:
        return result

    # 4. compl_etage_appartement (peut être un entier ou texte)
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

    # 5. numero_etage_appartement — seulement si > 0 (0 = non fiable)
    etage_num = dpe.get("numero_etage_appartement")
    if etage_num is not None and etage_num != 0:
        return f"{etage_num}e"

    return "—"


def extraire_digicode(dpe: dict) -> str:
    complement = dpe.get("complement_adresse_logement") or ""
    if complement:
        m = re.search(r"[Dd]igicode\s*=?\s*:?\s*([^;\n]+)", complement)
        if m:
            return m.group(1).strip()
    return "—"

# ══════════════════════════════════════════════════════════════
#  MISE À JOUR data/*.json
# ══════════════════════════════════════════════════════════════

def mise_a_jour_data_json(agence_id: str, nouveaux_dpe: list, zones_config: list):
    data_file = Path(f"data/{agence_id}.json")
    data_file.parent.mkdir(exist_ok=True)

    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = {"dpe": []}

    num_existants = {d["numero_dpe"] for d in historique["dpe"]}
    ajoutes = 0

    for nom_zone, dpes in nouveaux_dpe.items():
        for dpe in dpes:
            if dpe.get("numero_dpe") not in num_existants:
                historique["dpe"].append({
                    "numero_dpe":                dpe.get("numero_dpe"),
                    "date_reception_dpe":         dpe.get("date_reception_dpe"),
                    "adresse_ban":                dpe.get("adresse_ban"),
                    "code_postal_ban":            dpe.get("code_postal_ban"),
                    "nom_commune_ban":            dpe.get("nom_commune_ban"),
                    "etiquette_dpe":              dpe.get("etiquette_dpe"),
                    "type_batiment":              dpe.get("type_batiment"),
                    "surface_habitable_logement": dpe.get("surface_habitable_logement"),
                    "surface_habitable_immeuble": dpe.get("surface_habitable_immeuble"),
                    "numero_dpe_remplace":        dpe.get("numero_dpe_remplace"),
                    "zone":                       nom_zone,
                    "etage_str":                  extraire_etage(dpe),
                    "digicode_str":               extraire_digicode(dpe),
                    "geopoint":                   dpe.get("_geopoint"),
                })
                ajoutes += 1

    historique["dpe"].sort(key=lambda d: d.get("date_reception_dpe") or "", reverse=True)
    historique["derniere_maj"] = datetime.now().isoformat()

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    print(f"   📊 {data_file} : +{ajoutes} nouveaux ({len(historique['dpe'])} total)")
    return ajoutes

# ══════════════════════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════════════════════

def formater_date(date_iso: str) -> str:
    try:
        return datetime.strptime(date_iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return date_iso


def generer_email(agence_cfg: dict, resultats_par_zone: dict) -> tuple:
    nom_agence = agence_cfg.get("nom", "Agence")
    total      = sum(len(v) for v in resultats_par_zone.values())
    date_str   = datetime.now().strftime("%d/%m/%Y à %H:%M")

    if total == 0:
        sujet = f"📋 Aucun nouveau DPE · {nom_agence}"
        html  = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:32px auto;border-radius:12px;overflow:hidden;box-shadow:0 4px 32px rgba(0,0,0,0.10);">
    <div style="background:linear-gradient(135deg,#374151,#6b7280);padding:24px;color:#fff;">
      <div style="font-size:11px;opacity:0.55;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">DPE Prospector · Rapport quotidien</div>
      <div style="font-size:24px;font-weight:700;">📋 Aucun nouveau DPE</div>
      <div style="font-size:14px;opacity:0.75;margin-top:6px;">{nom_agence}</div>
      <div style="font-size:11px;opacity:0.4;margin-top:14px;">Généré le {date_str}</div>
    </div>
    <div style="background:#fff;padding:32px;">
      <p style="color:#374151;line-height:1.6;">Aucun nouveau DPE n'a été déposé depuis le dernier rapport.</p>
      <p style="color:#6b7280;font-size:14px;margin-top:12px;">Le prochain rapport sera envoyé demain matin.</p>
    </div>
  </div>
</body></html>"""
        return sujet, html

    # Email avec DPE
    sujet = f"🏠 {total} nouveau{'x' if total > 1 else ''} DPE · {nom_agence}"

    couleurs_dpe = {"A":"#009F6B","B":"#51B748","C":"#CADD43","D":"#F5E800","E":"#F0A800","F":"#E4581B","G":"#D7221F"}
    texte_dpe   = {"C":"#111","D":"#111"}

    lignes = ""
    for nom_zone, dpes in resultats_par_zone.items():
        dpes_tries = sorted(dpes, key=lambda d: d.get("date_reception_dpe",""))
        for dpe in dpes_tries:
            etiq    = (dpe.get("etiquette_dpe") or "?").upper()
            couleur = couleurs_dpe.get(etiq,"#555")
            txt_c   = texte_dpe.get(etiq,"#fff")
            adresse = dpe.get("adresse_ban","—")
            surface = dpe.get("surface_habitable_logement") or dpe.get("surface_habitable_immeuble")
            etage   = extraire_etage(dpe)
            digi    = extraire_digicode(dpe)
            renouv  = "🔄 Renouvellement" if dpe.get("numero_dpe_remplace") else "🆕 Premier"
            maps_url= f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(adresse)}"
            ademe_url= f"https://observatoire-dpe-audit.ademe.fr/afficher-dpe/{dpe.get('numero_dpe','')}"
            bg_row  = "#fff5f5" if etiq == "G" else "#ffffff"
            lignes += f"""
<tr style="background:{bg_row};border-bottom:1px solid #e5e7eb;">
  <td style="padding:10px 12px;font-size:12px;color:#6b7280;white-space:nowrap;">{formater_date(dpe.get('date_reception_dpe',''))}</td>
  <td style="padding:10px 12px;">
    <a href="{maps_url}" style="color:#1d4ed8;text-decoration:none;font-weight:600;font-size:13px;">{adresse}</a>
  </td>
  <td style="padding:10px 12px;font-size:12px;color:#6b7280;">{nom_zone}</td>
  <td style="padding:10px 12px;text-align:center;">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:5px;background:{couleur};color:{txt_c};font-weight:900;font-size:14px;">{etiq}</span>
  </td>
  <td style="padding:10px 12px;font-size:12px;color:#6b7280;">{f'{round(surface)} m²' if surface else '—'}</td>
  <td style="padding:10px 12px;font-size:12px;color:#6b7280;">{etage}</td>
  <td style="padding:10px 12px;font-size:12px;font-family:monospace;color:#d97706;">{digi}</td>
  <td style="padding:10px 12px;font-size:12px;color:#6b7280;">{renouv}</td>
  <td style="padding:10px 12px;">
    <a href="{ademe_url}" style="background:#1d4ed8;color:#fff;text-decoration:none;border-radius:5px;padding:4px 10px;font-size:11px;font-weight:600;">Voir →</a>
  </td>
</tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:800px;margin:32px auto;border-radius:12px;overflow:hidden;box-shadow:0 4px 32px rgba(0,0,0,0.10);">
    <div style="background:linear-gradient(135deg,#0a1628,#1a3a5c);padding:28px;color:#fff;">
      <div style="font-size:11px;opacity:0.55;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">DPE Prospector · Rapport quotidien</div>
      <div style="font-size:26px;font-weight:700;margin-bottom:6px;">🏠 {total} nouveau{'x' if total > 1 else ''} DPE</div>
      <div style="font-size:14px;opacity:0.75;">{nom_agence}</div>
      <div style="font-size:11px;opacity:0.4;margin-top:14px;">Généré le {date_str}</div>
    </div>
    <div style="background:#fff;overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f8fafc;">
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Date</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Adresse</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Zone</th>
            <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">DPE</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Surface</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Étage</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Digicode</th>
            <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Type</th>
            <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Attestation</th>
          </tr>
        </thead>
        <tbody>{lignes}</tbody>
      </table>
    </div>
    <div style="background:#f8fafc;padding:12px 20px;border-top:1px solid #e5e7eb;text-align:center;">
      <p style="margin:0;font-size:11px;color:#9ca3af;">Données <a href="https://data.ademe.fr" style="color:#6b7280;">ADEME Open Data</a> · Licence Etalab</p>
    </div>
  </div>
</body></html>"""

    return sujet, html


def envoyer_email(destinataire: str, cc: str, sujet: str, html: str):
    with smtplib.SMTP("smtp-relay.brevo.com", 587) as s:
        s.ehlo(); s.starttls()
        s.login(EMAIL_EXPEDITEUR, EMAIL_MOT_DE_PASSE)
        destinataires = [d for d in [destinataire, cc] if d]
        for dest in destinataires:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = sujet
            msg["From"]    = EMAIL_FROM
            msg["To"]      = dest
            msg.attach(MIMEText(html, "html"))
            s.sendmail(EMAIL_EXPEDITEUR, dest, msg.as_string())
            print(f"   ✉️  Envoyé à {dest}")

# ══════════════════════════════════════════════════════════════
#  CACHE GLOBAL ANTI-DOUBLONS
# ══════════════════════════════════════════════════════════════

CACHE_FILE = "dpe_cache.json"

def charger_cache() -> dict:
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"dpe_vus": {}}

def sauvegarder_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 64)
    print(f"🔍 DPE Prospector v6 · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"   {len(AGENCES)} agence(s) à surveiller")
    print("=" * 64)

    if not AGENCES:
        print("❌ Aucune agence configurée dans ZONES_JSON")
        return

    cache    = charger_cache()
    dpe_vus  = cache.get("dpe_vus", {})
    date_depuis = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    for agence in AGENCES:
        agence_id  = agence["id"]
        nom_agence = agence["nom"]
        zones      = agence.get("zones", [])
        destinataire = agence.get("email_destinataire", "")
        cc           = agence.get("email_cc", "")

        print(f"\n{'─'*64}")
        print(f"📍 {nom_agence} ({agence_id})")

        # Collecter tous les codes postaux de l'agence
        codes_postaux = set()
        for zone in zones:
            for cp in zone.get("codes_postaux", []):
                codes_postaux.add(cp)
        codes_postaux = list(codes_postaux)

        print(f"   Codes postaux : {', '.join(codes_postaux)}")
        print(f"   Zones : {', '.join(z['nom'] for z in zones)}")

        # Récupération API
        tous_dpe = recuperer_dpe_bruts(codes_postaux, date_depuis)
        print(f"   → {len(tous_dpe)} DPE bruts récupérés")

        # Filtrage par zone + anti-doublons
        resultats_par_zone = {z["nom"]: [] for z in zones}

        for dpe in tous_dpe:
            num = dpe.get("numero_dpe")
            if not num or num in dpe_vus:
                continue
            zone_nom = affecter_zone(dpe, zones)
            if zone_nom in resultats_par_zone:
                resultats_par_zone[zone_nom].append(dpe)

        # Supprimer zones vides
        resultats_par_zone = {k: v for k, v in resultats_par_zone.items() if v}

        total_nouveaux = sum(len(v) for v in resultats_par_zone.values())
        print(f"   → {total_nouveaux} nouveau(x) DPE (hors doublons)")

        # Marquer comme vus
        for dpes in resultats_par_zone.values():
            for dpe in dpes:
                if dpe.get("numero_dpe"):
                    dpe_vus[dpe["numero_dpe"]] = datetime.now().isoformat()

        # Mise à jour data/agence.json
        mise_a_jour_data_json(agence_id, resultats_par_zone, zones)

        # Email
        sujet, html = generer_email(agence, resultats_par_zone)
        if destinataire:
            envoyer_email(destinataire, cc, sujet, html)
        else:
            print(f"   ⚠️  Pas d'email configuré pour {agence_id}")

    cache["dpe_vus"]              = dpe_vus
    cache["derniere_verification"] = datetime.now().isoformat()
    sauvegarder_cache(cache)

    print(f"\n{'='*64}")
    print("✅ Toutes les agences traitées")
    print("=" * 64)


if __name__ == "__main__":
    main()
