#!/usr/bin/env python3
"""Verif impact reclass social->mixte/copro_non_immat sur les 2 compteurs.

LECTURE SEULE. Compare AVANT (les 27 cles taggees 'social') / APRES
(reclassees) pour :
  1. sctGenComputeIlots ventes/an (= compteur repartition conseillers)
  2. secteurRender ventes/an (= compteur global dashboard)

+ Confirmation : la divergence des deux compteurs (option A non
appliquee) persiste.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"

ANS = ("2021", "2022", "2023", "2024", "2025")


def vpa(a):
    return a.get("ventes_par_an_logement") or {}


def main():
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}

    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    assigns = kv.get("assignments") or {}
    fusions_kv = kv.get("fusions") or {}

    # ---------- Lire le overrides file pour identifier les 27 cles ----------
    if OVERRIDES.exists():
        ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cles_reclass = {o["cle"]: o for o in ov.get("overrides", [])}
        print(f"  Overrides loaded : {len(cles_reclass)} cles")
    else:
        print("  [warn] _social_overrides_dl.json absent ; tentative auto-detection")
        cles_reclass = {}

    # ---------- Verifier etat actuel des 27 cles dans KV ----------
    print()
    print("=" * 78)
    print("ETAT ACTUEL KV LOCAL (apres apply)")
    print("=" * 78)
    if cles_reclass:
        print(f"\n  Verif tag courant des {len(cles_reclass)} cles overrides :")
        cnt_actuel = Counter()
        for cle in cles_reclass:
            cur = (assigns.get(cle) or {}).get("type", "(vide)")
            cnt_actuel[cur] += 1
        for tag, n in cnt_actuel.most_common():
            print(f"    {tag:20s} : {n}")
        already_applied = all(
            (assigns.get(c) or {}).get("type") in ("mixte", "copro_non_immat")
            for c in cles_reclass
        )
        print(f"\n  Reclass apply effectif ? : {already_applied}")
    else:
        already_applied = False
        # Fallback : detection cles qui ont _qualif_source='dvf_decollect'
        cles_reclass = {
            cle: v for cle, v in assigns.items()
            if (v or {}).get("_qualif_source") == "dvf_decollect"
        }
        print(f"  Detection auto (via _qualif_source) : {len(cles_reclass)} cles")
        if cles_reclass:
            already_applied = True

    if not cles_reclass:
        print("\n  [abort] aucune cle reclassee identifiee. Apply pas fait ?")
        return

    # ---------- Helpers ----------
    def kv_type_avec_override(cle, mode_avant):
        """Retourne le tag selon le mode :
           - 'avant' : si cle in cles_reclass, force 'social' (etat pre-reclass)
           - 'apres' : etat KV actuel (= apres apply)"""
        if mode_avant and cle in cles_reclass:
            return "social"
        return ((assigns.get(cle) or {}).get("type")) or ""

    def kv_ilot(cle):
        v = (assigns.get(cle) or {}).get("ilot")
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def ilot_effectif(a):
        cle = a.get("cle") or ""
        ki = kv_ilot(cle)
        if ki is not None:
            return ki
        v = a.get("_ilot")
        if v is not None and v != "X":
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        return None

    # ---------- Calcul autoMerged + mergedInto + fusedSrc (commun) ----------
    merged_into = {}
    fused_src = set()
    for src, dst in fusions_kv.items():
        sa = by_cle.get(src)
        if not sa or not dst or src == dst:
            continue
        fused_src.add(src)
        m = merged_into.setdefault(dst, {"ventes": {}})
        for y in ANS:
            m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)
    auto_merged = {}
    for a in ad:
        cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
        cle = a.get("cle") or ""
        if a.get("_fusion_auto") and cible and cle not in fused_src:
            fused_src.add(cle)
            am = auto_merged.setdefault(cible, {"ventes": {}})
            for y in ANS:
                am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

    # ---------- sctGen sumVpa ----------
    def sumVpa(a):
        if a.get("ventes_par_an_logement"):
            if isinstance(a.get("nb_ventes_logement"), int):
                return a.get("nb_ventes_logement")
            return sum((a["ventes_par_an_logement"].get(y) or 0) for y in ANS)
        if isinstance(a.get("nb_ventes_total"), int):
            return a.get("nb_ventes_total")
        return 0

    # ---------- secteurRender (compteur GLOBAL) ----------
    def compute_secAllV(mode):
        total = 0
        for a in ad:
            cle = a.get("cle") or ""
            if cle in fused_src:
                continue
            # Note : secteurRender NE FILTRE PAS par tag par defaut.
            # Donc le reclass social->mixte ne change RIEN ici (sauf via
            # mergedInto/autoMerged si l'adresse FA-source change de tag,
            # ce qui n'est pas le cas ici).
            own = sum((vpa(a).get(y) or 0) for y in ANS)
            mi = sum((merged_into.get(cle, {}).get("ventes", {}).get(y) or 0)
                      for y in ANS)
            am = sum((auto_merged.get(cle, {}).get("ventes", {}).get(y) or 0)
                      for y in ANS)
            total += own + mi + am
        return total

    # ---------- sctGen (compteur REPARTITION) ----------
    def compute_sct(mode):
        total = 0
        for a in ad:
            cle = a.get("cle") or ""
            iid = ilot_effectif(a)
            if iid is None or a.get("_ilot") == "X":
                continue
            tg = kv_type_avec_override(cle, mode_avant=(mode == "avant"))
            if tg in ("social", "bureaux"):
                continue
            total += sumVpa(a)
        return total

    sec_avant = compute_secAllV("avant")
    sec_apres = compute_secAllV("apres")
    sct_avant = compute_sct("avant")
    sct_apres = compute_sct("apres")

    # ---------- Ventes propres des 27 cles ----------
    ventes_27_5ans = sum(
        sumVpa(by_cle.get(c, {})) for c in cles_reclass
    )
    ventes_27_an = ventes_27_5ans / 5

    # ---------- Affichage ----------
    print()
    print("=" * 78)
    print("Q1+Q2 : Impact reclass social -> mixte/copro_non_immat")
    print("=" * 78)
    print()
    print("  Rappel logique :")
    print("    sctGen      : EXCLUT 'social' et 'bureaux' (autres tags INCLUS)")
    print("    secteurRender : N'EXCLUT PAS par tag (au defaut)")
    print()
    print("  Reclass social -> mixte/copro_non_immat :")
    print("    - sctGen : les 27 cles passent de EXCLUES -> INCLUSES")
    print("               -> +ventes des 27 dans le compteur repartition")
    print("    - secteurRender : pas de filtre tag, donc INCHANGE")
    print()
    print("  Ventes propres cumulees des 27 cles :")
    print(f"    5 ans : {ventes_27_5ans}")
    print(f"    /an   : {ventes_27_an:.1f}")
    print()
    print("=" * 78)
    print("Q3 : CHIFFRES AVANT / APRES RECLASSEMENT (DL)")
    print("=" * 78)
    print()
    print(f"  {'Compteur':40s} {'AVANT 5ans':>11} {'APRES 5ans':>11} "
          f"{'AVANT /an':>10} {'APRES /an':>10} {'Delta /an':>11}")
    print("  " + "-" * 105)
    print(f"  {'[A] secteurRender (compteur global)':40s} {sec_avant:>11} "
          f"{sec_apres:>11} {sec_avant/5:>9.1f} {sec_apres/5:>9.1f} "
          f"{(sec_apres - sec_avant)/5:>+10.1f}")
    print(f"  {'[B] sctGenComputeIlots (repartition)':40s} {sct_avant:>11} "
          f"{sct_apres:>11} {sct_avant/5:>9.1f} {sct_apres/5:>9.1f} "
          f"{(sct_apres - sct_avant)/5:>+10.1f}")
    print(f"  {'[A] - [B]':40s} {sec_avant - sct_avant:>11} "
          f"{sec_apres - sct_apres:>11} "
          f"{(sec_avant - sct_avant)/5:>9.1f} "
          f"{(sec_apres - sct_apres)/5:>9.1f}")
    print()
    print("  Interpretation :")
    print(f"    - secteurRender stable : {sec_avant/5:.1f} -> {sec_apres/5:.1f} "
          f"(delta {(sec_apres-sec_avant)/5:+.1f}/an)")
    print(f"    - sctGen augmente      : {sct_avant/5:.1f} -> {sct_apres/5:.1f} "
          f"(delta {(sct_apres-sct_avant)/5:+.1f}/an)")
    gap_avant = (sec_avant - sct_avant) / 5
    gap_apres = (sec_apres - sct_apres) / 5
    print(f"    - Gap divergence : {gap_avant:.1f}/an -> {gap_apres:.1f}/an "
          f"(reduction de {gap_avant - gap_apres:+.1f}/an)")
    print()
    print(f"  Verification arithmetique :")
    print(f"    ventes 27 cles /an = {ventes_27_an:.1f}")
    print(f"    delta sctGen /an   = {(sct_apres - sct_avant)/5:+.1f}")
    delta_sctgen = (sct_apres - sct_avant) / 5
    if abs(delta_sctgen - ventes_27_an) < 0.5:
        print(f"    -> match (delta sctGen = ventes 27 cles)")
    else:
        print(f"    -> ECART : difference {delta_sctgen - ventes_27_an:+.1f}")
        print(f"       (peut venir de cles avec ilot=null/X ou autres filtres)")
    print()

    # ---------- Top contributeurs ----------
    print("=" * 78)
    print("Top 10 cles reclassees par ventes propres /an")
    print("=" * 78)
    contrib = []
    for cle in cles_reclass:
        a = by_cle.get(cle, {})
        v5 = sumVpa(a)
        ovd = cles_reclass[cle] if isinstance(cles_reclass[cle], dict) else {}
        contrib.append({
            "cle": cle, "v5": v5, "van": v5 / 5,
            "new_tag": ovd.get("new_tag") or
                       ((assigns.get(cle) or {}).get("type")),
            "mut_per_year": ovd.get("mut_apt_per_year"),
        })
    contrib.sort(key=lambda r: -r["van"])
    print(f"\n  {'#':>3} {'cle':32s} {'tag':16s} {'v5':>4} {'v/an':>6} {'mut/an (parcel)':>15}")
    print("  " + "-" * 80)
    for i, r in enumerate(contrib[:10], 1):
        mut = f"{r['mut_per_year']:.2f}" if r["mut_per_year"] is not None else "-"
        print(f"  {i:>3} {r['cle']:32s} {r['new_tag']:16s} {r['v5']:>4} "
              f"{r['van']:>5.1f} {mut:>15}")

    # ---------- Q4 confirmation unification ----------
    print()
    print("=" * 78)
    print("Q4 - CONFIRMATION UNIFICATION FILTRES (option A pas appliquee)")
    print("=" * 78)
    print()
    print("  Verifier dans index.html que les 2 fonctions NE sont PAS")
    print("  encore unifiees avec PROSPECTABLE_EXCLUDED partage :")
    idx = ROOT / "index.html"
    src = idx.read_text(encoding="utf-8")
    has_const = "PROSPECTABLE_EXCLUDED" in src
    print(f"    'PROSPECTABLE_EXCLUDED' dans index.html : {has_const}")
    if has_const:
        print("    -> UNIFICATION APPLIQUEE")
    else:
        print("    -> UNIFICATION NON APPLIQUEE : les 2 compteurs gardent")
        print("       leur logique divergente (filtre par tag de TARGET pour")
        print("       render vs filtre par tag de SOURCE pour sctGen).")
        print("    -> Cohrent avec ce que tu as decide : on a interrompu le")
        print("       chantier sur Charial avant unification.")


if __name__ == "__main__":
    main()
