#!/usr/bin/env python3
"""Nettoyage cosmetique des 12 facades fictives DAUPHINE mal qualifiees.

CONTEXTE :
  11 cles 25B/27B/29B/31B/33B/35B/53A/53B/55A/55C/55D RUE DAUPHINE
    - tag 'social' a tort (residuel d'un ancien batch)
    - FA-sources -> ancre 59|RUE|DAUPHINE
    - 0 vente propre (suffixes B/A/C/D absents dans DVF)
  1 cle 2B|RUE|DAUPHINE
    - tag 'mixte' (mis par le batch DVF decollect, faux positif controle)
    - FA-source -> ancre 2|RUE|DAUPHINE
    - 0 vente propre
  -> 12 cles a nettoyer (suppression de l'entry KV)

ANCRES PROTEGEES (NE PAS TOUCHER) :
  - 59|RUE|DAUPHINE (porte 9 ventes own pour ce groupe)
  - 2|RUE|DAUPHINE  (ancre de 2B)

PROCEDURE pattern _fix_*_dl.py :
  1. GET KV live (DPE_JWT)
  2. Audit pre-PATCH : pour CHAQUE cle, verifier
       - tag courant == expected (social pour 11, mixte pour 2B)
       - _fusion_auto == True
       - _fusion_cible == ancre attendue
       - nb_ventes_logement == 0 (own ventes nulles)
     Si un check rate, EXCLURE et signaler.
  2b. Verifier ancres 59 et 2 DAUPHINE PAS dans le batch + intactes.
  3. Backup data/_kv_assign_dl.pre_clean_fa.bak
  4. DRY-RUN affichage + STOP
  5. Sur apply :
       - del assigns[cle] pour les 12 cibles confirmees
       - POST atomique
       - re-GET ancres (intactes) + 3 temoins parmi les 12 (absents)
       - Maj _kv_assign_dl.json local
       - Maj _social_overrides_dl.json : RETIRER 2B DAUPHINE de la liste
         (n'etait pas un vrai reclassement)
"""
import json
import os
import random
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
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
KV_BAK = ROOT / "data" / "_kv_assign_dl.pre_clean_fa.bak"
OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

JWT = os.environ.get("DPE_JWT") or ""

# 12 cles a nettoyer : (cle, tag_attendu_actuel, ancre_FA_attendue)
CIBLES = [
    ("25B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("27B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("29B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("31B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("33B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("35B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("53A|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("53B|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("55A|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("55C|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("55D|RUE|DAUPHINE", "social", "59|RUE|DAUPHINE"),
    ("2B|RUE|DAUPHINE",  "mixte",  "2|RUE|DAUPHINE"),
]
ANCRES_PROTEGEES = {"59|RUE|DAUPHINE", "2|RUE|DAUPHINE"}


def kv_req(method, path, body=None):
    if not JWT:
        sys.exit("  [abort] env DPE_JWT absente")
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


def main():
    do_apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")
    mode = "APPLY" if do_apply else "DRY-RUN"
    print("=" * 78)
    print(f"NETTOYAGE 12 FA DAUPHINE ({mode})")
    print("=" * 78)

    # ---------- 1. GET KV ----------
    print("\n[1] GET KV live cloud...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  GET KV err: {st} {body}")
    assigns_cloud = body.get("assignments") or {}
    fusions_cloud = body.get("fusions") or {}
    noms_cloud = body.get("noms") or {}
    print(f"  assignments={len(assigns_cloud)}")

    # ---------- 2. Audit pre-PATCH ----------
    print("\n[2] Audit pre-PATCH (FA-source + tag + 0 own vente)")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}

    will_clean = []
    excluded = []
    for cle, expected_tag, expected_ancre in CIBLES:
        a = by_cle.get(cle)
        if not a:
            excluded.append((cle, "ABSENT light", None))
            continue
        cur_t = ((assigns_cloud.get(cle) or {}).get("type")) or ""
        is_fa = bool(a.get("_fusion_auto"))
        cible_fa = a.get("_fusion_cible") or a.get("_fusion_auto_target") or ""
        own_vlog = a.get("nb_ventes_logement") or 0

        reasons = []
        if cur_t != expected_tag:
            reasons.append(f"tag courant '{cur_t}' != attendu '{expected_tag}'")
        if not is_fa:
            reasons.append("PAS FA-source")
        if cible_fa != expected_ancre:
            reasons.append(f"FA-cible '{cible_fa}' != attendu '{expected_ancre}'")
        if own_vlog > 0:
            reasons.append(f"own ventes_logement={own_vlog} > 0 (a des "
                           f"ventes propres, NE PAS nettoyer)")

        if reasons:
            excluded.append((cle, " ; ".join(reasons), cur_t))
        else:
            will_clean.append((cle, cur_t, expected_ancre,
                                assigns_cloud.get(cle) or {}))

    print(f"  CIBLES initiales : {len(CIBLES)}")
    print(f"  A NETTOYER       : {len(will_clean)}")
    print(f"  EXCLUS           : {len(excluded)}")
    if excluded:
        for cle, raison, cur in excluded:
            print(f"    [SKIP] {cle:24s} : {raison}")

    # 2b. Verif ancres protegees
    print(f"\n[2b] Verif ancres protegees ({len(ANCRES_PROTEGEES)} cles)")
    for ancre in sorted(ANCRES_PROTEGEES):
        a = by_cle.get(ancre) or {}
        v_kv = assigns_cloud.get(ancre) or {}
        in_batch = any(c == ancre for c, _, _, _ in will_clean)
        immat = a.get("numero_immatriculation") or "-"
        own_v = a.get("nb_ventes_logement") or 0
        cur_t = v_kv.get("type", "(absent)")
        flag = "WARN DANS BATCH" if in_batch else "PROTEGE"
        print(f"  {ancre:24s} immat={immat:12s} own_ventes={own_v:>3} "
              f"tag_KV={cur_t:>12s} -> {flag}")
        if in_batch:
            sys.exit("  [abort] ANCRE dans le batch !!!")

    # ---------- 3. Backup ----------
    print(f"\n[3] Backup -> {KV_BAK.name}")
    snapshot = {
        "_meta": {
            "captured_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agence": AGENCE,
            "purpose": ("pre-clean-fa-dl : suppression tag residuel sur "
                         "12 FA-sources DAUPHINE (11 social + 1 mixte). "
                         "Ancres 59 et 2 DAUPHINE intactes."),
            "ancres_protegees": sorted(ANCRES_PROTEGEES),
            "n_to_clean": len(will_clean),
            "n_excluded": len(excluded),
        },
        "assignments": assigns_cloud,
        "fusions": fusions_cloud,
        "noms": noms_cloud,
    }
    if KV_BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {KV_BAK.name}")
    KV_BAK.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  ecrit {len(assigns_cloud)} assignments")

    # ---------- 4. DRY-RUN ----------
    print()
    print("=" * 78)
    print("DIFF prevu")
    print("=" * 78)
    print(f"\n  Methode : del assigns[cle]  (retour etat 'non qualifie')")
    print()
    print(f"  {'#':>3} {'cle':24s} {'tag avant':10s} {'cur full':40s} {'-> apres':30s}")
    print("  " + "-" * 110)
    for i, (cle, cur_t, ancre, cur_v) in enumerate(will_clean, 1):
        cur_str = json.dumps(cur_v, ensure_ascii=False)[:38]
        print(f"  {i:>3} {cle:24s} {cur_t:10s} {cur_str:40s} -> (entry supprime)")

    print(f"\n  Ancres PROTEGEES (non touchees) :")
    for ancre in sorted(ANCRES_PROTEGEES):
        a = by_cle.get(ancre) or {}
        v = assigns_cloud.get(ancre) or {}
        print(f"    {ancre:24s} tag={v.get('type', 'None'):>10s}  "
              f"own_ventes={a.get('nb_ventes_logement') or 0}")

    if not do_apply:
        print()
        print("=" * 78)
        print(f"DRY-RUN : STOP. Lance avec 'apply' pour POSTer.")
        print(f"  A nettoyer : {len(will_clean)} cles ; exclus : {len(excluded)}")
        print(f"  Backup en place : {KV_BAK.name}")
        print("=" * 78)
        return

    # ---------- 5. APPLY ----------
    print()
    print("=" * 78)
    print("APPLY : POST atomique...")
    print("=" * 78)
    for cle, _, _, _ in will_clean:
        if cle in assigns_cloud:
            del assigns_cloud[cle]
    st, body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                       {"assignments": assigns_cloud,
                        "fusions": fusions_cloud, "noms": noms_cloud})
    print(f"  status={st} body={body}")
    if st != 200:
        sys.exit("  POST echec")

    # ---------- 6. Re-GET + verif ----------
    print(f"\n[VERIF] re-GET ancres + 3 temoins parmi les 12...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  Re-GET err: {body}")
    a2 = body.get("assignments") or {}

    # Ancres
    fails = 0
    for ancre in sorted(ANCRES_PROTEGEES):
        v_apres = a2.get(ancre)
        v_avant = (snapshot["assignments"].get(ancre) or {}) or None
        # On compare juste presence : ancre doit etre identique a avant
        ok = (v_apres == v_avant) or (v_apres is None and not v_avant)
        flag = "INTACTE" if ok else "WARN MODIFIE"
        print(f"  ANCRE {ancre:24s} -> {v_apres}  ({flag})")
        if not ok:
            fails += 1

    # 3 temoins
    random.seed(42)
    sample = random.sample([c for c, _, _, _ in will_clean],
                            min(3, len(will_clean)))
    for cle in sample:
        v = a2.get(cle)
        ok = v is None
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] {cle:24s} -> {v}  (attendu: absent)")
        if not ok:
            fails += 1
    if fails:
        sys.exit(f"  [abort] {fails} verifications fail")

    # Maj cache local
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8")) \
        if KV_LOCAL.exists() else {"assignments": {}}
    kv_local["assignments"] = assigns_cloud
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n  [local] {KV_LOCAL.name} mis a jour "
          f"({len(assigns_cloud)} assignments)")

    # Maj _social_overrides_dl.json : retirer 2B DAUPHINE
    if OVERRIDES.exists():
        ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        before_n = len(ov.get("overrides", []))
        ov["overrides"] = [o for o in ov.get("overrides", [])
                           if o.get("cle") != "2B|RUE|DAUPHINE"]
        after_n = len(ov["overrides"])
        # Note dans meta
        ov.setdefault("_meta", {})["last_cleanup"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "removed": ["2B|RUE|DAUPHINE"],
            "reason": ("FA-source 0 own vente : pas un vrai reclassement, "
                        "retire de la liste pour eviter double-tracking"),
        }
        OVERRIDES.write_text(json.dumps(ov, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        print(f"  [overrides] {OVERRIDES.name} : "
              f"{before_n} -> {after_n} cles (retire 2B DAUPHINE)")

    print()
    print("=" * 78)
    print(f"APPLY REUSSI : {len(will_clean)} cles nettoyees ; "
          f"{len(excluded)} exclues.")
    print(f"  Ancres {sorted(ANCRES_PROTEGEES)} : INTACTES.")
    print("=" * 78)


if __name__ == "__main__":
    main()
