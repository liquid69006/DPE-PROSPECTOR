#!/usr/bin/env python3
"""Reconciliation exacte entre 2 compteurs DL (lecture seule).

CONTEXTE : dashboard secteur affiche ~597.8 ventes/an au global. La
repartition sctGen sur 10 secteurs donne ~56.6 ventes/an de moyenne
soit ~566 ventes/an. Ecart ~31 ventes/an a expliquer.

Reproduit EXACTEMENT les 2 algos cote JS :

  [A] GLOBAL (index.html ~ligne 5012 + 5261)
      secAllV / 5
      effV[y] = vpaOf(a)[y]                    (own)
              + mergedInto[a.cle][y]            (KV manual fusions)
              + autoMerged[a.cle][y]            (BDNB FA -> ancre)
      somme sur tous a NON fusedSrc (a._fusion_auto + KV fusions src)
      tag KV social/bureaux/mono : INCLUS (header ne filtre pas)

  [B] sctGen (index.html ~ligne 2606)
      sumVpa(a) = nb_ventes_logement OR nb_ventes_total OR somme vpa
      pour chaque a :
        if ilotEffectif(a) == null : SKIP
        if a._ilot === 'X' : SKIP
        if tag == 'social' or 'bureaux' : SKIP (ventes exclues mais
          adresse comptee dans byIlot.adresses)
      somme = somme des nb_ventes par ilot

Diff = (A) - (B). Identifie les adresses qui contribuent au delta.
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
ANS = ("2021", "2022", "2023", "2024", "2025")


def main():
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c
                 for c in doc["coproprietes"]}
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
        """ Replique JS ilotEffectif (index.html ~l 4805) """
        cle = a.get("cle") or ""
        ilot_kv = kv_ilot(cle)
        if ilot_kv is not None:
            return ilot_kv
        v = a.get("_ilot")
        if v is not None and v != "X":
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        return None

    # vpaOf strict (replique JS l. 4740 - secteurStrict==True hypothesise)
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

    # ============================================================
    # [A] secteurRender global secAllV
    # ============================================================
    print("=" * 78)
    print("RECONCILIATION COMPTEURS DL  (lecture seule)")
    print("=" * 78)

    secAllV = 0
    contribA = []  # adresses contribuant au global, avec leur effV total
    for a in ad:
        cle = a.get("cle") or ""
        if cle in fused_src:
            continue  # FA-sources skipped en render
        own_vpa = vpa(a)
        mi = merged_into.get(cle, {"ventes": {}})
        am = auto_merged.get(cle, {"ventes": {}})
        effTot = 0
        for y in ANS:
            effTot += (own_vpa.get(y) or 0)
            effTot += (mi["ventes"].get(y) or 0)
            effTot += (am["ventes"].get(y) or 0)
        if effTot > 0:
            contribA.append({"cle": cle, "eff": effTot,
                              "own": sum(own_vpa.values()),
                              "mi": sum(mi["ventes"].values()),
                              "am": sum(am["ventes"].values()),
                              "tag": kv_type(cle),
                              "ilot_eff": ilot_effectif(a),
                              "ilotX": a.get("_ilot") == "X",
                              "is_rnc": (cle in co_by_cle) or bool(a.get("numero_immatriculation"))})
        secAllV += effTot

    secVAn = secAllV / 5.0
    print(f"\n[A] GLOBAL (secteurRender header)")
    print(f"    Source       : ventes_par_an_logement (strict) + mergedInto + autoMerged")
    print(f"    Population   : toutes adresses NON fusedSrc")
    print(f"    Inclut tags  : ALL (social/bureaux/mono inclus)")
    print(f"    Total 5 ans  : {secAllV}")
    print(f"    Ventes/an    : {round(secVAn, 1)}")

    # ============================================================
    # [B] sctGenComputeIlots
    # ============================================================
    print(f"\n[B] sctGen (sctGenComputeIlots)")
    # Same useStrict = True : ventes_par_an_logement existe
    def sumVpa(a):
        if a.get("ventes_par_an_logement"):
            if isinstance(a.get("nb_ventes_logement"), int):
                return a.get("nb_ventes_logement")
            return sum((a["ventes_par_an_logement"].get(y) or 0) for y in ANS)
        if isinstance(a.get("nb_ventes_total"), int):
            return a.get("nb_ventes_total")
        if a.get("ventes_par_an"):
            return sum((a["ventes_par_an"].get(y) or 0) for y in ANS)
        return 0

    by_ilot = defaultdict(int)
    sct_total = 0
    excl_ilot_null = []
    excl_ilotX = []
    excl_social_bureaux = []
    included = []
    for a in ad:
        cle = a.get("cle") or ""
        iid = ilot_effectif(a)
        if iid is None:
            v = sumVpa(a)
            if v > 0:
                excl_ilot_null.append({"cle": cle, "v": v,
                                        "tag": kv_type(cle)})
            continue
        if a.get("_ilot") == "X":
            v = sumVpa(a)
            if v > 0:
                excl_ilotX.append({"cle": cle, "v": v,
                                    "tag": kv_type(cle)})
            continue
        tag = kv_type(cle)
        v = sumVpa(a)
        if tag in ("social", "bureaux"):
            if v > 0:
                excl_social_bureaux.append({"cle": cle, "v": v, "tag": tag,
                                             "ilot": iid})
            continue
        by_ilot[iid] += v
        sct_total += v
        if v > 0:
            included.append({"cle": cle, "v": v, "ilot": iid, "tag": tag})

    sct_van = sct_total / 5.0
    print(f"    Source       : sumVpa(a) = own ventes_par_an_logement")
    print(f"    Population   : adresses avec ilot != null, != 'X', tag != social/bureaux")
    print(f"    EXCLUT       : social, bureaux, sans ilot, ilot='X'")
    print(f"    NE INCLUT PAS: mergedInto, autoMerged (= sources comptees a leur propre ilot)")
    print(f"    Total 5 ans  : {sct_total}")
    print(f"    Ventes/an    : {round(sct_van, 1)}")
    print(f"    Nb ilots     : {len(by_ilot)}")

    # ============================================================
    # [C] DIFF
    # ============================================================
    print(f"\n[C] DELTA")
    print(f"    secAllV - sct_total = {secAllV} - {sct_total} = {secAllV - sct_total}")
    print(f"    (en ventes/an)       = {round((secAllV - sct_total) / 5, 1)}")

    # Breakdown delta :
    # - secteurRender INCLUT autoMerged ; sctGen NE l'inclut PAS sur le target
    #   MAIS la source FA n'est pas comptee dans secteurRender (fused_src) et
    #   EST comptee dans sctGen (via son propre ilot).
    #   -> equivalent IF source.ilot != null et != X et tag != social/bureaux
    # - Idem mergedInto vs KV fusions src

    # Calcul rigoureux : adresses dont les ventes sont dans (A) mais pas dans (B)
    total_excl_social_bureaux = sum(x["v"] for x in excl_social_bureaux)
    total_excl_ilot_null = sum(x["v"] for x in excl_ilot_null)
    total_excl_ilotX = sum(x["v"] for x in excl_ilotX)

    # Pour FA-sources et KV-src (skipped dans A car fused_src), elles sont
    # processed dans B normalement -> equivalent SAUF si elles tombent dans
    # une exclusion B (social/bureaux/no-ilot/X).
    excl_fused_no_render = []
    for a in ad:
        cle = a.get("cle") or ""
        if cle not in fused_src:
            continue
        v = sumVpa(a)
        if v <= 0:
            continue
        tag = kv_type(cle)
        iid = ilot_effectif(a)
        in_B = (iid is not None and a.get("_ilot") != "X"
                and tag not in ("social", "bureaux"))
        if not in_B:
            excl_fused_no_render.append({"cle": cle, "v": v, "tag": tag,
                                          "ilot": iid,
                                          "ilotX": a.get("_ilot") == "X"})

    print(f"\n[D] BREAKDOWN DELTA (5 ans)")
    print(f"    Exclus sctGen pour 'social/bureaux'      : {len(excl_social_bureaux):>4} adresses, {total_excl_social_bureaux:>4} ventes 5-ans")
    print(f"    Exclus sctGen pour ilot == null          : {len(excl_ilot_null):>4} adresses, {total_excl_ilot_null:>4} ventes 5-ans")
    print(f"    Exclus sctGen pour _ilot == 'X'          : {len(excl_ilotX):>4} adresses, {total_excl_ilotX:>4} ventes 5-ans")
    total_explained = total_excl_social_bureaux + total_excl_ilot_null + total_excl_ilotX
    print(f"    Total explique (somme)                   :      {total_explained:>4} ventes 5-ans")
    print(f"    En ventes/an                             :      {round(total_explained / 5, 1)}")
    residu = (secAllV - sct_total) - total_explained
    print(f"\n    Residu inexplique                        :      {residu} ventes 5-ans "
          f"({round(residu / 5, 1)}/an)")

    # ============================================================
    # [E] Liste detaillee
    # ============================================================
    print()
    print("=" * 78)
    print(f"[E] Adresses presentes dans (A) GLOBAL mais EXCLUES de (B) sctGen")
    print("=" * 78)

    blk1 = sorted(excl_social_bureaux, key=lambda x: -x["v"])
    blk2 = sorted(excl_ilot_null, key=lambda x: -x["v"])
    blk3 = sorted(excl_ilotX, key=lambda x: -x["v"])

    if blk1:
        print(f"\n[E1] EXCLUS via tag KV social/bureaux ({len(blk1)} adr, "
              f"{sum(x['v'] for x in blk1)} ventes 5-ans = "
              f"{round(sum(x['v'] for x in blk1) / 5, 1)}/an) :")
        print(f"  {'#':>3} {'cle':34s} {'v':>4} {'tag':10s} {'ilot':>5}")
        for i, r in enumerate(blk1[:30], 1):
            print(f"  {i:>3} {r['cle']:34s} {r['v']:>4} {r['tag']:10s} {r['ilot']:>5}")
        if len(blk1) > 30:
            print(f"  ... +{len(blk1) - 30} autres")

    if blk2:
        print(f"\n[E2] EXCLUS via ilot == null ({len(blk2)} adr, "
              f"{sum(x['v'] for x in blk2)} ventes 5-ans = "
              f"{round(sum(x['v'] for x in blk2) / 5, 1)}/an) :")
        print(f"  {'#':>3} {'cle':34s} {'v':>4} {'tag':10s}")
        for i, r in enumerate(blk2[:30], 1):
            print(f"  {i:>3} {r['cle']:34s} {r['v']:>4} {r['tag']:10s}")
        if len(blk2) > 30:
            print(f"  ... +{len(blk2) - 30} autres")

    if blk3:
        print(f"\n[E3] EXCLUS via _ilot == 'X' (hors secteur) ({len(blk3)} adr, "
              f"{sum(x['v'] for x in blk3)} ventes 5-ans = "
              f"{round(sum(x['v'] for x in blk3) / 5, 1)}/an) :")
        print(f"  {'#':>3} {'cle':34s} {'v':>4} {'tag':10s}")
        for i, r in enumerate(blk3[:30], 1):
            print(f"  {i:>3} {r['cle']:34s} {r['v']:>4} {r['tag']:10s}")
        if len(blk3) > 30:
            print(f"  ... +{len(blk3) - 30} autres")

    # ============================================================
    # [F] Tableau synthetique
    # ============================================================
    print()
    print("=" * 78)
    print("[F] TABLEAU DE RECONCILIATION")
    print("=" * 78)
    print(f"  {'Compteur':38s} {'5 ans':>10} {'/an':>10}")
    print("  " + "-" * 60)
    print(f"  {'[A] GLOBAL secteurRender':38s} {secAllV:>10} "
          f"{round(secVAn, 1):>10}")
    print(f"  {'[B] sctGenComputeIlots':38s} {sct_total:>10} "
          f"{round(sct_van, 1):>10}")
    print(f"  {'DELTA (A-B)':38s} {secAllV - sct_total:>10} "
          f"{round((secAllV - sct_total) / 5, 1):>10}")
    print("  " + "-" * 60)
    print(f"  {'  dont social/bureaux exclus':38s} "
          f"{total_excl_social_bureaux:>10} "
          f"{round(total_excl_social_bureaux / 5, 1):>10}")
    print(f"  {'  dont ilot == null exclus':38s} "
          f"{total_excl_ilot_null:>10} "
          f"{round(total_excl_ilot_null / 5, 1):>10}")
    print(f"  {'  dont _ilot == X exclus':38s} "
          f"{total_excl_ilotX:>10} "
          f"{round(total_excl_ilotX / 5, 1):>10}")
    print(f"  {'  residu non explique':38s} {residu:>10} "
          f"{round(residu / 5, 1):>10}")


if __name__ == "__main__":
    main()
