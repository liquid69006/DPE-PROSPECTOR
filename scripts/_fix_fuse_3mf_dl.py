#!/usr/bin/env python3
"""KV DL : FUSE 5+7 RUE MAURICE FLANDIN -> 3 RUE MAURICE FLANDIN.

Pattern eclatement mono-bgid : 3 cles light (3, 5, 7 MAURICE FLANDIN)
pointent toutes le meme bgid BDNB W2RS-K6JM-Z1H3 sur parcelle EI/0043
(1961, Resid collectif, bdnb=54 chacune = triple comptage). Aucune
immatriculation RNC, FONCIA COUPAT en syndic non declare.

Action : fusion KV { 5 MF -> 3 MF, 7 MF -> 3 MF } pour reduire le
triple comptage. L'ancre 3 MF garde son tag copro_non_immat + ilot.
Effet attendu : parc DL -108 logements (elimination du double-compte
sur 5 et 7 MF), hr-actifs UI -2 cles, 1 seule ancre visible bdnb=54.

Verification pre-fusion : controle que 3/5/7 MF partagent bien
bgid W2RS-K6JM-Z1H3 dans le snapshot light (anti-race condition).

Pattern script :
  GET KV live -> verif bgid light -> backup local .prefuse3mf.bak
  -> rebuild fusions dict avec 2 nouveaux mapping
  -> POST atomique (assignments inchanges, fusions etendu, noms idem)
  -> Re-GET verif presence des 2 mappings -> sync local.

Idempotent : si une fusion existe deja avec la meme dst, SKIP.
Si elle pointe une AUTRE dst, FAIL (conflict, decision manuelle).

Usage :
  python scripts/_fix_fuse_3mf_dl.py <JWT_TOKEN>
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT_P  = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".prefuse3mf.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

ANCRE = "3|RUE|MAURICE FLANDIN"
EXPECTED_BGID = "bdnb-bg-W2RS-K6JM-Z1H3"
NEW_FUSIONS = {
    "5|RUE|MAURICE FLANDIN": ANCRE,
    "7|RUE|MAURICE FLANDIN": ANCRE,
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
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


print("=" * 90)
print(f"KV DL fusion : 5+7 RUE MAURICE FLANDIN -> 3 RUE MAURICE FLANDIN (eclatement mono-bgid)")
print("=" * 90)

# 1. Verif anti-race : bgid partages dans light
print()
print("  Verif partage bgid via light JSON (anti-race condition) :")
light = json.loads(LIGHT_P.read_text(encoding="utf-8"))
adr_by_cle = {(a.get("cle") or ""): a for a in (light.get("adresses") or [])}
cles_a_verifier = [ANCRE] + list(NEW_FUSIONS.keys())
bgids = {}
for cle in cles_a_verifier:
    a = adr_by_cle.get(cle)
    if not a: fail(f"cle absente du light : {cle}")
    bgids[cle] = a.get("batiment_groupe_id")
    print(f"    {cle:<35} bgid={bgids[cle]}")
if len(set(bgids.values())) != 1:
    fail(f"bgids divergents : {bgids}")
if list(bgids.values())[0] != EXPECTED_BGID:
    fail(f"bgid commun = {list(bgids.values())[0]!r}, attendu {EXPECTED_BGID!r}")
print(f"  [OK] Les 3 cles partagent bgid {EXPECTED_BGID}")

# 2. GET KV live
print()
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions, {len(noms)} noms")

# 3. Audit pre-FUSE
print()
print("  Audit pre-FUSE (fusion existante ? conflits ?) :")
to_add = {}
skip = []
for src, dst in NEW_FUSIONS.items():
    cur = fusions.get(src)
    if cur == dst:
        print(f"    {src} -> {dst}  SKIP (deja fused, idempotent)")
        skip.append(src)
    elif cur:
        fail(f"CONFLIT : {src} deja fused vers {cur!r}, attendu {dst!r} (decision manuelle requise)")
    else:
        print(f"    {src} -> {dst}  ADD")
        to_add[src] = dst

if not to_add:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : aucune fusion a ajouter")
    print("=" * 90)
    sys.exit(0)

# 4. Backup local
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

# 5. Rebuild fusions
new_fusions = dict(fusions)
new_fusions.update(to_add)
print()
print(f"  POST atomique (fusions {len(fusions)} -> {len(new_fusions)}, +{len(to_add)}) ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": assigns, "fusions": new_fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

# 6. Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
fusions_after = kv_after.get("fusions") or {}
print(f"  Re-GET : {len(fusions_after)} fusions")
print()
print("  Verif post-FUSE :")
errs = []
for src, dst in to_add.items():
    if fusions_after.get(src) != dst:
        print(f"    {src} -> {dst}  KO (live = {fusions_after.get(src)!r})")
        errs.append(src)
    else:
        print(f"    {src} -> {dst}  OK")
if errs: fail(f"FUSE incomplet : {errs}")

# 7. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : +{len(to_add)} fusion(s), KV fusions {len(fusions)} -> {len(fusions_after)}")
if skip: print(f">>> {len(skip)} fusion(s) skip (deja en place) : {skip}")
print("=" * 90)
