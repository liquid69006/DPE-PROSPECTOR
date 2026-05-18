"""
Correctif d'attribution RNC -> BDNB pour les copros INVISIBLES detectees
par la passe INVERSE hors-RNC (scripts/verif_horsrnc_bdnb.py +
scripts/evalue_rattach_horsrnc.py ; rapports data/verif_horsrnc_bdnb_*
et data/rattach_horsrnc_dryrun.md).

Difference avec scripts/fix_rnc_bdnb_attribution.py (categorie B) :
  - Cible la **categorie A / B2** : copros dont la cle_adresse n'est
    EXACTEMENT aucune cle d'adresse (donc coproByCle ne matche pas ->
    invisibles), MAIS dont un batiment BDNB est DEJA reference par une
    adresse hors-RNC du jeu. L'ancien fix saute ces cas
    (`if bset & secteur_bgids: continue`).
  - Source du lien immat<->bgid : la relation LIVE many-to-many
    (cache data/_horsrnc_bdnb_live.json) UNION numero_immat_principal
    du snapshot — PAS numero_immat_principal seul (projection lossy,
    cause de l'omission).

Securite anti-double-comptage : on rattache la copro au bgid qui est
DEJA porte par une adresse hors-RNC. La cle de dedup du front
(`bg:<bgid>`) existe donc deja -> aucun batiment nouveau ajoute au parc ;
la valeur du bati passe seulement de l'estimation `nb_log_bdnb` aux lots
RNC (bgValue = somme lots RNC prioritaire). Delta parc NET attendu : ~+35
logements (et non +1169). Invariants asserts :
  - bgid choisi ∈ adresses existantes (sinon ce n'est pas categorie A)
  - AUCUNE copro RNC deja visible sur ce bgid (verdict DEJA-COMPTE = 0)
  - cle injectee unique et absente des cles existantes (COLLISION-CLE = 0)

Cible : data/secteur_dauphine_lacassagne_light.json. Backup distinct
(.prehorsrnc.bak) pour NE PAS ecraser le .bak du fix precedent.

Usage :
  python scripts/fix_horsrnc_attribution.py            # DRY-RUN (defaut)
  python scripts/fix_horsrnc_attribution.py --apply     # ecrit + .bak
"""

import sys
import json
import collections
from pathlib import Path

import os
ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
_SUF = "" if SECTEUR == "dauphine_lacassagne" else "_" + SECTEUR
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
CACHE = ROOT / "data" / f"_horsrnc_bdnb_live{_SUF}.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prehorsrnc.bak"

NR = {"non connu", "", None}


def cle_to_adresse(cle):
    """`5B|RUE|MEYNIS` -> `5B RUE MEYNIS` (convention des lignes existantes)."""
    if not cle:
        return ""
    return " ".join(p for p in cle.split("|") if p != "").strip()


def construire_ligne(copro, bg, cle, adresse):
    """Ligne `adresses` (schema light) : copro RNC portee par le bati BDNB
    deja present dans le jeu via une adresse hors-RNC. Champs SCI/MAJIC
    neutres (meme convention que fix_rnc_bdnb_attribution.py — la ligne
    represente la copro, pas le batiment dont l'adresse hors-RNC porte
    deja les signaux)."""
    vpa = copro.get("ventes_par_an") or {}
    return {
        "cle": cle,
        "adresse": adresse,
        "longitude": copro.get("longitude"),
        "latitude": copro.get("latitude"),
        "code_iris": copro.get("code_iris"),
        "_coord_source": "rnc_immat_horsrnc_fix",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": None,
        "sci_siren": None,
        "syndic": copro.get("syndic"),
        "_syndic_src": copro.get("_syndic_src"),
        "ventes_par_an": vpa,
        "nb_ventes_total": sum(vpa.values()) if vpa else 0,
        "nb_log_bdnb": bg.get("nb_log"),
        "annee_construction": bg.get("annee_construction"),
        "classe_dpe": bg.get("classe_bilan_dpe"),
        "type_batiment": bg.get("type_batiment_dpe"),
        "type_chauffage": bg.get("type_energie_chauffage"),
        "batiment_groupe_id": bg["batiment_groupe_id"],
        "_bdnb_match": "immat_horsrnc_fix",
    }


def main():
    apply = "--apply" in sys.argv

    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    copros, adresses = light["coproprietes"], light["adresses"]

    bg_meta = {r["batiment_groupe_id"]: r for r in bdnb}
    snap_principal = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                      for r in bdnb}
    copro_by_immat = {c["numero_immatriculation"]: c for c in copros
                      if c.get("numero_immatriculation")}

    cle_adresse_exact = {c.get("cle_adresse") for c in copros
                         if c.get("cle_adresse")}
    cles_existantes = collections.Counter(a.get("cle") for a in adresses)

    def visible(im):
        c = copro_by_immat.get(im)
        return bool(c) and c.get("cle_adresse") in cles_existantes

    # immat lie a chaque bgid : LIVE many-to-many UNION snapshot principal
    bg_immats = {}
    for bg, ent in cache.items():
        s = set(ent.get("immats") or [])
        if snap_principal.get(bg) not in NR:
            s.add(snap_principal[bg])
        bg_immats[bg] = s

    # bgid -> adresses hors-RNC qui le portent deja
    bg_hors = collections.defaultdict(list)
    for a in adresses:
        if a.get("cle") not in cle_adresse_exact and a.get("batiment_groupe_id"):
            bg_hors[a["batiment_groupe_id"]].append(a)

    # copro invisible -> bgids hors-RNC candidats
    cand = collections.defaultdict(set)
    for bg in bg_hors:
        for im in bg_immats.get(bg, ()):
            if im in copro_by_immat and not visible(im):
                cand[im].add(bg)

    a_injecter = []           # (copro, bg_meta_row, cle, libelle, bgids_all)
    rejets = []               # (immat, raison)
    for im, bgs in sorted(cand.items()):
        c = copro_by_immat[im]
        cle = c.get("cle_adresse")
        if not cle:
            rejets.append((im, "cle_adresse vide"))
            continue
        if cle in cles_existantes:
            rejets.append((im, f"COLLISION-CLE ({cle} deja prise)"))
            continue
        bgs_meta = [b for b in bgs if b in bg_meta]
        if not bgs_meta:
            rejets.append((im, "aucun bgid dans le snapshot (attrs bati nd)"))
            continue
        # bgid de rattachement : le plus 'porteur' (max #adr hors-RNC),
        # puis max nb_log -> deterministe. (cas AE1699040 : 2 bgid -> 1)
        bg_pick = sorted(
            bgs_meta,
            key=lambda b: (-len(bg_hors[b]), -(bg_meta[b].get("nb_log") or 0), b)
        )[0]
        # invariant DEJA-COMPTE : aucune copro RNC deja VISIBLE sur ce bgid
        sib_vis = sorted(x for x in bg_immats.get(bg_pick, ())
                         if x in copro_by_immat and visible(x))
        if sib_vis:
            rejets.append((im, f"DEJA-COMPTE (sibling visible {sib_vis} "
                               f"sur {bg_pick})"))
            continue
        a_injecter.append((c, bg_meta[bg_pick], cle, cle_to_adresse(cle),
                           sorted(bgs)))

    # Invariants durs
    inj_cles = [cle for _, _, cle, _, _ in a_injecter]
    assert len(inj_cles) == len(set(inj_cles)), "cle injectee en double"
    assert not (set(inj_cles) & set(cles_existantes)), "cle injectee deja prise"
    for _, bg, _, _, _ in a_injecter:
        assert bg["batiment_groupe_id"] in {a.get("batiment_groupe_id")
                                            for a in adresses}, \
            "bgid choisi PAS deja reference -> ce n'est pas categorie A"

    tot_lots = sum((c.get("nb_lots_habitation") or 0)
                   for c, *_ in a_injecter)

    # Delta parc NET (modele dedup front : immatBg first-wins, cle bg:)
    bg_bdnb_first = {}
    for a in adresses:
        bg = a.get("batiment_groupe_id")
        if bg and (a.get("nb_log_bdnb") or 0) > 0 and bg not in bg_bdnb_first:
            bg_bdnb_first[bg] = a["nb_log_bdnb"]
    net = 0
    for c, bg, _, _, _ in a_injecter:
        before = bg_bdnb_first.get(bg["batiment_groupe_id"], 0)
        after = c.get("nb_lots_habitation") or 0
        net += after - before

    print("=" * 72)
    print("CORRECTIF HORS-RNC -> RNC (categorie A/B2, copros invisibles)")
    print("=" * 72)
    print(f"Mode                               : "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print(f"Lignes adresses actuelles          : {len(adresses)}")
    print(f"Copros invisibles candidates       : {len(cand)}")
    print(f"  -> a injecter (PROPRE)           : {len(a_injecter)}")
    print(f"  -> rejetees                      : {len(rejets)}")
    print(f"Lots habitation RNC rendus visibles: {tot_lots}")
    print(f"Delta parc NET estime              : {net:+d} logements "
          f"(bati deja compte en estim. BDNB -> bascule lots RNC)")
    print("-" * 72)
    print("Injections (immat | cle | copro | bgid pick | nb_log | nlots):")
    for c, bg, cle, _lib, bgs in sorted(
            a_injecter,
            key=lambda x: -(x[0].get("nb_lots_habitation") or 0)):
        multi = f" [{len(bgs)} bgid->1]" if len(bgs) > 1 else ""
        print(f"  {c['numero_immatriculation']} | {cle:<42} | "
              f"{(c.get('nom_copropriete') or '')[:24]:<24} | "
              f"{bg['batiment_groupe_id']} | log={bg.get('nb_log')} | "
              f"nlots={c.get('nb_lots_habitation')}{multi}")
    if rejets:
        print("-" * 72)
        print("Rejets (NON injectees) :")
        for im, r in rejets:
            print(f"  {im} | {r}")
    print("-" * 72)
    print("NOTE rendu : l'adresse hors-RNC au numero de base reste un noeud")
    print("distinct (non fusionnee) ; le bati apparaitra en 2 lignes (base")
    print("'estime' a 0 lgt apres dedup + copro RNC nommee). Parc correct,")
    print("doublon VISUEL. Fusion auto optionnelle = changement separe.")
    print("=" * 72)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return

    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja (ne pas ecraser). "
              f"Le deplacer/supprimer avant --apply.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    for c, bg, cle, libelle, _bgs in a_injecter:
        adresses.append(construire_ligne(c, bg, cle, libelle))
    meta = light.setdefault("metadata", {})
    sg = meta.setdefault("stats_globales", {})
    sg["nb_adresses_croisement"] = len(adresses)
    meta["_correctif_horsrnc"] = (
        f"{len(a_injecter)} adresses injectees (copros invisibles cat. A/B2 "
        f"detectees par passe inverse hors-RNC ; lien live many-to-many ; "
        f"_bdnb_match=immat_horsrnc_fix ; delta parc ESTIME {net:+d} lgts "
        f"-- estimation approximative, valider le reel via "
        f"node scripts/test_render_secteur.js).")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(adresses)} adresses)")


if __name__ == "__main__":
    main()
