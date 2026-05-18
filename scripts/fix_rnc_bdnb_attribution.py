"""
Correctif d'attribution RNC -> BDNB par numero d'immatriculation.

Probleme (voir scripts/verif_rnc_bdnb.py et data/verif_rnc_bdnb_report.md) :
42 copros liees a la BDNB par `numero_immat_principal` n'ont AUCUNE ligne
dans `adresses` du fichier light -> le front (qui construit l'arbre depuis
`adresses` et joint la copro via coproByCle[a.cle]) ne les affiche pas du
tout et ne compte pas leurs logements (categorie B du rapport).

Correctif : pour chaque copro concernee dont la cle d'adresse n'entre PAS
en collision avec une ligne existante (sous-causes B1a / B1b / B2, 38
copros), on injecte UNE ligne `adresses` keyee par `copro.cle_adresse`,
portant le batiment BDNB principal lie a son immatriculation. Les copros
B3 (4) partagent une cle deja prise par une autre copro : non corrigeable
sans changer le modele de cle (indexation par (cle, immat)) -> listees,
non modifiees.

Invariant verifie : aucun bgid injecte n'est deja reference par une
adresse existante -> pas de double comptage dans le dedup du front.

Cible : data/secteur_dauphine_lacassagne_light.json (seul fichier charge
par le front). Le fichier complet 16 Mo n'est pas charge cote client.

Usage :
  python scripts/fix_rnc_bdnb_attribution.py            # DRY-RUN (defaut)
  python scripts/fix_rnc_bdnb_attribution.py --apply    # ecrit + .bak
"""

import sys
import json
import collections
from pathlib import Path

import os
ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"

NON_RENSEIGNE = {"non connu", "", None}


def cle_to_adresse(cle):
    """`2|RUE|DAHLIAS` -> `2 RUE DAHLIAS` (convention des lignes existantes)."""
    if not cle:
        return ""
    return " ".join(p for p in cle.split("|") if p != "").strip()


def construire_ligne(copro, bg, cle, adresse):
    """Ligne `adresses` (schema light) depuis la copro + le batiment BDNB.

    `cle` peut differer de copro['cle_adresse'] pour les cas B3
    (desambiguisation d'une adresse partagee) ; `adresse` reste le
    libelle propre derive de la cle d'origine.
    """
    vpa = copro.get("ventes_par_an") or {}
    return {
        "cle": cle,
        "adresse": adresse,
        "longitude": copro.get("longitude"),
        "latitude": copro.get("latitude"),
        "code_iris": copro.get("code_iris"),
        "_coord_source": "rnc_immat_fix",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": None,
        "sci_siren": None,
        "syndic": copro.get("syndic"),
        "_syndic_src": copro.get("_syndic_src"),
        "ventes_par_an": vpa,
        "nb_ventes_total": sum(vpa.values()) if vpa else 0,
        "nb_log_bdnb": bg.get("nb_log"),
        "annee_construction": bg.get("annee_construction"),
        "classe_dpe": bg.get("classe_bilan_dpe"),
        "type_batiment": bg.get("type_batiment_dpe"),
        "type_chauffage": bg.get("type_energie_chauffage"),
        "batiment_groupe_id": bg["batiment_groupe_id"],
        "_bdnb_match": "immat_fix",
    }


def main():
    apply = "--apply" in sys.argv

    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    copros, adresses = light["coproprietes"], light["adresses"]

    bg_meta = {r["batiment_groupe_id"]: r for r in bdnb}
    immat_to_bg = collections.defaultdict(set)
    for r in bdnb:
        im = r.get("numero_immat_principal")
        if im not in NON_RENSEIGNE:
            immat_to_bg[im].add(r["batiment_groupe_id"])

    secteur_bgids = {a["batiment_groupe_id"]
                     for a in adresses if a.get("batiment_groupe_id")}
    cles_existantes = {a.get("cle") for a in adresses}

    # Chaque element : (copro, bg_principal, cle_injectee, adresse_libelle,
    #                    bset, is_b3)
    a_injecter = []
    for c in copros:
        im = c.get("numero_immatriculation")
        cle = c.get("cle_adresse")
        if not im or im not in immat_to_bg or not cle:
            continue
        bset = immat_to_bg[im]
        if bset & secteur_bgids:
            continue                       # categorie A (deja represente)
        principal = max(bset, key=lambda g: (bg_meta[g].get("nb_log") or 0))
        libelle = cle_to_adresse(cle)
        if cle in cles_existantes:
            # B3 : cle deja prise par une autre copro -> desambiguisation
            # par (cle, immat). Reste pipe-3-safe (pas de '|' ajoute).
            cle_inj = f"{cle} #{im}"
            a_injecter.append((c, bg_meta[principal], cle_inj, libelle,
                               sorted(bset), True))
        else:
            a_injecter.append((c, bg_meta[principal], cle, libelle,
                               sorted(bset), False))

    # Invariant anti-double-comptage
    injectes_bg = [bg["batiment_groupe_id"] for _, bg, *_ in a_injecter]
    assert not (set(injectes_bg) & secteur_bgids), "COLLISION bgid existante"
    assert len(injectes_bg) == len(set(injectes_bg)), "bgid injecte en double"

    nb_b3 = sum(1 for *_, is_b3 in a_injecter if is_b3)
    tot_lots = sum((c.get("nb_lots_habitation") or 0)
                   for c, *_ in a_injecter)
    print("=" * 70)
    print("CORRECTIF ATTRIBUTION RNC -> BDNB par immatriculation")
    print("=" * 70)
    print(f"Mode                          : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Lignes adresses actuelles     : {len(adresses)}")
    print(f"Copros a injecter (total)     : {len(a_injecter)}")
    print(f"  dont B1a/B1b/B2             : {len(a_injecter) - nb_b3}")
    print(f"  dont B3 (cle desambiguisee) : {nb_b3}")
    print(f"Lots habitation RNC rendus visibles : {tot_lots}")
    print("-" * 70)
    print("Apercu (immat | cle injectee | copro | bgid | nb_log | nlots | B3):")
    for c, bg, cle_inj, _lib, bset, is_b3 in sorted(
            a_injecter, key=lambda x: -(x[0].get("nb_lots_habitation") or 0))[:25]:
        print(f"  {c['numero_immatriculation']} | {cle_inj:<30} | "
              f"{(c.get('nom_copropriete') or '')[:22]:<22} | "
              f"{bg['batiment_groupe_id']} | log={bg.get('nb_log')} | "
              f"nlots={c.get('nb_lots_habitation')}"
              f"{' | B3' if is_b3 else ''}")
    if len(a_injecter) > 25:
        print(f"  ... (+{len(a_injecter) - 25} autres)")
    print("-" * 70)
    print("B3 desambiguisees (cle_adresse copro modifiee -> cle#immat) :")
    for c, bg, cle_inj, _lib, _bs, is_b3 in a_injecter:
        if is_b3:
            print(f"  {c['numero_immatriculation']} | "
                  f"{c['cle_adresse']} -> {cle_inj} | "
                  f"{c.get('nom_copropriete')}")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. Relancer avec --apply pour ecrire.")
        return

    bak = LIGHT.with_suffix(".json.bak")
    bak.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    for c, bg, cle_inj, libelle, _bs, is_b3 in a_injecter:
        if is_b3:
            c["cle_adresse"] = cle_inj   # le front joint via coproByCle
        adresses.append(construire_ligne(c, bg, cle_inj, libelle))
    meta = light.setdefault("metadata", {})
    sg = meta.setdefault("stats_globales", {})
    sg["nb_adresses_croisement"] = len(adresses)
    meta["_correctif_rnc_immat"] = (
        f"{len(a_injecter)} adresses injectees via numero_immat_principal "
        f"(_bdnb_match=immat_fix) dont {nb_b3} B3 a cle desambiguisee "
        f"(cle_adresse copro suffixee #immat).")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {bak.name}")
    print(f"Ecrit : {LIGHT.name} ({len(adresses)} adresses)")


if __name__ == "__main__":
    main()
