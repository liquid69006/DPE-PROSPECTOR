#!/usr/bin/env python3
"""Diff sandbox v2 vs light actuel DL - mesure du fix indice_de_repetition.

Compare data/secteur_dl_light_v2.json (regen apres patch) vs
data/secteur_dauphine_lacassagne_light.json (current commited).

Sortie :
  - Nouvelles cles avec suffixe B/T/Q (cible Pattern A)
  - Nouvelles cles sans suffixe (autres Patterns B/D)
  - Cles perdues (correctifs manuels qui seraient ecrases)
  - Bilan numerique
"""
import json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
CURRENT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
SANDBOX = ROOT / "data" / "secteur_dl_light_v2.json"

print("=" * 90)
print("DIFF SANDBOX v2 vs LIGHT actuel DL")
print("=" * 90)

doc_c = json.loads(CURRENT.read_text(encoding="utf-8"))
doc_s = json.loads(SANDBOX.read_text(encoding="utf-8"))
ad_c = doc_c["adresses"]
ad_s = doc_s["adresses"]
co_c = doc_c["coproprietes"]
co_s = doc_s["coproprietes"]
cles_c = {a.get("cle") for a in ad_c if a.get("cle")}
cles_s = {a.get("cle") for a in ad_s if a.get("cle")}

print()
print(f"  Light current : {len(ad_c)} adresses, {len(co_c)} copros, {len(cles_c)} cles uniques")
print(f"  Sandbox v2    : {len(ad_s)} adresses, {len(co_s)} copros, {len(cles_s)} cles uniques")

new_cles = cles_s - cles_c
lost_cles = cles_c - cles_s
common = cles_c & cles_s
print()
print(f"  Communs       : {len(common)}")
print(f"  Nouvelles (v2 only)   : {len(new_cles)}")
print(f"  Perdues  (current only) : {len(lost_cles)}")

# --- Categoriser les nouvelles ---
NEW_SUF = []
NEW_NOSUF = []
SUFFIX_RX = re.compile(r"^(\d+)([A-Z])\|")
for cle in sorted(new_cles):
    m = SUFFIX_RX.match(cle)
    if m: NEW_SUF.append(cle)
    else: NEW_NOSUF.append(cle)

print()
print(f"=== NOUVELLES CLES (v2) ===")
print(f"  Avec suffixe B/T/Q/A/C/D (cible Pattern A) : {len(NEW_SUF)}")
print(f"  Sans suffixe (Pattern B/D)                  : {len(NEW_NOSUF)}")

# Index sandbox par cle pour stats
by_cle_s = {a.get("cle"): a for a in ad_s}

# Affichage cles avec suffixe (top 30 par nb_log_bdnb)
def to_int(x):
    try: return int(x)
    except: return 0

print()
print(f"=== NOUVELLES CLES AVEC SUFFIXE (top 30 par nb_log_bdnb desc) ===")
nuf_sorted = sorted(NEW_SUF, key=lambda c: -to_int(by_cle_s.get(c, {}).get("nb_log_bdnb") or 0))
for cle in nuf_sorted[:30]:
    a = by_cle_s.get(cle, {})
    print(f"  {cle:36s}  bdnb={a.get('nb_log_bdnb')}  bgid=...{(a.get('batiment_groupe_id') or '-')[-9:]}  immat={a.get('numero_immatriculation') or '-'}")
if len(nuf_sorted) > 30:
    print(f"  ... (+{len(nuf_sorted)-30} autres)")

# Distribution suffixes
from collections import Counter
suf_cnt = Counter()
for cle in NEW_SUF:
    m = SUFFIX_RX.match(cle)
    if m: suf_cnt[m.group(2)] += 1
print()
print(f"  Distribution suffixes : {dict(suf_cnt)}")

# Echantillon sans suffixe (top 20)
print()
print(f"=== NOUVELLES CLES SANS SUFFIXE (top 20 par nb_log_bdnb desc) ===")
nnsuf_sorted = sorted(NEW_NOSUF, key=lambda c: -to_int(by_cle_s.get(c, {}).get("nb_log_bdnb") or 0))
for cle in nnsuf_sorted[:20]:
    a = by_cle_s.get(cle, {})
    print(f"  {cle:36s}  bdnb={a.get('nb_log_bdnb')}  bgid=...{(a.get('batiment_groupe_id') or '-')[-9:]}")
if len(nnsuf_sorted) > 20:
    print(f"  ... (+{len(nnsuf_sorted)-20} autres)")

# --- Cles perdues (correctifs manuels effaces) ---
by_cle_c = {a.get("cle"): a for a in ad_c}

# Distinguer perdues "vraies" (cle absente sandbox) vs "perdues parce que pivot FA different"
# Categories :
#   A. perdue avec _injection ou markers correctifs -> ALERTE
#   B. perdue qui etait FA dans current (peut-etre re-cree differemment)
#   C. perdue sans markers (potentiel desaccord BAN ou MAJIC)
LOST_INJECT = []
LOST_FA = []
LOST_ANCRE = []
for cle in sorted(lost_cles):
    a = by_cle_c.get(cle, {})
    if any(k.startswith(("_injection","_correctif","_fix")) for k in a.keys()):
        LOST_INJECT.append(cle)
    elif a.get("_fusion_auto"):
        LOST_FA.append(cle)
    else:
        LOST_ANCRE.append(cle)

print()
print(f"=== CLES PERDUES (current only - non regenerees par make_light v2) ===")
print(f"  Avec marker _injection/_correctif (CORRECTIFS MANUELS A PRESERVER) : {len(LOST_INJECT)}")
for cle in LOST_INJECT:
    a = by_cle_c.get(cle, {})
    print(f"    ALERTE - {cle}")
print()
print(f"  FA (_fusion_auto=True dans current) - peuvent etre regenerees differemment : {len(LOST_FA)}")
for cle in LOST_FA[:15]:
    a = by_cle_c.get(cle, {})
    print(f"    {cle:36s}  bgid=...{(a.get('batiment_groupe_id') or '-')[-9:]}  cible={a.get('_fusion_cible')!r}")
if len(LOST_FA) > 15: print(f"    ... (+{len(LOST_FA)-15} autres)")
print()
print(f"  Ancres (non-FA dans current) - investigation requise : {len(LOST_ANCRE)}")
for cle in LOST_ANCRE[:15]:
    a = by_cle_c.get(cle, {})
    print(f"    {cle:36s}  bdnb={a.get('nb_log_bdnb')}  vlog={a.get('nb_ventes_logement')}  immat={a.get('numero_immatriculation')!r}")
if len(LOST_ANCRE) > 15: print(f"    ... (+{len(LOST_ANCRE)-15} autres)")

# --- Cles communes : diff sur attributs critiques (bgid, FA cible, label) ---
diffs_bgid = []
diffs_fa = []
diffs_immat = []
for cle in common:
    a_c = by_cle_c.get(cle, {})
    a_s = by_cle_s.get(cle, {})
    if a_c.get("batiment_groupe_id") != a_s.get("batiment_groupe_id"):
        diffs_bgid.append((cle, a_c.get("batiment_groupe_id"), a_s.get("batiment_groupe_id")))
    if (a_c.get("_fusion_cible") or "") != (a_s.get("_fusion_cible") or ""):
        diffs_fa.append((cle, a_c.get("_fusion_cible"), a_s.get("_fusion_cible")))
    if (a_c.get("numero_immatriculation") or "") != (a_s.get("numero_immatriculation") or ""):
        diffs_immat.append((cle, a_c.get("numero_immatriculation"), a_s.get("numero_immatriculation")))

print()
print(f"=== CLES COMMUNES AVEC ATTRIBUTS DIFFERENTS ===")
print(f"  bgid diverge        : {len(diffs_bgid)}")
print(f"  FA cible diverge    : {len(diffs_fa)}")
print(f"  immat diverge       : {len(diffs_immat)}")

# Aperçu top 10 diffs bgid (potentiellement les RE-POINT manuels effacés)
if diffs_bgid:
    print()
    print(f"  Top 10 diff bgid (potentiels RE-POINT manuels effaces) :")
    for cle, b_c, b_s in diffs_bgid[:10]:
        print(f"    {cle:36s}  current=...{(b_c or '-')[-9:]}  ->  v2=...{(b_s or '-')[-9:]}")
    if len(diffs_bgid) > 10: print(f"    ... (+{len(diffs_bgid)-10} autres)")

# Copros : injectees absentes du sandbox ?
co_c_immat = {c.get("numero_immatriculation") for c in co_c if c.get("numero_immatriculation")}
co_s_immat = {c.get("numero_immatriculation") for c in co_s if c.get("numero_immatriculation")}
lost_co = co_c_immat - co_s_immat
print()
print(f"=== COPROS PERDUES (immat current only) : {len(lost_co)} ===")
co_c_by_immat = {c.get("numero_immatriculation"): c for c in co_c if c.get("numero_immatriculation")}
for im in sorted(lost_co)[:15]:
    c = co_c_by_immat.get(im, {})
    correct = ""
    for k in c.keys():
        if k.startswith(("_injection","_correctif","_fix")):
            correct = f"  [{k}={c[k]!r}]"; break
    print(f"  {im}  '{c.get('nom_copropriete','')[:35]}'  cle={c.get('cle_adresse','?')}{correct}")
if len(lost_co) > 15: print(f"  ... (+{len(lost_co)-15} autres)")

# --- Bilan final ---
print()
print("=" * 90)
print("BILAN FINAL DIFF DL")
print("=" * 90)
print(f"  Adresses current  : {len(ad_c)}")
print(f"  Adresses sandbox  : {len(ad_s)}")
print(f"  -> delta brut     : {len(ad_s) - len(ad_c):+d}")
print()
print(f"  + {len(NEW_SUF):3d} nouvelles cles AVEC SUFFIXE B/T/Q (cible Pattern A) ✓")
print(f"  + {len(NEW_NOSUF):3d} nouvelles cles sans suffixe (Pattern B/C/D ou nouveaux MAJIC/BDNB)")
print(f"  - {len(lost_cles):3d} cles perdues dont :")
print(f"     . {len(LOST_INJECT):3d} avec marker correctif (PERTE GRAVE)")
print(f"     . {len(LOST_FA):3d} FA (regenerees differemment, possiblement OK)")
print(f"     . {len(LOST_ANCRE):3d} ancres (investigation requise)")
print()
print(f"  Copros perdues (immat manquant sandbox) : {len(lost_co)}")
print(f"    dont avec _injection_correctif : {sum(1 for im in lost_co if any(k.startswith('_injection') for k in co_c_by_immat.get(im,{}).keys()))}")
print()
print(f"  Sandbox preserved : {SANDBOX.name}")
print(f"  Current preserved : {CURRENT.name}")
