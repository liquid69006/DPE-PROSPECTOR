#!/usr/bin/env python3
"""Fix RE-POINT 132 RUE BARABAN + analyse MAJIC parcelle DS0046.

Pattern ECLATEMENT faux-matching make_light bgid identique a 11 BARA :
- BAN api-adresse reconnait distinctement 132 + 133 BARABAN (housenumber
  score 0.9761 chacun)
- BDNB autorite : 132 -> bgid LE6X-UMGS-VDM1 (parcelle DS0046, bati 1780)
  vs 133 -> bgid W5E1-2VY3-48EC (parcelles DP0060+DP0101, bati 1890)
- Sections cadastrales differentes (DS vs DP), parcelles disjointes
- make_light a snappe 132 sur bgid voisin 2VY3-48EC (133 BARABAN)

ACTIONS :
  1. RE-POINT 132|RUE|BARABAN
       bgid           : bdnb-bg-W5E1-2VY3-48EC -> bdnb-bg-LE6X-UMGS-VDM1
       annee_construction : 1890 -> 1780
       nb_log_bdnb   : 16 -> 16 (identique entre 2 batiments, coincidence)
       _bdnb_match   = 'correctif_132baraban_re_point'
       (NO FA : laissee comme ancre isolee, pas de fusion vers 253 PAUL
        BERT sur consigne user)

  2. Analyse MAJIC parcelle 69383000DS0046 (lecture seule, print)
       -> tous SIREN + % + nb_lots + denomination
       -> code_droit_libelle (Proprietaire vs Emphyteote)
       -> classification (HLM / SCI / prive / PP)
       -> social_pct total
       -> reco tag KV
"""
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre132baraban.bak"
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

NEW_BGID = "bdnb-bg-LE6X-UMGS-VDM1"
OLD_BGID = "bdnb-bg-W5E1-2VY3-48EC"
PARC_132 = "69383000DS0046"


# ============================================================
# PARTIE 1 : RE-POINT 132 BARABAN
# ============================================================
def apply_repoint():
    print("=" * 76)
    print("PARTIE 1 : RE-POINT 132|RUE|BARABAN")
    print("=" * 76)

    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_132_baraban"):
        sys.exit("  [abort] _correctif_132_baraban deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a132 = by_cle.get("132|RUE|BARABAN")
    if not a132:
        sys.exit("  [abort] 132|RUE|BARABAN absent du light.")
    cur_bgid = a132.get("batiment_groupe_id") or ""
    if cur_bgid != OLD_BGID:
        sys.exit(f"  [abort] bgid actuel inattendu : {cur_bgid} (attendu {OLD_BGID})")

    old_annee = a132.get("annee_construction")
    a132["batiment_groupe_id"] = NEW_BGID
    a132["annee_construction"] = 1780
    a132["_bdnb_match"] = "correctif_132baraban_re_point"
    print(f"  [RE-POINT] 132|RUE|BARABAN")
    print(f"             bgid {OLD_BGID[-9:]} -> {NEW_BGID[-9:]}")
    print(f"             annee_construction {old_annee} -> 1780")
    print(f"             _bdnb_match=correctif_132baraban_re_point")
    print(f"             (ancre isolee, pas de FA vers 253 PAUL BERT)")

    md["_correctif_132_baraban"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "ECLATEMENT faux-matching make_light bgid (pattern 11 BARA)",
        "autorite": ("BAN api-adresse 69383_0645_00132 housenumber score 0.9761 "
                     "-> BDNB rel_batiment_groupe_adresse LE6X-UMGS-VDM1 "
                     "(parcelle DS0046 distincte de 133 BARABAN parcelles "
                     "DP0060+DP0101)"),
        "ops": "RE-POINT bgid 2VY3-48EC -> LE6X-UMGS-VDM1 + annee 1890 -> 1780",
        "old_bgid": OLD_BGID,
        "new_bgid": NEW_BGID,
        "parcelle": PARC_132,
        "note": ("ancre isolee, pas de fusion vers 253 PAUL BERT (autre BAN "
                 "officielle du bati selon BDNB l_libelle_adr) sur consigne user"),
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"  [OK] light ecrit.")


# ============================================================
# PARTIE 2 : Analyse MAJIC parcelle DS0046
# ============================================================
def analyse_majic():
    print()
    print("=" * 76)
    print(f"PARTIE 2 : MAJIC parcelle {PARC_132} (132 BARABAN)")
    print("=" * 76)

    sec = PARC_132[8:10]
    plan = int(PARC_132[10:])
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", "69"), ("code_commune", "=", "383"),
        ("section", "=", sec), ("numero_parcelle", "=", plan),
    ])
    df = tbl.to_pandas()
    n_tot = len(df)
    print(f"  Total lots MAJIC : {n_tot}")

    # Adresses MAJIC
    if not df.empty:
        df["addr"] = (df["numero_voirie"].fillna(0).astype(int).astype(str)
                      + df["indice_de_repetition"].fillna("").astype(str)
                      + " " + df["nature_voie"].fillna("")
                      + " " + df["nom_voie"].fillna(""))
        addrs = df["addr"].value_counts().to_dict()
        print(f"  Adresses MAJIC sur la parcelle :")
        for adr, n in addrs.items():
            print(f"    {n:3d}  '{adr.strip()}'")

    # Decoupage par (SIREN, code_droit)
    print()
    print("  Detail par SIREN + code_droit :")
    grp = (df.groupby(["numero_siren", "code_droit", "code_droit_libelle",
                       "groupe_personne_libelle", "denomination",
                       "forme_juridique_libelle"], dropna=False)
             .size().reset_index(name="nb_lots")
             .sort_values("nb_lots", ascending=False))
    print(f"  {'SIREN':12s} {'droit':12s} {'lots':5s} {'pct':6s} {'groupe':45s} "
          f"{'denomination':45s} {'forme':30s}")
    print("  " + "-" * 156)
    for _, row in grp.iterrows():
        siren = str(row["numero_siren"] or "-")
        dr = str(row["code_droit_libelle"] or "-")[:12]
        nb = int(row["nb_lots"])
        pct = round(nb * 100 / n_tot, 1) if n_tot else 0
        gp = str(row["groupe_personne_libelle"] or "-")[:45]
        dn = str(row["denomination"] or "-")[:45]
        fj = str(row["forme_juridique_libelle"] or "-")[:30]
        print(f"  {siren:12s} {dr:12s} {nb:5d} {pct:5.1f}% {gp:45s} {dn:45s} {fj:30s}")

    # Classification per SIREN
    print()
    print("  Classification par SIREN :")

    def classify(row):
        gp = (row["groupe_personne_libelle"] or "").lower()
        dn = (row["denomination"] or "").lower()
        fj = (row["forme_juridique_libelle"] or "").lower()
        if "office hlm" in gp or "hlm" in dn or "habitat" in dn:
            return "HLM/SOCIAL"
        if "etablissements publics" in gp or "collectivite" in fj or "publique" in fj:
            return "PUBLIC/COLLECTIVITE"
        if "sci" in dn[:6] or "sci " in dn or "societe civile immobiliere" in fj.lower():
            return "SCI"
        if "personne physique" in gp:
            return "PP_PRIVE"
        if "societe" in gp or "sas" in fj or "sarl" in fj or "sa " in fj:
            return "SOCIETE_PRIVEE"
        return "AUTRE"

    siren_class = {}
    siren_lots = defaultdict(int)
    for _, row in grp.iterrows():
        k = (str(row["numero_siren"] or "-"), str(row["code_droit_libelle"] or "-"))
        siren_class[k] = classify(row)
        siren_lots[k] += int(row["nb_lots"])

    # Total social_pct : on retient code_droit prioritaire pour gestion logement
    # = Emphyteote (gestionnaire bailleur) si present, sinon Proprietaire.
    # Pour social_pct, on compte chaque SIREN une fois (pas de double :
    # 21 P MetroLyon + 21 E GrandLyon Habitat -> on prend les 21 lots HLM via E,
    # les 21 lots P du proprietaire foncier metro sont les MEMES locaux).
    lots_par_local = n_tot
    # Identifier les SIREN par categorie d'apres son code_droit dominant
    siren_groups = defaultdict(lambda: defaultdict(int))
    for (siren, droit), nb in siren_lots.items():
        cl = siren_class[(siren, droit)]
        siren_groups[siren][cl] = max(siren_groups[siren][cl], nb)
        siren_groups[siren]["__droit__"] = droit

    # Heuristique : si bail emphyteotique present sur la parcelle (E),
    # le gestionnaire des logements est l'emphyteote (HLM ici).
    droits_set = set(d for (_, d) in siren_lots.keys())
    if "Emphytéote" in droits_set:
        # Pour social_pct, on prend les lots geres par emphyteotes
        social_lots = sum(nb for (siren, droit), nb in siren_lots.items()
                          if droit == "Emphytéote"
                          and siren_class[(siren, droit)] == "HLM/SOCIAL")
        gest_total = sum(nb for (siren, droit), nb in siren_lots.items()
                         if droit == "Emphytéote")
    else:
        social_lots = sum(nb for (siren, droit), nb in siren_lots.items()
                          if siren_class[(siren, droit)] == "HLM/SOCIAL")
        gest_total = sum(nb for (siren, droit), nb in siren_lots.items()
                         if droit == "Propriétaire")

    print(f"  Droits presents : {sorted(droits_set)}")
    for (siren, droit), nb in sorted(siren_lots.items(), key=lambda x: -x[1]):
        cl = siren_class[(siren, droit)]
        pct = round(nb * 100 / n_tot, 1) if n_tot else 0
        print(f"    SIREN={siren} droit={droit:12s} -> {cl:20s} {nb} lots ({pct}%)")

    social_pct = round(social_lots * 100 / gest_total, 1) if gest_total else 0
    print()
    print(f"  social_pct (gestion logement) = {social_lots}/{gest_total} = {social_pct}%")

    # Reco tag KV
    print()
    print("  =" * 38)
    print("  RECOMMANDATION TAG KV :")
    print("  =" * 38)
    if social_pct >= 90:
        print(f"    -> social (gestion HLM emphyteote {social_pct}% des lots)")
    elif social_pct >= 50:
        print(f"    -> social (HLM majoritaire {social_pct}%, gestion mixte)")
    elif social_pct > 0:
        print(f"    -> mixte (HLM minoritaire {social_pct}%)")
    else:
        print(f"    -> autre (pas de HLM)")

    print()
    if "Emphytéote" in droits_set and social_pct >= 90:
        print("  Note : configuration BAIL EMPHYTEOTIQUE SOCIAL classique :")
        print("    - Proprietaire foncier (terrain) = collectivite publique")
        print("    - Emphyteote (gestion logements) = office HLM")
        print("    - Tous les logements sont sous gestion sociale.")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    apply_repoint()
    analyse_majic()
    print()
    print("=" * 76)
    print("BATCH 132 BARABAN COMPLET.")
    print("Reste : bump CACHE_VERSION + commit + push (etapes externes).")
    print("=" * 76)
