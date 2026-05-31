#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche G - re-tag KV des cible_0vente reclassifiees via levier BDNB : backup+diff.

AUCUN POST. Calque EXACT de _manche_f_backup_diff_dl.py. PUR re-tag de type
(cible_0vente_* -> nouveau tag). Le decision_dict est construit depuis
data/_fiche_needs_terrain_dl.json par le LEVIER BDNB :
  - classe==CLEAR + tag_propose (3 social via owner HLM) -> ce tag
  - step==MAJIC_KO + tag_propose None + nb_log_bdnb>1 + pas d'immat
    -> copro_non_immat (multi-logements non-immat detenu par PP)
  - immat present -> SKIP (reste cible_0vente, tag implicite RNC)
  - nb_log_bdnb absent/<=1 -> SKIP (non concluant)

Endpoint = manche D/F (route worker /secteur-assignments/<agence>).

  A. Construit les flips depuis la fiche (STOP si 0).
  B. GET prod -> data/_kv_assign_dl_PRE_manche_g.HOLD.json. STOP si total != 643.
  C. Confirme prod : les N cles presentes avec type cible_0vente_* (STOP sinon).
  D. candidat = prod + N changements de TYPE uniquement. SAFETY DIFF : exactement
     N cles modifiees (type-only), 0 ajout/retrait, count INCHANGE (643),
     fusions/noms inchanges -> data/_kv_assign_dl_manche_g.candidate.json.

A lancer dans une session PowerShell ou DPE_JWT est charge :
    . scripts\\load_jwt.ps1
    python scripts\\_manche_g_backup_diff_dl.py
"""
import os, sys, json, copy, urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "_kv_assign_dl_PRE_manche_g.HOLD.json"
CANDIDATE = ROOT / "data" / "_kv_assign_dl_manche_g.candidate.json"
FICHE = ROOT / "data" / "_fiche_needs_terrain_dl.json"
EXPECT_TOTAL = 643   # post manche F


def abort(msg):
    print(f"  [STOP] {msg}")
    sys.exit(1)


def resolve_flips():
    """Levier BDNB sur la fiche needs_terrain -> {cle: nouveau_tag}."""
    if not FICHE.exists():
        abort(f"fiche absente : {FICHE.name} (relancer _fiche_needs_terrain_dl.py).")
    res = json.loads(FICHE.read_text(encoding="utf-8")).get("results", [])
    flips, skip_immat, skip_nolog = {}, [], []
    for r in res:
        cle = r.get("cle")
        if r.get("immat"):
            skip_immat.append(cle)
            continue
        if r.get("classe") == "CLEAR" and r.get("tag_propose"):
            flips[cle] = r["tag_propose"]
        elif (r.get("step") == "MAJIC_KO" and r.get("tag_propose") is None
              and (r.get("nb_log_bdnb") or 0) > 1):
            flips[cle] = "copro_non_immat"
        elif r.get("step") == "MAJIC_KO":
            skip_nolog.append(cle)
    if not flips:
        abort("0 cle resolue par le levier. Rien a re-taguer.")
    return flips, skip_immat, skip_nolog


def main():
    jwt = os.environ.get("DPE_JWT") or ""
    if not jwt:
        abort("env var DPE_JWT absente. Charger d'abord : . scripts\\load_jwt.ps1")

    flips, skip_immat, skip_nolog = resolve_flips()
    from collections import Counter
    print("=" * 70)
    print("MANCHE G - BACKUP + SAFETY DIFF (levier BDNB, aucun POST)")
    print("=" * 70)
    print(f"  A. {len(flips)} cles resolues (par tag: {dict(Counter(flips.values()))})")
    print(f"     SKIP immat (RNC implicite) : {skip_immat}")
    print(f"     SKIP nb_log<=1/absent      : {skip_nolog}")

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

    bad = []
    for cle in flips:
        cur = (assigns.get(cle) or {}).get("type") if cle in assigns else None
        if cle not in assigns or not str(cur or "").startswith("cible_0vente_"):
            bad.append((cle, cur))
    if bad:
        abort(f"{len(bad)} cle(s) absente(s) ou type != cible_0vente_* : {bad}.")

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
        ok = False; print(f"     !! modifs != {len(flips)} (diff={sorted(set(changed)^set(flips))})")
    for k, (o, n) in changed.items():
        if flips.get(k) != n or not str(o or '').startswith("cible_0vente_"):
            ok = False; print(f"     !! transition {k}: {o}->{n}")
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
    print(f"     DIFF CONFORME : {len(flips)} re-tags (type uniquement), 0 ajout/"
          f"retrait, count {EXPECT_TOTAL} inchange, fusions/noms inchanges.")
    print(f"     candidat -> {CANDIDATE.name} (PAS encore POSTe)")
    print("=" * 70)
    print("  STOP. Aucun POST. Valider la table avant la manche PATCH.")


if __name__ == "__main__":
    main()
