#!/usr/bin/env python3
"""Reclassement KV DL : PATCH 10 cles copro_non_immat -> 3 types cibles.

Suite au cross-check MAJIC sur les 32 copro_non_immat residuelles
(nb_log_bdnb in [3,9]) :
  - 2 vrais MONO_SCI (top SIREN unique 100%)
  - 6 social (bailleurs publics/sociaux : Metropole + ESH, IN'LI,
    Habitat & Humanisme, CROUS)
  - 2 bureaux (administration : MAXCAR commercial, Direction Inter-
    regionale Penitentiaire)

Reclassement detaille :
  MONO (top SIREN unique 100%) :
    329 PAUL BERT     -> mono  (SCI LESSARB 100% 5 lots)
    47 av LACASSAGNE  -> mono  (SCI AMPERE SCP 100% 6 lots)

  SOCIAL (bailleur public ou medico-social >= 50% groupe) :
    339 PAUL BERT     -> social  (Metropole Lyon 50% + POSTE HABITAT 50%)
    341 PAUL BERT     -> social  (Metropole Lyon 50% + IRA HLM 50%)
    6 MEYNIS          -> social  (SA HLM LOGEMENT ALPES RHONE 50%)
    5 JEANNE KOEHLER  -> social  (CROUS 50% -- logement etudiant)
    8 JEANNE KOEHLER  -> social  (CROUS 50%)
    16 DAVID          -> social  (groupe Habitat & Humanisme 100% sur
                                  3 SIREN -- pattern medico-social
                                  identique a fix-15david-habitat-humanisme)

  BUREAUX (administration / commerce, pas du logement marchand) :
    23 ST PHILIPPE       -> bureaux  (MAXCAR 100% 1 lot, society
                                       commerciale)
    4 JEANNE HACHETTE    -> bureaux  (DIRECTION INTERREG SERVICES
                                       PENITENTIAIRES LYON 50%)

Pattern PATCH par-cle (cle, target_type), spread {**old, 'type': target}
pour preserver autres champs. Calque sur _fix_mono_18_dl.py.

Usage :
  python scripts/_fix_reclass_10_dl.py <JWT_TOKEN>
  ou : DPE_TOKEN=<jwt> python scripts/_fix_reclass_10_dl.py
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".prereclass10.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant (argv1 ou env)"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

# CIBLES : (cle, type_cible) -- type actuel attendu = copro_non_immat
CIBLES = [
    ("329|RUE|PAUL BERT",         "mono"),
    ("47|AVENUE|LACASSAGNE",      "mono"),
    ("339|RUE|PAUL BERT",         "social"),
    ("341|RUE|PAUL BERT",         "social"),
    ("6|RUE|MEYNIS",              "social"),
    ("5|RUE|JEANNE KOEHLER",      "social"),
    ("8|RUE|JEANNE KOEHLER",      "social"),
    ("16|RUE|DAVID",              "social"),
    ("23|RUE|ST PHILIPPE",        "bureaux"),
    ("4|RUE|JEANNE HACHETTE",     "bureaux"),
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
print("KV DL reclassement : PATCH 10 cles copro_non_immat -> mono / social / bureaux")
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
    print(">>> IDEMPOTENT : aucune cle a patcher (toutes deja propres ou tag divergent)")
    print("=" * 90)
    sys.exit(0)

# 2. Backup local
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

# 3. Rebuild assignments avec type cible (autres champs preserves)
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

# 4. Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
print()
print("  Verif post-PATCH (tag attendu match cible, autres champs preserves) :")
errs = []
for cle, target in to_patch:
    before = assigns[cle]
    after  = assigns_after.get(cle)
    if not after:
        print(f"    {cle:<32} -> KO (disparue)")
        errs.append(cle); continue
    if after.get("type") != target:
        print(f"    {cle:<32} -> KO (type={after.get('type')!r}, attendu {target})")
        errs.append(cle); continue
    extras_before = {k: v for k, v in before.items() if k != "type"}
    extras_after  = {k: v for k, v in after.items()  if k != "type"}
    if extras_before == extras_after:
        print(f"    {cle:<32} -> OK type={target:<8}  ({len(extras_after)} champ(s) preserve(s))")
    else:
        print(f"    {cle:<32} -> WARN type={target} mais extras differents (before={extras_before}, after={extras_after})")
if errs: fail(f"PATCH incomplet : {errs}")

# 5. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : {len(to_patch)} cle(s) reclassees ({breakdown})")
if skip:
    print(f">>> {len(skip)} cle(s) skip : {[(k, r) for k, r in skip]}")
print("=" * 90)
