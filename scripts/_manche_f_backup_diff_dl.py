#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche F - re-tag KV de 10 cibles_0vente reclassifiees : backup + safety diff.

AUCUN POST. Calque EXACT de _manche_d_backup_diff_dl.py. PUR re-tag de type
(cible_0vente_* -> nouveau tag) sur 10 cles deja existantes. Les cles canoniques
sont resolues depuis data/_fiche_cible_0vente_dl.json par (num, nom_voie) ;
STOP si une decision ne matche pas exactement.

Endpoint = celui de manche D (route worker /secteur-assignments/<agence>).

  A. Resout les 10 (num, voie) -> cle canonique (STOP si != 10 matches uniques).
  B. GET prod -> data/_kv_assign_dl_PRE_manche_f.HOLD.json. STOP si total != 642.
  C. Confirme prod : les 10 cles presentes avec type cible_0vente_* (STOP sinon).
  D. candidat = prod + 10 changements de TYPE uniquement (autres champs preserves).
     SAFETY DIFF : exactement 10 cles modifiees (type-only), 0 ajout/retrait,
     count assignments INCHANGE (642), fusions/noms inchanges ->
     data/_kv_assign_dl_manche_f.candidate.json (seulement si conforme).

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_manche_f_backup_diff_dl.py
"""
import os, sys, json, copy, re, unicodedata, urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_kv_assign_dl_PRE_manche_f.HOLD.json"
CANDIDATE = ROOT / "data" / "_kv_assign_dl_manche_f.candidate.json"
FICHE = ROOT / "data" / "_fiche_cible_0vente_dl.json"
EXPECT_TOTAL = 643

# Decisions Yann (num, nom_voie, tag cible). Voie matchee par tokens (articles
# et accents ignores) contre les cles canoniques du fiche.
DECISIONS = [
    (71,  "BARABAN",          "social"),
    (22,  "STE ANNE BARABAN", "social"),
    (135, "BARABAN",          "social"),
    (75,  "MAURICE FLANDIN",  "social"),
    (222, "FELIX FAURE",      "mono"),
    (6,   "24 FEVRIER 1848",  "copro_non_immat"),
    (76,  "BARABAN",          "copro_non_immat"),
    (65,  "STE ANNE BARABAN", "copro_non_immat"),
    (51,  "LACASSAGNE",       "copro_non_immat"),
    (1,   "CONVENTION",       "copro_non_immat"),
]
ART = {"DE", "DU", "LA", "LE", "LES", "DES", "L", "D", "ET", "AU", "AUX", "A"}


def toks(v):
    v = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().upper()
    return frozenset(t for t in re.split(r"[^A-Z0-9]+", v) if t and t not in ART)


def abort(msg):
    print(f"  [STOP] {msg}")
    sys.exit(1)


def resolve_flips():
    """Matche les 10 decisions -> {cle_canonique: tag_cible}. STOP si != 10."""
    if not FICHE.exists():
        abort(f"fiche absente : {FICHE.name} (relancer _fiche_cible_0vente_dl.py).")
    fiche = json.loads(FICHE.read_text(encoding="utf-8")).get("results", [])
    idx = {}
    for r in fiche:
        p = (r.get("cle") or "").split("|")
        if len(p) == 3:
            idx.setdefault((p[0].strip(), toks(p[2])), []).append(r["cle"])
    flips, bad = {}, []
    for num, voie, tag in DECISIONS:
        m = idx.get((str(num), toks(voie)), [])
        if len(m) != 1:
            bad.append((num, voie, f"{len(m)} match(s): {m}"))
        else:
            flips[m[0]] = tag
    if bad:
        abort(f"matching non-unique pour {len(bad)} decision(s) : {bad}. "
              "Pas de re-tag aveugle.")
    if len(flips) != 10:
        abort(f"resolu {len(flips)} cles != 10 attendues.")
    return flips


def main():
    jwt = os.environ.get("DPE_JWT") or ""
    if not jwt:
        abort("env var DPE_JWT absente. Charger d'abord : . scripts\\load_jwt.ps1")

    # ---- A. resolution cles ----
    flips = resolve_flips()
    print("=" * 70)
    print("MANCHE F - BACKUP + SAFETY DIFF (10 re-tags cible_0vente, aucun POST)")
    print("=" * 70)
    print(f"  A. 10 cles resolues depuis {FICHE.name}")

    # ---- B. GET prod + backup ----
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
    total = len(assigns)
    print(f"  B. backup prod -> {BACKUP.name}  (assignments={total} fusions="
          f"{len(fusions)} noms={len(noms)})")
    if total != EXPECT_TOTAL:
        abort(f"DRIFT total={total} != {EXPECT_TOTAL}. On ne touche a rien.")

    # ---- C. confirmation prod : type cible_0vente_* sur les 10 ----
    bad = []
    for cle in flips:
        cur = (assigns.get(cle) or {}).get("type") if cle in assigns else None
        if cle not in assigns or not str(cur or "").startswith("cible_0vente_"):
            bad.append((cle, cur))
    if bad:
        abort(f"{len(bad)} cle(s) absente(s) ou type != cible_0vente_* : {bad}.")

    # ---- D. candidat (type-only, autres champs preserves) + safety diff ----
    cand = copy.deepcopy(prod)
    ca = cand.setdefault("assignments", {})
    for cle, to in flips.items():
        base = dict(ca.get(cle) or {})
        base["type"] = to
        ca[cle] = base

    added, removed, changed, non_type = [], [], {}, []
    for k in set(assigns) | set(ca):
        a, b = assigns.get(k), ca.get(k)
        if k not in assigns:
            added.append(k)
        elif k not in ca:
            removed.append(k)
        elif a != b:
            changed[k] = ((a or {}).get("type"), (b or {}).get("type"))
            ra = {kk: vv for kk, vv in (a or {}).items() if kk != "type"}
            rb = {kk: vv for kk, vv in (b or {}).items() if kk != "type"}
            if ra != rb:
                non_type.append(k)

    print("  D. SAFETY DIFF :")
    print(f"     {'cle':30s} {'type_avant':20s} -> {'type_apres':16s} match")
    for cle, to in flips.items():
        old = (assigns.get(cle) or {}).get("type")
        ok = changed.get(cle) == (old, to) and cle not in non_type
        print(f"     {cle:30s} {str(old):20s} -> {to:16s} {'OK' if ok else '!!'}")
    print(f"     modifiees={len(changed)} ajouts={len(added)} retraits={len(removed)}"
          f" hors-type={len(non_type)} | count {len(assigns)}->{len(ca)}")

    ok = True
    if set(changed) != set(flips):
        ok = False; print(f"     !! modifs != 10 attendues (diff={sorted(set(changed)^set(flips))})")
    for k, (o, n) in changed.items():
        if flips.get(k) != n or not str(o or '').startswith("cible_0vente_"):
            ok = False; print(f"     !! transition {k}: {o}->{n} (attendu cible_0vente_*->{flips.get(k)})")
    if added or removed or non_type:
        ok = False; print("     !! ajout/retrait/hors-type detecte")
    if len(ca) != len(assigns):
        ok = False; print("     !! count assignments change")
    if fusions != cand.get("fusions", {}) or noms != cand.get("noms", {}):
        ok = False; print("     !! fusions/noms modifies")

    if not ok:
        abort("safety diff NON conforme. Candidat NON ecrit, rien a POSTER.")

    CANDIDATE.write_text(json.dumps(cand, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"     DIFF CONFORME : 10 re-tags (type uniquement), 0 ajout/retrait, "
          f"count {EXPECT_TOTAL} inchange, fusions/noms inchanges.")
    print(f"     candidat -> {CANDIDATE.name} (PAS encore POSTe)")
    print("=" * 70)
    print("  STOP. Aucun POST. Valider la table avant la manche PATCH.")


if __name__ == "__main__":
    main()
