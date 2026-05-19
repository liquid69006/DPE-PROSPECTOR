"""
Correctif SURGICAL : copro RNC "39-43 RUE GUILLOUD"
(Dauphine-Lacassagne, Lyon 3e) — entree mediane 41 detachee.

Constat (diagnostic ; hors-pattern du scan paires — cf.
data/PIPELINE.md §4 FUSION_RNC_EXTRA_NUMS / §5 chaine DL) :
  - Copro DOUBLEMENT immatriculee (meme SDC, 30 lots / 75 tot) :
      * AB9349846 "SDC 39-43 RUE GUILLOUD" (2018, syndic non connu,
        adr "39-43 r guilloud", nb_compl=0)
      * AJ0217901 "LE GUILLOUD" (re-immatriculation 2025, syndic
        REGIE DU LYONNAIS, adr "39" + adresse_complementaire_1 "43")
    Le light retient l'immat COURANTE AJ0217901 @ cle 39|RUE|GUILLOUD.
  - 39 / 41 / 43 RUE GUILLOUD partagent TOUS le meme batiment BDNB
    bgid YTPJ-Q2XB-2DEF (immeuble unique, entrees collineaires, meme
    IRIS 693830604). La fusion RNC multi-numeros agrege {39,43}
    (nom "39-43" / compl "43") et CONSOMME 39 & 43 ; la fusion-bgid
    suivante ignore les adresses consommees -> 41 (entree mediane,
    JAMAIS listee au RNC) reste SEUL dans son groupe bgid (len<2) =
    non fusionne, alors qu'il porte le meme bgid que la copro.
  - Resultat : 41|RUE|GUILLOUD = adresse hors-RNC autonome
    (immat None, syndic None, _fusion_auto None ; 2 ventes
    logement / 2 ventes totales) -> apparait en "hors-RNC actif".
  - Hors-pattern du scan de paires (plage tronquee 1 voie).

Aucune copro RNC distincte au 41 (verifie) : 41 est bien une entree
de la copro 39-43, pas une copro independante.

Source-of-truth : FUSION_RNC_EXTRA_NUMS += {"AJ0217901": {41},
"AB9349846": {41}} dans make_light.py (hors depot) -- reinjection de
41 dans le GROUPE DE FUSION RNC (les deux immat par defensivite,
double immatriculation). -> regen futur correct.

Effet PARC : STRICTEMENT NEUTRE. Contrairement a Acollas, 41 partage
DEJA le bgid YTPJ-Q2XB-2DEF de la copro -> son nb_log_bdnb est deja
dedupe aux 30 lots RNC (parc compte 1x/bgid, PIPELINE 6). Fusionner
41 ne retire aucun bucket BDNB autonome. Seul effet mesurable : les
2 ventes de 41 relocalisees au rendu sous AJ0217901, et 41 sort des
"hors-RNC actifs". Ventes secteur conservees (relocalisation).

Ici (light deja patche), reproduction chirurgicale SANS regen
destructif : 41 RUE GUILLOUD devient secondaire auto de 39, miroir
EXACT du frere 43 :
  - _fusion_auto=True / _fusion_cible=39|RUE|GUILLOUD
  - syndic propage depuis le principal (REGIE DU LYONNAIS, _grp)
  - bgid / nb_log_bdnb / _bdnb_match / usage / ventes (champs
    autoritatifs) : INCHANGES dans la donnee. Au RENDU : ventes
    relocalisees sous AJ0217901, 41 sort des "hors-RNC actifs".
  - 39._fusion_auto_sources : ['43'] -> ['41','43'] ;
    _fusion_auto_label -> "39/41/43 RUE GUILLOUD".
2 enregistrements touches (41, 39). Parc inchange.

Cible : data/secteur_dauphine_lacassagne_light.json. Backup
.preguilloud.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_guilloud_range.py            # DRY-RUN
  python scripts/fix_guilloud_range.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.preguilloud.bak"
SRC_CLES = ["41|RUE|GUILLOUD"]
DST_CLE = "39|RUE|GUILLOUD"
IMMAT = "AJ0217901"            # LE GUILLOUD (= AB9349846 "39-43")


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def _lead(cle):
    m = re.match(r"\d+", cle or "")
    return int(m.group()) if m else None


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a.get("cle"): a for a in light.get("adresses", [])}
    dst = by.get(DST_CLE)
    srcs = [(k, by.get(k)) for k in SRC_CLES]

    missing = [k for k, a in srcs if not a] + ([] if dst else [DST_CLE])
    if missing:
        print(f"ABORT : adresse(s) manquante(s) : {missing}.")
        return
    cop = next((c for c in light.get("coproprietes", [])
                if c.get("cle_adresse") == DST_CLE), None)
    if not cop or cop.get("numero_immatriculation") != IMMAT:
        print(f"ABORT : copro {IMMAT} introuvable sur {DST_CLE} "
              f"(got {cop and cop.get('numero_immatriculation')}).")
        return
    # Aucune adresse ne doit etre auto-fusionnee DANS 41
    # (fusionner 41 ailleurs perdrait alors ses ventes au rendu).
    bad = [a.get("cle") for a in light["adresses"]
           if a.get("_fusion_cible") in SRC_CLES]
    if bad:
        print(f"ABORT : adresses auto-fusionnees dans 41 : {bad}.")
        return
    # Garde parc-neutre : 41 doit partager le bgid de la copro (sinon
    # l'effet ne serait plus neutre -> revue manuelle requise).
    if dst.get("batiment_groupe_id") and any(
            a.get("batiment_groupe_id") != dst.get("batiment_groupe_id")
            for _k, a in srcs):
        print(f"ABORT : un src n'a pas le bgid de {DST_CLE} "
              f"({dst.get('batiment_groupe_id')}) -> effet parc NON "
              f"neutre, revue manuelle requise.")
        return

    prop_syn = syn_ok(dst.get("syndic"))
    cur_srcs = list(dst.get("_fusion_auto_sources") or [])
    new_srcs = sorted(set(cur_srcs) | set(SRC_CLES))
    all_nums = sorted({_lead(DST_CLE)}
                      | {_lead(s) for s in new_srcs if _lead(s) is not None})
    parts = DST_CLE.split("|")
    t, nm = (parts[1], parts[2]) if len(parts) == 3 else ("", "")
    new_label = "/".join(str(n) for n in all_nums) \
        + (" " + t if t else "") + (" " + nm if nm else "")

    done = all(a.get("_fusion_auto") is True
               and a.get("_fusion_cible") == DST_CLE for _, a in srcs) \
        and set(SRC_CLES).issubset(set(cur_srcs))

    print("=" * 70)
    print("CORRECTIF SURGICAL — 41 RUE GUILLOUD -> copro AJ0217901 "
          "(parc-neutre : bgid deja commun)")
    print("=" * 70)
    print(f"Mode                 : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Deja applique        : {done}")
    print(f"Copro cible          : {cop.get('nom_copropriete')} "
          f"({IMMAT}) — {cop.get('nb_lots_habitation')} lots — "
          f"syndic {cop.get('syndic')}")
    print(f"bgid copro           : {dst.get('batiment_groupe_id')}")
    print("-" * 70)
    for k, a in srcs:
        print(f"src {k}  AVANT :")
        print(f"  bgid={a.get('batiment_groupe_id')} "
              f"_bdnb_match={a.get('_bdnb_match')} "
              f"nb_log_bdnb={a.get('nb_log_bdnb')} "
              f"usage={a.get('usage_principal_bdnb')!r}")
        print(f"  syndic={a.get('syndic')!r} "
              f"_fusion_auto={a.get('_fusion_auto')} "
              f"_fusion_cible={a.get('_fusion_cible')} "
              f"nb_ventes_total={a.get('nb_ventes_total')} "
              f"nb_ventes_logement={a.get('nb_ventes_logement')}")
    print("Transformation (miroir fusion RNC multi-n°, comme frere 43) :")
    print(f"  champs autoritatifs (bgid/nb_log_bdnb/_bdnb_match/usage) "
          f"-> INCHANGES")
    print(f"  _fusion_auto/cible  -> True / {DST_CLE}")
    print(f"  syndic              -> {dst.get('syndic')!r} "
          f"{'(propage _grp)' if prop_syn else '(NON propage)'}")
    print(f"  ventes              : CONSERVEES (relocalisees au rendu "
          f"sous {IMMAT} ; 41 sort des hors-RNC actifs)")
    print(f"  parc                : STRICTEMENT INCHANGE (41 deja meme "
          f"bgid que la copro -> deja dedupe aux lots RNC)")
    print(f"  39._fusion_auto_sources : {cur_srcs} -> {new_srcs}")
    print(f"  39._fusion_auto_label   : "
          f"{dst.get('_fusion_auto_label')!r} -> {new_label!r}")
    print("=" * 70)

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

    for _k, a in srcs:
        a["_fusion_auto"] = True
        a["_fusion_cible"] = DST_CLE
        if prop_syn and not syn_ok(a.get("syndic")):
            a["syndic"] = dst.get("syndic")
            a["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"
        # bgid / nb_log_bdnb / _bdnb_match / usage / ventes : INTACTS.

    dst["_fusion_auto_sources"] = new_srcs
    dst["_fusion_auto_label"] = new_label

    meta = light.setdefault("metadata", {})
    meta["_correctif_guilloud"] = (
        "Copro RNC '39-43 RUE GUILLOUD' (30 lots), doublement "
        "immatriculee AB9349846 (2018) / AJ0217901 'LE GUILLOUD' "
        "(re-immat 2025, REGIE DU LYONNAIS ; light retient AJ0217901 "
        "@ cle 39). 39/41/43 partagent le bgid YTPJ-Q2XB-2DEF ; la "
        "fusion RNC agrege {39,43} (nom/compl) et consomme les bornes, "
        "laissant 41 (entree mediane jamais listee au RNC) isole. 41 "
        "RUE GUILLOUD rattachee chirurgicalement comme secondaire auto "
        "de 39 (miroir exact du frere 43) : champs autoritatifs "
        "(bgid/nb_log_bdnb/_bdnb_match/usage/ventes) INCHANGES. Au "
        "rendu : 2 ventes (2 strictes) relocalisees sous AJ0217901, "
        "41 sort des 'hors-RNC actifs'. PARC STRICTEMENT INCHANGE "
        "(41 partage deja le bgid de la copro -> deja dedupe aux 30 "
        "lots RNC, PIPELINE 6). 39._fusion_auto_sources -> ['41','43'], "
        "label '39/41/43 RUE GUILLOUD'. Source-of-truth = "
        "FUSION_RNC_EXTRA_NUMS dans make_light.py. 2 enregistrements "
        "touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (41 RUE GUILLOUD -> secondaire de "
          f"{DST_CLE} ; ventes relocalisees ; parc strictement "
          f"inchange)")


if __name__ == "__main__":
    main()
