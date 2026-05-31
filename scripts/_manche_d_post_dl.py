#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche D - PATCH KV : POST du candidat (7 re-tags type). Un seul POST.

Calque de _b2_post_dl.py, PUR re-tag (pas d'ajout, pas de fusion).

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_manche_d_post_dl.py

Sequence :
  1. GARDE ANTI-DRIFT : GET prod ; si prod != backup (assignments|fusions|noms)
     -> ABORT, imprime la difference, AUCUN POST.
  2. POST : si prod == backup, POST l'objet candidat complet (un seul POST).
  3. VERIF : re-GET prod ; confirme prod == candidat : les 7 cles a leur nouveau
     type, count assignments inchange, fusions/noms inchanges, tout le reste
     identique au backup. Si KO -> alerte forte, miroir NON touche.
  4. MIROIR LOCAL : ecrit l'etat prod re-GET verifie dans data/_kv_assign_dl.json
     (PAS de git commit ici).

Garde-fous : un seul POST, uniquement sur le candidat ; aucun token en dur ;
abort propre si DPE_JWT absent.
"""
import os, sys, json, urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_manche_d_backup_dl.json"
CANDIDATE = ROOT / "data" / "_manche_d_candidate_dl.json"
MIRROR = ROOT / "data" / "_kv_assign_dl.json"

# cle -> tag cible (TO) attendu apres POST
EXPECT_TO = {
    "54|RUE|VILLETTE":         "social",
    "121|RUE|ANTOINE CHARIAL": "social",
    "7|AVENUE|LACASSAGNE":     "copro_non_immat",
    "10|RUE|PETITES SOEURS":   "mono",
    "31|RUE|DAUPHINE":         "copro_non_immat",
    "17|RUE|DAUPHINE":         "mono",
    "1|RUE|CARRY":             "bureaux",
}


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
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def post_candidate(jwt, candidate):
    """UNIQUE POST du script : envoie l'objet candidat complet."""
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
        abort(f"backup absent : {BACKUP.name} (relancer la manche backup).")
    if not CANDIDATE.exists():
        abort(f"candidat absent : {CANDIDATE.name} (relancer la manche backup).")

    backup = json.loads(BACKUP.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    nb, nc = norm(backup), norm(candidate)

    print("=" * 64)
    print("MANCHE D - PATCH KV (POST candidat, 7 re-tags type) - DL")
    print("=" * 64)

    ba, ca = nb["assignments"], nc["assignments"]
    # sanity local : candidat = backup + exactement 7 modifs (type uniquement)
    if len(ba) != len(ca):
        abort(f"local : count assignments differe (backup={len(ba)} cand={len(ca)}).")
    added = [k for k in ca if k not in ba]
    removed = [k for k in ba if k not in ca]
    changed = [k for k in set(ba) & set(ca) if ba.get(k) != ca.get(k)]
    if added or removed:
        abort(f"local : ajouts/retraits inattendus (added={added} removed={removed}).")
    if set(changed) != set(EXPECT_TO):
        abort(f"local : modifs != 7 attendues (diff={sorted(set(changed)^set(EXPECT_TO))}).")
    for k, to in EXPECT_TO.items():
        if (ca.get(k) or {}).get("type") != to:
            abort(f"local : {k} TO={ (ca.get(k) or {}).get('type') } != {to}.")
        ra = {kk: vv for kk, vv in (ba.get(k) or {}).items() if kk != "type"}
        rb = {kk: vv for kk, vv in (ca.get(k) or {}).items() if kk != "type"}
        if ra != rb:
            abort(f"local : {k} change hors-type (champs non-type modifies).")
    if nb["fusions"] != nc["fusions"] or nb["noms"] != nc["noms"]:
        abort("local : fusions/noms modifies (doivent etre inchanges).")

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

    # verif fine : les 7 a leur TO, count inchange, reste identique au backup
    p2a = np2["assignments"]
    bad_to = [k for k, to in EXPECT_TO.items() if (p2a.get(k) or {}).get("type") != to]
    drift = [k for k in set(ba) | set(p2a)
             if k not in EXPECT_TO and (ba.get(k) or {}) != (p2a.get(k) or {})]
    if (len(p2a) != len(ba) or bad_to or drift
            or np2["fusions"] != nb["fusions"] or np2["noms"] != nb["noms"]):
        print(f"     !! verif fine KO : count={len(p2a)} bad_TO={bad_to} "
              f"reste_modifie={len(drift)}")
        if drift:
            print(f"        cles hors-manche modifiees : {sorted(drift)[:20]}")
        abort("ALERTE : etat prod incoherent. Miroir NON modifie.")
    print(f"     verif OK : prod == candidat (assignments={len(p2a)}).")
    print(f"     les 7 re-tags a leur cible ; count inchange ; fusions/noms inchanges.")

    # ---- 4. MIROIR LOCAL (pas de git commit) ----
    MIRROR.write_text(json.dumps(prod2, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  4. miroir local mis a jour -> {MIRROR.name} (PAS de git commit ici).")
    print("=" * 64)
    print("  OK. PATCH applique et verifie. Commit du miroir = manche suivante.")


if __name__ == "__main__":
    main()
