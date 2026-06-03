#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B2a Montchat - PATCH KV : POST du candidat (103 tags bureaux+mono).

Miroir de scripts/_b2_post_dl.py pour secteur_assignments:dauphine-lacassagne-montchat.
Un seul POST.

A lancer dans une session PowerShell ou DPE_JWT est charge, APRES
_b2a_backup_diff_montchat.py :
    . scripts\\load_jwt.ps1
    python scripts\\_b2a_post_montchat.py

Sequence :
  1. GARDE ANTI-DRIFT : GET prod (gracieux) ; si prod != backup (.bak) -> ABORT,
     imprime la difference, AUCUN POST.
  2. POST : si prod == backup, POST l'objet candidat complet (un seul POST).
  3. VERIF : re-GET prod ; confirme prod == candidat (nos 103 tags presents,
     aucune autre cle touchee). KO -> alerte forte, NE PAS toucher au miroir.
  4. MIROIR LOCAL : ecrit l'etat prod re-GET dans data/_kv_assign_montchat.json
     (PAS de git commit ici).
"""
import os
import sys
import json
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne-montchat"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_kv_assign_montchat.b2a.preaudit.bak"
CANDIDATE = ROOT / "data" / "_kv_assign_montchat.b2a.candidate.json"
MIRROR = ROOT / "data" / "_kv_assign_montchat.json"

ALLOWED_TYPES = {"bureaux", "mono"}


def abort(msg):
    print(f"  [ABORT] {msg}")
    sys.exit(1)


def norm(obj):
    return {
        "assignments": obj.get("assignments", {}) or {},
        "fusions": obj.get("fusions", {}) or {},
        "noms": obj.get("noms", {}) or {},
    }


def diff_view(a, b):
    out = []
    for sect in ("assignments", "fusions", "noms"):
        ka, kb = a[sect], b[sect]
        for k in sorted(set(ka) | set(kb)):
            if ka.get(k) != kb.get(k):
                out.append(f"    [{sect}] {k}: prod={ka.get(k)} != ref={kb.get(k)}")
    return out


def get_prod(jwt):
    req = urllib.request.Request(
        f"{API}/secteur-assignments/{AGENCE}",
        headers={"Authorization": f"Bearer {jwt}", "User-Agent": "Mozilla/5.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"assignments": {}, "fusions": {}, "noms": {}}
        raise
    obj = json.loads(raw) if raw.strip() else {}
    return obj


def post_candidate(jwt, candidate):
    body = json.dumps({
        "assignments": candidate.get("assignments", {}),
        "fusions": candidate.get("fusions", {}),
        "noms": candidate.get("noms", {}),
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/secteur-assignments/{AGENCE}",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {jwt}",
                 "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def main():
    jwt = os.environ.get("DPE_JWT") or ""
    if not jwt:
        abort("env var DPE_JWT absente. Charger d'abord : . scripts\\load_jwt.ps1")
    if not BACKUP.exists():
        abort(f"backup absent : {BACKUP.name} (relancer _b2a_backup_diff_montchat.py).")
    if not CANDIDATE.exists():
        abort(f"candidat absent : {CANDIDATE.name} (relancer le backup-diff).")

    backup_raw = BACKUP.read_text(encoding="utf-8")
    backup = json.loads(backup_raw) if backup_raw.strip() else {}
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    nb = norm(backup)
    nc = norm(candidate)

    print("=" * 64)
    print("B2a Montchat - PATCH KV (POST candidat, 103 tags bureaux+mono)")
    print("=" * 64)

    # sanity candidat = backup + uniquement des ajouts/no-op bureaux|mono
    ba, ca = nb["assignments"], nc["assignments"]
    removed = [k for k in ba if k not in ca]
    changed = [k for k in set(ba) & set(ca)
               if (ba.get(k) or {}) != (ca.get(k) or {})]
    added = [k for k in ca if k not in ba]
    if removed:
        abort(f"candidat local : retraits inattendus {removed[:20]}.")
    if changed:
        abort(f"candidat local : modifs de cles existantes {changed[:20]} "
              "(devrait etre 0 ; on n'ecrase rien).")
    for k in added:
        if (ca.get(k) or {}).get("type") not in ALLOWED_TYPES:
            abort(f"candidat local : ajout {k} type invalide {ca.get(k)}.")
    if nb["fusions"] != nc["fusions"] or nb["noms"] != nc["noms"]:
        abort("candidat local : fusions/noms modifies (doivent etre inchanges).")
    n_bur = sum(1 for k in added if ca[k].get("type") == "bureaux")
    n_mono = sum(1 for k in added if ca[k].get("type") == "mono")
    print(f"  candidat local OK : +{len(added)} ajouts "
          f"({n_bur} bureaux + {n_mono} mono), 0 retrait/modif.")

    # ---- 1. GARDE ANTI-DRIFT ----
    print("  1. garde anti-drift : GET prod vs backup ...")
    try:
        prod = get_prod(jwt)
    except Exception as e:
        abort(f"GET prod echoue : {e}")
    npd = norm(prod)
    if npd != nb:
        d = diff_view(npd, nb)
        print(f"     prod != backup ({len(d)} difference(s)) :")
        for line in d[:50]:
            print(line)
        abort("le KV a bouge depuis le backup -> candidat perime, REBUILD requis. "
              "AUCUN POST.")
    print(f"     prod == backup OK (assignments={len(ba)}, "
          f"fusions={len(nb['fusions'])}, noms={len(nb['noms'])})")

    # ---- 2. POST (unique) ----
    print("  2. POST candidat ...")
    try:
        res = post_candidate(jwt, candidate)
    except Exception as e:
        abort(f"POST echoue : {e}")
    print(f"     reponse worker : {json.dumps(res, ensure_ascii=False)}")

    # ---- 3. VERIF : re-GET == candidat ----
    print("  3. verif : re-GET prod == candidat ...")
    try:
        prod2 = get_prod(jwt)
    except Exception as e:
        abort(f"re-GET echoue (POST possiblement applique) : {e} "
              "-- NE PAS toucher au miroir, verifier manuellement.")
    np2 = norm(prod2)
    if np2 != nc:
        d = diff_view(np2, nc)
        print(f"     !! VERIF KO : re-GET != candidat ({len(d)} diff) :")
        for line in d[:50]:
            print(line)
        abort("ALERTE : etat prod apres POST != candidat. Miroir local NON "
              "modifie. Investiguer avant toute autre action.")
    # nos tags presents + rien d'autre touche
    bad = [k for k in added if (np2["assignments"].get(k) or {}).get("type")
           != ca[k].get("type")]
    drift = [k for k in set(ba) | set(np2["assignments"])
             if k not in added and (ba.get(k) or {}) != (np2["assignments"].get(k) or {})]
    if bad or drift or np2["fusions"] != nb["fusions"] or np2["noms"] != nb["noms"]:
        print(f"     !! verif fine KO : bad_tags={bad[:20]} drift={sorted(drift)[:20]}")
        abort("ALERTE : etat prod incoherent. Miroir NON modifie.")
    print(f"     verif OK : prod == candidat (assignments={len(np2['assignments'])}, "
          f"dont +{len(added)} B2a). Reste inchange.")

    # ---- 4. MIROIR LOCAL ----
    MIRROR.write_text(json.dumps(prod2, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  4. miroir local mis a jour -> {MIRROR.name} (PAS de git commit ici).")
    print("=" * 64)
    print("  PATCH applique et verifie. Commit du miroir = manche suivante.")


if __name__ == "__main__":
    main()
