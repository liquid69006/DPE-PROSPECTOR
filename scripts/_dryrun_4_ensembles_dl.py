#!/usr/bin/env python3
"""Dry-run sequentiel E3 / E2 / E4 / E5 - aucune modification.

E3 : 2|RUE|VILLETTE -> KV copro_non_immat (server KV uniquement)
E2 : 24 GABILLOT + 233 PAUL BERT -> RE-POINT 233 PB bgid (light.json)
E4 : 4/6 MILIEU -> RE-POINT 6 + RE-FUSE 6->4 (light.json)
E5 : 2 ST PHILIPPE + 20 DAUPHINE -> INJECT RNC + ATTRIBUER +
     RE-POINT 20 DAUPH + RE-FUSE 20->2 ST PHILIPPE (light.json + KV)

Affiche pour chaque ensemble :
  - etat AVANT (lecture light + KV)
  - operations a appliquer (delta)
  - etat APRES (simule)
  - delta parc UI + side effects

Lecture seule. Pas de POST. Pas d'ecriture fichier.
"""
import json, sys, os, urllib.parse, urllib.request, time
from pathlib import Path
from copy import deepcopy

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
KV_ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

RID_RNC = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID_RNC}/data/"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_KV = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}

def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return -1, {"_error": str(e)[:200]}

# ============================================================
# CHARGEMENT INITIAL
# ============================================================
print("=" * 90)
print("DRY-RUN E3 + E2 + E4 + E5 (sequentiel) - lecture seule")
print("=" * 90)

# Light snapshot
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}

# KV server
code, kv = http_get(KV_ENDPOINT, HDR_KV)
if code != 200:
    print(f"ERREUR GET KV : {kv}"); sys.exit(3)
assigns = kv.get("assignments") or {}
fusions_kv = kv.get("fusions") or {}
noms_kv = kv.get("noms") or {}
print(f"  light : {len(ad)} adresses, {len(co)} copros")
print(f"  KV server : {len(assigns)} assigns, {len(fusions_kv)} fusions, {len(noms_kv)} noms")

# Helper : etat compact d'une cle
def snap_cle(cle, light_view):
    a = light_view.get(cle)
    if not a: return f"{cle:34s} ABSENT"
    flags = []
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_cible"): flags.append(f"cible='{a['_fusion_cible']}'")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
    if a.get("_fusion_auto_sources"): flags.append(f"src={a['_fusion_auto_sources']}")
    if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
    return (f"{cle:34s} bgid=...{(a.get('batiment_groupe_id') or '-')[-9:]} "
            f"bdnb={a.get('nb_log_bdnb')} {'COPRO' if any(c.get('cle_adresse')==cle for c in co) else ''} "
            + " ".join(flags))

def kv_snap(cle, kv_view):
    v = kv_view.get(cle)
    return f"{cle:34s} KV={v}"

# ============================================================
# E3 : 2|RUE|VILLETTE -> KV copro_non_immat
# ============================================================
print()
print("#" * 90)
print("# DRY-RUN E3 : 2|RUE|VILLETTE -> KV copro_non_immat")
print("#" * 90)

E3_CLE = "2|RUE|VILLETTE"
print()
print("[AVANT]")
print(f"  light  : {snap_cle(E3_CLE, by_cle)}")
print(f"  KV     : {kv_snap(E3_CLE, assigns)}")

print()
print("[OPERATION]")
print(f"  POST  {KV_ENDPOINT}  body.assignments['{E3_CLE}']={{type:'copro_non_immat'}}")
print(f"  -> 1 cle ajoutee en KV (cle pas encore presente)")

# Etat simule
assigns_e3 = dict(assigns)
assigns_e3[E3_CLE] = {"type": "copro_non_immat"}
print()
print("[APRES (simule)]")
print(f"  KV     : {kv_snap(E3_CLE, assigns_e3)}")
print(f"  KV total : {len(assigns)} -> {len(assigns_e3)} (+1)")
print()
print("[DELTA]")
print(f"  - Parc UI       : 0 (KV-only, light intacte)")
print(f"  - Light         : 0 modif")
print(f"  - hr-ancres     : -0 (la cle 2 VILLETTE reste hr-ancre, juste taguee copro_non_immat)")
print(f"  - Side effects  : aucun")

# ============================================================
# E2 : 24 GABILLOT + 233 PAUL BERT -> RE-POINT 233 PB
# ============================================================
print()
print("#" * 90)
print("# DRY-RUN E2 : 24 GABILLOT + 233 PB -> RE-POINT 233 PB bgid TEDX -> XNGN")
print("#" * 90)

E2_ANCRE = "24|RUE|GABILLOT"
E2_REPOINT = "233|RUE|PAUL BERT"

a_ancre = by_cle.get(E2_ANCRE)
a_pb    = by_cle.get(E2_REPOINT)
bgid_ancre = (a_ancre.get("batiment_groupe_id") if a_ancre else "?")
bgid_pb_avant = (a_pb.get("batiment_groupe_id") if a_pb else "?")

print()
print("[AVANT]")
print(f"  {snap_cle(E2_ANCRE, by_cle)}")
print(f"  {snap_cle(E2_REPOINT, by_cle)}")

print()
print("[OPERATION light.json]")
print(f"  ad[cle={E2_REPOINT}].batiment_groupe_id : '{bgid_pb_avant}' -> '{bgid_ancre}'")
print(f"  ad[cle={E2_ANCRE}]._fusion_auto_label   : '-' -> '24 RUE GABILLOT / 233 RUE PAUL BERT'")
print(f"  ad[cle={E2_ANCRE}]._fusion_auto_sources : '-' -> ['233|RUE|PAUL BERT']")

# Simulation
by_cle_e2 = deepcopy(by_cle)
by_cle_e2[E2_REPOINT]["batiment_groupe_id"] = bgid_ancre
by_cle_e2[E2_ANCRE]["_fusion_auto_label"] = "24 RUE GABILLOT / 233 RUE PAUL BERT"
by_cle_e2[E2_ANCRE]["_fusion_auto_sources"] = ["233|RUE|PAUL BERT"]

print()
print("[APRES (simule)]")
print(f"  {snap_cle(E2_ANCRE, by_cle_e2)}")
print(f"  {snap_cle(E2_REPOINT, by_cle_e2)}")
print()
print("[DELTA]")
print(f"  - Parc UI       : 0 (233 PB.bdnb=None, pas de double-comptage)")
print(f"  - Light         : 1 RE-POINT bgid + 1 label/sources sur ancre")
print(f"  - hr-ancres     : 0 (233 PB reste hr-ancre, juste re-pointee carto)")
print(f"  - KV            : aucun changement (233 PB reste bureaux, 24 GABILLOT reste mono)")
print(f"  - Side effects  : aucun")

# ============================================================
# E4 : 4/6 MILIEU -> RE-POINT 6 + RE-FUSE 6->4
# ============================================================
print()
print("#" * 90)
print("# DRY-RUN E4 : 4/6 MILIEU -> RE-POINT 6 + RE-FUSE 6->4")
print("#" * 90)

E4_ANCRE = "4|RUE|MILIEU"
E4_FUSE = "6|RUE|MILIEU"
a_4 = by_cle.get(E4_ANCRE)
a_6 = by_cle.get(E4_FUSE)
bgid_4 = a_4.get("batiment_groupe_id") if a_4 else "?"
bgid_6_avant = a_6.get("batiment_groupe_id") if a_6 else "?"
bdnb_6 = a_6.get("nb_log_bdnb", 0) if a_6 else 0

print()
print("[AVANT]")
print(f"  {snap_cle(E4_ANCRE, by_cle)}")
print(f"  {snap_cle(E4_FUSE, by_cle)}")
print(f"  KV 4 MILIEU : {assigns.get(E4_ANCRE)}")
print(f"  KV 6 MILIEU : {assigns.get(E4_FUSE)}")

print()
print("[OPERATION light.json]")
print(f"  ad[cle={E4_FUSE}].batiment_groupe_id    : '{bgid_6_avant}' -> '{bgid_4}'")
print(f"  ad[cle={E4_FUSE}]._fusion_auto         : -> True")
print(f"  ad[cle={E4_FUSE}]._fusion_cible        : -> '{E4_ANCRE}'")
print(f"  ad[cle={E4_ANCRE}]._fusion_auto_label  : -> '4/6 RUE MILIEU'")
print(f"  ad[cle={E4_ANCRE}]._fusion_auto_sources: -> ['6|RUE|MILIEU']")
print()
print("[OPERATION KV (side-effect post-fusion)]")
print(f"  KV[{E4_FUSE}] = {{type:'mono'}} (JUNE) devient orphelin (cle FA -> hors menu UI)")
print(f"  -> RECOMMANDATION : retirer 6 MILIEU du KV pour hygiene (delete assignment)")

# Simulation
by_cle_e4 = deepcopy(by_cle)
by_cle_e4[E4_FUSE].update({
    "batiment_groupe_id": bgid_4,
    "_fusion_auto": True,
    "_fusion_cible": E4_ANCRE,
})
by_cle_e4[E4_ANCRE].update({
    "_fusion_auto_label": "4/6 RUE MILIEU",
    "_fusion_auto_sources": [E4_FUSE],
})

assigns_e4 = dict(assigns)
if E4_FUSE in assigns_e4: del assigns_e4[E4_FUSE]  # simu hygiene

print()
print("[APRES (simule)]")
print(f"  {snap_cle(E4_ANCRE, by_cle_e4)}")
print(f"  {snap_cle(E4_FUSE, by_cle_e4)}")
print(f"  KV {E4_FUSE} : {assigns_e4.get(E4_FUSE)} (retire)")
print(f"  KV total : {len(assigns)} -> {len(assigns_e4)} (-1, hygiene)")
print()
print("[DELTA]")
print(f"  - Parc UI       : -{bdnb_6} lgts (6 MILIEU bdnb={bdnb_6} absorbe via dedup bgid)")
print(f"  - Light         : 1 RE-POINT bgid + 1 FA cible + 1 label/sources")
print(f"  - hr-ancres     : -1 (6 MILIEU devient FA, sort des ancres)")
print(f"  - KV            : -1 (retire 6 MILIEU mono orphelin)")
print(f"  - Side effects  : enrich_majic re-mappera 4+6 MILIEU sur BARABAN (correction faux JUNE)")

# ============================================================
# E5 : 2 ST PHILIPPE + 20 DAUPHINE -> INJECT + ATTRIBUER + RE-POINT + FUSE
# ============================================================
print()
print("#" * 90)
print("# DRY-RUN E5 : 2 ST PHILIPPE + 20 DAUPHINE -> INJECT AF2921443 + RE-POINT 20")
print("#" * 90)

E5_ANCRE  = "2|RUE|ST PHILIPPE"
E5_REPOINT = "20|RUE|DAUPHINE"
IMMAT_NEW  = "AF2921443"

a_stph = by_cle.get(E5_ANCRE)
a_20dp = by_cle.get(E5_REPOINT)
bgid_stph = a_stph.get("batiment_groupe_id") if a_stph else "?"
bgid_20dp_avant = a_20dp.get("batiment_groupe_id") if a_20dp else "?"
fa_cible_20dp_avant = a_20dp.get("_fusion_cible") if a_20dp else None

print()
print("[AVANT]")
print(f"  {snap_cle(E5_ANCRE, by_cle)}")
print(f"  {snap_cle(E5_REPOINT, by_cle)}")
print(f"  KV 2 ST PHILIPPE : {assigns.get(E5_ANCRE)}")
print(f"  Existing copro AF2921443 in light : {any(c.get('numero_immatriculation')==IMMAT_NEW for c in co)}")

# Fetch RNC live AF2921443 pour donnees a injecter
print()
print(f"[FETCH RNC live AF2921443]")
url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": IMMAT_NEW})
code_rnc, rnc = http_get(url, timeout=20)
rnc_data = None
if isinstance(rnc, dict) and rnc.get("data"):
    rnc_data = rnc["data"][0]
if not rnc_data:
    print(f"  ERREUR : AF2921443 introuvable tabular-api (live cache?)");
else:
    print(f"  nom_usage           : '{rnc_data.get('nom_usage_copropriete')}'")
    print(f"  syndic              : '{rnc_data.get('nom_societe_mandataire')}'")
    print(f"  date_immatriculation : {rnc_data.get('date_immatriculation')}")
    print(f"  nb_lots_total       : {rnc_data.get('nombre_total_lots')}")
    print(f"  nb_lots_habit       : {rnc_data.get('nombre_lots_usage_habitation')}")
    print(f"  nb_lots_stat        : {rnc_data.get('nombre_lots_usage_stationnement')}")
    print(f"  adresse_reference   : '{rnc_data.get('adresse_reference')}'")
    print(f"  reference_cadastrale_1: '{rnc_data.get('reference_cadastrale_1')}'")
    print(f"  taux_rotation_an    : ? (a calculer make_light)")

print()
print("[OPERATION light.json] (4 modifications)")
print(f"  (A) INJECT coproprietes[] :")
print(f"      cle_adresse='{E5_ANCRE}', numero_immatriculation='{IMMAT_NEW}',")
print(f"      nom_copropriete='LE DAUPHINE', nb_lots_total=3, nb_lots_habitation=2, ...")
print(f"  (B) ATTRIBUER sur ad[{E5_ANCRE}] : propager immat/lots_habit/syndic/rotation")
print(f"  (C) RE-POINT ad[{E5_REPOINT}].batiment_groupe_id : '{bgid_20dp_avant}' -> '{bgid_stph}'")
print(f"      ad[{E5_REPOINT}]._fusion_cible : '{fa_cible_20dp_avant}' -> '{E5_ANCRE}'")
print(f"      ad[{E5_REPOINT}]._fusion_auto : True (deja True)")
print(f"  (D) LABEL ad[{E5_ANCRE}]._fusion_auto_label : -> '2 RUE ST PHILIPPE / 20 RUE DAUPHINE'")
print(f"      ad[{E5_ANCRE}]._fusion_auto_sources : -> ['20|RUE|DAUPHINE']")

print()
print("[OPERATION KV (side-effect post-fusion)]")
print(f"  KV[{E5_ANCRE}] = {{type:'mono'}} (SCI NSK) devient incoherent (cle devient RNC-immatriculee)")
print(f"  -> RECOMMANDATION : retirer 2 ST PHILIPPE du KV (sort du menu, devient copro RNC)")

# Simulation
by_cle_e5 = deepcopy(by_cle)
by_cle_e5[E5_REPOINT].update({
    "batiment_groupe_id": bgid_stph,
    "_fusion_cible": E5_ANCRE,
    "_fusion_auto": True,
})
by_cle_e5[E5_ANCRE].update({
    "_fusion_auto_label": "2 RUE ST PHILIPPE / 20 RUE DAUPHINE",
    "_fusion_auto_sources": [E5_REPOINT],
    "numero_immatriculation": IMMAT_NEW,
    "nb_lots_habitation": 2,
})

assigns_e5 = dict(assigns)
if E5_ANCRE in assigns_e5: del assigns_e5[E5_ANCRE]

print()
print("[APRES (simule)]")
print(f"  {snap_cle(E5_ANCRE, by_cle_e5)}")
print(f"  {snap_cle(E5_REPOINT, by_cle_e5)}")
print(f"  copros len : {len(co)} -> {len(co)+1}  (+1 INJECT {IMMAT_NEW})")
print(f"  KV total : {len(assigns)} -> {len(assigns_e5)} (-1, hygiene)")
print()
print("[DELTA]")
print(f"  - Parc UI       : 0 net (2 ST PHILIPPE bdnb=2 preserve, 20 DAUPH bdnb=9 reste sur LSG2 via 18 dauph,")
print(f"                       puis 20 DAUPH devient FA->2 ST PHILIPPE bgid NCPK, 18 DAUPH ancre garde son bgid LSG2)")
print(f"                    ATTENTION : verifier que 18 DAUPHINE n'est PAS impacte (il reste sur bgid LSG2 UZLIE)")
print(f"  - Light         : 1 INJECT copro + 1 ATTRIB immat + 1 RE-POINT bgid + 1 RE-FUSE + 1 label")
print(f"  - hr-ancres     : -1 (2 ST PHILIPPE passe en copro RNC)")
print(f"  - KV            : -1 (retire 2 ST PHILIPPE mono orphelin)")
print(f"  - Side effects  : 18 DAUPHINE perd 20 DAUPH dans son chain (etait FA src=['20|RUE|DAUPHINE']? a verifier)")

# Verification : 18 DAUPHINE est-il actuellement ancre de 20 ?
a_18dp = by_cle.get("18|RUE|DAUPHINE")
if a_18dp:
    sources_18 = a_18dp.get("_fusion_auto_sources") or []
    print(f"  - 18 DAUPHINE sources actuelles : {sources_18}")
    if E5_REPOINT in sources_18:
        new_sources = [s for s in sources_18 if s != E5_REPOINT]
        print(f"    -> 18 DAUPH._fusion_auto_sources : {sources_18} -> {new_sources}")
        if not new_sources:
            print(f"    -> 18 DAUPH._fusion_auto_label : retirer (plus de source FA)")

# ============================================================
# SYNTHESE FINALE
# ============================================================
print()
print("=" * 90)
print("SYNTHESE GLOBALE 4 DRY-RUNS")
print("=" * 90)
print(f"  E3 : KV +1   ({E3_CLE} -> copro_non_immat)             | delta parc :  0")
print(f"  E2 : light RE-POINT 233 PB                               | delta parc :  0")
print(f"  E4 : light RE-POINT+FUSE 6 MILIEU + KV -1                | delta parc : -{bdnb_6}")
print(f"  E5 : light INJECT + RE-POINT + FUSE + KV -1              | delta parc :  0")
print(f"  --")
print(f"  Light total    : 7 modifications dont 1 INJECT copro")
print(f"  KV total       : +1 -2 = -1 net (208 -> 207)")
print(f"  Parc UI total  : -{bdnb_6} lgts (E4 uniquement)")
print(f"  hr-ancres net  : -2 (E4: 6 MILIEU FA, E5: 2 ST PHILIPPE devient copro)")
print()
print(">>> AUCUNE MODIFICATION APPLIQUEE. Validation pour apply : -")
print("=" * 90)
