"""
Correctif SURGICAL — Extension ARMONIAL I (AA0646265) avec le coté
PAIR de la rue Cèpre (2/4/6/8). Confirmation terrain utilisateur
2026-05-20 : `2/4/6/8 RUE CEPRE + 20 RUE MIOLLIS` = une seule copro,
qui est ARMONIAL I (déjà rattachée pour Cèpre odd 13/15/17/19 +
Miollis pair 20-40 + Carrier-Belleuse 7/9/11, anchor 16 BD GARIBALDI).

ARMONIAL I : grand ensemble social de 592 lots, syndicat principal,
nombre_adresses_complementaires=14 au RNC mais open data ne montre que
3 slots (compl_1/2/3) -> les 11 autres adresses sont CACHEES dans
l'open-data RNC. Make_light en a déjà mappé 16 par déduction du nom
copro/secteur. Les 2/4/6/8 CEPRE n'avaient pas été mappés.

BDNB context :
- bgid XDM8-1XCX-84Y1 (1965, 20 lgts) liste BAN = 2 CEPRE + 4 CEPRE
  + 20 MIOLLIS (corner Cèpre/Miollis). MAIS dans le light, 2/4 CEPRE
  sont sur Z2Z2 (autre bgid) — make_light a inversé.
- bgid Z2Z2-65KJ-U324 (1972, 11 lgts) liste BAN = 6 + 8 CEPRE (bâti
  distinct adjacent). Le light a aussi 2 + 4 CEPRE sur Z2Z2 (par
  default num_voie/GPS, divergence vs BDNB authoritative).
- Indépendamment de la divergence bgid light vs BDNB, **terrain dit
  que les 4 numeros pair Cèpre sont la MEME copro = ARMONIAL I**
  (multi-bati, comme les 6 autres bgids deja membres).

Etat actuel dans le light :
- 2|RUE|CEPRE : principal (vlog=1), bgid Z2Z2, fsrcs=[4 CEPRE, 6 CEPRE]
- 4|RUE|CEPRE : fusé dans 2 CEPRE
- 6|RUE|CEPRE : fusé dans 2 CEPRE (vlog=1)
- 8|RUE|CEPRE : ABSENT (pas de DVF, juste BAN/BDNB) -> traité au
  niveau source-of-truth pour future regen

Mécanisme : **ALIAS_RNC multi-voies** (pattern ARMONIAL existant).
2|RUE|CEPRE et sa chaine (4, 6) deviennent secondaires de
16|BOULEVARD|GARIBALDI (AA0646265). Champs autoritatifs inchangés
(adoption MIRROR optionnelle, le bgid Z2Z2 -> LJRN s'aligne avec la
copro principale).

Parc effet (modele renderSecteur Sec 6) :
- Avant : bgid Z2Z2 contribue 11 (bgBdnb via 2 CEPRE principal
  résidentiel, pas de copro sur ce bgid).
- Après : 2 CEPRE + chain fusés -> skip dans parc, Z2Z2 disparait.
  16 BD GARIBALDI (bgid LJRN) reste principal avec lots RNC 592
  (inchange). Net parc : -11 = retrait d'un BDNB phantom (le bati
  Z2Z2 est en realite couvert par ARMONIAL I 592 lots, mais sans
  immat propre ; le BDNB l'estimait 11 lgts en independant -> dedup
  conforme PIPELINE Sec 6 "lots RNC prioritaire").

Ventes : 2 CEPRE (1 v_log) + 6 CEPRE (1 v_log via chaine) = 2 v_log
relocalisees sous AA0646265 ARMONIAL I. Champs ventes INCHANGES.

Source-of-truth : ALIAS_RNC += { 2/4/6/8 RUE CEPRE -> 16 BD GARIBALDI }
dans make_light_motte_picquet.py.

Cible : data/secteur_motte_picquet_light.json. Backup .prearmonial2.bak.
Dry-run par defaut.

Usage :
  python scripts/fix_armonial_pair_cepre.py          # DRY-RUN
  python scripts/fix_armonial_pair_cepre.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prearmonial2.bak"

ANCHOR = "16|BOULEVARD|GARIBALDI"
IMMAT = "AA0646265"
# (orph, role T=cible utilisateur ; on traite la chaine separement)
ORPHS = ["2|RUE|CEPRE", "4|RUE|CEPRE", "6|RUE|CEPRE"]
# 8|RUE|CEPRE absent du light, traite uniquement en source-of-truth

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

    da = by.get(ANCHOR)
    cp = cbc.get(ANCHOR)
    abort = []
    if da is None:
        abort.append(f"anchor absent : {ANCHOR}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANCHOR} "
                     f"(got {cp and cp.get('numero_immatriculation')})")
    if da and da.get("_fusion_auto") and da.get("_fusion_cible"):
        abort.append(f"anchor {ANCHOR} elle-meme fusionnee")

    # chaine deja absorbee par chaque orph dans le light (a co-rediriger)
    chain_of = {}
    for orph in ORPHS:
        chain_of[orph] = [a["cle"] for a in light["adresses"]
                          if a.get("_fusion_cible") == orph]

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pda = pby.get(ANCHOR)

    moves = []                                # (cle, role)
    for orph in ORPHS:
        s = pby.get(orph)
        if s is None:
            continue
        # idempotence : deja vers anchor ?
        if s.get("_fusion_auto") and s.get("_fusion_cible") == ANCHOR:
            continue
        # adoption MIRROR (anchor bgid LJRN, usage Tertiaire dans light
        # mais c'est OK : la copro AA0646265 domine via bgRncLots ; le
        # mirror aligne juste l'orph sur le bati principal d'ARMONIAL I)
        for k in MIRROR:
            s[k] = pda.get(k)
        s["_bdnb_match"] = "immat"
        if syn_ok(pda.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = pda.get("syndic")
            s["_syndic_src"] = (pda.get("_syndic_src") or "rnc") + "_grp"
        s["_fusion_auto"] = True
        s["_fusion_cible"] = ANCHOR
        s["_fusion_auto_sources"] = None
        moves.append((orph, "T"))
        # re-rediriger la chaine de l'orph (4 et 6 etaient fuses dans 2)
        for cle_ch in chain_of[orph]:
            if cle_ch in ORPHS:               # already handled as orph
                continue
            x = pby.get(cle_ch)
            if x is None:
                continue
            x["_fusion_auto"] = True
            x["_fusion_cible"] = ANCHOR
            x["_fusion_auto_sources"] = None
            moves.append((cle_ch, "D"))

    # anchor : union des nouvelles sources
    if moves:
        cur = list(pda.get("_fusion_auto_sources") or [])
        added = [m[0] for m in moves]
        pda["_fusion_auto_sources"] = sorted(set(cur + added))
        pda.setdefault("_fusion_auto_label", None)

    parc1 = parc_model(patched)

    print("=" * 78)
    print(f"ARMONIAL I extension pair-CEPRE — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCHOR  : {ANCHOR}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots  "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Adresses re-pointees vers ANCHOR ({len(moves)}) :")
    for cle, role in moves:
        a0 = by.get(cle, {})
        print(f"    [{role}] {cle:24s}  bgid_avant={a0.get('batiment_groupe_id')}"
              f"  vlog={a0.get('nb_ventes_logement')}"
              f"  fcible_avant={a0.get('_fusion_cible')!r}")
    print("-" * 78)
    print(f"Parc modele MP : {parc0} -> {parc1} (delta {parc1-parc0:+d})")
    print(f"  Note : delta -11 = retrait du BDNB phantom Z2Z2 (bati que "
          "ARMONIAL I couvre conceptuellement via 592 lots RNC, mais "
          "sans immat propre ; conforme PIPELINE Sec 6).")
    print(f"  Source-of-truth a porter : ALIAS_RNC += {{ 2/4/6/8 RUE "
          "CEPRE -> 16 BD GARIBALDI }} dans make_light_motte_picquet.py")
    print("=" * 78)
    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie.")
        return
    if not moves:
        print("Idempotent : aucun changement (deja applique).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_armonial_pair"] = (
        f"Extension ARMONIAL I (AA0646265) avec 2/4/6 RUE CEPRE "
        "(8 absent light, traite source-of-truth). Confirmation "
        "terrain 2026-05-20 : pair-CEPRE + 20 MIOLLIS = ARMONIAL I "
        "(multi-bati, deja 16 sources sur 6 bgids distincts). RNC "
        "declare 14 adr_complementaires (open data tronque a 3 slots, "
        "11 cachees). Pattern ALIAS_RNC multi-voies. 2 v_log "
        "relocalisees sous AA0646265. Parc MP "
        f"{parc0}->{parc1} ({parc1-parc0:+d} = retrait BDNB phantom "
        "Z2Z2 dedoublonne).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} adresses re-pointees)")


if __name__ == "__main__":
    main()
