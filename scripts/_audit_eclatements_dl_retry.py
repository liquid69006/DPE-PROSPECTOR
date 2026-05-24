#!/usr/bin/env python3
"""Retry les bgids ayant donne cache vide (429 ou fetch echec).
   Sleep 0.5s + retry exponentiel sur 429. Idempotent : ne re-fetch
   que les bgids avec cache=[].
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
CACHE = ROOT / "data" / "_audit_bdnb_adr_cache.json"

BDNB_ADR = "https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse?batiment_groupe_id=eq."

cache = json.loads(CACHE.read_text(encoding="utf-8"))
empty = [bg for bg, v in cache.items() if not v]
print(f"  cache : {len(cache)} entrees, {len(empty)} vides a re-tester")

# Set de bgids correspondant a une ancre RNC (pour ne pas perdre le scope)
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
co  = doc["coproprietes"]; ad = doc["adresses"]
ad_by_cle = {(a.get("cle") or ""): a for a in ad}
ancres_bgids = set()
for c in co:
    if not c.get("numero_immatriculation"): continue
    a = ad_by_cle.get(c.get("cle_adresse") or "")
    if a and a.get("batiment_groupe_id"):
        ancres_bgids.add(a["batiment_groupe_id"])
empty_in_scope = [b for b in empty if b in ancres_bgids]
print(f"  parmi elles, ancres RNC : {len(empty_in_scope)}")


def fetch(bg, retry=4):
    for attempt in range(retry):
        try:
            url = f"{BDNB_ADR}{bg}&limit=50"
            with urllib.request.urlopen(url, timeout=25) as r:
                rows = json.loads(r.read())
            out = []
            for row in rows:
                lib = row.get("libelle_adresse") or ""
                cleint = row.get("cle_interop_adr") or ""
                if lib:
                    out.append({"libelle": lib, "cle_interop": cleint})
            return out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 1 + attempt * 2
                print(f"    429 sur ...{bg[-9:]} -- backoff {wait}s")
                time.sleep(wait)
                continue
            else:
                print(f"    HTTPError {e.code} ...{bg[-9:]}: {e}")
                return None
        except Exception as e:
            print(f"    err ...{bg[-9:]}: {e}")
            return None
    print(f"    ABANDON ...{bg[-9:]} apres {retry} tentatives")
    return None


ok = ko = 0
for i, bg in enumerate(empty_in_scope, 1):
    r = fetch(bg)
    if r is None:
        ko += 1
        continue
    cache[bg] = r
    ok += 1
    if r:
        print(f"   {i}/{len(empty_in_scope)}  ...{bg[-9:]} -> {len(r)} BAN")
    # Sleep base entre requetes
    time.sleep(0.5)
    if i % 30 == 0:
        # Persiste cache toutes les 30 reqs
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"      [cache persiste, {i} traitees]")

CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n  termine : {ok} OK, {ko} KO (cache final {len(cache)} entrees)")
remaining = sum(1 for b in ancres_bgids if not cache.get(b))
print(f"  bgids ancres restant vides : {remaining}/{len(ancres_bgids)}")
