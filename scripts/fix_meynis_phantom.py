"""
Correctif SURGICAL : adresse DVF fantome "10 RUE MEYNIS".

Diagnostic (cf. ETAPE 1/2) :
  - 10 RUE MEYNIS : parcelle DN0005, bgid GFKS-DC3T-CRB1 = bati
    TERTIAIRE (adresse BAN reelle "7 Rue Meynis"), aucune copro,
    nb_log_bdnb null. Porte pourtant 10 ventes DVF (7 strictes).
  - 10 PASSAGE MEYNIS : parcelle DT0052, bgid WDLN-W7EH-5BGA,
    copro RNC RESIDENCE PAULINE AA8066532 (27 lots), 0 vente.
  -> DVF enregistre les mutations de la copro a l'adresse cadastrale
     "10 rue Meynis" ; l'entree postale reelle est "10 passage
     Meynis". bgid differents + cle RUE != PASSAGE + aucun immat sur
     l'adresse DVF => ni la fusion-bgid ni la jointure RNC ne les
     relient -> 2 lignes separees, ventes orphelines (et depuis la
     bascule usage, 10 RUE MEYNIS=Tertiaire -> 0 logement).

Correctif source-of-truth : ALIAS_RNC += {"10|RUE|MEYNIS":
"10|PASSAGE|MEYNIS"} dans make_light.py (hors depot) -> au prochain
regen complet, l'alias resout la copro -> jointure BDNB par immat ->
meme bgid que 10 PASSAGE MEYNIS -> fusion auto.

Ici (light deja patche par les correctifs additifs : usage_bdnb,
taux_logement, hors-RNC...), on REPRODUIT chirurgicalement le
resultat make_light SANS regen destructif : 10 RUE MEYNIS devient
secondaire auto de 10 PASSAGE MEYNIS (RESIDENCE PAULINE). Ses ventes
sont relocalisees par renderSecteur (autoMerged) ; parc inchange
(10 RUE MEYNIS etait Tertiaire->0, RESIDENCE PAULINE deja comptee
27 lots). Aucun autre enregistrement modifie.

Cible : data/secteur_dauphine_lacassagne_light.json. Backup
.premeynis.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_meynis_phantom.py            # DRY-RUN
  python scripts/fix_meynis_phantom.py --apply
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.premeynis.bak"
SRC_CLE = "10|RUE|MEYNIS"
DST_CLE = "10|PASSAGE|MEYNIS"
IMMAT = "AA8066532"            # RESIDENCE PAULINE


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a.get("cle"): a for a in light.get("adresses", [])}
    src, dst = by.get(SRC_CLE), by.get(DST_CLE)

    if not src or not dst:
        print(f"ABORT : adresse manquante (src={bool(src)} dst={bool(dst)}).")
        return
    cop = next((c for c in light.get("coproprietes", [])
                if c.get("cle_adresse") == DST_CLE), None)
    if not cop or cop.get("numero_immatriculation") != IMMAT:
        print(f"ABORT : copro {IMMAT} introuvable sur {DST_CLE} "
              f"(got {cop and cop.get('numero_immatriculation')}).")
        return
    already = (src.get("_fusion_auto") is True
               and src.get("_fusion_cible") == DST_CLE)

    # Etat AVANT
    print("=" * 70)
    print("CORRECTIF SURGICAL — 10 RUE MEYNIS (DVF fantome -> RESIDENCE "
          "PAULINE)")
    print("=" * 70)
    print(f"Mode                 : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Deja applique        : {already}")
    print(f"Copro cible          : {cop.get('nom_copropriete')} "
          f"({IMMAT}) — {cop.get('nb_lots_habitation')} lots — "
          f"syndic {cop.get('syndic')}")
    print("-" * 70)
    print("src 10 RUE MEYNIS  AVANT :")
    print(f"  bgid={src.get('batiment_groupe_id')} "
          f"_bdnb_match={src.get('_bdnb_match')} "
          f"usage={src.get('usage_principal_bdnb')} "
          f"nb_log_bdnb={src.get('nb_log_bdnb')} "
          f"syndic={src.get('syndic')}")
    print(f"  _fusion_auto={src.get('_fusion_auto')} "
          f"_fusion_cible={src.get('_fusion_cible')} "
          f"nb_ventes_total={src.get('nb_ventes_total')} "
          f"nb_ventes_logement={src.get('nb_ventes_logement')}")
    print("Transformation (mirroir make_light + ALIAS_RNC) :")
    print(f"  bgid                -> {dst.get('batiment_groupe_id')}")
    print(f"  _bdnb_match         -> immat")
    print(f"  usage_principal_bdnb-> {dst.get('usage_principal_bdnb')}")
    print(f"  nb_log_bdnb         -> {dst.get('nb_log_bdnb')}")
    print(f"  syndic              -> {dst.get('syndic')} (_syndic_src "
          f"rnc_grp)")
    print(f"  _fusion_auto/cible  -> True / {DST_CLE}")
    print(f"  ventes (DVF) src    : INCHANGEES (relocalisees au rendu)")
    print(f"  dst._fusion_auto_sources -> ['{SRC_CLE}']")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if already:
        print("ABORT : correctif deja applique (idempotent).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    # src : rattache au bati residentiel de la copro + secondaire auto
    src["batiment_groupe_id"] = dst.get("batiment_groupe_id")
    src["_bdnb_match"] = "immat"
    src["nb_log_bdnb"] = dst.get("nb_log_bdnb")
    src["usage_principal_bdnb"] = dst.get("usage_principal_bdnb")
    src["_usage_bdnb_src"] = dst.get("_usage_bdnb_src") or "snapshot"
    src["annee_construction"] = dst.get("annee_construction")
    src["classe_dpe"] = dst.get("classe_dpe")
    src["type_batiment"] = dst.get("type_batiment")
    src["type_chauffage"] = dst.get("type_chauffage")
    src["syndic"] = dst.get("syndic")
    src["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"
    src["_fusion_auto"] = True
    src["_fusion_cible"] = DST_CLE

    # dst (principal) : declare la source fusionnee (RUE != PASSAGE ->
    # _fusion_auto_label None, idem make_light same_street=False)
    srcs = list(dst.get("_fusion_auto_sources") or [])
    if SRC_CLE not in srcs:
        srcs.append(SRC_CLE)
    dst["_fusion_auto_sources"] = sorted(set(srcs))
    dst.setdefault("_fusion_auto_label", None)

    meta = light.setdefault("metadata", {})
    meta["_correctif_meynis"] = (
        "Adresse DVF fantome 10 RUE MEYNIS (parcelle DN0005, bati "
        "tertiaire) rattachee chirurgicalement a la copro RESIDENCE "
        "PAULINE AA8066532 @ 10 PASSAGE MEYNIS (parcelle DT0052, bgid "
        "WDLN-W7EH-5BGA) : _fusion_auto -> 10|PASSAGE|MEYNIS, ses 10 "
        "ventes DVF (7 strictes) relocalisees au rendu. Source-of-truth "
        "= ALIAS_RNC dans make_light.py. Parc inchange (src etait "
        "Tertiaire->0 ; copro deja comptee 27 lots). 2 enregistrements "
        "touches, aucun autre champ modifie.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (10|RUE|MEYNIS -> secondaire de "
          f"10|PASSAGE|MEYNIS ; ventes relocalisees au rendu)")


if __name__ == "__main__":
    main()
