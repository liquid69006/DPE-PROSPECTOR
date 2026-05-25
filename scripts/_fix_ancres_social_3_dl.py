#!/usr/bin/env python3
"""KV DL : 2 actions atomiques --
  ACTION 1 : tag social sur 3 ancres haute confiance (top SIREN
             OPH/Grand Lyon Habitat >= 95 % via MAJIC)
  ACTION 2 : fusion 11 TERNOIS -> 28 ETIENNE RICHERAND (supprime
             le doublon visuel ; meta-ancre 28 RICHERAND deja
             declare 11 TERNOIS dans ses _fusion_auto_sources).

ACTION 1 (3 tags social, CREATE) :
  25 RUE ST EUSEBE         OPH Metropole Lyon 98.8% (80/82 lots)
  29 RUE ETIENNE RICHERAND OPH Metropole Lyon 94.8% (146/154 lots)
  11 RUE TERNOIS           Grand Lyon Habitat OPH 98.4% (308/313 lots)

  Verification : SIRENs minoritaires lookup MAJIC forme_juridique
  -> tous SCI/SARL privees, aucun lien filiale OPH. Cumul social
  >= 95 %, 0 PP, qualif `social` certaine.

ACTION 2 (1 fusion KV, ADD) :
  11 TERNOIS -> 28 ETIENNE RICHERAND
  Les 13/15/17 TERNOIS deja _fusion_auto=True suivent automatiquement.
  Effet UI : 11 TERNOIS disparait, ses 211 lgts attribues a 28 RICHERAND
  (meta-ancre).

POST atomique unique : new_assigns (avec 3 tags) + new_fusions
(avec 1 fusion ajoutee). Backup .preancres3.bak.

Idempotent : SKIP cles deja taggees ou deja fused. FAIL sur conflit.

Usage :
  python scripts/_fix_ancres_social_3_dl.py <JWT_TOKEN>
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT_P  = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".preancres3.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CIBLES_ASSIGN = [
    ("25|RUE|ST EUSEBE",          "social"),
    ("29|RUE|ETIENNE RICHERAND",  "social"),
    ("11|RUE|TERNOIS",            "social"),
]
FUSION_SRC = "11|RUE|TERNOIS"
FUSION_DST = "28|RUE|ETIENNE RICHERAND"


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
print("KV DL : 3 tags social + 1 fusion 11 TERNOIS -> 28 ETIENNE RICHERAND")
print("=" * 90)

# 1. Verif anti-race : cles existent dans light + 28 RICHERAND sans tag
print()
print("  Verif light (anti-race) :")
light = json.loads(LIGHT_P.read_text(encoding="utf-8"))
adr_by_cle = {(a.get("cle") or ""): a for a in (light.get("adresses") or [])}
verif_cles = [c for c, _ in CIBLES_ASSIGN] + [FUSION_DST]
for cle in verif_cles:
    a = adr_by_cle.get(cle)
    if not a: fail(f"{cle} absent du light")
    print(f"    {cle:<35} bgid={a.get('batiment_groupe_id')}  bdnb={a.get('nb_log_bdnb')}")

# 2. GET KV live
print()
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions")

# 3. Audit ACTION 1 (tags assignments)
print()
print("  ACTION 1 - Audit tags social :")
to_assign = []
skip_assign = []
for cle, target in CIBLES_ASSIGN:
    cur = assigns.get(cle)
    tag = (cur or {}).get("type")
    if tag == target:
        print(f"    {cle:<35} SKIP (deja type={target})")
        skip_assign.append(cle)
    elif tag:
        fail(f"CONFLIT : {cle} a tag actuel = {tag!r}, attendu vide (ou {target})")
    else:
        print(f"    {cle:<35} CREATE type={target}")
        to_assign.append((cle, target))

# Verif 28 RICHERAND : doit etre sans tag KV (sinon on n'attribue pas la fusion)
tag_dst = (assigns.get(FUSION_DST) or {}).get("type")
print(f"    {FUSION_DST:<35} tag KV actuel = {tag_dst!r}")
if tag_dst:
    print(f"    [INFO] {FUSION_DST} a deja un tag KV -- la fusion s'applique quand meme")

# 4. Audit ACTION 2 (fusion)
print()
print("  ACTION 2 - Audit fusion :")
cur_fus = fusions.get(FUSION_SRC)
add_fusion = True
if cur_fus == FUSION_DST:
    print(f"    {FUSION_SRC} -> {FUSION_DST}  SKIP (deja fused)")
    add_fusion = False
elif cur_fus:
    fail(f"CONFLIT : {FUSION_SRC} deja fused vers {cur_fus!r}")
else:
    print(f"    {FUSION_SRC} -> {FUSION_DST}  ADD")

if not to_assign and not add_fusion:
    print(); print("=" * 90); print(">>> IDEMPOTENT : rien a faire"); print("=" * 90); sys.exit(0)

# 5. Backup
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print(); print(f"  Backup KV local : {BAK.name}")

# 6. Rebuild + POST atomique
new_assigns = dict(assigns)
for cle, target in to_assign:
    new_assigns[cle] = {**(assigns.get(cle) or {}), "type": target}
new_fusions = dict(fusions)
if add_fusion:
    new_fusions[FUSION_SRC] = FUSION_DST
print()
print(f"  POST atomique :")
print(f"    assigns  : {len(assigns)} -> {len(new_assigns)} (+{len(to_assign)} social)")
print(f"    fusions  : {len(fusions)} -> {len(new_fusions)} (+{int(add_fusion)})")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": new_fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

# 7. Re-GET verif
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
fusions_after = kv_after.get("fusions") or {}
print(f"  Re-GET : {len(assigns_after)} assigns, {len(fusions_after)} fusions")
print()
print("  Verif post-POST :")
errs = []
for cle, target in to_assign:
    after = assigns_after.get(cle)
    if not after or after.get("type") != target:
        print(f"    {cle:<35} KO type={after.get('type') if after else None!r}")
        errs.append(cle)
    else:
        print(f"    {cle:<35} OK type={target}")
if add_fusion:
    if fusions_after.get(FUSION_SRC) != FUSION_DST:
        print(f"    fusion {FUSION_SRC} -> {FUSION_DST}  KO live={fusions_after.get(FUSION_SRC)!r}")
        errs.append("fusion")
    else:
        print(f"    fusion {FUSION_SRC} -> {FUSION_DST}  OK")
if errs: fail(f"POST incomplet : {errs}")

# 8. Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : +{len(to_assign)} tag(s) social + {int(add_fusion)} fusion(s)")
print(f"    KV final : {len(assigns_after)} assigns, {len(fusions_after)} fusions")
print("=" * 90)
