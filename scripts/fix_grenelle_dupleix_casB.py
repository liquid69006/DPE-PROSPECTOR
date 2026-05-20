"""
Correctif COSMETIQUE CAS B — Re-point 85 BD GRENELLE vers bgid S543
(Tertiaire) + INJECT 41 RUE DUPLEIX label-only fused vers 85.
Confirmation terrain user 2026-05-20.

Pattern correction bgid (faux matching make_light, comme Sisley/
Chasseloup) + INJECT label-only (Suffren label-only).

Contexte :
  - Bati VOISIN BDNB bgid S543-UM97-SX5D (parcelle 75115000DH0001,
    1900, 0 nb_log_bdnb, TERTIAIRE PUR) couvre 13 facades BAN
    confirmees par BDNB pivot : 85, 87, 89 BD GRENELLE + 41, 43, 45
    RUE DUPLEIX + 2, 4, 6, 8, 10 RUE DE PONDICHERY + 2, 4 RUE DU
    SOUDAN. Syndic FA-G PERENNE par cadastre (visible sur 87 GRENELLE).
  - 0 copro RNC active (BDNB rel_RNC bgid S543 = 0 rows ; RNC live
    tabular-api 3ea8e2c3 par voie '85 grenelle'/'41 dupleix' + ref_
    cad DH/0001 = 0 hit). Megabati tertiaire (commerces/bureaux),
    pas de copropriete habitation.
  - `85|BOULEVARD|GRENELLE` actuellement bgid 5KST-PABL-LAUP (=
    bati VOISIN 83 GRENELLE, parcelle DJ/0019), fused vers 83.
    FAUX matching make_light (num_voie sans validation BAN/parcelle,
    pattern identique a 2 CHASSELOUP corrige plus tot).
  - `41|RUE|DUPLEIX` ABSENT du snapshot (0 DVF, 0 MAJIC), BAN
    existe (75115_3006_00041) sur bgid S543 selon BDNB rel_adresse.

Actions de ce correctif (parc-neutre, cosmetique) :
  1. RETIRER `85|BOULEVARD|GRENELLE` des `_fusion_auto_sources` du
     83 (anomalie corrigee).
  2. RE-POINT `85|BOULEVARD|GRENELLE` :
     - bgid 5KST -> S543 (correction)
     - usage Residentiel collectif -> Tertiaire (MIRROR S543)
     - nb_log_bdnb 31 -> 0 (MIRROR S543)
     - annee 1910 -> 1900 (MIRROR S543)
     - _fusion_auto=False (sort de fusion, devient ancre interne)
     - _fusion_cible=None
     - _fusion_auto_sources=['41|RUE|DUPLEIX'] (apres step 3)
     - _fusion_auto_label='85 BD GRENELLE / 41 RUE DUPLEIX'
  3. INJECT `41|RUE|DUPLEIX` entry minimaliste fused vers 85 (BAN
     cle 75115_3006_00041, bgid S543).

Note : 87|BOULEVARD|GRENELLE deja sur bgid S543 (Tertiaire, syndic
FA-G PERENNE cadastre) reste INCHANGE comme entry independante
parallele a 85 (pas de fusion entre 85 et 87 - laissees comme
entries co-existantes sur le meme bgid Tertiaire).

Effet parc (modele renderSecteur Sec 6) :
  - bgid 5KST (83 GRENELLE) : reste a 31 nb_log_bdnb (83 ancre
    Residentiel coll inchange). Le 85 n'apportait rien (fused).
    Inchange.
  - bgid S543 : Tertiaire pur, 0 nb_log_bdnb -> ne contribue jamais
    au bgBdnb (filtre RESID). 85, 87 et 41 DUPLEIX tous Tertiaire,
    exclus de bgBdnb. Inchange (toujours 0).
  - Delta parc = 0 (STRICTEMENT NEUTRE).

Aucune vente DVF aux 85 GRENELLE ni 41 DUPLEIX. Filet de securite
si mutations futures.

Source-of-truth a porter dans make_light_motte_picquet.py :
  - ALIAS_RNC : RETIRER '85|BOULEVARD|GRENELLE' du mapping vers 83
    (anomalie make_light corrigee : 85 sur bgid S543, pas 5KST).
  - ALIAS_RNC += { '41|RUE|DUPLEIX': '85|BOULEVARD|GRENELLE' }.
  - Correction bgid : 85 GRENELLE doit etre sur S543 pas 5KST
    (validation BAN/parcelle obligatoire avant matching num_voie,
    pattern identique a 2 CHASSELOUP).

Cible : data/secteur_motte_picquet_light.json. Backup
.pregrendupB.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_grenelle_dupleix_casB.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_grenelle_dupleix_casB.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.pregrendupB.bak"

OLD_ANCHOR_83 = "83|BOULEVARD|GRENELLE"
NEW_ANCHOR = "85|BOULEVARD|GRENELLE"   # devient ancre interne sur S543
INJECT_CLE = "41|RUE|DUPLEIX"
INJECT_ADR = "41 RUE DUPLEIX"
NEW_BGID = "bdnb-bg-S543-UM97-SX5D"     # bati Tertiaire DH/0001
LABEL = "85 BD GRENELLE / 41 RUE DUPLEIX"

# Donnees BDNB S543 figees pour reproductibilite (clone champs depuis
# 87 GRENELLE qui est deja sur S543 dans le light)
BDNB_S543 = {
    "batiment_groupe_id": NEW_BGID,
    "nb_log_bdnb": None,
    "annee_construction": 1900,
    "classe_dpe": None,
    "type_batiment": None,
    "type_chauffage": None,
    "usage_principal_bdnb": "Tertiaire",
    "_usage_bdnb_src": "snapshot",
}

MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


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


def build_inject_41(anchor_85_entry):
    """Entry adresses[] 41 RUE DUPLEIX minimaliste fused vers 85."""
    return {
        "cle": INJECT_CLE,
        "adresse": INJECT_ADR,
        "longitude": anchor_85_entry.get("longitude"),
        "latitude": anchor_85_entry.get("latitude"),
        "code_iris": anchor_85_entry.get("code_iris"),
        "_coord_source": "inject_label_only_grendupB",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": anchor_85_entry.get("syndic"),
        "_syndic_src": anchor_85_entry.get("_syndic_src"),
        "numero_immatriculation": None,
        "nb_lots_habitation": None,
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation": 0.0,
        "classement_rotation": "Fige",
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Figé",
        "nb_log_bdnb": BDNB_S543["nb_log_bdnb"],
        "annee_construction": BDNB_S543["annee_construction"],
        "classe_dpe": BDNB_S543["classe_dpe"],
        "type_batiment": BDNB_S543["type_batiment"],
        "type_chauffage": BDNB_S543["type_chauffage"],
        "batiment_groupe_id": BDNB_S543["batiment_groupe_id"],
        "_bdnb_match": "ban_inject_label_only",
        "_taux_logement_src": "copie_sans_dependance",
        "usage_principal_bdnb": BDNB_S543["usage_principal_bdnb"],
        "_usage_bdnb_src": BDNB_S543["_usage_bdnb_src"],
        "_fusion_auto": True,
        "_fusion_cible": NEW_ANCHOR,
        "_fusion_auto_sources": None,
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}

    abort = []
    a85 = by.get(NEW_ANCHOR)
    a83 = by.get(OLD_ANCHOR_83)
    if a85 is None:
        abort.append(f"85 absent : {NEW_ANCHOR}")
    elif not (a85.get("_fusion_auto") and a85.get("_fusion_cible") == OLD_ANCHOR_83):
        abort.append(f"85 n'est pas fused vers {OLD_ANCHOR_83} "
                     f"(actuel: cible={a85.get('_fusion_cible')!r}, "
                     f"auto={a85.get('_fusion_auto')})")
    if a83 is None:
        abort.append(f"83 absent : {OLD_ANCHOR_83}")
    if by.get(INJECT_CLE) is not None:
        abort.append(f"entry {INJECT_CLE} deja presente")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    p83 = pby.get(OLD_ANCHOR_83)
    p85 = pby.get(NEW_ANCHOR)

    re_pointed = False
    injected = False
    if not abort and p85 is not None and p83 is not None:
        # 1) Retirer 85 du sources de 83
        old83_sources = list(p83.get("_fusion_auto_sources") or [])
        new83_sources = [s for s in old83_sources if s != NEW_ANCHOR]
        p83["_fusion_auto_sources"] = new83_sources or None

        # 2) Re-point 85 vers S543 (MIRROR Tertiaire)
        old85_bgid = p85.get("batiment_groupe_id")
        for k in MIRROR:
            if k in BDNB_S543:
                p85[k] = BDNB_S543[k]
        p85["_bdnb_match"] = "bgid_corrige_S543"
        p85["_fusion_auto"] = False
        p85["_fusion_cible"] = None
        re_pointed = True

        # 3) INJECT 41 DUPLEIX fused vers 85
        new_entry = build_inject_41(p85)
        patched["adresses"].append(new_entry)
        pby[INJECT_CLE] = new_entry
        injected = True

        # 4) Update sources/label de 85
        p85["_fusion_auto_sources"] = [INJECT_CLE]
        p85["_fusion_auto_label"] = LABEL

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX GRENELLE/DUPLEIX CAS B (re-point 85 + INJECT 41) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  85 ancien bgid (faux) : {a85 and a85.get('batiment_groupe_id')}")
    print(f"  85 nouveau bgid       : {NEW_BGID} (Tertiaire DH/0001)")
    print(f"  Re-point done         : {re_pointed}")
    print(f"  INJECT {INJECT_CLE}    : {injected}")
    if a83:
        print(f"  83 _fusion_auto_sources : {a83.get('_fusion_auto_sources')} -> "
              f"{p83.get('_fusion_auto_sources') if p83 else 'n/a'}")
    if p85:
        print(f"  85 _fusion_auto_label   : {a85 and a85.get('_fusion_auto_label')!r} -> "
              f"{p85.get('_fusion_auto_label')!r}")
        print(f"  85 _fusion_auto_sources : {a85 and a85.get('_fusion_auto_sources')} -> "
              f"{p85.get('_fusion_auto_sources')}")
        print(f"  85 _fusion_auto/_cible  : "
              f"{a85 and a85.get('_fusion_auto')}/{a85 and a85.get('_fusion_cible')!r} -> "
              f"{p85.get('_fusion_auto')}/{p85.get('_fusion_cible')!r}")
    print("-" * 78)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc STRICTEMENT NEUTRE).")
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
    if not (re_pointed and injected):
        print("ABORT : aucune modification appliquee.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_grenelle_dupleix_casB"] = (
        "CAS B : re-point 85 BD GRENELLE de bgid 5KST (faux, = bati "
        "voisin 83 GRENELLE parcelle DJ/0019 Residentiel) vers bgid "
        f"{NEW_BGID} (= vrai bati VOISIN S543 parcelle 75115000DH0001 "
        "TERTIAIRE pur, 1900, 0 nb_log_bdnb, syndic FA-G PERENNE par "
        "cadastre) + adoption MIRROR (usage Tertiaire, annee 1900) + "
        "INJECT 41 RUE DUPLEIX label-only fused vers 85 (BAN 75115_"
        "3006_00041 confirme sur bgid S543 via BDNB rel_adresse). 85 "
        "sort de la fusion vers 83 (anomalie make_light corrigee : "
        "matching num_voie sans validation BAN/parcelle, pattern "
        "identique a 2 CHASSELOUP). 87 BD GRENELLE deja sur S543 "
        "reste INCHANGE comme entry independante parallele. 0 copro "
        "RNC active sur S543 (BDNB rel_RNC=0, RNC live=0). Bati "
        "Tertiaire (commerces/bureaux). Parc "
        f"{parc0}->{parc1} STRICTEMENT NEUTRE (85, 87, 41 DUPLEIX "
        f"tous Tertiaire -> exclus de bgBdnb). Label '{LABEL}' sur "
        "ancre 85. ALIAS_RNC a porter dans make_light_motte_picquet"
        ".py : RETIRER 85->83 (anomalie corrigee) + AJOUTER "
        "{'41|RUE|DUPLEIX': '85|BOULEVARD|GRENELLE'}.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (re-point 85 + INJECT 41)")


if __name__ == "__main__":
    main()
