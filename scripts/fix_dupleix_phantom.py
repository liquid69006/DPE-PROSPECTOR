"""
Correctif SURGICAL : adresse DVF fantome "28 RUE DUPLEIX" (Motte-Picquet).

Meme pattern que 10 RUE MEYNIS (cf. fix_meynis_phantom.py,
data/audit_paires_suspects.md) :
  - 28 RUE DUPLEIX : BAN reelle "35 rue Dupleix", parcelle DH0005,
    bgid ZW4Z-VEGN-9VF8 = bati TERTIAIRE, aucune copro, nb_log_bdnb=1.
    Porte 4 ventes DVF (4 strictes).
  - 28 PLACE DUPLEIX : parcelle DJ0018, bgid XRWJ-DP78-FV1D, copro
    RNC AA9462284 "28 PLACE ET RUE DUPLEIX" (36 lots) -> le nom de la
    copro couvre explicitement les 2 voies ; 3 ventes propres.
  -> DVF enregistre 4 mutations de la copro a l'adresse cadastrale
     "28 rue Dupleix" ; l'entree RNC est "28 place Dupleix". bgid
     differents + cle RUE != PLACE + aucun immat sur l'adresse DVF
     -> 2 lignes separees, 4 ventes orphelines (28 RUE=Tertiaire ->
     0 logement depuis la bascule usage).

Source-of-truth : ALIAS_RNC += {"28|RUE|DUPLEIX":"28|PLACE|DUPLEIX"}
dans make_light.py (hors depot) + critere copro_by_cle ajoute au tri
de la principale de fusion-bgid (la copro a syndic "non connu" & moins
de ventes que le fantome : sans ce critere la regen prendrait le
fantome comme principale). -> regen futur correct.

Ici (light deja patche), reproduction chirurgicale SANS regen
destructif : 28 RUE DUPLEIX devient secondaire auto de 28 PLACE
DUPLEIX (AA9462284). Ses 4 ventes relocalisees au rendu (28 PLACE
affichera 3 propres + 4 = 7). Parc inchange (28 RUE etait
Tertiaire->0 ; copro deja comptee 36 lots). 2 enregistrements.

Cible : data/secteur_motte_picquet_light.json. Backup
.predupleix.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_dupleix_phantom.py            # DRY-RUN
  python scripts/fix_dupleix_phantom.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.predupleix.bak"
SRC_CLE = "28|RUE|DUPLEIX"
DST_CLE = "28|PLACE|DUPLEIX"
IMMAT = "AA9462284"            # 28 PLACE ET RUE DUPLEIX


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


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
    if any(a.get("_fusion_cible") == SRC_CLE for a in light["adresses"]):
        print(f"ABORT : une adresse est auto-fusionnee DANS {SRC_CLE} "
              f"(fusionner perdrait ses ventes).")
        return
    already = (src.get("_fusion_auto") is True
               and src.get("_fusion_cible") == DST_CLE)

    print("=" * 70)
    print("CORRECTIF SURGICAL — 28 RUE DUPLEIX (DVF fantome -> copro "
          "AA9462284)")
    print("=" * 70)
    print(f"Mode                 : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Deja applique        : {already}")
    print(f"Copro cible          : {cop.get('nom_copropriete')} "
          f"({IMMAT}) — {cop.get('nb_lots_habitation')} lots — "
          f"syndic {cop.get('syndic')}")
    print("-" * 70)
    print("src 28 RUE DUPLEIX  AVANT :")
    print(f"  bgid={src.get('batiment_groupe_id')} "
          f"_bdnb_match={src.get('_bdnb_match')} "
          f"usage={src.get('usage_principal_bdnb')} "
          f"nb_log_bdnb={src.get('nb_log_bdnb')} "
          f"syndic={src.get('syndic')}")
    print(f"  _fusion_auto={src.get('_fusion_auto')} "
          f"_fusion_cible={src.get('_fusion_cible')} "
          f"nb_ventes_total={src.get('nb_ventes_total')} "
          f"nb_ventes_logement={src.get('nb_ventes_logement')}")
    prop_syn = syn_ok(dst.get("syndic"))
    print("Transformation (miroir make_light + ALIAS_RNC) :")
    print(f"  bgid                -> {dst.get('batiment_groupe_id')}")
    print(f"  _bdnb_match         -> immat")
    print(f"  usage_principal_bdnb-> {dst.get('usage_principal_bdnb')}")
    print(f"  nb_log_bdnb         -> {dst.get('nb_log_bdnb')}")
    print(f"  syndic              -> {dst.get('syndic')!r} "
          f"{'(propage)' if prop_syn else '(NON propage : non connu)'}")
    print(f"  _fusion_auto/cible  -> True / {DST_CLE}")
    print(f"  ventes (DVF) src    : INCHANGEES (relocalisees au rendu ; "
          f"28 PLACE = {dst.get('nb_ventes_logement')}+"
          f"{src.get('nb_ventes_logement')})")
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

    src["batiment_groupe_id"] = dst.get("batiment_groupe_id")
    src["_bdnb_match"] = "immat"
    src["nb_log_bdnb"] = dst.get("nb_log_bdnb")
    src["usage_principal_bdnb"] = dst.get("usage_principal_bdnb")
    src["_usage_bdnb_src"] = dst.get("_usage_bdnb_src") or "snapshot"
    src["annee_construction"] = dst.get("annee_construction")
    src["classe_dpe"] = dst.get("classe_dpe")
    src["type_batiment"] = dst.get("type_batiment")
    src["type_chauffage"] = dst.get("type_chauffage")
    if prop_syn:                       # idem make_light : seulement si syn_ok
        src["syndic"] = dst.get("syndic")
        src["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"
    src["_fusion_auto"] = True
    src["_fusion_cible"] = DST_CLE

    srcs = list(dst.get("_fusion_auto_sources") or [])
    if SRC_CLE not in srcs:
        srcs.append(SRC_CLE)
    dst["_fusion_auto_sources"] = sorted(set(srcs))
    dst.setdefault("_fusion_auto_label", None)

    meta = light.setdefault("metadata", {})
    meta["_correctif_dupleix"] = (
        "Adresse DVF fantome 28 RUE DUPLEIX (BAN '35 rue Dupleix', "
        "parcelle DH0005, bati tertiaire) rattachee chirurgicalement a "
        "la copro AA9462284 '28 PLACE ET RUE DUPLEIX' @ 28 PLACE DUPLEIX "
        "(parcelle DJ0018, bgid XRWJ-DP78-FV1D) : _fusion_auto -> "
        "28|PLACE|DUPLEIX, ses 4 ventes DVF (4 strictes) relocalisees au "
        "rendu (28 PLACE : 3 propres + 4 = 7). Source-of-truth = "
        "ALIAS_RNC + critere copro_by_cle du tri fusion dans "
        "make_light.py. Parc inchange. 2 enregistrements touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (28|RUE|DUPLEIX -> secondaire de "
          f"28|PLACE|DUPLEIX ; ventes relocalisees au rendu)")


if __name__ == "__main__":
    main()
