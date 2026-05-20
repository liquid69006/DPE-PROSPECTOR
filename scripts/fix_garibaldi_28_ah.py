"""
Correctif SURGICAL — Injection 2e copro RNC sur 28 BD GARIBALDI
(AH1602424 'PARIS (75015) – 28 boulevard Garibaldi', 13 lots hab /
27 tot, sans syndic au RNC). Confirmation terrain user 2026-05-20.

Pattern DISAMBIG (variante Suffren+INJECTION) : 2 copros coexistent
sur le meme bati BDNB 6KDV-F45P-6XA2 (parcelle CX0066 + CX0054, bati
moderne 2021). Pattern deja utilise pour 42|AVENUE|SAXE #AB8151755
(commit fix_perignon_saxe) et 11|AVENUE|SUFFREN #AD1287697 (snapshot
historique). Suffren strict pur abort car AD5922125 est deja sur la
cle 28|BOULEVARD|GARIBALDI ; on cree une cle disambig suffixee #immat.

Triple confirmation source-of-truth :
  - RNC live AH1602424 (tabular-api 3ea8e2c3-0038-...) :
    nom_usage='PARIS (75015) – 28 boulevard Garibaldi'
    adresse_reference='28 bd garibaldi 75015 Paris'
    date_immat=2021-10-19, date_reglement=2019-07-09, APRES_2010
    nombre_parcelles=2 : ref_cad_1=75056115CX0054 + ref_cad_2=
    75056115CX0066 (les 2 parcelles du bati 28 moderne). 13 lots
    hab + 14 commerces = 27 lots tot. nombre_adresses_complementaires
    =0. Mandat fini 2024-09-30 ('Pas de mandat en cours'), pas de
    representant legal RNC.
  - BDNB pivot bgid 6KDV-F45P-6XA2 (parcelle CX0066, 2021) :
    l_libelle_adr=['3 rue clouet', '28 Boulevard Garibaldi']
    nb_log=13 (= matche AH1602424 13 lots habit)
    nb_log_rnc=16 (= 3 AD5922125 + 13 AH1602424, MATCHE post-fix)
    rel_RNC 2 rows : AD5922125 (deja attribuee dans light) +
    AH1602424 (cible de ce fix).
  - Distinction des 2 copros sur le meme bati :
    AD5922125 'SDC 26/28 BD GARIBALDI' = copro historique 1950,
      3 lots habit + 15 commerces/bureaux, parcelle CX0054 seule
      (cour/RDC commerce), date_immat 2018, mandat fini 2025-12-31.
      Le '26/28' du nom est UN HERITAGE HISTORIQUE - le 26 (bati
      PNXA 1850 parcelle CX0067) n'est PAS couvert (verifie 0 row
      ref_cadastrale_X=CX0067).
    AH1602424 'PARIS – 28 boulevard Garibaldi' = copro VEFA
      moderne 2021, 13 lots habit residentiels, parcelles CX0054
      +CX0066 (le bati moderne + annexe historique).

ANOMALIE LIGHT ACTUELLE (corrigee par ce fix) :
  - 28|BOULEVARD|GARIBALDI attribue a AD5922125 uniquement (3 lots
    hab, copro historique RDC). La vraie copro residentielle
    moderne AH1602424 (13 lots hab) est ABSENTE du snapshot RNC.
    Pattern identique a AD2301695 (Suffren) et AB8146169 (Lowendal).

Mecanisme : INJECT entry adresses[] avec cle disambig suffixee
'28|BOULEVARD|GARIBALDI #AH1602424' (clone bgid 6KDV depuis 28 source)
+ INJECT copro AH1602424 dans coproprietes[] (cle_adresse=cle disambig).
AD5922125 sur '28|BOULEVARD|GARIBALDI' reste INCHANGE (toujours
attribuee, garde ses ventes DVF).

Effet parc (modele renderSecteur Sec 6) :
  - bgid 6KDV avant : bgRncLots={AD5922125:3} = 3 logements RNC
  - bgid 6KDV apres : bgRncLots={AD5922125:3, AH1602424:13} = 16
    logements RNC (= MATCHE exactement nb_log_rnc BDNB pivot)
  - Delta parc = +13 logements (switch BDNB(13)->RNC complete sur
    6KDV, PIPELINE Sec 6 lots RNC prioritaires).

Ventes : les 1 vlog 2023 (vente bloc 2 lots VEFA 1.156M EUR, lot 12
Appartement 84m2 + lot 21 Dependance) restent sur AD5922125 (cle non-
disambig). AH1602424 entree est vide cote ventes (probablement
correct : copro neuve livraison 2021, 1ere vente DVF est promoteur).
Au render, AH1602424 affichera 0 vlog / taux Fige (cohérent).

Source-of-truth a porter dans make_light_motte_picquet.py :
  - INJECT copro AH1602424 (cle '28|BOULEVARD|GARIBALDI #AH1602424')
    + INJECT entry adresses[] disambig (clone bgid 6KDV).
  - Investiguer pourquoi AH1602424 absent du snapshot RNC malgre
    date_immat 2021-10-19 (pattern identique a AD2301695/AB8146169 :
    filtre code_postal ou ID resource desuet).

Cible : data/secteur_motte_picquet_light.json. Backup
.pregaribah.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_garibaldi_28_ah.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_garibaldi_28_ah.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.pregaribah.bak"

SOURCE_CLE = "28|BOULEVARD|GARIBALDI"           # entry source clone (AD5922125)
NEW_CLE = "28|BOULEVARD|GARIBALDI #AH1602424"   # cle disambig suffixee
IMMAT = "AH1602424"
BGID = "bdnb-bg-6KDV-F45P-6XA2"

# RNC live AH1602424 figees ici pour reproductibilite
RNC_LIVE = {
    "numero_immatriculation": IMMAT,
    "nom_copropriete": "PARIS (75015) – 28 boulevard Garibaldi",
    "syndic": None,                # mandat fini 2024-09-30, pas de syndic actif
    "_syndic_src": "rnc_live_mandat_fini",
    "nb_lots_total": 27,
    "nb_lots_habitation": 13,
    "nb_lots_habitation_rnc": 13,
}


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


def build_inject_adr(src_entry):
    """Entry adresses[] disambig (clone bgid 6KDV depuis 28 source)."""
    return {
        "cle": NEW_CLE,
        "adresse": "28 BOULEVARD GARIBALDI",
        "longitude": src_entry.get("longitude"),
        "latitude": src_entry.get("latitude"),
        "code_iris": src_entry.get("code_iris"),
        "_coord_source": "rnc_inject_pattern_suffren_disambig",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": RNC_LIVE["syndic"],
        "_syndic_src": RNC_LIVE["_syndic_src"],
        "numero_immatriculation": IMMAT,
        "nb_lots_habitation": RNC_LIVE["nb_lots_habitation"],
        # Ventes vides : les ventes DVF du 28 restent sur la cle non-
        # disambig (AD5922125). AH1602424 entry vide cote ventes -
        # copro neuve VEFA 2021, 1ere vente DVF 17/05/2023 est probable-
        # ment promoteur (vente bloc 2 lots dont 1 Dependance), garde
        # sur AD5922125 par defaut.
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation": 0.0,
        "classement_rotation": "Fige",
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Figé",
        # BDNB clone (bgid 6KDV : moderne 2021, residentiel collectif)
        "nb_log_bdnb": src_entry.get("nb_log_bdnb"),
        "annee_construction": src_entry.get("annee_construction"),
        "classe_dpe": src_entry.get("classe_dpe"),
        "type_batiment": src_entry.get("type_batiment"),
        "type_chauffage": src_entry.get("type_chauffage"),
        "batiment_groupe_id": BGID,
        "_bdnb_match": "immat_inject_pattern_suffren_disambig",
        "_taux_logement_src": "filtre_habitation",
        "usage_principal_bdnb": src_entry.get("usage_principal_bdnb"),
        "_usage_bdnb_src": src_entry.get("_usage_bdnb_src"),
    }


def build_copro(adr_entry):
    """Ligne coproprietes[] AH1602424 ancree sur cle disambig."""
    return {
        "numero_immatriculation": IMMAT,
        "nom_copropriete": RNC_LIVE["nom_copropriete"],
        "syndic": RNC_LIVE["syndic"],
        "_syndic_src": RNC_LIVE["_syndic_src"],
        "adresse": "28 Boulevard Garibaldi | 28 Boulevard Garibaldi 75015 Paris | 75015 | Paris",
        "longitude": adr_entry.get("longitude"),
        "latitude": adr_entry.get("latitude"),
        "code_iris": adr_entry.get("code_iris"),
        "cle_adresse": NEW_CLE,
        "nb_lots_total": RNC_LIVE["nb_lots_total"],
        "nb_lots_habitation": RNC_LIVE["nb_lots_habitation"],
        "nb_lots_habitation_rnc": RNC_LIVE["nb_lots_habitation_rnc"],
        "nb_log_bdnb": adr_entry.get("nb_log_bdnb"),
        "nb_ventes_2021_2025": 0,
        "ventes_par_an": {},
        "taux_rotation_5ans": 0.0,
        "classement_rotation": "Figé",
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}
    by_immat = {c.get("numero_immatriculation"): c
                for c in light["coproprietes"]
                if c.get("numero_immatriculation")}

    abort = []
    src = by.get(SOURCE_CLE)
    if src is None:
        abort.append(f"source absente : {SOURCE_CLE}")
    elif src.get("batiment_groupe_id") != BGID:
        abort.append(f"bgid divergent {SOURCE_CLE} : "
                     f"{src.get('batiment_groupe_id')} != {BGID}")
    if by.get(NEW_CLE) is not None:
        abort.append(f"cle disambig {NEW_CLE} deja presente")
    if IMMAT in by_immat:
        abort.append(f"immat {IMMAT} deja injectee "
                     f"(cle={by_immat[IMMAT].get('cle_adresse')!r})")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    psrc = pby.get(SOURCE_CLE)

    inject_adr = False
    inject_cp = False
    new_adr = None
    new_cp = None
    if not abort and psrc is not None:
        new_adr = build_inject_adr(psrc)
        patched["adresses"].append(new_adr)
        pby[NEW_CLE] = new_adr
        inject_adr = True
        new_cp = build_copro(new_adr)
        patched["coproprietes"].append(new_cp)
        inject_cp = True

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX 28 GARIBALDI (INJECT AH1602424 disambig) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  Source clone    : {SOURCE_CLE}  bgid={src and src.get('batiment_groupe_id')}")
    print(f"  Cle disambig    : {NEW_CLE}")
    print(f"  Immat injectee  : {IMMAT}  {RNC_LIVE['nom_copropriete']!r}")
    print(f"  Lots            : {RNC_LIVE['nb_lots_total']} tot / "
          f"{RNC_LIVE['nb_lots_habitation']} hab")
    print(f"  Syndic          : {RNC_LIVE['syndic']!r} "
          f"(src={RNC_LIVE['_syndic_src']}, mandat fini 2024-09-30)")
    print(f"  Cohabitation    : AD5922125 (3 lots hab historique 1950) reste "
          f"sur {SOURCE_CLE} avec ses ventes DVF (1 vlog 2023)")
    print(f"  Inject adresse  : {inject_adr}")
    print(f"  Inject copro    : {inject_cp}")
    print("-" * 78)
    b0, k0 = contrib0.get(BGID, (0, "-"))
    b1, k1 = contrib1.get(BGID, (0, "-"))
    print(f"  bgid {BGID} : {b0} ({k0}) -> {b1} ({k1}) = {b1 - b0:+d} logements")
    print(f"    (verif coherence : nb_log_rnc BDNB pivot 6KDV = 16, "
          f"post-fix = {b1} {'MATCHE' if b1 == 16 else 'DIVERGE'})")
    print("-" * 78)
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
    if not (inject_adr and inject_cp):
        print("ABORT : aucune injection appliquee.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_garibaldi_28_ah"] = (
        f"Copro RNC AH1602424 ('{RNC_LIVE['nom_copropriete']}', "
        f"{RNC_LIVE['nb_lots_habitation']} lots hab / "
        f"{RNC_LIVE['nb_lots_total']} tot, sans syndic - mandat fini "
        "2024-09-30) injectee dans coproprietes[] + entry adresses[] "
        f"avec cle disambig '{NEW_CLE}'. Pattern DISAMBIG (variante "
        "Suffren+INJECTION) : 2 copros coexistent sur bati 6KDV-F45P-"
        "6XA2 (parcelle CX0066+CX0054, bati moderne 2021). AD5922125 "
        "'SDC 26/28 BD GARIBALDI' = copro historique 1950 RDC commerces "
        "(3 lots hab + 15 commerces, parcelle CX0054 seule, '26/28' du "
        "nom = heritage historique - le 26 bati PNXA parcelle CX0067 "
        "n'est PAS couvert) reste sur cle non-disambig avec ses ventes "
        "DVF. AH1602424 'PARIS – 28 boulevard Garibaldi' = vraie copro "
        "residentielle moderne VEFA 2021 (date_immat 2021-10-19, "
        "reglement 2019-07-09, APRES_2010, 2 parcelles CX0054+CX0066). "
        "Triple confirmation : RNC live + BDNB rel_RNC R41C 6KDV 2 "
        "rows (AD5922125+AH1602424) + BDNB nb_log_rnc=16 = MATCHE "
        f"exactement 3+13 post-fix. Parc {parc0}->{parc1} ({delta:+d} "
        "= switch BDNB(13)->RNC complete sur 6KDV, PIPELINE Sec 6). "
        "Ventes : 1 vlog 2023 (vente bloc 2 lots VEFA promoteur 1.156M "
        "EUR) reste sur AD5922125 (cle non-disambig). Pattern identique "
        "a 42|AVENUE|SAXE #AB8151755 (fix_perignon_saxe) et 11|AVENUE|"
        "SUFFREN #AD1287697 (snapshot historique).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 entry adresses disambig + "
          f"1 copro AH1602424)")


if __name__ == "__main__":
    main()
