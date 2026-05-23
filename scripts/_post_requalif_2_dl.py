#!/usr/bin/env python3
"""POST 2 requalifications KV DL :
  - 84B|RUE|DAUPHINE : (non qualifie) -> copro_non_immat
  - 80B|RUE|ANTOINE CHARIAL : social -> copro_non_immat (override)

Justification : ventes individuelles DVF actives malgre rattachement RNC
bailleur social. Probable desengagement parc / SDC mixte.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".prerequalif2.bak")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

PLAN = [
    ("84B|RUE|DAUPHINE", "copro_non_immat"),
    ("80B|RUE|ANTOINE CHARIAL", "copro_non_immat"),
]

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

# GET
print("=" * 90)
print("POST 2 requalifications KV DL")
print("=" * 90)
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: print(f"GET KO {code}: {raw[:200]}"); sys.exit(3)
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(f"  Backup : {BAK.name}")

# Merge
new_assigns = dict(assigns)
for cle, typ in PLAN:
    cur = new_assigns.get(cle)
    if cur and isinstance(cur, dict):
        prev = cur.get("type")
        if prev == typ:
            print(f"  IDEMPOTENT : {cle} deja {typ}")
        else:
            print(f"  OVERRIDE   : {cle} {prev} -> {typ}")
            new_assigns[cle] = {"type": typ}
    else:
        print(f"  NEW        : {cle} -> {typ}")
        new_assigns[cle] = {"type": typ}

# POST
code, raw = http("POST", ENDPOINT, HDR_POST, body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:160]}")
if code not in (200, 204): sys.exit(4)

# Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: print(f"Re-GET KO"); sys.exit(5)
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  KV apres : {len(assigns_after)} assigns")
ok = 0
for cle, typ in PLAN:
    cur = assigns_after.get(cle)
    if cur and isinstance(cur, dict) and cur.get("type") == typ:
        ok += 1
        print(f"  OK  {cle:34s} -> {cur}")
    else:
        print(f"  KO  {cle:34s} -> {cur}")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV_LOCAL.name}")
print()
print("=" * 90)
print(f">>> {'SUCCES' if ok == len(PLAN) else 'ECHEC PARTIEL'} : {ok}/{len(PLAN)} requalifications confirmees")
print(f"    KV : {len(assigns)} -> {len(assigns_after)}")
print("=" * 90)
