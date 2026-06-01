#!/usr/bin/env python3
"""Apply propagation immat sur 21 RATTACHABLES RNC suffixes DL.

Mecanisme : pour chaque cle suffixee rattachable, copie depuis la copro
mere (indexee par immat) les 6 champs :
  numero_immatriculation, nb_lots_habitation, taux_rotation,
  classement_rotation, syndic, _syndic_src
+ tag _correctif_propagation_indice pour tracage.

Backup + apply + verif post-write. Commit a faire par l'orchestrateur.
"""
import json, re, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"
BAK = LIGHT.with_suffix(LIGHT.suffix + ".prepropagimmat21.bak")

MARKER = "fix_propag_immat_21suff_dl_2026-05-23"

# ── GARDE ANTI-FANTOME 2026-06-01 ────────────────────────────────────────
# CAUSE RACINE : make_light rattache un suffixe (ex 11B, 121A) a un bgid par
# faux-matching num_voie (bdnb_par_voie, RAYON=80m, make_light l.477-499) :
# le batiment le PLUS PROCHE dans 80m peut etre une AUTRE copro. Ce script
# propageait alors l'immat de cette copro voisine sur le suffixe -> immat
# FANTOME (cf data/diag_s1_immat_provenance_dl.md + diag_deassoc_immat_fantome_dl.md).
# GARDE : ne propager immat/lots QUE si le bgid DECLARE le numero de base de
# la cle. La preuve = BDNB l_libelle_adr (LIVE) ; le snapshot BDNB local ne
# l'embarque PAS (seulement libelle_adr_principale_ban) -> table CUREE des
# numeros declares par les bgids VERIFIES en live (convention source-of-truth
# comme make_light DECLARED_S1 / ALIAS_RNC). bgid non verifie = comportement
# historique conserve (propage). Pour un nouveau suspect : verifier en live
# l_libelle_adr puis ajouter son entree ici. Le garde positif definitif est
# porte en amont par make_light (passe Consolidation S1 / DECLARED_S1).
BGID_DECLARED = {              # suffixe bgid -> {numeros de base declares (l_libelle_adr LIVE)}
    "3WFJ-G1YT-XLZF": {90, 92},   # 121A-D CHARIAL = intrus (vrai 121 = bgid AX8P)
    "RBD4-VFY6-RGM1": {23, 25},   # 11B ST MAXIMIN = intrus (CARRE DES LYS 23/25)
}

def _basenum(cle):
    m = re.match(r"\d+", (cle or "").split("|")[0])
    return int(m.group()) if m else None

def bgid_declares(a):
    """True si le bgid de l'adresse declare le n° de base de sa cle (garde
    positif sur les bgids verifies ; True par defaut sur les bgids inconnus
    pour ne pas casser les propagations legitimes deja validees)."""
    bg = a.get("batiment_groupe_id") or ""
    for sfx, nums in BGID_DECLARED.items():
        if sfx in bg:
            return _basenum(a.get("cle")) in nums
    return True

def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)

# --- Load ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}
by_cle = {a.get("cle"): a for a in ad}

triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RATTACH = list(triage.get("rattachables_rnc") or [])
by_cle_triage = {d["cle"]: d for d in triage.get("detail") or []}

# Memo init counts
N_AD_AVANT = len(ad)
N_CO_AVANT = len(co)

print("=" * 90)
print(f"APPLY propagation immat - 21 RATTACHABLES suffixes DL")
print("=" * 90)
print(f"  Light AVANT : {N_AD_AVANT} adresses, {N_CO_AVANT} copros")

# --- Backup ---
shutil.copy2(LIGHT, BAK)
print(f"  Backup : {BAK.name}")

# --- Choix copro source par cle (meme logique que le dry-run) ---
def pick_best_immat(rec):
    hits = rec.get("rnc_hits") or []
    if not hits: return None
    deja = [h for h in hits if h.get("in_sct") == "DEJA-SCT"]
    cands = deja or hits
    if len(cands) == 1: return cands[0]
    inco = [h for h in cands if h.get("immat") in co_by_immat]
    if inco: return inco[0]
    return cands[0]

PROPAGATED, ERRORS, SKIPPED_FANTOME = [], [], []

print()
print(f"  Propagation in-place...")
for cle in RATTACH:
    a = by_cle.get(cle)
    if not a:
        ERRORS.append((cle, "cle absente light")); continue
    # GARDE ANTI-FANTOME : ne pas propager si le bgid ne declare pas le numero.
    if not bgid_declares(a):
        SKIPPED_FANTOME.append((cle, a.get("batiment_groupe_id")))
        print(f"    SKIP {cle:34s} FANTOME (bgid ne declare pas le n° de base)")
        continue
    rec = by_cle_triage.get(cle, {})
    best = pick_best_immat(rec)
    if not best:
        ERRORS.append((cle, "no rnc hit")); continue
    immat = best.get("immat")
    co_src = co_by_immat.get(immat)
    if not co_src:
        ERRORS.append((cle, f"copro lookup KO ({immat})")); continue
    # Propagation
    a["numero_immatriculation"] = immat
    nb_hab = co_src.get("nb_lots_habitation")
    if nb_hab is not None:
        a["nb_lots_habitation"] = nb_hab
    tx = co_src.get("taux_rotation_5ans")
    if tx is not None:
        a["taux_rotation"] = tx
    cl = co_src.get("classement_rotation")
    if cl:
        a["classement_rotation"] = cl
    syn = co_src.get("syndic")
    if syn:
        a["syndic"] = syn
    ss = co_src.get("_syndic_src")
    if ss:
        a["_syndic_src"] = ss
    # Tag de tracage
    a["_correctif_propagation_indice"] = MARKER
    PROPAGATED.append((cle, immat))
    print(f"    OK  {cle:34s} immat={immat}  hab={nb_hab}  taux={tx}  classement='{cl}'")

if ERRORS:
    print()
    print(f"  ERREURS ({len(ERRORS)}) :")
    for cle, msg in ERRORS:
        print(f"    KO  {cle} : {msg}")
    fail(f"{len(ERRORS)} erreurs - stop avant ecriture")

print()
if SKIPPED_FANTOME:
    print(f"  GARDE anti-fantome : {len(SKIPPED_FANTOME)} cle(s) NON propagee(s) "
          f"(bgid faux-matche, n° non declare) :")
    for cle, bg in SKIPPED_FANTOME:
        print(f"    - {cle}  (bgid {bg})")
print(f"  {len(PROPAGATED)} propagations effectuees in-memory")

# --- Ecriture (indent=2 pour diff propre) ---
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f"  Ecriture light.json OK")

# --- Verif post-write ---
doc_check = json.loads(LIGHT.read_text(encoding="utf-8"))
N_AD_APR = len(doc_check["adresses"])
N_CO_APR = len(doc_check["coproprietes"])
if N_AD_APR != N_AD_AVANT or N_CO_APR != N_CO_AVANT:
    fail(f"Compte modifie : ad {N_AD_AVANT}->{N_AD_APR}, co {N_CO_AVANT}->{N_CO_APR}")

ad_check = {a.get("cle"): a for a in doc_check["adresses"]}
ok = 0
for cle, immat in PROPAGATED:
    a = ad_check.get(cle, {})
    if a.get("numero_immatriculation") != immat:
        fail(f"Verif post-write : {cle} immat={a.get('numero_immatriculation')!r} (attendu {immat!r})")
    if a.get("_correctif_propagation_indice") != MARKER:
        fail(f"Verif post-write : {cle} marker absent")
    ok += 1
print(f"  Verif post-write : {ok}/{len(PROPAGATED)} OK")
print(f"  Light APRES : {N_AD_APR} adresses, {N_CO_APR} copros (inchanges)")

print()
print("=" * 90)
print(f">>> APPLY OK - {len(PROPAGATED)} cles enrichies (immat + nb_lots + syndic + rotation)")
print(f"    Backup : {BAK.name}")
print(f"    Commit a faire par l'orchestrateur. PAS DE PUSH.")
print("=" * 90)
