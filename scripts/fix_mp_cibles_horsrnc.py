"""
Correctif SURGICAL — 7 adresses cibles Motte-Picquet hors-RNC avec
ventes DVF, rattachees a leur copro RNC reelle. DRY-RUN par defaut
(modelise l'effet parc/ventes en emulant la regle parc de
renderSecteur §6 ; n'ecrit RIEN sans --apply). Backup .precibleshr.bak.

3 mecanismes (cf. data/PIPELINE.md §4) :

A1 — ALIAS_RNC, meme bgid (PARC-NEUTRE x5) : adresse DVF fantome
     (variante d'orthographe / voie d'angle) -> copro reelle ancree
     sur la cle soeur, MEME batiment_groupe_id. On pose _fusion_auto
     vers l'ancre ; ventes relocalisees ; parc inchange (bgRncLots
     domine deja le bgid). Sortie des hors-RNC actifs.
       6|RUE|CHAMPFLEURY      -> 45|AVENUE|SUFFREN     (AB0758383,29)
       1|RUE|BUENOS AIRES     -> 1|RUE|BUENOS AYRES    (AD4111738,13)
       |ALLEE|LEON BOURGEOIS  -> 1|RUE|BUENOS AYRES    (AD4111738,13)
       5|RUE|GAL LAMBERT      -> 5|RUE|GENERAL LAMBERT (AB7917073,39)
       3|RUE|BUENOS AIRES     -> 3|RUE|BUENOS AYRES    (AB3659166,30)

A2 — ALIAS_RNC, bgid DIFFERENT (miroir, PARC -11 dedup x1) :
     4|AVENUE|OCTAVE GREARD (bg ZWNL, sans copro, nb_log_bdnb=11) ->
     copro AA1378777 nom "4 AVENUE OCTAVE GREARD" (11 lots) ancree
     15|AVENUE|SUFFREN (bg 9HGZ). Le fantome adopte le bgid/usage de
     l'ancre (miroir make_light, cf. fix_dupleix_phantom). ZWNL
     disparait du parc : -11 logements = retrait d'un DOUBLON BDNB
     (meme copro 11 lots deja comptee sous 9HGZ), pas une perte.

A3 — RE-POINT de fusion-bgid inversee (PARC +20 correction x1) :
     38|AVENUE|CHARLES FLOQUET porte la copro AC6620728 "38 Charles
     Floquet" (36 lots) mais est fusionnee A TORT dans le fantome
     6|AVENUE|GAL DETRIE (meme bgid 51P3) -> copro INVISIBLE, parc
     compte 16 (estim. BDNB) au lieu de 36 (lots RNC). On inverse :
     38|... redevient principale (copro visible), 6|AVENUE|GAL DETRIE
     devient sa secondaire. Parc 51P3 : 16 -> 36 = +20 (correction
     d'un SOUS-comptage, meme bgid, aucun double-comptage). Meme
     motif que les sous-fusions re-pointees de fix_armonial.

5 adresses cibles restantes = categorie B (AUCUNE copro RNC ni cote
BDNB ni au RNC open data live) : 55 AVENUE SUFFREN, 21 AVENUE CHARLES
FLOQUET, 2 RUE DE BUENOS AIRES, 4 RUE DE BUENOS AIRES, 69/71/73 QUAI
JACQUES CHIRAC -> vraies monoproprietes / copros non immatriculees,
RIEN a faire (restent hors-RNC, conforme).

Source-of-truth (a porter dans make_light_motte_picquet.py, hors
depot) : ALIAS_RNC += les 6 (A1+A2) ; pour A3, critere copro_by_cle
deja present mais a forcer sur ce bgid (la copro a 1 vente < fantome
3 -> tri prend le fantome).

Usage :
  python scripts/fix_mp_cibles_horsrnc.py            # DRY-RUN
  python scripts/fix_mp_cibles_horsrnc.py --apply    # (apres validation)
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.precibleshr.bak"

# A1 : phantom -> (anchor_cle, immat) ; meme bgid, parc-neutre
A1 = [
    ("6|RUE|CHAMPFLEURY",     "45|AVENUE|SUFFREN",     "AB0758383"),
    ("1|RUE|BUENOS AIRES",    "1|RUE|BUENOS AYRES",    "AD4111738"),
    ("|ALLEE|LEON BOURGEOIS", "1|RUE|BUENOS AYRES",    "AD4111738"),
    ("5|RUE|GAL LAMBERT",     "5|RUE|GENERAL LAMBERT", "AB7917073"),
    ("3|RUE|BUENOS AIRES",    "3|RUE|BUENOS AYRES",    "AB3659166"),
]
# A2 : phantom -> anchor, bgid different (miroir)
A2 = ("4|AVENUE|OCTAVE GREARD", "15|AVENUE|SUFFREN", "AA1378777")
# A3 : re-point (principal_actuel_fantome, ancre_copro, immat)
A3 = ("6|AVENUE|GAL DETRIE", "38|AVENUE|CHARLES FLOQUET", "AC6620728")

MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def parc_model(light):
    """Replique la regle parc renderSecteur §6 : dedup bgid, lots RNC
    prioritaires sinon nb_log_bdnb si bati residentiel."""
    ad = light["adresses"]
    co = {c["cle_adresse"]: c for c in light["coproprietes"]
          if c.get("cle_adresse")}
    RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    fused = set()
    for a in ad:
        if a.get("_fusion_auto") and a.get("_fusion_cible") \
                and a["cle"] not in fused:
            fused.add(a["cle"])
    bgRncLots, bgBdnb, immatBg = {}, {}, {}
    for a in ad:
        if a["cle"] in fused:
            continue
        bg = a.get("batiment_groupe_id")
        cp = co.get(a["cle"])
        if bg and cp and (cp.get("nb_lots_habitation") or 0) > 0:
            im = cp.get("numero_immatriculation") or cp["cle_adresse"]
            immatBg.setdefault(im, bg)
            bgRncLots.setdefault(immatBg[im], {})[im] = cp["nb_lots_habitation"]
        if bg and not cp and a.get("usage_principal_bdnb") in RESID \
                and (a.get("nb_log_bdnb") or 0) > 0 and bg not in bgBdnb:
            bgBdnb[bg] = a["nb_log_bdnb"]
    parc = 0
    for bg in set(bgRncLots) | set(bgBdnb):
        parc += (sum(bgRncLots[bg].values()) if bg in bgRncLots
                 else bgBdnb.get(bg, 0))
    return parc


def apply_changes(light):
    by = {}
    for a in light["adresses"]:
        by.setdefault(a["cle"], []).append(a)

    def one(cle):
        v = by.get(cle)
        return v[0] if v else None

    log = []
    # A1
    for ph, anc, immat in A1:
        s, d = one(ph), one(anc)
        s["_fusion_auto"] = True
        s["_fusion_cible"] = anc
        srcs = sorted(set((d.get("_fusion_auto_sources") or []) + [ph]))
        d["_fusion_auto_sources"] = srcs
        d.setdefault("_fusion_auto_label", None)
        log.append(f"A1 {ph:24s} -> {anc} ({immat}) [meme bgid]")
    # A2 (miroir)
    ph, anc, immat = A2
    s, d = one(ph), one(anc)
    for k in MIRROR:
        s[k] = d.get(k)
    s["_bdnb_match"] = "immat"
    s["_fusion_auto"] = True
    s["_fusion_cible"] = anc
    d["_fusion_auto_sources"] = sorted(
        set((d.get("_fusion_auto_sources") or []) + [ph]))
    d.setdefault("_fusion_auto_label", None)
    log.append(f"A2 {ph} -> {anc} ({immat}) [miroir bgid]")
    # A3 (re-point)
    fant, anc, immat = A3
    fa, da = one(fant), one(anc)
    da["_fusion_auto"] = None
    da["_fusion_cible"] = None
    da["_fusion_auto_sources"] = [fant]
    da.setdefault("_fusion_auto_label", None)
    fa["_fusion_auto"] = True
    fa["_fusion_cible"] = anc
    fa["_fusion_auto_sources"] = None
    log.append(f"A3 RE-POINT {anc} <= {fant} ({immat})")
    return log


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    log = apply_changes(patched)
    parc1 = parc_model(patched)

    print("=" * 74)
    print("CORRECTIF CIBLES MP HORS-RNC — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 74)
    for l in log:
        print("  " + l)
    print("-" * 74)
    print(f"Parc (modele renderSecteur §6) : {parc0} -> {parc1} "
          f"(delta {parc1 - parc0:+d})")
    print("  attendu : A1 x5 = 0 | A2 = -11 (dedup) | A3 = +20 "
          "=> net +9")
    print("Ventes : relocalisees au rendu (champs ventes INCHANGES) ;")
    print("  6 RUE CHAMPFLEURY 4, 1 BUENOS AIRES 2, LEON BOURGEOIS 1,")
    print("  5 GAL LAMBERT 5, 3 BUENOS AIRES 1, 4 OCTAVE GREARD 1,")
    print("  6 GAL DETRIE 3 -> sur la copro RNC correspondante.")
    print("=" * 74)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. "
              "Validation requise avant --apply.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_cibles_horsrnc"] = (
        "7 adresses cibles MP hors-RNC a ventes DVF rattachees a leur "
        "copro RNC : A1 x5 ALIAS_RNC meme bgid parc-neutre (6 Champfleury"
        "/1+Allee Bourgeois Buenos Ayres/5 Gal Lambert/3 Buenos Ayres), "
        "A2 4 Octave Greard miroir bgid (-11 dedup BDNB), A3 re-point "
        "fusion inversee 38 Ch Floquet<=6 Gal Detrie (+20 sous-comptage). "
        "Net parc +9 ; ventes relocalisees. 5 autres cibles = categorie "
        "B (aucune copro RNC) laissees hors-RNC.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
