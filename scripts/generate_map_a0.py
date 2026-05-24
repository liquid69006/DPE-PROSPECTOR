"""generate_map_a0.py -- Carte A0 print-ready (300 DPI portrait).

Lit REPARTITION_JSON et AGENCE_ID en env (passes par le workflow GitHub
Actions). Parse les 3 KML de data/kml/, applique KML_REMAP, genere une
carte folium (Positron) avec polygones colories selon la repartition,
puis capture en PNG via selenium / chromium headless a 9933x14043
(A0 300 DPI portrait).

Sortie : output/carte_a0.png (artifact uploade par le workflow).

Notes :
  - Si le dimensionnement 9933x14043 OOM en CI, baisser a 4961x7016
    (A0 150 DPI). 16 GB de RAM theorique sur runner ubuntu-latest.
  - L'ilot 82 (27 av. Lacassagne) n'a pas de polygone KML : ignore.
  - Les Placemark 'X' sont ignores (hors secteur).
"""
import base64
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import folium

# ---------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent.parent
KML_DIR = ROOT / "data" / "kml"
OUT_DIR = ROOT / "output"
KML_FILES = [
    "Secteur_DL_-_new.kml",
    "Secteur_DL_-_raye.kml",
    "Secteur_DL_-_non_raye.kml",
]
KML_REMAP = {"3A": "3", "3B": "13"}
KML_NS = "{http://www.opengis.net/kml/2.2}"

# Coordonnees agence (extensible). Aligne sur sctMap UI.
AGENCE_COORDS = {
    "dauphine-lacassagne": (45.75685, 4.86502),
}

# A0 portrait @ 300 DPI : 841 mm x 1189 mm.
A0_W, A0_H = 9933, 14043

# Couleurs par defaut (sec-1..8), aligne sur SCT_GEN_COLORS de index.html.
DEFAULT_COLORS = [
    "#e74c3c", "#3498db", "#f1c40f", "#2ecc71",
    "#95a5a6", "#e91e8c", "#9b59b6", "#e67e22",
]


# ---------------------------------------------------------------------
# Parseur KML
# ---------------------------------------------------------------------
def parse_kml(path):
    """Retourne {ilot_id: [ring1, ring2, ...]} ; chaque ring = liste de (lat,lng)."""
    out = {}
    try:
        tree = ET.parse(str(path))
    except (ET.ParseError, FileNotFoundError) as exc:
        print(f"[WARN] KML inutilisable {path.name}: {exc}", flush=True)
        return out
    root = tree.getroot()

    placemarks = root.findall(f".//{KML_NS}Placemark") or root.findall(".//Placemark")
    for pm in placemarks:
        nm = pm.find(f"{KML_NS}name")
        if nm is None:
            nm = pm.find("name")
        if nm is None or not nm.text:
            continue
        raw = nm.text.strip()
        if raw == "X":
            continue                                     # hors secteur
        ilot_id = KML_REMAP.get(raw, raw)

        coords_els = pm.findall(f".//{KML_NS}coordinates")
        if not coords_els:
            coords_els = pm.findall(".//coordinates")
        for ce in coords_els:
            if not ce.text:
                continue
            ring = []
            for triplet in ce.text.split():
                parts = triplet.split(",")
                if len(parts) < 2:
                    continue
                try:
                    lng = float(parts[0])
                    lat = float(parts[1])
                except ValueError:
                    continue
                ring.append((lat, lng))
            if len(ring) >= 3:
                out.setdefault(ilot_id, []).append(ring)
    return out


# ---------------------------------------------------------------------
# Capture headless (Chromium via Selenium)
# ---------------------------------------------------------------------
def capture_html_to_png(html_path, png_path, w, h):
    """Capture une page HTML locale en PNG via Google Chrome headless.

    Strategie CI (ubuntu-latest 24.04) :
      - google-chrome (paquet .deb officiel) au lieu de chromium-browser
        snap qui casse en headless ("DevToolsActivePort file doesn't
        exist").
      - chromedriver depuis chromium-driver apt (compatible CDP).
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument(f"--window-size={w},{h}")
    # Binaire Chrome : prefere google-chrome (CI), fallback chrome local.
    if pathlib.Path("/usr/bin/google-chrome").exists():
        opts.binary_location = "/usr/bin/google-chrome"
    elif pathlib.Path("/usr/bin/google-chrome-stable").exists():
        opts.binary_location = "/usr/bin/google-chrome-stable"

    # ChromeDriver : cherche dans PATH (chromium-driver apt), fallback
    # /usr/bin/chromedriver. Si introuvable, tente apt-get install.
    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        try:
            chrome_ver = subprocess.check_output(
                ["google-chrome", "--version"], stderr=subprocess.STDOUT
            ).decode().strip()
            print(f"[INFO] {chrome_ver}", flush=True)
        except Exception:
            pass
        try:
            subprocess.check_call(
                ["sudo", "apt-get", "install", "-y", "chromium-driver"],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            )
        except Exception as exc:
            print(f"[WARN] apt-get chromium-driver KO : {exc}", flush=True)
        chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
    print(f"[OK] chromedriver : {chromedriver_path}", flush=True)

    service = ChromeService(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        url = pathlib.Path(html_path).resolve().as_uri()
        driver.get(url)
        # Laisser le temps aux tuiles CartoDB de charger (rendu vectoriel
        # SVG des polygones est instantane, le bottleneck = tuiles).
        time.sleep(10)
        # Force la taille du viewport apres rendu.
        driver.set_window_size(w, h)
        time.sleep(2)
        # CDP screenshot : permet de capturer au-dela du viewport visible.
        try:
            result = driver.execute_cdp_cmd("Page.captureScreenshot", {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": 1},
            })
            data = base64.b64decode(result["data"])
            with open(png_path, "wb") as f:
                f.write(data)
        except Exception as exc:
            print(f"[WARN] CDP screenshot echec ({exc}), fallback save_screenshot", flush=True)
            driver.save_screenshot(png_path)
    finally:
        driver.quit()

    from PIL import Image
    img = Image.open(png_path)
    print(f"[OK] PNG sauve : {png_path} ({img.size[0]}x{img.size[1]})", flush=True)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    rep_json = os.environ.get("REPARTITION_JSON", "").strip()
    agence_id = os.environ.get("AGENCE_ID", "").strip()
    if not rep_json:
        print("[FATAL] REPARTITION_JSON manquant en env", file=sys.stderr)
        sys.exit(2)
    if not agence_id:
        print("[FATAL] AGENCE_ID manquant en env", file=sys.stderr)
        sys.exit(2)
    try:
        payload = json.loads(rep_json)
    except json.JSONDecodeError as exc:
        print(f"[FATAL] REPARTITION_JSON invalide : {exc}", file=sys.stderr)
        sys.exit(2)
    repartition = payload.get("repartition") or {}
    conseillers = payload.get("conseillers") or []

    # Index conseillers par id (nom + couleur).
    conseiller_by_id = {}
    for i, c in enumerate(conseillers):
        cid = c.get("id") or f"sec-{i + 1}"
        couleur = c.get("couleur") or DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        nom = c.get("nom") or cid
        conseiller_by_id[cid] = {"nom": nom, "couleur": couleur}

    # Parse les 3 KML.
    ilot_rings = {}
    for fn in KML_FILES:
        path = KML_DIR / fn
        if not path.exists():
            print(f"[WARN] KML manquant : {path}", file=sys.stderr)
            continue
        d = parse_kml(path)
        for k, rings in d.items():
            ilot_rings.setdefault(k, []).extend(rings)
    print(f"[OK] {len(ilot_rings)} ilots avec polygones KML", flush=True)

    if not ilot_rings:
        print("[FATAL] Aucun polygone KML utilisable", file=sys.stderr)
        sys.exit(3)

    # Calcul bbox.
    all_lats, all_lngs = [], []
    for rings in ilot_rings.values():
        for ring in rings:
            for (lat, lng) in ring:
                all_lats.append(lat)
                all_lngs.append(lng)
    center = (sum(all_lats) / len(all_lats), sum(all_lngs) / len(all_lngs))
    bounds = [[min(all_lats), min(all_lngs)], [max(all_lats), max(all_lngs)]]

    # Carte folium (Positron, aligne avec sctMap UI).
    m = folium.Map(
        location=center,
        zoom_start=14,
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="&copy; OpenStreetMap contributors &copy; CARTO",
        max_zoom=19,
    )

    # Polygones colories.
    for ilot_id, rings in ilot_rings.items():
        rep = repartition.get(str(ilot_id))
        if rep and rep.get("conseillerId"):
            c = conseiller_by_id.get(rep["conseillerId"])
            color = c["couleur"] if c else "#888888"
            nom = c["nom"] if c else "non affecté"
            affected = True
        else:
            color = "#888888"
            nom = "non affecté"
            affected = False
        tooltip = f"Îlot {ilot_id} — {nom}"
        for ring in rings:
            folium.Polygon(
                locations=ring,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.65 if affected else 0.20,
                tooltip=tooltip,
            ).add_to(m)

    # Marker agence (si coordonnees connues).
    coords = AGENCE_COORDS.get(agence_id)
    if coords:
        folium.Marker(coords, popup="📍 Agence").add_to(m)
        print(f"[OK] Marker agence ajoute : {agence_id} -> {coords}", flush=True)
    else:
        print(f"[INFO] Pas de coords pour agence {agence_id} (extensible via AGENCE_COORDS)", flush=True)

    # Fit bounds avec padding.
    m.fit_bounds(bounds, padding=(20, 20))

    # Sortie : HTML puis PNG.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUT_DIR / "carte_a0.html"
    png_path = OUT_DIR / "carte_a0.png"
    m.save(str(html_path))
    print(f"[OK] HTML sauve : {html_path}", flush=True)

    capture_html_to_png(str(html_path), str(png_path), A0_W, A0_H)


if __name__ == "__main__":
    main()
