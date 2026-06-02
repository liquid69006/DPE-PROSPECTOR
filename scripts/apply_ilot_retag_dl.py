# -*- coding: utf-8 -*-
"""Retag KV ilots DL (split ex-ilot 49) : 14 cles -> ilot=85, 1 cle -> ilot=54.
Full-replace anti-drift (pattern apply_bureaux_retag_dl.py). DRY-RUN par defaut.

Usage:
    PYTHONUTF8=1 python scripts/apply_ilot_retag_dl.py          # dry-run (aucun POST)
    PYTHONUTF8=1 python scripts/apply_ilot_retag_dl.py --go     # POST effectif

Pre-requis POST: $env:DPE_JWT charge (. scripts/load_jwt.ps1), dans LA MEME session.

Rituel:
  1. GET live -> backup horodate (data/_kv_assign_dl.<ts>.bak, gitignore *.bak).
  2. Anti-drift : live == miroir local (data/_kv_assign_dl.json) ; divergence => STOP.
  3. Audit pre-PATCH des 15 cles ; STOP si une est deja sur sa cible.
  4. Build : 14 -> ilot=85, 1 -> ilot=54 (merge, garde 'type' ; cree si absente). Rien d'autre.
  5. POST atomique full-replace (--go).
  6. Re-GET : diff == exactement 15 cles, reste inchange, sinon STOP.
  7. Miroir local data/_kv_assign_dl.json reecrit depuis le re-GET (le commit se fait a part).
"""
import json, os, sys, copy, urllib.request, urllib.error
from datetime import datetime

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
SECID = "dauphine-lacassagne"
MIRROR = "data/_kv_assign_dl.json"          # baseline anti-drift = miroir courant (post-bureaux, 636)
A_KEYS = ["148|RUE|BARABAN", "150|RUE|BARABAN", "152|RUE|BARABAN", "154|RUE|BARABAN",
          "156|RUE|BARABAN", "158|RUE|BARABAN", "160|RUE|BARABAN", "162|RUE|BARABAN",
          "164|RUE|BARABAN", "166|RUE|BARABAN", "168|RUE|BARABAN",
          "161|AVENUE|FELIX FAURE", "246|RUE|PAUL BERT", "33|AVENUE|LACASSAGNE"]  # -> 85
B_TARGET = {"22|AVENUE|LACASSAGNE": 54}      # -> 54 (correction mis-tag, immeuble Bricks)
TARGET = {k: 85 for k in A_KEYS}
TARGET.update(B_TARGET)
GO = "--go" in sys.argv


def unwrap(o):
    return {"assignments": o.get("assignments", {}) or {},
            "fusions": o.get("fusions", {}) or {},
            "noms": o.get("noms", {}) or {}}


def get_live():
    tok = os.environ.get("DPE_JWT")
    if not tok:
        sys.exit("ERREUR: $env:DPE_JWT absent (lancer . scripts/load_jwt.ps1 dans CETTE session)")
    req = urllib.request.Request(f"{API}/secteur-assignments/{SECID}",
                                 headers={"Authorization": f"Bearer {tok}",
                                          "User-Agent": "Mozilla/5.0",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return unwrap(json.loads(r.read()))
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} (GET): {e.read().decode()}")
        raise


def diff_keys(a, b):
    return [k for k in set(a) | set(b) if a.get(k) != b.get(k)]


def build(live):
    a = copy.deepcopy(live["assignments"])
    for k, il in TARGET.items():
        e = dict(a.get(k) or {})       # merge : garde 'type' s'il existe
        e["ilot"] = il
        a[k] = e
    return {"assignments": a, "fusions": live["fusions"], "noms": live["noms"]}


# --- 1. GET live + backup horodate ---
live = get_live()
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
bak = f"data/_kv_assign_dl.{ts}.bak"
json.dump(live, open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"1. GET live OK ({len(live['assignments'])} assignments) -> backup {bak}")

# --- 2. anti-drift live vs miroir local ---
mirror = unwrap(json.load(open(MIRROR, encoding="utf-8-sig")))
if live != mirror:
    print("ABORT anti-drift: live != miroir local (data/_kv_assign_dl.json).")
    for k in sorted(diff_keys(live["assignments"], mirror["assignments"])):
        print(f"  {k}: live={live['assignments'].get(k)} miroir={mirror['assignments'].get(k)}")
    if live["fusions"] != mirror["fusions"]:
        print("  fusions different")
    if live["noms"] != mirror["noms"]:
        print("  noms different")
    sys.exit(1)
print("2. anti-drift OK : live == miroir local.")

# --- 3. audit pre-PATCH ---
a0 = live["assignments"]
print("3. audit pre-PATCH des 15 cles :")
already = []
for k in list(A_KEYS) + list(B_TARGET):
    e = a0.get(k)
    cur = (e or {}).get("ilot")
    if e is None:
        etat = "ABSENTE"
    else:
        etat = "ilot=%s type=%s" % (cur, e.get("type"))
    print("   %-26s cible=%-3s actuel=%s" % (k, TARGET[k], etat))
    if str(cur) == str(TARGET[k]):
        already.append(k)
if already:
    sys.exit(f"ABORT: deja sur cible: {already}")

# --- 4. build ---
new = build(live)
chg = diff_keys(a0, new["assignments"])
assert set(chg) == set(TARGET), f"ABORT: diff={sorted(chg)} != 15 cibles"
assert new["fusions"] == live["fusions"] and new["noms"] == live["noms"], "ABORT: fusions/noms modifies"
print(f"4. build OK : {len(a0)} -> {len(new['assignments'])} assignments | {len(chg)} cles modifiees (attendu 15)")
for k in sorted(chg):
    print(f"   {k}: {a0.get(k)} -> {new['assignments'][k]}")

if not GO:
    print("\nDRY-RUN (pas de --go) : AUCUN POST effectue.")
    sys.exit(0)

# --- 5. POST full-replace ---
tok = os.environ["DPE_JWT"]
body = json.dumps(new).encode("utf-8")
req = urllib.request.Request(f"{API}/secteur-assignments/{SECID}", data=body, method="POST",
                             headers={"Authorization": f"Bearer {tok}",
                                      "Content-Type": "application/json",
                                      "User-Agent": "Mozilla/5.0",
                                      "Accept": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("5. POST OK:", r.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code} (POST): {e.read().decode()}")
    raise

# --- 6. re-GET verif ---
live2 = get_live()
post_chg = diff_keys(a0, live2["assignments"])
if live2 != new:
    print("ABORT post-POST: live relue != new.")
    for k in sorted(diff_keys(new["assignments"], live2["assignments"])):
        print(f"  {k}: new={new['assignments'].get(k)} live2={live2['assignments'].get(k)}")
    sys.exit(1)
assert set(post_chg) == set(TARGET), f"ABORT: diff post-POST = {sorted(post_chg)} != 15 cibles"
for k in A_KEYS:
    assert live2["assignments"][k]["ilot"] == 85, f"ABORT: {k} ilot != 85"
assert live2["assignments"]["22|AVENUE|LACASSAGNE"]["ilot"] == 54, "ABORT: 22 LAC ilot != 54"
print(f"6. re-GET OK : {len(post_chg)} cles modifiees (14 -> 85, 1 -> 54), reste inchange.")

# --- 7. miroir local reecrit depuis le re-GET ---
json.dump(live2, open(MIRROR, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"7. miroir local reecrit depuis le re-GET: {MIRROR}  (commit a faire separement)")
