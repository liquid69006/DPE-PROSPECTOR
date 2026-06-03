#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_fuser_b2a_montchat.py - FUSER B2a Montchat (doublon bgid, GARDE PARITE).

Phase 5 Manche B2a. FUSER = fusion DANS LE LIGHT (PAS un tag KV) : une adresse
hors-RNC active partageant un batiment_groupe_id avec une copro RNC visible est
un DOUBLON de batiment ; on la fuse en SECONDAIRE (_fusion_auto=true +
_fusion_cible=<cle de la copro RNC ancre>, + ajout a _fusion_auto_sources de
l'ancre). Mecanisme DL des doublons bgid (cf scripts/fix_fusion_s1_immat.py).

GARDE PARITE / anti-cross-rue (comme DL/make_light) : on ne fuse une source
QUE si une copro RNC VISIBLE du MEME bgid est sur la MEME voie ET la MEME parite
(pair/impair) du numero. Sinon = CROSS-RUE -> ECARTEE (reste hors-RNC pour B2b).
Rationale (PIPELINE.md, passe bgid-orphelin REJETEE) : un bgid partage entre 2
cotes opposes de la rue (ou 2 voies) est un artefact de faux-matching BDNB ;
bgid+immat == meme batiment physique est FAUX dans ce cas.

Chainage : si une source a deja ses propres _fusion_auto_sources, on aplatit
(re-pointe) chaque source vers la nouvelle ancre (comme Manche A / fix_fusion_s1).

PARC-NEUTRE : source et ancre partagent le bgid -> cle de dedup `bg:<bgid>` deja
unique -> parc renderSecteur inchange. VERIFIE via _parc_replique_montchat.

Contrat : dry-run par defaut / --apply ; backup .preb2a.bak (ecrit une fois) ;
idempotent ; additif (ne touche que _fusion_*) ; trace
metadata._correctif_fuser_b2a_montchat.

NOTE 2026-06-03 : la garde parite ECARTE 33/53 sources non-encore-fusees (>15,
seuil d'arret de la spec B2a) -> APPLY NON LANCE par defaut sans validation
Yann. Le dry-run liste les 20 retenus + 33 cross-rue ecartes. Voir
data/diag_mancheB2a_montchat.md.

Usage : PYTHONUTF8=1 python scripts/fix_fuser_b2a_montchat.py [--apply]
"""
import json
import os
import re
import shutil
import sys

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIGHT = os.path.join(ROOT, "data", "secteur_montchat_light.json")
BAK = LIGHT + ".preb2a.bak"


def num(v):
    return v if isinstance(v, (int, float)) else 0


def base_num(cle):
    m = re.match(r"(\d+)", (cle or "").split("|")[0])
    return int(m.group(1)) if m else None


def voie(cle):
    p = (cle or "").split("|")
    return "|".join(p[1:]) if len(p) > 1 else ""


def syn_ok(s):
    if not s:
        return False
    s = str(s).strip().lower()
    return s not in ("", "non connu", "non renseigne", "non renseigné", "-")


def is_secondary(a):
    return bool(a.get("_fusion_auto")
                and (a.get("_fusion_cible") or a.get("_fusion_auto_target")))


def main():
    apply = "--apply" in sys.argv
    with open(LIGHT, encoding="utf-8") as f:
        d = json.load(f)
    adr = d["adresses"]
    by_cle = {a["cle"]: a for a in adr}
    copros = d.get("coproprietes") or []
    copro_cle = {c["cle_adresse"] for c in copros if c.get("cle_adresse")}

    def hors_rnc(a):
        return (a["cle"] not in copro_cle) and not a.get("numero_immatriculation")

    # RNC-visible adresses par bgid (immat OU cle in coproprietes)
    bg_rnc = {}
    for a in adr:
        bg = a.get("batiment_groupe_id")
        if not bg:
            continue
        if a.get("numero_immatriculation") or (a["cle"] in copro_cle):
            bg_rnc.setdefault(bg, []).append(a)

    # Oranges actives (hors-RNC + (ventes_log>0 OU nb_log_bdnb>1))
    oranges = [a for a in adr if hors_rnc(a)
               and (num(a.get("nb_ventes_logement")) > 0
                    or num(a.get("nb_log_bdnb")) > 1)]
    # Candidates FUSER non-encore-fusees partageant un bgid RNC visible
    notyet = [a for a in oranges
              if a.get("batiment_groupe_id") in bg_rnc and not is_secondary(a)]

    # FAUX-BGID connus : meme voie + meme parite MAIS gros ecart de numero ->
    # pas le meme batiment physique (le bgid BDNB est un faux-matching).
    # Deferre en B2b (revue terrain), comme les cross-rue. Ex 104B vs 44 PINEL
    # (60 num d'ecart) : valide par Yann le 2026-06-03.
    EXCLUDE_FAUXBGID = {"104B|BOULEVARD|PINEL"}

    retained, cross = [], []
    for a in notyet:
        bg = a["batiment_groupe_id"]
        sn, sv = base_num(a["cle"]), voie(a["cle"])
        sibs = bg_rnc[bg]
        same = [u for u in sibs
                if voie(u["cle"]) == sv
                and base_num(u["cle"]) is not None and sn is not None
                and (base_num(u["cle"]) % 2) == (sn % 2)]
        if same and a["cle"] not in EXCLUDE_FAUXBGID:
            anchor = sorted(same, key=lambda u: (
                u["cle"] not in copro_cle,
                not syn_ok(u.get("syndic")),
                abs(base_num(u["cle"]) - sn),
                u["cle"]))[0]
            retained.append((a, anchor))
        elif same:
            anchor = sorted(same, key=lambda u: abs(base_num(u["cle"]) - sn))[0]
            cross.append((a["cle"], anchor["cle"],
                          "faux-bgid ecart num %d (B2b)"
                          % abs(base_num(anchor["cle"]) - sn)))
        else:
            anchor = sorted(sibs, key=lambda u: (
                u["cle"] not in copro_cle, not syn_ok(u.get("syndic")),
                -num(u.get("nb_ventes_logement")), u["cle"]))[0]
            reasons = []
            if voie(anchor["cle"]) != sv:
                reasons.append("voie diff")
            an = base_num(anchor["cle"])
            if an is None or sn is None or (an % 2) != (sn % 2):
                reasons.append("parite opposee (%s vs %s)" % (sn, an))
            cross.append((a["cle"], anchor["cle"], "; ".join(reasons) or "?"))

    print("== fix_fuser_b2a_montchat == (%s)" % ("APPLY" if apply else "DRY-RUN"))
    print("Candidates FUSER non-fusees (orange, meme bgid qu'une copro RNC): %d"
          % len(notyet))
    print("RETENUS (garde parite OK, meme voie + meme parite) : %d" % len(retained))
    for a, anc in retained:
        print("  [fuse]  %-32s -> %s" % (a["cle"], anc["cle"]))
    print("ECARTES CROSS-RUE (parite opposee / voie differente) : %d" % len(cross))
    for cle, anc, why in cross:
        print("  [skip]  %-32s (ancre candidate %s) [%s]" % (cle, anc, why))

    # Note : les sources DEJA fusees (secondaires) partageant un bgid RNC sont
    # comptees dans le "133" du dry-run mais sont des no-op ici.
    already = [a for a in oranges
               if a.get("batiment_groupe_id") in bg_rnc and is_secondary(a)]
    print("(deja fusees, no-op : %d ; total FUSER dry-run = %d)"
          % (len(already), len(retained) + len(cross) + len(already)))

    if not apply:
        print("\n[DRY-RUN] aucune ecriture. --apply pour fuser les RETENUS.")
        return

    if len(cross) > 15:
        print("\n[STOP] garde parite ecarte %d cross-rue (>15, seuil spec B2a). "
              "APPLY refuse sans flag explicite de forcage. Documente et valide "
              "avec Yann (data/diag_mancheB2a_montchat.md)." % len(cross))
        if "--force" not in sys.argv:
            sys.exit(2)
        print("  --force fourni : on continue malgre l'avertissement.")

    if not os.path.exists(BAK):
        shutil.copyfile(LIGHT, BAK)
        print("\n[backup] %s" % os.path.basename(BAK))
    else:
        print("\n[backup] %s existe deja (conserve)" % os.path.basename(BAK))

    n_fold = 0
    for a, anchor in retained:
        if is_secondary(anchor) or is_secondary(a):
            print("  [skip] %s : ancre/source deja secondaire" % a["cle"])
            continue
        srcs = list(anchor.get("_fusion_auto_sources") or [])
        # aplatir la chaine eventuelle de la source
        for sc in (a.get("_fusion_auto_sources") or []):
            sa = by_cle.get(sc)
            if sa is not None:
                sa["_fusion_auto"] = True
                sa["_fusion_cible"] = anchor["cle"]
                sa.pop("_fusion_auto_target", None)
            if sc not in srcs:
                srcs.append(sc)
        a.pop("_fusion_auto_sources", None)
        a["_fusion_auto"] = True
        a["_fusion_cible"] = anchor["cle"]
        a.pop("_fusion_auto_target", None)
        if syn_ok(anchor.get("syndic")) and not syn_ok(a.get("syndic")):
            a["syndic"] = anchor.get("syndic")
            a["_syndic_src"] = (anchor.get("_syndic_src") or "rnc") + "_grp"
        if a["cle"] not in srcs:
            srcs.append(a["cle"])
        anchor["_fusion_auto_sources"] = srcs
        n_fold += 1

    meta = d.setdefault("metadata", {})
    meta["_correctif_fuser_b2a_montchat"] = {
        "desc": "FUSER B2a : doublons bgid hors-RNC fuses en secondaires vers "
                "leur copro RNC ancre, GARDE PARITE (meme voie+parite).",
        "retenus": n_fold,
        "cross_rue_ecartes": [c[0] for c in cross],
        "parc_neutre": True,
    }
    with open(LIGHT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("[ok] %d sources fusees. Light ecrit." % n_fold)


if __name__ == "__main__":
    main()
