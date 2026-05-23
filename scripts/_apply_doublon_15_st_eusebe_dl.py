#!/usr/bin/env python3
"""Apply RE-FUSE 15 IMPASSE ST EUSEBE -> 15 RUE ST EUSEBE.

Confirmation terrain : meme immeuble physique, BDNB a dedouble en 2 bgids.

Operations :
  1. light : 15 IMPASSE  _fusion_auto=True, _fusion_cible='15|RUE|ST EUSEBE'
            bgid VC2S-BT7D-ZQ25 -> H9T9-DYCH-XSSS (= 12/15 RUE)
            tag _correctif_doublon_eusebe
  2. KV    : DELETE 15|IMPASSE|ST EUSEBE
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK_L = LIGHT.with_suffix(LIGHT.suffix + ".predoublon15eusebe.bak")
BAK_KV = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".predoublon15eusebe.bak")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

ORPHAN = "15|IMPASSE|ST EUSEBE"
PARENT = "15|RUE|ST EUSEBE"
TARGET_BGID = "bdnb-bg-H9T9-DYCH-XSSS"
MARKER = "fix_doublon_15_st_eusebe_2026-05-23"

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

# ============================================================
# 1. Backups
# ============================================================
print("=" * 90)
print("APPLY RE-FUSE 15 IMPASSE -> 15 RUE ST EUSEBE")
print("=" * 90)
shutil.copy2(LIGHT, BAK_L)
print(f"  Backup light : {BAK_L.name}")
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK_KV)
    print(f"  Backup KV    : {BAK_KV.name}")

# ============================================================
# 2. Modif light
# ============================================================
print()
print("[1] LIGHT modifs")
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
N_AD0 = len(doc["adresses"])
N_CO0 = len(doc["coproprietes"])

found = False
for a in doc["adresses"]:
    if a.get("cle") == ORPHAN:
        old_bgid = a.get("batiment_groupe_id")
        a["batiment_groupe_id"] = TARGET_BGID
        a["_fusion_auto"] = True
        a["_fusion_cible"] = PARENT
        a["_correctif_doublon_eusebe"] = MARKER
        found = True
        print(f"  {ORPHAN} :")
        print(f"    bgid {old_bgid} -> {TARGET_BGID}")
        print(f"    _fusion_auto -> True")
        print(f"    _fusion_cible -> {PARENT!r}")
        print(f"    _correctif_doublon_eusebe -> {MARKER!r}")
        break
if not found: fail(f"Cle {ORPHAN} absente light")

# Verifier 12 RUE et 15 RUE intacts (lecture)
chk_12 = next((a for a in doc["adresses"] if a.get("cle") == "12|RUE|ST EUSEBE"), None)
chk_15r = next((a for a in doc["adresses"] if a.get("cle") == "15|RUE|ST EUSEBE"), None)
if not chk_12 or not chk_15r: fail("12 RUE ou 15 RUE introuvable")
print(f"  12 RUE ST EUSEBE intacte : bgid {chk_12.get('batiment_groupe_id')!r} label {chk_12.get('_fusion_auto_label')!r}")
print(f"  15 RUE ST EUSEBE intacte : bgid {chk_15r.get('batiment_groupe_id')!r} FA={chk_15r.get('_fusion_auto')} cible={chk_15r.get('_fusion_cible')!r}")

# Ecriture
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f"  Ecriture light.json OK")

# Verif post-write
doc_chk = json.loads(LIGHT.read_text(encoding="utf-8"))
if len(doc_chk["adresses"]) != N_AD0: fail(f"count adresses change {N_AD0}->{len(doc_chk['adresses'])}")
if len(doc_chk["coproprietes"]) != N_CO0: fail(f"count copros change")
a_orph_chk = next((a for a in doc_chk["adresses"] if a.get("cle") == ORPHAN), None)
if not a_orph_chk: fail(f"{ORPHAN} disparu post-write")
if a_orph_chk.get("_fusion_cible") != PARENT: fail(f"cible incorrect : {a_orph_chk.get('_fusion_cible')}")
if not a_orph_chk.get("_fusion_auto"): fail(f"FA non True")
if a_orph_chk.get("batiment_groupe_id") != TARGET_BGID: fail(f"bgid incorrect")
if a_orph_chk.get("_correctif_doublon_eusebe") != MARKER: fail(f"marker absent")
print(f"  Verif post-write : 4 champs OK")

# ============================================================
# 3. KV DELETE
# ============================================================
print()
print("[2] KV DELETE")
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
print(f"  KV[{ORPHAN}] avant : {assigns.get(ORPHAN)}")
if ORPHAN not in assigns:
    print(f"  IDEMPOTENT : {ORPHAN} deja absent du KV")
else:
    new_assigns = {k: v for k, v in assigns.items() if k != ORPHAN}
    code, raw = http("POST", ENDPOINT, HDR_POST, body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
    print(f"  POST HTTP {code} : {raw[:160]}")
    if code not in (200, 204): fail(f"POST KO {code}")
    # Re-GET verif
    code, raw = http("GET", ENDPOINT, HDR_GET)
    if code != 200: fail(f"Re-GET {code}")
    kv_after = json.loads(raw)
    assigns_after = kv_after.get("assignments") or {}
    if ORPHAN in assigns_after: fail(f"DELETE echoue : {ORPHAN} toujours present")
    print(f"  KV apres : {len(assigns_after)} assigns")
    print(f"  Verif : {ORPHAN} absent  OK")
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Local sync : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> APPLY OK")
print(f"    light : 1 cle modifiee (15 IMPASSE), 4 champs")
print(f"    KV    : -1 assign (DELETE)")
print(f"    Backups : {BAK_L.name}, {BAK_KV.name}")
print(f"    Commit a faire par orchestrateur. PAS DE PUSH.")
print("=" * 90)
