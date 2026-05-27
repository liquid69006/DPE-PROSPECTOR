#!/usr/bin/env python3
"""Ventilation propriete SDC ANTOINE CHARIAL AA0358655 (lecture seule).

Cible : immat AA0358655 = bgid bdnb-bg-8U51-96UR-3947 = parcelle
69383000EI0113 (28/30 ETIENNE RICHERAND + 7-17 TERNOIS + 27/29 AUBIGNY,
10 adresses BAN sur 1 bati BDNB, 211 logements RNC).

Source MAJIC : majic_locaux2_2025.parquet (FICHIER 28B "LOCAUX 2").
  -> LIMITATION CRITIQUE : ce fichier contient UNIQUEMENT les Personnes
     Morales (PM). 0 row sans SIREN, 0 PP individuelle dans ce dataset.
     Les particuliers (lots vendus a des Personnes Physiques) ne sont
     PAS visibles ici.

Ventilation demandee :
  1. nb_lots_TOTAL du SDC (PM)
  2. nb_lots GRANDLYON HABITAT (SIREN 399898345)
  3. nb_lots SCI privees (PM non-publiques non-HLM)
  4. nb_lots PERSONNES PHYSIQUES  -> documenter limitation
  5. nb_lots AUTRES (public non-HLM / non classables)
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC2 = r"C:\Users\Station 5\majic_locaux2_2025.parquet"
MAJIC1 = r"C:\Users\Station 5\majic_locaux_2025.parquet"

PARCELLE = "69383000EI0113"
BGID = "bdnb-bg-8U51-96UR-3947"
IMMAT = "AA0358655"

# ============================================================
# Classification SIREN
# ============================================================
SIREN_GLH = "399898345"

# Public non-HLM : collectivites, etat, etablissements publics
# non-bailleurs sociaux
SIRENS_PUBLIC_NON_HLM = {
    "200046977": "METROPOLE DE LYON",
    "216901232": "COMMUNE DE LYON",  # approx
    "216900390": "COMMUNAUTE URBAINE DE LYON",
    "266901232": "DEPARTEMENT DU RHONE",
    "266900387": "DEPARTEMENT DU RHONE (var)",
    "130000338": "ETAT (Direction immobilier)",
    "266900007": "REGION AUVERGNE RHONE ALPES",
    "266900361": "HOSPICES CIVILS DE LYON",  # approx
}

# Bailleurs sociaux HLM connus (SIREN ou keywords)
HLM_SIRENS = {
    "399898345",  # GRANDLYON HABITAT
    "813755949",  # OPH METROPOLE LYON
    "778596510",  # BATIGERE RHONE ALPES
    "960506152",  # ALLIADE HABITAT
    "552046484",  # CDC HABITAT
    "470801168",  # CDC HABITAT var
    "398115808",  # IMMOBILIERE RHONE ALPES
    "779537125",  # ALPES ISERE HABITAT
    "339804858",  # FONCIERE D'HABITAT
}
HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT", "OFFICE PUBLIC DE L'HABITAT",
)
# Keywords public non-HLM (collectivites, hopitaux publics, SEM, fondations)
PUBLIC_NON_HLM_KEYWORDS = (
    "COMMUNE DE LYON", "METROPOLE DE LYON", "DEPARTEMENT DU RHONE",
    "REGION AUVERGNE", "REGION RHONE", "ETAT ", "ETAT,",
    "HOSPICES CIVILS", "CENTRE HOSPITALIER",
    "COMMUNAUTE URBAINE", "GRAND LYON", "DIRECTION DE L IMMOBILIER",
    "SEM ", "FONCIERE VESTA", "FONCIERE PIERRE",
    "CENTRE REGIONAL OEUVRES", "CROUS",
    "ASSOCIATION DIOCESAINE", "FONDATION", "ITINOVA",
    "INSTITUT NATIONAL", "INSTITUT DE FRANCE",
)


def classify_siren(siren, denomination, groupe, forme):
    """Categorise un SIREN : GLH / HLM_AUTRE / PUBLIC_NON_HLM / SCI_PRIVE /
    SOCIETE_PRIVEE / AUTRE."""
    s = str(siren or "")
    dn = (denomination or "").upper()
    gp = (groupe or "").upper()
    fj = (forme or "").upper()

    if s == SIREN_GLH:
        return "GLH"
    if s in HLM_SIRENS:
        return "HLM_AUTRE"
    if "OFFICE HLM" in gp or any(n in dn for n in HLM_NEEDLES if n.strip()):
        return "HLM_AUTRE"

    if s in SIRENS_PUBLIC_NON_HLM:
        return "PUBLIC_NON_HLM"
    if any(k in dn for k in PUBLIC_NON_HLM_KEYWORDS):
        return "PUBLIC_NON_HLM"
    if "ETABLISSEMENTS PUBLICS" in gp or "COLLECTIVITE" in fj.upper():
        return "PUBLIC_NON_HLM"

    # SCI explicite
    if dn.startswith("SCI ") or " SCI " in dn or "SOCIETE CIVILE IMMOBIL" in dn:
        return "SCI_PRIVE"

    # SARL/SAS/etc. (PM "personnes morales non remarquables")
    if "PERSONNES MORALES NON REMARQUABLES" in gp:
        return "SCI_PRIVE"

    if "SARL" in fj or "SAS" in fj or "SOCIETE" in fj:
        return "SOCIETE_PRIVEE"
    if "ASSOCIATION" in gp or "ASSOCIATION" in fj:
        return "AUTRE_NON_LUCRATIF"

    return "AUTRE"


CATS_ORDER = ["GLH", "HLM_AUTRE", "PUBLIC_NON_HLM", "SCI_PRIVE",
              "SOCIETE_PRIVEE", "AUTRE_NON_LUCRATIF", "AUTRE"]


# ============================================================
print("=" * 78)
print(f"VENTILATION SDC ANTOINE CHARIAL  ({IMMAT})")
print(f"  bgid     : {BGID}")
print(f"  parcelle : {PARCELLE}")
print("=" * 78)

# Verification du parc RNC selon light
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
co_match = [c for c in doc["coproprietes"]
            if c.get("numero_immatriculation") == IMMAT]
print(f"\n  RNC light : {len(co_match)} entree(s) pour immat {IMMAT}")
if co_match:
    c = co_match[0]
    print(f"    cle_adresse        : {c.get('cle_adresse')}")
    print(f"    nom_copropriete    : {c.get('nom_copropriete')}")
    print(f"    nb_lots_total      : {c.get('nb_lots_total')}")
    print(f"    nb_lots_habitation : {c.get('nb_lots_habitation')}")
    print(f"    syndic             : {c.get('syndic')}")

# ============================================================
# [1] Confirmation : la parcelle EI0113 couvre-t-elle uniquement ce SDC ?
# ============================================================
print()
print("[1] La parcelle EI0113 couvre-t-elle UNIQUEMENT le SDC AA0358655 ?")
# Methode : verifier que toutes les adresses light sur cette parcelle
# ont le meme immat principal OU sont FA vers la meme ancre
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}

# Cles light sur le bgid 8U51-96UR-3947
cles_sur_bgid = [a for a in ad
                  if a.get("batiment_groupe_id") == BGID]
print(f"  Adresses light sur bgid {BGID} : {len(cles_sur_bgid)}")
immats_sur_bgid = set()
for a in cles_sur_bgid:
    cle = a.get("cle") or ""
    cp = co_by_cle.get(cle, {})
    imm = cp.get("numero_immatriculation") or a.get("numero_immatriculation")
    if imm:
        immats_sur_bgid.add(imm)
print(f"  Immats RNC distincts sur ce bgid : {immats_sur_bgid}")

# ============================================================
# [2] Query MAJIC parcelle EI0113
# ============================================================
print()
print("[2] MAJIC parcelle EI0113 - tous proprietaires PM")
tbl = pq.read_table(MAJIC2, filters=[
    ("departement", "=", "69"), ("code_commune", "=", "383"),
    ("section", "=", "EI"), ("numero_parcelle", "=", 113),
])
df = tbl.to_pandas()
print(f"  rows MAJIC total : {len(df)}")
print(f"  rows sans SIREN  : {df['numero_siren'].isna().sum()}")

# Distribution code_droit
print(f"\n  Code droit distribution :")
for cd, n in df["code_droit_libelle"].value_counts().items():
    print(f"    {cd:32s} : {n}")

# ============================================================
# [3] Filtrer P + E (exclure syndics/mandataires)
# ============================================================
print()
print("[3] Filtre code_droit P + E (exclure syndic/mandataire)")
keep = df[df["code_droit"].isin(["P", "E"])].copy()
print(f"  rows P+E : {len(keep)}")

# Verifier rows pour 28 ETIENNE et 30 ETIENNE
print(f"\n  rows par adresse MAJIC (numero+voie) :")
keep["_addr"] = (keep["numero_voirie"].fillna("").astype(str).str.lstrip("0")
                 + keep["indice_de_repetition"].fillna("").astype(str)
                 + " " + keep["nature_voie"].fillna("").astype(str)
                 + " " + keep["nom_voie"].fillna("").astype(str))
keep["_addr"] = keep["_addr"].str.strip()
for adr, n in keep["_addr"].value_counts().items():
    print(f"    {n:>4} {adr}")

# ============================================================
# [4] Classification par SIREN
# ============================================================
print()
print("[4] Classification par SIREN")
keep["_cat"] = keep.apply(
    lambda r: classify_siren(r.get("numero_siren"),
                              r.get("denomination"),
                              r.get("groupe_personne_libelle"),
                              r.get("forme_juridique_libelle")),
    axis=1,
)

# Agreg par (cat, SIREN)
grp = (keep.groupby(["_cat", "numero_siren", "denomination",
                     "code_droit_libelle", "groupe_personne_libelle",
                     "forme_juridique_libelle"], dropna=False)
       .size().reset_index(name="nb_lots")
       .sort_values(["_cat", "nb_lots"], ascending=[True, False]))

print(f"\n  Detail par categorie + SIREN :")
print(f"    {'cat':18s} {'SIREN':12s} {'lots':>5} {'droit':14s} {'denomination'}")
print("    " + "-" * 90)
for _, row in grp.iterrows():
    cat = str(row["_cat"])
    sir = str(row["numero_siren"] or "-")
    nb = int(row["nb_lots"])
    dr = str(row["code_droit_libelle"] or "-")
    dn = str(row["denomination"] or "-")[:35]
    print(f"    {cat:18s} {sir:12s} {nb:>5} {dr:14s} {dn}")

# ============================================================
# [5] Tableau de ventilation final
# ============================================================
print()
print("=" * 78)
print("[5] TABLEAU DE VENTILATION (lots PM uniquement)")
print("=" * 78)

n_total = len(keep)
print(f"\n  {'Categorie':25s} {'nb_lots':>8} {'%':>6} {'nb_props':>9} "
      f"{'top owner'}")
print("  " + "-" * 92)
cat_totals = {}
cat_props = {}
for cat in CATS_ORDER:
    sub = keep[keep["_cat"] == cat]
    nb = len(sub)
    if nb == 0:
        continue
    cat_totals[cat] = nb
    pct = round(nb * 100 / n_total, 1) if n_total else 0
    n_props = sub["numero_siren"].nunique()
    cat_props[cat] = n_props
    # top owner
    top_siren = sub["numero_siren"].value_counts().idxmax()
    top_n = (sub["numero_siren"] == top_siren).sum()
    top_denom = sub[sub["numero_siren"] == top_siren]["denomination"].iloc[0]
    print(f"  {cat:25s} {nb:>8} {pct:>5.1f}% {n_props:>9} "
          f"{top_siren} {str(top_denom)[:25]} ({top_n})")

print("  " + "-" * 92)
print(f"  {'TOTAL PM (P+E)':25s} {n_total:>8} {'100.0%':>6}")

# PP : limitation
print()
print(f"  {'PERSONNES PHYSIQUES':25s} {'?':>8} {'?':>6} {'?':>9} "
      f"NON COMPTABLES dans cette base")
print(f"    -> majic_locaux2_2025.parquet contient UNIQUEMENT les PM")
print(f"    -> 0 row sans SIREN (verifie l. 'rows sans SIREN' ci-dessus)")
print(f"    -> Les lots PP (vendus a des particuliers) sont INVISIBLES")
print(f"       dans cette source. Pour les compter il faut :")
print(f"        - le fichier MAJIC LOCAUX 1 (28A) qui n'est pas dans data/")
print(f"        - OU croiser DVF + RNC live pour reperer les ventes PP")

# Estimation indirecte
nb_log_rnc = (co_match[0].get("nb_lots_habitation") if co_match else None) or 0
print(f"\n  Estimation indirecte du parc reel :")
print(f"    nb_lots_habitation RNC (declaratif) : {nb_log_rnc}")
print(f"    Total MAJIC PM P+E                   : {n_total}")
if n_total > nb_log_rnc:
    delta = n_total - nb_log_rnc
    print(f"    MAJIC PM > RNC habitation : MAJIC inclut +{delta} lots NON-habit")
    print(f"      = parking/cave/commerce (dependances du SDC)")
elif n_total < nb_log_rnc:
    delta = nb_log_rnc - n_total
    print(f"    MAJIC PM < RNC habitation : il MANQUE {delta} lots PM")
    print(f"      ces lots sont DETENUS PAR PP (invisibles dans MAJIC PM)")

# ============================================================
# [6] Sous-ventilation par adresse MAJIC (28 vs 30 etc.)
# ============================================================
print()
print("=" * 78)
print("[6] Sous-ventilation par adresse MAJIC (numero+voie)")
print("=" * 78)

addrs = keep["_addr"].value_counts().to_dict()
print(f"  {'Adresse':32s} {'tot':>4} {'GLH':>4} {'HLM_AUT':>7} {'PUB':>4} "
      f"{'SCI_pr':>7} {'SOC_pr':>7} {'AUT':>4}")
print("  " + "-" * 86)
for adr, n in sorted(addrs.items(), key=lambda x: -x[1]):
    sub = keep[keep["_addr"] == adr]
    cnt = {c: 0 for c in CATS_ORDER}
    for cat, n_cat in sub["_cat"].value_counts().items():
        cnt[cat] = int(n_cat)
    print(f"  {adr:32s} {n:>4} {cnt.get('GLH', 0):>4} "
          f"{cnt.get('HLM_AUTRE', 0):>7} {cnt.get('PUBLIC_NON_HLM', 0):>4} "
          f"{cnt.get('SCI_PRIVE', 0):>7} {cnt.get('SOCIETE_PRIVEE', 0):>7} "
          f"{cnt.get('AUTRE', 0) + cnt.get('AUTRE_NON_LUCRATIF', 0):>4}")
