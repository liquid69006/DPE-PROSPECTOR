"""
Correctif SURGICAL — Detachement pairs RUE CEPRE + 20 MIOLLIS de
ARMONIAL I (correction d'une erreur historique). Confirmation
terrain user 2026-05-21.

Contexte de l'erreur :
  - Les commits anterieurs (_correctif_armonial_pair, _correctif_
    armonial_8cepre) ont rattache 2/4/6/8 RUE CEPRE + 20 RUE MIOLLIS
    a ARMONIAL I (AA0646265, ancre 16 BD GARIBALDI bgid LJRN) sur
    confirmation terrain de l'epoque, malgre divergence BDNB pivot
    (l_libelle_adr LJRN ne contient QUE les impairs Cepre 1,3,5,7,
    9,11,13,15,17,19).
  - Nouveau signal terrain 2026-05-21 : 'ARMONIAL ne couvre que les
    IMPAIRS de la rue Cepre. Les pairs (2, 6) ont ete rattaches par
    erreur. 6 = meme ensemble que 8 (pas Armonial).'
  - BDNB confirme via rel_adresse + pivot batiment_groupe_complet :
    * bgid XDM8-1XCX-84Y1 (parcelle CY0046, 1965, 20 nb_log, Resid
      coll) = bati avec 2+4 RUE CEPRE + 20 RUE MIOLLIS (rel_adresse
      75115_1646_00002+_00004 + 75115_6377_00020).
    * bgid Z2Z2-65KJ-U324 (parcelle CY0047, 1972, 11 nb_log, Resid
      coll) = bati avec 6+8 RUE CEPRE (rel_adresse 75115_1646_00006
      +_00008).
    * Vente DVF 26/07/2022 17M EUR sur CY/46 = MATCHE XDM8 (vente
      bloc 17M = mono-propriete probable de l'ensemble 20 log).
    * Vente DVF 26/07/2022 15.5M EUR sur CY/47 = MATCHE Z2Z2 (idem
      11 log mono-propriete).
    * Aucune copro RNC sur XDM8 (rel_RNC=0) ni Z2Z2 (rel_RNC=0) ni
      RNC live aux voies 2/4/6/8 CEPRE (recherche tabular-api).
  - Correction 13|RUE|CEPRE : actuellement bgid VQB9 (= bati 2003
    Tertiaire 12/14 CEPRE) selon make_light (faux matching num_voie),
    mais BAN cle 75115_1646_00013 -> bgid LJRN selon BDNB rel_adresse
    + LJRN pivot l_libelle_adr inclut '13 Rue Cepre'. Correction bgid
    pattern 2 CHASSELOUP (validation BAN/parcelle obligatoire). Reste
    fused vers ARMONIAL (cohérent BAN+pivot).

Plan correctif (4 etapes A+B+C+D) :

A) 2 + 4 RUE CEPRE + 20 RUE MIOLLIS detaches d'ARMONIAL -> bati XDM8
   - 2|RUE|CEPRE : bgid LJRN -> XDM8, MIRROR Resid coll 1965 20 log,
     devient ancre interne (sort de fusion), label '2/4 RUE CEPRE /
     20 RUE MIOLLIS', sources=['4|RUE|CEPRE','20|RUE|MIOLLIS']
   - 4|RUE|CEPRE : bgid LJRN -> XDM8, MIRROR, fused vers 2|RUE|CEPRE
   - 20|RUE|MIOLLIS : bgid deja XDM8 (correct), MIRROR conservateur,
     re-fuse 16|BD|GARIBALDI -> 2|RUE|CEPRE
   - Syndic 'non connu' (heritage MIRROR ARMONIAL) supprime sur les 3
     (ARMONIAL n'est pas la copro de cet ensemble)

B) 6 + 8 RUE CEPRE detaches d'ARMONIAL -> bati Z2Z2
   - 6|RUE|CEPRE : bgid LJRN -> Z2Z2, MIRROR Resid coll 1972 11 log,
     devient ancre interne, label '6/8 RUE CEPRE', sources=['8|RUE|
     CEPRE']
   - 8|RUE|CEPRE : bgid LJRN -> Z2Z2, MIRROR, fused vers 6|RUE|CEPRE
   - Syndic supprime sur les 2

C) Correction bgid 13|RUE|CEPRE : VQB9 -> LJRN (selon BAN+pivot)
   - MIRROR LJRN (annee 1976, usage Tertiaire, nb_log_bdnb 555 -
     mais le 13 reste fused vers ARMONIAL donc exclu de bgBdnb au
     calcul parc)
   - Reste _fusion_auto=True _fusion_cible=16|BD|GARIBALDI

D) ANCRE ARMONIAL 16|BD|GARIBALDI : retirer 5 sources erronees
   - Sources avant (20) : 2/4/6/8 CEPRE + 20 MIOLLIS + 11 CB + 13/15/
     17/19 CEPRE + 24/26/28/30/32/34/36/40 MIOLLIS + 7/9 CB
   - Sources apres (15) : 11 CB + 13/15/17/19 CEPRE + 24/26/28/30/32/
     34/36/40 MIOLLIS + 7/9 CB

Effet parc (modele renderSecteur Sec 6) :
  - bgid LJRN ARMONIAL : reste 592 lots RNC (via 16 GAR ancre +
    AA0646265 attribue), bgRncLots inchange.
  - bgid XDM8 : nouvelle ancre interne 2|RUE|CEPRE Resid coll 20 log
    -> bgBdnb[XDM8] = 20. (+20 parc)
  - bgid Z2Z2 : nouvelle ancre interne 6|RUE|CEPRE Resid coll 11 log
    -> bgBdnb[Z2Z2] = 11. (+11 parc)
  - bgid VQB9 (12/14 CEPRE) : reste avec ancre 12, 14 fused (Tertiaire
    exclu) - inchange (13 sort de VQB9 -> LJRN, exclu fused).
  -> Delta parc = +31 logements (20+11 BDNB hors-RNC nouvellement
     exposes au calcul, PIPELINE Sec 6 fallback BDNB residentiel).

Note utilisateur : les ventes bloc DVF 17M EUR (2 CEPRE CY/46) et
15.5M EUR (6 CEPRE CY/47) suggerent des mono-proprietes actuelles.
L'utilisateur peut qualifier 'mono' via le menu UI apres ce fix ->
getEffectiveLog(a)=1 -> delta parc reel devient +2 au lieu de +31
(implementation commit ee3185f).

Source-of-truth a porter dans make_light_motte_picquet.py (hors-repo,
pipeline local utilisateur) :
  - RETIRER : ALIAS_RNC '2|RUE|CEPRE' -> '16|BOULEVARD|GARIBALDI'
  - RETIRER : ALIAS_RNC '4|RUE|CEPRE' -> '16|BOULEVARD|GARIBALDI'
  - RETIRER : ALIAS_RNC '6|RUE|CEPRE' -> '16|BOULEVARD|GARIBALDI'
  - RETIRER : ALIAS_RNC '8|RUE|CEPRE' -> '16|BOULEVARD|GARIBALDI'
  - RETIRER : ALIAS_RNC '20|RUE|MIOLLIS' -> '16|BOULEVARD|GARIBALDI'
  - AJOUTER : correction bgid 13|RUE|CEPRE -> LJRN (validation
    BAN/parcelle, pattern 2 CHASSELOUP)
  - AJOUTER : correction bgid 2/4 CEPRE + 20 MIOLLIS -> XDM8
  - AJOUTER : correction bgid 6/8 CEPRE -> Z2Z2

Cible : data/secteur_motte_picquet_light.json. Backup
.prearmonialpairdetach.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_armonial_pair_detach.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_armonial_pair_detach.py --apply
"""

import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prearmonialpairdetach.bak"

ARMONIAL_ANCHOR = "16|BOULEVARD|GARIBALDI"
LJRN = "bdnb-bg-LJRN-ABEM-2VT5"   # ARMONIAL (impairs Cepre)
XDM8 = "bdnb-bg-XDM8-1XCX-84Y1"   # 2+4 Cepre + 20 Miollis (Resid 1965)
Z2Z2 = "bdnb-bg-Z2Z2-65KJ-U324"   # 6+8 Cepre (Resid 1972)
VQB9 = "bdnb-bg-VQB9-WF5V-KQ2A"   # 10/12/14 Cepre (Tertiaire 2003)

# Donnees BDNB enrich figees ici pour reproductibilite
XDM8_DATA = {
    "batiment_groupe_id": XDM8,
    "nb_log_bdnb": 20,
    "annee_construction": 1965,
    "usage_principal_bdnb": "Résidentiel collectif",
    "_usage_bdnb_src": "snapshot",
    "classe_dpe": None,
    "type_batiment": "appartement",
    "type_chauffage": None,
}
Z2Z2_DATA = {
    "batiment_groupe_id": Z2Z2,
    "nb_log_bdnb": 11,
    "annee_construction": 1972,
    "usage_principal_bdnb": "Résidentiel collectif",
    "_usage_bdnb_src": "snapshot",
    "classe_dpe": None,
    "type_batiment": "appartement",
    "type_chauffage": None,
}
LJRN_DATA = {                          # pour 13|CEPRE re-pointe
    "batiment_groupe_id": LJRN,
    "nb_log_bdnb": 555,
    "annee_construction": 1976,
    "usage_principal_bdnb": "Tertiaire",
    "_usage_bdnb_src": "snapshot",
    "classe_dpe": "C",
    "type_batiment": "immeuble",
    "type_chauffage": "reseau de chaleur",
}

MIRROR_FIELDS = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
                 "_usage_bdnb_src", "annee_construction", "classe_dpe",
                 "type_batiment", "type_chauffage"]

# 5 cles a retirer du _fusion_auto_sources d'ARMONIAL
SOURCES_TO_REMOVE = ["2|RUE|CEPRE", "4|RUE|CEPRE", "6|RUE|CEPRE",
                     "8|RUE|CEPRE", "20|RUE|MIOLLIS"]


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


def apply_mirror(entry, data):
    """Copie MIRROR fields depuis data dans entry."""
    for k in MIRROR_FIELDS:
        if k in data:
            entry[k] = data[k]


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}

    abort = []
    needed = ["2|RUE|CEPRE", "4|RUE|CEPRE", "6|RUE|CEPRE", "8|RUE|CEPRE",
              "13|RUE|CEPRE", "20|RUE|MIOLLIS", ARMONIAL_ANCHOR]
    for cle in needed:
        if by.get(cle) is None:
            abort.append(f"adresse absente : {cle}")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    changes = []

    if not abort:
        # ====== ETAPE A : 2/4 CEPRE + 20 MIOLLIS -> XDM8 ======
        # 2|RUE|CEPRE devient ancre interne XDM8
        a2 = pby["2|RUE|CEPRE"]
        old_bgid_2 = a2.get("batiment_groupe_id")
        old_fc_2 = a2.get("_fusion_cible")
        apply_mirror(a2, XDM8_DATA)
        a2["_bdnb_match"] = "bgid_corrige_XDM8"
        a2["_fusion_auto"] = False
        a2["_fusion_cible"] = None
        a2["_fusion_auto_sources"] = ["4|RUE|CEPRE", "20|RUE|MIOLLIS"]
        a2["_fusion_auto_label"] = "2/4 RUE CEPRE / 20 RUE MIOLLIS"
        a2["syndic"] = None
        a2["_syndic_src"] = None
        changes.append(("A.2|CEPRE", f"bgid {old_bgid_2} -> {XDM8}, "
                        f"fcible {old_fc_2!r} -> None (ancre interne)"))

        # 4|RUE|CEPRE -> bgid XDM8, fused vers 2|RUE|CEPRE
        a4 = pby["4|RUE|CEPRE"]
        old_bgid_4 = a4.get("batiment_groupe_id")
        apply_mirror(a4, XDM8_DATA)
        a4["_bdnb_match"] = "bgid_corrige_XDM8"
        a4["_fusion_auto"] = True
        a4["_fusion_cible"] = "2|RUE|CEPRE"
        a4["_fusion_auto_sources"] = None
        a4["syndic"] = None
        a4["_syndic_src"] = None
        changes.append(("A.4|CEPRE", f"bgid {old_bgid_4} -> {XDM8}, "
                        "fcible ARMONIAL -> 2|RUE|CEPRE"))

        # 20|RUE|MIOLLIS : bgid deja XDM8, re-fuse vers 2|RUE|CEPRE
        a20 = pby["20|RUE|MIOLLIS"]
        old_fc_20 = a20.get("_fusion_cible")
        a20["_fusion_auto"] = True
        a20["_fusion_cible"] = "2|RUE|CEPRE"
        a20["_fusion_auto_sources"] = None
        a20["syndic"] = None
        a20["_syndic_src"] = None
        changes.append(("A.20|MIOLLIS",
                        f"fcible {old_fc_20!r} -> 2|RUE|CEPRE "
                        "(bgid XDM8 deja correct, inchange)"))

        # ====== ETAPE B : 6/8 CEPRE -> Z2Z2 ======
        a6 = pby["6|RUE|CEPRE"]
        old_bgid_6 = a6.get("batiment_groupe_id")
        old_fc_6 = a6.get("_fusion_cible")
        apply_mirror(a6, Z2Z2_DATA)
        a6["_bdnb_match"] = "bgid_corrige_Z2Z2"
        a6["_fusion_auto"] = False
        a6["_fusion_cible"] = None
        a6["_fusion_auto_sources"] = ["8|RUE|CEPRE"]
        a6["_fusion_auto_label"] = "6/8 RUE CEPRE"
        a6["syndic"] = None
        a6["_syndic_src"] = None
        changes.append(("B.6|CEPRE", f"bgid {old_bgid_6} -> {Z2Z2}, "
                        f"fcible {old_fc_6!r} -> None (ancre interne)"))

        a8 = pby["8|RUE|CEPRE"]
        old_bgid_8 = a8.get("batiment_groupe_id")
        apply_mirror(a8, Z2Z2_DATA)
        a8["_bdnb_match"] = "bgid_corrige_Z2Z2"
        a8["_fusion_auto"] = True
        a8["_fusion_cible"] = "6|RUE|CEPRE"
        a8["_fusion_auto_sources"] = None
        a8["syndic"] = None
        a8["_syndic_src"] = None
        changes.append(("B.8|CEPRE", f"bgid {old_bgid_8} -> {Z2Z2}, "
                        "fcible ARMONIAL -> 6|RUE|CEPRE"))

        # ====== ETAPE C : 13|CEPRE bgid VQB9 -> LJRN ======
        a13 = pby["13|RUE|CEPRE"]
        old_bgid_13 = a13.get("batiment_groupe_id")
        apply_mirror(a13, LJRN_DATA)
        a13["_bdnb_match"] = "bgid_corrige_LJRN"
        # fusion vers ARMONIAL inchangee
        changes.append(("C.13|CEPRE",
                        f"bgid {old_bgid_13} -> {LJRN} (correction "
                        "BAN+pivot, reste fused ARMONIAL)"))

        # ====== ETAPE D : retirer 5 sources erronees ARMONIAL ======
        ancre = pby[ARMONIAL_ANCHOR]
        old_srcs = list(ancre.get("_fusion_auto_sources") or [])
        new_srcs = [s for s in old_srcs if s not in SOURCES_TO_REMOVE]
        ancre["_fusion_auto_sources"] = new_srcs
        removed = sorted(set(old_srcs) - set(new_srcs))
        changes.append(("D.ARMONIAL",
                        f"_fusion_auto_sources : {len(old_srcs)} -> "
                        f"{len(new_srcs)} (retire {len(removed)} : "
                        f"{removed})"))

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 80)
    print(f"FIX ARMONIAL PAIR DETACH - {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 80)
    for tag, msg in changes:
        print(f"  [{tag}] {msg}")
    print("-" * 80)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) = {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte.")
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 80)
    print()
    print("ALIAS_RNC a RETIRER dans make_light_motte_picquet.py "
          "(hors-repo, pipeline local) :")
    for s in SOURCES_TO_REMOVE:
        print(f"  RETIRER : {s!r} -> '16|BOULEVARD|GARIBALDI'")
    print("AJOUTER correction bgid : 13|RUE|CEPRE -> LJRN ; 2/4 CEPRE "
          "+ 20 MIOLLIS -> XDM8 ; 6/8 CEPRE -> Z2Z2.")

    if abort:
        print("\nABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("\nDRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not changes:
        print("\nIdempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"\nABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_armonial_pair_detach"] = (
        "CORRECTION HISTORIQUE : pairs 2/4/6/8 RUE CEPRE + 20 RUE "
        "MIOLLIS detaches de ARMONIAL I (AA0646265 ancre 16 BD "
        "GARIBALDI bgid LJRN) - erreur des commits anterieurs "
        "_correctif_armonial_pair + _correctif_armonial_8cepre. "
        "Confirmation terrain user 2026-05-21 : ARMONIAL ne couvre "
        "que les IMPAIRS Cepre. BDNB pivot LJRN l_libelle_adr ne "
        "contient QUE 1/3/5/7/9/11/13/15/17/19 (impairs). BAN+rel_"
        "adresse confirme : 2+4 CEPRE + 20 MIOLLIS -> bgid XDM8-1XCX-"
        "84Y1 (parcelle CY0046, 1965, 20 nb_log, Resid coll, vente "
        "bloc DVF 26/07/2022 17M EUR matche CY/46 = mono-propriete) ; "
        "6+8 CEPRE -> bgid Z2Z2-65KJ-U324 (parcelle CY0047, 1972, 11 "
        "nb_log, Resid coll, vente bloc 15.5M EUR matche CY/47 = mono"
        "-propriete). Aucune copro RNC sur XDM8 ni Z2Z2 (rel_RNC=0 + "
        "RNC live=0). ETAPE A : 2 ancre interne XDM8 label '2/4 RUE "
        "CEPRE / 20 RUE MIOLLIS' ; 4 fused 2 ; 20 MIOLLIS bgid XDM8 "
        "deja correct, re-fuse vers 2|RUE|CEPRE. ETAPE B : 6 ancre "
        "interne Z2Z2 label '6/8 RUE CEPRE' ; 8 fused 6. ETAPE C : "
        "13|RUE|CEPRE bgid corrige VQB9 (= bati 2003 Tertiaire faux) "
        "-> LJRN (BAN+pivot LJRN inclut '13 Rue Cepre'), reste fused "
        "ARMONIAL (pattern correction bgid 2 CHASSELOUP). ETAPE D : "
        "16|BD|GARIBALDI _fusion_auto_sources passe de 20 a 15 "
        "(retire 2/4/6/8 CEPRE + 20 MIOLLIS). Syndic 'non connu' "
        f"heritage ARMONIAL supprime sur les 5 entrees. Parc "
        f"{parc0}->{parc1} ({delta:+d} = +20 XDM8 + 11 Z2Z2 BDNB "
        "hors-RNC residentiel, PIPELINE Sec 6 fallback BDNB). "
        "L'utilisateur peut qualifier 'mono' via menu UI -> "
        "getEffectiveLog(a)=1 -> delta reel +2 (commit ee3185f). "
        "Source-of-truth a porter make_light_motte_picquet.py : "
        "RETIRER 5 ALIAS_RNC pairs+20 MIOLLIS vers 16 GARIBALDI ; "
        "AJOUTER corrections bgid 2/4/20 -> XDM8, 6/8 -> Z2Z2, 13 "
        "-> LJRN.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\nSauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
