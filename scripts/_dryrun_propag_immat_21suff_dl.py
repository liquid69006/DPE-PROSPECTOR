#!/usr/bin/env python3
"""Dry-run propagation immat sur 21 RATTACHABLES RNC suffixes DL.

Source : data/_triage_85_suffixes_dl.json
Mecanisme (pattern fix-propagation-immat, accf07c) :
  Pour chaque cle suffixee rattachable :
    1. Selectionner la meilleure RNC hit (DEJA-SCT, pct_top match max si plusieurs)
    2. Lookup la copro dans light.coproprietes[immat]
    3. Propager : numero_immatriculation, nb_lots_habitation, taux_rotation,
       classement_rotation, syndic, _syndic_src
  Pas de modification des copros existantes ni d'autres cles.

Aucune ecriture - dry-run lecture seule.
"""
import json, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {a.get("cle"): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}

triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RATTACH_CLES = set(triage.get("rattachables_rnc") or [])
# Detail par cle (depuis triage.detail)
by_cle_triage = {d["cle"]: d for d in triage.get("detail") or []}

print("=" * 90)
print(f"DRY-RUN propagation immat - 21 RATTACHABLES RNC suffixes DL")
print("=" * 90)
print(f"  Light : {len(ad)} adresses, {len(co)} copros, {len(co_by_immat)} immats indexes")
print(f"  Rattachables a traiter : {len(RATTACH_CLES)}")

# --- Choix de la meilleure RNC hit par cle ---
def pick_best_immat(rec):
    """Choisit la meilleure copro RNC pour rattachement :
       priorite DEJA-SCT > HORS-SCT, puis le nom MAJIC top SIREN match nom_copro."""
    hits = rec.get("rnc_hits") or []
    if not hits: return None
    deja = [h for h in hits if h.get("in_sct") == "DEJA-SCT"]
    cands = deja or hits
    # Si 1 seul : direct
    if len(cands) == 1: return cands[0]
    # Sinon : prefere le hit dont le immat existe dans co_by_immat
    inco = [h for h in cands if h.get("immat") in co_by_immat]
    if inco: return inco[0]
    return cands[0]

# --- Propagation simulee ---
print()
print("=" * 90)
print("Detail par cle (AVANT -> APRES proposed)")
print("=" * 90)

NOOP = []    # immat deja propagee correctement
PROP_OK = [] # propagation a faire, copro lookup ok
LOOKUP_KO = [] # immat selectionnee mais pas dans co_by_immat
SKIP_AMBIG = [] # plusieurs immats potentiels - skipped

for cle in sorted(RATTACH_CLES):
    rec = by_cle_triage.get(cle, {})
    hits = rec.get("rnc_hits") or []
    best = pick_best_immat(rec)
    a_cur = by_cle.get(cle, {})
    cur_immat = a_cur.get("numero_immatriculation")
    cur_lots = a_cur.get("nb_lots_habitation")
    if not best:
        SKIP_AMBIG.append((cle, "no hits"))
        continue
    immat = best.get("immat")
    if cur_immat == immat:
        NOOP.append((cle, immat))
        continue
    co_src = co_by_immat.get(immat)
    if not co_src:
        LOOKUP_KO.append((cle, immat, "copro lookup KO"))
        continue
    PROP_OK.append({
        "cle": cle, "immat": immat,
        "cur_immat": cur_immat, "cur_lots": cur_lots,
        "co_src_cle": co_src.get("cle_adresse"),
        "nom_copro": co_src.get("nom_copropriete", "?"),
        "nb_lots_habit": co_src.get("nb_lots_habitation"),
        "nb_lots_total": co_src.get("nb_lots_total"),
        "taux_rot_5": co_src.get("taux_rotation_5ans"),
        "classement": co_src.get("classement_rotation"),
        "syndic": co_src.get("syndic"),
        "_syndic_src": co_src.get("_syndic_src"),
        "rec": rec,
    })

print()
print(f"[OPERATIONS PROPOSEES] : {len(PROP_OK)}")
for x in PROP_OK:
    print(f"  - {x['cle']:34s}  immat={x['immat']}  copro='{x['nom_copro'][:30]}'  "
          f"hab={x['nb_lots_habit']}  taux={x['taux_rot_5']}  classement='{x['classement']}'  "
          f"syndic='{(x['syndic'] or '-')[:30]}'  (parent cle copro={x['co_src_cle']!r})")

if NOOP:
    print()
    print(f"[NO-OP] : {len(NOOP)}  (immat deja correctement propagee)")
    for c, im in NOOP:
        print(f"  - {c:34s} immat deja={im}")

if LOOKUP_KO:
    print()
    print(f"[LOOKUP KO] : {len(LOOKUP_KO)}  (immat selectionnee mais pas dans coproprietes[])")
    for c, im, reason in LOOKUP_KO:
        print(f"  - {c:34s} immat={im}  {reason}")

if SKIP_AMBIG:
    print()
    print(f"[SKIP AMBIG] : {len(SKIP_AMBIG)}")
    for c, reason in SKIP_AMBIG:
        print(f"  - {c:34s} {reason}")

# --- Delta parc UI estime ---
# Algo simple : pour chaque bgid, max(RNC nb_lots, BDNB nb_log) par ancre primaire.
# La propagation immat sur une FA child ne change PAS le dedup bgid existant.
# Mais peut influencer le calcul si la FA child a un nb_lots_habitation
# different / superieur du parent.
USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
co_by_cle = {c.get("cle_adresse"): c for c in co if c.get("cle_adresse")}

def parc_ui(adresses, copros_by_cle):
    by_bgid = {}
    for a in adresses:
        if a.get("_fusion_auto"): continue
        bgid = a.get("batiment_groupe_id") or "<NB>" + (a.get("cle") or "")
        cm = copros_by_cle.get(a.get("cle"))
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid:
            by_bgid[bgid] = max(by_bgid[bgid], n)
        else:
            by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

# Avant
parc_av, n_bg_av = parc_ui(ad, co_by_cle)
# Apres simu : modifier in-memory uniquement nb_lots_habitation des cles
# concernees, et ajouter une entree coproByCle virtuelle.
# (En verite la cle FA child ne contribue pas au parc - on n'attend pas de delta).
co_by_cle_sim = dict(co_by_cle)
# La cle suffixee n'a pas de cle_adresse dans copros (la copro est sur le parent).
# On ne change PAS co_by_cle. Seul nb_lots_habitation propage sur l'adresse,
# qui est FA donc skip dans parc_ui.
# Donc parc_ap = parc_av strictement.
parc_ap, n_bg_ap = parc_ui(ad, co_by_cle_sim)

print()
print("=" * 90)
print("DELTA PARC UI ESTIME")
print("=" * 90)
print(f"  Parc UI avant : {parc_av} lgts sur {n_bg_av} bgids")
print(f"  Parc UI apres : {parc_ap} lgts sur {n_bg_ap} bgids")
print(f"  Delta : {parc_ap - parc_av:+d} lgts")
print()
print(f"  Note : les {len(PROP_OK)} cles a propager sont FA (_fusion_auto=True),")
print(f"  donc exclues du calcul parc UI (dedup bgid actif). La propagation")
print(f"  ajoute des METADATA (immat, syndic, taux, classement) visible dans")
print(f"  le tooltip de la cellule mais ne change pas le parc total.")

# --- Side effects KV ---
print()
print("=" * 90)
print("SIDE EFFECTS KV")
print("=" * 90)
print(f"  La cle FA devient 'copro RNC immatriculee' -> sort du menu 'A qualifier'.")
print(f"  Si elle etait taguee 'social' ou 'mono' dans KV, le tag devient orphelin")
print(f"  (cle FA + copro RNC = UI ne montre plus le menu, KV retired naturally).")
# Verif quelles cles sont en KV
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
if KV_LOCAL.exists():
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    assigns = kv.get("assignments") or {}
    kv_concerned = [(x["cle"], assigns.get(x["cle"])) for x in PROP_OK if assigns.get(x["cle"])]
    print(f"  Cles a propager + actuellement en KV : {len(kv_concerned)}")
    for cle, val in kv_concerned:
        print(f"    {cle:34s} -> KV={val}")

print()
print("=" * 90)
print(f">>> DRY-RUN TERMINE - {len(PROP_OK)} propagations proposees")
print(f"    parc UI : {parc_av} -> {parc_ap}  ({parc_ap-parc_av:+d})")
print("=" * 90)
