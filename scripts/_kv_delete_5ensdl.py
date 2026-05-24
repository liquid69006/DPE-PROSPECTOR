#!/usr/bin/env python3
"""DELETE KV 'copro_non_immat' sur 3 cles devenues FA dans 5 ensembles DL.

Cles : 15 RICHERAND (FIX 1) / 125 DAUPHINE (FIX 2) / 7 METALLURGIE (FIX 3).
Procedure : GET KV live -> verif type=copro_non_immat -> pop 3 cles
-> POST atomique -> Re-GET verif -> sync local.
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre5ensdl.bak")
API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

DELETE_CLES = [
    "15|RUE|ETIENNE RICHERAND",
    "125|RUE|DAUPHINE",
    "7|RUE|METALLURGIE",
]


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
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


print("=" * 90)
print(f"KV DELETE x3 : 5 ensembles DL  (15 RICHERAND, 125 DAUPHINE, 7 METAL)")
print("=" * 90)

# 1. GET KV live
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns, {len(fusions)} fusions")

# 2. Verif etats actuels
to_delete = {}
for c in DELETE_CLES:
    cur = assigns.get(c)
    print(f"  Etat : {c:38s} -> {cur}")
    if not cur:
        print(f"    [SKIP] absente (deja supprimee?)")
        continue
    t = cur.get("type") if isinstance(cur, dict) else None
    if t != "copro_non_immat":
        print(f"    [WARN] type={t!r}, attendu 'copro_non_immat' - delete quand meme")
    to_delete[c] = cur

if not to_delete:
    print("  Rien a supprimer.")
    sys.exit(0)

# 3. Backup local
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(f"  Backup : {BAK.name}")

# 4. Pop
new_assigns = {k: v for k, v in assigns.items() if k not in to_delete}
print(f"  Apres pop : {len(new_assigns)} assigns ({len(assigns) - len(new_assigns)} supprimees)")

# 5. POST
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

# 6. Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
for c in to_delete:
    if c in assigns_after:
        fail(f"verif KO : {c} encore present apres POST")
    print(f"    {c:38s} -> ABSENTE OK")

# 7. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV_LOCAL.name}")

# 8. Distribution
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
