#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_deassoc_fantome_dl.py - De-association MINIMALE d'immats FANTOMES (DL).

Perimetre STRICT (option 1, cf data/diag_deassoc_immat_fantome_dl.md) :

  A) 121A/B/C/D RUE ANTOINE CHARIAL : immat AA9271602 + lots 25 FANTOMES
     (heritage du bgid faux-matche 3WFJ-G1YT-XLZF = bati 90-92). RE-POINT vers
     le VRAI bgid AX8P-5ZM6-3A3B (parcelle DT0120) + rattachement a la vraie
     ancre `121|RUE|ANTOINE CHARIAL` (fusion label-only, deja sur AX8P) +
     RETRAIT immat/lots fantomes. -> resout le doublon d'ilot 34 (vrai 121)
     vs 39 (phantom) : seul `121` rendu, en ilot 34.

  B) 11B RUE ST MAXIMIN : immat AB4738928 + lots 76 FANTOMES (heritage du bgid
     RBD4-VFY6-RGM1 = CARRE DES LYS 23/25 ; aucun housenumber 11/11B declare,
     pas de vrai bgid BAN). Simple RETRAIT immat/lots ; on garde le bgid et la
     ligne (hors-RNC cible_0vente_active, nb_log_bdnb=41 conserve).

NE PAS toucher : les 21 fantomes deja fusionnes (caches, inoffensifs), la
vraie copro 90/92 (AA9271602), ni les impasses de l'Ordre (piege +21 lgts
sur-comptage si de-fusion).

Impact attendu STRICTEMENT NEUTRE (les fantomes sont social/cible 0-vente,
vlog=0, immat display-only ; le parc lit les lots via coproByCle pas la ligne) :
  parc secL 22381 inchange, Sigma ventes 2998 inchangee, marche-libre 578,4
  inchange. Seul effet : doublon d'ilot 121 resolu + immat trompeur retire.

Contrat PIPELINE.md S2 : dry-run defaut / --apply ; backup .predeassoc.bak ;
idempotent ; additif/surgical ; trace metadata._correctif_deassoc_fantome.

Usage : python scripts/fix_deassoc_fantome_dl.py [--apply]
"""
import json
import os
import shutil
import sys

LIGHT = os.path.join(os.path.dirname(__file__), "..", "data",
                     "secteur_dauphine_lacassagne_light.json")
BAK = LIGHT + ".predeassoc.bak"

AX8P = "bdnb-bg-AX8P-5ZM6-3A3B"     # VRAI bgid de 121 CHARIAL (parcelle DT0120)
G1YT = "bdnb-bg-3WFJ-G1YT-XLZF"     # bgid fantome (bati 90-92)
ANCRE_121 = "121|RUE|ANTOINE CHARIAL"
PHANTOM_121 = ["121A|RUE|ANTOINE CHARIAL", "121B|RUE|ANTOINE CHARIAL",
               "121C|RUE|ANTOINE CHARIAL", "121D|RUE|ANTOINE CHARIAL"]
ONZE_B = "11B|RUE|ST MAXIMIN"


def snap(a):
    return {k: a.get(k) for k in (
        "batiment_groupe_id", "numero_immatriculation", "nb_lots_habitation",
        "_nb_lots_habitation_override", "_fusion_auto", "_fusion_cible",
        "_fusion_auto_sources", "_ilot", "_bdnb_match")}


def main():
    apply = "--apply" in sys.argv
    with open(LIGHT, encoding="utf-8") as f:
        d = json.load(f)
    by = {a["cle"]: a for a in d["adresses"]}

    print("== fix_deassoc_fantome_dl.py == (%s)" % ("APPLY" if apply else "DRY-RUN"))

    # --- gardes de coherence (etat attendu) ---
    ok = True
    anc = by.get(ANCRE_121)
    if not anc or anc.get("batiment_groupe_id") != AX8P:
        print("  [!] ancre %s absente ou bgid != AX8P -> abort" % ANCRE_121); ok = False
    for c in PHANTOM_121:
        a = by.get(c)
        if not a:
            print("  [!] %s absent -> abort" % c); ok = False
    if ONZE_B not in by:
        print("  [!] %s absent -> abort" % ONZE_B); ok = False
    if not ok:
        return

    changes = []   # (cle, before_dict, after_fn)

    # ── A) 121A-D : re-point AX8P + fuse dans vrai 121 + retrait immat/lots ──
    anc_ilot = anc.get("_ilot")
    new_srcs = list(anc.get("_fusion_auto_sources") or [])
    for c in PHANTOM_121:
        a = by[c]
        before = snap(a)

        def mut(a=a, c=c):
            a["batiment_groupe_id"] = AX8P
            a["numero_immatriculation"] = None
            a["nb_lots_habitation"] = None
            a.pop("_nb_lots_habitation_override", None)
            a.pop("_fusion_auto_sources", None)   # 121A perd son role d'ancre
            a.pop("_fusion_auto_label", None)
            a["_fusion_auto"] = True
            a["_fusion_cible"] = ANCRE_121
            a.pop("_fusion_auto_target", None)
            a["_ilot"] = anc_ilot                 # rejoint l'ilot du vrai 121 (34)
        changes.append((c, before, mut))
        if c not in new_srcs:
            new_srcs.append(c)

    def mut_anc(anc=anc, new_srcs=new_srcs):
        anc["_fusion_auto_sources"] = new_srcs
    changes.append((ANCRE_121, snap(anc), mut_anc))

    # ── B) 11B ST MAXIMIN : retrait immat/lots fantomes (garde bgid + ligne) ──
    b = by[ONZE_B]

    def mut_11b(b=b):
        b["numero_immatriculation"] = None
        b["nb_lots_habitation"] = None
        b.pop("_nb_lots_habitation_override", None)
    changes.append((ONZE_B, snap(b), mut_11b))

    # idempotence : deja fait ?
    done = (all(by[c].get("batiment_groupe_id") == AX8P
                and by[c].get("numero_immatriculation") is None
                and by[c].get("_fusion_cible") == ANCRE_121 for c in PHANTOM_121)
            and by[ONZE_B].get("numero_immatriculation") is None)
    if done:
        print("  [idempotent] de-association deja appliquee -> no-op.")
        return

    # --- dry-run table avant/apres ---
    print("\n%-30s | %-26s | %-11s | %-5s | fa/cible / ilot"
          % ("cle", "bgid", "immat", "lots"))
    print("-" * 104)
    # applique en memoire pour afficher l'apres, mais n'ecrit que si --apply
    for cle, before, fn in changes:
        a = by[cle]
        fn()
        after = snap(a)
        bg_b = (before["batiment_groupe_id"] or "").replace("bdnb-bg-", "")
        bg_a = (after["batiment_groupe_id"] or "").replace("bdnb-bg-", "")
        print("AVANT %-24s | %-26s | %-11s | %-5s | fa=%s cible=%s ilot=%s"
              % (cle, bg_b, before["numero_immatriculation"], before["nb_lots_habitation"],
                 before["_fusion_auto"], before["_fusion_cible"], before["_ilot"]))
        print("APRES %-24s | %-26s | %-11s | %-5s | fa=%s cible=%s ilot=%s srcs=%s"
              % ("", bg_a, after["numero_immatriculation"], after["nb_lots_habitation"],
                 after["_fusion_auto"], after["_fusion_cible"], after["_ilot"],
                 after["_fusion_auto_sources"] if cle == ANCRE_121 else ""))
        print("-" * 104)

    if not apply:
        print("\n[DRY-RUN] aucune ecriture. Relancer avec --apply pour ecrire.")
        return

    if not os.path.exists(BAK):
        shutil.copyfile(LIGHT, BAK)
        print("[backup] %s" % os.path.basename(BAK))
    else:
        print("[backup] %s existe deja (conserve)" % os.path.basename(BAK))

    meta = d.setdefault("metadata", {})
    meta["_correctif_deassoc_fantome"] = {
        "desc": "De-association immats fantomes : 121A-D re-point bgid faux-match "
                "G1YT(90-92) -> AX8P(DT0120) + fuse vrai 121 + retrait immat/lots "
                "AA9271602 (resout doublon ilot 34/39) ; 11B ST MAXIMIN retrait "
                "immat/lots AB4738928 (pas de vrai bgid BAN). Parc/ventes neutres.",
        "repoint_121": PHANTOM_121, "retrait_11b": ONZE_B,
        "parc_neutre": True,
    }
    with open(LIGHT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("[ok] de-association ecrite (5 adresses touchees + ancre 121).")


if __name__ == "__main__":
    main()
