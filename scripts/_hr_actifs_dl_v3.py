#!/usr/bin/env python3
"""Liste hr-actifs DL enrichis SCI Prospector + KV qualifications.

Pour chaque hr-actif (vlog>0 && nb_log_bdnb>1) :
  - cle, vlog, bdnb
  - N SCI dans SCI Prospector (via parser cle adresse_bien)
  - sci_proprietaire light + sci_nom light
  - Qualif KV (ou non qualifie)
  - Suggestion :
    * 'mono' si 1 SCI unique proprietaire (et SCI active 'oui')
    * 'copro_non_immat' si plusieurs SCI ou pas de SCI

Tri par vlog desc.
"""
import json, sys, re
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
SCI   = ROOT / "data" / "dauphine-lacassagne-sci.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
kv = json.loads(KV.read_text(encoding="utf-8"))
assignments = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
sci_list = json.loads(SCI.read_text(encoding="utf-8")).get("sci") or []

ABBR_VOIE = {'AV':'AVENUE','AVE':'AVENUE','R':'RUE','BD':'BOULEVARD',
             'BLD':'BOULEVARD','BOUL':'BOULEVARD','PL':'PLACE','IMP':'IMPASSE',
             'CRS':'COURS','QU':'QUAI','SQ':'SQUARE','ALL':'ALLEE',
             'CHE':'CHEMIN','CH':'CHEMIN','MTE':'MONTEE','PAS':'PASSAGE',
             'TSSE':'TERRASSE','VLA':'VILLA','RTE':'ROUTE','GR':'GRANDE RUE'}
ART = {'DE','DES','DU','D','LA','LE','LES','L','AUX'}
ACC = str.maketrans('ÉÈÊËÀÂÔÎÏÇÛÙéèêëàâôîïçûù','EEEEAAOIICUUEEEEAAOIICUU')

def parse_cle(adresse_bien):
    if not adresse_bien: return None
    s = str(adresse_bien).upper().translate(ACC)
    s = re.sub(r'\s+\d{5}.*$', '', s)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    toks = s.split()
    if not toks: return None
    m = re.match(r'^(\d+)([A-Z]+)?$', toks[0])
    if not m: return None
    num = m.group(1)
    suff = m.group(2) or ''
    if suff in ('B','BIS','BS'): num += 'B'
    elif suff in ('T','TER'): num += 'T'
    toks = toks[1:]
    if not toks: return None
    typV = ABBR_VOIE.get(toks[0], toks[0])
    toks = toks[1:]
    while toks and toks[0] in ART: toks = toks[1:]
    return f"{num}|{typV}|{' '.join(toks)}"

# Index SCI par cle
sci_by_cle = defaultdict(list)
for s in sci_list:
    k = parse_cle(s.get('adresse_bien'))
    if k: sci_by_cle[k].append(s)

# hr-actifs
co_by_cle = {(c.get('cle_adresse') or ''): c for c in co}
def to_int(x):
    try: return int(x)
    except: return 0
hr = []
for a in ad:
    cle = a.get('cle') or ''
    if cle in co_by_cle: continue
    if a.get('numero_immatriculation'): continue
    if a.get('_fusion_auto'): continue
    if to_int(a.get('nb_ventes_logement')) <= 0: continue
    if to_int(a.get('nb_log_bdnb')) <= 1: continue
    hr.append(a)
hr.sort(key=lambda a: (-to_int(a.get('nb_ventes_logement')),
                       -to_int(a.get('nb_log_bdnb'))))

def qualif(cle):
    if cle in assignments: return assignments[cle].get('type','?')
    if cle in fusions: return 'fusion-src'
    if cle in fusions.values(): return 'fusion-tgt'
    return None

# Affichage
print("=" * 150)
print(f"  HR-ACTIFS UI Dauphine-Lacassagne avec SCI Prospector + KV  -  total={len(hr)}")
print("=" * 150)
print()

# Distribution
counts = Counter()
for a in hr:
    counts[qualif(a.get('cle') or '') or '(non qualifie)'] += 1
print(f"Distribution qualifications KV (sur ces hr-actifs) :")
for k,v in sorted(counts.items(), key=lambda x:-x[1]):
    print(f"  {k:24s} : {v}")
print()

# Tableau
print("-" * 150)
hdr = (f"{'#':2s} | {'cle':32s} | {'vlog':4s} | {'bdnb':4s} | {'N SCI':5s} | "
       f"{'light.sci_prop':14s} | {'light.sci_nom':22s} | {'KV':12s} | suggestion")
print(hdr)
print("-" * 150)

suggest_counts = Counter()
for i, a in enumerate(hr, 1):
    cle = a.get('cle') or ''
    vlog = to_int(a.get('nb_ventes_logement'))
    bdnb = to_int(a.get('nb_log_bdnb'))
    sci_pro = sci_by_cle.get(cle, [])
    n_sci = len(sci_pro)
    sci_prop_light = a.get('sci_proprietaire') or '-'
    sci_nom_light = (a.get('sci_nom') or '-')[:22]
    q = qualif(cle) or '(non qualif)'
    # Suggestion
    # Une SCI unique active = mono ; multi-SCI ou aucune SCI = copro_non_immat
    if n_sci == 1 and sci_pro[0].get('sci_active') == 'oui':
        sug = 'mono'
    elif n_sci >= 2:
        sug = 'copro_non_immat'
    elif n_sci == 0 and sci_prop_light == 'oui':
        # SCI light mais hors-Prospector (parser-miss)
        sug = 'mono?'  # ambigu : SCI declaree light mais parser n'a pas matche
    else:
        sug = 'copro_non_immat'
    suggest_counts[sug] += 1
    print(f"{i:2d} | {cle:32s} | {vlog:4d} | {bdnb:4d} | {n_sci:5d} | "
          f"{sci_prop_light:14s} | {sci_nom_light:22s} | {q:12s} | {sug}")
print("-" * 150)
print()

# Resume suggestions
print("Distribution suggestions :")
for k,v in sorted(suggest_counts.items(), key=lambda x:-x[1]):
    print(f"  {k:18s} : {v}")
print()

# Detail SCI multi pour les cas N>=2
print("=" * 150)
print(f"DETAIL multi-SCI (N>=2) - hr-actifs avec plusieurs SCI Prospector :")
print("=" * 150)
for i, a in enumerate(hr, 1):
    cle = a.get('cle') or ''
    sci_pro = sci_by_cle.get(cle, [])
    if len(sci_pro) < 2: continue
    print(f"\n  [{i}] {cle}  ({len(sci_pro)} SCI Prospector)")
    for s in sci_pro[:10]:
        actif = 'oui' if s.get('sci_active') == 'oui' else 'NON'
        print(f"      - {s.get('sci_nom','?'):30s}  SIREN={s.get('sci_siren','?'):10s}  "
              f"actif={actif}  biens_total={s.get('nb_biens_total')}")
    if len(sci_pro) > 10:
        print(f"      ... +{len(sci_pro)-10} autres")
