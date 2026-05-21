"""
SCAN lecture-seule : detecter les adresses hors-RNC non-fusees qui
partagent un bgid avec une ancre RNC connue (cas 6 CHAMPAUBERT).
Pattern propose pour passe 'bgid-orphelin' du pipeline make_light.

Critere :
  - adresse hors-RNC (immat null AND pas dans coproprietes)
  - bgid attribue dans BDNB
  - bgid deja occupe par une ancre RNC active (bgRncLots[bg] existe)
  - PAS deja fused (_fusion_auto != True)

Sortie : tableau ASCII trie par bgid (groupes) + stats.
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open(
        'r', encoding='utf-8') as f:
    light = json.load(f)
cp_by_cle = {c.get('cle_adresse'): c
             for c in light.get('coproprietes', [])
             if c.get('cle_adresse')}

# 1) bgid -> [ancres RNC actives (cle, immat, lots)]
bg_anchors = defaultdict(list)
for a in light['adresses']:
    bg = a.get('batiment_groupe_id')
    cle = a.get('cle')
    if not bg or not cle:
        continue
    if a.get('_fusion_auto'):
        continue
    cp = cp_by_cle.get(cle)
    if not cp:
        continue
    lots = cp.get('nb_lots_habitation') or 0
    if lots <= 0:
        continue
    immat = (cp.get('numero_immatriculation')
             or cp.get('cle_adresse') or cle)
    bg_anchors[bg].append({
        'cle': cle, 'immat': immat, 'lots': lots,
        'nom': cp.get('nom_copropriete'),
        'syndic': cp.get('syndic'),
    })

# 2) Orphelins : hors-RNC + bgid partage avec ancre + pas fused
orphelins = []
for a in light['adresses']:
    cle = a.get('cle')
    bg = a.get('batiment_groupe_id')
    if not bg:
        continue
    if a.get('numero_immatriculation') or cp_by_cle.get(cle):
        continue
    if a.get('_fusion_auto'):
        continue
    if bg not in bg_anchors:
        continue
    orphelins.append(a)

print(f'Ancres RNC (bgid->copro) : {len(bg_anchors)} bgids actifs')
print(f'Adresses orphelines sur bgid RNC : {len(orphelins)}')
print()

orphelins.sort(key=lambda a: (a.get('batiment_groupe_id'), a.get('cle')))
by_bg = defaultdict(list)
for o in orphelins:
    by_bg[o.get('batiment_groupe_id')].append(o)

print('=' * 180)
print('SCAN BGID-ORPHELIN - adresses hors-RNC non-fusees sur bgids deja RNC')
print('=' * 180)
hdr = (f"{'#':>4}  {'Cle orphelin':38}  {'bgid':30}  "
       f"{'Ancre RNC (cle)':28}  {'Immat':10}  {'Syndic ancre':22}  "
       f"{'Lots':>4}  {'vlog':>4}  {'syndic orph':22}  {'usage':22}")
print(hdr)
print('-' * 180)
n = 0
multi_warnings = []
for bg, orphs in sorted(by_bg.items(), key=lambda x: (-len(x[1]), x[0])):
    ancres = bg_anchors[bg]
    principal = max(ancres, key=lambda x: x['lots'])
    multi = len(ancres) > 1
    if multi:
        multi_warnings.append((bg, [a['immat'] for a in ancres], len(orphs)))
    for o in orphs:
        n += 1
        cle_o = (o.get('cle') or '')[:38]
        syn_o = (o.get('syndic') or '-')[:22]
        usage = (o.get('usage_principal_bdnb') or '-')[:22]
        vlog = o.get('nb_ventes_logement') or 0
        syn_a = (principal.get('syndic') or '-')[:22]
        cle_a = principal['cle'][:28]
        marker = ' [MULTI]' if multi else ''
        print(f"{n:>4}  {cle_o:38}  {bg:30}  {cle_a:28}  "
              f"{principal['immat']:10}  {syn_a:22}  "
              f"{principal['lots']:>4}  {vlog:>4}  {syn_o:22}  "
              f"{usage:22}{marker}")

print('=' * 180)
print(f'TOTAL : {n} orphelins sur {len(by_bg)} bgids RNC partages')

# Stats critere syndic match (haute confiance pour auto-fusion)
def s(x):
    return (x or '').strip()

syn_match = sum(
    1 for o in orphelins
    if s(o.get('syndic')) and any(s(o.get('syndic')) == s(a.get('syndic'))
                                  for a in bg_anchors[o['batiment_groupe_id']]))
vlog_pos = sum(1 for o in orphelins
               if (o.get('nb_ventes_logement') or 0) > 0)
resid = sum(1 for o in orphelins
            if o.get('usage_principal_bdnb') in (
                'Résidentiel collectif', 'Résidentiel individuel'))
tert = sum(1 for o in orphelins
           if o.get('usage_principal_bdnb') == 'Tertiaire')

print()
print('Stats orphelins :')
print(f'  - syndic orph match exact syndic ancre : {syn_match}')
print(f'  - avec vlog DVF > 0                     : {vlog_pos}')
print(f'  - usage Residentiel                     : {resid}')
print(f'  - usage Tertiaire                       : {tert}')

if multi_warnings:
    print()
    print(f'Bgids avec MULTI ancres RNC (>1 copro/bgid) : {len(multi_warnings)}')
    print(f'  -> risque ambiguite cible, principal = ancre avec le plus de lots')
    for bg, immats, no in multi_warnings:
        print(f'  {bg} : ancres {immats} - {no} orph(s) impacte(s)')
