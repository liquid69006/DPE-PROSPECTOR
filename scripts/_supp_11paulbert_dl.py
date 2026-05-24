#!/usr/bin/env python3
"""Suppression definitive des 11 adresses fantomes PAUL BERT (DL).

Suite des commits 185aaa7 + 3df3355 (decroche bgid+fusion) : le diag
revele que sur les 11 cles, 8 sont totalement inexistantes (ni BAN ni
DVF) et 3 (71, 148, 290) existent physiquement mais sont HORS PERIMETRE
DL (confirmation terrain : 71 Paul Bert est dans la partie ouest de la
rue, hors secteur Dauphine-Lacassagne).

Decision : suppression totale des 11 du light + DELETE KV des 2 tags
poses (71 et 148 = 'copro_non_immat').

Backup light + KV avant ecriture. Re-GET KV apres POST pour confirmer
DELETE. PAS DE PUSH (le user valide).

Token requis : argv[1] ou env DPE_TOKEN.
"""
import argparse, json, sys, os, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT    = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK_LT   = LIGHT.with_suffix(LIGHT.suffix + ".presupp11paulbert.bak")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK_KV   = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".presupp11paulbert.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN","")).strip()
if not TOKEN: print("ERREUR : TOKEN manquant"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

CLES_LIGHT_DEL = ["37|RUE|PAUL BERT", "71|RUE|PAUL BERT", "148|RUE|PAUL BERT",
                  "158|RUE|PAUL BERT", "163|RUE|PAUL BERT", "188|RUE|PAUL BERT",
                  "202|RUE|PAUL BERT", "205|RUE|PAUL BERT", "257|RUE|PAUL BERT",
                  "290|RUE|PAUL BERT", "293|RUE|PAUL BERT"]
CLES_KV_DEL    = ["71|RUE|PAUL BERT", "148|RUE|PAUL BERT"]


def http(method, url, headers, body=None):
    req = urllib.request.Request(
        url, method=method, headers=headers,
        data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


print("=" * 90)
print(f"  SUPP 11 cles PAUL BERT du light + DELETE KV 71 + 148")
print("=" * 90)

# 1. Load + verif
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
ad_by_cle = {a.get("cle"): a for a in ad}

missing = [c for c in CLES_LIGHT_DEL if c not in ad_by_cle]
if missing:
    fail(f"cles introuvables dans light : {missing}")

# Stats avant
total_vlog_lost = sum((ad_by_cle[c].get("nb_ventes_logement") or 0) for c in CLES_LIGHT_DEL)
total_vtot_lost = sum((ad_by_cle[c].get("nb_ventes_total") or 0) for c in CLES_LIGHT_DEL)
print(f"  Light avant : {len(ad)} adresses")
print(f"  Cles a supprimer : {len(CLES_LIGHT_DEL)}")
for c in CLES_LIGHT_DEL:
    a = ad_by_cle[c]
    vl = a.get("nb_ventes_logement") or 0
    vt = a.get("nb_ventes_total") or 0
    bg = a.get("batiment_groupe_id")
    print(f"    {c:24s}  bgid={bg!r:>6}  nb_log_bdnb={a.get('nb_log_bdnb')}  "
          f"v_log={vl}  v_tot={vt}  _ilot={a.get('_ilot')!r}")
print(f"  Total nb_ventes_logement perdues : {total_vlog_lost}  "
      f"(impact header secteur : -{total_vlog_lost} ventes)")
print(f"  Total nb_ventes_total perdues    : {total_vtot_lost}")
print()

# 2. GET KV
print(f"  [GET KV live] ...")
code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV avant : {len(assigns)} assigns")
present_kv = [c for c in CLES_KV_DEL if c in assigns]
print(f"  Cles KV a supprimer : {len(present_kv)} (sur {len(CLES_KV_DEL)} demandees)")
for c in present_kv:
    print(f"    {c:24s} -> {assigns[c]!r}")
absent_kv = [c for c in CLES_KV_DEL if c not in assigns]
if absent_kv:
    print(f"  Deja absentes (idempotent) : {absent_kv}")

# 3. Backups
shutil.copy2(LIGHT, BAK_LT)
print(f"  Backup light : {BAK_LT.name}")
if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK_KV)
    print(f"  Backup KV    : {BAK_KV.name}")

# 4. Apply light : filter out 11 cles
cible_set = set(CLES_LIGHT_DEL)
new_ad = [a for a in ad if a.get("cle") not in cible_set]
removed = len(ad) - len(new_ad)
if removed != len(CLES_LIGHT_DEL):
    fail(f"removed={removed} != attendu {len(CLES_LIGHT_DEL)}")
doc["adresses"] = new_ad
LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
print()
print(f"  Light ecrit : {LIGHT.name}  ({len(ad)} -> {len(new_ad)} adresses, "
      f"-{removed} supprimees)")

# 5. POST KV DELETE
if present_kv:
    new_assigns = {k: v for k, v in assigns.items() if k not in CLES_KV_DEL}
    print()
    print(f"  POST KV : {len(assigns)} -> {len(new_assigns)} (suppr {len(present_kv)})")
    code, raw = http("POST", ENDPOINT, HDR_POST,
                     body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
    print(f"  POST HTTP {code} : {raw[:200]}")
    if code not in (200, 204): fail(f"POST KO {code}")
    # Re-GET verif
    code, raw = http("GET", ENDPOINT, HDR_GET)
    if code != 200: fail(f"Re-GET {code}")
    kv_after = json.loads(raw)
    assigns_after = kv_after.get("assignments") or {}
    print(f"  Re-GET : {len(assigns_after)} assigns")
    errs = [c for c in CLES_KV_DEL if c in assigns_after]
    if errs:
        fail(f"DELETE KV incomplet : {errs}")
    print(f"  Verif : {CLES_KV_DEL} absents post-POST  OK")
    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Sync KV local : {KV_LOCAL.name}")
else:
    print(f"  [no-op KV] aucune cle a supprimer (idempotent)")

print()
print("=" * 90)
print(f">>> SUCCES : light -{removed} adresses, KV -{len(present_kv)} entries")
print(f"    Total ventes header secteur : -{total_vlog_lost} (toutes orphelines bgid=None)")
print("=" * 90)
