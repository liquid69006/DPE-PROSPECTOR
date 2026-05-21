"""
Correctif SURGICAL - INJECTION+ATTRIBUTION `6 RUE ALASSEUR`
(AJ6688972 'SDC immeuble sis a PARIS (75015) 6 rue Alasseur',
36 lots total / nb_lots_hab non renseigne RNC, syndic non
renseigne RNC). Detecte par scan parcelle cadastrale 2026-05-21
(scan_horsrnc_parcelle_mp.py).

Pattern INJECTION+ATTRIBUTION (clone fix_lowendal_suffren /
fix_suffren_barthelemy_garibaldi). La copro AJ6688972 vient
d'etre immatriculee 2026-03-16 (donc POSTERIEURE au snapshot
RNC utilise pour generer coproprietes[] du secteur), elle est
COMPLETEMENT ABSENTE du light (ni coproprietes[] ni avec immat
sur l'adresse 6 ALASSEUR). On l'INJECTE dans coproprietes[] et
on l'ATTRIBUE a `6|RUE|ALASSEUR` deja existante en hr-actif.

Triple confirmation source-of-truth :
  - RNC live AJ6688972 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='SDC immeuble sis a PARIS (75015) 6
    rue Alasseur'`, `adresse_reference='6 Rue Alasseur 75015
    Paris'`, `reference_cadastrale_1='75056115DH0016'` UNIQUE
    (ref_cad_2/3 vides), `nombre_total_lots=36`,
    `nombre_lots_usage_habitation=None` (= non renseigne par le
    declarant), `date_immatriculation='2026-03-16'`,
    `periode_construction='AVANT_1949'`, syndic non renseigne.
  - BDNB pivot bgid 9DSY-ZPJ1-Y95N : `l_libelle_adr=['6 Rue
    Alasseur, 75015, Paris 15e Arrondissement']` UNIQUE,
    parcelle 75115000DH0016 UNIQUE, annee_construction=1930,
    nb_log=16, nb_log_rnc=None.
  - DVF parcelle DH/16 : 1 mutation 2025 sur 6 ALASSEUR (la
    SCI DU 6 RUE ALASSEUR a probablement scinde en SDC en
    mars 2026, vente bloc preparatoire en 2025).
  - 0 collision : aucun autre bgid sur parcelle DH/0016.

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `6|RUE|ALASSEUR` dans adresses[] avec bgid 9DSY correct,
    `numero_immatriculation=None`, `_fusion_auto=None`, syndic
    null, `sci_proprietaire='oui'`/`sci_nom='SCI DU 6 RUE
    ALASSEUR'` (mono-propriete avant 2026-03-16), 1 vlog en
    2025, classement_rotation_logement='Modere'. La SCI 2025
    refletait la mono-propriete pre-immat ; depuis 2026-03-16
    c'est une copro RNC qui doit etre visible.

Mecanisme : INJECTION nouvelle ligne coproprietes[] AJ6688972
(extraite de RNC live) + ATTRIBUTION sur `6|RUE|ALASSEUR`
(immat + lots + nom_copropriete). Syndic reste null (RNC ne le
renseigne pas, mandat probablement pas encore depose).

NOTE FALLBACK LOTS_HABITATION : RNC live renseigne
`nombre_total_lots=36` mais `nombre_lots_usage_habitation=None`
(rare, lie a immatriculation tres recente 2026-03-16). Pour
eviter une perte parc (16 nb_log_bdnb actuel -> 0 sans
nb_lots_habit), on adopte nb_lots_habitation=36 (fallback total)
avec `_lots_habit_src='rnc_total_fallback'` pour tracabilite.
Cette estimation pourra etre raffinee quand le RNC ventilera.

Effet parc (modele renderSecteur Sec 6) :
  - bgid 9DSY : passe de bucket bgBdnb=16 (hr-actif Resid coll,
    16 nb_log_bdnb sans cp) -> bucket bgRncLots=36 (lots RNC
    autoritatifs AJ6688972, fallback total). Delta = +20
    logements (switch BDNB(16)->RNC(36) avec fallback total,
    Sec 6 lots RNC prioritaires).
  - Aucun autre bgid impacte.

Ventes : 1 vlog DVF 2025 deja en place sur 6 ALASSEUR, reste
en place. Apres fix elle apparait sous AJ6688972 (SCI cession
preparatoire 2025 a la mise en copropriete).

Source-of-truth a porter dans make_light_motte_picquet.py :
  - Investiguer pourquoi AJ6688972 manque dans le snapshot RNC
    (date_immat 2026-03-16 POSTERIEUR au snapshot. Verifier
    rafraichissement automatique RNC dans pipeline make_*).

Cible : data/secteur_motte_picquet_light.json. Backup
.prealasseur.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_alasseur_inject.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_alasseur_inject.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prealasseur.bak"

ANCHOR_CLE = "6|RUE|ALASSEUR"
IMMAT = "AJ6688972"
BGID = "bdnb-bg-9DSY-ZPJ1-Y95N"

# Donnees RNC live (tabular-api 3ea8e2c3-0038-464a-b17e-cd5c91f65ce2,
# numero_immatriculation__exact=AJ6688972) figees pour reproductibilite.
# date_immat 2026-03-16, periode AVANT_1949, syndic non renseigne,
# nombre_lots_usage_habitation=None (fallback total 36).
RNC_LIVE = {
    "numero_immatriculation": IMMAT,
    "nom_copropriete": "SDC 6 RUE ALASSEUR",
    "syndic": None,
    "_syndic_src": None,
    "nb_lots_total": 36,
    # Fallback total : RNC non renseigne, on prend total pour eviter
    # perte parc. Tracabilite via _lots_habit_src='rnc_total_fallback'.
    "nb_lots_habitation": 36,
    "nb_lots_habitation_rnc": None,
    "_lots_habit_src": "rnc_total_fallback",
}


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


def build_copro(adr_anchor):
    """Construit la ligne coproprietes[] AJ6688972."""
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
        "adresse": "6 Rue Alasseur | 6 Rue Alasseur 75015 Paris | 75015 | Paris",
        "longitude": adr_anchor.get("longitude"),
        "latitude": adr_anchor.get("latitude"),
        "code_iris": adr_anchor.get("code_iris"),
        "cle_adresse": ANCHOR_CLE,
        "nb_lots_total": RNC_LIVE["nb_lots_total"],
        "nb_lots_habitation": RNC_LIVE["nb_lots_habitation"],
        "nb_lots_habitation_rnc": RNC_LIVE["nb_lots_habitation_rnc"],
        "_lots_habit_src": RNC_LIVE["_lots_habit_src"],
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

    abort = []
    a = by.get(ANCHOR_CLE)
    if a is None:
        abort.append(f"ancre absente : {ANCHOR_CLE}")
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
    chain_in = [x["cle"] for x in light["adresses"]
                if x.get("_fusion_cible") == ANCHOR_CLE]

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {x["cle"]: x for x in patched["adresses"]}
    pa = pby.get(ANCHOR_CLE)

    new_copro = build_copro(pa) if pa else None
    moves = []
    if pa and new_copro and not abort:
        patched["coproprietes"].append(new_copro)
        pa["numero_immatriculation"] = IMMAT
        pa["nb_lots_habitation"] = RNC_LIVE["nb_lots_habitation"]
        # syndic et _syndic_src restent inchanges (RNC ne les renseigne pas)
        pa["_bdnb_match"] = "immat"
        moves.append(ANCHOR_CLE)

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX ALASSEUR INJECTION (AJ6688972) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCRE         : {ANCHOR_CLE}  bgid={BGID}")
    print(f"  Immat injectee: {IMMAT}  "
          f"{RNC_LIVE['nom_copropriete']!r}")
    print(f"  Lots          : {RNC_LIVE['nb_lots_total']} tot / "
          f"{RNC_LIVE['nb_lots_habitation']} hab "
          f"(src={RNC_LIVE['_lots_habit_src']})")
    print(f"  Syndic        : {RNC_LIVE['syndic']!r} "
          f"(non renseigne RNC, mandat pas encore depose)")
    print(f"  Date immat    : 2026-03-16 (posterieure snapshot RNC)")
    print(f"  Chain in {ANCHOR_CLE!r}: {chain_in or '[]'}")
    print("-" * 78)
    b0, k0 = contrib0.get(BGID, (0, "-"))
    b1, k1 = contrib1.get(BGID, (0, "-"))
    print(f"  bgid {BGID} : {b0} ({k0}) -> {b1} ({k1}) "
          f"= {b1 - b0:+d} logements")
    if new_copro:
        print(f"  Ventes : {new_copro['nb_ventes_2021_2025']} sur "
              f"5 ans ({new_copro['ventes_par_an']}) -> "
              f"taux={new_copro['taux_rotation_5ans']}% "
              f"-> {new_copro['classement_rotation']}")
    print("-" * 78)
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
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
        print("Idempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_alasseur_inject"] = (
        f"Copro RNC AJ6688972 ('{RNC_LIVE['nom_copropriete']}', "
        f"{RNC_LIVE['nb_lots_total']} lots tot / nb_lots_hab non "
        "renseigne RNC -> fallback total 36, syndic non renseigne, "
        "date_immat 2026-03-16 POSTERIEURE au snapshot) injectee "
        f"dans coproprietes[] et attribuee a {ANCHOR_CLE} (bgid "
        "9DSY, parcelle 75115000DH0016 unique, 1 bgid unique sur "
        "la parcelle). Confirmee par RNC live (ref_cad_1=75056115"
        "DH0016 unique, adresse_reference='6 Rue Alasseur 75015 "
        "Paris', periode AVANT_1949) + BDNB pivot 9DSY "
        "(l_libelle_adr=['6 Rue Alasseur'] unique, annee=1930). "
        "La SCI DU 6 RUE ALASSEUR (pre-immat) a probablement "
        "scinde en SDC en mars 2026 (1 vlog DVF 2025 = vente "
        "bloc preparatoire). Pattern INJECTION+ATTRIBUTION "
        "(clone fix_lowendal_suffren). Parc "
        f"{parc0}->{parc1} ({delta:+d} = switch BDNB(16)->RNC(36 "
        "fallback total) sur bgid 9DSY, Sec 6 lots RNC "
        "prioritaires). Investiguer make_light : rafraichissement "
        "RNC snapshot a faire pour capter immatriculations "
        "post-snapshot (date_immat 2026-03-16).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 copro {IMMAT}, attribution "
          f"{ANCHOR_CLE})")


if __name__ == "__main__":
    main()
