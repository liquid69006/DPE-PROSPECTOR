# -*- coding: utf-8 -*-
"""Inspection READ-ONLY de la repartition conseillers DL (aucun POST/PATCH).

Usage: PYTHONUTF8=1 python scripts/inspect_secteur_repartition_dl.py
Pre-requis: $env:DPE_JWT charge (. scripts/load_jwt.ps1) dans LA MEME session.
"""
import json, os, sys, urllib.request, urllib.error

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
SECID = "dauphine-lacassagne"


def get(path):
    tok = os.environ.get("DPE_JWT")
    if not tok:
        sys.exit("ERREUR: $env:DPE_JWT absent (lancer . scripts/load_jwt.ps1 dans CETTE session)")
    req = urllib.request.Request(f"{API}{path}",
                                 headers={"Authorization": f"Bearer {tok}",
                                          "User-Agent": "Mozilla/5.0",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} (GET {path}): {e.read().decode()}")
        raise


data = get(f"/secteur-repartition/{SECID}")
rep = (data or {}).get("repartition", {}) or {}
conseillers = (data or {}).get("conseillers", []) or []

print("=== /secteur-repartition/%s ===" % SECID)
print("repartition : %s (%d entrees)" % ("NON VIDE" if rep else "{} (VIDE)", len(rep)))
print()

print("=== Conseillers (%d) ===" % len(conseillers))
if conseillers:
    for c in conseillers:
        print("  id=%s nom=%s couleur=%s" % (c.get("id"), c.get("nom"), c.get("couleur")))
else:
    print("  (aucun)")
print()

def entry(ilot):
    e = rep.get(str(ilot)) or rep.get(ilot)
    return e

print("=== Ilot 49 ===")
e49 = entry(49)
if e49 is None:
    print("  (absent de la repartition)")
else:
    print("  conseillerId=%s locked=%s" % (e49.get("conseillerId"), e49.get("locked")))
print()

print("=== 82 / 85 deja presents ? (attendu : non) ===")
for il in ("82", "85"):
    print("  %s : %s" % (il, "PRESENT -> %s" % rep.get(il) if il in rep else "absent"))
print()

print("=== Mapping complet ilot -> conseiller (trie) ===")
nom_by_id = {c.get("id"): c.get("nom") for c in conseillers}
def sortkey(k):
    ks = str(k)
    return (0, int(ks)) if ks.isdigit() else (1, ks)
for k in sorted(rep.keys(), key=sortkey):
    e = rep[k] or {}
    cid = e.get("conseillerId")
    print("  ilot %-4s -> %-10s (%s) locked=%s" % (k, cid, nom_by_id.get(cid, "?"), e.get("locked")))
if not rep:
    print("  (repartition vide)")
