#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B2a Montchat - backup + safety diff KV, AUCUN POST.

Miroir de scripts/_b2_backup_diff_dl.py pour le secteur Montchat
(secteur_assignments:dauphine-lacassagne-montchat). Pose B2a = 103 tags as.type :
34 BUREAUX + 69 MONO (hors-RNC actifs). KV Montchat NEUF (attendu vide -> 0
assignments) mais MERGE DEFENSIF si non-vide.

Sequence :
  A. GET prod -> data/_kv_assign_montchat.b2a.preaudit.bak (GET gracieux : 404/{}
     traite comme objet vide {assignments:{},fusions:{},noms:{}}).
  B. confirme qu'AUCUNE de nos 103 cles n'ecrase un tag DIFFERENT existant
     (si une cle est deja taggee a la MEME valeur : no-op tolere ; valeur
     DIFFERENTE : STOP, on n'ecrase pas).
  C. candidat = prod merge nos 103 tags ; SAFETY DIFF : 0 retrait, 0 modif de
     cle non-B2a, ajouts/no-ops uniquement -> data/_kv_assign_montchat.b2a.candidate.json
     (re-ecrit depuis le candidat genere par la derivation light si conforme).

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_b2a_backup_diff_montchat.py
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
BACKUP = ROOT / "data" / "_kv_assign_montchat.b2a.preaudit.bak"
CANDIDATE = ROOT / "data" / "_kv_assign_montchat.b2a.candidate.json"

ALLOWED_TYPES = {"bureaux", "mono"}


def abort(msg):
    print(f"  [STOP] {msg}")
    sys.exit(1)


def get_prod_graceful(jwt):
    """GET secteur-assignments ; 404/objet vide -> {}. Renvoie dict normalise."""
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
        abort(f"candidat de derivation absent : {CANDIDATE.name} "
              "(relancer la derivation light B2a).")

    derived = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    our_tags = derived.get("assignments", {}) or {}
    if not our_tags:
        abort("candidat derive vide (0 tag).")
    for k, v in our_tags.items():
        if (v or {}).get("type") not in ALLOWED_TYPES:
            abort(f"candidat : tag inattendu {k} -> {v} (attendu bureaux|mono).")
    n_bur = sum(1 for v in our_tags.values() if v.get("type") == "bureaux")
    n_mono = sum(1 for v in our_tags.values() if v.get("type") == "mono")

    print("=" * 64)
    print("B2a Montchat - BACKUP + SAFETY DIFF (103 tags, aucun POST)")
    print("=" * 64)
    print(f"  candidat derive : {len(our_tags)} tags "
          f"({n_bur} bureaux + {n_mono} mono)")

    # ---- A. GET prod + backup ----
    prod, raw = get_prod_graceful(jwt)
    BACKUP.write_text(raw, encoding="utf-8")
    assigns = prod["assignments"]
    print(f"  A. backup prod -> {BACKUP.name}")
    print(f"     prod assignments={len(assigns)} fusions={len(prod['fusions'])} "
          f"noms={len(prod['noms'])}")

    # ---- B. aucune de nos cles n'ecrase un tag DIFFERENT ----
    conflicts = []
    noops = []
    for k, v in our_tags.items():
        cur = (assigns.get(k) or {}).get("type")
        if cur is not None:
            if cur == v.get("type"):
                noops.append(k)
            else:
                conflicts.append((k, cur, v.get("type")))
    if conflicts:
        for k, cur, new in conflicts:
            print(f"     [!!] {k}: prod={cur} != candidat={new}")
        abort(f"{len(conflicts)} conflit(s) : nos tags ecraseraient des valeurs "
              "DIFFERENTES. On n'ecrase pas. Investiguer.")
    print(f"  B. 0 conflit (no-op deja-taggees identiques : {len(noops)})")

    # ---- C. candidat merge + safety diff ----
    cand = {"assignments": copy.deepcopy(assigns),
            "fusions": copy.deepcopy(prod["fusions"]),
            "noms": copy.deepcopy(prod["noms"])}
    for k, v in our_tags.items():
        cand["assignments"][k] = {"type": v["type"]}

    added = [k for k in cand["assignments"] if k not in assigns]
    removed = [k for k in assigns if k not in cand["assignments"]]
    changed = [k for k in set(assigns) & set(cand["assignments"])
               if (assigns.get(k) or {}) != (cand["assignments"].get(k) or {})]
    # changed ne doit contenir QUE des cles a nous (no-op -> pas changed)
    changed_non_ours = [k for k in changed if k not in our_tags]

    print("  C. SAFETY DIFF (candidat vs backup) :")
    print(f"     assignments {len(assigns)} -> {len(cand['assignments'])} "
          f"(ajouts={len(added)} modifs={len(changed)} retraits={len(removed)})")
    ok = True
    if removed:
        ok = False
        print(f"     !! retraits inattendus : {sorted(removed)[:20]}")
    if changed_non_ours:
        ok = False
        print(f"     !! modifs hors-B2a : {sorted(changed_non_ours)[:20]}")
    if set(added) - set(our_tags):
        ok = False
        print(f"     !! ajouts hors candidat : {sorted(set(added)-set(our_tags))[:20]}")
    if prod["fusions"] != cand["fusions"] or prod["noms"] != cand["noms"]:
        ok = False
        print("     !! fusions/noms modifies (ne devraient pas)")
    if len(cand["assignments"]) != len(assigns) + len(added):
        ok = False
        print("     !! incoherence comptage")
    if not ok:
        abort("safety diff NON conforme. Candidat NON re-ecrit.")

    CANDIDATE.write_text(json.dumps(cand, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"     DIFF CONFORME : +{len(added)} ajouts, {len(noops)} no-op, "
          f"0 retrait, 0 modif hors-B2a.")
    print(f"     candidat (merge prod) -> {CANDIDATE.name} (PAS encore POSTe)")
    print("=" * 64)
    print("  STOP. Aucun POST. Valider avant _b2a_post_montchat.py.")


if __name__ == "__main__":
    main()
