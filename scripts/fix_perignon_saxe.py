"""
Correctif SURGICAL — `10 RUE PERIGNON -> 42 AVENUE DE SAXE` (#AB8151755).
Copro RNC AB8151755 "42, AV. SAXE/10 RUE PERIGNON" (147 lots hab, 22
ventes 2021-2025, ANDRE GRIFFATON S A). Confirmation terrain user
2026-05-20.

Triple confirmation source-of-truth :
  - RNC live AB8151755 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='42, AV. SAXE/10 RUE PERIGNON'`
    (declaratif des 2 voies), `adresse_reference='42 Avenue de Saxe
    75007 Paris'`, `adresse_complementaire_1='42 Avenue de Saxe -
    10 Rue Perignon 75007 PARIS'`, idem compl_2,
    `nombre_adresses_complementaires=2`. 147 lots hab, periode
    AVANT_1949. Syndic ANDRE GRIFFATON S A (date_immat 2018-01-11).
  - BDNB pivot : bgid `QPWJ-BC6L-9W1A` (42 SAXE, immat AB8151755 via
    rel_batiment_groupe_rnc) + bgid `6RE2-LG3N-FXCZ` (10 PERIGNON,
    sans rel RNC) -> MEME parcelle 75107000BO0050, MEME annee
    construction BDNB 1958. La parcelle voisine BO0051 porte le bgid
    TWU6 qui herberge la copro distincte AB7693641 "Saxe-Perignon"
    CONSORTIUM (75 lots, 1890) -> AUCUN conflit, copro separee.
  - BDNB enrich : bgid QPWJ nb_log_bdnb=32 (ancre AB8151755) ; bgid
    6RE2 nb_log_bdnb=27 (sans cp, usage 'Residentiel collectif'). Le
    total BDNB des 2 demi-bati 6RE2+QPWJ = 59, strictement inferieur
    aux 147 lots RNC -> coherent (BDNB sous-couvre, RNC autoritaire).

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `42|AVENUE|SAXE #AB8151755` bgid=QPWJ : copro AB8151755
    ATTRIBUEE correctement, 147 lots, principal.
  - `10|RUE|PERIGNON` bgid=6RE2 (DIVERGENT) : immat=None, 27
    nb_log_bdnb, 5 ventes, _fusion_auto=None. Sur la MEME parcelle
    BO0050 que QPWJ mais bgid BDNB distinct -> make_light n'a pas
    fusionne car voies differentes + lien BDNB->RNC absent
    (rel_batiment_groupe_rnc 0 ligne sur 6RE2). Pattern Fremicourt/
    Cambronne : ALIAS_RNC multi-voies manquant pour la paire
    PERIGNON <-> SAXE de AB8151755.

Mecanisme : ALIAS_RNC multi-voies (pattern Cambronne). 10|RUE|
PERIGNON devient secondaire de 42|AVENUE|SAXE #AB8151755. Adoption
MIRROR (bgid QPWJ + nb_log_bdnb=32 + usage Tertiaire + champs BDNB
autoritatifs de l'ancre).

Effet parc (modele renderSecteur Sec 6) :
  - bgid QPWJ : reste a 147 lots (RNC AB8151755, inchange).
  - bgid 6RE2 : 10 PERIGNON (seule adresse non-fusee residentielle
    BDNB) devient fusee -> bucket bgBdnb perd 6RE2 (27 lgts).
  -> Delta parc = -27 logements (dedup multi-bgid type Cambronne :
     les 27 BDNB de 6RE2 etaient deja inclus dans les 147 lots RNC
     qui couvrent QPWJ+6RE2, PIPELINE Sec 6 lots RNC prioritaires).

Ventes relocalisees : 10 PERIGNON (5 ventes logement) -> AB8151755
(syndic GRIFFATON, deja classement Actif a 3.0/an logement). Total
ventes consolidees AB8151755 sera 22+5=27 sur 5 ans = 5.4/an
logement (Tres actif probable au prochain calcul).

Source-of-truth a porter dans `make_light_motte_picquet.py` :
  - ALIAS_RNC += { "10|RUE|PERIGNON": "42|AVENUE|SAXE #AB8151755" }

Cible : data/secteur_motte_picquet_light.json. Backup
.preperignonsaxe.bak. Dry-run par defaut.

Usage :
  python scripts/fix_perignon_saxe.py            # DRY-RUN
  python scripts/fix_perignon_saxe.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.preperignonsaxe.bak"

ANCHOR = "42|AVENUE|SAXE #AB8151755"
IMMAT = "AB8151755"
ORPHS = ["10|RUE|PERIGNON"]

# Adoption MIRROR : champs autoritatifs BDNB copies depuis l'ancre
MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


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
        abort.append(f"ancre {ANCHOR} elle-meme fusionnee "
                     f"(-> {da.get('_fusion_cible')})")
    # garde : aucun orph ne doit porter un autre immat RNC
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
    print(f"FIX PERIGNON/SAXE — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCHOR : {ANCHOR}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots  "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Syndic : {(cp and cp.get('syndic')) or '—'}")
    print(f"  Re-points ({len(moves)}) :")
    for cle in moves:
        a0 = by.get(cle, {})
        print(f"    {cle:32s}  bgid_avant={a0.get('batiment_groupe_id')}"
              f"  vlog={a0.get('nb_ventes_logement')}"
              f"  vtot={a0.get('nb_ventes_total')}"
              f"  nb_log_bdnb={a0.get('nb_log_bdnb')}"
              f"  usage={a0.get('usage_principal_bdnb')!r}")
    print("-" * 78)
    # Detail des bgids impactes
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
        for a in abort:
            print("  - " + a)
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
    meta["_correctif_perignon_saxe"] = (
        "10 RUE PERIGNON -> 42 AVENUE DE SAXE #AB8151755 (AB8151755 "
        "'42, AV. SAXE/10 RUE PERIGNON', 147 lots hab, ANDRE "
        "GRIFFATON S A, date_immat 2018-01-11). Triple confirmation : "
        "RNC compl_1/_2='42 Avenue de Saxe - 10 Rue Perignon' + nom "
        "RNC declaratif des 2 voies, BDNB bgids QPWJ (42 SAXE, immat "
        "AB8151755) et 6RE2 (10 PERIGNON, sans rel RNC) sur MEME "
        "parcelle 75107000BO0050 et MEME annee BDNB 1958 (la parcelle "
        "voisine BO0051 bgid TWU6 herberge la copro DISTINCTE "
        "AB7693641 'Saxe-Perignon' CONSORTIUM 75 lots 1890, aucun "
        "conflit). Pattern ALIAS_RNC multi-voies (Cambronne/"
        "Fremicourt) : 10|RUE|PERIGNON (bgid 6RE2 errone, 27 "
        "nb_log_bdnb, 5 ventes) re-pointe vers 42|AVENUE|SAXE "
        "#AB8151755 avec adoption MIRROR bgid QPWJ. Parc "
        f"{parc0}->{parc1} ({delta:+d}) = dedup multi-bgid (les 27 "
        "BDNB de 6RE2 etaient deja compris dans les 147 lots RNC qui "
        "couvrent QPWJ+6RE2, PIPELINE Sec 6 lots RNC prioritaires). "
        "ALIAS_RNC a porter dans make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} re-point)")


if __name__ == "__main__":
    main()
