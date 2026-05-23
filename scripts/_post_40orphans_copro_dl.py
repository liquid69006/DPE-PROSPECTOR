#!/usr/bin/env python3
"""POST batch KV - 40 orphans BDNB DL -> copro_non_immat.

Source : light.adresses avec _injection_bdnb_orphelin marker.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre40orphans.bak")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

ORPHAN_MARKER = "fix_bdnb_orphelin_dl_2026-05-23"
TARGET = "copro_non_immat"

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

# --- Build PLAN from light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
PLAN = sorted([a.get("cle") for a in doc["adresses"]
               if a.get("_injection_bdnb_orphelin") == ORPHAN_MARKER and a.get("cle")])
print("=" * 90)
print(f"POST batch 40 orphans BDNB -> '{TARGET}'")
print("=" * 90)
print(f"  Plan : {len(PLAN)} cles (attendu 40)")
if len(PLAN) != 40:
    fail(f"Compte plan inattendu : {len(PLAN)} != 40")

# --- GET KV ---
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(f"  Backup local : {BAK.name}")

# --- Merge ---
new_assigns = dict(assigns)
already, overrides, new = [], [], []
for cle in PLAN:
    cur = new_assigns.get(cle)
    if cur and isinstance(cur, dict) and cur.get("type") == TARGET:
        already.append(cle)
    elif cur:
        overrides.append((cle, cur.get("type")))
        new_assigns[cle] = {"type": TARGET}
    else:
        new.append(cle)
        new_assigns[cle] = {"type": TARGET}
print(f"  Deja en KV (skip) : {len(already)}")
print(f"  Overrides type    : {len(overrides)}")
for cle, cur in overrides[:5]: print(f"    - {cle:36s} {cur} -> {TARGET}")
print(f"  Nouvelles cles    : {len(new)}")
print(f"  Total apres merge : {len(new_assigns)}  (avant {len(assigns)})")

# --- POST ---
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:160]}")
if code not in (200, 204): fail(f"POST KO {code}")

# --- Re-GET verif ---
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns (attendu {len(new_assigns)})")
ok = 0; missing = []; wrong = []
for cle in PLAN:
    cur = assigns_after.get(cle)
    if not cur: missing.append(cle)
    elif (cur.get("type") if isinstance(cur, dict) else None) != TARGET:
        wrong.append((cle, cur))
    else: ok += 1
print(f"  Verif : {ok}/{len(PLAN)} OK")
for c in missing: print(f"    KO manquant - {c}")
for c, cur in wrong: print(f"    KO mauv.type - {c} -> {cur}")
if missing or wrong: fail(f"verif : {len(missing)} manquants, {len(wrong)} mauvais type")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV_LOCAL.name}")
print()
print("=" * 90)
print(f">>> SUCCES : {ok}/{len(PLAN)} cles '{TARGET}' confirmees")
print(f"    KV : {len(assigns)} -> {len(assigns_after)} (+{len(assigns_after)-len(assigns)})")
print("=" * 90)
