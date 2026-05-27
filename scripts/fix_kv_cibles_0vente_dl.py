#!/usr/bin/env python3
"""Tag KV des 120 cibles prospection 0-vente DL.

Pattern _fix_*_dl.py (audit + backup distinct + DRY-RUN + STOP + apply
explicite).

DEUX TAGS distincts :
  - cible_0vente_active : 91 DISTINCT (voisin vend, quartier liquide,
    copro figee = cible chaude)
  - cible_0vente_isolee : 29 AUCUN_DVF (aucune vente +/-2, zone
    dormante ou full-PP = a qualifier)

Procedure :
  1. GET KV live (depuis env DPE_JWT)
  2. Reproduire le filtre Sans ventes UI (avec autoMerged) -> 120 cles
  3. Pour chaque cle : classifier DISTINCT vs AUCUN vs FUSION
     (le seul cas FUSION = 12 ESPERANCE, re-classe DISTINCT par
     decision user precedente)
  4. Audit pre-PATCH : si type courant in {social,bureaux,mono,mixte,
     cible_0vente_*} -> EXCLURE et signaler
  5. Backup data/_kv_assign_dl.pre_cible_0vente.bak (distinct du
     backup batch MAJIC)
  6. DRY-RUN : affichage + STOP
  7. Sur 'apply' : POST atomique + re-GET 3 cles temoins + maj cache local

Usage :
  python scripts/fix_kv_cibles_0vente_dl.py        # DRY
  python scripts/fix_kv_cibles_0vente_dl.py apply  # APPLY
"""
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
KV_BAK = ROOT / "data" / "_kv_assign_dl.pre_cible_0vente.bak"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")
ANS = ("2021", "2022", "2023", "2024", "2025")

JWT = os.environ.get("DPE_JWT")
if not JWT:
    sys.exit("  [abort] env var DPE_JWT absente.")

# Normalisation toks/numof (cf fix_taux_logement.py)
ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else ""


def is_logement(m):
    return str(m.get("Code type local") or "").strip() in ("1", "2")


# ============================================================
def kv_req(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {JWT}",
               "User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ============================================================
def main():
    do_apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")
    mode = "APPLY" if do_apply else "DRY-RUN"

    print("=" * 78)
    print(f"TAG KV CIBLES 0-VENTE DL  (mode = {mode})")
    print("=" * 78)

    # ---------- 1. GET KV ----------
    print("\n[1] GET KV live cloud...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  GET KV err: {st} {body}")
    assigns_cloud = body.get("assignments") or {}
    fusions_cloud = body.get("fusions") or {}
    noms_cloud = body.get("noms") or {}
    print(f"  assignments={len(assigns_cloud)}  fusions={len(fusions_cloud)}")

    # ---------- 2. Reproduire population 0-vente Sans ventes UI ----------
    print("\n[2] Reproduction filtre Sans ventes UI complet...")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c
                 for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}

    def kv_type(cle):
        return ((assigns_cloud.get(cle) or {}).get("type")) or ""

    def vpa(a):
        return a.get("ventes_par_an_logement") or {}

    # mergedInto (KV fusions manuelles) + fused_src
    merged_into = {}
    fused_src = set()
    for src, dst in fusions_cloud.items():
        sa = by_cle.get(src)
        if not sa or not dst or src == dst:
            continue
        fused_src.add(src)
        m = merged_into.setdefault(dst, {"ventes": {}})
        for y in ANS:
            m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

    # autoMerged (BDNB FA)
    auto_merged = {}
    for a in ad:
        cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
        cle = a.get("cle") or ""
        if a.get("_fusion_auto") and cible and cle not in fused_src:
            fused_src.add(cle)
            am = auto_merged.setdefault(cible, {"ventes": {}})
            for y in ANS:
                am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

    pop = []
    for a in ad:
        cle = a.get("cle") or ""
        if cle in fused_src:
            continue
        t = kv_type(cle)
        if t in ("social", "bureaux", "mono"):
            continue
        is_copro_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
        is_copro_ni = (t == "copro_non_immat")
        is_mixte = (t == "mixte")
        if not (is_copro_rnc or is_copro_ni or is_mixte):
            continue
        vlog = int(a.get("nb_ventes_logement") or 0)
        if vlog > 0:
            continue
        vpa_log = a.get("ventes_par_an_logement") or {}
        if any((vpa_log.get(y) or 0) > 0 for y in ANS):
            continue
        if is_copro_rnc:
            mi = merged_into.get(cle)
            if mi and any((mi["ventes"].get(y) or 0) > 0 for y in ANS):
                continue
        am = auto_merged.get(cle)
        if am and any((am["ventes"].get(y) or 0) > 0 for y in ANS):
            continue
        pop.append(a)

    print(f"  Population 0-vente filtre : {len(pop)} adresses")

    # ---------- 3. Classifier DISTINCT vs AUCUN ----------
    print("\n[3] Classification DISTINCT (voisin +/-2 vend) vs "
          "AUCUN (aucun DVF +/-2)...")
    dvf = json.loads(DVF.read_text(encoding="utf-8"))
    dvf_log_by_key = defaultdict(list)
    for m in dvf:
        if not is_logement(m):
            continue
        nv = numof(m.get("No voie"))
        vt = toks(m.get("Voie") or "")
        if not nv or not vt:
            continue
        dvf_log_by_key[(nv, vt)].append(m)

    def parse_cle(cle):
        p = cle.split("|")
        if len(p) != 3:
            return None
        m = re.match(r"^(\d+)([A-Z]*)$", p[0].upper())
        if not m:
            return None
        return m.group(1), m.group(2), toks(p[2])

    distinct = []  # voisin +/-2 vend
    aucun = []      # rien +/-2
    for a in pop:
        cle = a["cle"]
        parsed = parse_cle(cle)
        if parsed is None:
            aucun.append(a)
            continue
        num_base, _, voie_toks = parsed
        try:
            n_int = int(num_base)
            voisin_vend = False
            for delta in (-2, -1, 1, 2):
                rows = dvf_log_by_key.get((str(n_int + delta), voie_toks), [])
                if rows:
                    voisin_vend = True
                    break
            if voisin_vend:
                distinct.append(a)
            else:
                aucun.append(a)
        except (ValueError, TypeError):
            aucun.append(a)

    print(f"  DISTINCT (voisin +/-2 vend)  : {len(distinct)}")
    print(f"  AUCUN (aucun DVF +/-2)       : {len(aucun)}")
    print(f"  TOTAL                         : {len(distinct) + len(aucun)} "
          f"(attendu {len(pop)})")

    # Construction du batch : (cle, tag)
    batch = [(a["cle"], "cible_0vente_active") for a in distinct]
    batch += [(a["cle"], "cible_0vente_isolee") for a in aucun]

    # ---------- 4. Audit pre-PATCH ----------
    print("\n[4] Audit pre-PATCH (tags existants a preserver)...")
    will_patch = []
    excluded = []
    PROTECTED_TAGS = ("social", "bureaux", "mono", "mixte",
                      "cible_0vente_active", "cible_0vente_isolee")
    for cle, new_tag in batch:
        cur_t = ((assigns_cloud.get(cle) or {}).get("type")) or ""
        if cur_t in PROTECTED_TAGS:
            excluded.append((cle, cur_t, new_tag))
        elif cur_t in ("", "copro_non_immat"):
            will_patch.append((cle, cur_t, new_tag))
        else:
            # Tag inattendu - signaler et exclure par prudence
            excluded.append((cle, cur_t, new_tag))

    if excluded:
        print(f"  EXCLUS ({len(excluded)}) - tag existant a preserver :")
        cnt_by_tag = Counter(t for _, t, _ in excluded)
        for t, n in cnt_by_tag.most_common():
            print(f"    {t:25s} : {n} cles")
        # Detail
        for cle, cur, new in excluded:
            print(f"    [SKIP] {cle:34s} cur='{cur}' (aurait recu '{new}')")

    print(f"\n  A PATCHER : {len(will_patch)} cles")
    cnt_new = Counter(new for _, _, new in will_patch)
    for t, n in cnt_new.most_common():
        print(f"    {t:30s} : {n}")

    # ---------- 5. Backup distinct ----------
    print(f"\n[5] Backup distinct : {KV_BAK.name}")
    snapshot = {
        "_meta": {
            "captured_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agence": AGENCE,
            "purpose": "pre-tag-cible-0vente-dl (120 candidats)",
            "batch_summary": dict(cnt_new),
        },
        "assignments": assigns_cloud,
        "fusions": fusions_cloud,
        "noms": noms_cloud,
    }
    if KV_BAK.exists():
        print(f"  [warn] backup existant -> ecrase : {KV_BAK.name}")
    KV_BAK.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  ecrit {len(assigns_cloud)} assignments")

    # ---------- 6. Affichage tableau ----------
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

    def majic_top(cle):
        e = enrich_by_cle.get(cle)
        if not e:
            return "-"
        sirens = (e.get("sirens") or [])
        if not sirens:
            return f"({e.get('majic_lots') or 0} lots PM, 0 SIREN)"
        top = sirens[0]
        return (f"{top.get('denomination', '?')[:30]}"
                f"({top.get('lots')}/{top.get('pct_lots')}%)")

    print()
    print("=" * 120)
    print(f"DRY-RUN : Liste a patcher (trie nb_log_bdnb DESC)")
    print("=" * 120)
    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'tag':25s} {'top SIREN MAJIC'}")
    print("  " + "-" * 118)
    will_patch_sorted = sorted(
        will_patch,
        key=lambda x: -((by_cle[x[0]].get("nb_log_bdnb") or 0))
    )
    for i, (cle, cur, new) in enumerate(will_patch_sorted, 1):
        bdnb = by_cle[cle].get("nb_log_bdnb") or 0
        print(f"  {i:>3} {cle:32s} {bdnb:>6} {new:25s} {majic_top(cle)}")

    # ---------- 7. STOP ou APPLY ----------
    if not do_apply:
        print()
        print("=" * 78)
        print("DRY-RUN : STOP. Tape 'apply' pour POSTer.")
        print(f"Backup deja en place : {KV_BAK.name}")
        print(f"Patches a appliquer : {len(will_patch)} ; exclus : {len(excluded)}")
        print("=" * 78)
        return

    # APPLY
    print()
    print("=" * 78)
    print("APPLY : POST atomique...")
    print("=" * 78)
    for cle, _, new in will_patch:
        assigns_cloud[cle] = {"type": new}
    st, post_body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                            {"assignments": assigns_cloud,
                             "fusions": fusions_cloud,
                             "noms": noms_cloud})
    print(f"  status={st}  body={post_body}")
    if st != 200:
        sys.exit("  POST echec")

    # Re-GET 3 cles temoins
    print("\n[VERIF] re-GET 3 cles temoins...")
    random.seed(42)
    sample = random.sample([c for c, _, _ in will_patch], min(3, len(will_patch)))
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  Re-GET err: {body}")
    a2 = body.get("assignments") or {}
    fails = 0
    for cle in sample:
        v = a2.get(cle)
        expected = next(new for c, _, new in will_patch if c == cle)
        ok = bool(v) and v.get("type") == expected
        print(f"  [{'OK' if ok else 'FAIL'}] {cle:34s} -> {v} "
              f"(attendu '{expected}')")
        if not ok:
            fails += 1
    if fails:
        sys.exit(f"  [abort] {fails}/3 fails")

    # Maj cache local
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8")) \
        if KV_LOCAL.exists() else {"assignments": {}}
    kv_local["assignments"] = assigns_cloud
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n  [local] {KV_LOCAL.name} mis a jour "
          f"({len(assigns_cloud)} assignments)")

    print()
    print("=" * 78)
    print(f"APPLY REUSSI : {len(will_patch)} cles taggees ; "
          f"{len(excluded)} exclues ; 3/3 sample OK.")
    print("=" * 78)


if __name__ == "__main__":
    main()
