"""
Correctif HYBRIDE — `74 RUE DU DAUPHINE` + `76 RUE DU DAUPHINE` +
`6 RUE PROFESSEUR PAUL SISLEY` (AB4859047 LE PARC SISLEY, 39 lots
hab / 121 tot, REGIE FRANCOIS GOFFIN). Confirmation terrain :
data/audit_copros_multiparcelles.md v2 (RESTANT) + RNC live.

Pattern HYBRIDE Suffren + Cambronne + correction bgid :
  - INJECT `74|RUE|DAUPHINE` dans adresses[] (pattern Suffren) :
    l'ancre RNC est ABSENTE du light alors que la copro
    AB4859047 existe deja dans coproprietes[] (cle_adresse=
    74|RUE|DAUPHINE). make_light n'a pas genere l'entree.
  - RE-POINT `76|RUE|DAUPHINE` -> 74|DAUPHINE (pattern Cambronne).
  - CORRECTION bgid `6|RUE|PROFESSEUR PAUL SISLEY` : actuellement
    sur AM81 (= bati 5 PROF SISLEY, 2010) selon make_light, mais
    BDNB pivot dit que 6 PROF SISLEY est sur bgid ULHW (= bati
    74-76 DAUPHINE, 1988, 39 log = AB4859047). Adoption MIRROR
    corrige cette erreur d'attribution + fusion vers 74|DAUPHINE.

Triple confirmation source-of-truth :
  - RNC live AB4859047 (tabular-api 3ea8e2c3-0038...) :
    nom='LE PARC SISLEY', adresse_reference='74 r du dauphine',
    compl_1='76 r du dauphine', compl_2='6 r du professeur paul
    sisley'. 39 lots hab / 121 tot. REGIE FRANCOIS GOFFIN (SIRET
    74987004400049, mandat -> 2026-09-30, date_immat 2017-11-21,
    derniere maj 2025-11-01). DE_1975_A_1993. 3 parcelles RNC
    AZ0130, AZ0132, AZ0041.
  - BDNB pivot bgid ULHW-P9KF-JSGH : l_libelle_adr = ['76 Rue Du
    Dauphine', '6 Rue Professeur Paul Sisley'] (principal=76,
    sans 74 dans BAN). MEME bgid pour 76 + 6 PROF SISLEY.
  - BDNB enrich bgid ULHW : annee 1988, nb_log=39 (matche
    exactement AB4859047), classe D, 7 niveaux, immeuble,
    electricite.
  - BDNB pivot bgid AM81-DZPJ-QXMN : l_libelle_adr = ['5 Rue
    Professeur Paul Sisley'] uniquement (= autre bati 2010, 6
    log). Donc 6 PROF SISLEY actuel @AM81 = ERREUR make_light.

ANOMALIES LIGHT ACTUELLES (corrigees) :
  - `74|RUE|DAUPHINE` ABSENTE d'adresses[] (anomalie make_light :
    n'a pas cree l'entree alors qu'elle est cle_adresse de
    AB4859047 dans coproprietes[]).
  - `76|RUE|DAUPHINE` bgid=ULHW immat=None _fa=None (orphelin OK
    sur le bon bgid).
  - `6|RUE|PROFESSEUR PAUL SISLEY` bgid=AM81 (FAUX, devrait etre
    ULHW selon BDNB pivot) immat=None _fa=None.

Effet parc (modele renderSecteur Sec 6) :
  - bgid ULHW : avant bgBdnb=39 (via 76 DAUPHINE) -> apres
    bgRncLots={AB4859047:39} (via 74 DAUPHINE injecte) = switch
    BDNB->RNC autoritaire (PIPELINE Sec 6).
  - bgid AM81 : avant bgBdnb=6 (via 5 OU 6 PROF SISLEY, dedup
    first-wins) -> apres bgBdnb=6 (via 5 PROF SISLEY seul, 6
    deplace) = inchange.
  - Parc STRICTEMENT NEUTRE.

Ventes relocalisees au rendu :
  - 76 DAUPHINE : vlog=2 / vtot=3
  - 6 PROF SISLEY : vlog=2 / vtot=3
  - Total 4 v_log + 6 v_tot sous AB4859047 (taux ~2.05% -> Actif).

Source-of-truth a porter dans make_light_dauphine_lacassagne.py :
  - Cas 'cle_adresse copro sans entree adresses' = INJECT auto
    si copro.cle_adresse n'a pas d'entree dans adresses[].
  - ALIAS_RNC += {
      '76|RUE|DAUPHINE': '74|RUE|DAUPHINE',
      '6|RUE|PROFESSEUR PAUL SISLEY': '74|RUE|DAUPHINE'
    }
  - Correction bgid : 6 PROF SISLEY doit etre sur ULHW pas AM81
    (anomalie matching num_voie/GPS).

Cible : data/secteur_dauphine_lacassagne_light.json. Backup
.preparcsisley.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_parc_sisley.py        # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_parc_sisley.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.preparcsisley.bak"

ANCHOR = "74|RUE|DAUPHINE"
IMMAT = "AB4859047"
BGID = "bdnb-bg-ULHW-P9KF-JSGH"
ORPHS = ["76|RUE|DAUPHINE", "6|RUE|PROFESSEUR PAUL SISLEY"]

# Donnees BDNB enrich figees ici pour reproductibilite (bgid ULHW)
BDNB_ENRICH = {
    "batiment_groupe_id": BGID,
    "nb_log_bdnb": 39,
    "annee_construction": 1988,
    "classe_dpe": "D",
    "type_batiment": "immeuble",
    "type_chauffage": "electricite",
    "usage_principal_bdnb": "Résidentiel collectif",
    "_usage_bdnb_src": "bdnb_enrich",
    "longitude": 4.868473,
    "latitude": 45.75235,
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
    """Construit l'entree adresses[] pour 74|RUE|DAUPHINE injectee."""
    return {
        "cle": ANCHOR,
        "adresse": "74 RUE DU DAUPHINE",
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
        # fusionnees au rendu (76 + 6 PROF SISLEY)
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
        # nouvellement injectee = bgid ULHW + champs BDNB enrich)
        for o in ORPHS:
            s = pby.get(o)
            if s is None:
                continue
            # idempotence skip
            if s.get("_fusion_auto") and s.get("_fusion_cible") == ANCHOR:
                continue
            # Adoption MIRROR : bgid + nb_log_bdnb + champs BDNB
            # autoritatifs depuis l'ancre. Pour 6 PROF SISLEY, ca
            # corrige le bgid faux (AM81 -> ULHW). Pour 76 DAUPHINE,
            # bgid deja ULHW, MIRROR met juste les champs en
            # coherence.
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

        # Ancre absorbe les orphelins
        if moves:
            new_anchor["_fusion_auto_sources"] = sorted(set(moves))
            new_anchor.setdefault("_fusion_auto_label", None)

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    # ─── Rapport ───
    print("=" * 78)
    print(f"FIX PARC SISLEY (AB4859047) HYBRIDE INJECT+RE-POINT — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  Ancre a injecter : {ANCHOR}")
    print(f"  Bgid choisi      : {BGID}")
    print(f"  Immat            : {IMMAT}  copro deja dans coproprietes[]")
    print(f"  Nom copro        : {cp and cp.get('nom_copropriete')!r}")
    print(f"  Lots hab         : {cp and cp.get('nb_lots_habitation')}")
    print(f"  Syndic           : {cp and cp.get('syndic')!r}")
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
        print(f"  {o:34s}  vlog={oa.get('nb_ventes_logement') or 0}"
              f"  vtot={oa.get('nb_ventes_total') or 0}"
              f"  nb_log_bdnb_avant={oa.get('nb_log_bdnb')}  "
              f"bgid={bg_change}")

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
    print(f"Parc DL : {parc0} -> {parc1} (delta {delta:+d})")
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
    meta["_correctif_parc_sisley"] = (
        f"Cas hybride : injection ancre {ANCHOR} (pattern Suffren - "
        "absente d'adresses[] alors que copro AB4859047 'LE PARC "
        "SISLEY' existait dans coproprietes[]) + re-point 76 "
        "DAUPHINE + 6 PROF SISLEY (pattern Cambronne, adoption "
        "MIRROR). Bgid choisi ULHW-P9KF-JSGH (BDNB pivot dit "
        "l_libelle_adr=['76 DAUPHINE','6 PROF SISLEY'], annee "
        f"1988, 39 log matche AB4859047 39 lots). CORRECTION bgid "
        "6 PROF SISLEY : passe de AM81 (= 5 PROF SISLEY autre bati "
        "2010) vers ULHW (vrai bati AB4859047) - faux matching "
        f"make_light. Parc {parc0}->{parc1} strictement neutre "
        "(switch BDNB->RNC sur ULHW, AM81 conserve via 5 PROF "
        "SISLEY). 4 v_log + 6 v_tot relocalises sous AB4859047 "
        "(REGIE FRANCOIS GOFFIN, mandat -> 2026-09-30).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 ancre injectee, {len(moves)} "
          "orphelins re-points)")


if __name__ == "__main__":
    main()
