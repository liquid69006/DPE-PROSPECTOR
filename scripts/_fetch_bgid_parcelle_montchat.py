#!/usr/bin/env python3
"""Fetcher resumable + rate-limit-aware du cache bgid->parcelle pour montchat.

Produit EXACTEMENT le format consomme par enrich_majic_full.py :
  data/_bgid_parcelle_montchat.json = { "<bgid>": ["69383000CT0056", ...], ... }

Differences vs fetch_bdnb_parcelles_batch() interne :
- throttle plus doux (0.25s) + backoff exponentiel sur HTTP 429
- CHECKPOINT disque toutes les 25 entrees (le code interne n ecrit qu en fin
  de boucle -> un crash perdait tout)
- RESUMABLE : ne (re)fetch que les bgids ABSENTS du cache OU caches VIDES []
  (donc un 2e run repare les trous 429 ; l interne, lui, garde le [] et ne
  retente jamais -> c est pourquoi on n utilise PAS la completion interne ici)

Aucune ecriture KV. Aucun commit. ASCII-safe.
"""
import json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from secteur_config import load_secteur

THROTTLE = 0.25      # s entre 2 appels OK
CHECKPOINT = 25      # ecrit le cache tous les N fetch
MAX_RETRY = 6        # tentatives par bgid sur 429/erreur transitoire


def fetch_one(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    backoff = 1.0
    for attempt in range(1, MAX_RETRY + 1):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                rows = json.loads(r.read())
            return [x.get("parcelle_id") for x in rows if x.get("parcelle_id")], None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = backoff
                time.sleep(wait)
                backoff = min(backoff * 2, 30)
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue
    return None, "max_retry"


def main():
    cfg = load_secteur("montchat")
    light = json.loads(cfg.light.read_text(encoding="utf-8"))
    bgids = sorted({a.get("batiment_groupe_id") for a in light["adresses"]
                    if a.get("batiment_groupe_id")})
    cache_path = cfg.cache_bg
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    # A faire = absents OU caches vides (repare les trous 429 d un run precedent)
    todo = [b for b in bgids if b not in cache or not cache.get(b)]
    print("=" * 78)
    print("FETCH bgid->parcelle montchat (resumable)")
    print("=" * 78)
    print("bgids light distincts :", len(bgids))
    print("deja resolus (cache>0):", sum(1 for b in bgids if cache.get(b)))
    print("a fetch (absent/vide) :", len(todo))
    if not todo:
        print("RIEN A FAIRE -> cache complet.")
        return

    n_ok = n_empty = n_err = 0
    t0 = time.time()
    for i, bg in enumerate(todo, 1):
        parcs, err = fetch_one(bg)
        if err is not None:
            # on NE cache PAS l echec -> un prochain run reessaiera
            n_err += 1
            print(f"  ! {bg}: {err} (non cache, retente au prochain run)")
        else:
            cache[bg] = parcs
            if parcs:
                n_ok += 1
            else:
                n_empty += 1  # cache [] : bgid sans parcelle BDNB (legitime)
        if i % CHECKPOINT == 0:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
            rate = i / max(0.1, time.time() - t0)
            print(f"  checkpoint {i}/{len(todo)}  ok={n_ok} vide={n_empty} err={n_err}  {rate:.1f} req/s")
        time.sleep(THROTTLE)

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print()
    print("TERMINE :", f"ok={n_ok} vide={n_empty} err={n_err}  duree={time.time()-t0:.0f}s")
    print("cache total entries:", len(cache))
    still = [b for b in bgids if b not in cache or not cache.get(b)]
    print("RESTE a fetch (absent/vide) apres ce run:", len(still))


if __name__ == "__main__":
    main()
