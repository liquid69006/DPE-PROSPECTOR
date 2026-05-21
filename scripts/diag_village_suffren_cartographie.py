"""
DIAG 2 lecture-seule : cartographie complete du VILLAGE SUFFREN
(MS-110200 ensemble immobilier multi-copros A/B/C/D/E/F/G/H).

Etapes :
  1) RNC live tabular-api : toutes copros 75115 dont nom contient
     'VILLAGE SUFFREN' OU 'MS11202' (codes serie).
  2) Pour chaque copro RNC -> BDNB rel_batiment_groupe_rnc reverse
     (numero_immat=IMMAT) -> tous les bgids associes.
  3) Pour chaque bgid -> BDNB pivot l_libelle_adr (toutes les
     facades BAN).
  4) Croiser avec le light : pour chaque facade
       - existe dans adresses[] ?
       - bgid match ?
       - fused vers l'ancre RNC attendue ?
       - inversion ancre detectee ?
  5) Tableau recap + actions suggerees.

Aucune modification.
"""
import json
import urllib.request
import urllib.parse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open(
        'r', encoding='utf-8') as f:
    light = json.load(f)
by_cle = {a['cle']: a for a in light['adresses']}
cp_by_cle = {c['cle_adresse']: c
             for c in light['coproprietes'] if c.get('cle_adresse')}
cp_by_immat = {c['numero_immatriculation']: c
               for c in light['coproprietes']
               if c.get('numero_immatriculation')}

RID = '3ea8e2c3-0038-464a-b17e-cd5c91f65ce2'


def rnc_search_nom(q):
    url = ('https://tabular-api.data.gouv.fr/api/resources/'
           f'{RID}/data/?' + urllib.parse.urlencode(
               {'commune__exact': '75115',
                'nom_usage_copropriete__contains': q}))
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={'Accept': 'application/json'}),
                timeout=30) as r:
            return json.loads(r.read()).get('data', [])
    except Exception as e:
        print(f'  ERR RNC {q!r}: {e}')
        return []


# 1) Toutes copros RNC live 'VILLAGE SUFFREN' + variantes
print('=' * 80)
print('ETAPE 1 - Copros RNC VILLAGE SUFFREN (RNC live 75115)')
print('=' * 80)
copros_rnc = {}
for q in ['VILLAGE SUFFREN', 'village suffren', 'Village Suffren']:
    for row in rnc_search_nom(q):
        immat = row.get('numero_immatriculation')
        if immat and immat not in copros_rnc:
            copros_rnc[immat] = row

# Aussi recherche par parcelles connues VILLAGE SUFFREN
print(f'  {len(copros_rnc)} copros RNC live distinctes :')
for immat, row in copros_rnc.items():
    print(f'    {immat} : {row.get("nom_usage_copropriete")!r}')
    print(f'             adresse_ref = {row.get("numero_voie_adresse")!r}')
    print(f'             {row.get("nombre_lots_habitation")} lots hab '
          f'/ {row.get("nombre_total_lots")} tot, '
          f'syndic={row.get("raison_sociale_representant_legal")!r}')
    refs = [row.get(f'reference_cadastrale_{i}') for i in (1, 2, 3)]
    refs = [r for r in refs if r]
    print(f'             ref_cadastrales = {refs}')

# 2) Pour chaque immat -> bgids via BDNB rel_RNC reverse
print()
print('=' * 80)
print('ETAPE 2 - Bgids BDNB associes (reverse rel_batiment_groupe_rnc)')
print('=' * 80)
bgid_by_immat = defaultdict(set)
for immat in copros_rnc.keys():
    url = ('https://api.bdnb.io/v1/bdnb/donnees/'
           f'rel_batiment_groupe_rnc?numero_immat=eq.{immat}')
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={'Accept': 'application/json'}),
                timeout=20) as r:
            rows = json.loads(r.read())
        for r in rows:
            bg = r.get('batiment_groupe_id')
            if bg:
                bgid_by_immat[immat].add(bg)
    except Exception as e:
        print(f'  ERR {immat}: {e}')
    print(f'  {immat} : {len(bgid_by_immat[immat])} bgid(s) -> '
          f'{sorted(bgid_by_immat[immat])}')

# 3) Pour chaque bgid -> pivot l_libelle_adr + parcelle
all_bgids = set()
for bgs in bgid_by_immat.values():
    all_bgids |= bgs
print()
print('=' * 80)
print('ETAPE 3 - Pivot BDNB l_libelle_adr + parcelles')
print('=' * 80)
bg_info = {}
for bg in sorted(all_bgids):
    url = ('https://api.bdnb.io/v1/bdnb/donnees/'
           f'batiment_groupe_complet?batiment_groupe_id=eq.{bg}')
    out = {'libelles': [], 'principal': None, 'annee': None,
           'nb_log': None, 'nb_log_rnc': None, 'usage': None}
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={'Accept': 'application/json'}),
                timeout=30) as r:
            rows = json.loads(r.read())
        if rows:
            row = rows[0]
            out['libelles'] = row.get('l_libelle_adr') or []
            out['principal'] = row.get('libelle_adr_principale_ban')
            out['annee'] = row.get('annee_construction')
            out['nb_log'] = row.get('nb_log')
            out['nb_log_rnc'] = row.get('nb_log_rnc')
            out['usage'] = row.get('usage_principal_bdnb_open')
        url2 = ('https://api.bdnb.io/v1/bdnb/donnees/'
                f'rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}')
        with urllib.request.urlopen(urllib.request.Request(
                url2, headers={'Accept': 'application/json'}),
                timeout=20) as r:
            out['parcelles'] = [x.get('parcelle_id')
                                for x in json.loads(r.read())]
    except Exception as e:
        out['err'] = str(e)
    bg_info[bg] = out
    print(f'  {bg}: ancre={out["principal"]!r} parcelle={out["parcelles"]} '
          f'annee={out["annee"]} nb_log={out["nb_log"]} '
          f'nb_log_rnc={out["nb_log_rnc"]} usage={out["usage"]}')
    print(f'    facades ({len(out["libelles"])}):')
    for lib in out['libelles']:
        print(f'      - {lib}')

# 4) Croisement light : pour chaque facade BAN, status
print()
print('=' * 80)
print('ETAPE 4 - Croisement avec light JSON')
print('=' * 80)


def lib_to_cle(lib):
    """Heuristique : 'X Avenue De Y' -> 'X|AVENUE|Y' (sans DE/DU/DES)."""
    import re
    s = lib.split(',')[0].strip()
    m = re.match(r'^(\d+\w?)\s+(\S+)\s+(.+)$', s)
    if not m:
        return None
    no, tv, voie = m.group(1), m.group(2), m.group(3)
    # type voie : Avenue->AVENUE, Rue->RUE, etc.
    tv_norm = tv.upper()
    voie_up = voie.upper()
    voie_up = re.sub(r'^(DE\s+|DU\s+|DES\s+|LA\s+)', '', voie_up).strip()
    # Variantes mapping
    if tv_norm in ('AVENUE', 'AV'): tv_norm = 'AVENUE'
    elif tv_norm in ('RUE', 'R'): tv_norm = 'RUE'
    elif tv_norm in ('BOULEVARD', 'BD'): tv_norm = 'BOULEVARD'
    elif tv_norm in ('PASSAGE', 'PAS', 'PASS'): tv_norm = 'PASSAGE'
    return f'{no}|{tv_norm}|{voie_up}'


report = []
for immat, bgs in bgid_by_immat.items():
    nom = copros_rnc[immat].get('nom_usage_copropriete', '')
    # Trouver l'ancre attendue dans coproprietes light
    cp_light = cp_by_immat.get(immat)
    if cp_light:
        ancre_attendue = cp_light.get('cle_adresse')
    else:
        ancre_attendue = '(copro absente light)'

    for bg in sorted(bgs):
        info = bg_info.get(bg, {})
        for lib in info.get('libelles', []):
            cle_attendu = lib_to_cle(lib)
            ad = by_cle.get(cle_attendu) if cle_attendu else None
            # Variantes possibles : disambig
            if not ad and cle_attendu:
                for k in by_cle:
                    if k.startswith(cle_attendu + ' #'):
                        ad = by_cle[k]
                        cle_attendu = k
                        break

            if not ad:
                status = 'ABSENT'
                action = 'INJECT label-only ou inutile (si pas BAN actif)'
            else:
                bg_light = ad.get('batiment_groupe_id', '')
                if bg_light != bg:
                    status = f'PRESENT mais bgid DIFFERENT ({bg_light})'
                    action = 'CORRECTION BGID + fuse vers ancre'
                elif ad.get('numero_immatriculation') == immat:
                    if ad.get('_fusion_auto'):
                        status = f'fused vers {ad.get("_fusion_cible")!r} (PORTE immat)'
                        action = 'INVERSION ANCRE possible (porte immat mais fused)'
                    else:
                        status = 'ANCRE RNC OK'
                        action = '-'
                elif ad.get('_fusion_auto'):
                    fc = ad.get('_fusion_cible', '')
                    fc_cp = cp_by_cle.get(fc)
                    if fc_cp and fc_cp.get('numero_immatriculation') == immat:
                        status = f'fused -> {fc} (ancre RNC OK)'
                        action = '-'
                    else:
                        status = f'fused -> {fc} (PAS ancre RNC attendue)'
                        action = f'RE-FUSE vers ancre {ancre_attendue}'
                else:
                    syn_match = (ad.get('syndic', '') or '').strip() == (
                        copros_rnc[immat].get(
                            'raison_sociale_representant_legal', '') or '').strip()
                    status = (f'ORPHELINE (bgid OK, pas immat)'
                              f' syndic_match={syn_match}')
                    action = f'RE-FUSE vers ancre {ancre_attendue}'
            report.append({
                'lib': lib[:48],
                'cle': cle_attendu or '(parsing fail)',
                'bgid': bg[-8:],   # short
                'immat': immat,
                'status': status[:50],
                'action': action[:48],
            })

# Tableau recap
print()
print('=' * 180)
print('TABLEAU RECAP - cartographie VILLAGE SUFFREN')
print('=' * 180)
hdr = (f"{'Facade BAN':50}  {'Cle light':32}  {'bgid':10}  "
       f"{'Immat':10}  {'Status light':52}  Action")
print(hdr)
print('-' * 180)
for r in sorted(report, key=lambda x: (x['immat'], x['cle'])):
    print(f"  {r['lib']:48}  {r['cle']:32}  {r['bgid']:10}  "
          f"{r['immat']:10}  {r['status']:52}  {r['action']}")
print('=' * 180)

# Stats
from collections import Counter
stats = Counter(r['action'] for r in report)
print()
print('Actions suggerees :')
for a, n in stats.most_common():
    print(f'  {n:3d}  {a}')
