#!/usr/bin/env python3
"""Batch KV DL post-scan MAJIC (34 patches) avec corrections user.

PATTERN _fix_*_dl.py (pas de POST sans 'apply' explicite) :
  1. GET KV live de chaque cle concernee
  2. Audit pre-PATCH : verifier type === 'copro_non_immat' et tag vide
     (sinon EXCLURE + signaler, ne JAMAIS ecraser)
  3. Backup data/_kv_assign_dl.prebatch_majic.bak (etat complet AVANT)
  4. Diff cle par cle ('copro_non_immat' -> classification)
  5. STOP -> attendre 'apply' positionnel
  6. Sur apply : POST atomique + relire 3 cles au hasard pour confirmer
     persistance

Corrections post-scan validees user :
  - RECLASSER BUREAUX -> SOCIAL (usage Tertiaire mais HLM>=70%) :
      12 RUE ST SIDOINE, 191 AVENUE FELIX FAURE, 59 RUE BARABAN
  - RETIRER du batch (audit terrain ulterieur) :
      50 RUE DAUPHINE, 35 RUE ANTOINE CHARIAL (BUREAUX 0 lots PM)
      79 COURS ALBERT THOMAS, 40 RUE DAUPHINE, 133 RUE BARABAN,
      148 RUE BARABAN (MIXTE faux positifs)
  - METTRE EN ATTENTE (echantillon trop faible) :
      17 RUE ST MAXIMIN (5 lots, 60% pile, douteux)

JWT lu depuis env var DPE_JWT (ne pas hardcoder).

Usage :
  python scripts/fix_kv_batch_majic_dl.py          # affiche + STOP
  python scripts/fix_kv_batch_majic_dl.py apply    # POST atomique
"""
import json
import os
import random
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
KV_BAK = ROOT / "data" / "_kv_assign_dl.prebatch_majic.bak"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

JWT = os.environ.get("DPE_JWT")
if not JWT:
    sys.exit("  [abort] env var DPE_JWT absente. Lance "
             "$env:DPE_JWT='<jwt>' avant le script.")

# ---------- Batch source : 41 du scan MAJIC ----------
SCAN_SOCIAL = [
    "28|RUE|ETIENNE RICHERAND",
    "22|RUE|ST ANTOINE",
    "20B|AVENUE|LACASSAGNE",
    "35|RUE|ST ANTOINE",
    "59|COURS|ALBERT THOMAS",
    "66|AVENUE|LACASSAGNE",
    "10|RUE|JEAN RENOIR",
    "272|RUE|PAUL BERT",
    "17|RUE|ST MAXIMIN",
    "128|RUE|ANTOINE CHARIAL",
]
SCAN_BUREAUX = [
    "12|RUE|ST SIDOINE",
    "50|RUE|DAUPHINE",
    "35|RUE|ANTOINE CHARIAL",
    "30|RUE|ANTOINE CHARIAL",
    "2|RUE|BARA",
    "336|RUE|PAUL BERT",
    "79|RUE|DAUPHINE",
    "99|RUE|BARABAN",
    "256|COURS|LAFAYETTE",
    "191|AVENUE|FELIX FAURE",
    "5|COURS|ALBERT THOMAS",
    "59|RUE|BARABAN",
]
SCAN_MIXTE = [
    "7|COURS|ALBERT THOMAS",
    "3|RUE|NAZARETH",
    "8|RUE|FRANCOIS GILLET",
    "14|RUE|DOCTEUR REBATEL",
    "56|RUE|MAURICE FLANDIN",
    "23|RUE|METALLURGIE",
    "52|RUE|ETIENNE RICHERAND",
    "79|COURS|ALBERT THOMAS",
    "40|RUE|DAUPHINE",
    "133|RUE|BARABAN",
    "39|RUE|DAUPHINE",
    "148|RUE|BARABAN",
    "77|RUE|ETIENNE RICHERAND",
]
SCAN_MONO = [
    "3|RUE|FRANCOIS GILLET",
    "1|RUE|VILLETTE",
    "251|RUE|PAUL BERT",
    "41|AVENUE|LACASSAGNE",
    "14|RUE|ROPOSTE",
    "20|RUE|FREDERIC MISTRAL",
]

# ---------- Corrections user ----------
RECLASS_TO_SOCIAL = {
    "12|RUE|ST SIDOINE",
    "191|AVENUE|FELIX FAURE",
    "59|RUE|BARABAN",
}
REMOVE_FROM_BATCH = {
    "50|RUE|DAUPHINE",
    "35|RUE|ANTOINE CHARIAL",
    "79|COURS|ALBERT THOMAS",
    "40|RUE|DAUPHINE",
    "133|RUE|BARABAN",
    "148|RUE|BARABAN",
}
HOLD_PENDING = {"17|RUE|ST MAXIMIN"}


# ---------- Construire le batch final ----------
def build_batch():
    batch = {}  # cle -> type
    for c in SCAN_SOCIAL:
        if c in REMOVE_FROM_BATCH or c in HOLD_PENDING:
            continue
        batch[c] = "social"
    for c in SCAN_BUREAUX:
        if c in REMOVE_FROM_BATCH or c in HOLD_PENDING:
            continue
        batch[c] = "social" if c in RECLASS_TO_SOCIAL else "bureaux"
    for c in SCAN_MIXTE:
        if c in REMOVE_FROM_BATCH or c in HOLD_PENDING:
            continue
        batch[c] = "mixte"
    for c in SCAN_MONO:
        if c in REMOVE_FROM_BATCH or c in HOLD_PENDING:
            continue
        batch[c] = "mono"
    return batch


# ---------- KV helpers ----------
def kv_req(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {JWT}",
        "User-Agent": UA,
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---------- Main ----------
def main():
    do_apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")

    batch = build_batch()

    print("=" * 78)
    print(f"BATCH KV MAJIC DL  ({'MODE APPLY' if do_apply else 'MODE DRY (STOP)'})")
    print("=" * 78)
    print()
    print("Sommaire batch construit :")
    ct = Counter(batch.values())
    expected = {"social": 12, "bureaux": 7, "mixte": 9, "mono": 6}
    total = sum(ct.values())
    for cat in ("social", "mixte", "mono", "bureaux"):
        got = ct.get(cat, 0)
        exp = expected[cat]
        flag = "OK" if got == exp else f"!! attendu {exp}"
        print(f"  {cat:8s} : {got:3d}  ({flag})")
    print(f"  {'TOTAL':8s} : {total:3d}  (attendu 34, scan 41 - retires 6 - en attente 1)")
    if total != 34:
        print(f"  [warn] total {total} != 34 attendu (verifier les listes)")
    print()
    print(f"  Retires (audit terrain) : {sorted(REMOVE_FROM_BATCH)}")
    print(f"  En attente              : {sorted(HOLD_PENDING)}")
    print(f"  Reclasses SOCIAL        : {sorted(RECLASS_TO_SOCIAL)}")
    print()

    # ---------- GET KV live + audit ----------
    print("[GET] etat live KV cloud...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  GET KV err: status={st} body={body}")
    assigns = body.get("assignments") or {}
    fusions = body.get("fusions") or {}
    noms = body.get("noms") or {}
    print(f"  assignments={len(assigns)}  fusions={len(fusions)}  noms={len(noms)}")
    print()

    # ---------- Backup ----------
    print(f"[BAK] backup full snapshot KV cloud -> {KV_BAK.name}")
    snapshot = {
        "_meta": {
            "captured_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agence": AGENCE,
            "purpose": "pre-batch_majic_dl (34 KV PATCH proposes)",
            "batch_summary": dict(ct),
        },
        "assignments": assigns,
        "fusions": fusions,
        "noms": noms,
    }
    KV_BAK.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  ecrit {len(assigns)} assignments + {len(fusions)} fusions.")
    print()

    # ---------- Audit pre-PATCH ----------
    print("[AUDIT] verification pre-PATCH (type courant doit etre 'copro_non_immat'):")
    will_patch = []
    excluded = []
    for cle, new_type in sorted(batch.items()):
        cur = assigns.get(cle) or {}
        cur_type = cur.get("type") or ""
        if cur_type == "":
            # tag vide -> on accepte (cas edge mais legitime)
            will_patch.append((cle, cur_type, new_type))
        elif cur_type == "copro_non_immat":
            will_patch.append((cle, cur_type, new_type))
        elif cur_type == new_type:
            excluded.append((cle, cur_type, new_type, "DEJA OK"))
        else:
            excluded.append((cle, cur_type, new_type, "TAG NON-VIDE NON-COPRO_NI"))

    if excluded:
        print(f"  EXCLUS ({len(excluded)}) - non patches (regle audit) :")
        for cle, cur_t, new_t, reason in excluded:
            print(f"    [SKIP] {cle:34s} cur='{cur_t}' new='{new_t}' raison={reason}")
        print()
    print(f"  A PATCHER : {len(will_patch)} cles")
    print()

    # ---------- Diff par categorie ----------
    print("[DIFF] detail patches a appliquer (groupes par categorie nouvelle) :")
    by_cat = {}
    for cle, cur_t, new_t in will_patch:
        by_cat.setdefault(new_t, []).append((cle, cur_t))
    for cat in ("social", "mixte", "mono", "bureaux"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        print(f"\n  === {cat.upper()}  ({len(items)} cles) ===")
        for cle, cur_t in items:
            print(f"    {cle:34s} '{cur_t}' -> '{cat}'")
    print()

    if not do_apply:
        print("=" * 78)
        print("DRY RUN : STOP. Tape 'python scripts/fix_kv_batch_majic_dl.py apply' "
              "pour POSTer.")
        print(f"Backup deja ecrit : {KV_BAK.name}")
        print(f"Batch final {len(will_patch)} patches (exclus={len(excluded)}).")
        print("=" * 78)
        return

    # ---------- APPLY : POST atomique ----------
    print("[APPLY] POST atomique...")
    for cle, _, new_type in will_patch:
        assigns[cle] = {"type": new_type}
    st, post_body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                           {"assignments": assigns, "fusions": fusions,
                            "noms": noms})
    print(f"  status={st}  body={post_body}")
    if st != 200:
        sys.exit("  POST echec")

    # ---------- Re-GET verif 3 cles au hasard ----------
    print()
    print("[VERIF] re-GET 3 cles au hasard...")
    random.seed(42)
    sample = random.sample([c for c, _, _ in will_patch], min(3, len(will_patch)))
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  Re-GET err: {body}")
    a2 = body.get("assignments") or {}
    fails = 0
    for cle in sample:
        v = a2.get(cle)
        expected_t = batch[cle]
        ok = bool(v) and v.get("type") == expected_t
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] {cle:34s} -> {v} (attendu '{expected_t}')")
        if not ok:
            fails += 1

    if fails:
        sys.exit(f"  [abort] {fails}/3 sample fail")

    # ---------- Maj cache local ----------
    if KV_LOCAL.exists():
        kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    else:
        kv_local = {"assignments": {}}
    kv_local["assignments"] = assigns
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print()
    print(f"  [local] {KV_LOCAL.name} mis a jour ({len(assigns)} assignments)")
    print()
    print("=" * 78)
    print(f"APPLY REUSSI : {len(will_patch)} cles patchees ; "
          f"{len(excluded)} exclues ; 3/3 sample OK.")
    print("=" * 78)


if __name__ == "__main__":
    main()
