#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche F Montchat - backup + safety diff KV, AUCUN POST.

Calque de scripts/_D_backup_diff_montchat.py pour la manche F
(secteur_assignments:dauphine-lacassagne-montchat). Pose F = +N tags as.type
social|mixte (hors-RNC bailleurs), AJOUTES par-dessus les 381 (103 B2a + 278 D).

Le candidat (data/_kv_assign_montchat.F.candidate.json) est l'OBJET POST COMPLET
genere par scripts/_F_derive_montchat.py. Ce script :
  A. GET prod -> data/_kv_assign_montchat.F.preaudit.bak (GET gracieux 404 -> {}).
  B. confirme qu'AUCUN des nouveaux tags F n'ecrase un tag existant DIFFERENT
     (no-op identique tolere ; valeur DIFFERENTE : STOP).
  C. SAFETY DIFF candidat vs prod : 0 retrait, 0 modif de cle non-F, ajouts/no-op
     uniquement.

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_F_backup_diff_montchat.py
"""
import os
import sys
import json
import copy
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne-montchat"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_kv_assign_montchat.F.preaudit.bak"
CANDIDATE = ROOT / "data" / "_kv_assign_montchat.F.candidate.json"

ALLOWED_TYPES = {"bureaux", "mono", "copro_non_immat", "social", "mixte"}
# Les NOUVEAUX tags (manche F) sont uniquement social | mixte.
ALLOWED_NEW_TYPES = {"social", "mixte"}


def abort(msg):
    print(f"  [STOP] {msg}")
    sys.exit(1)


def get_prod_graceful(jwt):
    req = urllib.request.Request(
        f"{API}/secteur-assignments/{AGENCE}",
        headers={"Authorization": f"Bearer {jwt}", "User-Agent": "Mozilla/5.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"assignments": {}, "fusions": {}, "noms": {}}, "{}"
        abort(f"GET HTTP {e.code} : {e}")
    except Exception as e:
        abort(f"GET echoue : {e}")
    obj = json.loads(raw) if raw.strip() else {}
    return {
        "assignments": obj.get("assignments", {}) or {},
        "fusions": obj.get("fusions", {}) or {},
        "noms": obj.get("noms", {}) or {},
    }, raw


def main():
    jwt = os.environ.get("DPE_JWT") or ""
    if not jwt:
        abort("env var DPE_JWT absente. Charger d'abord : . scripts\\load_jwt.ps1")
    if not CANDIDATE.exists():
        abort(f"candidat absent : {CANDIDATE.name} "
              "(relancer scripts\\_F_derive_montchat.py).")

    cand = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    cand_assign = cand.get("assignments", {}) or {}
    if not cand_assign:
        abort("candidat vide (0 tag).")
    for k, v in cand_assign.items():
        if (v or {}).get("type") not in ALLOWED_TYPES:
            abort(f"candidat : tag inattendu {k} -> {v} "
                  "(attendu bureaux|mono|copro_non_immat|social|mixte).")

    print("=" * 64)
    print("Manche F Montchat - BACKUP + SAFETY DIFF (candidat complet, aucun POST)")
    print("=" * 64)
    print(f"  candidat (POST complet) : {len(cand_assign)} entrees")

    # ---- A. GET prod + backup ----
    prod, raw = get_prod_graceful(jwt)
    BACKUP.write_text(raw, encoding="utf-8")
    assigns = prod["assignments"]
    print(f"  A. backup prod -> {BACKUP.name}")
    print(f"     prod assignments={len(assigns)} fusions={len(prod['fusions'])} "
          f"noms={len(prod['noms'])}")

    # ---- B. aucun de nos NOUVEAUX tags n'ecrase un tag DIFFERENT ----
    conflicts = []
    noops = []
    added = []
    for k, v in cand_assign.items():
        cur = (assigns.get(k) or {}).get("type")
        if cur is None:
            added.append(k)
            if v.get("type") not in ALLOWED_NEW_TYPES:
                abort(f"ajout {k} type {v.get('type')} non autorise en manche F "
                      "(attendu social|mixte).")
        elif cur == v.get("type"):
            noops.append(k)
        else:
            conflicts.append((k, cur, v.get("type")))
    if conflicts:
        for k, cur, new in conflicts:
            print(f"     [!!] {k}: prod={cur} != candidat={new}")
        abort(f"{len(conflicts)} conflit(s) : nos tags ecraseraient des valeurs "
              "DIFFERENTES. On n'ecrase pas. Investiguer.")
    print(f"  B. 0 conflit (no-op deja-taggees identiques : {len(noops)}, "
          f"ajouts : {len(added)})")

    # ---- C. SAFETY DIFF (candidat complet vs prod) ----
    cand_full = {"assignments": copy.deepcopy(cand_assign),
                 "fusions": copy.deepcopy(cand.get("fusions", {}) or {}),
                 "noms": copy.deepcopy(cand.get("noms", {}) or {})}
    removed = [k for k in assigns if k not in cand_full["assignments"]]
    changed = [k for k in set(assigns) & set(cand_full["assignments"])
               if (assigns.get(k) or {}) != (cand_full["assignments"].get(k) or {})]

    print("  C. SAFETY DIFF (candidat vs backup) :")
    print(f"     assignments {len(assigns)} -> {len(cand_full['assignments'])} "
          f"(ajouts={len(added)} modifs={len(changed)} retraits={len(removed)})")
    ok = True
    if removed:
        ok = False
        print(f"     !! retraits inattendus : {sorted(removed)[:20]}")
    if changed:
        ok = False
        print(f"     !! modifs de cles existantes (devrait etre 0) : "
              f"{sorted(changed)[:20]}")
    if prod["fusions"] != cand_full["fusions"] or prod["noms"] != cand_full["noms"]:
        ok = False
        print("     !! fusions/noms differents du prod (ne devraient pas)")
    if not ok:
        abort("safety diff NON conforme. NE PAS POSTER. Investiguer.")

    print(f"     DIFF CONFORME : +{len(added)} ajouts, {len(noops)} no-op, "
          f"0 retrait, 0 modif.")
    print(f"     candidat pret -> {CANDIDATE.name} (PAS encore POSTe)")
    print("=" * 64)
    print("  STOP. Aucun POST. Valider avant _F_post_montchat.py.")


if __name__ == "__main__":
    main()
