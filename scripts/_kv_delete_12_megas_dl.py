#!/usr/bin/env python3
"""DELETE KV 12 megas DL : 8 cles devenues fauto qui avaient encore un tag."""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre12megas.bak")
ENDPOINT = "https://dpe-prospector-api.yann-bufferne.workers.dev/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

DELETE_CLES = {
    "177B|AVENUE|FELIX FAURE":   "copro_non_immat",
    "177T|AVENUE|FELIX FAURE":   "copro_non_immat",
    "64|AVENUE|LACASSAGNE":      "mono",
    "64B|AVENUE|LACASSAGNE":     "social",
    "5|RUE|ETIENNE RICHERAND":   "copro_non_immat",
    "9|RUE|FRANCOIS GILLET":     "copro_non_immat",
    "14|RUE|ETIENNE RICHERAND":  "copro_non_immat",
    "3|RUE|TEINTURIERS":         "copro_non_immat",
}


def http(method, url, headers=None, body=None):
    req = urllib.request.Request(
        url, method=method, headers=headers or {},
        data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print("!"*90); print(f"!  ECHEC : {msg}"); print("!"*90); sys.exit(10)


print("=" * 90)
print(f"KV DELETE x{len(DELETE_CLES)} : 12 megas DL")
print("=" * 90)

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}; fusions = kv.get("fusions") or {}; noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns, {len(fusions)} fusions")

to_delete = {}
for c, expected in DELETE_CLES.items():
    cur = assigns.get(c)
    print(f"  Etat : {c:38s} -> {cur}")
    if not cur:
        print(f"    [SKIP] absente"); continue
    t = cur.get("type") if isinstance(cur, dict) else None
    if t != expected:
        print(f"    [WARN] type={t!r}, attendu {expected!r} - delete quand meme")
    to_delete[c] = cur

if not to_delete: print("  Rien a supprimer."); sys.exit(0)

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK); print(f"  Backup : {BAK.name}")

new_assigns = {k: v for k, v in assigns.items() if k not in to_delete}
print(f"  Apres pop : {len(new_assigns)} assigns ({len(assigns) - len(new_assigns)} supprimees)")

code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw); assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
for c in to_delete:
    if c in assigns_after: fail(f"verif KO : {c} encore present")
    print(f"    {c:38s} -> ABSENTE OK")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV_LOCAL.name}")

from collections import Counter
co = Counter((v or {}).get("type", "?") for v in assigns_after.values())
print()
print("  Distribution KV apres :")
for k, v in co.most_common():
    print(f"    {k:20s} {v}")

print()
print("=" * 90)
print(f">>> SUCCES : {len(to_delete)} cles KV supprimees")
print("=" * 90)
