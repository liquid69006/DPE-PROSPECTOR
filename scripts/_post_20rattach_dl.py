#!/usr/bin/env python3
"""POST batch KV - 20 RATTACHABLES suffixes DL (14 copro + 6 social).

User a override 121A/B/C/D CHARIAL en social (vs suggestion copro_non_immat).
Decision : proprietaire MAJIC OPH METROPOLE LYON majoritaire (43-48/25 hab par
facade) ; copro RNC gere par REGIE LESTRA (mandat). Tag social refletant le
parc OPH residuel.

Social explicite (6) :
  - 28B|RUE|CLAUDIUS PIONCHON (GRANDLYON HABITAT)
  - 2B|RUE|DAUPHINE (RHONE SAONE HABITAT)
  - 121A|RUE|ANTOINE CHARIAL (OPH via REGIE LESTRA)
  - 121B|RUE|ANTOINE CHARIAL (idem)
  - 121C|RUE|ANTOINE CHARIAL (idem)
  - 121D|RUE|ANTOINE CHARIAL (idem)

Copro_non_immat (14) : tous les autres RATTACHABLES non qualifies KV.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre20rattach.bak")

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

SOCIAL_OVERRIDE = {
    "28B|RUE|CLAUDIUS PIONCHON",
    "2B|RUE|DAUPHINE",
    "121A|RUE|ANTOINE CHARIAL",
    "121B|RUE|ANTOINE CHARIAL",
    "121C|RUE|ANTOINE CHARIAL",
    "121D|RUE|ANTOINE CHARIAL",
}

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)

# --- Charger triage + KV pour identifier les RATTACHABLES non qualifies ---
triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RATTACH = set(triage.get("rattachables_rnc") or [])

# GET KV
print("=" * 90)
print("POST batch 20 RATTACHABLES DL (14 copro_non_immat + 6 social)")
print("=" * 90)
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
shutil.copy2(KV_LOCAL, BAK) if KV_LOCAL.exists() else None
print(f"  Backup : {BAK.name}")

# Filtre cles non qualifiees
NON_QUALIF = sorted([c for c in RATTACH if c not in assigns])
print(f"  RATTACHABLES non qualifies : {len(NON_QUALIF)}")

# Verifier que les 6 social_override existent dans NON_QUALIF
miss = [c for c in SOCIAL_OVERRIDE if c not in NON_QUALIF]
if miss:
    fail(f"social_override cles introuvables : {miss}")

# Composer plan
PLAN_SOCIAL = sorted(SOCIAL_OVERRIDE)
PLAN_COPRO = sorted([c for c in NON_QUALIF if c not in SOCIAL_OVERRIDE])
print(f"  Plan social      : {len(PLAN_SOCIAL)} cles")
for c in PLAN_SOCIAL: print(f"    - {c}")
print(f"  Plan copro_non_immat : {len(PLAN_COPRO)} cles")
for c in PLAN_COPRO: print(f"    - {c}")
total = len(PLAN_SOCIAL) + len(PLAN_COPRO)
print(f"  Total : {total}  (attendu 20)")

# Merge
new_assigns = dict(assigns)
for cle in PLAN_SOCIAL:
    new_assigns[cle] = {"type": "social"}
for cle in PLAN_COPRO:
    new_assigns[cle] = {"type": "copro_non_immat"}

# POST
print()
print(f"  POST atomique ({total} cles, KV {len(assigns)} -> {len(new_assigns)}) ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:160]}")
if code not in (200, 204): fail(f"POST KO {code}")

# Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns (attendu {len(new_assigns)})")
ok_s, ok_c = 0, 0
missing, wrong = [], []
for cle in PLAN_SOCIAL:
    cur = assigns_after.get(cle)
    if not cur: missing.append((cle, "social"))
    elif (cur.get("type") if isinstance(cur, dict) else None) != "social":
        wrong.append((cle, "social", cur))
    else: ok_s += 1
for cle in PLAN_COPRO:
    cur = assigns_after.get(cle)
    if not cur: missing.append((cle, "copro_non_immat"))
    elif (cur.get("type") if isinstance(cur, dict) else None) != "copro_non_immat":
        wrong.append((cle, "copro_non_immat", cur))
    else: ok_c += 1

print()
print(f"  Verif : social {ok_s}/{len(PLAN_SOCIAL)}  copro_non_immat {ok_c}/{len(PLAN_COPRO)}")
for c, t in missing: print(f"    KO manquant - {c} ({t})")
for c, t, cur in wrong: print(f"    KO mauv.type - {c} ({t}) -> {cur}")
if missing or wrong: fail(f"verif post-POST : {len(missing)} manquants, {len(wrong)} mauvais type")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local sync : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : {ok_s + ok_c}/{total} cles confirmees ({ok_s} social + {ok_c} copro_non_immat)")
print(f"    KV : {len(assigns)} -> {len(assigns_after)} (+{len(assigns_after)-len(assigns)})")
print("=" * 90)
