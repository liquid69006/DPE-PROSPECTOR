"""
_etape5_ecrire_part_dieu_nr.py
─────────────────────────────────────────────────────────────────
ETAPE 5 : ajoute les fiches zone "Part-Dieu NR" a
data/dauphine-lacassagne-sci.json. STRICTEMENT ADDITIF.

Garanties :
  - sauvegarde .prepartdieu.bak avant toute ecriture
  - les 2567 fiches existantes sont reecrites a l'IDENTIQUE, au meme
    rang, et verifiees par MD5 avant/apres
  - aucun champ `lot` sur les nouvelles fiches (decision Yann) :
    la valeur de `zone` suffit a isoler le lot
  - nb_biens_total calcule comme majic_sci_2025.py:256-265
    (comptage France entiere, forme 6540, dedup section+parcelle+siren)

Usage :
  python scripts/_etape5_ecrire_part_dieu_nr.py            # dry-run
  python scripts/_etape5_ecrire_part_dieu_nr.py --write    # ecrit
"""

import argparse
import collections
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
DATA   = os.path.join(RACINE, "data")
SCI    = os.path.join(DATA, "dauphine-lacassagne-sci.json")
BAK    = SCI + ".prepartdieu.bak"
CAND   = os.path.join(DATA, "_part_dieu_nr_candidats.json")
MAJIC  = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

ZONE   = "Part-Dieu NR"
ORDRE  = ["zone", "parcelle", "adresse_bien", "sci_nom", "sci_siren",
          "nb_biens_total", "code_droit", "millesime", "sci_active",
          "siege_social", "gerants",
          "siege_verifie", "siege_statut", "siege_score", "siege_lon", "siege_lat"]


def empreinte(fiches):
    """MD5 d'une liste de fiches, serialisation stable."""
    s = json.dumps(fiches, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def nb_biens_france():
    """Portefeuille national par SIREN — meme calcul que majic_sci_2025.py:256-265."""
    import pyarrow.parquet as pq
    t = pq.read_table(MAJIC, columns=["forme_juridique", "section",
                                      "numero_parcelle", "numero_siren"],
                      filters=[("forme_juridique", "=", "6540")])
    sec = t.column("section").to_pylist()
    par = t.column("numero_parcelle").to_pylist()
    sir = t.column("numero_siren").to_pylist()
    vus, cpt = set(), collections.Counter()
    for s, p, si in zip(sec, par, sir):
        cle = (str(s), str(p), str(si))
        if cle in vus:
            continue
        vus.add(cle)
        cpt[str(si)] += 1
    return cpt


def main(write):
    print("=" * 74)
    print("  ETAPE 5 — ajout des fiches « %s » (additif strict)" % ZONE)
    print("=" * 74)

    doc = json.load(io.open(SCI, encoding="utf-8"))
    avant = doc["sci"]
    n_avant = len(avant)
    md5_avant = empreinte(avant)
    robin_avant = sum(1 for f in avant if f.get("lot") == "robin")
    n_avant_robin = [f for f in avant if f.get("code_droit") == "N" and f.get("lot") == "robin"]
    print("\n[1] Etat initial")
    print("    fiches        : %d" % n_avant)
    print("    MD5           : %s" % md5_avant)
    print("    lot robin     : %d" % robin_avant)
    print("    robin code_droit=N : %d (%s)"
          % (len(n_avant_robin), ", ".join(f["sci_siren"] for f in n_avant_robin)))
    print("    zones         : %s" % dict(collections.Counter(f.get("zone") for f in avant)))

    cand = json.load(io.open(CAND, encoding="utf-8"))["candidats"]
    retenus = [c for c in cand if not str(c["siege_statut"]).startswith("EXCLU")]
    print("\n[2] Candidats")
    print("    total         : %d" % len(cand))
    print("    exclus        : %d" % (len(cand) - len(retenus)))
    print("    A AJOUTER     : %d" % len(retenus))

    print("\n[3] nb_biens_total (comptage France, forme 6540)")
    cpt = nb_biens_france()
    print("    %d SIREN SCI distincts en France" % len(cpt))

    nouvelles = []
    for c in sorted(retenus, key=lambda x: (x["parcelle"], x["sci_siren"])):
        f = {
            "zone":           ZONE,
            "parcelle":       c["parcelle"],
            "adresse_bien":   c["adresse_bien"],
            "sci_nom":        c["sci_nom"],
            "sci_siren":      c["sci_siren"],
            "nb_biens_total": int(cpt.get(c["sci_siren"], 1)),
            "code_droit":     c["code_droit"],
            "millesime":      int(c["millesime"]),
            "sci_active":     c["sci_active"],
            "siege_social":   c["siege_social"],
            "gerants":        c["gerants"],
            "siege_verifie":  bool(c["siege_verifie"]),
            "siege_statut":   c["siege_statut"],
            "siege_score":    c["siege_score"],
            "siege_lon":      c["siege_lon"],
            "siege_lat":      c["siege_lat"],
        }
        nouvelles.append({k: f[k] for k in ORDRE})

    print("\n[4] Fiches construites : %d" % len(nouvelles))
    print("    siege_verifie=True  : %d" % sum(1 for f in nouvelles if f["siege_verifie"]))
    print("    siege_verifie=False : %d" % sum(1 for f in nouvelles if not f["siege_verifie"]))
    print("    motifs : %s" % dict(collections.Counter(f["siege_statut"] for f in nouvelles)))
    print("    nb_biens_total : moyenne %.2f  max %d  =1 : %d"
          % (sum(f["nb_biens_total"] for f in nouvelles) / len(nouvelles),
             max(f["nb_biens_total"] for f in nouvelles),
             sum(1 for f in nouvelles if f["nb_biens_total"] == 1)))

    apres = avant + nouvelles

    print("\n[5] CONTROLES D'INTEGRITE")
    md5_apres = empreinte(apres[:n_avant])
    ok1 = md5_apres == md5_avant
    print("    C1 MD5 des %d premieres fiches" % n_avant)
    print("       avant %s" % md5_avant)
    print("       apres %s   -> %s" % (md5_apres, "IDENTIQUE" if ok1 else "DIVERGENT"))
    ok1b = all(a is b for a, b in zip(avant, apres[:n_avant]))
    print("    C1b identite objet (aucune copie/mutation) : %s" % ("OK" if ok1b else "ALERTE"))

    robin_apres = sum(1 for f in apres if f.get("lot") == "robin")
    ok2 = robin_apres == robin_avant == 650
    print("    C2 lot robin : %d -> %d  -> %s" % (robin_avant, robin_apres, "OK" if ok2 else "ALERTE"))

    n_apres = [f for f in apres if f.get("code_droit") == "N" and f.get("lot") == "robin"]
    attendus = {"477842330", "814132171", "U21893667"}
    ok3 = {f["sci_siren"] for f in n_apres} == attendus
    print("    C3 robin code_droit=N (3a589d3) : %d/%d  -> %s"
          % (len(n_apres), len(attendus), "OK" if ok3 else "ALERTE"))

    zn = collections.Counter(f.get("zone") for f in apres[:n_avant])
    ok4 = set(zn) == {"Dauphiné-Lacassagne", "Montchat"}
    print("    C4 zones des %d premieres inchangees : %s  -> %s"
          % (n_avant, dict(zn), "OK" if ok4 else "ALERTE"))

    ok5 = all("lot" not in f and "type_pm" not in f for f in nouvelles)
    print("    C5 aucun champ lot/type_pm sur les nouvelles : %s" % ("OK" if ok5 else "ALERTE"))

    ok6 = all(set(f.keys()) == set(ORDRE) for f in nouvelles)
    print("    C6 schema homogene des nouvelles : %s" % ("OK" if ok6 else "ALERTE"))

    # Dedup du front, mesuree sur le fichier REEL (index.html:6269-6276)
    seen, masquees, visibles = set(), [], 0
    for f in apres:
        k = f.get("sci_siren") or f.get("sci_nom")
        if k in seen:
            if f.get("zone") == ZONE:
                masquees.append(f)
        else:
            seen.add(k)
            visibles += 1
    pd_tot = sum(1 for f in apres if f.get("zone") == ZONE)
    print("\n[6] DEDUP DU FRONT (cle sci_siren||sci_nom, 1er gagnant) — mesure reelle")
    print("    fiches dans le fichier        : %d" % len(apres))
    print("    affichees apres dedup         : %d" % visibles)
    print("    ecartees au total             : %d" % (len(apres) - visibles))
    print("    dont zone « %s »     : %d / %d" % (ZONE, len(masquees), pd_tot))
    print("    -> nouvelles fiches VISIBLES  : %d" % (pd_tot - len(masquees)))

    tous_ok = all([ok1, ok1b, ok2, ok3, ok4, ok5, ok6])
    print("\n" + "=" * 74)
    if not tous_ok:
        print("  CONTROLES EN ECHEC — AUCUNE ECRITURE")
        sys.exit(1)
    if write:
        shutil.copy2(SCI, BAK)
        print("  sauvegarde : %s" % os.path.basename(BAK))
        doc["sci"] = apres
        doc["derniere_maj"] = datetime.now().isoformat()
        tmp = SCI + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SCI)
        relu = json.load(io.open(SCI, encoding="utf-8"))["sci"]
        print("  relecture  : %d fiches" % len(relu))
        print("  MD5 des %d premieres apres relecture : %s  -> %s"
              % (n_avant, empreinte(relu[:n_avant]),
                 "IDENTIQUE" if empreinte(relu[:n_avant]) == md5_avant else "DIVERGENT"))
        print("  ECRIT : %s" % SCI)
    else:
        print("  DRY-RUN — rien ecrit. Relancer avec --write.")
        print("  (le fichier passerait de %d a %d fiches)" % (n_avant, len(apres)))
    print("=" * 74)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    main(ap.parse_args().write)
