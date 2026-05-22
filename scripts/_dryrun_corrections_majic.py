#!/usr/bin/env python3
"""DRYRUN des corrections immediates post-sweep MAJIC :

1. KV qualif mono 45|AVENUE|GEORGES POMPIDOU (MAESTRIMMO 190/190 lots)
   -> POST API /secteur-assignments/dauphine-lacassagne
   (effet UI immediat, pas de modif light.json)

2. RE-POINT 18|RUE|ST ANTOINE :
   bgid PFFK-6Z9V-TUP1 (= 17 ST ANTOINE) -> KXL7-E97N (4 TERNOIS bati)
   + FA fused vers chaine 4 TERNOIS (label etendu)
   (modif light.json + .pre18stantoine.bak + commit local)

Faux-matchings POMPIDOU 48/52 et 21 ST ANTOINE = faux positifs
MAJIC (BAN-BDNB autorite confirme les bgids actuels). PAS de fix.
"""
import json, sys, copy
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV = ROOT / "data" / "_kv_assign_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
kv = json.loads(KV.read_text(encoding="utf-8"))
def to_int(x):
    try: return int(x)
    except: return 0

by_cle = {(a.get("cle") or ""): a for a in ad}

# ============================================================
# 1) KV qualif mono 45 POMPIDOU
# ============================================================
print("=" * 76)
print("[1] KV QUALIF mono 45|AVENUE|GEORGES POMPIDOU (MAESTRIMMO 190 lots)")
print("=" * 76)
print()
assignments = kv.get("assignments") or {}
cur_45 = assignments.get("45|AVENUE|GEORGES POMPIDOU")
print(f"  KV actuel 45 POMPIDOU : {cur_45 or '(absent)'}")
print(f"  KV actuel TOTAL : {len(assignments)} assignments + "
      f"{len(kv.get('fusions') or {})} fusions")
print()
new_assign = dict(assignments)
new_assign["45|AVENUE|GEORGES POMPIDOU"] = {"type": "mono"}
new_payload = {
    "assignments": new_assign,
    "fusions": kv.get("fusions") or {},
    "noms": kv.get("noms") or {},
}
print(f"  Apres POST KV :")
print(f"    45|AVENUE|GEORGES POMPIDOU -> {{type: 'mono'}}")
print(f"    Total assignments : {len(new_assign)} (+1)")
print()

# Effet sur hr-actifs UI : 45 POMPIDOU avait vlog=1, bdnb=61
# Avec type=mono -> getEffectiveLog retourne 1 (pas exclu du compte)
# Mais surtout : badge UI mono + exit periode "non qualifie"
a45 = by_cle["45|AVENUE|GEORGES POMPIDOU"]
print(f"  Effet UI sur 45 POMPIDOU :")
print(f"    vlog={a45.get('nb_ventes_logement')} bdnb={a45.get('nb_log_bdnb')} -> badge 'Monopropriete'")
print(f"    getEffectiveLog avant : {a45.get('nb_log_bdnb')} (BDNB)")
print(f"    getEffectiveLog apres : 1 (mono)")
print()

# ============================================================
# 2) RE-POINT 18 ST ANTOINE
# ============================================================
print("=" * 76)
print("[2] RE-POINT 18|RUE|ST ANTOINE : PFFK-6Z9V-TUP1 -> KXL7-E97N")
print("=" * 76)
print()
a18 = by_cle.get("18|RUE|ST ANTOINE")
a4t = by_cle.get("4|RUE|TERNOIS")
print(f"  AVANT :")
print(f"    18 ST ANTOINE : bgid={a18.get('batiment_groupe_id')}")
print(f"      bdnb={a18.get('nb_log_bdnb')} vlog={a18.get('nb_ventes_logement')}")
print(f"      _bdnb_match={a18.get('_bdnb_match')}")
print(f"      _fusion_auto={a18.get('_fusion_auto')} _fusion_cible={a18.get('_fusion_cible')}")
print(f"    4 TERNOIS ancre : bgid={a4t.get('batiment_groupe_id')}")
print(f"      label='{a4t.get('_fusion_auto_label')}' src={a4t.get('_fusion_auto_sources')}")
print()

NEW_BGID = "bdnb-bg-5RMC-KXL7-E97N"
LABEL = "4/6 RUE TERNOIS / 93 RUE BELLECOMBE / 18 RUE ST ANTOINE"

# Simulation
ad_after = copy.deepcopy(ad)
by_after = {(a.get("cle") or ""): a for a in ad_after}
a18_aft = by_after["18|RUE|ST ANTOINE"]
a4t_aft = by_after["4|RUE|TERNOIS"]

# RE-POINT 18 ST ANTOINE
a18_aft["batiment_groupe_id"] = NEW_BGID
a18_aft["nb_log_bdnb"] = 80          # BDNB KXL7-E97N nb_log
a18_aft["annee_construction"] = 1990
a18_aft["_bdnb_match"] = "correctif_18stantoine_re_point"
a18_aft["_fusion_auto"] = True
a18_aft["_fusion_cible"] = LABEL

# Extension label 4 TERNOIS
a4t_aft["_fusion_auto_label"] = LABEL
srcs = list(a4t_aft.get("_fusion_auto_sources") or [])
for s in ["18|RUE|ST ANTOINE","93|RUE|BELLECOMBE"]:
    if s not in srcs and s in by_after:
        srcs.append(s)
# 93 BELLECOMBE n'existe peut-etre pas en light : on ajoute seulement 18 ST ANTOINE
srcs_real = [s for s in srcs if s in by_after or s == "18|RUE|ST ANTOINE"]
a4t_aft["_fusion_auto_sources"] = srcs_real

print(f"  OPS :")
print(f"    [RE-POINT] 18|RUE|ST ANTOINE  PFFK-6Z9V-TUP1 -> KXL7-E97N")
print(f"               nb_log_bdnb 42 -> 80  annee 1932 -> 1990")
print(f"               _fusion_auto=True  _fusion_cible='{LABEL}'")
print(f"    [LABEL]    4|RUE|TERNOIS  label='{LABEL}'")
print(f"               sources={srcs_real}")
print()

# Algo UI parc
def parc_ui(adlist, colist, assign):
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in colist}
    bgRnc, bgBd = {}, {}
    def eff_log(a):
        cle = a.get("cle") or ""
        t = (assign.get(cle) or {}).get("type")
        if t == "mono": return 1
        if t in ("social","bureaux"): return 0
        return to_int(a.get("nb_log_bdnb"))
    for a in adlist:
        cle = a.get("cle") or ""; bg = a.get("batiment_groupe_id") or ""
        if not bg: continue
        c = co_by_cle.get(cle)
        if c:
            lots = to_int(c.get("nb_lots_habitation"))
            if lots > 0: bgRnc.setdefault(bg, {})[cle] = lots
        else:
            eff = eff_log(a)
            if eff > 0 and bg not in bgBd: bgBd[bg] = eff
    t = 0
    for bg in set(list(bgRnc.keys()) + list(bgBd.keys())):
        t += sum(bgRnc[bg].values()) if bg in bgRnc else bgBd.get(bg, 0)
    return t

def count_hr(adlist, colist):
    cm = {(c.get("cle_adresse") or ""): c for c in colist}
    n = 0
    for a in adlist:
        cle = a.get("cle") or ""
        if cle in cm: continue
        if a.get("numero_immatriculation"): continue
        if a.get("_fusion_auto"): continue
        if to_int(a.get("nb_ventes_logement")) <= 0: continue
        if to_int(a.get("nb_log_bdnb")) <= 1: continue
        n += 1
    return n

# Cas combines avant/apres
p_av_kv0 = parc_ui(ad, co, assignments)
p_av_kv1 = parc_ui(ad, co, new_assign)            # KV applique
p_ap_kv0 = parc_ui(ad_after, co, assignments)     # light fix mais KV ancien
p_ap_kv1 = parc_ui(ad_after, co, new_assign)      # light fix + KV applique
hr_av = count_hr(ad, co)
hr_ap = count_hr(ad_after, co)

print("[VERIFICATIONS combinees]")
print(f"  parc DL UI :")
print(f"    avant    (light original + KV original)        : {p_av_kv0}")
print(f"    KV-seul  (light original + KV mono 45 POMPIDOU): {p_av_kv1}  (delta {p_av_kv1-p_av_kv0:+d})")
print(f"    light-seul (light fix + KV original)            : {p_ap_kv0}  (delta {p_ap_kv0-p_av_kv0:+d})")
print(f"    final    (light fix + KV mono)                 : {p_ap_kv1}  (delta {p_ap_kv1-p_av_kv0:+d})")
print()
print(f"  hr-actifs UI : {hr_av} -> {hr_ap}  (delta {hr_ap-hr_av:+d})  (18 ST ANTOINE sort en FA)")
print(f"  adresses     : {len(ad)} -> {len(ad_after)}  (delta {len(ad_after)-len(ad):+d})")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
print(">>> POST API NON ENVOYE.")
