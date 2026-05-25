#!/usr/bin/env python3
"""Cleanup KV DL : DELETE 13 cles copro_non_immat OBSOLETES.

Contexte : ces 13 B-suffixes ont une `numero_immatriculation` dans le
light JSON (rattaches a une vraie copro RNC), mais portent encore le
flag KV `type=copro_non_immat`. Le flag est donc obsolete -- l'UI
les affichera comme copros RNC normales une fois le KV supprime.

Dry-run prealable confirme par cartographie (cf conversation 2026-05-25) :
toutes 13 sont rattachees a une copro RNC immatriculee avec nom + syndic
present dans le snapshot light.

Pattern standard (cf _kv_delete_26b_14b_dl.py) :
  GET KV live -> backup local -> rebuild assignments sans cles ->
  POST atomique -> Re-GET verifier absence -> sync local.

Idempotent : si une cle est deja absente ou tag != copro_non_immat,
elle est ignoree (audit pre-POST). Si TOUTES deja propres, exit 0.

Usage :
  python scripts/_fix_copronni_13bug_dl.py <JWT_TOKEN>
  ou : DPE_TOKEN=<jwt> python scripts/_fix_copronni_13bug_dl.py
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".precopronni13.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant (argv1 ou env)"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

# 13 B-suffixes a nettoyer, avec leur immat attendue (verification de coherence
# pre-DELETE : si l'immat KV ne matche pas le light actuel, on n'efface pas).
CIBLES = [
    ("10B|RUE|FREDERIC MISTRAL",          "AA1991173"),    # CLOS MISTRAL
    ("11B|RUE|PROFESSEUR PAUL SISLEY",    "AA0012898"),    # ATRIUM SISLEY
    ("11B|RUE|ST MAXIMIN",                "AB4738928"),    # SDC LE CARRE DES LYS
    ("130B|RUE|BARABAN",                  "AE1293612"),    # SOPHIA
    ("191B|AVENUE|FELIX FAURE",           "AI6510671"),    # RESIDENCE ARTY
    ("19B|RUE|ST ANTOINE",                "AA3187663"),    # LE SAINT ANTOINE
    ("4B|RUE|DAVID",                      "AB8779696"),    # CLOS DE L'ISLE
    ("6B|RUE|STE ANNE DE BARABAN",        "AE4069597"),    # LE NIVOLET
    ("84B|RUE|DAUPHINE",                  "AH1784180"),    # 84 rue du Dauphine
    ("8B|RUE|DAVID",                      "AB8779696"),    # CLOS DE L'ISLE
    ("9B|RUE|PROFESSEUR PAUL SISLEY",     "AA0012898"),    # ATRIUM SISLEY
    ("9Q|RUE|MONTBRILLANT",               "AB6211445"),    # PRIVILEGE MONTBRILLANT A
    ("9T|RUE|MONTBRILLANT",               "AB6211445"),    # PRIVILEGE MONTBRILLANT A
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
print("KV DL cleanup : DELETE 13 cles copro_non_immat OBSOLETES (B-suffixes rattaches RNC)")
print("=" * 90)

# 1. GET KV live + light pour verif coherence
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions")

light_path = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
light = json.loads(light_path.read_text(encoding="utf-8"))
adr_by_cle = {(a.get("cle") or ""): a for a in (light.get("adresses") or [])}

print()
print("  Audit pre-DELETE (presence KV + coherence immat light) :")
to_delete = []
skip = []
for cle, immat_attendu in CIBLES:
    cur = assigns.get(cle)
    a   = adr_by_cle.get(cle) or {}
    light_immat = a.get("numero_immatriculation")
    tag = (cur or {}).get("type")
    if tag != "copro_non_immat":
        print(f"    {cle:<37} -> SKIP (tag KV actuel = {tag!r})")
        skip.append((cle, "tag-non-copronni"))
        continue
    if light_immat != immat_attendu:
        print(f"    {cle:<37} -> SKIP (light immat = {light_immat!r}, attendu {immat_attendu})")
        skip.append((cle, "immat-divergente"))
        continue
    print(f"    {cle:<37} -> DELETE  (immat {immat_attendu} confirme dans light)")
    to_delete.append(cle)

if not to_delete:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : aucune cle a supprimer (toutes deja propres ou divergentes)")
    print("=" * 90)
    sys.exit(0)

# 2. Backup local
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

# 3. Rebuild assignments sans les cibles
new_assigns = {k: v for k, v in assigns.items() if k not in to_delete}
n_deletes = len(assigns) - len(new_assigns)
print()
print(f"  POST atomique (DELETE {n_deletes} cle(s), KV {len(assigns)} -> {len(new_assigns)}) ...")
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
print("  Verif post-DELETE :")
errs = []
for cle in to_delete:
    cur = assigns_after.get(cle)
    if cur:
        print(f"    {cle:<37} -> KO encore present {cur!r}")
        errs.append(cle)
    else:
        print(f"    {cle:<37} -> OK absent")
if errs: fail(f"DELETE incomplet : {errs}")

# 5. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : -{n_deletes} cle(s) supprimee(s), KV {len(assigns)} -> {len(assigns_after)}")
if skip:
    print(f">>> {len(skip)} cle(s) skip (deja propre ou immat divergente) : {[k for k, _ in skip]}")
print("=" * 90)
