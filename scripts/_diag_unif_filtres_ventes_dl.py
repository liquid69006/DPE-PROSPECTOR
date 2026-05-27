#!/usr/bin/env python3
"""Cartographie + dry-run unification filtres ventes/an DL (lecture seule).

ETAPE 1 - Code exact des 2 filtres (secteurRender vs sctGenComputeIlots)
ETAPE 2 - Tableau par tag KV : inclus/exclus dans chaque compteur
ETAPE 3 - DRY-RUN unification : si PROSPECTABLE_EXCLUDED_TAGS = ['social',
          'bureaux'] applique aux deux, sont-ils strictement egaux ?
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ANS = ("2021", "2022", "2023", "2024", "2025")


def main():
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    assigns = kv.get("assignments") or {}
    fusions_kv = kv.get("fusions") or {}

    def kv_type(cle):
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
        ilot_kv_v = kv_ilot(cle)
        if ilot_kv_v is not None:
            return ilot_kv_v
        v = a.get("_ilot")
        if v is not None and v != "X":
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        return None

    def vpa(a):
        return a.get("ventes_par_an_logement") or {}

    # ---- merged_into + auto_merged + fused_src ----
    merged_into = {}
    fused_src = set()
    for src, dst in fusions_kv.items():
        sa = by_cle.get(src)
        if not sa or not dst or src == dst:
            continue
        fused_src.add(src)
        m = merged_into.setdefault(dst, {"ventes": {}, "srcs": []})
        m["srcs"].append(src)
        for y in ANS:
            m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

    auto_merged = {}
    auto_src_tags = {}  # target -> list of (src_cle, src_tag, src_ventes_5ans)
    for a in ad:
        cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
        cle = a.get("cle") or ""
        if a.get("_fusion_auto") and cible and cle not in fused_src:
            fused_src.add(cle)
            am = auto_merged.setdefault(cible, {"ventes": {}, "srcs": []})
            am["srcs"].append(cle)
            ven = sum((vpa(a).get(y) or 0) for y in ANS)
            auto_src_tags.setdefault(cible, []).append((cle, kv_type(cle), ven))
            for y in ANS:
                am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

    # ============================================================
    # ETAPE 1 - Cartographie des 2 filtres (code exact JS reproduit)
    # ============================================================
    print("=" * 78)
    print("ETAPE 1 - Cartographie code exact des 2 filtres")
    print("=" * 78)

    print("\n[1.A] secteurRender (compteur GLOBAL, ligne 5232 secAllV)")
    print("      Filtres adresses (ligne 4897 onwards) :")
    print("        if (fusedSrc[a.cle]) return;          // FA + KV fusions src")
    print("        if (secteurNoLog) { ... } [UI toggle, OFF par defaut]")
    print("        if (secteurHrActif) { ... } [UI toggle, OFF par defaut]")
    print("        if (secteurMono) { ... } [UI toggle, OFF par defaut]")
    print("        if (secteurCoproNI) { ... } [UI toggle, OFF par defaut]")
    print("        if (secteurMixte) { ... } [UI toggle, OFF par defaut]")
    print("        if (secteurAQualif) { ... } [UI toggle, OFF par defaut]")
    print("        if (filterSansVentes) { ... } [UI toggle, OFF par defaut]")
    print("      -> A l'etat defaut (aucun toggle) : SEUL fusedSrc est exclu")
    print("      Cumul effV (l.5011) :")
    print("        effV[y] = vpaOf(a)[y] + mergedInto[a.cle].ventes[y]")
    print("                 + autoMerged[a.cle].ventes[y]")
    print("      iloAllV += effTot (l.5033)")
    print("      secAllV += iloAllV (l.5232)")
    print("      secVAn = secAllV / 5 (l.5261)")

    print("\n[1.B] sctGenComputeIlots (compteur REPARTITION, ligne 2606)")
    print("      Filtres adresses (ligne 2637 onwards) :")
    print("        const iid = ilotEffectif(a);")
    print("        if (iid == null) continue;            // sans ilot")
    print("        if (a._ilot === 'X') continue;         // hors secteur")
    print("        const tg = (secteurAssign[a.cle] || {}).type;")
    print("        if (tg !== 'social' && tg !== 'bureaux') {")
    print("            o.nb_ventes += sumVpa(a);")
    print("        }")
    print("      -> EXCLU systematique : social, bureaux, ilot=null, _ilot='X'")
    print("      Cumul nb_ventes = own sumVpa(a) UNIQUEMENT (pas mergedInto/autoMerged)")
    print("      (les FA-sources sont processees a leur propre ilot)")

    # ============================================================
    # ETAPE 2 - Tableau par tag KV : inclus/exclus
    # ============================================================
    print()
    print("=" * 78)
    print("ETAPE 2 - Tableau comparatif par tag KV (etat actuel DL)")
    print("=" * 78)

    # Stats par tag : nb adresses, nb adresses contribuant > 0, ventes contribuees
    tag_stats = {}  # tag -> {n_adr, n_ventes, ventes_5ans}
    all_tags = ("social", "bureaux", "mono", "mixte", "copro_non_immat",
                "cible_0vente_active", "cible_0vente_isolee", "(vide)")

    for tag_clean in all_tags:
        tag_stats[tag_clean] = {"n_adr": 0, "n_ventes": 0,
                                 "v_render_own": 0,
                                 "v_render_via_autoMerged": 0,
                                 "v_sctgen_own": 0,
                                 "incl_render": True, "incl_sctgen": True}

    for a in ad:
        cle = a.get("cle") or ""
        tag = kv_type(cle)
        tag_clean = tag if tag in ("social", "bureaux", "mono", "mixte",
                                    "copro_non_immat", "cible_0vente_active",
                                    "cible_0vente_isolee") else "(vide)"
        ts = tag_stats[tag_clean]
        ts["n_adr"] += 1
        own_v = sum((vpa(a).get(y) or 0) for y in ANS)
        if own_v > 0:
            ts["n_ventes"] += 1
        ts["v_render_own"] += own_v if cle not in fused_src else 0
        # Render via autoMerged : si CET adresse est target, ventes des
        # FA-source contribuent (peu importe leur tag a elles)
        ts["v_render_via_autoMerged"] += sum(
            (auto_merged.get(cle, {}).get("ventes", {}).get(y) or 0)
            for y in ANS) if cle not in fused_src else 0
        # sctGen : si ilot OK et pas social/bureaux, on compte own_v
        iid = ilot_effectif(a)
        if iid is not None and a.get("_ilot") != "X" and tag not in ("social",
                                                                     "bureaux"):
            ts["v_sctgen_own"] += own_v

    # Calcul inclus/exclus
    for tag_clean, ts in tag_stats.items():
        ts["incl_render"] = True  # tag tags inclus dans render par defaut
        ts["incl_sctgen"] = tag_clean not in ("social", "bureaux")

    print(f"\n  {'Tag KV':25s} {'n_adr':>6} {'n_ventes':>8} "
          f"{'render':>8} {'sctgen':>8} {'v render (5ans)':>16} "
          f"{'v sctgen (5ans)':>16}")
    print("  " + "-" * 96)
    total_render = 0
    total_sctgen = 0
    for tag_clean in all_tags:
        ts = tag_stats[tag_clean]
        incl_r = "OUI" if ts["incl_render"] else "non"
        incl_s = "OUI" if ts["incl_sctgen"] else "non"
        v_r = ts["v_render_own"] + ts["v_render_via_autoMerged"]
        v_s = ts["v_sctgen_own"]
        total_render += v_r
        total_sctgen += v_s
        print(f"  {tag_clean:25s} {ts['n_adr']:>6} {ts['n_ventes']:>8} "
              f"{incl_r:>8} {incl_s:>8} {v_r:>16} {v_s:>16}")
    print("  " + "-" * 96)
    print(f"  {'TOTAL':25s} {'':>6} {'':>8} {'':>8} {'':>8} "
          f"{total_render:>16} {total_sctgen:>16}")

    # ============================================================
    # ETAPE 3 - DRY-RUN unification PROSPECTABLE_EXCLUDED_TAGS=['social','bureaux']
    # ============================================================
    print()
    print("=" * 78)
    print("ETAPE 3 - DRY-RUN unification (PROSPECTABLE_EXCLUDED_TAGS)")
    print("=" * 78)
    print("  Proposition : ajouter dans secteurRender (avant ligne 4897) :")
    print("    const PROSPECTABLE_EXCLUDED = new Set(['social', 'bureaux']);")
    print("    if (PROSPECTABLE_EXCLUDED.has(secteurAssign[a.cle]?.type)) return;")
    print("  Et reutiliser exactement la meme constante dans sctGenComputeIlots.")

    EXCL = {"social", "bureaux"}

    # AVANT (etat actuel)
    secAllV_before = 0
    for a in ad:
        cle = a.get("cle") or ""
        if cle in fused_src:
            continue
        own = sum((vpa(a).get(y) or 0) for y in ANS)
        mi = sum((merged_into.get(cle, {}).get("ventes", {}).get(y) or 0)
                  for y in ANS)
        am = sum((auto_merged.get(cle, {}).get("ventes", {}).get(y) or 0)
                  for y in ANS)
        secAllV_before += own + mi + am

    sct_total_before = 0
    for a in ad:
        cle = a.get("cle") or ""
        iid = ilot_effectif(a)
        if iid is None or a.get("_ilot") == "X":
            continue
        if kv_type(cle) in EXCL:
            continue
        sct_total_before += sum((vpa(a).get(y) or 0) for y in ANS)

    # APRES (filtre unifie applique aux 2)
    # Dans secteurRender APRES : on exclut les target dont tag in EXCL
    # ET aussi on doit exclure les FA-source contribuant via autoMerged
    # si leur tag a EUX est EXCL (sinon discrepance)
    # On reconstruit auto_merged et merged_into en excluant les sources EXCL
    auto_merged_purged = {}
    for a in ad:
        cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
        cle = a.get("cle") or ""
        if a.get("_fusion_auto") and cible:
            # IF cible has tag EXCL : on n'aggrege rien (target sera filtre)
            # IF source has tag EXCL : on n'aggrege pas (sinon double compte ?)
            if kv_type(cle) in EXCL:
                continue
            if kv_type(cible) in EXCL:
                continue
            am = auto_merged_purged.setdefault(cible, {"ventes": {}})
            for y in ANS:
                am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

    merged_into_purged = {}
    for src, dst in fusions_kv.items():
        sa = by_cle.get(src)
        if not sa or not dst or src == dst:
            continue
        if kv_type(src) in EXCL:
            continue
        if kv_type(dst) in EXCL:
            continue
        m = merged_into_purged.setdefault(dst, {"ventes": {}})
        for y in ANS:
            m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

    # secAllV APRES
    secAllV_after = 0
    for a in ad:
        cle = a.get("cle") or ""
        if cle in fused_src:
            continue
        if kv_type(cle) in EXCL:
            continue
        own = sum((vpa(a).get(y) or 0) for y in ANS)
        mi = sum((merged_into_purged.get(cle, {}).get("ventes", {}).get(y) or 0)
                  for y in ANS)
        am = sum((auto_merged_purged.get(cle, {}).get("ventes", {}).get(y) or 0)
                  for y in ANS)
        secAllV_after += own + mi + am

    # sctGen APRES = identique au BEFORE (deja excluant social/bureaux)
    sct_total_after = sct_total_before

    print(f"\n  {'Compteur':38s} {'AVANT':>10} {'APRES':>10}")
    print("  " + "-" * 60)
    print(f"  {'[A] GLOBAL secteurRender (5 ans)':38s} "
          f"{secAllV_before:>10} {secAllV_after:>10}")
    print(f"  {'[B] sctGenComputeIlots (5 ans)':38s} "
          f"{sct_total_before:>10} {sct_total_after:>10}")
    print(f"  {'[B] - [A]':38s} "
          f"{sct_total_before - secAllV_before:>+10} "
          f"{sct_total_after - secAllV_after:>+10}")
    print(f"  {'[A] / 5 (ventes/an)':38s} "
          f"{round(secAllV_before / 5, 1):>10} "
          f"{round(secAllV_after / 5, 1):>10}")
    print(f"  {'[B] / 5 (ventes/an)':38s} "
          f"{round(sct_total_before / 5, 1):>10} "
          f"{round(sct_total_after / 5, 1):>10}")

    delta_after = secAllV_after - sct_total_after
    print(f"\n  DELTA APRES : {delta_after} (5 ans) = "
          f"{round(delta_after / 5, 1)}/an")
    if delta_after == 0:
        print(f"  -> APRES strictement egaux. Unification possible.")
    else:
        print(f"  -> APRES NON egaux. NE PAS patcher avant d'expliquer le delta.")

    # ============================================================
    # ETAPE 3b - Verification FA-sources tag social/bureaux
    # ============================================================
    print()
    print("[3b] Verification : FA-sources avec tag social/bureaux ?")
    fa_src_excl = 0
    fa_src_excl_ventes = 0
    for a in ad:
        if not a.get("_fusion_auto"):
            continue
        cle = a.get("cle") or ""
        if kv_type(cle) in EXCL:
            fa_src_excl += 1
            fa_src_excl_ventes += sum((vpa(a).get(y) or 0) for y in ANS)
    print(f"  FA-sources avec tag social/bureaux : {fa_src_excl} (ventes 5-ans : {fa_src_excl_ventes})")

    # Targets tag social/bureaux qui recoivent du autoMerged
    targets_excl_with_am = 0
    targets_excl_am_ventes = 0
    for cible, am in auto_merged.items():
        if kv_type(cible) in EXCL:
            v = sum(am["ventes"].values())
            if v > 0:
                targets_excl_with_am += 1
                targets_excl_am_ventes += v
    print(f"  Targets tag social/bureaux recevant autoMerged : "
          f"{targets_excl_with_am} (ventes 5-ans : {targets_excl_am_ventes})")


if __name__ == "__main__":
    main()
