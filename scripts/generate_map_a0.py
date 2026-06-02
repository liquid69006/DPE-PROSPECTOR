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
  - Fond CartoDB en double couche (crs='EPSG:4326', reproj auto
    des tuiles Mercator vers le plan lat/lng) :
      1. light_nolabels (base : rues + batiments sans noms)
      2. light_only_labels (overlay : noms de rues au-dessus des
         polygones de prospection, sinon les couleurs masqueraient).
  - L'ilot 82 (27 av. Lacassagne) n'a pas de polygone KML : ignore.
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
    # [ZONE] AGENCE_ID porte deja la zone via suffixe '-montchat' (secId front).
    _SUF = '-montchat'
    zone = 'montchat' if agence_id.endswith(_SUF) else 'dl'
    base_agence = agence_id[:-len(_SUF)] if agence_id.endswith(_SUF) else agence_id
    data = json.loads(rep_raw)
    repartition = data['repartition']
    conseillers = {c['id']: c for c in data['conseillers']}

    # [ZONE] Charger les KML scopes a la zone via data/kml_manifest.json
    # (fin du glob global qui melangeait DL + Montchat).
    kml_dir = Path('data/kml')
    polygones = {}
    manifest = {}
    try:
        manifest = json.loads(Path('data/kml_manifest.json').read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[WARN] manifeste illisible ({e})")
    files = (manifest.get(base_agence, {}) or {}).get(zone)
    if files:
        loaded = []
        for fn in files:
            polygones.update(parse_kml(kml_dir / fn))
            loaded.append(fn)
        print(f"[INFO] zone={zone} base_agence={base_agence} kml={loaded}")
    else:
        print(f"[WARN] manifeste/zone absent (base_agence={base_agence} zone={zone}) -> fallback glob('*.kml')")
        loaded = []
        for kml_file in kml_dir.glob('*.kml'):
            polygones.update(parse_kml(kml_file))
            loaded.append(kml_file.name)
        print(f"[INFO] zone={zone} base_agence={base_agence} kml={loaded}")
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

    # Fond OSM CartoDB en double couche via contextily.
    # 1. BASE = light_nolabels : rues, batiments, parcs sans texte.
    # 2. (apres polygones) OVERLAY = light_only_labels : noms de
    #    rues par-dessus les polygones colories.
    # URLs @2x = tuiles 512px (vs 256px standard) pour eviter le
    # flou a 200 DPI sur figure A0.
    base_url = (
        "https://a.basemaps.cartocdn.com"
        "/light_nolabels/{z}/{x}/{y}@2x.png"
    )
    labels_url = (
        "https://a.basemaps.cartocdn.com"
        "/light_only_labels/{z}/{x}/{y}@2x.png"
    )

    # zoom=16 : noms de rues tres lisibles pour impression A0.
    # Fallback zoom=15 si zoom=16 echoue (timeout, tuile manquante).
    print('[INFO] Fetch tuiles OSM base (zoom=16)...')
    try:
        ctx.add_basemap(
            ax,
            crs='EPSG:4326',
            source=base_url,
            zoom=16,
            attribution=False,
            zorder=1,
        )
        used_zoom = 16
        print('[OK] Fond OSM base ajoute (zoom=16)')
    except Exception as exc:
        print(f'[WARN] zoom=16 KO ({exc}), fallback zoom=15...')
        ctx.add_basemap(
            ax,
            crs='EPSG:4326',
            source=base_url,
            zoom=15,
            attribution=False,
            zorder=1,
        )
        used_zoom = 15
        print('[OK] Fond OSM base ajoute (zoom=15)')

    # Passe 2 : dessiner les polygones (zorder=2) au-dessus de la base
    # OSM (zorder=1). Alpha 0.60 : laisse voir les rues/batiments
    # dessous, sera complete par le 2e basemap labels (zorder=3) qui
    # ajoute les noms par-dessus les couleurs.
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
          linewidth=1.5, alpha=0.60, zorder=2)
        ax.add_collection(patch)

    # Overlay labels OSM (zorder=3) par-dessus les polygones :
    # les noms de rues restent visibles malgre la coloration.
    print(f'[INFO] Overlay labels OSM (zoom={used_zoom})...')
    try:
        ctx.add_basemap(
            ax,
            crs='EPSG:4326',
            source=labels_url,
            zoom=used_zoom,
            attribution=False,
            zorder=3,
        )
        print('[OK] Overlay labels ajoute')
    except Exception as exc:
        print(f'[WARN] Overlay labels KO ({exc}) : carte sans noms de rues')


    # Marker agence
    AGENCE_COORDS = {
      'dauphine-lacassagne': (4.86502, 45.75685),
      'motte-picquet': (2.30, 48.85),
    }
    if base_agence in AGENCE_COORDS:
        lng_a, lat_a = AGENCE_COORDS[base_agence]
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
