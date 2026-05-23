#!/usr/bin/env python3
"""POST 4 batches KV pour les 85 cles suffixees DL (triage termine).

Batch 1 : 21 social (20 + 15T DAUPHINE reclasse depuis copro)
Batch 2 :  9 mono (exclure 185T FELIX FAURE ENEDIS)
Batch 3 :  1 bureaux : 185T FELIX FAURE (ENEDIS = utilitaire)
Batch 4 : 13 copro_non_immat (sans 15T DAUPHINE)

Source plan : data/_triage_85_suffixes_dl.json
Verifications : backup local + POST + re-GET + diff par batch.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
TRIAGE  = ROOT / "data" / "_triage_85_suffixes_dl.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

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

# --- Charger triage + composer batches ---
triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RECLASS_TO_SOCIAL = "15T|RUE|DAUPHINE"   # depuis COPRO -> SOCIAL
EXCLUDE_MONO = "185T|AVENUE|FELIX FAURE"  # ENEDIS utilitaire -> bureaux

BATCH1_SOCIAL = sorted(triage["social"] + [RECLASS_TO_SOCIAL])
BATCH2_MONO = sorted([c for c in triage["mono_majic"] if c != EXCLUDE_MONO])
BATCH3_BUREAUX = [EXCLUDE_MONO]
BATCH4_COPRO = sorted([c for c in triage["copro_non_immat"] if c != RECLASS_TO_SOCIAL])

# Sanity check
n_total = len(BATCH1_SOCIAL) + len(BATCH2_MONO) + len(BATCH3_BUREAUX) + len(BATCH4_COPRO)
expected_total = len(triage["social"]) + len(triage["mono_majic"]) + len(triage["copro_non_immat"])
print(f"  Triage source : social={len(triage['social'])} mono={len(triage['mono_majic'])} copro={len(triage['copro_non_immat'])}")
print(f"  Batches construits : B1={len(BATCH1_SOCIAL)} B2={len(BATCH2_MONO)} B3={len(BATCH3_BUREAUX)} B4={len(BATCH4_COPRO)}")
print(f"  Total {n_total} (attendu {expected_total} = 20+10+14 sans modification)")
if n_total != expected_total:
    fail(f"Compte batches {n_total} != triage total {expected_total}")

def run_batch(label, cles, target_type, bak_suffix):
    print()
    print("#" * 90)
    print(f"# {label} - {len(cles)} cles -> '{target_type}'")
    print("#" * 90)
    # GET
    kv = kv_get()
    assigns_before = kv.get("assignments") or {}
    fusions = kv.get("fusions") or {}
    noms = kv.get("noms") or {}
    print(f"  KV avant : {len(assigns_before)} assigns")
    # Backup
    if KV_LOCAL.exists():
        bak = KV_LOCAL.with_suffix(KV_LOCAL.suffix + bak_suffix)
        shutil.copy2(KV_LOCAL, bak)
        print(f"  Backup : {bak.name}")
    # Merge
    assigns_new = dict(assigns_before)
    already, overrides, new = [], [], []
    for cle in cles:
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
    for cle, cur in overrides[:5]: print(f"    - {cle:34s} {cur} -> {target_type}")
    if len(overrides) > 5: print(f"    ... (+{len(overrides)-5} autres)")
    print(f"  Nouvelles cles     : {len(new)}")
    print(f"  Total apres merge  : {len(assigns_new)}  (avant {len(assigns_before)})")
    # POST
    raw = kv_post({"assignments": assigns_new, "fusions": fusions, "noms": noms})
    print(f"  POST OK : {raw[:160]}")
    # Re-GET
    kv_after = kv_get()
    assigns_after = kv_after.get("assignments") or {}
    print(f"  Re-GET : {len(assigns_after)} assigns (attendu {len(assigns_new)})")
    missing, wrong = [], []
    for cle in cles:
        cur = assigns_after.get(cle)
        if not cur: missing.append(cle)
        elif (cur.get("type") if isinstance(cur, dict) else None) != target_type:
            wrong.append((cle, cur))
    print(f"  Verif : {len(cles) - len(missing) - len(wrong)} / {len(cles)} OK")
    for c in missing: print(f"    KO manquant - {c}")
    for c, cur in wrong: print(f"    KO type     - {c} -> {cur}")
    if missing or wrong:
        fail(f"{label} verif post-POST : {len(missing)} manquants, {len(wrong)} mauvais type")
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Local sync : {KV_LOCAL.name}")
    print(f"  >>> {label} OK : KV {len(assigns_before)} -> {len(assigns_after)} (+{len(assigns_after)-len(assigns_before)})")

# ============================================================
print("=" * 90)
print("POST 4 BATCHES SUFFIXES DL")
print("=" * 90)

run_batch(f"BATCH 1 - SOCIAL ({len(BATCH1_SOCIAL)})", BATCH1_SOCIAL, "social", ".preb1suffsoc.bak")
run_batch(f"BATCH 2 - MONO ({len(BATCH2_MONO)})", BATCH2_MONO, "mono", ".preb2suffmono.bak")
run_batch(f"BATCH 3 - BUREAUX ({len(BATCH3_BUREAUX)})", BATCH3_BUREAUX, "bureaux", ".preb3suffbur.bak")
run_batch(f"BATCH 4 - COPRO_NON_IMMAT ({len(BATCH4_COPRO)})", BATCH4_COPRO, "copro_non_immat", ".preb4suffcopro.bak")

# Bilan final
print()
print("=" * 90)
kv_final = kv_get()
af = kv_final.get("assignments") or {}
print(f">>> TOUS BATCHES OK")
print(f"    KV final server : {len(af)} assigns")
print(f"    Fusions : {len(kv_final.get('fusions') or {})}  Noms : {len(kv_final.get('noms') or {})}")
print("=" * 90)
