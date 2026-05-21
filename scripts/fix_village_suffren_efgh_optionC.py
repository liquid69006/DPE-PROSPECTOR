"""
Correctif COMPLET Option C — VILLAGE SUFFREN EFGH (AB7861529).
Confirmation terrain user 2026-05-21.

Pattern HYBRIDE multi-volets (Cambronne multi-bgid multi-parcelles
+ correction fusion + INJECT_LABEL_ONLY) :

A) 2/8/14 PASSAGE GUESCLIN re-fuse vers 7 RUE PRESLES (preuve
   cadastrale forte : 3 bgids QX4P/PS7Y/TW35 tous sur parcelle
   75115000DI0016 = ref_cadastrale_1 d'AB7861529 RNC live ;
   syndic GERARD SAFAR cadastre = match exact AB7861529).
   Pattern Fondary/Croix-Nivert : copro RNC multi-parcelles avec
   BDNB qui ne mappe qu'une parcelle (DI/0010 -> bgid QNW4) ;
   les autres parcelles (DI/0003 partage avec D, DI/0016 = ce cas)
   restent orphelines BDNB.

B) 11 RUE PRESLES correction fusion : actuellement bgid 4EHZ (=
   bgid 13 PRESLES AB3028107 'PRESLES RUE DE 13 LMC' Tertiaire 22
   lots, syndic JEAN CHARPENTIER), fused vers 13. Mais BDNB pivot
   QNW4 (AB7861529) inclut '11 Rue De Presles' dans son l_libelle_
   adr -> 11 PRESLES devrait etre sur QNW4. AMBIGUITE : 13 PRESLES
   AB3028107 est une vraie copro distincte avec 5 vlog actives,
   donc une erreur d'attribution pourrait casser cette copro.
   Cette correction RE-FUSE 11 vers 7 PRESLES (AB7861529) +
   correction bgid 4EHZ -> QNW4 + retire 11 de chain 13.
   FLAG : verifier terrain si besoin avant apply.

C) INJECT label-only 5/9 PRESLES + 16/18/20 PASSAGE GUESCLIN (5
   facades BAN absentes du light) fused vers 7 PRESLES, MIRROR
   bgid QNW4. Pattern 8 CEPRE / 41 DUPLEIX visibilite multi-voies.

D) Ancre 7 PRESLES : _fusion_auto_sources etendu (8 nouvelles
   sources : 5/9/11 PRESLES + 2/8/14/16/18/20 GUESCLIN), nouveau
   label '5/7/9/11 RUE PRESLES / 2/8/14/16/18/20 PASSAGE GUESCLIN'.

Triple confirmation :
  - RNC live AB7861529 'village suffren EFGH - MS192006' : 116
    lots hab, syndic GERARD SAFAR, adresse_ref '7 r de presles',
    nombre_parcelles=3 : ref_cad_1=75056115DI0016 (= parcelle
    2/8/14 GUESCLIN !), ref_cad_2=75056115DI0010 (= QNW4 ancre),
    ref_cad_3=75056115DI0003 (= partage avec D AB6092555).
  - BDNB pivot bgid QNW4 l_libelle_adr = ['11 Presles', '7 Presles',
    '16 Guesclin', '5 Presles', '20 Guesclin', '9 Presles', '18
    Guesclin'] (7 facades). Confirme rattachement Presles+Guesclin.
  - BDNB rel_RNC bgid QNW4 = AB7861529 (tres fiable).
  - BDNB rel_RNC bgids QX4P/PS7Y/TW35 (2/8/14 GUESCLIN) = vides,
    parcelle DI/0016 commune = ref_cad_1 RNC AB7861529.

Effet parc (modele renderSecteur Sec 6) :
  - bgid TW35 (14 GUESCLIN, ancre interne, Resid coll, nb_log_bdnb
    =42) : entre dans bgBdnb=42 actuellement -> APRES fix : 14
    fused, sort de bgBdnb. Delta -42 logements.
  - bgid QX4P/PS7Y (2/8 GUESCLIN deja fused) : inchanges.
  - bgid 4EHZ (11+13 PRESLES, Tertiaire, AB3028107 22 lots) : 11
    sort de chain 13 -> bgRncLots[4EHZ]={AB3028107:22} inchange.
  - bgid QNW4 (7 PRESLES + AB7861529) : reste 115 lots RNC
    autoritaire prioritaire, les 6 INJECT + 4 re-fuse sont fused
    -> exclus de bgBdnb (de toute facon bgid QNW4 deja en bgRncLots).
  -> Delta parc total = -42 (correction phantom TW35).

Ventes consolidees au rendu :
  - 14 GUESCLIN (0 vlog/vtot directes, mais peut absorber via chain)
    -> rebascule sous AB7861529 GERARD SAFAR.
  - 2/8 GUESCLIN (0 vlog/vtot) -> idem.
  - 11 PRESLES (0 vlog/vtot) -> idem (sort de chain 13 AB3028107
    SOPAGI sans impact sur les ventes de 13 propre = 4 vlog
    restent sur 13).

Source-of-truth a porter make_light_motte_picquet.py :
  - ALIAS_RNC += { '2|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '8|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '14|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '16|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '18|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '20|PASSAGE|GUESCLIN': '7|RUE|PRESLES',
                    '5|RUE|PRESLES': '7|RUE|PRESLES',
                    '9|RUE|PRESLES': '7|RUE|PRESLES',
                    '11|RUE|PRESLES': '7|RUE|PRESLES' (override 13) }
  - Correction bgid 2/8/14 GUESCLIN -> uniformisation QNW4 (ou
    garder bgids distincts ; pas critique car fused).
  - Correction bgid 11 PRESLES : 4EHZ -> QNW4 (validation BAN/
    parcelle obligatoire).

Cible : data/secteur_motte_picquet_light.json. Backup
.prevsuffrenefgh.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_village_suffren_efgh_optionC.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_village_suffren_efgh_optionC.py --apply
"""

import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prevsuffrenefgh.bak"

ANCHOR = "7|RUE|PRESLES"
IMMAT = "AB7861529"
BGID_QNW4 = "bdnb-bg-QNW4-6U22-1GTJ"

# A) Re-fuse cibles (deja dans light)
REFUSE_GUESCLIN = ["2|PASSAGE|GUESCLIN", "8|PASSAGE|GUESCLIN",
                   "14|PASSAGE|GUESCLIN"]

# B) Correction fusion 11 PRESLES (cible actuelle 13 -> 7)
OLD_FC_11 = "13|RUE|PRESLES"

# C) INJECT label-only (absents light)
INJECTS = [
    ("5|RUE|PRESLES",       "5 RUE DE PRESLES"),
    ("9|RUE|PRESLES",       "9 RUE DE PRESLES"),
    ("16|PASSAGE|GUESCLIN", "16 PASSAGE DU GUESCLIN"),
    ("18|PASSAGE|GUESCLIN", "18 PASSAGE DU GUESCLIN"),
    ("20|PASSAGE|GUESCLIN", "20 PASSAGE DU GUESCLIN"),
]

NEW_LABEL = ("5/7/9/11 RUE PRESLES / "
             "2/8/14/16/18/20 PASSAGE GUESCLIN")


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


def build_inject(new_cle, new_adr, anchor):
    """Entry minimaliste clone bgid QNW4 fused vers 7 PRESLES."""
    return {
        "cle": new_cle,
        "adresse": new_adr,
        "longitude": anchor.get("longitude"),
        "latitude": anchor.get("latitude"),
        "code_iris": anchor.get("code_iris"),
        "_coord_source": "inject_label_only_vsuffren_efgh",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": anchor.get("syndic"),
        "_syndic_src": "rnc_grp",
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
        "nb_log_bdnb": anchor.get("nb_log_bdnb"),
        "annee_construction": anchor.get("annee_construction"),
        "classe_dpe": anchor.get("classe_dpe"),
        "type_batiment": anchor.get("type_batiment"),
        "type_chauffage": anchor.get("type_chauffage"),
        "batiment_groupe_id": BGID_QNW4,
        "_bdnb_match": "ban_inject_label_only",
        "_taux_logement_src": "filtre_habitation",
        "usage_principal_bdnb": anchor.get("usage_principal_bdnb"),
        "_usage_bdnb_src": anchor.get("_usage_bdnb_src"),
        "_fusion_auto": True,
        "_fusion_cible": ANCHOR,
        "_fusion_auto_sources": None,
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}

    abort = []
    a_anc = by.get(ANCHOR)
    if a_anc is None:
        abort.append(f"ancre absente : {ANCHOR}")
    elif a_anc.get("numero_immatriculation") != IMMAT:
        abort.append(f"ancre {ANCHOR} sans immat {IMMAT}")
    for cle in REFUSE_GUESCLIN + [OLD_FC_11, "11|RUE|PRESLES"]:
        if by.get(cle) is None:
            abort.append(f"adresse cible absente : {cle}")
    for cle, _ in INJECTS:
        if by.get(cle) is not None:
            abort.append(f"INJECT {cle} : deja present (idempotence)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    p_anc = pby.get(ANCHOR)

    changes = []
    if not abort and p_anc:
        # === A) Re-fuse 2/8/14 GUESCLIN -> 7 PRESLES ===
        for cle in REFUSE_GUESCLIN:
            a = pby[cle]
            old_fc = a.get("_fusion_cible")
            old_fa = a.get("_fusion_auto")
            a["_fusion_auto"] = True
            a["_fusion_cible"] = ANCHOR
            a["_fusion_auto_sources"] = None
            a["_fusion_auto_label"] = None
            if a.get("_syndic_src") == "cadastre":
                a["_syndic_src"] = "rnc_grp"
            changes.append(("A", cle,
                            f"fcible {old_fc!r} -> {ANCHOR}, "
                            f"_syndic_src cadastre->rnc_grp"))

        # === B) 11 PRESLES correction fusion 13->7 + bgid 4EHZ->QNW4 ===
        a11 = pby.get("11|RUE|PRESLES")
        if a11:
            old_fc = a11.get("_fusion_cible")
            old_bg = a11.get("batiment_groupe_id")
            a11["_fusion_auto"] = True
            a11["_fusion_cible"] = ANCHOR
            a11["_fusion_auto_sources"] = None
            a11["batiment_groupe_id"] = BGID_QNW4
            a11["_bdnb_match"] = "bgid_corrige_QNW4"
            a11["usage_principal_bdnb"] = p_anc.get("usage_principal_bdnb")
            a11["nb_log_bdnb"] = p_anc.get("nb_log_bdnb")
            a11["annee_construction"] = p_anc.get("annee_construction")
            # syndic : remplacer JEAN CHARPENTIER par GERARD SAFAR
            a11["syndic"] = p_anc.get("syndic")
            a11["_syndic_src"] = "rnc_grp"
            changes.append(("B", "11|RUE|PRESLES",
                            f"fcible {old_fc!r}->{ANCHOR}, bgid "
                            f"{old_bg[-15:]}->{BGID_QNW4[-15:]}, "
                            "syndic JEAN CHARPENTIER->GERARD SAFAR"))
            # Retirer 11 de la chain 13 PRESLES
            a13 = pby.get(OLD_FC_11)
            if a13:
                src13 = list(a13.get("_fusion_auto_sources") or [])
                if "11|RUE|PRESLES" in src13:
                    src13.remove("11|RUE|PRESLES")
                    a13["_fusion_auto_sources"] = src13 or None
                    # Update label 13 si plus de sources
                    if not src13:
                        a13["_fusion_auto_label"] = None
                    changes.append(("B'", OLD_FC_11,
                                    "_fusion_auto_sources retire 11"))

        # === C) INJECT 5/9 PRESLES + 16/18/20 GUESCLIN ===
        for cle, adr in INJECTS:
            new = build_inject(cle, adr, p_anc)
            patched["adresses"].append(new)
            pby[cle] = new
            changes.append(("C", cle, f"INJECT label-only (bgid QNW4)"))

        # === D) Ancre 7 PRESLES : sources + label ===
        new_sources = REFUSE_GUESCLIN + ["11|RUE|PRESLES"] \
            + [c for c, _ in INJECTS]
        cur = list(p_anc.get("_fusion_auto_sources") or [])
        all_sources = sorted(set(cur + new_sources))
        p_anc["_fusion_auto_sources"] = all_sources
        p_anc["_fusion_auto_label"] = NEW_LABEL
        changes.append(("D", ANCHOR,
                        f"_fusion_auto_sources {len(cur)}->"
                        f"{len(all_sources)} + label '{NEW_LABEL}'"))

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 110)
    print(f"FIX VILLAGE SUFFREN EFGH (AB7861529) Option C - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 110)
    print(f"  ANCRE : {ANCHOR} (copro {IMMAT}, 115 lots hab, GERARD SAFAR SAS)")
    print(f"  Bgid  : {BGID_QNW4}")
    print(f"  Changes : {len(changes)}")
    print("-" * 110)
    for tag, cle, msg in changes:
        print(f"  [{tag}] {cle:32s} {msg}")
    print("-" * 110)
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
    print(f"  Attendu : -42 (TW35 phantom BDNB sortie via re-fuse 14)")
    print("=" * 110)

    if abort:
        print("\nABORT (gardes) :")
        for x in abort:
            print("  - " + x)
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
    meta["_correctif_village_suffren_efgh_optionC"] = (
        "VILLAGE SUFFREN EFGH (AB7861529 GERARD SAFAR 115 lots hab, "
        "ancre 7 PRESLES, bgid QNW4) - completion Option C terrain "
        "user 2026-05-21. A) Re-fuse 2/8/14 PASSAGE GUESCLIN vers 7 "
        "PRESLES (3 bgids QX4P/PS7Y/TW35 tous sur parcelle BDNB "
        "75115000DI0016 = ref_cad_1 RNC AB7861529 ; syndic GERARD "
        "SAFAR cadastre match ; pattern Fondary/Croix-Nivert copro "
        "multi-parcelles avec BDNB mappant 1 seule parcelle). B) 11 "
        "PRESLES correction fusion 13 (AB3028107 SOPAGI Tertiaire) "
        "-> 7 PRESLES (AB7861529) + correction bgid 4EHZ -> QNW4 "
        "(selon BDNB pivot QNW4 l_libelle_adr inclut '11 Rue De "
        "Presles') ; retire 11 de chain 13. C) INJECT label-only 5/"
        "9 PRESLES + 16/18/20 PASSAGE GUESCLIN (5 facades BAN "
        "absentes) MIRROR bgid QNW4. D) Ancre 7 PRESLES _fusion_"
        "auto_sources 0->9 + label '5/7/9/11 RUE PRESLES / 2/8/14/"
        "16/18/20 PASSAGE GUESCLIN'. Triple confirmation : RNC live "
        "AB7861529 nombre_parcelles=3 (DI/0016+DI/0010+DI/0003) + "
        "BDNB pivot QNW4 l_libelle_adr=7 facades + BDNB rel_RNC "
        f"QNW4 = AB7861529 tres fiable. Parc {parc0}->{parc1} "
        f"({delta:+d} = correction phantom TW35 -42 logements, BDNB "
        "incluait deja faussement 14 GUESCLIN apparte BDNB hors-RNC "
        "alors que AB7861529 RNC autoritaire couvre l'ensemble via "
        "ref_cad multi-parcelles). 13 PRESLES AB3028107 (22 lots) "
        "garde son ancre propre + ses ventes (5 vlog), juste perd "
        "sa source '11|RUE|PRESLES' erronee. Source-of-truth ALIAS_"
        "RNC + correction bgid 11 PRESLES (4EHZ->QNW4) a porter "
        "make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\nSauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
