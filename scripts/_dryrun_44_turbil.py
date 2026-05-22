#!/usr/bin/env python3
"""DRYRUN 44 RUE TURBIL -> RE-FUSE vers 153 RUE BARABAN (LE PATIO DE L'ISLE).

Pattern Fondary RE-FUSE multi-bgid sur UNE seule parcelle DP0051
(3e instance DL apres 139 DAUPHINE et 21 PIONCHON).

5 preuves convergentes :
1. RNC live AB0535203 LE PATIO DE L'ISLE (SOC ADMIN & GESTION IMMEUB
   ROLIN BAINSON, 120 lots / 43 hab) declare explicitement
   '44 r turbil 69003 LYON' dans adresse_complementaire_1
2. Parcelle BDNB DP0051 identique pour les 2 batis :
   - UN53-G1LZ-2P34 (44 TURBIL, 27 lgts, 2005)
   - HD5Z-A5ZB-RL1N (153 BARABAN, 16 lgts, 2005, immat_principal AB0535203)
3. Tailles : 27+16 BDNB = 43 ≈ 43 RNC hab (parfait)
4. Periodes construction identiques (2005)
5. Terrain utilisateur confirme : meme ensemble

OPS :
- RE-FUSE 44|RUE|TURBIL : _fusion_auto=True,
  _fusion_cible='153 RUE BARABAN / 44 RUE TURBIL'
- Etendre label 153 BARABAN ancre :
  (label actuel : aucun) -> '153 RUE BARABAN / 44 RUE TURBIL'
  + sources = ['44|RUE|TURBIL']

PAS d'INJECT copro (AB0535203 deja ancree cle 153 BARABAN).
"""
import json, sys, copy
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]; co = doc["coproprietes"]

def to_int(x):
    try: return int(x)
    except Exception: return 0

by_cle = {(a.get("cle") or ""): a for a in ad}
a44 = by_cle["44|RUE|TURBIL"]
a153 = by_cle["153|RUE|BARABAN"]

LABEL = "153 RUE BARABAN / 44 RUE TURBIL"

print("=" * 72)
print("DRYRUN 44 TURBIL -> RE-FUSE 153 BARABAN (LE PATIO DE L'ISLE)")
print("=" * 72)
print()
print("[AVANT]")
print(f"  44 TURBIL   : bgid={a44['batiment_groupe_id'][-9:]}  "
      f"bdnb={a44.get('nb_log_bdnb')} vlog={a44.get('nb_ventes_logement')}  "
      f"immat=-  _fusion_auto={a44.get('_fusion_auto')}")
print(f"  153 BARABAN : bgid={a153['batiment_groupe_id'][-9:]}  "
      f"immat={a153.get('numero_immatriculation')}  "
      f"lots_hab={a153.get('nb_lots_habitation')}  "
      f"label={a153.get('_fusion_auto_label') or '(aucun)'}  "
      f"src={a153.get('_fusion_auto_sources') or '(aucun)'}")

# Simulation
ad_after = copy.deepcopy(ad)
by_after = {(a.get("cle") or ""): a for a in ad_after}
a44_aft = by_after["44|RUE|TURBIL"]
a44_aft["_fusion_auto"] = True
a44_aft["_fusion_cible"] = LABEL
a44_aft["_bdnb_match"] = "correctif_44turbil_re_fuse"

a153_aft = by_after["153|RUE|BARABAN"]
old_label = a153_aft.get("_fusion_auto_label")
old_srcs = list(a153_aft.get("_fusion_auto_sources") or [])
a153_aft["_fusion_auto_label"] = LABEL
if "44|RUE|TURBIL" not in old_srcs:
    old_srcs.append("44|RUE|TURBIL")
a153_aft["_fusion_auto_sources"] = old_srcs

print()
print("[OPS]")
print(f"  [RE-FUSE] 44|RUE|TURBIL  _fusion_cible='{LABEL}'")
print(f"  [LABEL]   153|RUE|BARABAN :")
print(f"      label '{old_label or '(aucun)'}' -> '{LABEL}'")
print(f"      sources -> {a153_aft['_fusion_auto_sources']}")

# Algo UI parc
def parc_ui(adlist, colist, assign=None):
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in colist}
    assign = assign or {}
    bgRnc, bgBd = {}, {}
    def eff(a):
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
            e = eff(a)
            if e > 0 and bg not in bgBd: bgBd[bg] = e
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

# KV courant (pour parc exact UI)
KV = ROOT / "data" / "_kv_assign_dl.json"
try:
    kv = json.loads(KV.read_text(encoding="utf-8"))
    assignments = kv.get("assignments") or {}
except Exception:
    assignments = {}

p_av = parc_ui(ad, co, assignments)
p_ap = parc_ui(ad_after, co, assignments)
hr_av = count_hr(ad, co)
hr_ap = count_hr(ad_after, co)

print()
print("[VERIFICATIONS]")
print(f"  parc DL UI    : {p_av} -> {p_ap}  ({p_ap-p_av:+d})")
print(f"  hr-actifs UI  : {hr_av} -> {hr_ap}  ({hr_ap-hr_av:+d})")
print(f"  adresses      : {len(ad)} -> {len(ad_after)}  ({len(ad_after)-len(ad):+d})")
print()
print(">>> AUCUNE MODIFICATION ECRITE.")
