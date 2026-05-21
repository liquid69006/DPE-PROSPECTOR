"""
Extraction lecture-seule des ventes 'immeuble entier' / vente bloc
dans le perimetre Motte-Picquet (DVF 2021-2025).

Critere : Vente DVF, groupee par (date + valeur + section + plan),
categorisee selon les types_locaux des lots constitutifs :
  - IMMEUBLE_RESID : vente bloc residentiel (>=5 appartements OU
    >=3 apt + >=2M EUR)
  - BLOC_MIXTE     : multi-lots avec mix apartments / commerces /
    dependances
  - GROS_LOT       : 1 seul lot mais >=2M EUR (hotel particulier)
  - COMMERCE/BUREAUX : lots commerciaux seuls (cessions activite)
  - FONCIER        : 0 lot declare (terrain, droit, cession
    institutionnelle)

Sortie : 2 tableaux ASCII tries valeur decroissante + stats.
Aucune modification fichier.
"""
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'dvf_motte_picquet.json').open('r', encoding='utf-8') as f:
    dvf = json.load(f)
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open('r', encoding='utf-8') as f:
    light = json.load(f)

PREPS = re.compile(r'^(DE|DU|DES|LA|LE|L|D)\s+', re.I)
TYPES = {
    'AV': 'AVENUE', 'BD': 'BOULEVARD', 'R': 'RUE', 'RUE': 'RUE',
    'PL': 'PLACE', 'SQ': 'SQUARE', 'IMP': 'IMPASSE', 'VLA': 'VILLA',
    'ALL': 'ALLEE', 'PAS': 'PASSAGE', 'PASS': 'PASSAGE',
    'CRS': 'COURS', 'QU': 'QUAI', 'CHE': 'CHEMIN', 'RTE': 'ROUTE',
}


def normalize_voie(v):
    v = (v or '').upper().strip()
    while True:
        m = PREPS.match(v)
        if not m:
            break
        v = v[m.end():]
    return v.strip()


def light_cle(no, type_voie, voie):
    tv = TYPES.get((type_voie or '').upper().strip(),
                   (type_voie or '').upper().strip())
    return f"{no}|{tv}|{normalize_voie(voie)}"


def parse_val(s):
    if not s:
        return 0.0
    try:
        return float(str(s).replace(',', '.').replace(' ', ''))
    except Exception:
        return 0.0


def parse_date(s):
    if not s or '/' not in s:
        return ''
    d, mo, y = s.split('/')
    return f'{y}-{mo}-{d}'


adr_by_cle = {a.get('cle'): a for a in light.get('adresses', [])}
cp_by_cle = {c.get('cle_adresse'): c
             for c in light.get('coproprietes', [])
             if c.get('cle_adresse')}


def keyof(m):
    return (m.get('Date mutation', ''), m.get('Valeur fonciere', ''),
            m.get('Section', ''), m.get('No plan', ''))


groups = defaultdict(list)
for m in dvf:
    if m.get('Nature mutation', '') != 'Vente':
        continue
    groups[keyof(m)].append(m)

mutations = []
for k, rows in groups.items():
    date_iso = parse_date(rows[0].get('Date mutation', ''))
    if date_iso < '2020-01-01':
        continue
    val = parse_val(rows[0].get('Valeur fonciere', ''))
    lots_set = set()
    n_app = n_dep = n_com = 0
    surf_carrez = surf_bati = surf_terrain = 0.0
    for r in rows:
        lot = r.get('1er lot', '')
        if lot:
            if lot not in lots_set:
                lots_set.add(lot)
                surf_carrez += parse_val(r.get('Surface Carrez du 1er lot', ''))
                surf_bati += parse_val(r.get('Surface reelle bati', ''))
            ctl = r.get('Code type local', '')
            if ctl == '2':
                n_app += 1
            elif ctl == '3':
                n_dep += 1
            elif ctl == '4':
                n_com += 1
        surf_terrain = max(surf_terrain,
                           parse_val(r.get('Surface terrain', '')))
    nlots = len(lots_set)
    r0 = rows[0]
    no = r0.get('No voie', '')
    tv = r0.get('Type de voie', '')
    voie = r0.get('Voie', '')
    cp = r0.get('Code postal', '')
    adresse = f"{no} {tv} {voie} {cp}".strip()
    cle = light_cle(no, tv, voie)
    a = adr_by_cle.get(cle)
    bgid = (a or {}).get('batiment_groupe_id')
    immat = ((a or {}).get('numero_immatriculation')
             or (cp_by_cle.get(cle, {}) or {}).get('numero_immatriculation'))
    if not bgid:
        for k2, av in adr_by_cle.items():
            if k2.startswith(cle + ' #'):
                bgid = bgid or av.get('batiment_groupe_id')
                immat = immat or av.get('numero_immatriculation')
                break

    if nlots == 0:
        cat = 'FONCIER'
    elif nlots == 1 and n_app == 1 and val < 1_000_000:
        cat = 'lot_individuel'
    elif n_app >= 5 or (n_app >= 3 and val >= 2_000_000):
        cat = 'IMMEUBLE_RESID'
    elif n_com >= 1 and n_app == 0:
        cat = 'COMMERCE/BUREAUX'
    elif nlots >= 2 and (n_app >= 1 or n_com >= 1):
        cat = 'BLOC_MIXTE'
    elif nlots == 1 and val >= 2_000_000:
        cat = 'GROS_LOT'
    else:
        cat = 'AUTRE'

    qualif = (cat in ('IMMEUBLE_RESID', 'BLOC_MIXTE',
                      'COMMERCE/BUREAUX', 'GROS_LOT')
              or val >= 5_000_000)
    if not qualif:
        continue

    mutations.append({
        'date_iso': date_iso,
        'date_disp': r0.get('Date mutation', ''),
        'val': val, 'nlots': nlots,
        'n_app': n_app, 'n_dep': n_dep, 'n_com': n_com,
        'surf_carrez': surf_carrez, 'surf_bati': surf_bati,
        'surf_terrain': surf_terrain,
        'adresse': adresse,
        'section': r0.get('Section', ''),
        'plan': r0.get('No plan', ''),
        'bgid': bgid or '-',
        'immat': immat or '-',
        'cat': cat,
    })

mutations.sort(key=lambda x: (-x['val'], x['date_iso']))

cats = Counter(m['cat'] for m in mutations)
print(f'Mutations retenues : {len(mutations)}')
print('Repartition par categorie :')
for c, n in cats.most_common():
    s = sum(m['val'] for m in mutations if m['cat'] == c)
    s_fmt = f'{s:>16,.0f}'.replace(',', ' ')
    print(f'  {c:18s} {n:4d} mutations  total {s_fmt} EUR')

print()
print('=' * 165)
print('TABLEAU 1 - IMMEUBLES ENTIERS RESIDENTIELS (vente bloc multi-appartements)')
print('=' * 165)
muts1 = [m for m in mutations if m['cat'] in ('IMMEUBLE_RESID', 'BLOC_MIXTE')]
print(f'{len(muts1)} mutations - tri valeur decroissante')
print()
hdr = (f"{'Date':11} {'Valeur':>14} {'Lots':>4} {'App':>3} {'Dep':>3} "
       f"{'Com':>3} {'SurfCrz':>8} {'SurfBati':>8} {'Sec':>4} {'Plan':>5}  "
       f"{'Adresse':38}  {'Immat':10}  {'Cat':12}  Bgid")
print(hdr)
print('-' * 165)
for m in muts1[:60]:
    v = f"{m['val']:>10,.0f}".replace(',', ' ')
    print(f"{m['date_disp']:11} {v:>14} EUR  {m['nlots']:>3} {m['n_app']:>3} "
          f"{m['n_dep']:>3} {m['n_com']:>3} {m['surf_carrez']:>8.0f} "
          f"{m['surf_bati']:>8.0f} {m['section']:>4} {m['plan']:>5}  "
          f"{m['adresse'][:38]:38}  {m['immat']:10}  {m['cat']:12}  "
          f"{m['bgid'][:34]}")

print()
print('=' * 165)
print('TABLEAU 2 - CESSIONS COMMERCIALES / GROS LOTS / FONCIER >= 5M EUR '
      '(institutionnel, bureaux, terrain)')
print('=' * 165)
muts2 = [m for m in mutations
         if m['cat'] in ('COMMERCE/BUREAUX', 'GROS_LOT', 'FONCIER', 'AUTRE')
         and m['val'] >= 5_000_000]
print(f'{len(muts2)} mutations')
print()
hdr2 = (f"{'Date':11} {'Valeur':>14} {'Lots':>4} {'App':>3} {'Com':>3} "
        f"{'SurfBati':>8} {'SurfTerr':>8} {'Sec':>4} {'Plan':>5}  "
        f"{'Adresse':38}  {'Immat':10}  {'Cat':16}  Bgid")
print(hdr2)
print('-' * 165)
for m in muts2[:30]:
    v = f"{m['val']:>10,.0f}".replace(',', ' ')
    print(f"{m['date_disp']:11} {v:>14} EUR  {m['nlots']:>3} {m['n_app']:>3} "
          f"{m['n_com']:>3} {m['surf_bati']:>8.0f} {m['surf_terrain']:>8.0f} "
          f"{m['section']:>4} {m['plan']:>5}  {m['adresse'][:38]:38}  "
          f"{m['immat']:10}  {m['cat']:16}  {m['bgid'][:34]}")

print()
print('LEGENDE :')
print('  IMMEUBLE_RESID   = vente bloc residentiel (>=5 appartements OU >=3 apt + >=2M EUR)')
print('  BLOC_MIXTE       = multi-lots mix (apartments + commerces + dependances)')
print('  GROS_LOT         = 1 seul lot >=2M EUR (hotel particulier / etage entier)')
print('  COMMERCE/BUREAUX = lots commerciaux seuls (cessions activite)')
print('  FONCIER          = 0 lot declare (terrain, droit, cession institutionnelle)')
print()
print('Note : groupement par (date+valeur+section+plan). Les lignes DVF '
      'incluant le meme `1er lot` repetee sont dedupliquees (count distinct).')
