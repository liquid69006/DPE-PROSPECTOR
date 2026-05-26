#!/usr/bin/env python3
"""Canary test : POST seul 1|RUE|VILLETTE -> mono, re-GET cette cle.

Avant le batch complet de 34 patches, on teste sur 1 cle :
  - GET KV live
  - Set assigns['1|RUE|VILLETTE'] = {'type': 'mono'}
  - POST atomique
  - Re-GET la cle seule
  - Display + STOP (attendre 'ok suite' user)

JWT lu depuis env var DPE_JWT (pas hardcode). PYTHONUTF8=1, ASCII-safe.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

JWT = os.environ.get("DPE_JWT")
if not JWT:
    sys.exit("  [abort] env var DPE_JWT absente.")

CLE = "1|RUE|VILLETTE"
NEW_TYPE = "mono"


def kv_req(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {JWT}",
        "User-Agent": UA,
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


print("=" * 70)
print(f"CANARY KV PATCH : {CLE} -> {NEW_TYPE}")
print("=" * 70)

# 1. GET
print("\n[GET] etat live KV cloud...")
st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
if st != 200:
    sys.exit(f"  GET err: status={st} body={body}")
assigns = body.get("assignments") or {}
fusions = body.get("fusions") or {}
noms = body.get("noms") or {}
print(f"  assignments={len(assigns)}  fusions={len(fusions)}  noms={len(noms)}")
print(f"  AVANT : {CLE} -> {assigns.get(CLE)}")

# 2. Audit : verifier que c'est patchable
cur = assigns.get(CLE) or {}
cur_t = cur.get("type") or ""
if cur_t not in ("", "copro_non_immat"):
    sys.exit(f"  [abort] {CLE} a deja un tag non patchable : '{cur_t}'")

# 3. Set + POST
assigns[CLE] = {"type": NEW_TYPE}
print(f"\n[POST] atomique (1 changement)...")
st, body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                  {"assignments": assigns, "fusions": fusions, "noms": noms})
print(f"  status={st}  body={body}")
if st != 200:
    sys.exit("  POST echec")

# 4. Re-GET cette cle
print(f"\n[Re-GET] verification {CLE}...")
st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
if st != 200:
    sys.exit(f"  Re-GET err: {body}")
a2 = body.get("assignments") or {}
v = a2.get(CLE)
ok = bool(v) and v.get("type") == NEW_TYPE
flag = "OK" if ok else "FAIL"
print(f"  [{flag}] {CLE} -> {v}  (attendu type='{NEW_TYPE}')")

if not ok:
    sys.exit("  [abort] persistance KV non confirmee.")

# 5. Maj cache local
if KV_LOCAL.exists():
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
else:
    kv_local = {"assignments": {}}
kv_local.setdefault("assignments", {})
kv_local["assignments"][CLE] = {"type": NEW_TYPE}
KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                    encoding="utf-8")
print(f"  [local] {KV_LOCAL.name} mis a jour ({len(kv_local['assignments'])} assigns)")

print()
print("=" * 70)
print(f"CANARY REUSSI : {CLE} = {NEW_TYPE} persiste.")
print("STOP. Attendre 'ok suite' avant le batch complet des 33 autres.")
print("=" * 70)
