"""
Diagnostic v2 : DVF (raw secteur.mutations_dvf) + verifications complementaires.
"""
import json, os, sys
io_kw = dict(encoding='utf-8')

ROOT = r'C:\Users\Station 5\DPE-PROSPECTOR\data'
RAW   = os.path.join(ROOT, 'secteur_dauphine_lacassagne.json')
LIGHT = os.path.join(ROOT, 'secteur_dauphine_lacassagne_light.json')

def load(p):
    with open(p, **io_kw) as f:
        return json.load(f)

def section(t):
    print('\n' + '=' * 78); print(t); print('=' * 78)

raw   = load(RAW)
light = load(LIGHT)
muts  = raw.get('mutations_dvf', [])
print('mutations_dvf count:', len(muts))
if muts:
    print('sample mutation keys:', list(muts[0].keys())[:40])
    print('sample mutation[0]:')
    import pprint
    pprint.pprint(muts[0])

section("3) DVF 50 + ANTOINE")
def f(m, names):
    for n in names:
        if n in m and m[n] not in (None, ''):
            return m[n]
    return None

hits = []
for m in muts:
    # try fields
    adr  = str(f(m, ['adresse','adresse_complete','l_adresse']) or '').upper()
    num  = str(f(m, ['num_voie','numero_voie','no_voie','no_plaque']) or '')
    nv   = str(f(m, ['nom_voie','libelle_voie','type_voie']) or '').upper()
    cle  = str(f(m, ['cle','cle_adresse']) or '').upper()
    # union all text fields starting with a/v/n
    big = ' '.join(str(v) for k, v in m.items() if isinstance(v, (str, int, float))).upper()
    if 'ANTOINE' in big and ('50' in num.strip()
                              or '50B' in num.upper()
                              or '50T' in num.upper()
                              or ' 50 ' in (' '+adr+' ')
                              or adr.strip().startswith('50 ')
                              or cle.startswith('50|')
                              or cle.startswith('50B|')):
        hits.append(m)
print(f"Matches: {len(hits)}")
for m in hits:
    print('-' * 78)
    for k in ('date_mutation','datemut','date','nature_mutation','nature',
              'valeur_fonciere','valeur','montant',
              'surface_reelle_bati','surface_bati','surface',
              'id_mutation','idmut',
              'num_voie','nom_voie','adresse','adresse_complete','cle','cle_adresse',
              'numero_cadastre','parcelle','id_parcelle','reference_cadastrale',
              'ref_cadastre','batiment_groupe_id','bgid'):
        if k in m:
            print(f"  {k}: {m[k]}")

# parcelles distinctes
if hits:
    parcs = set()
    for m in hits:
        p = f(m, ['numero_cadastre','parcelle','id_parcelle',
                  'reference_cadastrale','ref_cadastre'])
        if p: parcs.add(p)
    print(f"\nParcelles distinctes : {sorted(parcs)}")

# =================== Confirmation hypotheses ===================
section("CONFIRMATION HYPOTHESES")

# Cherche 50 ST ANTOINE dans light, voir ilot exact
for a in light['adresses']:
    if (a.get('cle') or '').upper() in ('50|RUE|ST ANTOINE','50B|RUE|ST ANTOINE',
                                         '50|RUE|SAINT ANTOINE','50B|RUE|SAINT ANTOINE',
                                         '50|RUE|ANTOINE CHARIAL'):
        print('CLE:', a.get('cle'))
        for k in ('adresse','_ilot','ilotEffectif','batiment_groupe_id','_bdnb_match',
                 'numero_immatriculation','nb_lots_habitation','syndic',
                 'nb_log_bdnb','annee_construction','classe_dpe',
                 'nb_ventes_total','nb_ventes_logement',
                 '_fusion_auto_label','_fusion_auto_sources','_correctif_appliques',
                 'dans_majic','sci_proprietaire','sci_nom','sci_siren'):
            v = a.get(k)
            if v not in (None, '', [], {}): print(f"  {k}: {v}")
        print()

# Verifier copro RNC dans light.coproprietes
section("Copro RNC dans light.coproprietes")
copros = light.get('coproprietes', [])
print('coproprietes count:', len(copros))
if copros:
    print('sample copro keys:', list(copros[0].keys())[:30])
# match par immat
for cp in copros:
    immat = cp.get('numero_immatriculation') or cp.get('immat') or ''
    if immat in ('AD9391244','AE9778358','AA2266625'):
        print('\nIMMAT', immat)
        for k, v in cp.items():
            if v not in (None, '', [], {}):
                print(f"  {k}: {v}")

# verifier les autres bgids 50 ST-ANTOINE absents du light
section("Bgids 50 ST-ANTOINE referenced ?")
for bgid in ('bdnb-bg-9H8U-9VAU-EN8T','bdnb-bg-NBV8-YC65-QXEZ'):
    found = False
    for a in light['adresses']:
        if a.get('batiment_groupe_id') == bgid:
            print(f"  bgid {bgid} present dans light : cle={a.get('cle')} adr={a.get('adresse')}")
            found = True
    if not found:
        print(f"  bgid {bgid} ABSENT du light")

# Verifier _fusion_auto_sources global pour bgid HQWX (50 ST ANTOINE) et XQQB (50B)
section("Fusion sources contenant 50 ST ANTOINE / 50B")
for a in light['adresses']:
    srcs = a.get('_fusion_auto_sources') or []
    if not isinstance(srcs, list): continue
    for s in srcs:
        sU = (s or '').upper()
        if (sU.startswith('50|') or sU.startswith('50B|')) and ('ST ANTOINE' in sU or 'SAINT ANTOINE' in sU):
            print(f"  cle anchor: {a.get('cle')} contains source {s}")
            break

print("\n[END]")
