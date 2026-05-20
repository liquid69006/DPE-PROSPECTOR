"""
Correctif SURGICAL — `91 RUE FONDARY -> 40 RUE DE LA CROIX NIVERT`
(AB9273434 SDC 40/42 RUE DE LA CROIX NIVERT, 17 lots hab / 28 tot,
FOREST GESTION). Confirmation terrain user 2026-05-20 ("91 r fondary
/ 42 r croix nivert = une seule copro").

Triple confirmation source-of-truth :
  - RNC live AB9273434 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='SDC 40/42 RUE DE LA CROIX NIVERT'`
    (declaratif des 2 voies),
    `adresse_reference='40 r de la croix nivert'`,
    `adresse_complementaire_1='91 r fondary 75015 Paris'`
    (LA reference explicite),
    `reference_cadastrale_1=75056115DF0112` (= parcelle DF0112 =
    bgid DN3P = 91 FONDARY + 42 CN),
    `reference_cadastrale_2=75056115DF0111` (= parcelle DF0111 =
    bgid STYB = 40 CN). 17 lots hab / 28 tot. Syndic FOREST
    GESTION (SIRET 88204640200013), mandat -> 2026-06-30,
    date_immat 2018-01-11, derniere maj 2025-12-27.
  - BDNB pivot : bgid STYB-453N-Y18X = [40 Rue De La Croix Nivert]
    (1 facade BAN, parcelle DF0111, annee 1880) ; bgid
    DN3P-4R65-2XG2 = [42 Rue De La Croix Nivert, 91 Rue Fondary]
    (2 facades BAN, parcelle DF0112, annee 1900).
  - BDNB enrich : bgid STYB nb_log=8 / nb_log_rnc=17 matche
    AB9273434 ; bgid DN3P nb_log=4 / nb_log_rnc=None
    (manquant, mais MEME copro RNC via parcelle declaree).

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `40|RUE|CROIX NIVERT` bgid=STYB immat=AB9273434 17 lots
    (principal OK).
  - `91|RUE|FONDARY` bgid=DN3P (parcelle differente DF0112)
    immat=None nb_log_bdnb=4 vlog=1 (2024) _fusion_auto=None
    adresse=None : make_light n'a pas fusionne (voies differentes
    + 2 parcelles distinctes). Pattern Fremicourt/ARMONIAL :
    ALIAS_RNC multi-voies manquant pour la paire FONDARY <->
    CROIX NIVERT.
  - `42 RUE DE LA CROIX NIVERT` : ABSENTE du light (BAN
    secondaire, 0 vente DVF). Source-of-truth ALIAS_RNC dans
    make_light_motte_picquet.py.

Mecanisme : ALIAS_RNC multi-voies (Fremicourt). 91|RUE|FONDARY
devient secondaire auto de 40|RUE|CROIX NIVERT avec adoption
MIRROR (bgid STYB + nb_log_bdnb=8 + champs BDNB autoritatifs de
l'ancre + syndic FOREST GESTION propage rnc_grp).

Effet parc (modele renderSecteur Sec 6) :
  - bgid STYB : 17 lots (RNC AB9273434, inchange).
  - bgid DN3P : seule adresse non-fusee residentielle (91 FONDARY)
    devient fusee -> bucket bgBdnb perd DN3P (4 lgts).
  - Parc MP : -4 net = dedup multi-bgid type ARMONIAL/Cambronne
    (les 4 BDNB de DN3P etaient deja compris dans les 17 lots
    RNC qui couvrent STYB+DN3P, PIPELINE Sec 6 lots RNC
    prioritaires).
  - Hors-RNC actifs : 91 FONDARY (taux 5 % "Tres actif") sort
    -> 1 adresse / 4 lgts en moins.
  - 1 v_log + 1 v_tot (2024) de 91 FONDARY relocalisees sous
    AB9273434 (FOREST GESTION).

Source-of-truth a porter dans `make_light_motte_picquet.py` :
  - ALIAS_RNC += { "91|RUE|FONDARY": "40|RUE|CROIX NIVERT",
                    "42|RUE|CROIX NIVERT": "40|RUE|CROIX NIVERT" }

Cible : data/secteur_motte_picquet_light.json. Backup
.prefondary.bak. Dry-run par defaut.

Usage :
  python scripts/fix_fondary_croixnivert.py            # DRY-RUN
  python scripts/fix_fondary_croixnivert.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prefondary.bak"

ANCHOR = "40|RUE|CROIX NIVERT"
IMMAT = "AB9273434"
ORPHS = ["91|RUE|FONDARY"]

MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


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
    contrib = {}
    for bg in set(bgRncLots) | set(bgBdnb):
        v = (sum(bgRncLots[bg].values()) if bg in bgRncLots
             else bgBdnb.get(bg, 0))
        parc += v
        contrib[bg] = (v, "RNC" if bg in bgRncLots else "BDNB")
    return parc, contrib


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    da = by.get(ANCHOR)
    cp = cbc.get(ANCHOR)
    abort = []
    if da is None:
        abort.append(f"ancre absente : {ANCHOR}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANCHOR} "
                     f"(got {cp and cp.get('numero_immatriculation')})")
    if da and da.get("_fusion_auto") and da.get("_fusion_cible"):
        abort.append(f"ancre {ANCHOR} fusionnee (-> "
                     f"{da.get('_fusion_cible')})")
    for o in ORPHS:
        oa = by.get(o)
        if oa and oa.get("numero_immatriculation") \
                and oa.get("numero_immatriculation") != IMMAT:
            abort.append(f"orph {o} porte un autre immat : "
                         f"{oa.get('numero_immatriculation')}")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pda = pby.get(ANCHOR)

    moves = []
    for orph in ORPHS:
        s = pby.get(orph)
        if s is None:
            continue
        if s.get("_fusion_auto") and s.get("_fusion_cible") == ANCHOR:
            continue       # idempotent
        for k in MIRROR:
            s[k] = pda.get(k)
        s["_bdnb_match"] = "immat"
        if syn_ok(pda.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = pda.get("syndic")
            s["_syndic_src"] = (pda.get("_syndic_src") or "rnc") + "_grp"
        s["_fusion_auto"] = True
        s["_fusion_cible"] = ANCHOR
        s["_fusion_auto_sources"] = None
        moves.append(orph)

    if moves and pda is not None:
        cur = list(pda.get("_fusion_auto_sources") or [])
        pda["_fusion_auto_sources"] = sorted(set(cur + moves))
        pda.setdefault("_fusion_auto_label", None)

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX FONDARY/CROIX NIVERT — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCHOR : {ANCHOR}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Syndic : {(cp and cp.get('syndic')) or '—'}")
    print(f"  Re-points ({len(moves)}) :")
    for cle in moves:
        a0 = by.get(cle, {})
        print(f"    {cle:24s}  bgid_avant={a0.get('batiment_groupe_id')}"
              f"  vlog={a0.get('nb_ventes_logement')}"
              f"  vtot={a0.get('nb_ventes_total')}"
              f"  nb_log_bdnb={a0.get('nb_log_bdnb')}")
    print("-" * 78)
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "—"))
        v1, k1 = contrib1.get(bg, (0, "—"))
        if v0 != v1 or k0 != k1:
            print(f"  bgid {bg} : {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    print(f"Parc modele MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 78)

    if abort:
        print("ABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not moves:
        print("Idempotent : deja applique.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_fondary_croixnivert"] = (
        "91 RUE FONDARY -> 40 RUE DE LA CROIX NIVERT (AB9273434 "
        "SDC 40/42 RUE DE LA CROIX NIVERT, 17 lots hab / 28 tot, "
        "FOREST GESTION, mandat -> 2026-06-30). Triple "
        "confirmation : RNC compl_1='91 r fondary 75015 Paris', "
        "ref_cadastrale_1=DF0112 (bgid DN3P=91 FONDARY+42 CN) + "
        "ref_cadastrale_2=DF0111 (bgid STYB=40 CN), BDNB pivot "
        "DN3P=['42 Croix Nivert', '91 Fondary'] sur parcelle "
        "DF0112, nb_log_rnc=17 sur STYB matche AB9273434. "
        "Pattern ALIAS_RNC multi-voies (Fremicourt/Cambronne). "
        "91|FONDARY (bgid DN3P, 4 nb_log_bdnb, 1 vlog 2024) "
        "re-pointe vers 40|CROIX NIVERT avec adoption MIRROR "
        f"bgid STYB. Parc {parc0}->{parc1} ({delta:+d}) = dedup "
        "multi-bgid (les 4 BDNB de DN3P etaient deja compris "
        "dans les 17 lots RNC qui couvrent STYB+DN3P, PIPELINE "
        "Sec 6). 42 CROIX NIVERT absente du light - ALIAS_RNC "
        "a porter dans make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} re-point)")


if __name__ == "__main__":
    main()
