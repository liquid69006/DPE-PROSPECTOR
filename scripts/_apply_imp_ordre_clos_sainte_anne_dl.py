#!/usr/bin/env python3
"""Apply RE-FUSE 7/9/11 IMP ORDRE -> 118 BARABAN (LE CLOS SAINTE ANNE).

Operations :
  (A) light : 3 cles 7/9/11 IMP ORDRE
        - propagation immat AB8922999 + lots 49 + syndic REGIE POZETTO + taux/classement
        - bgid alignment -> AGDC-W8DF-4GCQ
        - _fusion_auto=True, _fusion_cible='118|RUE|BARABAN'
        - tag _correctif_imp_ordre
  (B) light : 118 BARABAN
        - _fusion_auto_label = '118 RUE BARABAN / 7/9/11 IMPASSE DE L ORDRE'
        - _fusion_auto_sources = [3 cles IMP]
  (C) KV : DELETE 3 cles IMP ORDRE
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK_L = LIGHT.with_suffix(LIGHT.suffix + ".preimporder.bak")
BAK_KV = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".preimporder.bak")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CLES_IMP = ["7|IMPASSE|ORDRE", "9|IMPASSE|ORDRE", "11|IMPASSE|ORDRE"]
PARENT = "118|RUE|BARABAN"
IMMAT_CLOS = "AB8922999"
TARGET_BGID = "bdnb-bg-AGDC-W8DF-4GCQ"
NEW_LABEL = "118 RUE BARABAN / 7/9/11 IMPASSE DE L ORDRE"
MARKER = "fix_imp_ordre_clos_sainte_anne_2026-05-23"

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def fail(msg):
    print(); print("!"*90); print(f"!  ECHEC : {msg}"); print("!"*90); sys.exit(10)

# Backups
print("=" * 90)
print("APPLY RE-FUSE 7/9/11 IMP ORDRE -> 118 BARABAN (LE CLOS SAINTE ANNE)")
print("=" * 90)
shutil.copy2(LIGHT, BAK_L)
print(f"  Backup light : {BAK_L.name}")
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK_KV)
    print(f"  Backup KV    : {BAK_KV.name}")

# Charger copro mere pour propagation
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
N_AD0 = len(doc["adresses"])
N_CO0 = len(doc["coproprietes"])
co_clos = next((c for c in doc["coproprietes"]
                if c.get("numero_immatriculation") == IMMAT_CLOS), None)
if not co_clos: fail(f"Copro {IMMAT_CLOS} introuvable")

# Champs a propager
HAB = co_clos.get("nb_lots_habitation")
TAUX = co_clos.get("taux_rotation_5ans")
CLS = co_clos.get("classement_rotation")
SYNDIC = co_clos.get("syndic")
SYN_SRC = co_clos.get("_syndic_src")
print()
print(f"  Copro mere {IMMAT_CLOS} '{co_clos.get('nom_copropriete')}'")
print(f"    hab={HAB} taux={TAUX} class={CLS!r} syndic={SYNDIC!r} src={SYN_SRC!r}")

# (A) Modif 3 cles IMP ORDRE
print()
print("[A] LIGHT propag + RE-FUSE sur 3 cles IMP ORDRE")
n_modif = 0
for cle in CLES_IMP:
    a = next((x for x in doc["adresses"] if x.get("cle") == cle), None)
    if not a: fail(f"Cle absente light : {cle}")
    old_bgid = a.get("batiment_groupe_id")
    a["numero_immatriculation"] = IMMAT_CLOS
    a["nb_lots_habitation"] = HAB
    a["taux_rotation"] = TAUX
    a["classement_rotation"] = CLS
    a["syndic"] = SYNDIC
    a["_syndic_src"] = SYN_SRC
    a["batiment_groupe_id"] = TARGET_BGID
    a["_fusion_auto"] = True
    a["_fusion_cible"] = PARENT
    a["_correctif_imp_ordre"] = MARKER
    n_modif += 1
    print(f"  OK  {cle:30s}  bgid {old_bgid} -> {TARGET_BGID}")

# (B) Modif PARENT 118 BARABAN
print()
print(f"[B] LIGHT label/sources sur {PARENT}")
a_par = next((x for x in doc["adresses"] if x.get("cle") == PARENT), None)
if not a_par: fail(f"Parent {PARENT} introuvable")
old_label = a_par.get("_fusion_auto_label") or ""
old_sources = list(a_par.get("_fusion_auto_sources") or [])
a_par["_fusion_auto_label"] = NEW_LABEL
a_par["_fusion_auto_sources"] = list(old_sources) + CLES_IMP
a_par["_correctif_imp_ordre"] = MARKER
print(f"  label   : {old_label!r} -> {NEW_LABEL!r}")
print(f"  sources : {old_sources} -> {a_par['_fusion_auto_sources']}")

# Ecriture light
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print()
print(f"  Ecriture light.json OK")

# Verif post-write
doc_chk = json.loads(LIGHT.read_text(encoding="utf-8"))
if len(doc_chk["adresses"]) != N_AD0: fail(f"count adresses change")
if len(doc_chk["coproprietes"]) != N_CO0: fail(f"count copros change")
for cle in CLES_IMP:
    a = next((x for x in doc_chk["adresses"] if x.get("cle") == cle), None)
    if not a: fail(f"Cle disparue post-write : {cle}")
    if a.get("numero_immatriculation") != IMMAT_CLOS: fail(f"{cle} immat KO")
    if a.get("_fusion_cible") != PARENT: fail(f"{cle} cible KO")
    if a.get("batiment_groupe_id") != TARGET_BGID: fail(f"{cle} bgid KO")
    if not a.get("_fusion_auto"): fail(f"{cle} FA KO")
a_par_chk = next((x for x in doc_chk["adresses"] if x.get("cle") == PARENT), None)
if a_par_chk.get("_fusion_auto_label") != NEW_LABEL: fail(f"118 BARABAN label KO")
print(f"  Verif post-write : 3 cles IMP + 1 parent OK")

# (C) KV DELETE
print()
print(f"[C] KV DELETE 3 cles IMP ORDRE")
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
new_assigns = {k: v for k, v in assigns.items() if k not in CLES_IMP}
n_deletes = len(assigns) - len(new_assigns)
print(f"  Cles a supprimer : {n_deletes}")
for cle in CLES_IMP:
    if cle in assigns: print(f"    DELETE {cle:30s} (etait {assigns[cle]})")

if n_deletes == 0:
    print(f"  IDEMPOTENT : aucune des 3 cles dans KV")
else:
    code, raw = http("POST", ENDPOINT, HDR_POST, body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
    print(f"  POST HTTP {code} : {raw[:160]}")
    if code not in (200, 204): fail(f"POST KO")
    # Re-GET verif
    code, raw = http("GET", ENDPOINT, HDR_GET)
    if code != 200: fail(f"Re-GET {code}")
    kv_after = json.loads(raw)
    assigns_after = kv_after.get("assignments") or {}
    for cle in CLES_IMP:
        if cle in assigns_after:
            fail(f"DELETE echoue : {cle} encore dans KV")
    print(f"  KV apres : {len(assigns_after)} assigns")
    print(f"  Verif : 3 cles IMP ORDRE absentes  OK")
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Local sync : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> APPLY OK")
print(f"    light : 3 cles (8-9 champs) + 1 parent (label/sources)")
print(f"    KV    : -{n_deletes} DELETE")
print(f"    Backups : {BAK_L.name}, {BAK_KV.name}")
print(f"    Commit a faire par orchestrateur. PAS DE PUSH.")
print("=" * 90)
