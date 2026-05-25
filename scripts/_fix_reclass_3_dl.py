#!/usr/bin/env python3
"""Reclassement KV DL : PATCH 3 cles copro_non_immat (fallback MAJIC).

Suite au re-enrich MAJIC complet (+44 bgids parcelles BDNB ajoutees au
cache) puis a un fallback adresse loose-normalisation sur les 20 cibles
'absent' de l'enrich initial, 3 cibles supplementaires identifiees :

  12 DAVID         -> mono     SCI CBV IMMO (843151226) 100% sur 5 lots
                                MAJIC parcelle DO/0088 (BDNB pointait
                                DO/0051, parcelle MAJIC voisine differente).

  21 ST EUSEBE     -> social   OPH METROPOLE DE LYON (813755949) 100%
                                sur 1 lot MAJIC parcelle DW/0067. Top
                                SIREN = Office Public HLM Metropole =
                                signal social fort malgre faible couver-
                                ture parcellaire (BDNB pointait DW/0047).

  22 ST EUSEBE     -> social   ALLIADE HABITAT (960506152) 100% sur 14
                                lots MAJIC parcelle DW/0059 (bailleur
                                Action Logement, idem 16 LACASSAGNE,
                                18 LACASSAGNE et 30+ autres adresses DL).

Les 17 autres cibles 'absent' restent en copro_non_immat (verifie via
diagnostic MAJIC : numero absent du parquet PM sur leur voie -> 100 %
proprietaires personnes physiques, donc vraies petites copros non immat,
qualif correcte).

Pattern script identique a _fix_reclass_10_dl.py : CIBLES = liste de
(cle, target_type), audit pre-PATCH, backup, POST atomique, re-GET verif,
sync local.

Usage :
  python scripts/_fix_reclass_3_dl.py <JWT_TOKEN>
  ou : DPE_TOKEN=<jwt> python scripts/_fix_reclass_3_dl.py
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".prereclass3.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant (argv1 ou env)"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CIBLES = [
    ("12|RUE|DAVID",       "mono"),     # SCI CBV IMMO 100% (5 lots)
    ("21|RUE|ST EUSEBE",   "social"),   # OPH Metropole de Lyon 100% (1 lot)
    ("22|RUE|ST EUSEBE",   "social"),   # ALLIADE HABITAT 100% (14 lots)
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
print("KV DL reclassement : PATCH 3 cles copro_non_immat (fallback MAJIC)")
print("=" * 90)

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
for cle, target in CIBLES:
    cur = assigns.get(cle)
    tag = (cur or {}).get("type")
    if not cur:
        print(f"    {cle:<32} -> SKIP (absent du KV)")
        skip.append((cle, "absente"))
    elif tag == target:
        print(f"    {cle:<32} -> SKIP (deja type={target}, idempotent)")
        skip.append((cle, f"deja-{target}"))
    elif tag != "copro_non_immat":
        print(f"    {cle:<32} -> SKIP (tag actuel = {tag!r}, attendu copro_non_immat)")
        skip.append((cle, f"tag-{tag}"))
    else:
        extras = sorted(k for k in cur if k != "type")
        print(f"    {cle:<32} -> PATCH copro_non_immat -> {target:<8}  (preserve {extras})")
        to_patch.append((cle, target))

if not to_patch:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : aucune cle a patcher")
    print("=" * 90)
    sys.exit(0)

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

new_assigns = dict(assigns)
counts = {}
for cle, target in to_patch:
    new_assigns[cle] = {**assigns[cle], "type": target}
    counts[target] = counts.get(target, 0) + 1
breakdown = ", ".join(f"{t}={n}" for t, n in sorted(counts.items()))
print()
print(f"  POST atomique (PATCH {len(to_patch)} cle(s), breakdown : {breakdown}) ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
print()
print("  Verif post-PATCH :")
errs = []
for cle, target in to_patch:
    before = assigns[cle]
    after  = assigns_after.get(cle)
    if not after:
        print(f"    {cle:<32} -> KO (disparue)"); errs.append(cle); continue
    if after.get("type") != target:
        print(f"    {cle:<32} -> KO (type={after.get('type')!r}, attendu {target})"); errs.append(cle); continue
    extras_before = {k: v for k, v in before.items() if k != "type"}
    extras_after  = {k: v for k, v in after.items()  if k != "type"}
    if extras_before == extras_after:
        print(f"    {cle:<32} -> OK type={target:<8}  ({len(extras_after)} champ(s) preserve(s))")
    else:
        print(f"    {cle:<32} -> WARN type={target} mais extras differents")
if errs: fail(f"PATCH incomplet : {errs}")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : {len(to_patch)} cle(s) reclassees ({breakdown})")
if skip:
    print(f">>> {len(skip)} cle(s) skip : {[(k, r) for k, r in skip]}")
print("=" * 90)
