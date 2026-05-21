"""
AUDIT lecture-seule des 11 cas SAFE bgid-orphelin avant decision
finale. Pour chaque paire orphelin->ancre :
  - distance entre numeros de rue
  - meme voie OU voies differentes
  - parcelles cadastrales BDNB des 2 bgids (devraient etre identiques
    par definition du critere - sinon BDNB agrege 2 batis distincts)
  - l_libelle_adr BDNB du bgid (verification que les 2 facades sont
    listees dans le pivot - confirmation physique meme bati)
  - bonus : annee_construction comparable

Aucune modification.
"""
import json
import urllib.request
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / 'data' / 'secteur_motte_picquet_light.json').open(
        'r', encoding='utf-8') as f:
    light = json.load(f)

# Les 11 cas du dry-run safe
CASES = [
    ("1|RUE|COMMERCE", "4|RUE|COMMERCE", "AB4253712", "ISAMBERT ETUDE DU THEA"),
    ("10|RUE|CLOUET", "11|RUE|CLOUET", "AC3292430", "DM GESTION"),
    ("14|RUE|BOUCHUT", "15|RUE|BOUCHUT", "AD4294989", "I2M"),
    ("17|RUE|AVRE", "16|RUE|AVRE", "AB9945825", "CABINET GPIMO"),
    ("17|RUE|DESAIX", "16|RUE|DESAIX", "AI8302572", "FURGE MULHAUSER-MSG"),
    ("38|RUE|LETELLIER", "39|RUE|LETELLIER", "AA5186549", "INGENCIA"),
    ("4|RUE|PRESLES", "7|RUE|PRESLES", "AB7861529", "GERARD SAFAR SAS"),
    ("51|AVENUE|MOTTE PICQUET", "50|AVENUE|MOTTE PICQUET", "AC1472232", "TIFFENCOGE"),
    ("58|BOULEVARD|GRENELLE", "69|BOULEVARD|GRENELLE", "AC0256198", "DELON SYNDIC DE COPROP"),
    ("6|AVENUE|CHAMPAUBERT", "78|AVENUE|SUFFREN", "AA0529289", "ATRIUM GESTION"),
    ("8|RUE|CLOUET", "9|RUE|CLOUET", "AA3471208", "JFT GESTION"),
]

by_cle = {a['cle']: a for a in light['adresses']}

# 1) Cache bgid -> {parcelle, l_libelle_adr, annee, nb_log, nb_log_rnc, usage}
bgid_cache = {}
def fetch_bgid(bg):
    if bg in bgid_cache:
        return bgid_cache[bg]
    out = {'parcelle': None, 'libelles': [], 'annee': None,
           'nb_log': None, 'nb_log_rnc': None, 'usage': None}
    try:
        url = f'https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet?batiment_groupe_id=eq.{bg}'
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept':'application/json'}), timeout=30) as r:
            rows = json.loads(r.read())
        if rows:
            row = rows[0]
            out['libelles'] = row.get('l_libelle_adr') or []
            out['annee'] = row.get('annee_construction')
            out['nb_log'] = row.get('nb_log')
            out['nb_log_rnc'] = row.get('nb_log_rnc')
            out['usage'] = row.get('usage_principal_bdnb_open')
        url2 = f'https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}'
        with urllib.request.urlopen(urllib.request.Request(url2, headers={'Accept':'application/json'}), timeout=20) as r:
            rows2 = json.loads(r.read())
        out['parcelle'] = [r.get('parcelle_id') for r in rows2]
    except Exception as e:
        out['err'] = str(e)
    bgid_cache[bg] = out
    return out


def num_voie(cle):
    """Extract numero from cle '6|AVENUE|CHAMPAUBERT' -> 6 (int) ou None."""
    parts = (cle or '').split('|')
    if not parts: return None
    n = parts[0]
    # Strip suffix lettres (6B, 12T, etc.)
    import re
    m = re.match(r'^(\d+)', n)
    return int(m.group(1)) if m else None


def voie_only(cle):
    parts = (cle or '').split('|')
    if len(parts) >= 3:
        return f'{parts[1]} {parts[2]}'
    return cle


def in_libelle(cle, libelles):
    """Verifie si la cle (ex '6|AVENUE|CHAMPAUBERT') correspond a une
    facade BAN du pivot l_libelle_adr (ex '6 Avenue De Champaubert')."""
    parts = (cle or '').split('|')
    if len(parts) < 3: return False
    no = parts[0]
    voie_norm = parts[2].lower().replace(' ', '')
    for lib in libelles:
        l_low = lib.lower().replace(' ', '').replace('-', '')
        # check no debute la ligne + voie_norm presente
        if l_low.startswith(no + ' ') or l_low.startswith(no.lower()):
            if voie_norm in l_low or voie_norm.replace('e', '').replace('é','e') in l_low:
                return True
        # variante : 'X rueXxx' format compact
        if l_low.startswith(no) and voie_norm[:6] in l_low:
            return True
    return False


print(f'Audit des {len(CASES)} cas SAFE bgid-orphelin')
print()

for i, (orph_cle, anc_cle, immat, syndic) in enumerate(CASES, 1):
    orph = by_cle.get(orph_cle, {})
    anc = by_cle.get(anc_cle, {})
    bg_o = orph.get('batiment_groupe_id')
    bg_a = anc.get('batiment_groupe_id')

    no_o = num_voie(orph_cle)
    no_a = num_voie(anc_cle)
    voie_o = voie_only(orph_cle)
    voie_a = voie_only(anc_cle)

    same_voie = (voie_o == voie_a)
    dist = abs(no_o - no_a) if (no_o is not None and no_a is not None and same_voie) else None

    bg_match = bg_o == bg_a
    info_o = fetch_bgid(bg_o) if bg_o else {}
    info_a = fetch_bgid(bg_a) if (bg_a and bg_a != bg_o) else info_o

    in_lib_o = in_libelle(orph_cle, info_o.get('libelles', []))
    in_lib_a = in_libelle(anc_cle, info_a.get('libelles', []))

    parc_o = info_o.get('parcelle') or []
    parc_a = info_a.get('parcelle') or []
    same_parc = (set(parc_o) & set(parc_a)) if (parc_o and parc_a) else set()

    print('=' * 100)
    print(f'CAS {i:>2} : {orph_cle:32s} -> {anc_cle:32s}  (immat {immat}, syndic {syndic[:24]})')
    print('-' * 100)
    print(f'  Voie orph vs ancre   : {voie_o!r} vs {voie_a!r}  '
          f'{"MEME VOIE" if same_voie else "VOIES DIFFERENTES"}')
    if dist is not None:
        print(f'  Distance numeros     : {dist} (orph {no_o} vs ancre {no_a})')
    print(f'  Bgid orph            : {bg_o}')
    print(f'  Bgid ancre           : {bg_a}  '
          f'{"(MEME bgid)" if bg_match else "(BGID DIFFERENT - critere viole !)"}')
    print(f'  Parcelle orph        : {parc_o}')
    print(f'  Parcelle ancre       : {parc_a}  '
          f'{"(MEME parcelle)" if same_parc else "(parcelles distinctes - inhabituel)"}')
    print(f'  l_libelle_adr bgid orph  ({len(info_o.get("libelles", []))} facades) :')
    for lib in info_o.get('libelles', [])[:10]:
        marker = ''
        if in_libelle(orph_cle, [lib]): marker += ' [ORPH]'
        if in_libelle(anc_cle, [lib]): marker += ' [ANC]'
        print(f'      - {lib}{marker}')
    if len(info_o.get('libelles', [])) > 10:
        print(f'      ... ({len(info_o["libelles"])-10} autres)')
    print(f'  Orph dans l_libelle  : {"OUI" if in_lib_o else "NON"}')
    print(f'  Ancre dans l_libelle : {"OUI" if in_lib_a else "NON"}')
    print(f'  Annee bati BDNB      : {info_o.get("annee")}  '
          f'(nb_log={info_o.get("nb_log")}, nb_log_rnc={info_o.get("nb_log_rnc")}, '
          f'usage={info_o.get("usage")!r})')
    # Verdict
    if not bg_match:
        verdict = 'INVALIDE - bgid different (critere viole)'
    elif in_lib_o and in_lib_a:
        verdict = 'CONFIRME meme bati BDNB (les 2 facades dans pivot)'
    elif in_lib_a and not in_lib_o:
        verdict = f'PARTIEL - ancre OK mais orph absent du pivot (matching gps/num_voie)'
    elif in_lib_o and not in_lib_a:
        verdict = 'PARTIEL - orph dans pivot mais ancre absente (inhabituel)'
    else:
        verdict = 'A INVESTIGUER - aucune des 2 facades dans pivot BDNB'
    print(f'  VERDICT              : {verdict}')

print()
print('=' * 100)
print('Synthese des verdicts :')
