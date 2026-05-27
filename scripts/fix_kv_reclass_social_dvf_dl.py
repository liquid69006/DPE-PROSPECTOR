#!/usr/bin/env python3
"""Reclassement KV des 27 faux positifs social DL (DVF decollect).

LOT FERME : uniquement les cles 'FAUX POSITIF CONFIRME'
(social_pct_corrige < 60% OU mutations_Apt >= 2/an).
NE TOUCHE PAS aux 11 cles zone grise (1 <= mut/an < 2).

Pattern _fix_*_dl.py :
  1. GET KV live (DPE_JWT)
  2. Reproduit le diag combined MAJIC+DVF
  3. Filtre FAUX_POSITIF_CONFIRME
  4. Audit pre-PATCH : cles doivent etre 'social' currently
  5. Backup data/_kv_assign_dl.pre_social_reclass.bak
  6. DRY-RUN affichage + STOP
  7. Sur apply : POST atomique + re-GET 3 temoins + maj cache local
     + ecrit data/_social_overrides_dl.json (override file pour proteger
     de futurs auto-tags MAJIC-seul)

Chaque valeur KV reclassee porte :
  {
    "type": "mixte" ou "copro_non_immat",
    "_qualif_source": "dvf_decollect",
    "_qualif_date": "2026-...Z",
    "_social_pct_corrige": float,
    "_mut_apt_per_year": float,
    "_previous_tag": "social"
  }

Usage :
  $env:DPE_JWT='<jwt>'  (PowerShell - doit etre posee avant)
  python scripts/fix_kv_reclass_social_dvf_dl.py           # DRY
  python scripts/fix_kv_reclass_social_dvf_dl.py apply     # APPLY
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
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
KV_BAK = ROOT / "data" / "_kv_assign_dl.pre_social_reclass.bak"
OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

JWT = os.environ.get("DPE_JWT") or ""

HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT", "OFFICE PUBLIC DE L'HABITAT",
)


def is_hlm_denom(denom):
    if not denom:
        return False
    d = denom.upper()
    return any(n in d for n in HLM_NEEDLES if n.strip())


def parcelle_to_dvf_key(parc):
    sec = parc[8:10]
    plan = parc[10:].lstrip("0") or "0"
    return (sec, plan)


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
    print(f"RECLASSEMENT SOCIAL DVF DL ({mode})")
    print("=" * 78)

    # ---------- Charger sources ----------
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}

    # GET KV (cloud si APPLY, sinon local cache pour DRY-RUN)
    if do_apply:
        if not JWT:
            sys.exit("  [abort] env DPE_JWT requise pour APPLY")
        print("\n[GET] KV live cloud...")
        st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
        if st != 200:
            sys.exit(f"  GET KV err: {st} {body}")
        assigns = body.get("assignments") or {}
        fusions = body.get("fusions") or {}
        noms = body.get("noms") or {}
        print(f"  assignments={len(assigns)}")
    else:
        print("\n[DRY-RUN] lecture cache local _kv_assign_dl.json (pas de GET cloud)")
        kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
        assigns = kv.get("assignments") or {}
        fusions = kv.get("fusions") or {}
        noms = kv.get("noms") or {}
        print(f"  local assignments={len(assigns)}")

    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

    # ---------- DVF ----------
    print("\n[DVF] chargement + index parcelles...")
    dvf = json.loads(DVF.read_text(encoding="utf-8"))
    dvf_by_parc = defaultdict(list)
    for m in dvf:
        sec = m.get("Section") or ""
        plan = m.get("No plan") or ""
        if not sec or not plan:
            continue
        plan_norm = plan.lstrip("0") or "0"
        if str(m.get("Code type local") or "").strip() in ("1", "2"):
            dvf_by_parc[(sec, plan_norm)].append(m)

    def mutations_apt(parcs):
        seen = set()
        for parc in parcs:
            for m in dvf_by_parc.get(parcelle_to_dvf_key(parc), []):
                seen.add((m.get("Date mutation"), m.get("No disposition"),
                          m.get("Valeur fonciere")))
        return len(seen)

    # ---------- Compute verdicts pour 209 social ----------
    social_cles = [c for c, v in assigns.items()
                    if (v or {}).get("type") == "social"]
    print(f"\n  Cles social actuelles : {len(social_cles)}")

    faux_pos = []
    for cle in social_cles:
        cp = co_by_cle.get(cle, {})
        a = by_cle.get(cle, {})
        e = enrich_by_cle.get(cle, {})

        rnc_habit = cp.get("nb_lots_habitation") or 0
        rnc_total = cp.get("nb_lots_total") or 0
        sirens = e.get("sirens") or []
        parcs = e.get("parcelles_bdnb") or []
        hlm_pm = sum(s.get("lots") or 0 for s in sirens
                      if is_hlm_denom(s.get("denomination")))

        if rnc_habit > 0 and rnc_total > 0:
            prop = rnc_habit / rnc_total
            hlm_habit_estim = round(hlm_pm * prop, 1)
            pct_cor = round(hlm_habit_estim * 100 / rnc_habit, 1)
        elif rnc_habit > 0:
            pct_cor = round(hlm_pm * 100 / rnc_habit, 1)
        else:
            pct_cor = None

        mut_5 = mutations_apt(parcs)
        mut_an = round(mut_5 / 5, 2)

        pct_low = pct_cor is not None and pct_cor < 60
        mut_high = mut_an >= 2.0
        if not (pct_low or mut_high):
            continue  # pas un faux positif

        has_immat = bool(cp.get("numero_immatriculation")
                         or a.get("numero_immatriculation"))
        new_tag = "mixte" if has_immat else "copro_non_immat"
        faux_pos.append({
            "cle": cle,
            "social_pct_corrige": pct_cor,
            "mut_apt_5ans": mut_5,
            "mut_per_year": mut_an,
            "has_immat": has_immat,
            "new_tag": new_tag,
            "raison_pct": "pct<60" if pct_low else None,
            "raison_mut": "mut>=2/an" if mut_high else None,
        })

    # Tri par mut/an DESC
    faux_pos.sort(key=lambda r: (-r["mut_per_year"], -(r["social_pct_corrige"] or 0)))
    print(f"\n  FAUX_POSITIF_CONFIRME identifies : {len(faux_pos)}")

    # ---------- Audit pre-PATCH ----------
    print(f"\n[AUDIT] verif tag courant = 'social' pour les {len(faux_pos)} cles")
    will_patch = []
    excluded = []
    for r in faux_pos:
        cur_t = ((assigns.get(r["cle"]) or {}).get("type")) or ""
        if cur_t != "social":
            excluded.append((r["cle"], cur_t, r["new_tag"]))
        else:
            will_patch.append(r)
    if excluded:
        print(f"  EXCLUS ({len(excluded)}) - tag courant != social :")
        for cle, cur, new in excluded:
            print(f"    [SKIP] {cle:34s} cur='{cur}' (aurait recu '{new}')")
    print(f"  A PATCHER : {len(will_patch)}")

    # ---------- Backup ----------
    print(f"\n[BAK] backup distinct -> {KV_BAK.name}")
    snapshot = {
        "_meta": {
            "captured_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agence": AGENCE,
            "purpose": ("pre-reclass-social-dvf-dl (27 faux positifs "
                         "FAUX_POSITIF_CONFIRME) ; backup distinct du "
                         "pre_cible_0vente et pre_batch_majic"),
            "n_to_patch": len(will_patch),
            "n_excluded": len(excluded),
        },
        "assignments": assigns,
        "fusions": fusions,
        "noms": noms,
    }
    if KV_BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {KV_BAK.name}")
    KV_BAK.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  ecrit {len(assigns)} assignments")

    # ---------- Tableau DRY-RUN ----------
    print()
    print("=" * 120)
    print(f"TABLEAU DRY-RUN (tri mutations/an DESC)")
    print("=" * 120)
    print(f"  {'#':>3} {'cle':32s} {'tag AVANT':10s} -> {'nouveau':16s} "
          f"{'%COR':>7} {'mut/an':>7} {'raison_verdict'}")
    print("  " + "-" * 118)
    cnt_new = Counter(r["new_tag"] for r in will_patch)
    for i, r in enumerate(will_patch, 1):
        pct = (f"{r['social_pct_corrige']:>6.1f}%"
                if r["social_pct_corrige"] is not None else "  N/A ")
        rs = []
        if r["raison_pct"]:
            rs.append(r["raison_pct"])
        if r["raison_mut"]:
            rs.append(r["raison_mut"])
        raison = " + ".join(rs)
        print(f"  {i:>3} {r['cle']:32s} {'social':10s} -> {r['new_tag']:16s} "
              f"{pct:>7} {r['mut_per_year']:>6.2f} {raison}")

    print()
    print(f"  Reclassements proposes :")
    for tag, n in cnt_new.most_common():
        print(f"    {tag:20s} : {n}")

    # ---------- STOP / APPLY ----------
    if not do_apply:
        print()
        print("=" * 78)
        print(f"DRY-RUN : STOP. Backup ecrit. Lance avec 'apply' pour POSTer.")
        print(f"Cles a patcher : {len(will_patch)} ; exclus : {len(excluded)}")
        print(f"NB : 11 cles 'zone grise' (1 <= mut/an < 2) NON incluses.")
        print("=" * 78)
        return

    # APPLY
    print()
    print("=" * 78)
    print(f"APPLY : POST atomique...")
    print("=" * 78)
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Construire override JSON parallele (filet de securite)
    overrides_doc = {
        "_meta": {
            "generated_at": now_iso,
            "secteur": "dauphine-lacassagne",
            "purpose": ("Protect these cles from being re-tagged 'social' "
                         "by future MAJIC-only scans (PM-only heuristic). "
                         "DVF mutations or social_pct_corrige confirm they "
                         "are NOT pure HLM social."),
            "rule": ("Si une cle figure ici, le scan MAJIC ne doit PAS "
                      "lui auto-attribuer 'social'. Le tag manuel "
                      "(_qualif_source='dvf_decollect') prevaut."),
        },
        "overrides": [],
    }

    for r in will_patch:
        assigns[r["cle"]] = {
            "type": r["new_tag"],
            "_qualif_source": "dvf_decollect",
            "_qualif_date": now_iso,
            "_social_pct_corrige": r["social_pct_corrige"],
            "_mut_apt_per_year": r["mut_per_year"],
            "_previous_tag": "social",
        }
        overrides_doc["overrides"].append({
            "cle": r["cle"],
            "previous_tag": "social",
            "new_tag": r["new_tag"],
            "qualif_source": "dvf_decollect",
            "social_pct_corrige": r["social_pct_corrige"],
            "mut_apt_per_year": r["mut_per_year"],
            "reason": " + ".join(filter(None, [r["raison_pct"], r["raison_mut"]])),
        })

    st, body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                       {"assignments": assigns, "fusions": fusions,
                        "noms": noms})
    print(f"  status={st} body={body}")
    if st != 200:
        sys.exit("  POST echec")

    # ---------- VERIF 3 temoins (incl 28 ETIENNE) ----------
    print(f"\n[VERIF] re-GET temoins...")
    pool = [r["cle"] for r in will_patch]
    sample = ["28|RUE|ETIENNE RICHERAND"]
    rest = [c for c in pool if c != "28|RUE|ETIENNE RICHERAND"]
    random.seed(42)
    sample += random.sample(rest, min(2, len(rest)))

    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  Re-GET err: {body}")
    a2 = body.get("assignments") or {}
    fails = 0
    for cle in sample:
        v = a2.get(cle)
        expected = next((r["new_tag"] for r in will_patch
                          if r["cle"] == cle), None)
        ok = (bool(v) and v.get("type") == expected
              and v.get("_qualif_source") == "dvf_decollect")
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] {cle:34s} -> {v}")
        if not ok:
            fails += 1
    if fails:
        sys.exit(f"  [abort] {fails}/{len(sample)} fails")

    # Maj cache local
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8")) \
        if KV_LOCAL.exists() else {"assignments": {}}
    kv_local["assignments"] = assigns
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"  [local] {KV_LOCAL.name} mis a jour")

    # Ecrit overrides
    OVERRIDES.write_text(json.dumps(overrides_doc, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"  [overrides] {OVERRIDES.name} ecrit ({len(overrides_doc['overrides'])} cles)")

    print()
    print("=" * 78)
    print(f"APPLY REUSSI : {len(will_patch)} cles reclassees ; "
          f"{len(excluded)} exclues ; {len(sample)-fails}/{len(sample)} sample OK.")
    print("=" * 78)


if __name__ == "__main__":
    main()
