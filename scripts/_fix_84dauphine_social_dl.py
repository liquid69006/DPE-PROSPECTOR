#!/usr/bin/env python3
"""KV DL : CREATE tags social sur 84 + 84B RUE DU DAUPHINE.

Cross-check MAJIC : copro RNC AH1784180 '84 rue du Dauphine'
(syndic RHONE SAONE HABITAT, 60 lots hab) =>
  - 84 lots PM MAJIC repartis 98.8% IMMOBILIERE RHONE ALPES SA D'HLM
    (SIREN 398115808) + 1.2% RHONE-SAONE HABITAT (= le syndic).
  - 100% bailleur social (HLM), 0% PP, 0% prive => MEGA-bloc HLM pur.
  - Ratio MAJIC/BDNB = 1.4 (84 lots PM > 60 log BDNB) => bonne couverture.

Action : tagger '84|RUE|DAUPHINE' + '84B|RUE|DAUPHINE' en `social` dans
le KV (si les cles ne sont pas deja taggees). Effet UI : ces 2 adresses
seront exclues du marche logement marchand (getEffectiveLog=0).

Pattern PATCH atomique unique (CREATE multi-cles). Backup local.

Usage :
  python scripts/_fix_84dauphine_social_dl.py <JWT_TOKEN>
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre84dauphine.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CIBLES = [
    ("84|RUE|DAUPHINE",  "social"),
    ("84B|RUE|DAUPHINE", "social"),
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
print("KV DL : CREATE 84 + 84B RUE DU DAUPHINE -> social (MEGA-bloc HLM IRA)")
print("=" * 90)

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions")

print()
print("  Audit pre-CREATE :")
to_create = []
skip = []
for cle, target in CIBLES:
    cur = assigns.get(cle)
    tag = (cur or {}).get("type")
    if tag == target:
        print(f"    {cle:<25} SKIP (deja type={target})")
        skip.append(cle)
    elif tag:
        fail(f"CONFLIT : {cle} a tag actuel = {tag!r}, attendu vide ou {target}")
    else:
        print(f"    {cle:<25} CREATE type={target}")
        to_create.append((cle, target))

if not to_create:
    print(); print("=" * 90); print(">>> IDEMPOTENT"); print("=" * 90); sys.exit(0)

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(); print(f"  Backup KV local : {BAK.name}")

new_assigns = dict(assigns)
for cle, target in to_create:
    new_assigns[cle] = {**(assigns.get(cle) or {}), "type": target}
print()
print(f"  POST atomique (CREATE {len(to_create)} cle(s)) ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
errs = []
print()
print("  Verif post-CREATE :")
for cle, target in to_create:
    after = assigns_after.get(cle)
    if not after or after.get("type") != target:
        print(f"    {cle:<25} KO {after!r}"); errs.append(cle)
    else:
        print(f"    {cle:<25} OK type={target}")
if errs: fail(f"CREATE incomplet : {errs}")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : +{len(to_create)} tag(s) social, KV {len(assigns)} -> {len(assigns_after)} assigns")
print("=" * 90)
