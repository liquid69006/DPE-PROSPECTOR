#!/usr/bin/env python3
"""Scan MAJIC exhaustif des adresses light DL sans tag KV.

Pour chaque adresse light (hors FA, sans type KV manuel) :
  1. Recupere parcelles BDNB via _enrich_majic_dl_full.json
  2. Interroge MAJIC parquet (code_droit Proprietaire/Emphyteote, exclut
     Syndic/Mandataire)
  3. Calcule social_pct (gestion via emphyteote HLM ou propriete HLM)
  4. Classifie :
       social_pct >= 60 OU Emphyteote HLM   -> SOCIAL
       social_pct 20-60                      -> MIXTE
       1 SIREN prive >= 80                   -> MONO
       usage_principal_bdnb = Tertiaire      -> BUREAUX
       sinon                                  -> laisser
  5. Affiche tableau pre-patch, trie nb_log_bdnb DESC

Sources lecture seule :
  - data/secteur_dauphine_lacassagne_light.json
  - data/_enrich_majic_dl_full.json   (parcelles_bdnb + sirens cached)
  - data/_kv_assign_dl.json           (tags KV locaux)
  - majic_locaux2_2025.parquet        (code_droit + groupe_personne_libelle)

Mode : --dry (display only, defaut)   ou   --apply (POST KV atomique)
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
# JWT lu depuis env DPE_JWT, requis uniquement en mode --apply.
JWT = os.environ.get("DPE_JWT") or ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")


# ---------- Helpers ----------
def normalize_gp(s):
    return (s or "").lower()


def is_hlm_social(gp_lib, denomination, forme):
    g = normalize_gp(gp_lib)
    d = normalize_gp(denomination)
    f = normalize_gp(forme)
    if "office hlm" in g or " hlm" in g or g.startswith("hlm"):
        return True
    if " hlm " in d or "hlm-" in d or "habitat" in d or "logement social" in d:
        return True
    if "office public" in f or "office hlm" in f:
        return True
    return False


def is_public(gp_lib, forme):
    g = normalize_gp(gp_lib)
    f = normalize_gp(forme)
    if "etablissements publics" in g or u"établissements publics" in g:
        return True
    if "collectivit" in f or "publique" in f or "etat" in g:
        return True
    if "metropole" in normalize_gp(forme) or "commune" in g:
        return True
    return False


def is_sci_or_prive(gp_lib, denomination, forme):
    g = normalize_gp(gp_lib)
    d = normalize_gp(denomination)
    f = normalize_gp(forme)
    if d.startswith("sci ") or d.startswith("scic ") or " sci " in d:
        return True
    if "soci" in f or "sas" in f or "sarl" in f:
        return True
    if "soci" in g and "publics" not in g:
        return True
    return False


def is_pp(gp_lib):
    g = normalize_gp(gp_lib)
    return "personne physique" in g or "personnes physiques" in g


def classify_siren(gp_lib, denomination, forme):
    if is_hlm_social(gp_lib, denomination, forme):
        return "HLM"
    if is_public(gp_lib, forme):
        return "PUBLIC"
    if is_pp(gp_lib):
        return "PP"
    if is_sci_or_prive(gp_lib, denomination, forme):
        return "PRIVE"
    return "AUTRE"


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="POST KV atomique apres affichage")
    args = parser.parse_args()

    # 1. Inputs
    print("=" * 78)
    print("SCAN MAJIC KV UNTAGGED DL")
    print("=" * 78)

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    assigns = kv.get("assignments", {})
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

    print(f"  light adresses     : {len(ad)}")
    print(f"  KV local assigns   : {len(assigns)}")
    print(f"  enrich majic rows  : {len(enrich_by_cle)}")

    # 2. Candidates : exclude FA + already-tagged
    candidates = []
    for a in ad:
        cle = a.get("cle") or ""
        if a.get("_fusion_auto"):
            continue
        t = ((assigns.get(cle) or {}).get("type")) or ""
        if t:
            continue
        candidates.append(a)
    print(f"  candidates total   : {len(candidates)} (exclus FA + deja taggees)")

    # 3. Collect parcelles (from enrich cache when possible)
    needed_parcels = set()
    cle_to_parcels = {}
    for a in candidates:
        cle = a["cle"]
        e = enrich_by_cle.get(cle)
        parcs = (e.get("parcelles_bdnb") if e else None) or []
        cle_to_parcels[cle] = parcs
        for p in parcs:
            needed_parcels.add(p)
    print(f"  parcelles uniques  : {len(needed_parcels)}")

    # 4. MAJIC global query
    sections = sorted({p[8:10] for p in needed_parcels})
    parcel_nums = sorted({int(p[10:]) for p in needed_parcels})
    print(f"  sections MAJIC     : {len(sections)} ({sections[:8]}{'...' if len(sections) > 8 else ''})")
    print(f"  MAJIC parquet query global...")
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", "69"),
        ("code_commune", "=", "383"),
        ("section", "in", sections),
    ])
    df = tbl.to_pandas()
    # Filter to relevant parcelles
    df["_parc"] = ("69383000" + df["section"].astype(str)
                   + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
    df = df[df["_parc"].isin(needed_parcels)].copy()
    # Exclude syndic/mandataire (only Proprietaire + Emphyteote count)
    keep_droits = {"P", "E"}
    df = df[df["code_droit"].isin(keep_droits)].copy()
    print(f"  MAJIC rows utiles  : {len(df)} (code_droit P+E)")

    # 5. Aggregate by parcelle x (siren, code_droit, denomination, gp, forme)
    aggreg = defaultdict(lambda: defaultdict(int))
    meta = {}  # (siren, code_droit) -> meta
    for _, row in df.iterrows():
        parc = row["_parc"]
        sir = str(row["numero_siren"] or "-")
        dr = str(row["code_droit"] or "-")
        gp = str(row["groupe_personne_libelle"] or "")
        dn = str(row["denomination"] or "")
        fj = str(row["forme_juridique_libelle"] or "")
        key = (sir, dr)
        aggreg[parc][key] += 1
        meta[key] = {"gp": gp, "dn": dn, "fj": fj,
                     "class": classify_siren(gp, dn, fj),
                     "droit_lib": str(row["code_droit_libelle"] or "")}

    # 6. Classify each candidate
    rows = []
    for a in candidates:
        cle = a["cle"]
        parcs = cle_to_parcels.get(cle) or []
        bdnb = a.get("nb_log_bdnb") or 0
        vlog = a.get("nb_ventes_logement") or 0
        usage = a.get("usage_principal_bdnb") or ""
        is_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))

        # Aggreger les owners sur l'union des parcelles
        owner_lots = defaultdict(int)
        for p in parcs:
            for k, n in aggreg.get(p, {}).items():
                owner_lots[k] += n
        n_tot = sum(owner_lots.values())

        # Calcul social_pct
        # Regle : si Emphyteote HLM present, social_pct = lots geres par
        # emphyteote HLM / total lots emphyteote (gestion). Sinon
        # social_pct = lots HLM proprietaires / total.
        droits_present = {k[1] for k in owner_lots}
        emphy_lots = sum(n for k, n in owner_lots.items() if k[1] == "E")
        emphy_hlm_lots = sum(n for k, n in owner_lots.items()
                             if k[1] == "E" and meta[k]["class"] == "HLM")
        prop_lots = sum(n for k, n in owner_lots.items() if k[1] == "P")
        prop_hlm_lots = sum(n for k, n in owner_lots.items()
                            if k[1] == "P" and meta[k]["class"] == "HLM")

        if emphy_lots > 0:
            social_lots = emphy_hlm_lots
            denom = emphy_lots
        else:
            social_lots = prop_hlm_lots
            denom = prop_lots if prop_lots > 0 else n_tot
        social_pct = round(social_lots * 100 / denom, 1) if denom else 0.0

        # Top SIREN prive (pour MONO)
        prive_owners = [(k, n) for k, n in owner_lots.items()
                        if meta[k]["class"] in ("PRIVE", "AUTRE", "PP")]
        if prive_owners:
            top_p = max(prive_owners, key=lambda x: x[1])
            # pct relatif aux lots PM uniquement (compatible heuristique
            # MAJIC PM-only)
            top_p_pct = round(top_p[1] * 100 / (prop_lots if prop_lots > 0 else n_tot), 1) if (prop_lots if prop_lots > 0 else n_tot) > 0 else 0
            # pct relatif au parc BDNB (vraie densite : si <80% du parc
            # alors les autres sont en PP -> pas mono)
            top_p_pct_bdnb = round(top_p[1] * 100 / bdnb, 1) if bdnb > 0 else 0
        else:
            top_p = None
            top_p_pct = 0
            top_p_pct_bdnb = 0

        # Top SIREN tous types
        if owner_lots:
            top_all = max(owner_lots.items(), key=lambda x: x[1])
        else:
            top_all = None

        # Classification
        has_emphy_hlm = emphy_hlm_lots > 0
        if usage == "Tertiaire":
            reco = "bureaux"
            reason = "usage_principal_bdnb=Tertiaire"
        elif has_emphy_hlm or social_pct >= 60:
            reco = "social"
            reason = (f"Emphyteote HLM ({emphy_hlm_lots}/{emphy_lots})"
                      if has_emphy_hlm else f"social_pct={social_pct}%")
        elif 20 <= social_pct < 60:
            reco = "mixte"
            reason = f"social_pct={social_pct}%"
        elif top_p and top_p_pct >= 80 and top_p_pct_bdnb >= 80:
            # vrai mono : domine PM ET couvre majorite du parc BDNB
            reco = "mono"
            reason = (f"top SIREN prive {meta[top_p[0]]['dn'][:22]} "
                      f"{top_p_pct}% PM / {top_p_pct_bdnb}% BDNB")
        else:
            reco = "-"
            reason = ""

        # Format top SIREN string
        def fmt_owner(k, n):
            if k is None:
                return "-"
            sir, dr = k
            m = meta[k]
            return f"{sir} {dr} {m['dn'][:22]}({n}/{m['class']})"

        rows.append({
            "cle": cle,
            "bdnb": bdnb,
            "vlog": vlog,
            "usage": usage,
            "is_rnc": is_rnc,
            "immat": (co_by_cle.get(cle) or {}).get("numero_immatriculation")
                       or a.get("numero_immatriculation"),
            "majic_lots_tot": n_tot,
            "social_pct": social_pct,
            "emphy_hlm_lots": emphy_hlm_lots,
            "emphy_lots": emphy_lots,
            "prop_hlm_lots": prop_hlm_lots,
            "prop_lots": prop_lots,
            "top_all": fmt_owner(top_all[0], top_all[1]) if top_all else "-",
            "top_prive": fmt_owner(top_p[0], top_p[1]) if top_p else "-",
            "top_prive_pct": top_p_pct,
            "top_prive_pct_bdnb": top_p_pct_bdnb,
            "reco": reco,
            "reason": reason,
            "has_emphy_hlm": has_emphy_hlm,
        })

    rows.sort(key=lambda r: -r["bdnb"])

    # 7. Resumes
    from collections import Counter
    ct = Counter(r["reco"] for r in rows)
    print()
    print(f"  Classification : {dict(ct)}")
    print()
    # Filtrer pour affichage : ne montrer que ceux avec recommandation
    proposed = [r for r in rows if r["reco"] != "-"]
    skipped = [r for r in rows if r["reco"] == "-"]
    print(f"  Avec recommandation tag KV : {len(proposed)}")
    print(f"  Sans recommandation (skip) : {len(skipped)}")
    print()

    # 8. Tableau pre-patch
    print("=" * 156)
    print("TABLEAU PRE-PATCH - tri nb_log_bdnb DESC (recommandations uniquement)")
    print("=" * 156)
    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'usage':22s} "
          f"{'RNC':3s} {'lots':>5} {'soc%':>6} {'reco':8s} {'top owner':54s} {'reason'}")
    print("  " + "-" * 154)
    for i, r in enumerate(proposed, 1):
        print(f"  {i:>3} {r['cle']:32s} {r['bdnb']:>6} {r['usage']:22s} "
              f"{'oui' if r['is_rnc'] else 'non':3s} {r['majic_lots_tot']:>5} "
              f"{r['social_pct']:>5.1f}% {r['reco']:8s} {r['top_all']:54s} {r['reason']}")

    # 9. Apply ? Non par defaut.
    if not args.apply:
        print()
        print("=" * 78)
        print(f"DRY RUN. Lance --apply apres validation pour POST KV atomique.")
        print(f"Recos : social={ct.get('social',0)}  mixte={ct.get('mixte',0)}  "
              f"mono={ct.get('mono',0)}  bureaux={ct.get('bureaux',0)}")
        print("=" * 78)
        return

    # --- APPLY ---
    if not JWT:
        sys.exit("  [abort] env var DPE_JWT absente (requise pour --apply).")
    print()
    print("=" * 78)
    print("MODE --apply : POST KV atomique")
    print("=" * 78)
    headers = {
        "Authorization": f"Bearer {JWT}",
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # GET current
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               headers={k: v for k, v in headers.items() if k != "Content-Type"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    assigns_cloud = body.get("assignments") or {}
    fusions_cloud = body.get("fusions") or {}
    noms_cloud = body.get("noms") or {}
    print(f"  [GET] assigns={len(assigns_cloud)} fusions={len(fusions_cloud)}")

    n_changes = 0
    for r in proposed:
        prev = assigns_cloud.get(r["cle"])
        prev_t = (prev or {}).get("type")
        if prev_t == r["reco"]:
            continue
        assigns_cloud[r["cle"]] = {"type": r["reco"]}
        n_changes += 1
    print(f"  [diff] {n_changes} changes")

    if n_changes == 0:
        print("  [skip] rien a appliquer")
        return

    data = json.dumps({"assignments": assigns_cloud,
                       "fusions": fusions_cloud,
                       "noms": noms_cloud}).encode("utf-8")
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            print(f"  [POST] status={resp.status} body={json.loads(resp.read())}")
    except urllib.error.HTTPError as e:
        sys.exit(f"  POST err: {e.code} {e.read().decode('utf-8','replace')}")

    # Re-GET verif
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               headers={k: v for k, v in headers.items() if k != "Content-Type"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    a2 = body.get("assignments") or {}
    fails = 0
    for r in proposed:
        v = a2.get(r["cle"])
        if not v or v.get("type") != r["reco"]:
            print(f"  [FAIL] {r['cle']:34s} got {v} (expected {r['reco']})")
            fails += 1
    print(f"  [verif] {len(proposed)-fails}/{len(proposed)} OK ; {fails} FAIL")

    # Maj cache local
    kv["assignments"] = assigns_cloud
    KV_LOCAL.write_text(json.dumps(kv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [local] {KV_LOCAL.name} mis a jour ({len(assigns_cloud)} assignments)")


if __name__ == "__main__":
    main()
