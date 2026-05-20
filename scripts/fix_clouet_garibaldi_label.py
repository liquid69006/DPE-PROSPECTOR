"""
Correctif SURGICAL — Etiquetage multi-voies de `26 BOULEVARD GARIBALDI`
pour exposer la facade BAN `1 RUE CLOUET` (meme bgid, meme parcelle).
Confirmation terrain user 2026-05-20 ("1 r clouet / 26 bd garibaldi
= une seule copropriete").

Constat (diagnostic complet) :
  - BDNB pivot bgid `PNXA-8DRE-F4GM` : `l_libelle_adr` = ['26 Boulevard
    Garibaldi', '1 rue clouet'] = MEME bati BAN, parcelle 75115000CX0067,
    annee_construction 1850, nb_log_bdnb=15, classe G electricite.
  - DVF section CX plan 67 : 9 mutations 2021-2024 toutes a "26 BD
    GARIBALDI" (0 a "1 r clouet" - facade non-postale).
  - MAJIC : SCI CROCO (SIREN 490030913) sci_proprietaire=oui, sortie
    progressive par ventes (6 vlog + 1 v_local en 4 ans).
  - RNC live exhaustif (75015) :
      * Rue Clouet : 9 copros recensees aux numeros 2, 9, 11, 12, 13,
        14, 16, 18 (2x) - AUCUNE au 1, 3, 5, 7.
      * Bd Garibaldi 22-30 : copros 22(/24), 23, 27, 28(/26), 28, 30
        - AUCUNE au 26 seul.
      * AD5922125 "SDC 26/28 BD GARIBALDI" (3 lots) : copro residuelle
        d'un ancien decoupage, ancree sur 28 (parcelle CX0054), n'a
        plus de mandat depuis 2025-12-31, NE COUVRE PAS le bati du 26
        (parcelle CX0067).
  - Cache `_horsrnc_bdnb_live_motte_picquet[PNXA]` = {'immats': [],
    'meta': {}} : confirme zero copro RNC.

Conclusion : Bati hors-RNC reel (SCI sortante en copro de fait, non
immatriculee). Le filtre Hors-RNC actifs catalogue deja correctement
26 BD GARIBALDI (taux 8 % "Tres actif"). Aucune copro a injecter,
aucune ancre a re-pointer.

Anomalie minore : le rendu n'expose pas la facade BAN secondaire
"1 RUE CLOUET", invisible pour le terrain commercial.

Mecanisme : ajouter `_fusion_auto_label = "26 BD GARIBALDI / 1 RUE
CLOUET"` sur 26|BOULEVARD|GARIBALDI (`_fusion_auto_sources=None`,
pattern existant Fremicourt/ARMONIAL pour les labels informatifs
sans absorption). Le rendu pickup ce label en priorite sur l'adresse
seule (cf. index.html L2305-2308 dispNom).

Effet parc : STRICTEMENT NEUTRE (aucun champ data modifie, juste un
libelle d'affichage). Test : `parc_model` AVANT == APRES.

Source-of-truth a porter dans `make_light_motte_picquet.py` :
  - ALIAS_RNC += { "1|RUE|CLOUET": "26|BOULEVARD|GARIBALDI" }
    (pour re-router toute future vente DVF a "1 r clouet").

Cible : data/secteur_motte_picquet_light.json. Backup .preclouet.bak.
Dry-run par defaut.

Usage :
  python scripts/fix_clouet_garibaldi_label.py            # DRY-RUN
  python scripts/fix_clouet_garibaldi_label.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.preclouet.bak"

ANCHOR = "26|BOULEVARD|GARIBALDI"
BGID = "bdnb-bg-PNXA-8DRE-F4GM"
NEW_LABEL = "26 BD GARIBALDI / 1 RUE CLOUET"
ABSENT_FACADE = "1 RUE CLOUET"        # facade BAN non-postale, pas dans light


def parc_model(light):
    """Replique renderSecteur Sec 6 : dedup bgid, lots RNC prioritaires
    sinon nb_log_bdnb si bati residentiel."""
    ad = light["adresses"]
    co = {c["cle_adresse"]: c for c in light["coproprietes"]
          if c.get("cle_adresse")}
    RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    bgRncLots, bgBdnb, immatBg = {}, {}, {}
    for a in ad:
        if a["cle"] in fused:
            continue
        bg = a.get("batiment_groupe_id")
        cp = co.get(a["cle"])
        if bg and cp and (cp.get("nb_lots_habitation") or 0) > 0:
            im = cp.get("numero_immatriculation") or cp["cle_adresse"]
            immatBg.setdefault(im, bg)
            bgRncLots.setdefault(immatBg[im], {})[im] = \
                cp["nb_lots_habitation"]
        if bg and not cp and a.get("usage_principal_bdnb") in RESID \
                and (a.get("nb_log_bdnb") or 0) > 0 and bg not in bgBdnb:
            bgBdnb[bg] = a["nb_log_bdnb"]
    parc = 0
    for bg in set(bgRncLots) | set(bgBdnb):
        parc += (sum(bgRncLots[bg].values()) if bg in bgRncLots
                 else bgBdnb.get(bg, 0))
    return parc


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    abort = []
    a = by.get(ANCHOR)
    if a is None:
        abort.append(f"ancre absente : {ANCHOR}")
    elif a.get("batiment_groupe_id") != BGID:
        abort.append(f"bgid divergent : {ANCHOR} "
                     f"{a.get('batiment_groupe_id')} != {BGID}")
    if a and a.get("_fusion_auto") and a.get("_fusion_cible"):
        abort.append(f"ancre {ANCHOR} fusionnee (-> "
                     f"{a.get('_fusion_cible')})")
    # garde : confirmer que cette adresse est BIEN hors-RNC (sinon
    # le diagnostic n'est plus valide)
    if cbc.get(ANCHOR):
        abort.append(f"ancre {ANCHOR} a une copro RNC "
                     f"({cbc[ANCHOR].get('numero_immatriculation')}) "
                     "- diagnostic obsolete, revoir RNC")
    if a and a.get("numero_immatriculation"):
        abort.append(f"ancre {ANCHOR} a un immat "
                     f"({a.get('numero_immatriculation')}) - "
                     "diagnostic obsolete")
    # garde : 1 RUE CLOUET ne doit pas exister dans le light
    # (sinon il faudrait un VRAI re-point, pas juste un label)
    if by.get("1|RUE|CLOUET"):
        abort.append("1|RUE|CLOUET present dans le light : "
                     "utiliser un VRAI re-point (pattern Fremicourt) "
                     "au lieu de ce simple label")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pa = patched["adresses"][[i for i, x in enumerate(
        patched["adresses"]) if x["cle"] == ANCHOR][0]] if a else None

    # idempotence
    already = (pa is not None
               and pa.get("_fusion_auto_label") == NEW_LABEL)

    if pa is not None and not already:
        pa["_fusion_auto_label"] = NEW_LABEL
        # _fusion_auto_sources reste None (label informatif, cf.
        # pattern "27|RUE|FREMICOURT" / "4|RUE|GAL DE CASTELNAU")

    parc1 = parc_model(patched)

    print("=" * 76)
    print(f"FIX CLOUET/GARIBALDI (etiquetage multi-voies) — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 76)
    print(f"  ANCHOR        : {ANCHOR}  bgid={BGID}")
    print(f"  Etat actuel   : immat={a and a.get('numero_immatriculation')!r}"
          f"  syndic={a and a.get('syndic')!r}"
          f"  SCI={a and a.get('sci_nom')!r}")
    print(f"  nb_log_bdnb   : {a and a.get('nb_log_bdnb')}  "
          f"v_log={a and a.get('nb_ventes_logement')}  "
          f"classement={a and a.get('classement_rotation_logement')!r}")
    print(f"  Facade BAN    : '{ABSENT_FACADE}' (absente du light, "
          "0 vente DVF, non-postale)")
    print(f"  Label avant   : {a and a.get('_fusion_auto_label')!r}")
    print(f"  Label apres   : {NEW_LABEL!r}")
    print(f"  Sources       : None (label informatif, pas d'absorption)")
    print(f"  Idempotent    : {already}")
    print("-" * 76)
    print(f"Parc modele MP : {parc0} -> {parc1} "
          f"(delta {parc1-parc0:+d}, neutre={parc0==parc1})")
    print("=" * 76)

    if abort:
        print("ABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie.")
        return
    if already:
        print("Idempotent : deja applique.")
        return
    if parc0 != parc1:
        print("ABORT : parc NON neutre - le label n'est pas cense "
              "modifier le parc !")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_clouet_garibaldi_label"] = (
        "26 BOULEVARD GARIBALDI : ajout label multi-voies "
        f"{NEW_LABEL!r} (rendu dispNom). Facade BAN '1 RUE CLOUET' "
        "documentee comme appartenant au MEME bati BDNB (bgid "
        f"{BGID}, parcelle 75115000CX0067, annee 1850, 15 lgts). "
        "Aucune copro RNC pour ce bati (verifie snapshot + RNC "
        "live exhaustif Rue Clouet/Bd Garibaldi 75015 - SCI CROCO "
        "490030913 en sortie progressive, copro de fait non "
        "immatriculee). Parc STRICTEMENT NEUTRE. Source-of-truth "
        "a porter dans make_light_motte_picquet.py : "
        "ALIAS_RNC += {'1|RUE|CLOUET': '26|BOULEVARD|GARIBALDI'} "
        "pour re-router toute future vente DVF a '1 r clouet'.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (label sur {ANCHOR})")


if __name__ == "__main__":
    main()
