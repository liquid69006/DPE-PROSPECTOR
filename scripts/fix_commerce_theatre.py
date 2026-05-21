"""
Correctif SURGICAL - `55 RUE DU COMMERCE -> 115 RUE DU THEATRE`
(AC9381674 'SDC 115 RUE DU THEATRE', 62 lots tot / 26 hab,
FONCIA PARIS RIVE DROITE). Detecte par scan parcelle cadastrale
2026-05-21 (scan_horsrnc_parcelle_mp.py).

Pattern Cambronne RE-FUSE multi-bgid (clone fix_cambronne_belleuse).
Le bati 55 COMMERCE (bgid ZC1A) et le bati 115 THEATRE (bgid NVZ2)
sont sur la MEME parcelle BDNB 75115000EF0065, AC9381674 declare
cette unique parcelle dans son ref_cad_1 RNC.

Triple confirmation source-of-truth :
  - BDNB pivot : bgid ZC1A-K8AP-RZ1P (l_libelle_adr=['55 Rue Du
    Commerce'], parcelle 75115000EF0065, annee=1913, nb_log=6)
    + bgid NVZ2-TY7G-Q7SJ (l_libelle_adr=['115 Rue Du Theatre'],
    parcelle 75115000EF0065 IDENTIQUE, annee=1913 IDENTIQUE,
    nb_log=15, nb_log_rnc=26 matche AC9381674).
  - RNC live AC9381674 : ref_cad_1=75056115EF0065 UNIQUE
    (ref_cad_2/3 vides), nom='SDC 115 RUE DU THEATRE',
    adresse_reference='115 r du theatre 75015 Paris',
    nombre_total_lots=62, nombre_lots_usage_habitation=None
    (= heritage RNC, lots_habitation=26 dans le snapshot light).
  - Syndic IDENTIQUE : FONCIA PARIS RIVE DROITE des deux cotes.
  - Voies parallles 15e arr (Commerce // Theatre) : facades sur
    le meme bati avec 2 rues adjacentes (pattern Fremicourt).

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - `115|RUE|THEATRE` bgid=NVZ2 : copro AC9381674 ATTRIBUEE
    correctement, ancre RNC OK, 26 lots hab, _fusion_auto=None,
    _fusion_auto_sources absent.
  - `55|RUE|COMMERCE` bgid=ZC1A : MEME parcelle BDNB, MEME annee,
    MEME syndic, mais immat=None, 6 nb_log_bdnb, 3 ventes_log,
    'Tres actif' -> make_light n'a pas fusionne car voies
    differentes (pattern Fremicourt / CARRIER-BELLEUSE / ARMONIAL
    : ALIAS_RNC multi-voies manquant pour la paire COMMERCE <->
    THEATRE).

Mecanisme : ALIAS_RNC multi-voies. 55|RUE|COMMERCE devient
secondaire de 115|RUE|THEATRE. Adoption MIRROR (bgid NVZ2 +
nb_log_bdnb=15 + usage Resid coll + champs BDNB autoritatifs de
l'ancre).

Effet parc (modele renderSecteur Sec 6) :
  - bgid NVZ2 : reste a 26 lots (RNC AC9381674, inchange).
  - bgid ZC1A : 55 COMMERCE (seule adresse non-fusee residentielle
    BDNB) devient fusee -> bucket bgBdnb perd ZC1A (6 lgts).
  -> Delta parc = -6 logements (dedup multi-bgid type CAMBRONNE /
     ARMONIAL : les 6 BDNB de ZC1A etaient deja inclus dans les
     26 lots RNC qui couvrent NVZ2+ZC1A, Sec 6 lots RNC
     prioritaires).

Ventes relocalisees : 55 COMMERCE (3 vlog, 'Tres actif') ->
AC9381674 sous 115 THEATRE (3 vlog deja, classement 'Actif').
Apres fix : 5 vlog cumules sous AC9381674 (taux ~ 3.8% Tres
actif sur 26 lots).

Source-of-truth a porter dans make_light_motte_picquet.py :
  - ALIAS_RNC += { "55|RUE|COMMERCE": "115|RUE|THEATRE" }

Cible : data/secteur_motte_picquet_light.json. Backup
.precommercetheatre.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_commerce_theatre.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_commerce_theatre.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.precommercetheatre.bak"

ANCHOR = "115|RUE|THEATRE"
IMMAT = "AC9381674"
ORPHS = ["55|RUE|COMMERCE"]

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
            continue
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
        pda.setdefault("_fusion_auto_label",
                       "55 RUE DU COMMERCE / 115 RUE DU THEATRE")
        if pda.get("_fusion_auto_label") in (None, ""):
            pda["_fusion_auto_label"] = ("55 RUE DU COMMERCE / "
                                         "115 RUE DU THEATRE")

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX COMMERCE/THEATRE (AC9381674) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCHOR : {ANCHOR}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots  "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Syndic : {(cp and cp.get('syndic')) or '-'}")
    print(f"  Re-points ({len(moves)}) :")
    for cle in moves:
        a0 = by.get(cle, {})
        print(f"    {cle:32s}  bgid_avant={a0.get('batiment_groupe_id')}"
              f"  vlog={a0.get('nb_ventes_logement')}"
              f"  vtot={a0.get('nb_ventes_total')}"
              f"  nb_log_bdnb={a0.get('nb_log_bdnb')}"
              f"  usage={a0.get('usage_principal_bdnb')!r}")
    print("-" * 78)
    print(f"  ANCHOR label : {pda.get('_fusion_auto_label')!r}")
    print(f"  Sources fusionnees : {pda.get('_fusion_auto_sources')}")
    print("-" * 78)
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
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
    meta["_correctif_commerce_theatre"] = (
        "55 RUE DU COMMERCE -> 115 RUE DU THEATRE (AC9381674 "
        "'SDC 115 RUE DU THEATRE', 62 lots tot / 26 hab, FONCIA "
        "PARIS RIVE DROITE). Detecte par scan parcelle cadastrale "
        "2026-05-21 (scan_horsrnc_parcelle_mp.py). Triple "
        "confirmation : BDNB pivot bgids ZC1A (55 Commerce) et "
        "NVZ2 (115 Theatre) sur MEME parcelle 75115000EF0065 et "
        "MEME annee 1913 ; AC9381674 ref_cad_1=75056115EF0065 "
        "UNIQUE ; syndic FONCIA PARIS RIVE DROITE IDENTIQUE des "
        "deux cotes. Voies parallles 15e arr (Commerce // Theatre) "
        "= pattern Fremicourt classique. Pattern ALIAS_RNC multi-"
        "voies (CAMBRONNE/ARMONIAL) : 55|RUE|COMMERCE (bgid ZC1A, "
        "6 nb_log_bdnb, 3 vlog 'Tres actif') re-pointe vers "
        "115|RUE|THEATRE avec adoption MIRROR bgid NVZ2. Label "
        "'55 RUE DU COMMERCE / 115 RUE DU THEATRE'. Parc "
        f"{parc0}->{parc1} ({delta:+d}) = dedup multi-bgid (les "
        "6 BDNB de ZC1A etaient deja compris dans les 26 lots "
        "RNC qui couvrent NVZ2+ZC1A). 3 vlog DVF relocalises sous "
        "AC9381674. Source-of-truth a porter make_light : "
        "ALIAS_RNC += {'55|RUE|COMMERCE': '115|RUE|THEATRE'}.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (re-fuse {ORPHS} -> {ANCHOR})")


if __name__ == "__main__":
    main()
