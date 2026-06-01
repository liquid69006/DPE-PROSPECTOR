#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fusion_s1_immat.py - Fusion S1 (meme bgid + meme immat + DECLARE par BDNB), DL.

PERIMETRE STRICT : 3 groupes LEGITIMES seulement (QRF3 6B->4, FUDZ 19B->19,
JTAL 28B->24). EXCLUT volontairement G1YT (121A-D) et VFY6 (11B) : immat
FANTOME (cf diag data/diag_s1_immat_provenance_dl.md).

Pourquoi un GARDE l_libelle_adr (et pas juste "meme bgid + meme immat") :
make_light rattache parfois un suffixe au mauvais bgid par faux-matching
num_voie (type Fremicourt), PUIS denormalise l'immat de l'ancre copro sur tout
le bloc bgid -> le suffixe herite d'un immat FANTOME. Exemples confirmes LIVE
(BDNB l_libelle_adr) :
  - 121A/B/C/D CHARIAL : bgid 3WFJ-G1YT-XLZF declare {90,92} SEULEMENT -> 121
    est un intrus (vrai 121 = bgid AX8P, parcelle DT0120). NE PAS fusionner.
  - 11B ST MAXIMIN : bgid RBD4-VFY6-RGM1 declare {23,25} SEULEMENT. Intrus.
Ces 2 fantomes relevent d'une DE-ASSOCIATION (retrait immat fantome +
correction bgid), PAS d'une fusion -> hors de ce lot.

Critere SUR de fusion : (1) meme bgid, (2) toutes les unites rendues du bgid
portent le MEME numero_immatriculation non null, (3) le numero de base de la
source est REELLEMENT declare par le bgid cote BDNB (table DECLARED, preuve
LIVE l_libelle_adr du diag). Un bgid absent de DECLARED n'est PAS fusionne
tant que sa declaration n'a pas ete verifiee en live.

Contrat PIPELINE.md S2 : dry-run defaut / --apply ; backup .prefusions1.bak
(ecrit une fois) ; idempotent ; additif (ne touche que _fusion_* + _syndic_src) ;
trace metadata._correctif_fusion_s1.

Ancre (regle Yann) : unite portant la copro (cle_adresse) ; sinon syndic ;
sinon +ventes ; sinon cle. Parc bg:bgid inchange ; Sigma ventes conservee.

Usage : python scripts/fix_fusion_s1_immat.py [--apply]
"""
import json
import os
import re
import shutil
import sys

LIGHT = os.path.join(os.path.dirname(__file__), "..", "data",
                     "secteur_dauphine_lacassagne_light.json")
BAK = LIGHT + ".prefusions1.bak"

# Numeros REELLEMENT declares par chaque bgid cote BDNB l_libelle_adr (preuve
# LIVE, cf data/diag_s1_immat_provenance_dl.md E1). Une source n'est fusionnee
# que si son numero de base figure ici -> ecarte les immats FANTOMES.
# bgid absent de cette table = NON fusionnable (verification live requise).
# Cle = suffixe de bgid (substring), valeur = set des numeros de base declares.
DECLARED = {
    "SR2C-QRF3-15LG": {4, 6},        # LE NIVOLET / 4-6 RUE STE ANNE DE BARABAN
    "7TYE-FUDZ-T2KQ": {19},          # LE SAINT ANTOINE / 19 RUE ST ANTOINE
    "JTAL-3RN1-KX5T": {24, 26, 28},  # RES. CLAUDIUS PIONCHON / 24-26-28
    # --- FANTOMES exclus (bgid NE declare PAS le numero source) -> de-association ---
    "3WFJ-G1YT-XLZF": {90, 92},      # 90-92 CHARIAL : 121A-D = intrus
    "RBD4-VFY6-RGM1": {23, 25},      # CARRE DES LYS : 11B = intrus
}


def base_num(cle):
    m = re.match(r"(\d+)", (cle or "").split("|")[0])
    return int(m.group(1)) if m else None


def declared_for(bg):
    for sfx, nums in DECLARED.items():
        if sfx in (bg or ""):
            return nums
    return None


def syn_ok(s):
    if not s:
        return False
    s = str(s).strip().lower()
    return s not in ("", "non connu", "non renseigne", "non renseigné", "-")


def vlog(a):
    v = a.get("nb_ventes_logement")
    return v if isinstance(v, (int, float)) else 0


def is_secondary(a):
    return bool(a.get("_fusion_auto")
                and (a.get("_fusion_cible") or a.get("_fusion_auto_target")))


def main():
    apply = "--apply" in sys.argv
    with open(LIGHT, encoding="utf-8") as f:
        d = json.load(f)
    adr = d["adresses"]
    by_cle = {a["cle"]: a for a in adr}
    copro_cle = {c["cle_adresse"] for c in (d.get("coproprietes") or [])
                 if c.get("cle_adresse")}

    # 1. Grouper les UNITES RENDUES (non-secondaires) par bgid.
    grp = {}
    for a in adr:
        bg = a.get("batiment_groupe_id")
        if not bg or is_secondary(a):
            continue
        grp.setdefault(bg, []).append(a)

    # 2. Candidats S1 : >1 unite rendue, toutes meme immat NON null.
    cands = []
    for bg, units in grp.items():
        if len(units) < 2:
            continue
        immats = {u.get("numero_immatriculation") for u in units}
        if len(immats) == 1 and None not in immats and "" not in immats:
            cands.append((bg, sorted(units, key=lambda u: u["cle"])))

    print("== fix_fusion_s1_immat.py == (%s)"
          % ("APPLY" if apply else "DRY-RUN"))
    print("Candidats S1 (meme bgid + meme immat) : %d" % len(cands))

    plan = []
    excluded = []
    total_reloc = 0
    for bg, units in cands:
        immat = units[0].get("numero_immatriculation")
        ancre = sorted(units, key=lambda u: (
            u["cle"] not in copro_cle,
            not syn_ok(u.get("syndic")),
            -vlog(u),
            u["cle"],
        ))[0]
        secs = [u for u in units if u["cle"] != ancre["cle"]]
        decl = declared_for(bg)
        # GARDE l_libelle_adr : ne garder que les sources DONT le numero de base
        # est declare par le bgid cote BDNB.
        kept, ghosts = [], []
        for u in secs:
            n = base_num(u["cle"])
            if decl is not None and n in decl:
                kept.append(u)
            else:
                ghosts.append(u)
        if ghosts:
            excluded.append((bg, immat, [u["cle"] for u in ghosts],
                             "bgid declare %s" % (sorted(decl) if decl else "??")))
        if not kept:
            continue
        if is_secondary(ancre) or any(is_secondary(u) for u in kept):
            print("  [skip] %s : ancre/unite deja fusionnee" % bg)
            continue
        rechained = []
        for u in kept:
            rechained += list(u.get("_fusion_auto_sources") or [])
        reloc = sum(vlog(u) for u in kept) + sum(
            vlog(by_cle[c]) for c in rechained if c in by_cle)
        total_reloc += reloc
        plan.append({
            "bg": bg, "immat": immat, "ancre": ancre["cle"],
            "fold": [u["cle"] for u in kept], "rechain": rechained,
            "reloc": reloc,
        })

    # 3. Affichage
    print("\nGroupes FUSIONNES (garde l_libelle_adr OK) : %d" % len(plan))
    print("%-22s | %-11s | %-30s | %-26s | reloc"
          % ("bgid (suffixe)", "immat", "ANCRE <-", "source foldee"))
    print("-" * 104)
    for p in plan:
        sfx = p["bg"].replace("bdnb-bg-", "")
        fold_str = ", ".join(p["fold"])
        if p["rechain"]:
            fold_str += " (+chaine: %s)" % ", ".join(p["rechain"])
        print("%-22s | %-11s | %-30s | %-26s | %d"
              % (sfx, p["immat"], p["ancre"], fold_str[:26], p["reloc"]))
    print("-" * 104)
    print("TOTAL : %d groupes, %d ventes_logement relocalisees" % (len(plan), total_reloc))

    if excluded:
        print("\nSources EXCLUES (immat FANTOME : numero NON declare par le bgid) :")
        for bg, immat, cles, why in excluded:
            print("  %-22s immat=%-11s exclut %s  [%s]"
                  % (bg.replace("bdnb-bg-", ""), immat, ", ".join(cles), why))
        print("  -> relevent d'une DE-ASSOCIATION (hors de ce lot).")

    if not apply:
        print("\n[DRY-RUN] aucune ecriture. Relancer avec --apply pour ecrire.")
        return

    # 4. APPLY
    if not os.path.exists(BAK):
        shutil.copyfile(LIGHT, BAK)
        print("\n[backup] %s" % os.path.basename(BAK))
    else:
        print("\n[backup] %s existe deja (conserve)" % os.path.basename(BAK))

    n_fold = 0
    for p in plan:
        ancre = by_cle[p["ancre"]]
        srcs = list(ancre.get("_fusion_auto_sources") or [])
        for cle in p["fold"]:
            u = by_cle[cle]
            for sc in (u.get("_fusion_auto_sources") or []):
                sa = by_cle.get(sc)
                if sa is not None:
                    sa["_fusion_auto"] = True
                    sa["_fusion_cible"] = p["ancre"]
                    sa.pop("_fusion_auto_target", None)
                    if syn_ok(ancre.get("syndic")) and not syn_ok(sa.get("syndic")):
                        sa["syndic"] = ancre.get("syndic")
                        sa["_syndic_src"] = (ancre.get("_syndic_src") or "rnc") + "_grp"
                if sc not in srcs:
                    srcs.append(sc)
            u.pop("_fusion_auto_sources", None)
            u.pop("_fusion_auto_label", None)
            u["_fusion_auto"] = True
            u["_fusion_cible"] = p["ancre"]
            u.pop("_fusion_auto_target", None)
            if syn_ok(ancre.get("syndic")) and not syn_ok(u.get("syndic")):
                u["syndic"] = ancre.get("syndic")
                u["_syndic_src"] = (ancre.get("_syndic_src") or "rnc") + "_grp"
            if cle not in srcs:
                srcs.append(cle)
            n_fold += 1
        ancre["_fusion_auto_sources"] = srcs

    meta = d.setdefault("metadata", {})
    meta["_correctif_fusion_s1"] = {
        "desc": "Fusion S1 : suffixes meme-bgid + meme immat DECLARE par BDNB "
                "(garde l_libelle_adr). 3 groupes legitimes (QRF3/FUDZ/JTAL). "
                "Fantomes G1YT(121A-D)+VFY6(11B) EXCLUS -> de-association separee.",
        "groupes": len(plan),
        "unites_foldees": n_fold,
        "ventes_relocalisees": total_reloc,
        "exclus_fantome": [c for _, _, cles, _ in excluded for c in cles],
        "parc_neutre": True,
    }

    with open(LIGHT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("[ok] %d groupes, %d unites foldees. Light ecrit." % (len(plan), n_fold))


if __name__ == "__main__":
    main()
