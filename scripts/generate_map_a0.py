"""generate_map_a0.py -- Carte A0 print-ready (matplotlib + contextily).

Lit REPARTITION_JSON et AGENCE_ID en env (passes par le workflow GitHub
Actions). Parse les 3 KML de data/kml/, applique KML_REMAP, genere
directement un PNG A0 portrait (33.1 x 46.8 in @ 150 DPI) via
matplotlib + fond OSM (CartoDB Positron) via contextily, sans HTML
ni Selenium.

Sortie : output/carte_a0.png (artifact uploade par le workflow).

Notes :
  - Aspect ratio corrige : set_aspect(1/cos(lat_center)) pour eviter
    la distortion est-ouest en lat/lng a 45 deg.
  - Fond CartoDB Positron via contextily (crs='EPSG:4326', reproj
    automatique des tuiles Mercator vers le plan lat/lng).
  - L'ilot 82 (27 av. Lacassagne) n'a pas de polygone KML : ignore.
  - Les Placemark 'X' sont ignores (hors secteur).
"""
import math
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

import contextily as ctx

KML_REMAP = {'3A': '3', '3B': '13'}

COULEURS = {
  'sec-1': '#e74c3c', 'sec-2': '#3498db',
  'sec-3': '#f1c40f', 'sec-4': '#2ecc71',
  'sec-5': '#95a5a6', 'sec-6': '#e91e8c',
  'sec-7': '#9b59b6', 'sec-8': '#e67e22',
}

A0_W_IN = 33.1  # A0 portrait en pouces
A0_H_IN = 46.8
DPI = 200       # 200 DPI -> 6614 x 9354 px, bon compromis taille/qualite imprimeur


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

    # Passe 1 : collecter tous les points pour calculer bounds globaux
    # AVANT de creer la figure (on a besoin de lat_center pour aspect).
    all_lngs, all_lats = [], []
    for coords in polygones.values():
        for lng, lat in coords:
            all_lngs.append(lng)
            all_lats.append(lat)
    if not all_lngs:
        raise SystemExit('[FATAL] Aucun polygone KML utilisable')

    # Bounds + marge 5 %
    lng_margin = (max(all_lngs) - min(all_lngs)) * 0.05
    lat_margin = (max(all_lats) - min(all_lats)) * 0.05

    # Creer la figure A0
    fig, ax = plt.subplots(1, 1,
      figsize=(A0_W_IN, A0_H_IN), dpi=DPI)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # Aspect ratio geographique : 1 degre lng = cos(lat) degre lat.
    # set_aspect(1/cos(lat)) compense la distortion est-ouest sur un
    # plan lat/lng (sinon le secteur apparait ecrase verticalement).
    lat_center = (min(all_lats) + max(all_lats)) / 2
    lng_correction = math.cos(math.radians(lat_center))
    ax.set_aspect(1 / lng_correction)
    ax.axis('off')

    # set_xlim/set_ylim AVANT add_basemap : contextily a besoin de
    # l'extent pour calculer le niveau de zoom des tuiles a fetcher.
    ax.set_xlim(min(all_lngs) - lng_margin,
                max(all_lngs) + lng_margin)
    ax.set_ylim(min(all_lats) - lat_margin,
                max(all_lats) + lat_margin)

    # Fond OSM CartoDB Positron via contextily. crs='EPSG:4326' :
    # axe en lat/lng, contextily reprojette les tuiles Mercator
    # (EPSG:3857) automatiquement vers le plan lat/lng.
    # zoom=16 : noms de rues tres lisibles pour impression A0.
    # Fallback zoom=15 si zoom=16 echoue (timeout, tuile manquante).
    print('[INFO] Fetch tuiles OSM (CartoDB Positron, zoom=16)...')
    try:
        ctx.add_basemap(
            ax,
            crs='EPSG:4326',
            source=ctx.providers.CartoDB.Positron,
            zoom=16,
            attribution=False,
        )
        print('[OK] Fond OSM ajoute (zoom=16)')
    except Exception as exc:
        print(f'[WARN] zoom=16 KO ({exc}), fallback zoom=15...')
        ctx.add_basemap(
            ax,
            crs='EPSG:4326',
            source=ctx.providers.CartoDB.Positron,
            zoom=15,
            attribution=False,
        )
        print('[OK] Fond OSM ajoute (zoom=15)')

    # Passe 2 : dessiner les polygones PAR-DESSUS le fond (ordre
    # d'ajout = ordre de zorder par defaut, donc polygones au-dessus).
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

        poly = MplPolygon(list(zip(lngs, lats)),
                          closed=True)
        patch = PatchCollection([poly],
          facecolor=couleur, edgecolor='white',
          linewidth=1.5, alpha=0.75)
        ax.add_collection(patch)

        # Numero d'ilot au centroide. Texte noir gras 14pt sans bbox :
        # le fond blanc derriere les chiffres masquait le contexte OSM ;
        # sans bbox, l'oeil lit le numero ET la rue dessous.
        cx = sum(lngs) / len(lngs)
        cy = sum(lats) / len(lats)
        ax.text(cx, cy, ilot_id,
            ha='center', va='center',
            fontsize=14,
            fontweight='bold',
            color='black',
            zorder=5)

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
