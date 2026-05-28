#!/usr/bin/env python3
"""Securiser les 58 tags MP existants - marker terrain_manual_legacy.

OBJECTIF :
  Preserver et tracer les 58 tags MP actuels sans changer aucun type.
  AUCUN scan, AUCUN reclassement. Filet + tracabilite avant chantier
  pipeline.

ARTEFACTS PRODUITS :
  1. data/_kv_assign_mp.backup_preaudit.json
       Snapshot RAW de l'etat KV live (assignments + fusions + noms).
  2. data/_mp_legacy_review.json
       Registre des 58 cles : { cle, type_legacy, a_reauditer: true }.
  3. data/_kv_assign_mp.pre_legacy_mark.bak  (apply only)
       Backup distinct AVANT mutation, identique au snapshot
       (filet de restauration cote local).
  4. (cloud) chaque entree assignment recoit :
       _qualif_source = "terrain_manual_legacy"
       _qualif_date   = "pre_2026_pipeline"
     Le champ "type" reste IDENTIQUE.

PROCEDURE :
  1. GET KV live cloud (lecture seule)
  2. Snapshot et registry (toujours, meme en DRY-RUN)
  3. Construction du plan : meme dict, _qualif_source/_qualif_date ajoutes
  4. AUDIT BLOQUANT : types avant == types apres (set + Counter exact)
     Si difference -> ABORT immediat.
  5. DRY-RUN : affichage + STOP
  6. APPLY : backup distinct, POST KV, re-GET, re-audit, sync local.

Usage :
  PYTHONUTF8=1 python scripts/fix_kv_mp_legacy_mark.py          # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_kv_mp_legacy_mark.py apply    # APPLY

Pre-requis :
  $env:DPE_JWT pose via scripts/load_jwt.ps1
"""
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_mp.json"
SNAPSHOT = ROOT / "data" / "_kv_assign_mp.backup_preaudit.json"
REGISTRY = ROOT / "data" / "_mp_legacy_review.json"
KV_BAK = ROOT / "data" / "_kv_assign_mp.pre_legacy_mark.bak"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "motte-picquet"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

QUALIF_SOURCE = "terrain_manual_legacy"
QUALIF_DATE = "pre_2026_pipeline"
EXPECTED_COUNT = 58

JWT = os.environ.get("DPE_JWT") or ""


def kv_req(method, path, body=None):
    if not JWT:
        sys.exit("  [abort] env DPE_JWT absente -> source scripts/load_jwt.ps1")
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {JWT}", "User-Agent": UA,
               "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def type_signature(assigns):
    """Signature deterministe : cle -> type, pour comparaison stricte."""
    return {c: (v or {}).get("type") for c, v in assigns.items()}


def main():
    do_apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")
    mode = "APPLY" if do_apply else "DRY-RUN"
    print("=" * 78)
    print(f"MP LEGACY MARK  ({mode})  source={QUALIF_SOURCE}")
    print("=" * 78)

    # ------------------------------------------------------------------
    # 1. GET KV live cloud
    # ------------------------------------------------------------------
    print("\n[1] GET KV live cloud...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  GET KV err: {st} {body!r}")
    assigns_live = body.get("assignments") or {}
    fusions_live = body.get("fusions") or {}
    noms_live = body.get("noms") or {}
    n_live = len(assigns_live)
    print(f"  assignments={n_live}  fusions={len(fusions_live)}  noms={len(noms_live)}")

    if n_live != EXPECTED_COUNT:
        print(f"  [warn] count={n_live} attendu={EXPECTED_COUNT}")
        print(f"         L'ecart sera trace tel quel (snapshot raw cloud).")
        # Pas d'abort : on snapshot raw quel que soit le count, c'est
        # le but du filet. On adapte juste le registry au reel.

    # ------------------------------------------------------------------
    # 2. Snapshot RAW (toujours, lecture seule cote KV)
    # ------------------------------------------------------------------
    print("\n[2] Ecriture snapshot RAW...")
    snapshot = {
        "_meta": {
            "purpose": "snapshot brut KV live MP avant marquage legacy",
            "secteur": AGENCE,
            "n_assignments": n_live,
            "qualif_source_planned": QUALIF_SOURCE,
            "qualif_date_planned": QUALIF_DATE,
        },
        "assignments": assigns_live,
        "fusions": fusions_live,
        "noms": noms_live,
    }
    SNAPSHOT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ecrit : {SNAPSHOT.relative_to(ROOT)}")

    # ------------------------------------------------------------------
    # 3. Registry des cles a re-auditer
    # ------------------------------------------------------------------
    print("\n[3] Ecriture registry _mp_legacy_review.json...")
    types_counter = Counter((v or {}).get("type") for v in assigns_live.values())
    entries = []
    for cle in sorted(assigns_live):
        v = assigns_live.get(cle) or {}
        entries.append({
            "cle": cle,
            "type_legacy": v.get("type"),
            "a_reauditer": True,
        })
    registry = {
        "_meta": {
            "purpose": ("registre des tags MP herites pre-pipeline. "
                        "Chaque entree devra etre re-auditee via le futur "
                        "pipeline secteur-agnostique (port DL->MP)."),
            "secteur": AGENCE,
            "n_entries": len(entries),
            "qualif_source": QUALIF_SOURCE,
            "qualif_date": QUALIF_DATE,
            "type_distribution": dict(types_counter),
        },
        "entries": entries,
    }
    REGISTRY.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ecrit : {REGISTRY.relative_to(ROOT)}  ({len(entries)} entrees)")
    print(f"  Distribution : {dict(types_counter)}")

    # ------------------------------------------------------------------
    # 4. Construction du plan (marquage)
    # ------------------------------------------------------------------
    print("\n[4] Construction plan marquage (type INCHANGE)...")
    planned = {}
    n_marked = 0
    n_skip_already = 0
    for cle, v_in in assigns_live.items():
        v = dict(v_in or {})
        if v.get("_qualif_source") == QUALIF_SOURCE:
            n_skip_already += 1
            planned[cle] = v
            continue
        v["_qualif_source"] = QUALIF_SOURCE
        v["_qualif_date"] = QUALIF_DATE
        planned[cle] = v
        n_marked += 1
    print(f"  a marquer       : {n_marked}")
    print(f"  deja marquees   : {n_skip_already}")
    print(f"  total planned   : {len(planned)}")

    # ------------------------------------------------------------------
    # 5. AUDIT BLOQUANT : types avant == types apres
    # ------------------------------------------------------------------
    print("\n[5] AUDIT BLOQUANT - types avant vs apres...")
    sig_before = type_signature(assigns_live)
    sig_after = type_signature(planned)
    if sig_before != sig_after:
        # Detailler la diff
        diffs = []
        for cle in set(sig_before) | set(sig_after):
            if sig_before.get(cle) != sig_after.get(cle):
                diffs.append((cle, sig_before.get(cle), sig_after.get(cle)))
        print(f"  [ABORT] type a change pour {len(diffs)} cle(s) :")
        for cle, tb, ta in diffs[:20]:
            print(f"    {cle:35s}  '{tb}' -> '{ta}'")
        sys.exit("  ABORT IMMEDIAT : marquage modifie un type.")
    ct_before = Counter(sig_before.values())
    ct_after = Counter(sig_after.values())
    if ct_before != ct_after:
        print(f"  [ABORT] Counter avant {dict(ct_before)} != apres {dict(ct_after)}")
        sys.exit("  ABORT.")
    if set(sig_before) != set(sig_after):
        print(f"  [ABORT] set cles avant ({len(sig_before)}) != apres ({len(sig_after)})")
        sys.exit("  ABORT.")
    print(f"  OK : {len(sig_before)} cles, types identiques avant/apres.")
    print(f"  Counter strict : {dict(ct_after)}")

    # ------------------------------------------------------------------
    # 6. DRY-RUN affichage 5 echantillons + STOP
    # ------------------------------------------------------------------
    print("\n[6] Echantillon 5 entrees plan (avant -> apres) :")
    sample_cles = sorted(assigns_live)[:5]
    for cle in sample_cles:
        before = assigns_live.get(cle)
        after = planned.get(cle)
        print(f"  {cle}")
        print(f"    AVANT : {json.dumps(before, ensure_ascii=False)}")
        print(f"    APRES : {json.dumps(after, ensure_ascii=False)}")

    if not do_apply:
        print()
        print("=" * 78)
        print(f"DRY-RUN OK : {n_marked} cles a marquer, type inchange.")
        print(f"Snapshot et registry ecrits :")
        print(f"  {SNAPSHOT}")
        print(f"  {REGISTRY}")
        print(f"Pour appliquer (POST KV cloud + backup distinct + sync local) :")
        print(f"  python scripts/fix_kv_mp_legacy_mark.py apply")
        print("=" * 78)
        return

    # ==================================================================
    # APPLY : backup distinct + POST + re-GET + re-audit + sync local
    # ==================================================================

    print("\n[7] Backup distinct pre-mutation...")
    bak_payload = {
        "_meta": {
            "purpose": ("backup AVANT marquage legacy MP - "
                        "filet de restauration"),
            "secteur": AGENCE,
            "n_assignments": n_live,
        },
        "assignments": assigns_live,
        "fusions": fusions_live,
        "noms": noms_live,
    }
    KV_BAK.write_text(
        json.dumps(bak_payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ecrit : {KV_BAK.relative_to(ROOT)}")

    print("\n[8] POST KV cloud (assignments marques)...")
    post_body = {
        "assignments": planned,
        "fusions": fusions_live,
        "noms": noms_live,
    }
    st, body = kv_req(
        "POST", f"/secteur-assignments/{AGENCE}", body=post_body
    )
    if st != 200:
        sys.exit(f"  POST err: {st} {body!r}")
    print(f"  POST OK status={st}")

    print("\n[9] re-GET et re-audit strict...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  re-GET err: {st} {body!r}")
    assigns_after = body.get("assignments") or {}
    sig_re = type_signature(assigns_after)
    if sig_re != sig_before:
        diffs = []
        for cle in set(sig_before) | set(sig_re):
            if sig_before.get(cle) != sig_re.get(cle):
                diffs.append((cle, sig_before.get(cle), sig_re.get(cle)))
        print(f"  [ALERT] re-GET diverge :")
        for cle, tb, ta in diffs[:20]:
            print(f"    {cle:35s}  '{tb}' -> '{ta}'")
        sys.exit("  ALERT : cloud state inattendu apres POST.")
    n_marked_cloud = sum(
        1 for v in assigns_after.values()
        if (v or {}).get("_qualif_source") == QUALIF_SOURCE
    )
    print(f"  cloud assignments={len(assigns_after)}")
    print(f"  marques avec {QUALIF_SOURCE} : {n_marked_cloud}")
    print(f"  types preserves : OK")

    print("\n[10] Sync cache local data/_kv_assign_mp.json...")
    final = {
        "assignments": assigns_after,
        "fusions": body.get("fusions") or {},
        "noms": body.get("noms") or {},
    }
    KV_LOCAL.write_text(
        json.dumps(final, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ecrit : {KV_LOCAL.relative_to(ROOT)}")

    print()
    print("=" * 78)
    print("APPLY DONE")
    print(f"  cloud marques : {n_marked_cloud} / {len(assigns_after)}")
    print(f"  types inchanges : OK (audit bloquant + re-audit cloud)")
    print(f"  artefacts traceabilite :")
    print(f"    snapshot : {SNAPSHOT.relative_to(ROOT)}")
    print(f"    registry : {REGISTRY.relative_to(ROOT)}")
    print(f"    backup   : {KV_BAK.relative_to(ROOT)}")
    print(f"    cache    : {KV_LOCAL.relative_to(ROOT)}")
    print("=" * 78)


if __name__ == "__main__":
    main()
