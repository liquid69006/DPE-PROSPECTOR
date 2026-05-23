#!/usr/bin/env python3
"""POST 2 phases finales DL.

Phase 1 : 9 cles social anomalies (bailleurs sociaux non detectes batch initial)
Phase 2 : 97 cles copro_non_immat (le reste des hr-ancres)

Chaque phase : backup local KV + POST + re-GET + verification. Stop sur erreur.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
PLAN_COPRO = ROOT / "data" / "_plan_batch_copro_dl.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

# Phase 1 : 9 social anomalies (tries pour reproductibilite)
PHASE1_SOCIAL = [
    "17|RUE|ETIENNE RICHERAND",      # ALLIADE HABITAT 202
    "208|AVENUE|FELIX FAURE",        # IRA SA HLM 220
    "212|AVENUE|FELIX FAURE",        # IRA SA HLM 220
    "353|RUE|PAUL BERT",             # ALLIADE HABITAT 36
    "192|AVENUE|FELIX FAURE",        # COMMUNAUTE URBAINE 33
    "155|AVENUE|FELIX FAURE",        # GRANDLYON HABITAT 22
    "13|RUE|CLAUDIUS PIONCHON",      # COMMUNE DE LYON 16
    "3|RUE|ROGER BRECHAN",           # COMMUNAUTE URBAINE 15
    "252|RUE|PAUL BERT",             # COMMUNAUTE URBAINE 14
]

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def kv_get():
    code, raw = http("GET", ENDPOINT, HDR_GET)
    if code != 200: raise RuntimeError(f"KV GET {code}: {raw[:200]}")
    return json.loads(raw)

def kv_post(payload):
    code, raw = http("POST", ENDPOINT, HDR_POST, body=payload)
    if code not in (200, 204): raise RuntimeError(f"KV POST {code}: {raw[:200]}")
    return raw

def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)

def run_phase(label, plan, target_type, backup_suffix):
    print()
    print("#" * 90)
    print(f"# {label} - {len(plan)} cles -> '{target_type}'")
    print("#" * 90)
    # GET
    kv = kv_get()
    assigns_before = kv.get("assignments") or {}
    fusions = kv.get("fusions") or {}
    noms = kv.get("noms") or {}
    print(f"  KV avant : {len(assigns_before)} assigns ({len(fusions)} fusions, {len(noms)} noms)")
    if KV_LOCAL.exists():
        bak = KV_LOCAL.with_suffix(KV_LOCAL.suffix + backup_suffix)
        shutil.copy2(KV_LOCAL, bak)
        print(f"  Backup local KV : {bak.name}")
    # Merge
    assigns_new = dict(assigns_before)
    already, overrides, new = [], [], []
    for cle in plan:
        cur = assigns_new.get(cle)
        if cur and isinstance(cur, dict) and cur.get("type") == target_type:
            already.append(cle)
        elif cur:
            overrides.append((cle, cur.get("type") if isinstance(cur, dict) else cur))
            assigns_new[cle] = {"type": target_type}
        else:
            new.append(cle)
            assigns_new[cle] = {"type": target_type}
    print(f"  Deja en KV (skip)  : {len(already)}")
    print(f"  Overrides type     : {len(overrides)}")
    for cle, cur in overrides[:5]: print(f"    - {cle:32s} {cur} -> {target_type}")
    if len(overrides) > 5: print(f"    ... (+{len(overrides)-5} autres)")
    print(f"  Nouvelles cles     : {len(new)}")
    print(f"  Total apres merge  : {len(assigns_new)}  (avant {len(assigns_before)})")
    # POST
    raw = kv_post({"assignments": assigns_new, "fusions": fusions, "noms": noms})
    print(f"  POST OK : {raw[:200]}")
    # Re-GET verif
    kv_after = kv_get()
    assigns_after = kv_after.get("assignments") or {}
    print(f"  Re-GET : {len(assigns_after)} assigns (attendu {len(assigns_new)})")
    missing, wrong = [], []
    for cle in plan:
        cur = assigns_after.get(cle)
        if not cur: missing.append(cle)
        elif (cur.get("type") if isinstance(cur, dict) else None) != target_type:
            wrong.append((cle, cur))
    print(f"  Verif : {len(plan) - len(missing) - len(wrong)} / {len(plan)} OK")
    for c in missing: print(f"    KO manquant - {c}")
    for c, cur in wrong: print(f"    KO type     - {c} -> {cur}")
    if missing or wrong:
        fail(f"{label} verif post-POST : {len(missing)} manquants, {len(wrong)} mauvais type")
    # Sync local
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Local sync : {KV_LOCAL.name}")
    print(f"  >>> {label} OK : KV {len(assigns_before)} -> {len(assigns_after)} (+{len(assigns_after)-len(assigns_before)})")


# ============================================================
print("=" * 90)
print("POST 2 PHASES FINALES DL - 9 social anomalies + 97 copro_non_immat")
print("=" * 90)

# --- Phase 1 ---
run_phase("PHASE 1 - social anomalies (9 cles)", PHASE1_SOCIAL, "social", ".prephase1social.bak")

# --- Phase 2 ---
plan_copro_doc = json.loads(PLAN_COPRO.read_text(encoding="utf-8"))
PHASE2_COPRO = [item["cle"] for item in plan_copro_doc.get("plan") or []]
if not PHASE2_COPRO:
    fail("Plan copro vide dans _plan_batch_copro_dl.json")
print()
print(f"  Plan copro charge : {len(PHASE2_COPRO)} cles depuis {PLAN_COPRO.name}")
run_phase("PHASE 2 - copro_non_immat (97 cles)", PHASE2_COPRO, "copro_non_immat", ".prephase2copro.bak")

# --- Bilan final ---
print()
print("=" * 90)
print(">>> TOUS LES POST TERMINES")
kv_final = kv_get()
print(f"    KV final server : {len(kv_final.get('assignments') or {})} assigns")
print(f"    Fusions : {len(kv_final.get('fusions') or {})}  Noms : {len(kv_final.get('noms') or {})}")
print("=" * 90)
