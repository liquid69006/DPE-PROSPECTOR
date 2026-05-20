"""
Correctif SURGICAL — Etiquetage multi-voies de `16 RUE VIOLET` pour
exposer la facade BAN `1 VILLA DE GRENELLE` (meme bgid, meme
parcelle). Confirmation terrain user 2026-05-20 ("1 villa de grenelle
/ 16 rue violet = une seule copropriete").

Pattern IDENTIQUE a fix_clouet_garibaldi_label.py (commit 148089d) :
hors-RNC native sans copro RNC, ETIQUETAGE pur via
`_fusion_auto_label` sans sources.

Constat (diagnostic complet) :
  - BDNB pivot bgid `9PX4-LE3D-RT3Q` : `l_libelle_adr` = ['16 Rue
    Violet' (principal), '1 villa de grenelle']. MEME parcelle
    75115000DJ0089, annee_construction 1920, classe F, gaz, type
    "immeuble", 7 nb_log_bdnb.
  - DVF section DJ plan 89 : 9 lignes le 04/10/2022 a "16 RUE
    VIOLET" pour 1 000 000 EUR = mutation collective unique (6 appts
    + 3 dependances). 0 vente DVF a "1 villa de grenelle" / "1 vla
    de grenelle".
  - MAJIC : SCI VIOLET (SIREN 913995643) sci_proprietaire=oui :
    mono-propriete vendue en bloc 2022, copro de fait en formation
    (ou nouveau proprietaire unique).
  - RNC live exhaustif :
      * Rue Violet 75015 : 34 copros recensees (4B a 65 + Villa
        Violet 1-3) - AUCUNE au n° 16 seul.
      * Villa de Grenelle 75015 : SEULEMENT AI7174394 au 2 Villa
        de Grenelle (17 lots, mandat expire sans successeur)
        - AUCUNE au 1 Villa de Grenelle.
      * Aucun compl RNC ne reference "16 r violet" ni "villa de
        grenelle".
  - Cache `_horsrnc_bdnb_live_motte_picquet[9PX4]` = {'immats': [],
    'meta': {}} : zero copro RNC pour ce bati.

Conclusion : Bati hors-RNC reel, mono-propriete SCI sortante.
Correctement classe "Hors-RNC actif" (taux 2.9 % "Actif") dans le
rendu actuel. Aucune copro a injecter, aucune ancre a re-pointer.

Anomalie minore : le rendu n'expose pas la facade BAN secondaire
"1 VILLA DE GRENELLE", invisible pour le terrain commercial.

Mecanisme : ajouter `_fusion_auto_label = "16 RUE VIOLET / 1 VILLA
DE GRENELLE"` sur 16|RUE|VIOLET (`_fusion_auto_sources=None`,
pattern existant). Le rendu (index.html L2305 dispNom) pickup ce
label en priorite sur l'adresse seule.

Effet parc : STRICTEMENT NEUTRE.

Source-of-truth a porter dans `make_light_motte_picquet.py` :
  - ALIAS_RNC += { "1|VILLA|DE GRENELLE": "16|RUE|VIOLET" }
    (re-router toute future vente DVF a "1 vla de grenelle").

Cible : data/secteur_motte_picquet_light.json. Backup .previolet.bak.
Dry-run par defaut.

Usage :
  python scripts/fix_violet_grenelle_label.py            # DRY-RUN
  python scripts/fix_violet_grenelle_label.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.previolet.bak"

ANCHOR = "16|RUE|VIOLET"
BGID = "bdnb-bg-9PX4-LE3D-RT3Q"
NEW_LABEL = "16 RUE VIOLET / 1 VILLA DE GRENELLE"
ABSENT_FACADE = "1 VILLA DE GRENELLE"


def parc_model(light):
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
        abort.append(f"ancre {ANCHOR} fusionnee")
    if cbc.get(ANCHOR):
        abort.append(f"ancre {ANCHOR} a une copro RNC "
                     f"({cbc[ANCHOR].get('numero_immatriculation')}) "
                     "- diagnostic obsolete, revoir RNC")
    if a and a.get("numero_immatriculation"):
        abort.append(f"ancre {ANCHOR} a un immat "
                     f"({a.get('numero_immatriculation')}) - "
                     "diagnostic obsolete")
    # Garde : 1|VILLA DE GRENELLE ne doit pas exister dans le light
    # (sinon vrai re-point necessaire, pas un simple label)
    if by.get("1|VILLA|DE GRENELLE") or by.get("1||VILLA DE GRENELLE"):
        abort.append("1|VILLA DE GRENELLE present dans le light : "
                     "utiliser un VRAI re-point au lieu d'un label seul")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pa = next((x for x in patched["adresses"]
               if x["cle"] == ANCHOR), None)

    already = (pa is not None
               and pa.get("_fusion_auto_label") == NEW_LABEL)
    if pa is not None and not already:
        pa["_fusion_auto_label"] = NEW_LABEL

    parc1 = parc_model(patched)

    print("=" * 76)
    print(f"FIX VIOLET/VILLA GRENELLE (etiquetage multi-voies) — "
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
        print("ABORT : parc NON neutre.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_violet_grenelle_label"] = (
        "16 RUE VIOLET : ajout label multi-voies "
        f"{NEW_LABEL!r} (rendu dispNom). Facade BAN '1 VILLA DE "
        "GRENELLE' documentee comme appartenant au MEME bati BDNB "
        f"(bgid {BGID}, parcelle 75115000DJ0089, annee 1920, 7 "
        "lgts). Aucune copro RNC pour ce bati (verifie snapshot + "
        "RNC live exhaustif Rue Violet/Villa de Grenelle 75015 - "
        "SCI VIOLET 913995643 mono-propriete vendue en bloc "
        "04/10/2022 1 M EUR collective). Pattern IDENTIQUE a "
        "Clouet/Garibaldi (commit 148089d). Parc STRICTEMENT "
        "NEUTRE. Source-of-truth a porter dans "
        "make_light_motte_picquet.py : ALIAS_RNC += "
        "{'1|VILLA|DE GRENELLE': '16|RUE|VIOLET'} pour re-router "
        "future vente DVF a '1 vla de grenelle'.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (label sur {ANCHOR})")


if __name__ == "__main__":
    main()
