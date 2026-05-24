#!/usr/bin/env python3
"""DELETE KV : 20B|AVENUE|LACASSAGNE (tag 'copro_non_immat' incorrect).

Justification : la cle '20B|AVENUE|LACASSAGNE' porte deja l'immat RNC
AD5268305 (= SDC BRICKS 1, 98 lots_hab) -- le tag KV 'copro_non_immat'
est donc faux (c'est une copro IMMATRICULEE RNC).

Note terrain : la fusion 22|AVENUE|LACASSAGNE -> 20B|AVENUE|LACASSAGNE
reste LEGITIME (PV AG officiel confirme que 22+22BIS LACASSAGNE font
partie de BRICKS 1, malgre le bgid BDNB different 9DFR-GCRL-WUGG
attribue a tort par make_light). On ne touche pas a cette fusion.

GET KV live -> verifier tag present -> rebuild assignments sans la cle
-> POST atomique -> Re-GET verifier absence -> sync local KV.

Idempotent : si deja absente, n'ecrit rien et exit 0.
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".predel20blacassagne.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CLE = "20B|AVENUE|LACASSAGNE"


def http(method, url, headers, body=None):
    req = urllib.request.Request(
        url, method=method, headers=headers,
        data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


print("=" * 90)
print(f"DELETE KV : {CLE} (tag 'copro_non_immat' incorrect, immat AD5268305 existe)")
print("=" * 90)

# 1. GET KV
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")

cur = assigns.get(CLE)
print(f"  Etat actuel : {CLE!r} -> {cur!r}")
if cur is None:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : la cle est deja absente du KV, rien a faire")
    print("=" * 90)
    sys.exit(0)

# 2. Backup
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(f"  Backup : {BAK.name}")

# 3. POST atomique
new_assigns = {k: v for k, v in assigns.items() if k != CLE}
print(f"  POST atomique : {len(assigns)} -> {len(new_assigns)} (DELETE 1)")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

# 4. Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
if CLE in assigns_after:
    fail(f"DELETE KO : {CLE!r} encore present {assigns_after[CLE]!r}")
print(f"  Verif : {CLE!r} absent post-POST  OK")

# 5. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : KV {len(assigns)} -> {len(assigns_after)} (DELETE 1)")
print("=" * 90)
