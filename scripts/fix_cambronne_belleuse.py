"""
Correctif SURGICAL — `13 RUE CARRIER BELLEUSE -> 19 RUE CAMBRONNE`
(AA8571440 IMMEUBLE 19 CAMBRON-13CBELLEUS, 62 lots hab / 201 tot,
GERARD SAFAR SAS PARIS). Confirmation terrain user 2026-05-20.

Triple confirmation source-of-truth :
  - RNC live AA8571440 (tabular-api `3ea8e2c3-0038-...`) :
    `nom_usage_copropriete='IMMEUBLE 19 CAMBRON-13CBELLEUS'`
    (declaratif des 2 voies), `adresse_reference='19 r cambronne'`,
    `adresse_complementaire_1='19-21 r cambronne'`,
    `adresse_complementaire_2='13-13 r carrier-belleuse'`,
    `nombre_adresses_complementaires=2`. 62 lots hab / 201 tot.
    Syndic GERARD SAFAR SAS (SIRET 31817431500065), mandat ->
    2026-09-30.
  - BDNB pivot : bgid `2UC3-3G75-JFPB` (l_libelle_adr = [19, 21]
    CAMBRONNE) + bgid `4CUT-Z57B-XDTM` (l_libelle_adr = [13,
    13B] CARRIER BELLEUSE) -> MEME parcelle 75115000CY0067, MEME
    annee_construction 1977.
  - BDNB enrich : bgid 2UC3 nb_log_bdnb=26 / nb_log_rnc=62 (matche
    AA8571440 exactement) ; bgid 4CUT nb_log_bdnb=33 / nb_log_rnc=
    None (mais MEME parcelle + nom RNC declaratif -> meme ensemble).

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `19|RUE|CAMBRONNE` bgid=2UC3 : copro AA8571440 ATTRIBUEE
    correctement, 62 lots, principal.
  - `13|RUE|CARRIER BELLEUSE` bgid=4CUT (DIVERGENT) : immat=None,
    33 nb_log_bdnb, 4 ventes, _fusion_auto=None. Sur la MEME
    parcelle que 2UC3 mais bgid BDNB distinct -> make_light n'a
    pas fusionne car voies differentes (pattern Fremicourt/
    ARMONIAL : ALIAS_RNC multi-voies manquant pour la paire
    CARRIER BELLEUSE <-> CAMBRONNE).
  - `13B RUE CARRIER BELLEUSE` et `21 RUE CAMBRONNE` : ABSENTES
    du light (BAN non-postal, 0 vente DVF). Source-of-truth
    ALIAS_RNC dans make_light_motte_picquet.py pour re-routage
    si vente future.

Mecanisme : ALIAS_RNC multi-voies (pattern Fremicourt). 13|RUE|
CARRIER BELLEUSE devient secondaire de 19|RUE|CAMBRONNE.
Adoption MIRROR (bgid 2UC3 + nblog_bdnb=26 + usage Resid coll +
champs BDNB autoritatifs de l'ancre).

Effet parc (modele renderSecteur Sec 6) :
  - bgid 2UC3 : reste a 62 lots (RNC AA8571440, inchange).
  - bgid 4CUT : 13 CARRIER (seule adresse non-fusee residentielle
    BDNB) devient fusee -> bucket bgBdnb perd 4CUT (33 lgts).
  -> Delta parc = -33 logements (dedup multi-bgid type ARMONIAL/
     Acollas : les 33 BDNB de 4CUT etaient deja inclus dans les
     62 lots RNC qui couvrent 2UC3+4CUT, PIPELINE Sec 6 lots
     RNC prioritaires).

Ventes relocalisees : 13 CARRIER BELLEUSE (4 ventes total -
verifier nb_ventes_logement) -> AA8571440 (syndic GERARD SAFAR
SAS, classement deja "Actif" sur la copro).

Source-of-truth a porter dans `make_light_motte_picquet.py` :
  - ALIAS_RNC += { "13|RUE|CARRIER BELLEUSE": "19|RUE|CAMBRONNE",
                    "13B|RUE|CARRIER BELLEUSE": "19|RUE|CAMBRONNE",
                    "21|RUE|CAMBRONNE": "19|RUE|CAMBRONNE" }

Cible : data/secteur_motte_picquet_light.json. Backup
.precambronne.bak. Dry-run par defaut.

Usage :
  python scripts/fix_cambronne_belleuse.py            # DRY-RUN
  python scripts/fix_cambronne_belleuse.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.precambronne.bak"

ANCHOR = "19|RUE|CAMBRONNE"
IMMAT = "AA8571440"
ORPHS = ["13|RUE|CARRIER BELLEUSE"]

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
    print(f"FIX CAMBRONNE/CARRIER-BELLEUSE — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
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
    meta["_correctif_cambronne_belleuse"] = (
        "13 RUE CARRIER BELLEUSE -> 19 RUE CAMBRONNE (AA8571440 "
        "IMMEUBLE 19 CAMBRON-13CBELLEUS, 62 lots hab / 201 tot, "
        "GERARD SAFAR SAS, mandat -> 2026-09-30). Triple "
        "confirmation : RNC compl_2='13-13 r carrier-belleuse' + "
        "nom RNC declaratif des 2 voies, BDNB bgids 2UC3 (19+21 "
        "Cambronne) et 4CUT (13+13B Carrier Belleuse) sur MEME "
        "parcelle 75115000CY0067 et MEME annee 1977, nb_log_rnc "
        "BDNB=62 sur 2UC3 matche AA8571440. Pattern ALIAS_RNC "
        "multi-voies (Fremicourt/ARMONIAL) : 13|CARRIER|BELLEUSE "
        "(bgid 4CUT errone, 33 nb_log_bdnb, 4 ventes) re-pointe "
        "vers 19|CAMBRONNE avec adoption MIRROR bgid 2UC3. Parc "
        f"{parc0}->{parc1} ({delta:+d}) = dedup multi-bgid (les "
        "33 BDNB de 4CUT etaient deja compris dans les 62 lots "
        "RNC qui couvrent 2UC3+4CUT, PIPELINE Sec 6 lots RNC "
        "prioritaires). 13B Carrier Belleuse et 21 Cambronne "
        "absentes du light - ALIAS_RNC a porter dans "
        "make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} re-point)")


if __name__ == "__main__":
    main()
