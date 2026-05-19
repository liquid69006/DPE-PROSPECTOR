"""
Correctif SURGICAL : ensemble social RNC "ARMONIAL I" (AA0646265),
Motte-Picquet — copro multi-voies eclatee.

Constat (diagnostic ; cf. data/PIPELINE.md §4 ALIAS_RNC) :
  - RNC AA0646265 "ARMONIAL I" : 592 lots hab / 1726 tot / 557 park,
    ancree 16 BOULEVARD GARIBALDI (bgid LJRN-ABEM-2VT5),
    nombre_d_adresses_complementaires=14 (open-data tronque a 3 :
    compl_1 "7 Rue Carrier-Belleuse", compl_2 "15 Rue Cepre",
    compl_3 "16 bd Garibaldi"). Grand ensemble sur tout l'ilot
    Garibaldi / Carrier-Belleuse / Cepre / Miollis.
  - BDNB modelise l'ensemble en bgid MULTIPLES (LJRN principal + XDM8
    + KKXK + XUWV + LJD4 + VQB9 + CC8V/DRGZ/P3MV ...). Hors-pattern
    FUSION_RNC_EXTRA_NUMS (voies differentes) -> ALIAS_RNC multi-voie.
  - Etat : seul 32|RUE|MIOLLIS deja fusionne dans ARMONIAL. 15
    adresses existantes detachees (lignes hors-RNC ou sous-fusions
    bgid locales erronees : 20/24/26/28->30, 34->36, 15/19->17).
    13 adresses demandees ABSENTES du light (non geocodees DVF/BAN)
    -> hors de portee, rien a faire.

Decisions de perimetre (validees) :
  - Carrier-Belleuse 7+9+11 -> ARMONIAL (7 confirme RNC compl_1 ;
    9/11 assertes ; parc-neutre, co-occupes par copros 6/8/10).
  - 20 RUE MIOLLIS -> ARMONIAL aussi (meme bati XDM8 que 24-30,
    0 vente ; evite une chaine de fusion orpheline).
  - Sous-fusions locales (30/36/17 principaux + membres) RE-POINTEES
    directement sur 16|BOULEVARD|GARIBALDI, _fusion_auto_sources
    locaux vides -> etat propre, toutes ventes sur ARMONIAL.

15 adresses (re)fusionnees comme secondaires auto de
16|BOULEVARD|GARIBALDI :
  Carrier-Belleuse : 7, 9, 11
  Cepre            : 13, 15, 17, 19
  Miollis          : 20, 24, 26, 28, 30, 34, 36, 40
(+ 32|RUE|MIOLLIS deja fusionne -> conserve)

Miroir d'une fusion RNC multi-numeros : src -> _fusion_auto=True /
_fusion_cible=16|BOULEVARD|GARIBALDI ; _fusion_auto_sources local
VIDE (les ex-principaux deviennent secondaires) ; bgid /
nb_log_bdnb / _bdnb_match / usage / ventes (autoritatifs) INCHANGES.
Syndic NON propage (copro/principal = "non connu", non syn_ok).
ARMONIAL._fusion_auto_sources = union ; label informatif.

Effet : ventes des 15 (+32) relocalisees au rendu sous AA0646265,
sortie des hors-RNC actifs. Parc : co-occupes -> neutre ; bgid
entierement absorbes (LJD4/XDM8/KKXK/XUWV) -> dedup §6 (BDNB
fantomes du MEME ensemble 592-lots, subsumes, comme Acollas).
Ventes secteur CONSERVEES (relocalisation). Mesure via
test_render_secteur.js.

Source-of-truth : ALIAS_RNC (multi-voie) += {cle: "16|BOULEVARD|
GARIBALDI"} x15 dans make_light_motte_picquet.py (hors depot).

Cible : data/secteur_motte_picquet_light.json. Backup
.prearmonial.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_armonial.py            # DRY-RUN
  python scripts/fix_armonial.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prearmonial.bak"
DST_CLE = "16|BOULEVARD|GARIBALDI"
IMMAT = "AA0646265"

SRC_CLES = [
    "7|RUE|CARRIER BELLEUSE", "9|RUE|CARRIER BELLEUSE",
    "11|RUE|CARRIER BELLEUSE",
    "13|RUE|CEPRE", "15|RUE|CEPRE", "17|RUE|CEPRE", "19|RUE|CEPRE",
    "20|RUE|MIOLLIS", "24|RUE|MIOLLIS", "26|RUE|MIOLLIS",
    "28|RUE|MIOLLIS", "30|RUE|MIOLLIS", "32|RUE|MIOLLIS",
    "34|RUE|MIOLLIS", "36|RUE|MIOLLIS", "40|RUE|MIOLLIS",
]
# adresses demandees mais ABSENTES du light (trace, rien a faire)
ABSENTES = [
    "1/3/5 RUE CARRIER BELLEUSE",
    "1/3/5/7/9/9Z/11 RUE CEPRE",
    "12/14 BD GARIBALDI", "38 RUE MIOLLIS",
]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a.get("cle"): a for a in light.get("adresses", [])}
    dst = by.get(DST_CLE)
    if not dst:
        print(f"ABORT : principal {DST_CLE} absent du light.")
        return
    cop = next((c for c in light.get("coproprietes", [])
                if c.get("cle_adresse") == DST_CLE), None)
    if not cop or cop.get("numero_immatriculation") != IMMAT:
        print(f"ABORT : copro {IMMAT} introuvable sur {DST_CLE} "
              f"(got {cop and cop.get('numero_immatriculation')}).")
        return

    present = [(k, by[k]) for k in SRC_CLES if k in by]
    absent_cles = [k for k in SRC_CLES if k not in by]
    if absent_cles:
        print(f"NOTE : src attendues absentes du light : {absent_cles}")
    # garde : aucun src ne doit etre un autre SDC immatricule
    bad_immat = [k for k, a in present if a.get("numero_immatriculation")
                 and a.get("numero_immatriculation") != IMMAT]
    if bad_immat:
        print(f"ABORT : src porte une autre immatriculation : {bad_immat}.")
        return
    # garde : aucune adresse HORS set fusionnee dans un src (orphelin)
    setk = {k for k, _ in present}
    orphan = [a.get("cle") for a in light["adresses"]
              if a.get("_fusion_cible") in setk
              and a.get("cle") not in setk and a.get("cle") != DST_CLE]
    if orphan:
        print(f"ABORT : adresses hors-set fusionnees dans un src "
              f"(seraient orphelines) : {orphan}.")
        return

    cur = list(dst.get("_fusion_auto_sources") or [])
    new = sorted(set(cur) | {k for k, _ in present})
    new_label = ("ARMONIAL I — 16 BD GARIBALDI / CARRIER-BELLEUSE / "
                 "CEPRE / MIOLLIS")
    prop = syn_ok(dst.get("syndic"))

    def is_done(a):
        return (a.get("_fusion_auto") is True
                and a.get("_fusion_cible") == DST_CLE
                and not a.get("_fusion_auto_sources"))
    done = all(is_done(a) for _, a in present) \
        and {k for k, _ in present}.issubset(set(cur))

    print("=" * 72)
    print("CORRECTIF SURGICAL — ARMONIAL I (AA0646265) multi-voies")
    print("=" * 72)
    print(f"Mode            : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Deja applique   : {done}")
    print(f"Copro           : {cop.get('nom_copropriete')} ({IMMAT}) "
          f"{cop.get('nb_lots_habitation')} lots — syndic "
          f"{cop.get('syndic')!r} (propage syndic={prop})")
    print(f"Principal       : {DST_CLE} bgid={dst.get('batiment_groupe_id')}")
    print(f"Sources {len(cur)} -> {len(new)} : {new}")
    print(f"Label           : {dst.get('_fusion_auto_label')!r} -> "
          f"{new_label!r}")
    print(f"Absentes light  : {ABSENTES}")
    print("-" * 72)
    tot_vl = tot_vt = 0
    for k, a in present:
        tot_vl += a.get("nb_ventes_logement") or 0
        tot_vt += a.get("nb_ventes_total") or 0
        print(f"  {k:26s} bgid={a.get('batiment_groupe_id')} "
              f"v_log={a.get('nb_ventes_logement')} "
              f"vt={a.get('nb_ventes_total')} "
              f"_fa={a.get('_fusion_auto')} cible={a.get('_fusion_cible')} "
              f"src={a.get('_fusion_auto_sources')} -> cible {DST_CLE}, "
              f"src local VIDE")
    print("-" * 72)
    print(f"Total relocalise : {len(present)} adr, "
          f"{tot_vl} ventes logement / {tot_vt} ventes totales -> {IMMAT}")
    print("=" * 72)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if done:
        print("ABORT : correctif deja applique (idempotent).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    for _k, a in present:
        a["_fusion_auto"] = True
        a["_fusion_cible"] = DST_CLE
        # ex-principal local -> devient secondaire : sources videes
        if a.get("_fusion_auto_sources"):
            a["_fusion_auto_sources"] = None
        if a.get("_fusion_auto_label"):
            a["_fusion_auto_label"] = None
        if prop and not syn_ok(a.get("syndic")):
            a["syndic"] = dst.get("syndic")
            a["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"

    dst["_fusion_auto_sources"] = new
    dst["_fusion_auto_label"] = new_label

    meta = light.setdefault("metadata", {})
    meta["_correctif_armonial"] = (
        "Ensemble social RNC 'ARMONIAL I' (AA0646265, 592 lots hab / "
        "1726 tot, ancre 16 BD GARIBALDI bgid LJRN, nb_compl=14 "
        "tronque open-data) eclate sur 4 voies (Garibaldi/Carrier-"
        "Belleuse/Cepre/Miollis). 15 adresses existantes (re)fusionnees "
        "comme secondaires auto de 16|BOULEVARD|GARIBALDI via ALIAS_RNC "
        "multi-voie (sous-fusions bgid locales 30/36/17 re-pointees, "
        "sources locales videes) : CB 7/9/11 ; Cepre 13/15/17/19 ; "
        "Miollis 20/24/26/28/30/34/36/40 (+32 deja fusionne). Champs "
        "autoritatifs (bgid/nb_log_bdnb/_bdnb_match/usage/ventes) "
        "INCHANGES ; syndic NON propage (copro 'non connu'). Au rendu : "
        "ventes des 15 (+32) relocalisees sous AA0646265, sorties des "
        "hors-RNC actifs ; parc : co-occupes neutres, bgid integralement "
        "absorbes (LJD4/XDM8/KKXK/XUWV) subsumes par les 592 lots RNC "
        "(dedup §6, comme Acollas) ; ventes secteur conservees. 13 "
        "adresses demandees ABSENTES du light (non geocodees) hors "
        "portee. Source-of-truth = ALIAS_RNC dans "
        "make_light_motte_picquet.py. "
        f"{len(present) + 1} enregistrements touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(present)} adresses -> "
          f"secondaires de {DST_CLE} ; ventes relocalisees)")


if __name__ == "__main__":
    main()
