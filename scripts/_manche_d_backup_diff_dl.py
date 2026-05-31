#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche D - re-tag KV de 7 cles EXISTANTES (modif type) : backup + safety diff.

AUCUN POST. Calque de _b2_backup_diff_dl.py, mais PUR re-tag (pas d'ajout, pas de
fusion). Les 7 cles existent deja ; on ne change QUE leur type. Les eventuels
autres champs de l'assignment (ilot, etc.) sont PRESERVES.

Decisions Yann (cle exacte resolue depuis _tagcoherence_bgid_confirmed_dl.json) :
  54|RUE|VILLETTE          bureaux -> social
  121|RUE|ANTOINE CHARIAL  bureaux -> social
  7|AVENUE|LACASSAGNE      social  -> copro_non_immat
  10|RUE|PETITES SOEURS    social  -> mono
  31|RUE|DAUPHINE          social  -> copro_non_immat
  17|RUE|DAUPHINE          social  -> mono
  1|RUE|CARRY              social  -> bureaux

  A. GET prod -> data/_manche_d_backup_dl.json. STOP si une cle absente ou tag
     courant != attendu (FROM).
  B. candidat = prod entier + SEULEMENT les 7 changements de type ->
     data/_manche_d_candidate_dl.json. SAFETY DIFF : exactement 7 cles different,
     toutes en TYPE uniquement, assignments count INCHANGE, fusions/noms inchanges.
     Sinon STOP, candidat NON ecrit.

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_manche_d_backup_diff_dl.py
"""
import os, sys, json, copy, urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_manche_d_backup_dl.json"
CANDIDATE = ROOT / "data" / "_manche_d_candidate_dl.json"

# cle exacte -> (tag_courant_attendu, tag_cible)
FLIPS = {
    "54|RUE|VILLETTE":         ("bureaux", "social"),
    "121|RUE|ANTOINE CHARIAL": ("bureaux", "social"),
    "7|AVENUE|LACASSAGNE":     ("social",  "copro_non_immat"),
    "10|RUE|PETITES SOEURS":   ("social",  "mono"),
    "31|RUE|DAUPHINE":         ("social",  "copro_non_immat"),
    "17|RUE|DAUPHINE":         ("social",  "mono"),
    "1|RUE|CARRY":             ("social",  "bureaux"),
}


def abort(msg):
    print(f"  [STOP] {msg}")
    sys.exit(1)


def main():
    if len(FLIPS) != 7:
        abort(f"FLIPS doit valoir 7 re-tags (n={len(FLIPS)}).")
    jwt = os.environ.get("DPE_JWT") or ""
    if not jwt:
        abort("env var DPE_JWT absente. Charger d'abord : . scripts\\load_jwt.ps1")

    # ---- A. GET prod + backup ----
    req = urllib.request.Request(
        f"{API}/secteur-assignments/{AGENCE}",
        headers={"Authorization": f"Bearer {jwt}", "User-Agent": "Mozilla/5.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    except Exception as e:
        abort(f"GET echoue : {e}")
    prod = json.loads(raw)
    assigns = prod.get("assignments", {})
    fusions = prod.get("fusions", {})
    noms = prod.get("noms", {})
    BACKUP.write_text(raw, encoding="utf-8")
    print("=" * 64)
    print("MANCHE D - BACKUP + SAFETY DIFF (7 re-tags type, aucun POST)")
    print("=" * 64)
    print(f"  A. backup prod -> {BACKUP.name}")
    print(f"     assignments={len(assigns)}  fusions={len(fusions)}  noms={len(noms)}")

    # ---- B. confirmation prod : tag courant attendu (FROM) par cle ----
    bad = []
    for cle, (frm, to) in FLIPS.items():
        cur = (assigns.get(cle) or {}).get("type") if cle in assigns else None
        if cle not in assigns:
            bad.append((cle, "ABSENT", frm))
            flag = "!! ABSENT"
        elif cur != frm:
            bad.append((cle, cur, frm))
            flag = "!! DIFFERENT"
        else:
            flag = "OK"
        print(f"     {cle:30s} prod={str(cur):16s} (attendu {frm:8s}) -> {to:16s} [{flag}]")
    if bad:
        abort(f"{len(bad)} cle(s) absente(s) ou tag courant != attendu : {bad}. "
              "On ne patche pas.")

    # ---- C. candidat (preserve les champs non-type) + safety diff ----
    cand = copy.deepcopy(prod)
    cand_assigns = cand.setdefault("assignments", {})
    for cle, (frm, to) in FLIPS.items():
        base = dict(cand_assigns.get(cle) or {})
        base["type"] = to
        cand_assigns[cle] = base

    keys_all = set(assigns) | set(cand_assigns)
    added, removed, changed, non_type = [], [], {}, []
    for k in keys_all:
        a = assigns.get(k)
        b = cand_assigns.get(k)
        if k not in assigns:
            added.append(k)
        elif k not in cand_assigns:
            removed.append(k)
        elif a != b:
            changed[k] = ((a or {}).get("type"), (b or {}).get("type"))
            # verifie que SEUL le type change (autres champs identiques)
            ra = {kk: vv for kk, vv in (a or {}).items() if kk != "type"}
            rb = {kk: vv for kk, vv in (b or {}).items() if kk != "type"}
            if ra != rb:
                non_type.append(k)

    print("  B. SAFETY DIFF (candidat vs backup) :")
    print(f"     total assignments backup={len(assigns)} candidat={len(cand_assigns)}"
          f"  (delta {len(cand_assigns) - len(assigns)})")
    print(f"     cles modifiees={len(changed)} ajoutees={len(added)} "
          f"retirees={len(removed)}")
    for k in sorted(changed):
        old, new = changed[k]
        print(f"        {k:30s} {old} -> {new}")
    if added:
        print(f"     !! AJOUTS INATTENDUS : {sorted(added)}")
    if removed:
        print(f"     !! RETRAITS INATTENDUS : {sorted(removed)}")
    if non_type:
        print(f"     !! CHANGEMENTS HORS-TYPE : {sorted(non_type)}")

    ok = True
    if added or removed or non_type:
        ok = False
    if len(cand_assigns) != len(assigns):
        ok = False
        print(f"     !! count assignments change ({len(assigns)}->{len(cand_assigns)})")
    if set(changed) != set(FLIPS):
        ok = False
        print(f"     !! l'ensemble modifie != les {len(FLIPS)} attendus "
              f"(diff={sorted(set(changed) ^ set(FLIPS))})")
    for k, (old, new) in changed.items():
        exp = FLIPS.get(k)
        if exp is None or (old, new) != exp:
            ok = False
            print(f"     !! transition inattendue {k}: {old}->{new} (attendu {exp})")
    if fusions != cand.get("fusions", {}) or noms != cand.get("noms", {}):
        ok = False
        print("     !! fusions/noms modifies (ne devraient pas)")

    if not ok:
        abort("safety diff NON conforme. Candidat NON ecrit, rien a POSTER.")

    CANDIDATE.write_text(json.dumps(cand, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"     DIFF CONFORME : exactement {len(FLIPS)} re-tags (type uniquement), "
          f"0 ajout / 0 retrait, count {len(assigns)} inchange, fusions/noms inchanges.")
    print(f"     candidat valide -> {CANDIDATE.name} (PAS encore POSTe)")
    print("=" * 64)
    print("  STOP. Aucun POST effectue. Valider avant la manche PATCH.")


if __name__ == "__main__":
    main()
