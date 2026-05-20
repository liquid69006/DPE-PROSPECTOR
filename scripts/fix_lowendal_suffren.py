"""
Correctif SURGICAL — `16/18 AVENUE LOWENDAL` + facade `108 AVENUE DE
SUFFREN` (AB8146169 '16-18, AVENUE LOWENDAL', 76 lots hab / 80 tot,
CONSEIL RICHOU IMMOBILIER). Confirmation terrain user 2026-05-20.

Pattern INJECTION+ATTRIBUTION (clone fix_suffren_barthelemy_garibaldi).
La copro RNC AB8146169 est COMPLETEMENT ABSENTE du snapshot (ni
coproprietes[] ni adresses[]). On l'INJECTE dans coproprietes[] et on
l'ATTRIBUE a l'ancre `16|AVENUE|LOWENDAL` deja existante.

Triple confirmation source-of-truth :
  - RNC live AB8146169 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='16-18, AVENUE LOWENDAL'`,
    `adresse_reference='16-18 av de lowendal 75015 PARIS'`,
    `nombre_total_lots=80`, `nombre_lots_habitation=76`,
    `nombre_adresses_complementaires=0` (RNC tronque les facades,
    BDNB+BAN exhibent 108 SUFFREN). Syndic CONSEIL RICHOU
    IMMOBILIER (SIRET 82426879100020), mandat -> 2026-06-30, date_
    immat 2017-12-28, derniere maj 2025-11-22, periode AVANT_1949.
  - BDNB pivot bgid R41C-48RR-9DHU (parcelle 75115000DE0070) :
    `l_libelle_adr = ['18 Avenue De Lowendal', '108 avenue de suffren',
    '16 Avenue De Lowendal']` (3 facades BAN sur le meme bati,
    `nb_log=27`, `nb_log_rnc=76` = MATCHE AB8146169 exactement).
    `libelle_adr_principale_ban='16 Avenue de Lowendal'`.
  - BDNB rel_batiment_groupe_rnc R41C : 1 row pointant AB8146169
    (adresse_brut='16 18 Avenue De Lowendal 75015 Paris', cle_
    interop 75115_5827_00018).
  - DVF parcelle DE/70 : 6 mutations 16+18 LOWENDAL (3 chaque),
    aucune au 108 SUFFREN (facade non-postale type Barthelemy).
  - Distinction copro voisine : AA0600619 SQUARE LOWENDAL (399
    lots, parcelle CZ0015) = copro DIFFERENTE, ne couvre PAS
    16/18 LOWENDAL ni 108 SUFFREN.

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `16|AVENUE|LOWENDAL` dans adresses[] avec bgid R41C correct,
    `_fusion_auto_sources=['18|AVENUE|LOWENDAL']`, label '16/18
    AVENUE LOWENDAL', mais `numero_immatriculation=None`,
    `nb_lots_habitation=None`, syndic=None : copro AB8146169
    invisible parce que ABSENTE du snapshot RNC. Pattern identique
    a AD2301695/163 SUFFREN.
  - `18|AVENUE|LOWENDAL` deja fused vers 16 (bgid R41C identique).
  - `108|AVENUE|SUFFREN` : ABSENTE du light (non-postale, 0 vente
    DVF). Aucune entree a creer dans adresses[]. Source-of-truth
    ALIAS_RNC dans make_light_motte_picquet.py pour re-routage
    futur si vente DVF s'y rattache.

Mecanisme : INJECTION nouvelle ligne coproprietes[] AB8146169
(extraite de RNC live) + ATTRIBUTION sur `16|AVENUE|LOWENDAL`
(immat + lots + syndic). Update label '16/18 LOWENDAL' -> '16/18
LOWENDAL / 108 SUFFREN' pour visibilite 3 facades.

Effet parc (modele renderSecteur Sec 6) :
  - bgid R41C : passe de bucket bgBdnb=27 (estim BDNB, 16 LOWENDAL
    sans copro RESID coll) -> bucket bgRncLots=76 (lots RNC
    autoritatifs AB8146169). Delta = +49 logements (switch
    BDNB(27)->RNC(76) autoritaire, PIPELINE Sec 6 lots RNC
    prioritaires).
  - Aucun autre bgid impacte.

Ventes : 16 LOWENDAL (2 vlog) + 18 LOWENDAL fused (3 vlog) = 5 vlog
deja en place, restent en place. Apres fix elles apparaissent sous
AB8146169 '16-18, AVENUE LOWENDAL'. Taux 5/(5*76/100) = 1.32%
(Modere).

Source-of-truth a porter dans make_light_motte_picquet.py :
  - ALIAS_RNC += { "108|AVENUE|SUFFREN": "16|AVENUE|LOWENDAL" }
  - Investiguer pourquoi AB8146169 manque dans le snapshot RNC
    (pattern identique a AD2301695, possible filtre code_postal
    ou autre).

Cible : data/secteur_motte_picquet_light.json. Backup
.prelowendal.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_lowendal_suffren.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_lowendal_suffren.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prelowendal.bak"

ANCHOR_CLE = "16|AVENUE|LOWENDAL"
IMMAT = "AB8146169"
BGID = "bdnb-bg-R41C-48RR-9DHU"
LABEL = "16/18 AVENUE LOWENDAL / 108 AVENUE DE SUFFREN"

# Donnees RNC live (tabular-api 3ea8e2c3-0038-464a-b17e-cd5c91f65ce2,
# numero_immatriculation__exact=AB8146169) figees ici pour
# reproductibilite. date_immat 2017-12-28, derniere maj 2025-11-22,
# mandat -> 2026-06-30, SIRET 82426879100020, type=professionnel,
# periode=AVANT_1949, residence_service=non, syndicat_principal=oui.
RNC_LIVE = {
    "numero_immatriculation": IMMAT,
    "nom_copropriete": "16-18, AVENUE LOWENDAL",
    "syndic": "CONSEIL RICHOU IMMOBILIER",
    "_syndic_src": "rnc_live",
    "nb_lots_total": 80,
    "nb_lots_habitation": 76,
    "nb_lots_habitation_rnc": 76,
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
    """Construit la ligne coproprietes[] AB8146169."""
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
        # adresse composite multi-voies (3 facades BDNB confirmees)
        "adresse": ("16 Avenue de Lowendal | 18 Avenue de Lowendal | "
                    "108 Avenue de Suffren | 75015 | Paris"),
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
        if not syn_ok(pa.get("syndic")):
            pa["syndic"] = RNC_LIVE["syndic"]
            pa["_syndic_src"] = RNC_LIVE["_syndic_src"]
        pa["_bdnb_match"] = "immat"
        # Label : update '16/18 AVENUE LOWENDAL' -> '...108 SUFFREN'
        old_label = pa.get("_fusion_auto_label")
        pa["_fusion_auto_label"] = LABEL
        moves.append((ANCHOR_CLE, old_label, LABEL))

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX LOWENDAL/SUFFREN (AB8146169) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCRE         : {ANCHOR_CLE}  bgid={BGID}")
    print(f"  Immat injectee: {IMMAT}  {RNC_LIVE['nom_copropriete']!r}")
    print(f"  Lots          : {RNC_LIVE['nb_lots_total']} tot / "
          f"{RNC_LIVE['nb_lots_habitation']} hab")
    print(f"  Syndic        : {RNC_LIVE['syndic']} "
          f"(src={RNC_LIVE['_syndic_src']})")
    print(f"  Facade 108 SUFFREN : non-postale (0 vente DVF, hors "
          "light) - ALIAS_RNC source-of-truth")
    print(f"  Chain in {ANCHOR_CLE!r}: {chain_in or '[]'}")
    if moves:
        for cle, old, new in moves:
            print(f"  Label updated : {old!r} -> {new!r}")
    print("-" * 78)
    b0, k0 = contrib0.get(BGID, (0, "-"))
    b1, k1 = contrib1.get(BGID, (0, "-"))
    print(f"  bgid {BGID} : {b0} ({k0}) -> {b1} ({k1}) "
          f"= {b1 - b0:+d} logements")
    if new_copro:
        print(f"  Ventes RNC : {new_copro['nb_ventes_2021_2025']} sur "
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
    meta["_correctif_lowendal_suffren"] = (
        f"Copro RNC AB8146169 ('{RNC_LIVE['nom_copropriete']}', "
        f"{RNC_LIVE['nb_lots_habitation']} lots hab / "
        f"{RNC_LIVE['nb_lots_total']} tot, syndic CONSEIL RICHOU "
        "IMMOBILIER, mandat -> 2026-06-30, derniere maj 2025-11-22) "
        f"injectee dans coproprietes[] et attribuee a {ANCHOR_CLE} "
        f"(bgid {BGID}, parcelle 75115000DE0070). Copro ABSENTE du "
        "snapshot RNC mais confirmee par RNC live + BDNB pivot "
        "(l_libelle_adr=['18 Lowendal', '108 Suffren', '16 Lowendal'] "
        "+ nb_log_rnc=76 matche exactement) + BDNB rel_RNC R41C ('16 "
        "18 Avenue De Lowendal'). 108 AVENUE DE SUFFREN : facade "
        "non-postale (0 vente DVF, hors light) - ALIAS_RNC a porter "
        "dans make_light_motte_picquet.py. Distinction copro voisine "
        "AA0600619 SQUARE LOWENDAL (parcelle CZ0015) = copro "
        "DIFFERENTE. Pattern INJECTION+ATTRIBUTION (clone "
        f"fix_suffren_barthelemy_garibaldi). Parc {parc0}->{parc1} "
        f"({delta:+d} = switch BDNB(27)->RNC(76) sur bgid R41C, "
        "PIPELINE Sec 6 lots RNC prioritaires). Label '16/18 AVENUE "
        f"LOWENDAL' -> '{LABEL}'. 5 vlog DVF (2 sur 16 + 3 sur 18 "
        "fused) relocalises sous AB8146169 (taux 1.32% Modere).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 copro AB8146169, attribution "
          f"{ANCHOR_CLE})")


if __name__ == "__main__":
    main()
