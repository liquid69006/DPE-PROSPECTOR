#!/usr/bin/env python3
"""Diag 132 vs 133 RUE BARABAN (lecture seule).

Repond a :
  1. bgid + parcelle BDNB + libelle_adr_principale_ban pour 132 et 133
  2. Meme parcelle cadastrale ?
  3. BAN reconnait-il '132 BARABAN' ou uniquement '133 BARABAN' ?
  4. 132 a-t-il son propre bgid BDNB ou partage-t-il celui du 133 ?

Sources : light + BAN api-adresse + BDNB rel_batiment_groupe_adresse +
batiment_groupe_complet + rel_batiment_groupe_parcelle.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"


def http_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def ban_search(q, limit=3):
    url = ("https://api-adresse.data.gouv.fr/search/"
           f"?limit={limit}&q=" + urllib.parse.quote(q))
    return http_json(url).get("features", [])


def bdnb_bg_for_ban(cle_interop):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle_interop)}"
           "&select=batiment_groupe_id")
    return [r["batiment_groupe_id"] for r in http_json(url)]


def bdnb_parcelles(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    return [p["parcelle_id"] for p in http_json(url)]


def bdnb_pivot(bgs):
    if not bgs:
        return []
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
           "numero_immat_principal,nb_adresse_valid_ban"
           f"&batiment_groupe_id=in.({','.join(bgs)})")
    return http_json(url, timeout=20)


# ---------- 1. light ----------
print("=" * 76)
print("DIAG 132 vs 133 RUE BARABAN")
print("=" * 76)
print()
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}

print("[1] Etat light :")
for cle in ("132|RUE|BARABAN", "133|RUE|BARABAN", "131|RUE|BARABAN", "134|RUE|BARABAN"):
    a = by_cle.get(cle)
    if not a:
        print(f"    {cle:30s} ABSENT light")
        continue
    bg = a.get("batiment_groupe_id") or ""
    cp = co_by_cle.get(cle, {})
    immat = cp.get("numero_immatriculation") or a.get("numero_immatriculation") or "-"
    nom = cp.get("nom_copropriete") or ""
    print(f"    {cle:30s} bgid=...{bg[-9:]:9s} bdnb={a.get('nb_log_bdnb') or 0:3d} "
          f"vlog={a.get('nb_ventes_logement') or 0:2d} immat={immat:12s} "
          f"FA={a.get('_fusion_auto')}  '{nom[:35]}'")

# Adresses partageant les 2 bgids
bgs_set = set()
for cle in ("132|RUE|BARABAN", "133|RUE|BARABAN"):
    a = by_cle.get(cle)
    if a and a.get("batiment_groupe_id"):
        bgs_set.add(a["batiment_groupe_id"])

print()
print("[1b] Adresses light partageant ces bgids :")
for a in doc["adresses"]:
    if a.get("batiment_groupe_id") in bgs_set:
        bg = a["batiment_groupe_id"]
        cp = co_by_cle.get(a.get("cle") or "", {})
        immat = cp.get("numero_immatriculation") or "-"
        print(f"    bgid=...{bg[-9:]} : {a.get('cle'):30s} bdnb={a.get('nb_log_bdnb')} "
              f"immat={immat:12s} FA={a.get('_fusion_auto')} cible={a.get('_fusion_cible')}")

# ---------- 2. BAN ----------
print()
print("[2] BAN api-adresse reconnait-il 132 / 133 BARABAN ?")
for q in ("132 rue baraban 69003 Lyon",
          "133 rue baraban 69003 Lyon",
          "131 rue baraban 69003 Lyon",
          "134 rue baraban 69003 Lyon"):
    try:
        feats = ban_search(q, limit=3)
    except Exception as e:
        print(f"    {q:36s} ERR {e}")
        continue
    if not feats:
        print(f"    {q:36s} 0 feature")
        continue
    for f in feats[:3]:
        p = f["properties"]
        score = round(p.get("score") or 0.0, 4)
        print(f"    {q:36s} BAN={p.get('id'):26s} '{p.get('name','')}' "
              f"type={p.get('type','')} score={score}")
    time.sleep(0.05)

# ---------- 3. BAN -> BDNB bgid mapping ----------
print()
print("[3] BAN -> BDNB bgid (autorite) :")
bgs_ban = set()
for q in ("132 rue baraban 69003 Lyon", "133 rue baraban 69003 Lyon"):
    try:
        feats = ban_search(q, limit=1)
    except Exception as e:
        print(f"    {q:36s} ERR {e}")
        continue
    if not feats:
        print(f"    {q:36s} 0 feature BAN")
        continue
    p = feats[0]["properties"]
    ban_id = p.get("id") or ""
    try:
        bgs = bdnb_bg_for_ban(ban_id)
    except Exception as e:
        bgs = [f"ERR {e}"]
    print(f"    {q:36s} BAN={ban_id} '{p.get('name','')}' -> bgid {bgs}")
    for b in bgs:
        if isinstance(b, str) and b.startswith("bdnb-bg-"):
            bgs_set.add(b)
            bgs_ban.add(b)
    time.sleep(0.05)

# ---------- 4. BDNB pivot ----------
print()
print("[4] BDNB pivot batiment_groupe_complet :")
try:
    pivots = bdnb_pivot(sorted(bgs_set))
except Exception as e:
    pivots = []
    print(f"    ERR pivot {e}")
for p in pivots:
    bg = p.get("batiment_groupe_id") or ""
    print(f"\n    {bg[-9:]} :")
    print(f"      libelle_adr_principale_ban = '{p.get('libelle_adr_principale_ban','')}'")
    print(f"      nb_adresse_valid_ban       = {p.get('nb_adresse_valid_ban')}")
    print(f"      nb_log                     = {p.get('nb_log')}  "
          f"nb_log_rnc={p.get('nb_log_rnc')}")
    print(f"      annee_construction         = {p.get('annee_construction')}")
    print(f"      usage_principal            = "
          f"{(p.get('usage_principal_bdnb_open') or '')[:40]}")
    print(f"      numero_immat_principal     = {p.get('numero_immat_principal') or '-'}")
    print(f"      l_libelle_adr :")
    for x in p.get("l_libelle_adr") or []:
        print(f"        . {x}")

# ---------- 5. Parcelles BDNB ----------
print()
print("[5] Parcelles BDNB par bgid :")
parcs_par_bg = {}
all_parcs = set()
for bg in sorted(bgs_set):
    try:
        parcs = bdnb_parcelles(bg)
    except Exception as e:
        parcs = []
        print(f"    {bg} ERR {e}")
        continue
    parcs_par_bg[bg] = parcs
    for p in parcs:
        all_parcs.add(p)
    print(f"    {bg} -> {parcs}")

# ---------- 6. Reponses synthese ----------
print()
print("=" * 76)
print("SYNTHESE :")
print("=" * 76)
a132 = by_cle.get("132|RUE|BARABAN") or {}
a133 = by_cle.get("133|RUE|BARABAN") or {}
bg132 = a132.get("batiment_groupe_id") or "-"
bg133 = a133.get("batiment_groupe_id") or "-"
print(f"  bgid light    132 BARABAN : ...{bg132[-9:]}")
print(f"  bgid light    133 BARABAN : ...{bg133[-9:]}")
print(f"  Memes bgid (light) ?       : {bg132 == bg133}")

# autorite BAN
bgs132 = []
bgs133 = []
try:
    feats132 = ban_search("132 rue baraban 69003 Lyon", limit=1)
    if feats132:
        bgs132 = bdnb_bg_for_ban(feats132[0]["properties"]["id"])
except Exception:
    pass
try:
    feats133 = ban_search("133 rue baraban 69003 Lyon", limit=1)
    if feats133:
        bgs133 = bdnb_bg_for_ban(feats133[0]["properties"]["id"])
except Exception:
    pass
print(f"  bgid BAN auto 132 BARABAN  : {bgs132}")
print(f"  bgid BAN auto 133 BARABAN  : {bgs133}")
inter = set(bgs132) & set(bgs133)
print(f"  intersection bgid (BAN)    : {sorted(inter) if inter else '(aucune)'}")

# parcelles
parcs132 = set()
parcs133 = set()
if bg132 and bg132 != "-":
    parcs132 = set(parcs_par_bg.get(bg132, []))
if bg133 and bg133 != "-":
    parcs133 = set(parcs_par_bg.get(bg133, []))
print(f"  parcelles bgid 132 (light) : {sorted(parcs132)}")
print(f"  parcelles bgid 133 (light) : {sorted(parcs133)}")
inter_p = parcs132 & parcs133
print(f"  intersection parcelles     : {sorted(inter_p) if inter_p else '(aucune)'}")

# bgid BAN autoritaire
parcs_ban = {}
for bg in (bgs_ban - {bg132, bg133}):
    try:
        parcs_ban[bg] = bdnb_parcelles(bg)
    except Exception:
        parcs_ban[bg] = []
if parcs_ban:
    print(f"  parcelles bgids BAN nouvelles :")
    for bg, ps in parcs_ban.items():
        print(f"    {bg} -> {ps}")
