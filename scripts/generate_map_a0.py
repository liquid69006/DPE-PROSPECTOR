"""generate_map_a0.py -- Carte A0 print-ready (matplotlib).

Lit REPARTITION_JSON et AGENCE_ID en env (passes par le workflow GitHub
Actions). Parse les 3 KML de data/kml/, applique KML_REMAP, genere
directement un PNG A0 portrait (33.1 x 46.8 in @ 150 DPI) via
matplotlib, sans HTML/Leaflet/Selenium intermediaires.

Sortie : output/carte_a0.png (artifact uploade par le workflow).

Notes :
  - Pas de fond de carte tuile : carte de prospection a polygones
    colories + numero d'ilot au centroide. Fond blanc.
  - L'ilot 82 (27 av. Lacassagne) n'a pas de polygone KML : ignore.
  - Les Placemark 'X' sont ignores (hors secteur).
  - Aspect 'equal' : lng/lat traites comme un plan cartesien. A 45 deg
    de latitude, distortion est-ouest de ~30 % (acceptable pour une
    carte de quartier ; passer en projection si zone plus etendue).
"""
import os, json, xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from pathlib import Path

KML_REMAP = {'3A': '3', '3B': '13'}

COULEURS = {
  'sec-1': '#e74c3c', 'sec-2': '#3498db',
  'sec-3': '#f1c40f', 'sec-4': '#2ecc71',
  'sec-5': '#95a5a6', 'sec-6': '#e91e8c',
  'sec-7': '#9b59b6', 'sec-8': '#e67e22',
}

A0_W_IN = 33.1  # A0 portrait en pouces
A0_H_IN = 46.8
DPI = 150       # 150 DPI -> qualite suffisante pour impression murale

def parse_kml(path):
    """Retourne dict {ilot_id: [(lng, lat), ...]}"""
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    tree = ET.parse(path)
    result = {}
    for pm in tree.findall('.//kml:Placemark', ns):
        name_el = pm.find('kml:name', ns)
        if name_el is None:
            continue
        name = KML_REMAP.get(name_el.text.strip(),
                              name_el.text.strip())
        coords_el = pm.find('.//kml:coordinates', ns)
        if coords_el is None:
            continue
        coords = []
        for c in coords_el.text.strip().split():
            parts = c.split(',')
            if len(parts) >= 2:
                coords.append((float(parts[0]),
                               float(parts[1])))
        if coords:
            result[name] = coords
    return result

def main():
    rep_raw = os.environ['REPARTITION_JSON']
    agence_id = os.environ.get('AGENCE_ID', '')
    data = json.loads(rep_raw)
    repartition = data['repartition']
    conseillers = {c['id']: c for c in data['conseillers']}

    # Charger les 3 KML
    kml_dir = Path('data/kml')
    polygones = {}
    for kml_file in kml_dir.glob('*.kml'):
        polygones.update(parse_kml(kml_file))
    print(f"[OK] {len(polygones)} polygones KML charges")

    # Creer la figure A0
    fig, ax = plt.subplots(1, 1,
      figsize=(A0_W_IN, A0_H_IN), dpi=DPI)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    ax.set_aspect('equal')
    ax.axis('off')

    # Calculer bounds globaux
    all_lngs, all_lats = [], []

    # Dessiner les polygones
    for ilot_id, coords in polygones.items():
        if not coords:
            continue
        rep = repartition.get(ilot_id, {})
        sec_id = rep.get('conseillerId') if rep else None
        c = conseillers.get(sec_id, {})
        couleur = c.get('couleur', '#cccccc') if c else '#cccccc'
        nom = c.get('nom', 'Non affecte') if c else 'Non affecte'

        lngs = [p[0] for p in coords]
        lats = [p[1] for p in coords]
        all_lngs.extend(lngs)
        all_lats.extend(lats)

        poly = MplPolygon(list(zip(lngs, lats)),
                          closed=True)
        patch = PatchCollection([poly],
          facecolor=couleur, edgecolor='white',
          linewidth=1.5, alpha=0.75)
        ax.add_collection(patch)

        # Numero d'ilot au centroide
        cx = sum(lngs) / len(lngs)
        cy = sum(lats) / len(lats)
        ax.text(cx, cy, ilot_id,
          ha='center', va='center',
          fontsize=6, fontweight='bold',
          color='#222222',
          bbox=dict(boxstyle='round,pad=0.1',
                    facecolor='white',
                    edgecolor='none', alpha=0.6))

    # Fit bounds avec marge 5 %
    lng_margin = lat_margin = 0
    if all_lngs and all_lats:
        lng_margin = (max(all_lngs) - min(all_lngs)) * 0.05
        lat_margin = (max(all_lats) - min(all_lats)) * 0.05
        ax.set_xlim(min(all_lngs) - lng_margin,
                    max(all_lngs) + lng_margin)
        ax.set_ylim(min(all_lats) - lat_margin,
                    max(all_lats) + lat_margin)

    # Marker agence
    AGENCE_COORDS = {
      'dauphine-lacassagne': (4.86502, 45.75685),
      'motte-picquet': (2.30, 48.85),
    }
    if agence_id in AGENCE_COORDS:
        lng_a, lat_a = AGENCE_COORDS[agence_id]
        ax.plot(lng_a, lat_a, 'k*', markersize=15,
                zorder=10)
        ax.text(lng_a, lat_a + lat_margin * 0.3,
                'Agence', ha='center',
                fontsize=8, fontweight='bold')

    # Legende
    handles = []
    for c in data['conseillers']:
        handles.append(mpatches.Patch(
          color=c['couleur'], label=c['nom']))
    ax.legend(handles=handles, loc='lower right',
              fontsize=8, framealpha=0.9,
              title='Secteurs', title_fontsize=9)

    # Titre
    ax.set_title(f'Carte des secteurs - {agence_id}',
                 fontsize=14, fontweight='bold', pad=20)

    # Export PNG
    out = Path('output')
    out.mkdir(exist_ok=True)
    png_path = out / 'carte_a0.png'
    fig.savefig(str(png_path), dpi=DPI,
                bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    print(f"[OK] PNG sauve : {png_path}")

if __name__ == '__main__':
    main()
