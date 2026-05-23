#!/usr/bin/env python3
"""Dry-run RE-FUSE 7/9/11 IMP ORDRE -> 118 RUE BARABAN (CLOS SAINTE ANNE AB8922999).

Pattern combine :
  - fix-propagation-immat : propagation AB8922999 + lots + syndic vers 3 cles
  - RE-FUSE bgid : QHUC/7CXY/PK29 -> AGDC-W8DF-4GCQ (= 118 BARABAN)
  - FA cible='118|RUE|BARABAN'
  - Label parent '118 RUE BARABAN / 7/9/11 IMPASSE DE L ORDRE'
  - DELETE KV des 3 IMP ORDRE (etaient copro_non_immat batch orphans)

Lecture seule.
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

# Cibles
CLES_IMP = ["7|IMPASSE|ORDRE", "9|IMPASSE|ORDRE", "11|IMPASSE|ORDRE"]
PARENT = "118|RUE|BARABAN"
IMMAT_CLOS = "AB8922999"
TARGET_BGID = "bdnb-bg-AGDC-W8DF-4GCQ"
NEW_LABEL = "118 RUE BARABAN / 7/9/11 IMPASSE DE L ORDRE"

# --- Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
by_cle = {a.get("cle"): a for a in doc["adresses"]}
co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]
               if c.get("numero_immatriculation")}

# Recup copro mere AB8922999
co_clos = co_by_immat.get(IMMAT_CLOS)
if not co_clos: print(f"ERREUR : copro {IMMAT_CLOS} introuvable"); sys.exit(3)
print("=" * 90)
print("DRY-RUN RE-FUSE 7/9/11 IMP ORDRE -> 118 BARABAN (LE CLOS SAINTE ANNE)")
print("=" * 90)
print()
print("[AVANT]")
print(f"  Parent : {PARENT}")
a_par = by_cle.get(PARENT, {})
print(f"    bgid={a_par.get('batiment_groupe_id')}  immat={a_par.get('numero_immatriculation')}")
print(f"    bdnb={a_par.get('nb_log_bdnb')}  lots_hab={a_par.get('nb_lots_habitation')}")
print(f"    syndic={a_par.get('syndic')!r}")
print(f"    label='{a_par.get('_fusion_auto_label') or ''}'")
print(f"    sources={a_par.get('_fusion_auto_sources')}")
print()
print(f"  Copro mere {IMMAT_CLOS} (light.coproprietes) :")
print(f"    nom='{co_clos.get('nom_copropriete')}'  syndic='{co_clos.get('syndic')}'  src={co_clos.get('_syndic_src')!r}")
print(f"    nb_lots_total={co_clos.get('nb_lots_total')}  nb_lots_habitation={co_clos.get('nb_lots_habitation')}")
print(f"    taux_rotation_5ans={co_clos.get('taux_rotation_5ans')}  classement_rotation={co_clos.get('classement_rotation')!r}")
print(f"    cle_adresse={co_clos.get('cle_adresse')!r}")
print()
print(f"  Cles a fuser :")
for cle in CLES_IMP:
    a = by_cle.get(cle, {})
    print(f"    {cle:30s}  bgid=...{(a.get('batiment_groupe_id') or '-')[-9:]}  bdnb={a.get('nb_log_bdnb')}  immat={a.get('numero_immatriculation') or '-'}  FA={a.get('_fusion_auto')}")

# --- GET KV ---
req = urllib.request.Request(ENDPOINT, headers={
    "Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    kv = json.loads(r.read().decode("utf-8"))
assigns = kv.get("assignments") or {}
print(f"  KV avant : {len(assigns)} assigns")
for cle in CLES_IMP:
    print(f"    KV[{cle}] = {assigns.get(cle)}")

# --- OPERATIONS PROPOSEES ---
print()
print("[OPERATIONS PROPOSEES]")
print()
print(f"  (A) Pour chaque cle 7/9/11 IMP ORDRE :")
print(f"      numero_immatriculation : (absent) -> {IMMAT_CLOS}")
print(f"      nb_lots_habitation     : (absent) -> {co_clos.get('nb_lots_habitation')}")
print(f"      taux_rotation          : (None)   -> {co_clos.get('taux_rotation_5ans')}")
print(f"      classement_rotation    : 'Aucune vente' -> {co_clos.get('classement_rotation')!r}")
print(f"      syndic                 : None     -> {co_clos.get('syndic')!r}")
print(f"      _syndic_src            : None     -> {co_clos.get('_syndic_src')!r}")
print(f"      batiment_groupe_id     : (orphan bgid) -> {TARGET_BGID}")
print(f"      _fusion_auto           : -> True")
print(f"      _fusion_cible          : -> {PARENT!r}")
print(f"      _correctif_imp_ordre   : -> 'fix_imp_ordre_clos_sainte_anne_2026-05-23'")
print()
print(f"  (B) Sur {PARENT} :")
old_label = a_par.get("_fusion_auto_label") or ""
old_sources = a_par.get("_fusion_auto_sources") or []
new_sources = list(old_sources) + CLES_IMP
print(f"      _fusion_auto_label : {old_label!r} -> {NEW_LABEL!r}")
print(f"      _fusion_auto_sources : {old_sources} -> {new_sources}")
print()
print(f"  (C) KV DELETE 3 cles 7/9/11 IMP ORDRE (etaient 'copro_non_immat')")

# --- Delta parc UI ---
USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
def parc_ui(adresses, copros):
    co_by_cle_ = {c.get("cle_adresse"): c for c in copros if c.get("cle_adresse")}
    by_bgid = {}
    for a in adresses:
        if a.get("_fusion_auto"): continue
        bgid = a.get("batiment_groupe_id") or "<NB>" + (a.get("cle") or "")
        cm = co_by_cle_.get(a.get("cle"))
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid: by_bgid[bgid] = max(by_bgid[bgid], n)
        else: by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

parc_av, n_bg_av = parc_ui(doc["adresses"], doc["coproprietes"])
doc_sim = json.loads(json.dumps(doc))
for a in doc_sim["adresses"]:
    if a.get("cle") in CLES_IMP:
        a["batiment_groupe_id"] = TARGET_BGID
        a["_fusion_auto"] = True
        a["_fusion_cible"] = PARENT
parc_ap, n_bg_ap = parc_ui(doc_sim["adresses"], doc_sim["coproprietes"])

print()
print("[DELTA PARC UI ESTIME]")
print(f"  Parc avant : {parc_av} lgts sur {n_bg_av} bgids actifs")
print(f"  Parc apres : {parc_ap} lgts sur {n_bg_ap} bgids actifs")
print(f"  Delta : {parc_ap - parc_av:+d} lgts  |  bgids : {n_bg_ap - n_bg_av:+d}")
print()
print(f"  Explication :")
print(f"    Avant : DS0119 comptait 4 bgids (AGDC 118 BARABAN=49 RNC, QHUC 7 IMP=9, 7CXY 9 IMP=6, PK29 11 IMP=6)")
print(f"            = sur-comptage BDNB multi-bgid (4 bgids artificiels pour 1 copro physique).")
print(f"    Apres : DS0119 reste sur 1 bgid AGDC avec 49 lots RNC (autoritaire).")
print(f"    Net   : correction -21 lgts (somme des 3 bgids BDNB orphelins qui sortent).")

print()
print("[SIDE EFFECTS]")
print(f"  - hr-ancres   : -3 (3 IMP ORDRE deviennent FA)")
print(f"  - KV server   : -3 (DELETE 3 copro_non_immat orphans)")
print(f"  - copros      : 554 (inchangees)")
print(f"  - 118 BARABAN reste ancre RNC (intact bgid + immat)")
print(f"  - bgids orphans (QHUC, 7CXY, PK29) deviennent inactifs (plus d'adresse)")

print()
print("=" * 90)
print(">>> DRY-RUN TERMINE - aucune modification effectuee")
print(f"    light : 3 cles 7/9/11 modifs (8-9 champs chacune) + 1 parent (label+sources)")
print(f"    KV    : 3 DELETE")
print("=" * 90)
