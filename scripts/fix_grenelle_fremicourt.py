"""
Correctif SURGICAL — `23/25/27 RUE FREMICOURT -> 146 BD GRENELLE`
(AA0469049 RESIDENCE GRENELLE FREMICOURT, 316 lots, ATRIUM GESTION
PARIS 15). Confirmation terrain user 2026-05-20.

Triple confirmation source-of-truth :
  - RNC live AA0469049 : adresse_reference=146 BD GRENELLE +
    adresse_complementaire_1=27 r fremicourt + compl_2=25 +
    compl_3=23 (les 3 slots open-data exhibent exactement les 3
    cibles, nb_adr_compl=3).
  - BDNB bgid 1TM4-6XEE-7D4Q (146 GRENELLE) : l_libelle_adr =
    [144/146 BD GRENELLE, 21B/23/25/27/29 RUE FREMICOURT] = 7
    adresses BAN sur le meme bati (1965, 13 niveaux, 6258 m2, 306
    lgts BDNB / 316 RNC).
  - Syndic ATRIUM GESTION PARIS 15 identique sur 23/25/27/146.

ANOMALIES LIGHT ACTUELLES (corrigees par ce fix) :
  - 23 RUE FREMICOURT bgid=TPGT (= bgid de 22 FREMICOURT, autre copro
    AC0129718 41 lots) : faux bgid assigne par make_light num_voie.
  - 25 RUE FREMICOURT bgid=1C2P (= bgid de 24 FREMICOURT, copro
    distincte) : faux bgid idem.
  - 27 RUE FREMICOURT bgid=28QF (= bgid de 28 FREMICOURT, copro
    distincte AB3441680 16 lots, aussi ATRIUM) : faux bgid idem.
  - 23/25 sont deja fuses vers 27 (cross-bgid, syndic ATRIUM propage)
    par un correctif anterieur. 27 reste principal hr-active.
  - 22 (AC0129718), 24 (autre), 28 (AB3441680) restent inchanges -
    ce sont des copros distinctes voisines.

Mecanisme : ALIAS_RNC multi-voies (pattern ARMONIAL). 27 + chain
(23, 25) deviennent secondaires de 146 GRENELLE. Adoption MIRROR
(bgid 1TM4 + nblog 306 + usage Resid coll + champs BDNB derives).

Parc effet (modele renderSecteur Sec 6) :
  - bgid 1TM4 : reste a 316 (lots RNC AA0469049 via 146, inchange).
  - bgid TPGT : reste a 26 (via 22 FREMICOURT principal, 23 etait
    deja fuse donc ne contribuait pas).
  - bgid 1C2P : reste a 36 (via 24 FREMICOURT, 25 etait fuse).
  - bgid 28QF : 27 etait Tertiaire (pas dans bgBdnb) + 28 Resid 15
    -> 28QF=15 ; apres = 15 (27 devient fuse, mais ne contribuait
    pas car Tertiaire).
  -> Parc STRICTEMENT NEUTRE. Le script ABORT si delta != 0.

Ventes relocalisees : 27 (2 v_log / 2 v_tot) + chain 23 (0/0) + 25
(0/2) = 2 v_log + 4 v_tot sous AA0469049 RESIDENCE GRENELLE
FREMICOURT.

Source-of-truth a porter : ALIAS_RNC += { 23/25/27 RUE FREMICOURT
-> 146 BD GRENELLE } dans make_light_motte_picquet.py.

Cible : data/secteur_motte_picquet_light.json. Backup
.pregrenellefrem.bak. Dry-run par defaut.

Usage :
  python scripts/fix_grenelle_fremicourt.py            # DRY-RUN
  python scripts/fix_grenelle_fremicourt.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.pregrenellefrem.bak"

ANCHOR = "146|BOULEVARD|GRENELLE"
IMMAT = "AA0469049"
# Cibles : 27 (principal hr-active actuel) + chain (23, 25 deja fuses dans 27)
ORPHS = ["27|RUE|FREMICOURT", "25|RUE|FREMICOURT", "23|RUE|FREMICOURT"]

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

    parc0 = parc_model(light)
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

    if moves:
        cur = list(pda.get("_fusion_auto_sources") or [])
        pda["_fusion_auto_sources"] = sorted(set(cur + moves))
        pda.setdefault("_fusion_auto_label", None)

    parc1 = parc_model(patched)
    neutral = (parc1 == parc0)

    print("=" * 78)
    print(f"FIX GRENELLE/FREMICOURT — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCHOR : {ANCHOR}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots  "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Re-points ({len(moves)}) :")
    for cle in moves:
        a0 = by.get(cle, {})
        print(f"    {cle:24s}  bgid_avant={a0.get('batiment_groupe_id')}"
              f"  fcible_avant={a0.get('_fusion_cible')!r}"
              f"  vlog={a0.get('nb_ventes_logement')}"
              f"  vtot={a0.get('nb_ventes_total')}"
              f"  usage={a0.get('usage_principal_bdnb')!r}")
    print("-" * 78)
    print(f"Parc modele MP : {parc0} -> {parc1} "
          f"(delta {parc1-parc0:+d}, neutre={'OUI' if neutral else 'NON'})")
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
        print("Idempotent : deja applique.")
        return
    if not neutral:
        print("ABORT : modele parc NON neutre -> fix non sur.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_grenelle_fremicourt"] = (
        "23/25/27 RUE FREMICOURT -> 146 BD GRENELLE (AA0469049 "
        "RESIDENCE GRENELLE FREMICOURT, 316 lots, ATRIUM). "
        "Confirmation triple : RNC compl_1/2/3 = 27/25/23 FREMICOURT, "
        "BDNB bgid 1TM4 liste les 7 adr BAN, syndic ATRIUM identique. "
        "Bgids light errones (TPGT/1C2P/28QF = voisins 22/24/28 qui "
        "sont d'autres copros) corriges par adoption MIRROR vers 1TM4. "
        f"Parc {parc0}->{parc1} strictement neutre. 2 v_log + 2 v_tot "
        "relocalises sous AA0469049.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} re-points)")


if __name__ == "__main__":
    main()
