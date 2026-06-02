# -*- coding: utf-8 -*-
"""Applique la nouvelle palette de couleurs aux conseillers DL (secteur_repartition).
DRY-RUN par defaut ; --go pour POST full-replace.

Usage:
    PYTHONUTF8=1 python scripts/apply_palette_repartition_dl.py          # dry-run (aucun POST)
    PYTHONUTF8=1 python scripts/apply_palette_repartition_dl.py --go     # POST effectif

Pre-requis POST: $env:DPE_JWT charge (. scripts/load_jwt.ps1) dans LA MEME session.

Rituel:
  1. GET live -> backup horodate data/_kv_repartition_dl.<ts>.bak.
  2. Charger l'objet complet (adresse_agence, conseillers[], repartition{}, ...).
  3. Par conseiller : couleur := PALETTE[id] ; supprimer 'kind'/'stripe' s'ils existent.
     Rien d'autre touche (id, nom, repartition, locked, autres champs).
  4. Audit avant/apres des couleurs + repartition strictement identique.
  5. --go : POST full-replace ; re-GET : seules les couleurs changent, repartition inchangee.
"""
import json, os, sys, copy, urllib.request, urllib.error
from datetime import datetime

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
SECID = "dauphine-lacassagne"
PALETTE = {
    "sec-1": "#E03131", "sec-2": "#F76707", "sec-3": "#FCC419", "sec-4": "#69DB7C",
    "sec-5": "#2B8A3E", "sec-6": "#4DABF7", "sec-7": "#1864AB", "sec-8": "#7048E8",
    "sec-9": "#E64980", "sec-10": "#868E96",
}
GO = "--go" in sys.argv


def _req(path, data=None, method="GET"):
    tok = os.environ.get("DPE_JWT")
    if not tok:
        sys.exit("ERREUR: $env:DPE_JWT absent (lancer . scripts/load_jwt.ps1 dans CETTE session)")
    headers = {"Authorization": f"Bearer {tok}", "User-Agent": "Mozilla/5.0",
               "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} ({method} {path}): {e.read().decode()}")
        raise


def repmap(obj):
    """ilot -> conseillerId (pour comparer le mapping a l'identique)."""
    return {k: (v or {}).get("conseillerId") for k, v in (obj.get("repartition", {}) or {}).items()}


def repfull(obj):
    return obj.get("repartition", {}) or {}


# --- 1. GET live + backup horodate ---
live = _req(f"/secteur-repartition/{SECID}")
if not live or not isinstance(live, dict) or not live.get("conseillers"):
    sys.exit("ABORT: repartition live vide ou sans conseillers -> rien a faire.")
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
bak = f"data/_kv_repartition_dl.{ts}.bak"
json.dump(live, open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
cons = live.get("conseillers", [])
print(f"1. GET live OK : {len(cons)} conseillers, {len(repfull(live))} entrees repartition -> backup {bak}")

# --- 2/3. build : couleur := PALETTE[id], retire kind/stripe ---
new = copy.deepcopy(live)
unknown = []
for c in new.get("conseillers", []):
    cid = c.get("id")
    if cid in PALETTE:
        c["couleur"] = PALETTE[cid]
        c.pop("kind", None)
        c.pop("stripe", None)
    else:
        unknown.append(cid)
if unknown:
    print(f"   AVERTISSEMENT: conseiller(s) hors palette, couleur inchangee: {unknown}")

# --- 4. audit avant/apres ---
print("\n4. audit couleurs avant -> apres :")
old_by = {c.get("id"): c for c in live.get("conseillers", [])}
for c in new.get("conseillers", []):
    cid = c.get("id"); o = old_by.get(cid, {})
    flags = []
    if "kind" in o:
        flags.append("kind:%s retire" % o.get("kind"))
    if "stripe" in o:
        flags.append("stripe retire")
    print("   %-7s %-22s %s -> %s%s" % (
        cid, "(" + str(c.get("nom")) + ")",
        o.get("couleur"), c.get("couleur"),
        ("  [" + ", ".join(flags) + "]") if flags else ""))

# repartition strictement identique
same_full = repfull(live) == repfull(new)
same_map = repmap(live) == repmap(new)
print("\n   repartition identique (objet complet) :", same_full)
print("   mapping ilot->conseiller identique     :", same_map)
print("   nb entrees repartition avant/apres     : %d / %d" % (len(repfull(live)), len(repfull(new))))
# autres champs top-level inchanges
for k in ("adresse_agence", "agence_lat", "agence_lng"):
    print("   %-15s avant=%r apres=%r" % (k, live.get(k), new.get(k)))
assert same_full, "ABORT: repartition modifiee -> STOP"
# diff doit se limiter au champ couleur (+ retrait kind/stripe) des conseillers
chg_cons = [c.get("id") for c in new["conseillers"]
            if c != old_by.get(c.get("id"))]
print("   conseillers modifies :", chg_cons)

if not GO:
    print("\nDRY-RUN (pas de --go) : AUCUN POST effectue.")
    sys.exit(0)

# --- 5. POST full-replace + re-GET verif ---
body = json.dumps(new).encode("utf-8")
res = _req(f"/secteur-repartition/{SECID}", data=body, method="POST")
print("\n5. POST OK:", res)

live2 = _req(f"/secteur-repartition/{SECID}")
# verif : couleurs == palette, repartition inchangee
col2 = {c.get("id"): c.get("couleur") for c in live2.get("conseillers", [])}
bad = [cid for cid, hexa in PALETTE.items() if cid in col2 and col2[cid] != hexa]
assert not bad, f"ABORT post-POST: couleurs incorrectes pour {bad}"
assert repfull(live2) == repfull(live), "ABORT post-POST: repartition modifiee !"
assert len(repfull(live2)) == len(repfull(live)), "ABORT post-POST: nb entrees repartition change"
# aucun kind/stripe residuel
resid = [c.get("id") for c in live2.get("conseillers", []) if "kind" in c or "stripe" in c]
assert not resid, f"ABORT post-POST: kind/stripe residuel sur {resid}"
print("6. re-GET verif OK : 10 couleurs appliquees, repartition (%d entrees) inchangee, aucun kind/stripe." % len(repfull(live2)))
