"""
Extraction lecture-seule des adresses hors-RNC sans logements BDNB
ET sans ventes DVF dans Motte-Picquet, pour qualification manuelle
via menu UI (commit 94b3de5 + ee3185f).

Criteres :
  - hors-RNC : numero_immatriculation None/'' ET pas dans
    coproprietes[cle_adresse]
  - nb_log_bdnb = 0 ou null
  - nb_ventes_logement = 0 ou null (et nb_ventes_total = 0 ou null
    aussi, pour ne pas garder les commerces vendus)
  - _fusion_auto = False (ancres uniquement, pas les fused vers une
    autre cle)

Enrichissement BDNB (cache local par bgid) :
  - usage_principal_bdnb du snapshot (deja dans adresses)
  - l_libelle_adr_count (nb de facades BAN) si bgid present

Note : la qualification posee (as.type) est dans KV Cloudflare cote
worker.js, pas accessible en lecture locale. Colonne 'Qualif' affichee
'-' systematiquement (a verifier via l'UI dashboard).

Sortie : tableau ASCII trie par usage BDNB puis cle_adresse.
Aucune modification fichier.
"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open(
        'r', encoding='utf-8') as f:
    light = json.load(f)

cp_by_cle = {c.get('cle_adresse'): c
             for c in light.get('coproprietes', [])
             if c.get('cle_adresse')}


def is_empty(v):
    return v is None or v == '' or v == 0


candidates = []
for a in light.get('adresses', []):
    cle = a.get('cle', '')
    immat = a.get('numero_immatriculation')
    in_cp = cp_by_cle.get(cle)
    # Hors-RNC strict : pas d'immat ET pas dans coproprietes
    if immat or in_cp:
        continue
    # _fusion_auto = False (ancre, pas fused)
    if a.get('_fusion_auto'):
        continue
    nlog = a.get('nb_log_bdnb')
    nv_log = a.get('nb_ventes_logement')
    nv_tot = a.get('nb_ventes_total')
    if not is_empty(nlog):
        continue
    if not is_empty(nv_log):
        continue
    if not is_empty(nv_tot):
        continue
    candidates.append(a)

print(f'Candidats hors-RNC sans logements ni ventes : {len(candidates)}')
print()

# Stats usage BDNB
usages = Counter(a.get('usage_principal_bdnb') or '(inconnu)'
                 for a in candidates)
print('Repartition par usage_principal_bdnb :')
for u, n in usages.most_common():
    print(f'  {n:4d}  {u}')

# Stats MAJIC / SCI
print()
n_majic = sum(1 for a in candidates if a.get('dans_majic'))
n_sci = sum(1 for a in candidates if a.get('sci_proprietaire') == 'oui')
n_no_bgid = sum(1 for a in candidates
                if not a.get('batiment_groupe_id'))
print(f'dans_majic=True    : {n_majic}')
print(f'sci_proprietaire   : {n_sci}')
print(f'sans bgid BDNB     : {n_no_bgid}')

# Tri par usage puis cle
candidates.sort(key=lambda a: (
    a.get('usage_principal_bdnb') or 'zzz',
    a.get('cle') or '',
))

print()
print('=' * 175)
print('TABLEAU - adresses hors-RNC sans logements ni ventes (qualification manuelle)')
print('=' * 175)
hdr = (f"{'#':>4}  {'Cle adresse':40}  {'Usage BDNB':24}  "
       f"{'Annee':5}  {'Bgid':30}  {'Majic':5}  {'SCI':4}  "
       f"{'SCI nom (SIREN)':30}  {'Qualif':10}")
print(hdr)
print('-' * 175)
for i, a in enumerate(candidates, 1):
    cle = (a.get('cle') or '')[:40]
    usage = (a.get('usage_principal_bdnb') or '(inconnu)')[:24]
    annee = a.get('annee_construction') or '-'
    bgid = (a.get('batiment_groupe_id') or '-')[:30]
    majic = 'oui' if a.get('dans_majic') else 'non'
    sci = a.get('sci_proprietaire') or '-'
    sci_nom = a.get('sci_nom') or ''
    sci_siren = a.get('sci_siren') or ''
    sci_str = (f'{sci_nom} ({sci_siren})' if sci_nom and sci_siren
               else (sci_nom or '-'))[:30]
    qualif = '-'   # KV Cloudflare non accessible localement
    print(f"{i:>4}  {cle:40}  {usage:24}  {str(annee):>5}  "
          f"{bgid:30}  {majic:5}  {sci:4}  {sci_str:30}  {qualif:10}")

print('=' * 175)
print()
print('NOTE qualification :')
print('  La colonne Qualif est vide car secteurAssign[cle].type est')
print('  stocke en KV Cloudflare (route /secteur-assignments/motte-')
print('  picquet du worker.js, accessible uniquement avec token Bearer).')
print('  Pour voir les qualifications deja posees, consulter le')
print('  dashboard UI (https://...) ou interroger directement le KV.')
