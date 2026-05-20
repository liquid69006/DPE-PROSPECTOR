"""
Correctif SURGICAL — `163 AV DE SUFFREN` + facades `9 RUE BARTHELEMY`
+ `59 BD GARIBALDI` (AD2301695, 17 lots hab / 20 tot, GESTION ET
TRANSACTIONS DE FRANCE). Confirmation terrain user 2026-05-20.

Triple confirmation source-of-truth :
  - RNC live AD2301695 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='163 AVENUE DE SUFFREN'`,
    `adresse_reference='59 bd garibaldi 75015 PARIS'`,
    `nombre_total_lots=20`, `nombre_lots_habitation=17`,
    `nombre_adresses_complementaires=0` (RNC tronque les facades,
    BDNB+BAN les exhibent). Syndic GESTION ET TRANSACTIONS DE FRANCE
    (SIRET 57203237300100), mandat -> 2026-06-30.
  - BDNB bgid `QTC9-KFAU-5TPU` (cache pivot, parcelle 75115000CW0053) :
    `l_libelle_adr = ['9 rue barthelemy', '163 Avenue De Suffren',
    '59 Boulevard Garibaldi']` (3 facades BAN sur le meme bati,
    `numero_immat_principal=AD2301695`, `nb_log=14` / `nb_log_rnc=17`).
  - Cache `_horsrnc_bdnb_live_motte_picquet.json[QTC9]` = immats
    [AD2301695], meta {nb_log_rnc:17, nb_lot_tot:20}.

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `163|AVENUE|SUFFREN` dans adresses[] avec bgid QTC9 correct,
    mais `numero_immatriculation=None`, `nb_lots_habitation=None`,
    syndic=None : copro AD2301695 invisible parce que ABSENTE du
    snapshot RNC (`secteur_motte_picquet.json` n'inclut pas cet
    immat, raison inconnue -- a investiguer make_*). Le fix
    `fix_horsrnc_attribution.py` ne la rattache pas non plus :
    il depend de `copro_by_immat` du snapshot.
  - `9 RUE BARTHELEMY` et `59 BD GARIBALDI` : ABSENTES du light
    (non-postales en BAN, 0 vente DVF). Aucune entree a creer
    dans `adresses[]` (sinon double-comptage parc). Source-of-
    truth ALIAS_RNC dans make_light_motte_picquet.py pour
    re-routage futur si une vente DVF s'y rattache.

Mecanisme : INJECTION d'une nouvelle entree `coproprietes[]`
AD2301695 (extraite de RNC live) + ATTRIBUTION sur l'adresse
`163|AVENUE|SUFFREN` (immat + lots + syndic copies). Pas
d'orphelin a re-pointer (chain vide : QTC9 ne porte qu'un
record adresse).

Effet parc (modele renderSecteur Sec 6) :
  - bgid QTC9 : passe de bucket bgBdnb=14 (estim BDNB, 163 SUFFREN
    sans copro RESID coll) -> bucket bgRncLots=17 (lots RNC
    autoritatifs AD2301695). Delta = +3 logements (switch
    BDNB->RNC documente PIPELINE Sec 6).
  - Aucun autre bgid impacte (chain vide).

Ventes : 2 ventes DVF (12/07/2023 + 23/07/2025) deja sur
`163|AVENUE|SUFFREN`, restent en place. Apres fix, elles
apparaissent sous AD2301695 "163 AVENUE DE SUFFREN" (taux
2/(5*17/100)=2.35% -> "Actif").

Source-of-truth a porter dans `make_light_motte_picquet.py`
(hors depot) :
  - ALIAS_RNC += { "9|RUE|BARTHELEMY": "163|AVENUE|SUFFREN",
                    "59|BOULEVARD|GARIBALDI": "163|AVENUE|SUFFREN" }
  - Investiguer pourquoi AD2301695 manque dans le snapshot RNC
    (peut-etre filtre code_postal ou autre -- non resolu ici).

Cible : data/secteur_motte_picquet_light.json. Backup
.presuffren.bak. Dry-run par defaut.

Usage :
  python scripts/fix_suffren_barthelemy_garibaldi.py            # DRY-RUN
  python scripts/fix_suffren_barthelemy_garibaldi.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.presuffren.bak"

ANCHOR_CLE = "163|AVENUE|SUFFREN"
IMMAT = "AD2301695"
BGID = "bdnb-bg-QTC9-KFAU-5TPU"

# Donnees RNC live (tabular-api 3ea8e2c3-0038-464a-b17e-cd5c91f65ce2,
# numero_immatriculation__exact=AD2301695) figees ici pour
# reproductibilite (le script ne refait pas l'appel).
RNC_LIVE = {
    "numero_immatriculation": IMMAT,
    "nom_copropriete": "163 AVENUE DE SUFFREN",
    "syndic": "GESTION ET TRANSACTIONS DE FRANCE",
    "_syndic_src": "rnc_live",
    "nb_lots_total": 20,
    "nb_lots_habitation": 17,
    "nb_lots_habitation_rnc": 17,
    # date_immatriculation: 2018-09-03, date_derniere_maj: 2025-09-06,
    # mandat en cours -> 2026-06-30, SIRET 57203237300100, type=
    # professionnel, periode_construction=AVANT_1949, residence_service=non,
    # syndicat_principal_ou_secondaire=oui, copro_aidee=False.
}


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


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
    contrib = {}
    for bg in set(bgRncLots) | set(bgBdnb):
        v = (sum(bgRncLots[bg].values()) if bg in bgRncLots
             else bgBdnb.get(bg, 0))
        parc += v
        contrib[bg] = (v, "RNC" if bg in bgRncLots else "BDNB")
    return parc, contrib


def build_copro(adr_anchor):
    """Construit la ligne `coproprietes[]` AD2301695, alignee sur le
    schema courant (cf. AA0646265 ARMONIAL I)."""
    vpa = adr_anchor.get("ventes_par_an") or {}
    nlog = RNC_LIVE["nb_lots_habitation"]
    nv5 = sum(int(v or 0) for k, v in vpa.items()
              if str(k) in {"2021", "2022", "2023", "2024", "2025"})
    taux = round(nv5 / (5 * nlog / 100), 1) if nlog else None
    if taux is None:
        cls = "Figé"
    elif taux > 3:
        cls = "Très actif"
    elif taux >= 2:
        cls = "Actif"
    elif taux >= 1:
        cls = "Modéré"
    else:
        cls = "Figé"
    return {
        "numero_immatriculation": IMMAT,
        "nom_copropriete": RNC_LIVE["nom_copropriete"],
        "syndic": RNC_LIVE["syndic"],
        "_syndic_src": RNC_LIVE["_syndic_src"],
        # adresse composite multi-voies (les 3 facades BDNB confirmees)
        "adresse": ("163 Avenue de Suffren | 9 Rue Barthelemy | "
                    "59 Boulevard Garibaldi | 75015 | Paris"),
        "longitude": adr_anchor.get("longitude"),
        "latitude": adr_anchor.get("latitude"),
        "code_iris": adr_anchor.get("code_iris"),
        "cle_adresse": ANCHOR_CLE,
        "nb_lots_total": RNC_LIVE["nb_lots_total"],
        "nb_lots_habitation": RNC_LIVE["nb_lots_habitation"],
        "nb_lots_habitation_rnc": RNC_LIVE["nb_lots_habitation_rnc"],
        "nb_log_bdnb": adr_anchor.get("nb_log_bdnb"),
        "nb_ventes_2021_2025": nv5,
        "ventes_par_an": vpa,
        "taux_rotation_5ans": taux,
        "classement_rotation": cls,
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}
    by_immat = {c.get("numero_immatriculation"): c
                for c in light["coproprietes"]
                if c.get("numero_immatriculation")}

    # ---- gardes ----
    abort = []
    a = by.get(ANCHOR_CLE)
    if a is None:
        abort.append(f"ancre absente du light : {ANCHOR_CLE}")
    elif a.get("batiment_groupe_id") != BGID:
        abort.append(f"bgid divergent : {ANCHOR_CLE} "
                     f"{a.get('batiment_groupe_id')} != {BGID}")
    if a and a.get("_fusion_auto") and a.get("_fusion_cible"):
        abort.append(f"ancre {ANCHOR_CLE} elle-meme fusionnee "
                     f"(-> {a.get('_fusion_cible')})")
    if IMMAT in by_immat:
        abort.append(f"immat {IMMAT} deja injectee "
                     f"(cle={by_immat[IMMAT].get('cle_adresse')!r})")
    if cbc.get(ANCHOR_CLE):
        abort.append(f"copro deja presente sur {ANCHOR_CLE} "
                     f"(immat={cbc[ANCHOR_CLE].get('numero_immatriculation')})")
    # chain : adresses fusionnees DANS l'ancre ?
    chain_in = [x["cle"] for x in light["adresses"]
                if x.get("_fusion_cible") == ANCHOR_CLE]

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {x["cle"]: x for x in patched["adresses"]}
    pa = pby.get(ANCHOR_CLE)

    # Construire et injecter la copro
    new_copro = build_copro(pa) if pa else None
    moves = []
    if pa and new_copro:
        patched["coproprietes"].append(new_copro)
        # Attribution sur l'adresse ancre (champs autoritatifs RNC)
        pa["numero_immatriculation"] = IMMAT
        pa["nb_lots_habitation"] = RNC_LIVE["nb_lots_habitation"]
        if not syn_ok(pa.get("syndic")):
            pa["syndic"] = RNC_LIVE["syndic"]
            pa["_syndic_src"] = RNC_LIVE["_syndic_src"]
        moves.append(ANCHOR_CLE)

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    # ---- rapport ----
    print("=" * 76)
    print(f"FIX SUFFREN/BARTHELEMY/GARIBALDI — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 76)
    print(f"  ANCHOR        : {ANCHOR_CLE}  bgid={BGID}")
    print(f"  Immat injectee: {IMMAT}  {RNC_LIVE['nom_copropriete']!r}")
    print(f"                  {RNC_LIVE['nb_lots_total']} lots tot / "
          f"{RNC_LIVE['nb_lots_habitation']} hab / nb_log_bdnb=14")
    print(f"  Syndic        : {RNC_LIVE['syndic']} "
          f"(src={RNC_LIVE['_syndic_src']})")
    print(f"  Facades BDNB  : 9 RUE BARTHELEMY + 59 BD GARIBALDI "
          "(non-postales, 0 vente DVF, hors light)")
    print(f"  Chain in {ANCHOR_CLE!r}: {chain_in or '[]'}")
    print("-" * 76)
    b0, k0 = contrib0.get(BGID, (0, "—"))
    b1, k1 = contrib1.get(BGID, (0, "—"))
    print(f"  bgid {BGID} : {b0} ({k0}) -> {b1} ({k1}) "
          f"= {b1 - b0:+d} logements (switch BDNB->RNC, "
          f"PIPELINE Sec 6 lots RNC prioritaires)")
    if new_copro:
        print(f"  Ventes RNC : {new_copro['nb_ventes_2021_2025']} sur "
              f"5 ans ({new_copro['ventes_par_an']}) -> "
              f"taux={new_copro['taux_rotation_5ans']}% "
              f"-> {new_copro['classement_rotation']}")
    print("-" * 76)
    print(f"Parc modele MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 76)

    if abort:
        print("ABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not moves:
        print("Idempotent : aucune modification (deja applique ?).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_suffren_barthelemy_garibaldi"] = (
        f"Copro RNC AD2301695 ({RNC_LIVE['nom_copropriete']}, "
        f"{RNC_LIVE['nb_lots_habitation']} lots hab / "
        f"{RNC_LIVE['nb_lots_total']} tot, syndic GESTION ET "
        "TRANSACTIONS DE FRANCE) injectee dans coproprietes[] et "
        f"attribuee a {ANCHOR_CLE} (bgid {BGID}). Copro ABSENTE du "
        "snapshot RNC mais confirmee par RNC live (tabular-api "
        "3ea8e2c3-0038...) + BDNB pivot (l_libelle_adr = 9 BARTH + "
        "163 SUFFREN + 59 GAR sur QTC9-KFAU-5TPU, parcelle "
        "75115000CW0053). 9 RUE BARTHELEMY et 59 BD GARIBALDI : "
        "facades non-postales, 0 vente DVF, hors light - ALIAS_RNC "
        "a porter dans make_light_motte_picquet.py. Parc "
        f"{parc0}->{parc1} ({delta:+d} logements : switch BDNB(14)"
        "->RNC(17) autoritatif sur bgid QTC9, PIPELINE Sec 6). "
        "2 ventes DVF (12/07/2023 + 23/07/2025) relocalisees sous "
        "AD2301695, classement Actif.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 copro AD2301695, "
          f"attribution {ANCHOR_CLE})")


if __name__ == "__main__":
    main()
