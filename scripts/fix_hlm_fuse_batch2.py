#!/usr/bin/env python3
"""Batch HLM + 4 fantomes DL (lot 2) :

  Partie 1 - KV PATCH (3 HLM confirmes terrain) :
    31|RUE|DAUPHINE  -> social
    23|RUE|DAUPHINE  -> social
    35|RUE|DAUPHINE  -> social

  Partie 2 - RE-FUSE light JSON (4 fantomes confirmes terrain) :
    42|RUE|ST ANTOINE      -> 41|RUE|ST ANTOINE
       (39 deja FA->41 ; on ne fait pas de chaine, on rattache directement
        a l ancre 41, exactement comme 39 est attache. Apres : 39 et 42
        fanenent dans 41.)
       Label 41 : '39/41 RUE ST ANTOINE / 42 RUE ST ANTOINE'

    129|AVENUE|FELIX FAURE -> 138|AVENUE|FELIX FAURE
       (meme bgid JKBL-KRG6 ; 138 a immat RNC AB2812469.)
       Label 138 : '138 AVENUE FELIX FAURE / 129 AVENUE FELIX FAURE'

    7|RUE|CARRY            -> 5|RUE|CARRY
       (bgid different : 7 sur YECQ-FPCT, 5 sur 984W-VRFJ. Terrain
        confirme meme batiment - faux-matching make_light. Pure FA, pas
        de RE-POINT bgid : bgid YECQ reste anchored via 6 CARRY ancre,
        8 CARRY FA->6.)
       Label 5 : '5 RUE CARRY / 7 RUE CARRY'

    17|RUE|METALLURGIE     -> 21|RUE|METALLURGIE
       (bgid different : 17 sur C8ML-QMSG, 21 sur D7S5-UCGW. Terrain
        confirme meme batiment - faux-matching make_light. Pure FA ;
        bgid C8ML garde 18 METAL en ancre.)
       Label 21 : '21 RUE METALLURGIE / 17 RUE METALLURGIE'

Effets attendus :
  - KV cloud + local _kv_assign_dl.json : 3 social ajoutes
  - light : 4 RE-FUSE + 4 extensions label
  - parc DL UI : strictement neutre (tous bgids restent anchored
    via une autre adresse non-FA ou via RNC)
  - hr-actifs UI : -4 (les 4 sources sortent en FA)
  - filtre 'Sans ventes' : -7 (3 HLM via type=social + 4 FA)

Idempotence : metadata._correctif_hlm_fuse_batch2 verifie ; aborte si deja
applique.
"""
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.prehlmfusebatch2.bak"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
JWT = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
       "eyJhZ2VuY2UiOiJkYXVwaGluZS1sYWNhc3NhZ25lIiwiYWdlbmNlcyI6WyJkYXVwaGluZS1sYWNhc3NhZ25lIl0sInJvbGUiOiJwYXRyb24iLCJleHAiOjE3Nzk4MzExOTM0NDV9."
       "VwaMO5jqFtDtZ4L_5SACyom2ehgmSJ-kauLhFwA55pE")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

HLM_SOCIAL = [
    "31|RUE|DAUPHINE",
    "23|RUE|DAUPHINE",
    "35|RUE|DAUPHINE",
]

FUSES = [
    # (src_cle, tgt_cle, label, label_tgt_existant_attendu)
    ("42|RUE|ST ANTOINE",      "41|RUE|ST ANTOINE",
     "39/41 RUE ST ANTOINE / 42 RUE ST ANTOINE",
     "39/41 RUE ST ANTOINE"),
    ("129|AVENUE|FELIX FAURE", "138|AVENUE|FELIX FAURE",
     "138 AVENUE FELIX FAURE / 129 AVENUE FELIX FAURE", None),
    ("7|RUE|CARRY",            "5|RUE|CARRY",
     "5 RUE CARRY / 7 RUE CARRY", None),
    ("17|RUE|METALLURGIE",     "21|RUE|METALLURGIE",
     "21 RUE METALLURGIE / 17 RUE METALLURGIE", None),
]


# ============================================================
# PARTIE 1 : KV PATCH
# ============================================================
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


def apply_kv():
    print("=" * 70)
    print("PARTIE 1 : KV PATCH -> social (3 HLM)")
    print("=" * 70)

    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    print(f"  [GET] status={st}")
    if st != 200:
        sys.exit(f"  GET KV err: {body}")
    assigns = body.get("assignments") or {}
    fusions = body.get("fusions") or {}
    noms = body.get("noms") or {}
    print(f"  [GET] assignments={len(assigns)} fusions={len(fusions)} noms={len(noms)}")

    print("\n  Etat AVANT :")
    for c in HLM_SOCIAL:
        print(f"    {c:34s} : {assigns.get(c)}")

    for c in HLM_SOCIAL:
        assigns[c] = {"type": "social"}

    print("\n  [POST] atomique...")
    st, body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                      {"assignments": assigns, "fusions": fusions, "noms": noms})
    print(f"    status={st} body={body}")
    if st != 200:
        sys.exit("  POST KV echec")

    print("\n  Re-GET verif...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit("  Re-GET KV echec")
    a2 = body.get("assignments") or {}
    all_ok = True
    for c in HLM_SOCIAL:
        v = a2.get(c)
        ok = bool(v) and v.get("type") == "social"
        print(f"    [VERIF] {c:34s} -> {v}  [{'OK' if ok else 'FAIL'}]")
        if not ok:
            all_ok = False
    if not all_ok:
        sys.exit("  KV verif echec")

    # Mise a jour cache local
    if KV_LOCAL.exists():
        kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    else:
        kv_local = {"assignments": {}}
    kv_local.setdefault("assignments", {})
    for c in HLM_SOCIAL:
        kv_local["assignments"][c] = {"type": "social"}
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n  Local KV mis a jour : {KV_LOCAL.name} "
          f"({len(kv_local['assignments'])} assignments total)")


# ============================================================
# PARTIE 2 : RE-FUSE light (4 fantomes)
# ============================================================
def apply_light():
    print()
    print("=" * 70)
    print("PARTIE 2 : RE-FUSE light (4 fantomes)")
    print("=" * 70)

    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_hlm_fuse_batch2"):
        sys.exit("  [abort] _correctif_hlm_fuse_batch2 deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}

    # Verif presence des 8 cles
    for src, tgt, _, _ in FUSES:
        if src not in by_cle:
            sys.exit(f"  [abort] source absente: {src}")
        if tgt not in by_cle:
            sys.exit(f"  [abort] target absent: {tgt}")
        if by_cle[src].get("_fusion_auto"):
            sys.exit(f"  [abort] source deja FA: {src} (cible={by_cle[src].get('_fusion_cible')})")

    ops_log = []
    for src, tgt, label, label_attendu in FUSES:
        a_src = by_cle[src]
        a_tgt = by_cle[tgt]

        # Verif optionnelle du label cible existant
        cur_label_tgt = a_tgt.get("_fusion_auto_label")
        if label_attendu is not None and cur_label_tgt != label_attendu:
            print(f"  [warn] {tgt} label actuel='{cur_label_tgt}' != attendu='{label_attendu}'")

        # RE-FUSE source
        a_src["_fusion_auto"] = True
        a_src["_fusion_cible"] = tgt
        a_src["_bdnb_match"] = "correctif_hlm_fuse_batch2_re_fuse"
        print(f"\n  [RE-FUSE] {src:34s} -> {tgt}")
        print(f"            _fusion_auto=True  _fusion_cible='{tgt}'")

        # Extension label target
        a_tgt["_fusion_auto_label"] = label
        srcs = list(a_tgt.get("_fusion_auto_sources") or [])
        if src not in srcs:
            srcs.append(src)
        a_tgt["_fusion_auto_sources"] = srcs
        print(f"  [LABEL]   {tgt:34s} label='{label}'")
        print(f"            sources={srcs}")

        ops_log.append({"src": src, "tgt": tgt, "label": label, "sources": srcs})

    md["_correctif_hlm_fuse_batch2"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Batch 2 fantomes BGD_PARTAGE post-diag-sansventes-21-128 "
                   "(terrain confirme user)",
        "autorite": "Confirmation terrain user + diag _diag_sansventes_21_128.py "
                    "(BGD_PARTAGE 4/8 retenus apres tri terrain)",
        "kv_social": HLM_SOCIAL,
        "fuses": ops_log,
        "notes": {
            "42_st_antoine": "39 deja FA->41 ; 42 rattachee directement a 41 "
                             "(pas de chaine, 39+42 fanenent dans 41)",
            "129_138_felix_faure": "meme bgid JKBL-KRG6 ; 138 immat AB2812469",
            "7_5_carry": "bgid different (YECQ vs 984W) ; pure FA ; "
                         "bgid YECQ reste anchored via 6 CARRY",
            "17_21_metallurgie": "bgid different (C8ML vs D7S5) ; pure FA ; "
                                  "bgid C8ML reste anchored via 18 METAL",
        },
        "delta_parc_ui_attendu": 0,
        "delta_hr_actifs_attendu": -4,
        "delta_filtre_sansventes_attendu": -7,
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print(f"  [OK] 4 RE-FUSE + 4 extensions label appliques.")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    apply_kv()
    apply_light()
    print()
    print("=" * 70)
    print("BATCH HLM-FUSE-BATCH2 COMPLET.")
    print("Reste : bump CACHE_VERSION + commit + push (etapes externes).")
    print("=" * 70)
