"""
Correctif HYBRIDE — `126 AV. SUFFREN` + `128 AV. SUFFREN` + `2 RUE
CHASSELOUP LAUBAT` (+ 4 documentee via label) (AF9030966 SDC 126-128
AVENUE DE SUFFREN, 33 lots hab / 47 tot, FIDUCIAIRE DU DISTRICT DE
PARIS). Confirmation terrain user 2026-05-20.

Pattern HYBRIDE Suffren + Cambronne + correction bgid (calque Parc
Sisley) :
  - INJECT `126|AVENUE|SUFFREN` dans adresses[] (pattern Suffren) :
    l'ancre RNC AF9030966 a cle_adresse='126|AVENUE|SUFFREN' dans
    coproprietes[] mais AUCUNE entree adresses[] correspondante.
    make_light n'a pas genere l'entree (pas de MAJIC ni DVF au 126
    direct, BAN code voie 9114_00126 hors ranges).
  - RE-POINT `128|AVENUE|SUFFREN` -> 126|AVENUE|SUFFREN (pattern
    Cambronne). 128 deja bgid WAEU correct (= MEME bati BDNB que
    126), syndic FIDUCIAIRE DU DISTRICT par cadastre.
  - RE-POINT + CORRECTION bgid `2|RUE|CHASSELOUP LAUBAT` :
    actuellement sur bgid 1GJW (= bati TERTIAIRE 3 Chasseloup,
    parcelle CZ0047) selon make_light, mais BDNB pivot dit que 2
    CHASSELOUP est sur bgid WAEU (= bati 128 SUFFREN, parcelle
    CZ0041, residentiel). Adoption MIRROR corrige + fusion.
  - 4|RUE|CHASSELOUP LAUBAT : ABSENTE du light (pas de MAJIC ni
    DVF), documentee via `_fusion_auto_label` sur l'ancre.

Triple confirmation source-of-truth :
  - RNC live AF9030966 (tabular-api 3ea8e2c3-0038...) :
    nom='126-128 Avenue de Suffren 75015 PARIS', adresse_reference=
    '126 av de suffren 75015 Paris', adresse_complementaire_1=null
    (RNC sous-declare ; le nom mentionne 126-128 seul, pas
    Chasseloup), 33 lots hab / 47 tot. FIDUCIAIRE DU DISTRICT DE
    PARIS, date_immat 2020-02-03, periode DE_1961_A_1974, ref_
    cadastrale_1='75056115CZ0041'.
  - BDNB pivot bgid WAEU-1XSX-V5GP : l_libelle_adr = ['128 Avenue
    De Suffren', '4 rue chasseloup laubat', '2 rue chasseloup
    laubat'] -> CONFIRME les 3 facades du MEME bati. Parcelle
    BDNB 75115000CZ0041 = MATCH parfait avec ref_cad_1 RNC.
    rel_batiment_groupe_adresse WAEU : 4 cles BAN (75115_1908_
    00002, 75115_1908_00004, 75115_9114_00128, IMB/75115/C/01QX).
  - BDNB pivot bgid 1GJW-7MDQ-9RGA (= attribution actuelle FAUSSE
    du 2 CHASSELOUP) : l_libelle_adr = ['3 Rue Chasseloup Laubat']
    SEUL, usage Tertiaire, parcelle 75115000CZ0047 (parcelle
    DIFFERENTE de CZ0041). Donc le 2 CHASSELOUP @1GJW = ERREUR
    make_light (matching num_voie sans validation BAN/parcelle).
  - BDNB enrich bgid WAEU : annee 1972, nb_log=18, appartement,
    reseau de chaleur, Residentiel collectif. 18 BDNB < 33 lots
    RNC -> coherent (BDNB sous-couvre, RNC autoritaire).

ANOMALIES LIGHT ACTUELLES (corrigees) :
  - `126|AVENUE|SUFFREN` ABSENTE d'adresses[] (anomalie make_light :
    pas de MAJIC/DVF direct, mais cle_adresse de AF9030966 dans
    coproprietes[]).
  - `128|AVENUE|SUFFREN` bgid=WAEU immat=None, syndic FIDUCIAIRE
    par cadastre (orphelin OK sur le bon bgid, manque attribution
    immat AF9030966).
  - `2|RUE|CHASSELOUP LAUBAT` bgid=1GJW (FAUX, devrait etre WAEU
    selon BDNB pivot+parcelle) immat=None usage=Tertiaire (FAUX,
    suit bgid 1GJW alors que le bati reel WAEU est Resid collectif).
  - `4|RUE|CHASSELOUP LAUBAT` ABSENTE (pas de MAJIC/DVF) -
    documentation via label.
  - `3|RUE|CHASSELOUP LAUBAT` bgid=1GJW Tertiaire : CORRECT (bati
    distinct, parcelle CZ0047), INCHANGE.

Mecanisme INJECT + RE-POINT MIRROR. L'ancre 126 absorbe les 2
orphelins (128 SUFFREN, 2 CHASSELOUP). Le 4 CHASSELOUP est
documente uniquement via _fusion_auto_label sur l'ancre.

Effet parc (modele renderSecteur Sec 6) :
  - bgid WAEU : avant bgBdnb=18 (via 128 SUFFREN, sans cp) ->
    apres bgRncLots={AF9030966:33} (via 126 SUFFREN injecte avec
    immat) = switch BDNB->RNC autoritaire (PIPELINE Sec 6 lots RNC
    prioritaires).
  - bgid 1GJW : avant bgBdnb=0 (3 CHASSELOUP Tertiaire exclu) ->
    apres bgBdnb=0 (idem, 3 reste non-fused Tertiaire) = inchange.
  - Le 2 CHASSELOUP fused (bgid 1GJW -> WAEU MIRROR) sort de toute
    contribution (0 avant + 0 apres car Tertiaire dans les 2 cas).
  -> Delta parc = +15 logements (passage 18 BDNB -> 33 RNC sur
     WAEU = 33 lots RNC AF9030966 prennent autorite sur 18 nb_log
     BDNB qui sous-couvrait).

Ventes relocalisees au rendu :
  - 128 SUFFREN : vlog=1 / vtot=2
  - 2 CHASSELOUP : vlog=0 / vtot=0 (aucune)
  - Total 1 v_log + 2 v_tot sous AF9030966 (taux 0.6% logement ->
    Modere probable au prochain calcul).

Source-of-truth a porter dans make_light_motte_picquet.py :
  - Cas 'cle_adresse copro sans entree adresses' = INJECT auto
    si copro.cle_adresse n'a pas d'entree dans adresses[].
  - ALIAS_RNC += {
      '128|AVENUE|SUFFREN': '126|AVENUE|SUFFREN',
      '2|RUE|CHASSELOUP LAUBAT': '126|AVENUE|SUFFREN',
      '4|RUE|CHASSELOUP LAUBAT': '126|AVENUE|SUFFREN'
    }
  - Correction bgid : 2 CHASSELOUP doit etre sur WAEU pas 1GJW
    (validation BAN/parcelle obligatoire avant matching num_voie).

Cible : data/secteur_motte_picquet_light.json. Backup
.prechasselousuf.bak. Dry-run par defaut.

Usage :
  python scripts/fix_chasseloup_suffren.py            # DRY-RUN
  python scripts/fix_chasseloup_suffren.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prechasselousuf.bak"

ANCHOR = "126|AVENUE|SUFFREN"
IMMAT = "AF9030966"
BGID = "bdnb-bg-WAEU-1XSX-V5GP"
ORPHS = ["128|AVENUE|SUFFREN", "2|RUE|CHASSELOUP LAUBAT"]
LABEL = "126-128 AV. SUFFREN / 2-4 RUE CHASSELOUP LAUBAT"

# Donnees BDNB enrich figees ici pour reproductibilite (bgid WAEU)
BDNB_ENRICH = {
    "batiment_groupe_id": BGID,
    "nb_log_bdnb": 18,
    "annee_construction": 1972,
    "classe_dpe": None,
    "type_batiment": "appartement",
    "type_chauffage": "reseau de chaleur",
    "usage_principal_bdnb": "Résidentiel collectif",
    "_usage_bdnb_src": "snapshot",
    # Coordonnees : on prend celles du 128 (geocode) decalees
    # legerement vers le 126 (offset −0.000020 lon ~1.5m). Centroide
    # BDNB en EPSG:2154 confirme zone immeuble unique.
    "longitude": 2.305372,
    "latitude": 48.848135,
}

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


def build_anchor_entry(cp):
    """Construit l'entree adresses[] pour 126|AVENUE|SUFFREN injectee."""
    return {
        "cle": ANCHOR,
        "adresse": "126 AVENUE DE SUFFREN",
        "longitude": BDNB_ENRICH["longitude"],
        "latitude": BDNB_ENRICH["latitude"],
        "code_iris": cp.get("code_iris"),
        "_coord_source": "rnc_inject_pattern_suffren",
        "dans_majic": False,
        "sci_proprietaire": "inconnu",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": cp.get("syndic"),
        "_syndic_src": cp.get("_syndic_src") or "rnc",
        "numero_immatriculation": IMMAT,
        "nb_lots_habitation": cp.get("nb_lots_habitation"),
        # ventes vides initialement : seront remplies par les chains
        # fusionnees au rendu (128 SUFFREN)
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation": 0.0,
        "classement_rotation": "Figé",
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Figé",
        "nb_log_bdnb": BDNB_ENRICH["nb_log_bdnb"],
        "annee_construction": BDNB_ENRICH["annee_construction"],
        "classe_dpe": BDNB_ENRICH["classe_dpe"],
        "type_batiment": BDNB_ENRICH["type_batiment"],
        "type_chauffage": BDNB_ENRICH["type_chauffage"],
        "batiment_groupe_id": BGID,
        "_bdnb_match": "immat_inject_pattern_suffren",
        "_taux_logement_src": "filtre_habitation",
        "usage_principal_bdnb": BDNB_ENRICH["usage_principal_bdnb"],
        "_usage_bdnb_src": BDNB_ENRICH["_usage_bdnb_src"],
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    abort = []
    cp = cbc.get(ANCHOR)
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur cle "
                     f"{ANCHOR} (got {cp and cp.get('numero_immatriculation')})")
    if by.get(ANCHOR) is not None:
        abort.append(f"ancre {ANCHOR} deja presente dans adresses[] "
                     "- diagnostic obsolete (l'injection serait un "
                     "doublon)")
    # orphelins doivent exister
    for o in ORPHS:
        if by.get(o) is None:
            abort.append(f"orphelin {o} absent du light")
        else:
            oa = by[o]
            if oa.get("numero_immatriculation") \
                    and oa.get("numero_immatriculation") != IMMAT:
                abort.append(f"orph {o} porte autre immat : "
                             f"{oa.get('numero_immatriculation')}")
            if oa.get("_fusion_auto") and oa.get("_fusion_cible") \
                    and oa.get("_fusion_cible") != ANCHOR:
                abort.append(f"orph {o} fuse vers "
                             f"{oa.get('_fusion_cible')} (collision)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    inject_done = False
    moves = []
    if not abort and cp is not None:
        # INJECT
        new_anchor = build_anchor_entry(cp)
        patched["adresses"].append(new_anchor)
        pby[ANCHOR] = new_anchor
        inject_done = True

        # RE-POINT orphelins (avec adoption MIRROR depuis l'ancre
        # nouvellement injectee = bgid WAEU + champs BDNB enrich)
        for o in ORPHS:
            s = pby.get(o)
            if s is None:
                continue
            if s.get("_fusion_auto") and s.get("_fusion_cible") == ANCHOR:
                continue
            # Adoption MIRROR : bgid + nb_log_bdnb + champs BDNB
            # autoritatifs depuis l'ancre. Pour 2 CHASSELOUP, ca
            # corrige le bgid faux (1GJW -> WAEU) + usage Tertiaire
            # -> Resid collectif. Pour 128 SUFFREN, bgid deja WAEU,
            # MIRROR met les champs en coherence (idempotent).
            for k in MIRROR:
                s[k] = new_anchor.get(k)
            s["_bdnb_match"] = "immat"
            if syn_ok(new_anchor.get("syndic")) \
                    and not syn_ok(s.get("syndic")):
                s["syndic"] = new_anchor.get("syndic")
                s["_syndic_src"] = \
                    (new_anchor.get("_syndic_src") or "rnc") + "_grp"
            s["_fusion_auto"] = True
            s["_fusion_cible"] = ANCHOR
            s["_fusion_auto_sources"] = None
            moves.append(o)

        # Ancre absorbe les orphelins + label multi-voies (documente
        # la 4e facade 4 CHASSELOUP absente du snapshot)
        if moves:
            new_anchor["_fusion_auto_sources"] = sorted(set(moves))
            new_anchor["_fusion_auto_label"] = LABEL

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    # ─── Rapport ───
    print("=" * 78)
    print(f"FIX CHASSELOUP/SUFFREN (AF9030966) HYBRIDE INJECT+RE-POINT — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  Ancre a injecter : {ANCHOR}")
    print(f"  Bgid choisi      : {BGID}")
    print(f"  Immat            : {IMMAT}  copro deja dans coproprietes[]")
    print(f"  Nom copro        : {cp and cp.get('nom_copropriete')!r}")
    print(f"  Lots hab         : {cp and cp.get('nb_lots_habitation')}")
    print(f"  Syndic           : {cp and cp.get('syndic')!r}")
    print(f"  Label fusion     : {LABEL!r}")
    print(f"  Inject done      : {inject_done}")
    print(f"  Re-points        : {len(moves)} -> {moves}")
    print("-" * 78)

    # Etat des orphelins
    for o in ORPHS:
        oa = by.get(o, {})
        pa = pby.get(o, {})
        anc_bg = BGID
        was_bg = oa.get("batiment_groupe_id")
        new_bg = pa.get("batiment_groupe_id")
        bg_change = "OK (idem ancre)" if was_bg == anc_bg \
            else f"CORRIGE {was_bg} -> {new_bg}"
        was_us = oa.get("usage_principal_bdnb")
        new_us = pa.get("usage_principal_bdnb")
        us_change = "OK" if was_us == new_us \
            else f"{was_us!r} -> {new_us!r}"
        print(f"  {o:34s}  vlog={oa.get('nb_ventes_logement') or 0}"
              f"  vtot={oa.get('nb_ventes_total') or 0}"
              f"  nb_log_bdnb_avant={oa.get('nb_log_bdnb')}")
        print(f"    bgid : {bg_change}")
        print(f"    usage: {us_change}")

    print("-" * 78)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "—"))
        v1, k1 = contrib1.get(bg, (0, "—"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc strictement neutre).")
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
    if not inject_done:
        print("ABORT : aucune injection appliquee.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_chasseloup_suffren"] = (
        f"Cas hybride : injection ancre {ANCHOR} (pattern Suffren - "
        "absente d'adresses[] alors que copro AF9030966 SDC '126-128 "
        "Avenue de Suffren' existait dans coproprietes[] sur cle "
        "126|AVENUE|SUFFREN) + re-point 128 SUFFREN + 2 CHASSELOUP "
        "LAUBAT (pattern Cambronne, adoption MIRROR). Bgid choisi "
        "WAEU-1XSX-V5GP (BDNB pivot dit l_libelle_adr=['128 Suffren',"
        "'4 Chasseloup','2 Chasseloup'], annee 1972, 18 log < 33 lots "
        "RNC -> RNC autoritaire). Parcelle BDNB CZ0041 = MATCH "
        "ref_cad_1 RNC '75056115CZ0041'. CORRECTION bgid 2 CHASSELOUP "
        "LAUBAT : passe de 1GJW (= bati TERTIAIRE 3 CHASSELOUP sur "
        "parcelle CZ0047 DIFFERENTE) vers WAEU (vrai bati AF9030966 "
        "parcelle CZ0041) + usage Tertiaire -> Resid collectif - faux "
        "matching make_light. 4 CHASSELOUP LAUBAT absente du snapshot "
        "(pas de MAJIC ni DVF), documentee via _fusion_auto_label="
        f"'{LABEL}' sur l'ancre. 3 CHASSELOUP intouche (bati Tertiaire "
        "distinct, parcelle CZ0047, INCHANGE). Parc "
        f"{parc0}->{parc1} ({delta:+d}) = switch BDNB->RNC sur WAEU "
        "(18 BDNB -> 33 RNC AF9030966). 1 v_log + 2 v_tot relocalises "
        "sous AF9030966 (FIDUCIAIRE DU DISTRICT DE PARIS, date_immat "
        "2020-02-03).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 ancre injectee, {len(moves)} "
          "orphelins re-points)")


if __name__ == "__main__":
    main()
