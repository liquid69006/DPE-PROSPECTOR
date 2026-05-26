#!/usr/bin/env python3
"""KV PATCH 132|RUE|BARABAN -> social (post fix-132-baraban).

Suite a l analyse MAJIC parcelle DS0046 : 100% bail emphyteotique HLM
(21 lots GRANDLYON HABITAT emphyteote sur 21 lots propriete METROPOLE).
Cf metadata._correctif_132_baraban (commit 491c359).

POST atomique + Re-GET verif + maj cache local _kv_assign_dl.json.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
JWT = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
       "eyJhZ2VuY2UiOiJkYXVwaGluZS1sYWNhc3NhZ25lIiwiYWdlbmNlcyI6WyJkYXVwaGluZS1sYWNhc3NhZ25lIl0sInJvbGUiOiJwYXRyb24iLCJleHAiOjE3Nzk4MzExOTM0NDV9."
       "VwaMO5jqFtDtZ4L_5SACyom2ehgmSJ-kauLhFwA55pE")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

CIBLE = "132|RUE|BARABAN"


def req(method, path, body=None):
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
print(f"KV PATCH : {CIBLE} -> social")
print("=" * 70)

print("\n[GET] etat actuel...")
st, body = req("GET", f"/secteur-assignments/{AGENCE}")
print(f"  status={st}")
if st != 200:
    sys.exit(f"  GET err: {body}")
assigns = body.get("assignments") or {}
fusions = body.get("fusions") or {}
noms = body.get("noms") or {}
print(f"  assignments={len(assigns)} fusions={len(fusions)} noms={len(noms)}")
print(f"  AVANT : {CIBLE} -> {assigns.get(CIBLE)}")

assigns[CIBLE] = {"type": "social"}

print("\n[POST] atomique...")
st, body = req("POST", f"/secteur-assignments/{AGENCE}",
               {"assignments": assigns, "fusions": fusions, "noms": noms})
print(f"  status={st} body={body}")
if st != 200:
    sys.exit("  POST KV echec")

print("\n[Re-GET] verif...")
st, body = req("GET", f"/secteur-assignments/{AGENCE}")
if st != 200:
    sys.exit("  Re-GET KV echec")
a2 = body.get("assignments") or {}
v = a2.get(CIBLE)
ok = bool(v) and v.get("type") == "social"
print(f"  [VERIF] {CIBLE} -> {v}  [{'OK' if ok else 'FAIL'}]")
if not ok:
    sys.exit("  KV verif echec")

# Cache local
if KV_LOCAL.exists():
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
else:
    kv_local = {"assignments": {}}
kv_local.setdefault("assignments", {})
kv_local["assignments"][CIBLE] = {"type": "social"}
KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                    encoding="utf-8")
print(f"\n  Local KV mis a jour : {KV_LOCAL.name} "
      f"({len(kv_local['assignments'])} assignments total)")

print()
print("=" * 70)
print("KV PATCH 132 BARABAN -> social REUSSI.")
print("=" * 70)
