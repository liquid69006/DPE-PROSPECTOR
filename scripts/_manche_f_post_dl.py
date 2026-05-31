#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche F - PATCH KV : POST du candidat (10 re-tags cible_0vente). Un seul POST.

Calque EXACT de _manche_d_post_dl.py. PUR re-tag de type. Endpoint manche D
(/secteur-assignments/<agence>).

Sequence :
  1. GARDE ANTI-DRIFT : GET prod ; si prod != backup -> ABORT, AUCUN POST.
  2. POST : si prod == backup, POST l'objet candidat complet (un seul POST).
  3. VERIF : re-GET ; confirme les 10 cles a leur nouveau tag, count inchange,
     reste identique au backup. Si KO -> alerte, miroir NON touche.
  4. MIROIR LOCAL : ecrit l'etat prod re-GET dans data/_kv_assign_dl.json
     (PAS de git commit ici).

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_manche_f_post_dl.py
"""
import os, sys, json, urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_kv_assign_dl_PRE_manche_f.HOLD.json"
CANDIDATE = ROOT / "data" / "_kv_assign_dl_manche_f.candidate.json"
MIRROR = ROOT / "data" / "_kv_assign_dl.json"


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
    ba, ca = nb["assignments"], nc["assignments"]

    print("=" * 70)
    print("MANCHE F - PATCH KV (POST candidat, 10 re-tags cible_0vente) - DL")
    print("=" * 70)

    # sanity local : candidat = backup + exactement 10 modifs (type-only),
    # toutes cible_0vente_* -> nouveau tag.
    if len(ba) != len(ca):
        abort(f"local : count differe (backup={len(ba)} cand={len(ca)}).")
    added = [k for k in ca if k not in ba]
    removed = [k for k in ba if k not in ca]
    changed = [k for k in set(ba) & set(ca) if ba.get(k) != ca.get(k)]
    if added or removed:
        abort(f"local : ajout/retrait inattendu (added={added} removed={removed}).")
    if len(changed) != 10:
        abort(f"local : {len(changed)} modifs != 10.")
    EXPECT_TO = {}
    for k in changed:
        o = (ba.get(k) or {}).get("type")
        n = (ca.get(k) or {}).get("type")
        if not str(o or "").startswith("cible_0vente_"):
            abort(f"local : {k} type avant={o} != cible_0vente_*.")
        ra = {kk: vv for kk, vv in (ba.get(k) or {}).items() if kk != "type"}
        rb = {kk: vv for kk, vv in (ca.get(k) or {}).items() if kk != "type"}
        if ra != rb:
            abort(f"local : {k} change hors-type.")
        EXPECT_TO[k] = n
    if nb["fusions"] != nc["fusions"] or nb["noms"] != nc["noms"]:
        abort("local : fusions/noms modifies.")

    # ---- 1. GARDE ANTI-DRIFT ----
    print("  1. garde anti-drift : GET prod vs backup ...")
    try:
        prod = get_prod(jwt)
    except Exception as e:
        abort(f"GET prod echoue : {e}")
    if norm(prod) != nb:
        d = diff_view(norm(prod), nb)
        print(f"     prod != backup ({len(d)} diff) :")
        for line in d[:50]:
            print(line)
        abort("le KV a bouge depuis le backup -> candidat perime, REBUILD. AUCUN POST.")
    print(f"     prod == backup OK (assignments={len(ba)})")

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
        abort(f"re-GET echoue (POST possiblement applique) : {e} -- NE PAS toucher "
              "au miroir, verifier manuellement.")
    np2 = norm(prod2)
    if np2 != nc:
        d = diff_view(np2, nc)
        print(f"     !! VERIF KO : re-GET != candidat ({len(d)} diff) :")
        for line in d[:50]:
            print(line)
        abort("ALERTE : etat prod apres POST != candidat. Miroir NON modifie.")

    p2a = np2["assignments"]
    bad_to = [k for k, to in EXPECT_TO.items() if (p2a.get(k) or {}).get("type") != to]
    drift = [k for k in set(ba) | set(p2a)
             if k not in EXPECT_TO and (ba.get(k) or {}) != (p2a.get(k) or {})]
    if len(p2a) != len(ba) or bad_to or drift \
            or np2["fusions"] != nb["fusions"] or np2["noms"] != nb["noms"]:
        print(f"     !! verif fine KO : count={len(p2a)} bad_TO={bad_to} drift={len(drift)}")
        if drift:
            print(f"        cles hors-manche modifiees : {sorted(drift)[:20]}")
        abort("ALERTE : etat prod incoherent. Miroir NON modifie.")
    print(f"     verif OK : 10 re-tags a leur cible ; count={len(p2a)} inchange ; "
          "fusions/noms inchanges.")

    # ---- 4. MIROIR LOCAL (pas de git commit) ----
    MIRROR.write_text(json.dumps(prod2, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  4. miroir local -> {MIRROR.name} (PAS de git commit ici).")
    print("=" * 70)
    print("  OK. 10 re-tags appliques et verifies en prod. Commit du miroir = "
          "manche suivante.")


if __name__ == "__main__":
    main()
