#!/usr/bin/env python3
"""DELETE KV vague 4 DL : 3 RUE BARA (copro_non_immat -> fauto)."""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV   = ROOT / "data" / "_kv_assign_dl.json"
BAK  = KV.with_suffix(KV.suffix + ".prev4.bak")
ENDPOINT = "https://dpe-prospector-api.yann-bufferne.workers.dev/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

DELETE = {"3|RUE|BARA": "copro_non_immat"}


def http(m, u, h=None, b=None):
    req = urllib.request.Request(u, method=m, headers=h or {},
        data=(json.dumps(b).encode("utf-8") if b is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print("!"*90); print(f"!  ECHEC : {msg}"); print("!"*90); sys.exit(10)


print("=" * 90); print(f"KV DELETE x{len(DELETE)} : vague 4 DL"); print("=" * 90)
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}; fusions = kv.get("fusions") or {}; noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")

to_del = {}
for c, exp in DELETE.items():
    cur = assigns.get(c)
    print(f"  Etat : {c:38s} -> {cur}")
    if not cur: print("    [SKIP]"); continue
    t = cur.get("type") if isinstance(cur, dict) else None
    if t != exp: print(f"    [WARN] type={t!r}, attendu {exp!r}")
    to_del[c] = cur

if not to_del: print("  Rien"); sys.exit(0)
if KV.exists(): shutil.copy2(KV, BAK); print(f"  Backup : {BAK.name}")

new_a = {k: v for k, v in assigns.items() if k not in to_del}
code, raw = http("POST", ENDPOINT, HDR_POST,
                 {"assignments": new_a, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
ka = json.loads(raw).get("assignments") or {}
print(f"  Re-GET : {len(ka)} assigns")
for c in to_del:
    if c in ka: fail(f"verif KO : {c} present")
    print(f"    {c:38s} -> ABSENTE OK")

KV.write_text(json.dumps(json.loads(raw), ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV.name}")

from collections import Counter
co = Counter((v or {}).get("type", "?") for v in ka.values())
print()
print("  Distribution KV apres :")
for k, v in co.most_common(): print(f"    {k:20s} {v}")
print()
print(f">>> SUCCES : {len(to_del)} cle supprimee")
