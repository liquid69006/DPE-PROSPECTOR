"""Calcule nb_log_marchand pour chaque adresse light DL.

Estimateur ponderation par pct (v2 - mode unifie) :
  social_pct = nb_lots_sociaux_brut / total_lots_majic
  nb_lots_sociaux_estimes = round(social_pct * nb_log_bdnb)
  nb_log_marchand = max(0, nb_log_bdnb - nb_lots_sociaux_estimes)

Hypothese : la repartition social/non-social observee dans le sous-
ensemble MAJIC (personnes morales) est representative de la
repartition globale du bati. Plus juste que brut/scale quand
ratio<1 (MAJIC sous-couvre, les PP sont implicites mais on suppose
la meme proportion social/marchand).

Ecrit dans le light JSON UNIQUEMENT pour adresses ayant >=1 lot
social MAJIC.
"""
import json

SOCIAL_KW = ['HLM', 'OPAC', 'SACVL', 'ALLIADE', "IN'LI", 'INLI', 'ICF ',
             'GRAND LYON HABITAT', 'GRANDLYON HABITAT', 'EST METROPOLE',
             'RHONE SAONE HABITAT', 'ALPES ISERE HABITAT',
             'ABC HLM', 'BATIGERE', '3F', 'CDC HABITAT', 'IMMOBILIERE 3F',
             'METROPOLE HABITAT', 'ALLIANCE HABITAT', 'HABITAT ET HUMANISME',
             'HABITAT HUMANISME', 'ENT.HUMANISER', 'ETROITS', 'SOIN',
             'OPH ', 'OFFICE PUBLIC', 'IMMOBILIERE RHONE ALPES',
             'COMMUNAUTE URBAINE DE LYON', 'HOSPICES CIVILS', 'VILLE DE LYON',
             'METROPOLE DE LYON', 'ASSOCIATION DE L HOTEL SOCIAL',
             'DYNACITE', 'FONCIERE D HABITAT ET HUMANISME']

def is_social(d):
    d = (d or '').upper()
    return any(k in d for k in SOCIAL_KW)

with open('data/secteur_dauphine_lacassagne_light.json', 'r', encoding='utf-8') as f:
    light = json.load(f)
with open('data/_enrich_majic_dl_full.json', 'r', encoding='utf-8') as f:
    em = json.load(f)
em_by_cle = {r['cle']: r for r in em.get('results', [])}

n_updated = 0
total_marchand = 0
total_bdnb = 0
samples = []
for adresse in light['adresses']:
    cle = adresse.get('cle')
    em_r = em_by_cle.get(cle)
    if not em_r: continue
    nb_log_bdnb = adresse.get('nb_log_bdnb') or 0
    if nb_log_bdnb <= 0: continue
    sirens = em_r.get('sirens') or []
    nb_lots_sociaux_brut = 0
    social_sirens = []
    for s in sirens:
        den = s.get('denomination') or ''
        if is_social(den):
            lots = s.get('lots') or 0
            nb_lots_sociaux_brut += lots
            social_sirens.append((den, lots))
    if nb_lots_sociaux_brut == 0: continue

    majic_lots = em_r.get('majic_lots') or 0
    ratio = em_r.get('ratio_pm_bdnb') or 0
    # Estimateur ponderation pct (toujours, quel que soit ratio) :
    # on projette le ratio social/total_MAJIC sur nb_log_bdnb.
    if majic_lots > 0:
        social_pct = nb_lots_sociaux_brut / majic_lots
        nb_lots_sociaux_estimes = round(social_pct * nb_log_bdnb)
    else:
        nb_lots_sociaux_estimes = 0
    nb_lots_sociaux_estimes = min(nb_lots_sociaux_estimes, nb_log_bdnb)
    nb_log_marchand = max(0, nb_log_bdnb - nb_lots_sociaux_estimes)

    adresse['nb_lots_sociaux'] = nb_lots_sociaux_estimes
    adresse['nb_lots_sociaux_brut'] = nb_lots_sociaux_brut
    adresse['nb_log_marchand'] = nb_log_marchand
    n_updated += 1
    total_marchand += nb_log_marchand
    total_bdnb += nb_log_bdnb
    if len(samples) < 15:
        samples.append((cle, nb_log_bdnb, nb_lots_sociaux_estimes,
                        nb_log_marchand, ratio, social_sirens[:2]))

with open('data/secteur_dauphine_lacassagne_light.json', 'w', encoding='utf-8') as f:
    json.dump(light, f, ensure_ascii=False, indent=2)

print(f'=== nb_log_marchand calcule : {n_updated} adresses ===')
print(f'  Total marchand : {total_marchand}')
print(f'  Total BDNB     : {total_bdnb}')
print(f'  Diff (social)  : {total_bdnb - total_marchand}\n')
print('Top samples :')
for cle, nbdnb, nsoc, nmar, ratio, sir in sorted(samples, key=lambda x: -x[1]):
    sir_str = ', '.join(f'{d[:25]}({l})' for d, l in sir)
    print(f'  {cle:<35} bdnb={nbdnb:>3} sociaux={nsoc:>3} marchand={nmar:>3} ratio={ratio:.2f}  {sir_str}')
