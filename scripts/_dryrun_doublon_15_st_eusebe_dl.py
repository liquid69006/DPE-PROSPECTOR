#!/usr/bin/env python3
"""Dry-run RE-FUSE 15 IMPASSE ST EUSEBE -> 15 RUE ST EUSEBE.

Cause : confirmation terrain - meme immeuble, BDNB a dedouble en 2 bgids
distincts. DVF enregistre les 7 ventes sur 'RUE ST EUSEBE' qui sont en
realite sur la parcelle DT0108 du bgid IMPASSE.

Operations :
  1. light : 15 IMPASSE -> _fusion_auto=True, _fusion_cible='15|RUE|ST EUSEBE'
            bgid BT7D-ZQ25 -> DYCH-XSSS (alignement physique sur ancre 12 RUE)
            tag _correctif_doublon_eusebe
  2. KV    : DELETE 15|IMPASSE|ST EUSEBE (etait copro_non_immat batch orphans)

Parc UI : -31 lgts (correction sur-comptage BDNB sur le bgid BT7D-ZQ25
qui sort du calcul, 12 RUE garde sa contribution 55 lgts via DYCH-XSSS).
"""
import json, sys, os, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 diag/1.0"

# --- Get KV ---
req = urllib.request.Request(ENDPOINT, headers={
    "Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    kv = json.loads(r.read().decode("utf-8"))
assigns = kv.get("assignments") or {}

# --- Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
by_cle = {a.get("cle"): a for a in doc["adresses"]}

ORPHAN = "15|IMPASSE|ST EUSEBE"
PARENT = "15|RUE|ST EUSEBE"
ANCRE_REAL = "12|RUE|ST EUSEBE"

a_orph = by_cle.get(ORPHAN)
a_par  = by_cle.get(PARENT)
a_anc  = by_cle.get(ANCRE_REAL)

print("=" * 90)
print("DRY-RUN RE-FUSE 15 IMPASSE ST EUSEBE -> 15 RUE ST EUSEBE (doublon BDNB)")
print("=" * 90)
print()
print("[AVANT]")
print(f"  {ANCRE_REAL:34s} bgid=...{a_anc.get('batiment_groupe_id','-')[-9:]} bdnb={a_anc.get('nb_log_bdnb')} FA={a_anc.get('_fusion_auto')}")
print(f"    label   = {a_anc.get('_fusion_auto_label')!r}")
print(f"    sources = {a_anc.get('_fusion_auto_sources')}")
print(f"  {PARENT:34s} bgid=...{a_par.get('batiment_groupe_id','-')[-9:]} bdnb={a_par.get('nb_log_bdnb')} vlog={a_par.get('nb_ventes_logement')} FA={a_par.get('_fusion_auto')} cible={a_par.get('_fusion_cible')!r}")
print(f"  {ORPHAN:34s} bgid=...{a_orph.get('batiment_groupe_id','-')[-9:]} bdnb={a_orph.get('nb_log_bdnb')} vlog={a_orph.get('nb_ventes_logement')} FA={a_orph.get('_fusion_auto')}")
print(f"  KV[{ORPHAN}] = {assigns.get(ORPHAN)}")

# Operations proposees
target_bgid = a_par.get("batiment_groupe_id")
print()
print("[OPERATIONS PROPOSEES]")
print(f"  light : {ORPHAN}")
print(f"    bgid              : {a_orph.get('batiment_groupe_id')} -> {target_bgid}")
print(f"    _fusion_auto      : (absent) -> True")
print(f"    _fusion_cible     : (absent) -> {PARENT!r}")
print(f"    _correctif_doublon_eusebe : -> 'fix_doublon_15_st_eusebe_2026-05-23'")
print(f"    (label/sources 12 RUE inchanges - terrain dit meme immeuble que 15 RUE")
print(f"     deja dans sources de 12 RUE)")
print()
print(f"  KV : DELETE {ORPHAN!r}  (etait '{(assigns.get(ORPHAN) or {}).get('type')}')")

# Simulation parc
USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
def parc_ui(adresses, copros):
    co_by_cle = {c.get("cle_adresse"): c for c in copros if c.get("cle_adresse")}
    by_bgid = {}
    for a in adresses:
        if a.get("_fusion_auto"): continue
        bgid = a.get("batiment_groupe_id") or "<NB>" + (a.get("cle") or "")
        cm = co_by_cle.get(a.get("cle"))
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid: by_bgid[bgid] = max(by_bgid[bgid], n)
        else: by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

# Avant
parc_av, n_bg_av = parc_ui(doc["adresses"], doc["coproprietes"])
# Simulation : modifier 15 IMPASSE in-memory
import copy
doc_sim = json.loads(json.dumps(doc))  # deep copy
for a in doc_sim["adresses"]:
    if a.get("cle") == ORPHAN:
        a["batiment_groupe_id"] = target_bgid
        a["_fusion_auto"] = True
        a["_fusion_cible"] = PARENT
        break
parc_ap, n_bg_ap = parc_ui(doc_sim["adresses"], doc_sim["coproprietes"])

print()
print("[DELTA PARC UI ESTIME]")
print(f"  Parc avant : {parc_av} lgts sur {n_bg_av} bgids actifs")
print(f"  Parc apres : {parc_ap} lgts sur {n_bg_ap} bgids actifs")
print(f"  Delta : {parc_ap - parc_av:+d} lgts  |  bgids : {n_bg_ap - n_bg_av:+d}")
print()
print(f"  Explication : le bgid BT7D-ZQ25 perd son ancre (15 IMPASSE devient FA),")
print(f"  donc sort du calcul parc. Le bgid DYCH-XSSS garde son ancre (12 RUE)")
print(f"  avec ses 55 lgts. Le delta -31 correspond a la CORRECTION du sur-comptage")
print(f"  BDNB (bati dedouble en 2 bgids alors que c'est le meme immeuble terrain).")

print()
print("[SIDE EFFECTS]")
print(f"  - 15 IMPASSE ST EUSEBE devient FA -> sort des hr-ancres UI")
print(f"  - hr-ancres total       : -1")
print(f"  - KV total              : 456 -> 455 (delete)")
print(f"  - copros (inchangees)   : 554")
print(f"  - cles existantes autres modifiees : 0 (12 RUE intact, 15 RUE intact)")

print()
print("=" * 90)
print(">>> DRY-RUN TERMINE - aucune modification effectuee")
print(f"    light modifs prevues : 1 cle (15 IMPASSE) = 4 champs")
print(f"    KV modifs prevues    : 1 DELETE")
print("=" * 90)
