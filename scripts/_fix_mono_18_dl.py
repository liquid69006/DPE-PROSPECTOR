#!/usr/bin/env python3
"""Reclassement KV DL : PATCH 18 cles copro_non_immat -> mono.

Contexte : ces 18 adresses portent un flag KV `type=copro_non_immat`
alors que leur signature BDNB est manifestement mono-propriete :
nb_log_bdnb <= 2 ET (majoritairement) usage Residentiel individuel,
type_batiment=maison, annee_construction ancienne. Ce sont des
maisons individuelles ou des petites bi-prop, pas des copropriete
non immatriculee.

Dry-run prealable (cf conversation 2026-05-25) :
  18 entrees identifiees nb_log_bdnb <= 2 dans copro_non_immat ;
  16/18 sont Residentiel individuel maison/sans type ;
  2/18 sont Residentiel collectif bi-prop (13 METALLURGIE et
  81 RICHERAND) -- exclus de ce lot, traites separement.

Pattern standard (calque sur _fix_copronni_13bug_dl.py) :
  GET KV live -> audit coherence (tag = copro_non_immat) ->
  backup local .precopronni18mono.bak -> rebuild assignments avec
  type=mono sur les cibles (autres champs preserves via spread) ->
  POST atomique -> Re-GET verifier tag=mono -> sync local.

Idempotent : si une cle a deja type=mono ou tag != copro_non_immat,
elle est SKIP avec log. Si toutes deja propres -> exit 0.

Usage :
  python scripts/_fix_mono_18_dl.py <JWT_TOKEN>
  ou : DPE_TOKEN=<jwt> python scripts/_fix_mono_18_dl.py
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".precopronni18mono.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant (argv1 ou env)"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CIBLES = [
    "14|RUE|PREVOYANTS DE L AVENIR",
    "157|RUE|ANTOINE CHARIAL",
    "17|RUE|CLAUDIUS PIONCHON",
    "21|RUE|GUILLOUD",
    "225|AVENUE|FELIX FAURE",
    "22|RUE|GABILLOT",
    "25|RUE|DAUPHINE",
    "27|RUE|AUBIGNY",
    "27|RUE|DAUPHINE",
    "32|RUE|AUBIGNY",
    "33|AVENUE|LACASSAGNE",
    "34|RUE|STE ANNE DE BARABAN",
    "3|RUE|PETITES SOEURS",
    "40|RUE|STE ANNE DE BARABAN",
    "6|RUE|BARA",
    "6|RUE|PREVOYANTS DE L AVENIR",
    "8|RUE|ST PHILIPPE",
    "9|RUE|TUILIERS",
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
print("KV DL reclassement : PATCH 18 cles copro_non_immat -> mono (mono-prop nb_log_bdnb<=2)")
print("=" * 90)

# 1. GET KV live
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions, {len(noms)} noms")

print()
print("  Audit pre-PATCH (tag actuel doit etre copro_non_immat) :")
to_patch = []
skip = []
for cle in CIBLES:
    cur = assigns.get(cle)
    tag = (cur or {}).get("type")
    if not cur:
        print(f"    {cle:<40} -> SKIP (absent du KV)")
        skip.append((cle, "absente"))
    elif tag == "mono":
        print(f"    {cle:<40} -> SKIP (deja type=mono, idempotent)")
        skip.append((cle, "deja-mono"))
    elif tag != "copro_non_immat":
        print(f"    {cle:<40} -> SKIP (tag actuel = {tag!r}, attendu copro_non_immat)")
        skip.append((cle, f"tag-{tag}"))
    else:
        print(f"    {cle:<40} -> PATCH copro_non_immat -> mono  (preserve {sorted(k for k in cur if k != 'type')})")
        to_patch.append(cle)

if not to_patch:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : aucune cle a patcher (toutes deja propres ou tag divergent)")
    print("=" * 90)
    sys.exit(0)

# 2. Backup local
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

# 3. Rebuild assignments avec type=mono sur cibles (autres champs preserves)
new_assigns = dict(assigns)
for cle in to_patch:
    new_assigns[cle] = {**assigns[cle], "type": "mono"}
print()
print(f"  POST atomique (PATCH {len(to_patch)} cle(s) -> mono, KV {len(assigns)} assigns inchanges) ...")
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
print()
print("  Verif post-PATCH (tag attendu = mono, autres champs preserves) :")
errs = []
for cle in to_patch:
    before = assigns[cle]
    after  = assigns_after.get(cle)
    if not after:
        print(f"    {cle:<40} -> KO (disparue)")
        errs.append(cle)
        continue
    if after.get("type") != "mono":
        print(f"    {cle:<40} -> KO (type={after.get('type')!r})")
        errs.append(cle)
        continue
    # Verifier champs preserves (hors 'type')
    extras_before = {k: v for k, v in before.items() if k != "type"}
    extras_after  = {k: v for k, v in after.items()  if k != "type"}
    if extras_before == extras_after:
        print(f"    {cle:<40} -> OK type=mono, {len(extras_after)} champ(s) preserve(s)")
    else:
        print(f"    {cle:<40} -> WARN type=mono mais champs differents (before={extras_before}, after={extras_after})")
if errs: fail(f"PATCH incomplet : {errs}")

# 5. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : {len(to_patch)} cle(s) reclassees mono")
if skip:
    print(f">>> {len(skip)} cle(s) skip : {[(k, r) for k, r in skip]}")
print("=" * 90)
