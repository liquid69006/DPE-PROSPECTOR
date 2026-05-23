#!/usr/bin/env python3
"""Apply E1 revise - 31/33 RICHERAND + 40/42 AUBIGNY (FONCIERE VESTA bailleur social).

Operations :
  light.json :
    1. RE-POINT 40 AUB bgid YD2U -> D61Z + FA + cible=33 RICH + cleanup label
    2. RE-POINT 42 AUB bgid YD2U -> D61Z + FA cible 40 -> 33 RICH
    3. Label sur 33 RICH : '31/33 RUE ETIENNE RICHERAND / 40/42 RUE AUBIGNY'
       sources = ['40|RUE|AUBIGNY', '42|RUE|AUBIGNY']
  KV :
    33|RUE|ETIENNE RICHERAND : mono -> social

Backup + apply + verif. Stop sur erreur. Commit local sans push.
"""
import json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
KV_ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

# Cibles
ANCRE  = "33|RUE|ETIENNE RICHERAND"
F40    = "40|RUE|AUBIGNY"
F42    = "42|RUE|AUBIGNY"
LABEL  = "31/33 RUE ETIENNE RICHERAND / 40/42 RUE AUBIGNY"

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def kv_get():
    code, raw = http("GET", KV_ENDPOINT, HDR_GET)
    if code != 200: raise RuntimeError(f"KV GET {code}: {raw[:200]}")
    return json.loads(raw)

def kv_post(payload):
    code, raw = http("POST", KV_ENDPOINT, HDR_POST, body=payload)
    if code not in (200, 204): raise RuntimeError(f"KV POST {code}: {raw[:200]}")
    return raw

def fail(msg):
    print()
    print("!" * 90)
    print(f"!  ECHEC : {msg}")
    print("!" * 90)
    sys.exit(10)

# ============================================================
# PHASE 1 : Backups
# ============================================================
print("=" * 90)
print("APPLY E1 REVISE - 31/33 RICHERAND + 40/42 AUBIGNY (FONCIERE VESTA bailleur social)")
print("=" * 90)
print()
print("[1] BACKUPS")
bak_light = LIGHT.with_suffix(LIGHT.suffix + ".pree1revise.bak")
shutil.copy2(LIGHT, bak_light)
print(f"  Backup light : {bak_light.name}")
if KV_LOCAL.exists():
    bak_kv = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pree1revise.bak")
    shutil.copy2(KV_LOCAL, bak_kv)
    print(f"  Backup KV    : {bak_kv.name}")

# ============================================================
# PHASE 2 : Light modifications
# ============================================================
print()
print("[2] LIGHT modifications (in-memory)")
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
by_cle = {(a.get("cle") or ""): a for a in ad}

a_ancre = by_cle.get(ANCRE)
a_40 = by_cle.get(F40)
a_42 = by_cle.get(F42)
if not all([a_ancre, a_40, a_42]):
    fail(f"Cle absente light : ancre={a_ancre is not None} 40={a_40 is not None} 42={a_42 is not None}")

bgid_ancre = a_ancre.get("batiment_groupe_id")
bgid_40_avant = a_40.get("batiment_groupe_id")
bgid_42_avant = a_42.get("batiment_groupe_id")
label_40_avant = a_40.get("_fusion_auto_label")
sources_40_avant = a_40.get("_fusion_auto_sources")
fa_cible_42_avant = a_42.get("_fusion_cible")

# (1) 40 AUB : RE-POINT + FA + cible + cleanup label/sources
a_40["batiment_groupe_id"] = bgid_ancre
a_40["_fusion_auto"] = True
a_40["_fusion_cible"] = ANCRE
a_40.pop("_fusion_auto_label", None)
a_40.pop("_fusion_auto_sources", None)
print(f"  40 AUB :")
print(f"    bgid : {bgid_40_avant} -> {bgid_ancre}")
print(f"    _fusion_auto : -> True")
print(f"    _fusion_cible : -> '{ANCRE}'")
print(f"    cleanup label '{label_40_avant}' + sources {sources_40_avant}")

# (2) 42 AUB : RE-POINT + FA cible
a_42["batiment_groupe_id"] = bgid_ancre
a_42["_fusion_cible"] = ANCRE
# (_fusion_auto deja True dans light avant)
print(f"  42 AUB :")
print(f"    bgid : {bgid_42_avant} -> {bgid_ancre}")
print(f"    _fusion_cible : '{fa_cible_42_avant}' -> '{ANCRE}'")

# (3) 33 RICH : label + sources
a_ancre["_fusion_auto_label"] = LABEL
a_ancre["_fusion_auto_sources"] = [F40, F42]
print(f"  33 RICH :")
print(f"    _fusion_auto_label : -> '{LABEL}'")
print(f"    _fusion_auto_sources : -> ['{F40}', '{F42}']")

# Verifs in-memory
if a_40.get("batiment_groupe_id") != bgid_ancre: fail("40 AUB RE-POINT non applique")
if not a_40.get("_fusion_auto"): fail("40 AUB FA non applique")
if a_40.get("_fusion_cible") != ANCRE: fail("40 AUB cible incorrect")
if "_fusion_auto_label" in a_40: fail("40 AUB label non retire")
if a_42.get("batiment_groupe_id") != bgid_ancre: fail("42 AUB RE-POINT non applique")
if a_42.get("_fusion_cible") != ANCRE: fail("42 AUB cible incorrect")
if a_ancre.get("_fusion_auto_label") != LABEL: fail("33 RICH label incorrect")
if a_ancre.get("_fusion_auto_sources") != [F40, F42]: fail("33 RICH sources incorrect")
print(f"  >>> Verifs in-memory OK")

# ============================================================
# PHASE 3 : Ecriture light (indent=2 pour diff compact)
# ============================================================
print()
print("[3] ECRITURE light.json (indent=2)")
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

# Re-read verif
doc_check = json.loads(LIGHT.read_text(encoding="utf-8"))
ad_check = {(a.get("cle") or ""): a for a in doc_check["adresses"]}
def ck(c, k, exp):
    actual = (c or {}).get(k)
    if actual != exp:
        fail(f"VERIF post-write : {c.get('cle','?') if c else '?'}.{k} = {actual!r} (attendu {exp!r})")
ck(ad_check.get(F40), "batiment_groupe_id", bgid_ancre)
ck(ad_check.get(F40), "_fusion_auto", True)
ck(ad_check.get(F40), "_fusion_cible", ANCRE)
if ad_check.get(F40, {}).get("_fusion_auto_label") is not None:
    fail(f"40 AUB label encore present apres write")
ck(ad_check.get(F42), "batiment_groupe_id", bgid_ancre)
ck(ad_check.get(F42), "_fusion_cible", ANCRE)
ck(ad_check.get(ANCRE), "_fusion_auto_label", LABEL)
ck(ad_check.get(ANCRE), "_fusion_auto_sources", [F40, F42])
print(f"  Re-read verif : 4 cles OK")

# ============================================================
# PHASE 4 : KV - 33 RICH mono -> social
# ============================================================
print()
print("[4] KV : 33 RICH mono -> social")
kv = kv_get()
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
cur_33 = assigns.get(ANCRE)
print(f"  KV[{ANCRE}] avant : {cur_33}")
if cur_33 and cur_33.get("type") == "social":
    print(f"  IDEMPOTENT : deja social")
else:
    new_assigns = dict(assigns)
    new_assigns[ANCRE] = {"type": "social"}
    kv_post({"assignments": new_assigns, "fusions": fusions, "noms": noms})
    print(f"  POST OK")
    kv_after = kv_get()
    val = (kv_after.get("assignments") or {}).get(ANCRE)
    if not val or val.get("type") != "social":
        fail(f"KV 33 RICH verif post-POST : {val}")
    print(f"  KV[{ANCRE}] apres : {val}  OK")
    print(f"  KV apres : {len(kv_after.get('assignments') or {})} assigns")
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Local KV sync : {KV_LOCAL.name}")

print()
print("=" * 90)
print(">>> APPLY E1 REVISE TERMINE")
print(f"    light : 7 modifications (2 RE-POINT bgid + 2 FA cible + 1 FA flag + 1 cleanup + 1 label)")
print(f"    KV    : 1 update (33 RICH mono -> social)")
print(f"    backups : pree1revise.bak (light + KV)")
print(f"    COMMIT a faire par l'orchestrateur. PAS DE PUSH.")
print("=" * 90)
