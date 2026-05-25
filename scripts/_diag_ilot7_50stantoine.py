"""
Diagnostic ilot 7 + 50 RUE ST ANTOINE (Dauphine-Lacassagne).
Read-only investigation: light, BDNB, DVF, KV.
"""
import json, os, sys
io_kw = dict(encoding='utf-8')

ROOT = r'C:\Users\Station 5\DPE-PROSPECTOR\data'
LIGHT = os.path.join(ROOT, 'secteur_dauphine_lacassagne_light.json')
RAW   = os.path.join(ROOT, 'secteur_dauphine_lacassagne.json')
BDNB  = os.path.join(ROOT, 'bdnb_dauphine_lacassagne.json')
DVF   = os.path.join(ROOT, 'dauphine-lacassagne.json')
KV    = os.path.join(ROOT, '_kv_assign_dl.json')

def load(p):
    if not os.path.exists(p):
        print('[MISS]', p); return None
    with open(p, **io_kw) as f:
        return json.load(f)

def section(t):
    print('\n' + '=' * 78); print(t); print('=' * 78)

light = load(LIGHT)
kv    = load(KV)
print('light adr:', len(light['adresses']))
print('KV type:', type(kv).__name__, 'len:', len(kv) if hasattr(kv, '__len__') else '?')
if isinstance(kv, dict):
    print('KV keys sample:', list(kv.keys())[:5])

# =================== 1) INVENTAIRE ILOT 7 ===================
section("1) INVENTAIRE ILOT 7 (light)")
adr_il7 = [a for a in light['adresses']
           if str(a.get('_ilot') or '').strip() == '7'
           or str(a.get('ilotEffectif') or '').strip() == '7']
print(f"Adresses _ilot/ilotEffectif=7 : {len(adr_il7)}")
print()
# headers
hdr = f"{'cle':<40} {'adresse':<55} {'log':>4} {'vlog':>5} {'immat':<14} {'tag_kv':<22}"
print(hdr); print('-' * len(hdr))
for a in sorted(adr_il7, key=lambda x: (x.get('adresse') or '')):
    cle = a.get('cle') or ''
    adr = (a.get('adresse') or '')[:55]
    nblog = a.get('nb_log_bdnb') or 0
    nbvlog = a.get('nb_ventes_logement') or 0
    immat = a.get('numero_immatriculation') or ''
    tag = ''
    if isinstance(kv, dict):
        e = kv.get(cle) or {}
        if isinstance(e, dict):
            tag = (e.get('type') or e.get('assign') or e.get('tag') or
                   e.get('classification') or str(e)[:22])
        else:
            tag = str(e)[:22]
    print(f"{cle[:40]:<40} {adr:<55} {nblog:>4} {nbvlog:>5} {immat:<14} {str(tag)[:22]:<22}")

# =================== 2) RECHERCHE 50 ST ANTOINE (light) ===================
section("2) RECHERCHE 50* RUE ST ANTOINE (light)")
hits = []
for a in light['adresses']:
    adr = (a.get('adresse') or '').upper()
    cle = (a.get('cle') or '').upper()
    if 'ANTOINE' in adr or 'ANTOINE' in cle:
        # numero
        num = ''
        # cle format: num|TYPE|VOIE
        parts = cle.split('|')
        if len(parts) >= 1:
            num = parts[0]
        if num.startswith('50'):
            hits.append((num, a))
        else:
            # secondary - any '50' as standalone token in adresse
            tokens = adr.replace(',', ' ').split()
            if any(t in ('50', '50B', '50T', '50BIS', '50TER') for t in tokens):
                hits.append((num or '?', a))
print(f"Hits ANTOINE + num start '50' : {len(hits)}")
for num, a in hits:
    print(f"  num={num} cle={a.get('cle')} adresse={a.get('adresse')} "
          f"ilot={a.get('_ilot')} immat={a.get('numero_immatriculation')} "
          f"bgid={a.get('batiment_groupe_id')} bdnb_match={a.get('_bdnb_match')}")

# All ANTOINE entries for context (regardless of num)
section("2bis) Toutes adresses *ANTOINE* light")
ant = [a for a in light['adresses']
       if 'ANTOINE' in (a.get('cle') or '').upper()
       or 'ANTOINE' in (a.get('adresse') or '').upper()]
print(f"Total ANTOINE entries : {len(ant)}")
# distinguish voies
voies = {}
for a in ant:
    cle = a.get('cle') or ''
    parts = cle.split('|')
    if len(parts) >= 3:
        voie_key = '|'.join(parts[1:])
    else:
        voie_key = (a.get('adresse') or '')[-40:]
    voies.setdefault(voie_key, []).append(a)
for vk, lst in sorted(voies.items()):
    print(f"  voie='{vk}' nb={len(lst)}")
    nums = sorted({(x.get('cle') or '').split('|')[0] for x in lst})
    print(f"    nums : {nums}")

# =================== 3) DVF 50 ANTOINE ===================
section("3) DVF mutations '50' + 'ANTOINE'")
dvf = load(DVF)
print('DVF type:', type(dvf).__name__)
muts_iter = None
if isinstance(dvf, list):
    muts_iter = dvf
elif isinstance(dvf, dict):
    for k in ('mutations', 'features', 'data', 'dvf', 'records'):
        v = dvf.get(k)
        if isinstance(v, list):
            muts_iter = v; print(f"DVF iter sur dvf[{k!r}] len={len(v)}"); break
    if muts_iter is None:
        print('DVF dict keys:', list(dvf.keys())[:30])
if muts_iter:
    print('DVF count:', len(muts_iter))
    if muts_iter:
        s = muts_iter[0]
        if isinstance(s, dict):
            print('Sample keys:', list(s.keys())[:30])

found = []
def field_of(m, names):
    for n in names:
        if isinstance(m, dict) and n in m and m[n] not in (None, ''):
            return m[n]
    return None

if muts_iter:
    for m in muts_iter:
        if not isinstance(m, dict):
            continue
        adr = (str(field_of(m, ['adresse', 'adresse_complete',
                                 'voie', 'adr', 'l_adresse']) or '')).upper()
        num = str(field_of(m, ['num_voie', 'numero_voie',
                                'no_voie', 'no_plaque']) or '')
        nom_voie = str(field_of(m, ['nom_voie', 'type_voie',
                                     'libelle_voie']) or '').upper()
        merge = f"{num} {nom_voie} | {adr}"
        if 'ANTOINE' in merge.upper() and ('50' in num.strip()
                                            or ' 50 ' in (' '+adr+' ')
                                            or adr.strip().startswith('50 ')
                                            or '50B' in num.upper()
                                            or '50T' in num.upper()):
            found.append(m)

print(f"\nMatches DVF 50 + ANTOINE: {len(found)}")
for m in found:
    date = field_of(m, ['date_mutation', 'date', 'datemut'])
    typ  = field_of(m, ['nature_mutation', 'type_mutation', 'nature'])
    val  = field_of(m, ['valeur_fonciere', 'montant', 'valeur'])
    surf = field_of(m, ['surface_reelle_bati', 'surface_bati',
                         'surface', 'sbati'])
    idm  = field_of(m, ['id_mutation', 'idmut', 'id'])
    cad  = field_of(m, ['numero_cadastre', 'parcelle', 'id_parcelle',
                         'reference_cadastrale', 'ref_cadastre'])
    adr  = field_of(m, ['adresse', 'adresse_complete'])
    num  = field_of(m, ['num_voie', 'numero_voie', 'no_voie'])
    nv   = field_of(m, ['nom_voie', 'libelle_voie'])
    print(f"  {date} {typ} val={val} surf={surf} id={idm}")
    print(f"     num={num} voie={nv} adr={adr} parc={cad}")

if found:
    parc = sorted({field_of(m, ['numero_cadastre','parcelle','id_parcelle',
                                'reference_cadastrale','ref_cadastre'])
                   for m in found})
    print(f"\nParcelles distinctes : {parc}")

# =================== 4) BDNB ===================
section("4) BDNB 50 Saint Antoine / Antoine Charial")
bdnb = load(BDNB)
print('BDNB type:', type(bdnb).__name__)
bd_iter = None
if isinstance(bdnb, list):
    bd_iter = bdnb
elif isinstance(bdnb, dict):
    for k in ('batiments', 'features', 'data', 'bdnb',
              'batiment_groupe', 'records'):
        v = bdnb.get(k)
        if isinstance(v, list):
            bd_iter = v; print(f"BDNB iter sur bdnb[{k!r}] len={len(v)}"); break
    if bd_iter is None:
        print('BDNB dict keys (top):', list(bdnb.keys())[:20])
        # peut-etre map bgid -> obj
        sample_keys = list(bdnb.keys())[:3]
        for k in sample_keys:
            v = bdnb[k]
            if isinstance(v, dict):
                print(f'  sample {k!r} keys:', list(v.keys())[:20])
                break
        bd_iter = [v for v in bdnb.values()
                   if isinstance(v, dict)]
        print(f'  fallback bgid->dict iter len={len(bd_iter)}')

print('BDNB count:', len(bd_iter) if bd_iter else 0)

def has_token(s, *tokens):
    s = (s or '').upper()
    return all(t.upper() in s for t in tokens)

matches_sa, matches_ac = [], []
if bd_iter:
    if bd_iter and isinstance(bd_iter[0], dict):
        print('Sample BDNB keys:', list(bd_iter[0].keys())[:30])
    for b in bd_iter:
        if not isinstance(b, dict): continue
        # Try common BAN fields
        adr_fields = []
        for k, v in b.items():
            kl = k.lower()
            if any(x in kl for x in ('adresse','libelle_adr','l_libelle','ban','voie')):
                if isinstance(v, str):
                    adr_fields.append(v)
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, str): adr_fields.append(x)
        blob = ' | '.join(adr_fields).upper()
        if ('50' in blob) and ('SAINT ANTOINE' in blob or 'ST ANTOINE' in blob or 'SAINT-ANTOINE' in blob):
            matches_sa.append((b, blob))
        if ('50' in blob) and ('ANTOINE CHARIAL' in blob or 'A CHARIAL' in blob):
            matches_ac.append((b, blob))

def show(label, lst, lim=20):
    print(f"\n{label} : {len(lst)} matches")
    for b, blob in lst[:lim]:
        bgid = b.get('batiment_groupe_id') or b.get('bgid') or b.get('id') or '?'
        nblog = (b.get('nb_log') or b.get('nb_logements')
                 or b.get('nb_log_total') or b.get('nb_log_rnc') or '?')
        parc = (b.get('parcelle_id') or b.get('parcelle')
                or b.get('cadastre') or b.get('reference_cadastrale') or '?')
        print(f"  bgid={bgid} nb_log={nblog} parc={parc}")
        print(f"     blob={blob[:200]}")

show("50 SAINT ANTOINE", matches_sa)
show("50 ANTOINE CHARIAL", matches_ac)

# =================== 5) HYPOTHESES ===================
section("5) HYPOTHESES")
# 5a label fusion
print("[5a] Cherche '_fusion_auto_label' contenant 'ANTOINE' + '50'")
fused = []
for a in light['adresses']:
    lbl = (a.get('_fusion_auto_label') or '')
    if 'ANTOINE' in lbl.upper() and '50' in lbl:
        fused.append(a)
print(f"  hits : {len(fused)}")
for a in fused[:10]:
    print(f"  cle={a.get('cle')} adresse={a.get('adresse')} label={a.get('_fusion_auto_label')}")

# 5b sources fusion
print("\n[5b] Cherche '_fusion_auto_sources' contenant cle '50|...|ANTOINE...'")
src_hits = []
for a in light['adresses']:
    srcs = a.get('_fusion_auto_sources') or []
    if not isinstance(srcs, list): continue
    for s in srcs:
        if isinstance(s, str) and 'ANTOINE' in s.upper() and s.startswith('50'):
            src_hits.append((a, s)); break
print(f"  hits : {len(src_hits)}")
for a, s in src_hits[:10]:
    print(f"  cle={a.get('cle')} fused_src={s} label={a.get('_fusion_auto_label')}")

# 5c parcelle cache : 50 ANTOINE
print("\n[5c] Parcelle cache _bgid_parcelle_dl.json -> bgid des matches SA/AC")
try:
    pc = load(os.path.join(ROOT, '_bgid_parcelle_dl.json'))
    print('  parcelle cache keys count:', len(pc) if isinstance(pc, dict) else '?')
    for b, _ in matches_sa + matches_ac:
        bgid = b.get('batiment_groupe_id') or b.get('bgid') or b.get('id')
        if bgid and isinstance(pc, dict):
            print(f"  bgid={bgid} -> {pc.get(bgid)}")
except Exception as e:
    print('  err:', e)

print("\n[END]")
