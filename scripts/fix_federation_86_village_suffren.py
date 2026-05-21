"""
Correctif HYBRIDE — Inversion ancre 86 RUE FEDERATION + 88 + INJECT
label-only 84+90 FEDERATION (4 facades BAN du bati VILLAGE SUFFREN D).
Confirmation terrain user 2026-05-21.

Pattern HYBRIDE 'inversion ancre RNC' + INJECT_LABEL_ONLY :
  - Make_light a choisi 88|RUE|FEDERATION comme ancre par defaut
    (probablement par GPS/DVF : 10 mutations Dependance/commerce au
    88) alors que la copro RNC AB6092555 'LE VILLAGE SUFFREN D' est
    declaree sur cle_adresse '86|RUE|FEDERATION' dans coproprietes[].
  - Anomalie parc : 86 fused -> AB6092555 invisible dans bgRncLots,
    bgid 69B5 entre dans bgBdnb = 181 (BDNB) au lieu de 110 (RNC).
    Surevaluation +71 logements actuelle.
  - 4 facades BAN du bati 69B5 (84/86/88/90) -> 84 et 90 absentes
    light, INJECT label-only pour visibilite multi-voies.

Triple confirmation source-of-truth :
  - RNC live AB6092555 'LE VILLAGE SUFFREN D - MS11202' : 110 lots
    hab / 208 tot, syndic GERARD SAFAR SAS, ancre 86 Rue de la
    Federation (75115_3541_00086 BAN).
  - BDNB pivot bgid 69B5-LL5X-E2NB (parcelle 75115000DI0003, 1967) :
    l_libelle_adr = ['88', '84', '90', '86' RUE FEDERATION] (4
    facades), libelle_adr_principale_ban = '86' (officiel), nb_log
    =181 (estimation BDNB incluant dependances), nb_log_rnc=110
    (= MATCHE EXACT AB6092555).
  - BDNB rel_RNC bgid 69B5 : 1 ligne AB6092555 (tres fiable).
  - DVF 88 FEDERATION : 13 mutations 2021-2025 toutes type Dependance
    /Local commercial (caves, parkings, 1 cession commerciale 8.55M
    EUR 2024) - 0 vlog cohrent avec 86 ancre apres fix (consolidees
    sous AB6092555 GERARD SAFAR).

VILLAGE SUFFREN ensemble (info) :
  - AB6092555 'LE VILLAGE SUFFREN D' = bati 69B5 parcelle DI/0003
    (cible de ce fix).
  - AB7861529 'village suffren EFGH' = 7 PRESLES + DI/0010 + DI/0016
    + DI/0003 partage (copro distincte 116 lots, deja ancree dans
    light - non touchee ici).

Plan correctif (3 etapes) :

A) Inversion ancre 86 <-> 88 :
   - 86|RUE|FEDERATION : _fusion_auto=False, _fusion_cible=None,
     devient ANCRE interne. sources=['84','88','90'|RUE|FEDERATION]
     label '84/86/88/90 RUE FEDERATION' (4 facades VILLAGE SUFFREN D).
   - 88|RUE|FEDERATION : _fusion_auto=True, _fusion_cible='86|RUE|
     FEDERATION'. sources=None, label=None. _syndic_src cadastre ->
     rnc_grp (cohrence).

B) INJECT 84 + 90 RUE FEDERATION label-only :
   - Entries minimalistes clones bgid 69B5 + MIRROR ancre 86.
   - _fusion_auto=True, _fusion_cible='86|RUE|FEDERATION'.
   - Aucune DVF historique sur ces 2 facades -> 0 vlog/vtot.

C) Le label '86/88 RUE FEDERATION' sur 88 est vide ; le label
   '84/86/88/90 RUE FEDERATION' est pose sur 86 (nouvelle ancre).

Effet parc (modele renderSecteur Sec 6) :
  - bgid 69B5 :
    Avant : bgBdnb=181 (via 88 ancre sans cp, Resid coll, nb_log
            BDNB)
    Apres : bgRncLots={AB6092555: 110} (via 86 ancre + AB6092555,
            RNC autoritaire prioritaire PIPELINE Sec 6)
  - Delta parc = -71 logements (correction de l'anomalie, alignement
    sur nb_log_rnc BDNB = 110).
  - 84 et 90 injectes fused -> exclus de bgBdnb (idem comportement
    avant : ils n'apportaient rien car bgid 69B5 deja occupe).

Ventes consolidees au rendu :
  - 88 FEDERATION (10 vtot Dependance/commerce) -> fused vers 86,
    consolidees sur 86 AB6092555 (taux 0 vlog/110 = Fige conforme :
    aucune vente habitation).
  - 86 reste 0 vlog/vtot directes.

Source-of-truth a porter dans make_light_motte_picquet.py (hors-repo) :
  - Force l'ancre adresse a etre celle de la cle_adresse de la copro
    RNC (AB6092555 -> 86|RUE|FEDERATION).
  - ALIAS_RNC += { '88|RUE|FEDERATION': '86|RUE|FEDERATION',
                    '84|RUE|FEDERATION': '86|RUE|FEDERATION',
                    '90|RUE|FEDERATION': '86|RUE|FEDERATION' }

Cible : data/secteur_motte_picquet_light.json. Backup
.prefederation86.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_federation_86_village_suffren.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_federation_86_village_suffren.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prefederation86.bak"

ANCHOR = "86|RUE|FEDERATION"               # ancre RNC AB6092555 (nouveau ancrage light)
OLD_ANCHOR = "88|RUE|FEDERATION"           # ancien ancrage light (incorrect, devient fused)
IMMAT = "AB6092555"
BGID = "bdnb-bg-69B5-LL5X-E2NB"
INJECTS = [("84|RUE|FEDERATION", "84 RUE DE LA FEDERATION"),
           ("90|RUE|FEDERATION", "90 RUE DE LA FEDERATION")]
NEW_LABEL = "84/86/88/90 RUE FEDERATION"

# Champs MIRROR a cloner depuis l'ancre 86 vers les nouvelles entries
MIRROR_FIELDS = ["batiment_groupe_id", "nb_log_bdnb",
                 "usage_principal_bdnb", "_usage_bdnb_src",
                 "annee_construction", "classe_dpe", "type_batiment",
                 "type_chauffage"]


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


def build_inject(new_cle, new_adr, src):
    """Entry minimaliste clone bgid 69B5 (depuis ancre 86)."""
    return {
        "cle": new_cle,
        "adresse": new_adr,
        "longitude": src.get("longitude"),
        "latitude": src.get("latitude"),
        "code_iris": src.get("code_iris"),
        "_coord_source": "inject_label_only_fed86",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": src.get("syndic"),
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
        "nb_log_bdnb": src.get("nb_log_bdnb"),
        "annee_construction": src.get("annee_construction"),
        "classe_dpe": src.get("classe_dpe"),
        "type_batiment": src.get("type_batiment"),
        "type_chauffage": src.get("type_chauffage"),
        "batiment_groupe_id": src.get("batiment_groupe_id"),
        "_bdnb_match": "ban_inject_label_only",
        "_taux_logement_src": "filtre_habitation",
        "usage_principal_bdnb": src.get("usage_principal_bdnb"),
        "_usage_bdnb_src": src.get("_usage_bdnb_src"),
        "_fusion_auto": True,
        "_fusion_cible": ANCHOR,
        "_fusion_auto_sources": None,
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    abort = []
    a86 = by.get(ANCHOR)
    a88 = by.get(OLD_ANCHOR)
    cp86 = cbc.get(ANCHOR)
    if a86 is None:
        abort.append(f"86 absent : {ANCHOR}")
    if a88 is None:
        abort.append(f"88 absent : {OLD_ANCHOR}")
    if cp86 is None or cp86.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANCHOR}")
    # Garde idempotence : si 86 est deja ancre (pas fused), pas besoin
    if a86 and not (a86.get("_fusion_auto")
                    and a86.get("_fusion_cible") == OLD_ANCHOR):
        abort.append(f"86 deja ancre (pas fused vers 88), inversion "
                     "non necessaire ou deja faite")
    for cle, _ in INJECTS:
        if by.get(cle) is not None:
            abort.append(f"INJECT {cle} : deja present (idempotence)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    p86 = pby.get(ANCHOR)
    p88 = pby.get(OLD_ANCHOR)

    inv_done = False
    inject_count = 0
    if not abort and p86 and p88:
        # ===== A) Inversion ancre 86 <-> 88 =====
        # 86 devient ancre interne
        p86["_fusion_auto"] = False
        p86["_fusion_cible"] = None
        # 88 devient fused vers 86
        p88["_fusion_auto"] = True
        p88["_fusion_cible"] = ANCHOR
        p88["_fusion_auto_sources"] = None
        p88["_fusion_auto_label"] = None
        if p88.get("_syndic_src") == "cadastre":
            p88["_syndic_src"] = "rnc_grp"
        # ===== B) INJECT 84 + 90 (clones MIRROR 86) =====
        for cle, adr in INJECTS:
            new_entry = build_inject(cle, adr, p86)
            patched["adresses"].append(new_entry)
            pby[cle] = new_entry
            inject_count += 1
        # ===== C) Ancre 86 : sources etendues + nouveau label =====
        new_sources = sorted({OLD_ANCHOR}
                             | {c for c, _ in INJECTS})
        p86["_fusion_auto_sources"] = new_sources
        p86["_fusion_auto_label"] = NEW_LABEL
        inv_done = True

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 100)
    print(f"FIX 86/88 FEDERATION VILLAGE SUFFREN - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 100)
    print(f"  ANCRE NEW   : {ANCHOR}  copro {IMMAT} "
          f"'{cp86 and cp86.get('nom_copropriete')}' "
          f"({cp86 and cp86.get('nb_lots_habitation')} lots hab)")
    print(f"  Syndic      : {(cp86 and cp86.get('syndic')) or '-'}")
    print(f"  Bgid        : {BGID}")
    print(f"  Inversion   : {OLD_ANCHOR} -> {ANCHOR} done={inv_done}")
    print(f"  INJECT      : {inject_count} entries "
          f"({[c for c,_ in INJECTS]})")
    print(f"  Label       : {p86 and p86.get('_fusion_auto_label')}")
    print(f"  Sources     : {p86 and p86.get('_fusion_auto_sources')}")
    print("-" * 100)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes (delta) :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) = {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc neutre).")
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
    print(f"  Note : -71 attendu = correction surevaluation BDNB(181)->"
          "RNC(110) via switch ancre 88 (sans cp) -> 86 (AB6092555)")
    print("=" * 100)

    if abort:
        print("\nABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("\nDRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not inv_done:
        print("\nIdempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"\nABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_federation_86_village_suffren"] = (
        f"INVERSION ANCRE + INJECT label-only 84/90 FEDERATION. "
        f"AB6092555 'LE VILLAGE SUFFREN D - MS11202' (GERARD SAFAR SAS, "
        f"110 lots hab / 208 tot) etait declaree dans coproprietes[] "
        f"sur cle_adresse {ANCHOR} mais l'ancre light etait {OLD_ANCHOR} "
        "(make_light a privilegie le 88 par GPS/DVF : 10 mutations "
        "Dependance/commerce). Anomalie : 86 fused -> AB6092555 "
        "invisible dans bgRncLots, bgid 69B5 entre dans bgBdnb=181 "
        f"(estim BDNB) au lieu de RNC=110 -> surevaluation +71. Fix : "
        f"86 devient ancre interne ({ANCHOR} sort de fusion), 88 fused "
        f"vers 86 (_syndic_src cadastre->rnc_grp), INJECT 84+90 "
        "FEDERATION label-only (4 facades BAN bati 69B5 parcelle "
        f"DI/0003 confirmees pivot BDNB), label '{NEW_LABEL}' sur 86. "
        f"Parc {parc0}->{parc1} ({delta:+d} = correction surevaluation, "
        "alignement nb_log_rnc BDNB = 110 = AB6092555). Triple "
        "confirmation : RNC live AB6092555 ancre 86 + BDNB pivot 69B5 "
        "l_libelle_adr 4 facades + libelle_principal_ban='86' (BAN "
        "officiel). VILLAGE SUFFREN ensemble = AB6092555 D (ce fix) + "
        "AB7861529 EFGH (7 PRESLES, copro distincte deja ancree non "
        "touchee). DVF 88 FEDERATION (10 vtot Dependance/commerce dont "
        "cession 8.55M EUR 2024) consolidees sous AB6092555 via fusion. "
        "Source-of-truth a porter make_light : force ancre = cle copro "
        "RNC + ALIAS_RNC '88/84/90 RUE FEDERATION' -> '86 RUE FEDERATION'.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\nSauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (inversion + {inject_count} INJECT)")


if __name__ == "__main__":
    main()
