"""
Diagnostic v3 : DVF avec bons noms de champs (espaces).
"""
import json, os
io_kw = dict(encoding='utf-8')

ROOT  = r'C:\Users\Station 5\DPE-PROSPECTOR\data'
RAW   = os.path.join(ROOT, 'secteur_dauphine_lacassagne.json')

with open(RAW, **io_kw) as f:
    raw = json.load(f)
muts = raw.get('mutations_dvf', [])
print('mutations total:', len(muts))

def section(t):
    print('\n' + '=' * 78); print(t); print('=' * 78)

section("DVF mutations - No voie '50' ou '50B' et Voie contient ANTOINE")
hits = []
for m in muts:
    nov = str(m.get('No voie') or '').strip()
    btq = str(m.get('B/T/Q') or '').strip().upper()
    voie = str(m.get('Voie') or '').upper()
    adr = str(m.get('adresse_geocodee') or '').upper()
    # accept No voie == '50' (with or without B/T/Q) and ANTOINE in Voie or adresse
    if 'ANTOINE' in voie or 'ANTOINE' in adr:
        if nov == '50':
            hits.append(m)
print(f'hits: {len(hits)}')

# group by Section+No plan (parcelle) + B/T/Q + voie
from collections import defaultdict
g = defaultdict(list)
for m in hits:
    key = (
        m.get('B/T/Q') or '',
        m.get('Voie') or '',
        (m.get('Section') or '') + (m.get('No plan') or ''),
        m.get('Code commune') or '',
        m.get('Prefixe de section') or '',
    )
    g[key].append(m)

print(f'groupes (B/T/Q, Voie, Section+NoPlan, CodeCommune, Prefixe) : {len(g)}')
for key, lst in sorted(g.items(), key=lambda x: x[0]):
    btq, voie, parc, codecom, pref = key
    print(f"\n  GROUPE B/T/Q={btq!r} Voie={voie!r} Section+Plan={parc!r} Commune={codecom!r} Prefixe={pref!r}  | {len(lst)} mutations")
    # group by id mutation
    by_date = defaultdict(list)
    for m in lst:
        by_date[(m.get('Date mutation'), m.get('No disposition'))].append(m)
    for (date, ndisp), mlst in sorted(by_date.items()):
        m = mlst[0]
        sumval = m.get('Valeur fonciere')
        nlots = m.get('Nombre de lots')
        nat = m.get('Nature mutation')
        tloc = set(x.get('Type local') for x in mlst)
        surf = sum(int(float((x.get('Surface reelle bati') or '0').replace(',', '.')) or 0) for x in mlst)
        adr = m.get('adresse_geocodee')
        print(f"    {date} disp={ndisp} {nat} val={sumval} nb_lots={nlots} surf_bati_sum={surf} types={tloc}")
        print(f"       adr_geo={adr}")

section("Toutes parcelles DVF distinctes pour 50 ANTOINE")
parcs = sorted({(m.get('Prefixe de section') or '', m.get('Section') or '',
                 m.get('No plan') or '', m.get('B/T/Q') or '',
                 m.get('Voie') or '',
                 m.get('Code commune') or '')
                for m in hits})
for p in parcs:
    print(' ', p)

section("Recap hypothese : 2 batiments distincts ?")
# 50 ST ANTOINE -> bgid HQWX -> parcelles 69383000DY0023 + DY0110
# 50B ST ANTOINE -> bgid XQQB -> parcelle 69383000DY0022
# 50 ANTOINE CHARIAL -> bgid 7XNB -> parcelles 69383000DS0040 / DS0132 / DS0134
for m in hits[:30]:
    print(f"  No voie={m.get('No voie')} B/T/Q={m.get('B/T/Q')} Voie={m.get('Voie')} "
          f"| Section={m.get('Section')} No plan={m.get('No plan')} "
          f"Date={m.get('Date mutation')} Nat={m.get('Nature mutation')} "
          f"Val={m.get('Valeur fonciere')} Type={m.get('Type local')} "
          f"Adr_geo={m.get('adresse_geocodee')}")
