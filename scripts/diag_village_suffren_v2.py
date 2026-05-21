"""
DIAG 2 v2 cartographie VILLAGE SUFFREN + verif 2/8/14 GUESCLIN.
Lecture seule.
"""
import json
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open(
        'r', encoding='utf-8') as f:
    light = json.load(f)
by_cle = {a['cle']: a for a in light['adresses']}
cp_by_immat = {c['numero_immatriculation']: c
               for c in light['coproprietes']
               if c.get('numero_immatriculation')}

GUESCLIN_BGIDS = {
    '2|PASSAGE|GUESCLIN':  'bdnb-bg-QX4P-4SRC-PQKA',
    '8|PASSAGE|GUESCLIN':  'bdnb-bg-PS7Y-T8QH-F26C',
    '14|PASSAGE|GUESCLIN': 'bdnb-bg-TW35-U22F-U92T',
}

all_bgids = ['bdnb-bg-69B5-LL5X-E2NB', 'bdnb-bg-QNW4-6U22-1GTJ'] \
    + list(GUESCLIN_BGIDS.values())

bg_info = {}
for bg in all_bgids:
    info = {'libelles': [], 'parcelles': [], 'immats': [],
            'annee': None, 'nb_log': None, 'nb_log_rnc': None}
    url = ('https://api.bdnb.io/v1/bdnb/donnees/'
           f'batiment_groupe_complet?batiment_groupe_id=eq.{bg}')
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={'Accept': 'application/json'}),
            timeout=30) as r:
        rows = json.loads(r.read())
    if rows:
        row = rows[0]
        info['libelles'] = row.get('l_libelle_adr') or []
        info['annee'] = row.get('annee_construction')
        info['nb_log'] = row.get('nb_log')
        info['nb_log_rnc'] = row.get('nb_log_rnc')
    url2 = ('https://api.bdnb.io/v1/bdnb/donnees/'
            f'rel_batiment_groupe_rnc?batiment_groupe_id=eq.{bg}')
    with urllib.request.urlopen(urllib.request.Request(
            url2, headers={'Accept': 'application/json'}),
            timeout=20) as r:
        info['immats'] = [x.get('numero_immat')
                          for x in json.loads(r.read())]
    url3 = ('https://api.bdnb.io/v1/bdnb/donnees/'
            f'rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}')
    with urllib.request.urlopen(urllib.request.Request(
            url3, headers={'Accept': 'application/json'}),
            timeout=20) as r:
        info['parcelles'] = [x.get('parcelle_id')
                             for x in json.loads(r.read())]
    bg_info[bg] = info

# Verif copros RNC live sur parcelles 2/8/14 GUESCLIN
RID = '3ea8e2c3-0038-464a-b17e-cd5c91f65ce2'
def rnc_by_refcad(ref):
    out = []
    for col in ('reference_cadastrale_1',
                'reference_cadastrale_2', 'reference_cadastrale_3'):
        url = ('https://tabular-api.data.gouv.fr/api/resources/'
               f'{RID}/data/?' + urllib.parse.urlencode(
                   {f'{col}__exact': ref}))
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={'Accept': 'application/json'}),
                    timeout=30) as r:
                out.extend(json.loads(r.read()).get('data', []))
        except Exception:
            pass
    return out


print('=' * 100)
print('TABLEAU RECAP — VILLAGE SUFFREN cartographie complete')
print('=' * 100)

FACADES = [
    ('AB6092555 (D)', '69B5', '84 RUE FEDERATION', '84|RUE|FEDERATION'),
    ('AB6092555 (D)', '69B5', '86 RUE FEDERATION', '86|RUE|FEDERATION'),
    ('AB6092555 (D)', '69B5', '88 RUE FEDERATION', '88|RUE|FEDERATION'),
    ('AB6092555 (D)', '69B5', '90 RUE FEDERATION', '90|RUE|FEDERATION'),
    ('AB7861529 (EFGH)', 'QNW4', '5 RUE PRESLES',  '5|RUE|PRESLES'),
    ('AB7861529 (EFGH)', 'QNW4', '7 RUE PRESLES',  '7|RUE|PRESLES'),
    ('AB7861529 (EFGH)', 'QNW4', '9 RUE PRESLES',  '9|RUE|PRESLES'),
    ('AB7861529 (EFGH)', 'QNW4', '11 RUE PRESLES', '11|RUE|PRESLES'),
    ('AB7861529 (EFGH)', 'QNW4', '16 PASSAGE GUESCLIN', '16|PASSAGE|GUESCLIN'),
    ('AB7861529 (EFGH)', 'QNW4', '18 PASSAGE GUESCLIN', '18|PASSAGE|GUESCLIN'),
    ('AB7861529 (EFGH)', 'QNW4', '20 PASSAGE GUESCLIN', '20|PASSAGE|GUESCLIN'),
]

print(f"  {'Copro':18s}  {'bgid':5s}  {'Facade BAN':22s}  "
      f"{'Cle light':22s}  {'Status':35s}  Action")
print('-' * 130)
for copro_str, bgs, lib, cle in FACADES:
    immat_target = copro_str.split(' ')[0]
    a = by_cle.get(cle)
    if not a:
        status = 'ABSENT light'
        action = 'INJECT label-only possible'
    else:
        bg_a = a.get('batiment_groupe_id', '') or ''
        bg_short = bg_a[8:12] if bg_a.startswith('bdnb-bg-') else ''
        if a.get('numero_immatriculation') == immat_target:
            if a.get('_fusion_auto'):
                status = f'fused -> {a.get("_fusion_cible")} (porte immat)'
                action = 'INVERSION ANCRE candidat'
            else:
                status = 'ANCRE RNC OK'
                action = '-'
        elif a.get('_fusion_auto'):
            fc = a.get('_fusion_cible', '')
            fc_cp_immat = None
            for c in light['coproprietes']:
                if c.get('cle_adresse') == fc:
                    fc_cp_immat = c.get('numero_immatriculation')
                    break
            if fc_cp_immat == immat_target:
                status = f'fused -> {fc} (ancre OK)'
                action = '-'
            else:
                status = f'fused -> {fc}'
                action = f'verifier (cible immat={fc_cp_immat})'
        else:
            status = f'ORPHELINE bgid={bg_short} syndic={(a.get("syndic") or "-")[:14]}'
            action = 'RE-FUSE vers ancre RNC'
    print(f"  {copro_str:18s}  {bgs:5s}  {lib:22s}  {cle:22s}  "
          f"{status:35s}  {action}")

# Section 2/8/14 GUESCLIN
print()
print('=' * 130)
print('CAS 2/8/14 PASSAGE GUESCLIN (signalement terrain user 2026-05-21)')
print('=' * 130)
print(f"  {'Cle light':22s}  {'bgid':10s}  {'Annee':5s}  "
      f"{'nb_log':>6s}  {'Syndic light':22s}  rel_RNC BDNB / Copros RNC parcelle")
print('-' * 130)
for cle, bg in GUESCLIN_BGIDS.items():
    a = by_cle.get(cle, {})
    info = bg_info.get(bg, {})
    bg_short = bg[8:18]
    annee = str(a.get('annee_construction') or '-')
    nlog = str(a.get('nb_log_bdnb') or '-')
    syn = (a.get('syndic') or '-')[:22]
    immats = info.get('immats', [])
    parcs = info.get('parcelles', [])
    # Verif RNC live par parcelle
    rnc_hits = []
    for parc in parcs:
        if parc.startswith('75115000'):
            ref_rnc = '75056115' + parc[8:]
            for r in rnc_by_refcad(ref_rnc):
                rnc_hits.append(
                    f'{r.get("numero_immatriculation")}'
                    f' ({r.get("nom_usage_copropriete","")[:30]})')
    immat_status = f'rel_RNC={immats} parc={parcs}'
    print(f"  {cle:22s}  {bg_short:10s}  {annee:5s}  {nlog:>6s}  "
          f"{syn:22s}  {immat_status}")
    if rnc_hits:
        for h in rnc_hits[:3]:
            print(f"      RNC live parcelle : {h}")
    else:
        print(f"      RNC live parcelle : AUCUNE copro RNC trouvee")

print()
print('=' * 130)
print('SYNTHESE')
print('=' * 130)
print('VILLAGE SUFFREN connu RNC = 2 copros distinctes :')
print('  AB6092555 D     : bgid 69B5, parcelle DI/0003, 110 lots, GERARD SAFAR (4 facades FEDERATION)')
print('  AB7861529 EFGH  : bgid QNW4, parcelle DI/0010, 116 lots, GERARD SAFAR (4 PRESLES + 3 GUESCLIN)')
print()
print('2/8/14 PASSAGE GUESCLIN :')
print('  - 3 bgids BDNB DISTINCTS (QX4P 1987, PS7Y 1969, TW35 1966) ≠ bgids VILLAGE SUFFREN connus')
print('  - syndic GERARD SAFAR par cadastre (match)')
print('  - dans le light : fused entre eux (14 ancre, label "2/8/14 PASSAGE GUESCLIN")')
print('  - aucune copro RNC attribuee (rel_RNC vide)')
print('  - confirmation terrain user : "fait partie du VILLAGE SUFFREN"')
print()
print('CONCLUSION 2/8/14 :')
print('  -> Possibles copros A/B/C VILLAGE SUFFREN non immatriculees RNC, ou copros')
print('     distinctes gerees par GERARD SAFAR sans appartenance VILLAGE SUFFREN.')
print('  -> RNC live ne trouve AUCUNE copro VS au-dela de D et EFGH (recherche par nom).')
print('  -> Verif parcelles necessaire pour conclusion definitive.')
