# -*- coding: utf-8 -*-
"""
Construit data/dauphine-lacassagne-sci-exclusions.json depuis les 2 CSV
d'arbitrage tertiaire du chantier Part-Dieu NR (2026-10-13/14).

Fichier produit = liste FIGEE des fiches SCI exclues de l'export CSV et du
courrier. Elles restent dans les donnees et visibles dans l'outil : seul le
front les retire de filtrerSciPourCourrier() quand la case "Exclure les
grands ensembles tertiaires" est cochee (cochee par defaut).

Cle = "<sci_siren>|<parcelle>", volontairement PAS le SIREN nu : la dedup de
loadSciData (sci_siren||sci_nom, 1re occurrence gagnante) peut faire gagner
une fiche d'une AUTRE zone pour le meme SIREN. Exclure par SIREN nu sortirait
2 prospects Montchat legitimes (AS2M 811928365, FONCIERE DI 01 2004 449498922).

Dry-run par defaut. --apply pour ecrire.
Usage : python scripts/_build_sci_exclusions_part_dieu.py [--apply]
"""
import csv, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = [("data/_part_dieu_exclusion_tertiaire.csv", "ferme"),
       ("data/_part_dieu_horsAR_300plus.csv", "horsAR")]
SCI = "data/dauphine-lacassagne-sci.json"
OUT = "data/dauphine-lacassagne-sci-exclusions.json"
ZONE = "Part-Dieu NR"
APPLY = "--apply" in sys.argv

CRITERES = [
    {"id": "C1_centre_commercial", "libelle": "Centre commercial",
     "regle": "libelle de voie MAJIC contenant 'CTRE COMMERCIAL'"},
    {"id": "C2_numero_pseudo", "libelle": "Pseudo-numero d'ensemble",
     "regle": "numero de voirie MAJIC >= 9000 (numero fictif d'ensemble immobilier)"},
    {"id": "C3_AR_300plus", "libelle": "Parcelle AR a plus de 300 locaux",
     "regle": "parcelle de la section AR portant > 300 locaux MAJIC"},
    {"id": "C4_horsAR_300plus", "libelle": "Parcelle hors AR a plus de 300 locaux",
     "regle": "parcelle hors section AR portant > 300 locaux MAJIC"},
]


def criteres_de(row, src):
    """Normalise critere_declencheur du CSV vers les ids stables ci-dessus."""
    brut = (row.get("critere_declencheur") or "").strip()
    ids = []
    if "C1_centre_commercial" in brut:
        ids.append("C1_centre_commercial")
    if "C2_numero_pseudo" in brut:
        ids.append("C2_numero_pseudo")
    if "C3_AR" in brut:
        ids.append("C3_AR_300plus")
    if not ids and src == "horsAR":
        ids.append("C4_horsAR_300plus")
    return ids, brut


def main():
    rows = []
    for rel, src in SRC:
        with open(os.path.join(ROOT, rel), encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                r["_src"] = src
                rows.append(r)

    excl, vus = [], set()
    for r in rows:
        siren, parcelle = r["sci_siren"].strip(), r["parcelle"].strip()
        cle = siren + "|" + parcelle
        if cle in vus:
            print("  ! doublon ignore :", cle)
            continue
        vus.add(cle)
        ids, brut = criteres_de(r, r["_src"])
        try:
            locaux = int(r["locaux_majic_parcelle"])
        except (ValueError, KeyError, TypeError):
            locaux = None
        excl.append({
            "siren": siren, "parcelle": parcelle, "zone": ZONE,
            "sci_nom": r["sci_nom"].strip(),
            "adresse_bien": r["adresse_bien"].strip(),
            "criteres": ids,
            "critere_source": brut or "(hors-AR > 300 locaux)",
            "locaux_majic_parcelle": locaux,
        })
    excl.sort(key=lambda e: (e["parcelle"], e["siren"]))

    # Orphelines ATTENDUES : regles qui ne matchent aucune fiche VISIBLE, parce que
    # la dedup du front ne garde qu'une fiche par SIREN. Calcule ici pour que le
    # front n'alerte que si ce nombre AUGMENTE (= la liste a vraiment peri).
    sci_pre = json.load(open(os.path.join(ROOT, SCI), encoding="utf-8"))
    _seen, _all = set(), []
    for _s in sci_pre["sci"]:
        _k = _s.get("sci_siren") or _s.get("sci_nom")
        if _k in _seen:
            continue
        _seen.add(_k)
        _all.append(_s)
    _cles_front = {(x.get("sci_siren") or "") + "|" + (x.get("parcelle") or "") for x in _all}
    orphelines = sum(1 for e in excl
                     if (e["siren"] + "|" + e["parcelle"]) not in _cles_front)

    doc = {
        "_meta": {
            "objet": ("Fiches SCI exclues de l'EXPORT CSV et du COURRIER. Elles restent "
                      "dans les donnees et visibles dans l'outil : seuls l'export et "
                      "l'envoi de courrier les ignorent."),
            "reversible": ("Decocher la case « Exclure les grands ensembles tertiaires » "
                           "dans la modale Export CSV ou Courrier. Aucune modification de "
                           "code ni de deploiement necessaire."),
            "zone": ZONE,
            "agence": "dauphine-lacassagne",
            "decide_par": "Yann",
            "date_decision": "2026-10-14",
            "cle": "sci_siren|parcelle",
            "cle_pourquoi": ("PAS le SIREN nu : la dedup du front (sci_siren||sci_nom, 1re "
                             "occurrence gagnante, cf. CLAUDE.md §7) peut faire gagner une "
                             "fiche d'une autre zone pour le meme SIREN. Exclure par SIREN "
                             "nu sortirait 2 prospects Montchat legitimes (AS2M 811928365 "
                             "au 6 imp Victor Hugo, FONCIERE DI 01 2004 449498922 au 65 av "
                             "Lacassagne)."),
            "criteres": CRITERES,
            "non_retenu": {
                "AY0088": ("Grande copropriete d'HABITATION (537 locaux MAJIC, 70 personnes "
                           "morales, 19 batiments, 8 adresses). Les 29 fiches restent "
                           "prospectables. Decision Yann 2026-10-14 ; arbitrage conserve "
                           "dans data/_part_dieu_ay0088_a_trancher.csv.")
            },
            "hors_perimetre": {
                "449498922": ("FONCIERE DI 01 2004 (397 biens, siege quai d'Austerlitz) reste "
                              "prospectable sous sa fiche Montchat. Un critere « gros "
                              "detenteur » n'a pas ete pose : hors perimetre, decision Yann.")
            },
            "orphelines_attendues": orphelines,
            "orphelines_pourquoi": (
                "%d des regles ne matchent aucune fiche VISIBLE dans l'outil : la dedup "
                "du front (sci_siren||sci_nom) ne garde qu'une fiche par SIREN, et pour "
                "ces SCI c'est une fiche d'une autre parcelle (10 cas) ou d'une autre "
                "zone (2 cas Montchat) qui gagne. C'est normal et attendu : le front "
                "n'alerte que SI ce nombre augmente, signe que la liste a peri."
                % orphelines),
            "sources": [rel for rel, _ in SRC],
            "regenerer": "python scripts/_build_sci_exclusions_part_dieu.py --apply",
        },
        "exclusions": excl,
    }

    # ---- controles de non-regression ----
    sci = json.load(open(os.path.join(ROOT, SCI), encoding="utf-8"))
    seen, allsci = set(), []
    for s in sci["sci"]:
        k = s.get("sci_siren") or s.get("sci_nom")
        if k in seen:
            continue
        seen.add(k)
        allsci.append(s)
    cles_front = {(s.get("sci_siren") or "") + "|" + (s.get("parcelle") or ""): s
                  for s in allsci}
    cles = {e["siren"] + "|" + e["parcelle"] for e in excl}
    match = [cles_front[k] for k in cles if k in cles_front]
    hors = [s for s in match if s.get("zone") != ZONE]
    robin = [s for s in match if s.get("lot") == "robin"]

    print("=== CONTROLES ===")
    print("  lignes CSV lues ............... %d" % len(rows))
    print("  cles d'exclusion (uniques) .... %d" % len(cles))
    print("  fiches visibles matchees ...... %d" % len(match))
    print("  regles sans fiche visible ..... %d" % (len(cles) - len(match)))
    print("  matchees hors zone %-12s %d  <- doit etre 0" % (ZONE, len(hors)))
    print("  matchees lot=robin ............ %d  <- doit etre 0" % len(robin))
    assert not hors, "REGRESSION : fiche hors %s matchee" % ZONE
    assert not robin, "REGRESSION : fiche lot=robin matchee"
    print("  par critere : %s" % dict(collections.Counter(
        c for e in excl for c in e["criteres"])))

    txt = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    dest = os.path.join(ROOT, OUT)
    if APPLY:
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        print("\nECRIT : %s (%d octets)" % (OUT, len(txt.encode("utf-8"))))
    else:
        print("\nDRY-RUN — rien ecrit. Cible : %s (%d octets)"
              % (OUT, len(txt.encode("utf-8"))))
        print("  le fichier existe deja ? %s" % os.path.exists(dest))


if __name__ == "__main__":
    main()
