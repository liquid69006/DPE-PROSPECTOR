#!/usr/bin/env python3
"""KV DL micro-fix : 12B|RUE|GUILLOUD copro_non_immat -> bureaux.

Cas non-residentiel detecte lors du cross-check MAJIC des 9 candidats
mono potentiels :
  bdnb=None (=batiment non residentiel), MAJIC=117 lots PM repartis
  entre 2 SCI patrimoniales (SOCIETE CIVILE COURS GAMBETTA 57% +
  SANS SOUCI IMMOBILIER H E P S 43%). Probable immeuble de parkings
  ou locaux tertiaires lie au COURS GAMBETTA voisin.

Pattern PATCH unitaire calque sur _fix_reclass_5_social_dl.py.

Usage :
  python scripts/_fix_12b_guilloud_bureaux_dl.py <JWT_TOKEN>
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre12bguilloud.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CLE, TARGET = "12B|RUE|GUILLOUD", "bureaux"


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
print(f"KV DL micro-fix : {CLE} -> {TARGET}")
print("=" * 90)

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")

cur = assigns.get(CLE)
tag = (cur or {}).get("type")
print(f"  Etat actuel : {cur!r}")
if tag == TARGET:
    print(f">>> IDEMPOTENT : deja type={TARGET}")
    sys.exit(0)
if tag and tag != "copro_non_immat":
    fail(f"tag actuel = {tag!r}, attendu copro_non_immat ou vide")

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(f"  Backup KV local : {BAK.name}")

new_assigns = dict(assigns)
new_assigns[CLE] = {**(cur or {}), "type": TARGET}
print(f"  POST atomique ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
after = (kv_after.get("assignments") or {}).get(CLE)
if not after or after.get("type") != TARGET:
    fail(f"Verif KO : {after!r}")
print(f"  Verif post-PATCH : {after!r} OK")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")
print()
print("=" * 90)
print(f">>> SUCCES : {CLE} = {TARGET}, KV total = {len(kv_after.get('assignments') or {})}")
print("=" * 90)
