#!/usr/bin/env python3
"""Diag approfondi 28/30 ETIENNE RICHERAND - faux positif social ?

CONTEXTE : 28 ETIENNE RICHERAND taggee social via batch MAJIC
(GRANDLYON HABITAT 306/311 lots = 98.4%). Suspicion terrain : la TOUR
28/30 est PRIVEE, les barres HLM sont d'autres batiments de la meme
residence.

Verifications :
  1. bgid + nb_log_bdnb + nb_lots de 28 et 30 ETIENNE RICHERAND
  2. immat RNC : meme copro ou distinctes ?
  3. MAJIC detail : les 306 lots GLH sont-ils tous sur la MEME parcelle
     que la tour, ou sur plusieurs parcelles agregees ?
  4. BAN api-adresse autoritaire pour 28 et 30
  5. Adresses voisines social : meme bgid que la tour ?

+ Extension : autres tags 'social' du secteur DL ou bgid n'est pas
celui du bailleur dominant (meme pattern d'agregation MAJIC trompeuse).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
BGID_PARC = ROOT / "data" / "_bgid_parcelle_dl.json"
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

CIBLES = ["28|RUE|ETIENNE RICHERAND", "30|RUE|ETIENNE RICHERAND",
          "26|RUE|ETIENNE RICHERAND", "32|RUE|ETIENNE RICHERAND",
          "33|RUE|ETIENNE RICHERAND", "29|RUE|ETIENNE RICHERAND",
          "31|RUE|ETIENNE RICHERAND"]


def http_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def ban_search(q, limit=2):
    url = ("https://api-adresse.data.gouv.fr/search/?limit="
           f"{limit}&q=" + urllib.parse.quote(q))
    try:
        return http_json(url).get("features", [])
    except Exception as e:
        return [{"_err": str(e)}]


def bdnb_bg_for_ban(cle_interop):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle_interop)}"
           "&select=batiment_groupe_id")
    try:
        return [r["batiment_groupe_id"] for r in http_json(url)]
    except Exception as e:
        return [f"ERR {e}"]


def bdnb_pivot(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,"
           "l_libelle_adr,nb_log,nb_log_rnc,annee_construction,"
           "numero_immat_principal,nb_adresse_valid_ban"
           f"&batiment_groupe_id=eq.{bg}")
    try:
        data = http_json(url, 20)
        return data[0] if data else None
    except Exception:
        return None


HLM_NEEDLES = (
    "HABITAT", " HLM", "HLM ", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH ", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "OPH", "DYNACITE", "3F RESIDENCES",
    "MGT", "ICF", "FONDATION ARALIS",
)


def is_hlm_name(denom):
    d = (denom or "").upper()
    return any(n in d for n in HLM_NEEDLES)


# ============================================================
print("=" * 78)
print("DIAG APPROFONDI : 28 / 30 ETIENNE RICHERAND")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}

kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}


def kv_type(cle):
    return ((assigns.get(cle) or {}).get("type")) or ""


bgid_parc = {}
if BGID_PARC.exists():
    bgid_parc = json.loads(BGID_PARC.read_text(encoding="utf-8"))

# Index light : bgid -> [cles]
cles_par_bgid = defaultdict(list)
for a in ad:
    bg = a.get("batiment_groupe_id") or ""
    if bg:
        cles_par_bgid[bg].append(a.get("cle") or "")

# ============================================================
# [1] Etat light
# ============================================================
print("\n[1] Etat light + KV pour les 7 cles ETIENNE RICHERAND voisines :")
print(f"  {'cle':30s} {'bgid':35s} {'bdnb':>5} {'lots':>5} {'vlog':>5} "
      f"{'immat':12s} {'tag':12s} {'nom RNC'}")
print("  " + "-" * 145)

bgs_seen = {}
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:30s} ABSENT light")
        continue
    bg = a.get("batiment_groupe_id") or ""
    bgs_seen[cle] = bg
    cp = co_by_cle.get(cle, {})
    immat = cp.get("numero_immatriculation") or a.get("numero_immatriculation") or "-"
    bdnb = a.get("nb_log_bdnb") or 0
    lots = cp.get("nb_lots_habitation") or "-"
    vlog = a.get("nb_ventes_logement") or 0
    nom = cp.get("nom_copropriete") or "-"
    tag = kv_type(cle)
    fa = "FA->" + (a.get("_fusion_cible") or "?") if a.get("_fusion_auto") else ""
    print(f"  {cle:30s} {bg:35s} {bdnb:>5} {str(lots):>5} {vlog:>5} "
          f"{immat:12s} {tag:12s} {nom[:35]} {fa}")

# ============================================================
# [2] Comparaison immats 28 vs 30
# ============================================================
print("\n[2] Comparaison immats RNC 28 vs 30 :")
i28 = (co_by_cle.get("28|RUE|ETIENNE RICHERAND") or {}).get("numero_immatriculation") \
      or (by_cle.get("28|RUE|ETIENNE RICHERAND") or {}).get("numero_immatriculation")
i30 = (co_by_cle.get("30|RUE|ETIENNE RICHERAND") or {}).get("numero_immatriculation") \
      or (by_cle.get("30|RUE|ETIENNE RICHERAND") or {}).get("numero_immatriculation")
print(f"  immat 28 ETIENNE RICHERAND : {i28}")
print(f"  immat 30 ETIENNE RICHERAND : {i30}")
print(f"  identiques (= meme copro)  : {i28 == i30 and i28 is not None}")

# ============================================================
# [3] BAN -> BDNB autoritaire
# ============================================================
print("\n[3] BAN api-adresse autoritaire (cle_interop -> bgid BDNB) :")
ban_bgs = {}
for q in ("28 rue etienne richerand 69003 Lyon",
          "30 rue etienne richerand 69003 Lyon",
          "26 rue etienne richerand 69003 Lyon",
          "32 rue etienne richerand 69003 Lyon"):
    feats = ban_search(q, limit=2)
    if not feats:
        print(f"  {q:40s} 0 feature")
        continue
    for f in feats[:2]:
        if "_err" in f:
            print(f"  {q:40s} ERR {f['_err']}")
            continue
        p = f.get("properties", {})
        bid = p.get("id") or ""
        name = p.get("name", "")
        typ = p.get("type", "")
        score = p.get("score", 0)
        bgs = bdnb_bg_for_ban(bid) if typ == "housenumber" else []
        time.sleep(0.05)
        ban_bgs[name] = bgs
        print(f"  {q:40s} BAN={bid} '{name}' type={typ} "
              f"score={round(score, 4)} -> {bgs}")
    time.sleep(0.05)

# ============================================================
# [4] BDNB pivots pour chaque bgid distinct
# ============================================================
print("\n[4] BDNB pivots pour chaque bgid present :")
bgs_uniq = set(bgs_seen.values()) | {b for bgs in ban_bgs.values() for b in bgs
                                      if isinstance(b, str) and b.startswith("bdnb-bg-")}
for bg in sorted(bgs_uniq):
    if not bg:
        continue
    p = bdnb_pivot(bg)
    time.sleep(0.05)
    if not p:
        print(f"  {bg}: ABSENT BDNB")
        continue
    print(f"\n  {bg}")
    print(f"    lib='{p.get('libelle_adr_principale_ban','')}'")
    print(f"    nb_log={p.get('nb_log')} nb_log_rnc={p.get('nb_log_rnc')} "
          f"annee={p.get('annee_construction')} immat={p.get('numero_immat_principal') or '-'}")
    print(f"    nb_adresses_BAN={p.get('nb_adresse_valid_ban')}")
    for x in p.get("l_libelle_adr") or []:
        print(f"      . {x}")

# ============================================================
# [5] Adresses voisines social partageant le bgid de la tour
# ============================================================
print("\n[5] Adresses light social sur la rue ETIENNE RICHERAND :")
bg_28 = bgs_seen.get("28|RUE|ETIENNE RICHERAND") or ""
print(f"  bgid actuel de 28 (light) : {bg_28}")
print(f"  Adresses partageant ce bgid :")
for c in cles_par_bgid.get(bg_28, []):
    a = by_cle[c]
    cp = co_by_cle.get(c, {})
    print(f"    {c:30s} tag={kv_type(c):12s} immat={cp.get('numero_immatriculation') or a.get('numero_immatriculation') or '-':12s} "
          f"bdnb={a.get('nb_log_bdnb')} FA={a.get('_fusion_auto')}")

print(f"\n  Toutes les adresses tag social sur la rue ETIENNE RICHERAND :")
for a in ad:
    cle = a.get("cle") or ""
    if "ETIENNE RICHERAND" not in cle:
        continue
    if kv_type(cle) != "social":
        continue
    bg = a.get("batiment_groupe_id") or ""
    cp = co_by_cle.get(cle, {})
    print(f"    {cle:30s} bgid=...{bg[-9:]} immat={cp.get('numero_immatriculation') or '-':12s} "
          f"bdnb={a.get('nb_log_bdnb')} lots={cp.get('nb_lots_habitation') or '-'} "
          f"nom='{(cp.get('nom_copropriete') or '')[:30]}'")

# ============================================================
# [6] MAJIC detail : les 306 lots GLH sur quelle parcelle ?
# ============================================================
print("\n[6] MAJIC detail : repartition des proprietaires HLM par parcelle :")
# Parcelles connues du bgid 28 ETIENNE RICHERAND
parcs_28 = bgid_parc.get(bg_28, [])
print(f"  Parcelles bgid 28 (cache) : {parcs_28}")
# Et autres parcelles ETIENNE RICHERAND voisines
parcs_voisines = set()
for cle in CIBLES:
    bg = bgs_seen.get(cle) or ""
    for p in bgid_parc.get(bg, []):
        parcs_voisines.add(p)
print(f"  Parcelles toutes voisines : {sorted(parcs_voisines)}")

# Si parcs_28 vide, fallback enrich
if not parcs_28:
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    e28 = next((r for r in enrich["results"] if r["cle"] == "28|RUE|ETIENNE RICHERAND"), None)
    if e28:
        parcs_28 = e28.get("parcelles_bdnb") or []
        print(f"  Parcelles bgid 28 (enrich) : {parcs_28}")

all_parcs_to_check = parcs_voisines | set(parcs_28)
if all_parcs_to_check:
    print(f"\n  Query MAJIC sur {len(all_parcs_to_check)} parcelles :")
    sections = sorted({p[8:10] for p in all_parcs_to_check})
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", "69"), ("code_commune", "=", "383"),
        ("section", "in", sections),
    ])
    df = tbl.to_pandas()
    df["_parc"] = ("69383000" + df["section"].astype(str)
                   + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
    df = df[df["_parc"].isin(all_parcs_to_check)].copy()
    # P et E uniquement (exclu syndic/mandataire)
    df = df[df["code_droit"].isin(["P", "E"])].copy()
    print(f"  Rows P+E : {len(df)}")
    df["adresse_majic"] = (df["numero_voirie"].fillna(0).astype(int).astype(str)
                            + df["indice_de_repetition"].fillna("").astype(str)
                            + " " + df["nature_voie"].fillna("")
                            + " " + df["nom_voie"].fillna(""))
    df["adresse_majic"] = df["adresse_majic"].str.strip()
    # Group by parcelle + SIREN
    grp = df.groupby(["_parc", "numero_siren", "code_droit",
                      "denomination", "groupe_personne_libelle"],
                     dropna=False).size().reset_index(name="nb_lots")
    grp = grp.sort_values(["_parc", "nb_lots"], ascending=[True, False])

    for parc in sorted(all_parcs_to_check):
        sub = grp[grp["_parc"] == parc]
        if sub.empty:
            print(f"\n  parc {parc} : 0 lot P+E")
            continue
        print(f"\n  parc {parc} :")
        # Quelles adresses MAJIC sur cette parcelle ?
        df_p = df[df["_parc"] == parc]
        addrs = df_p["adresse_majic"].value_counts().to_dict()
        for adr, n in addrs.items():
            print(f"    adresse MAJIC : {n:4d} lots  '{adr}'")
        print(f"    TOP proprietaires P+E :")
        for _, row in sub.head(8).iterrows():
            sir = str(row["numero_siren"] or "-")
            dn = str(row["denomination"] or "-")[:30]
            dr = str(row["code_droit"])
            gp = str(row["groupe_personne_libelle"] or "-")[:30]
            hlm = "HLM" if is_hlm_name(dn) else ""
            print(f"      {sir:10s} {dr:2s} {row['nb_lots']:>4} "
                  f"{dn:30s} {gp:30s} {hlm}")

# ============================================================
# [7] Extension : autres tags 'social' suspects
# ============================================================
print()
print("=" * 78)
print("[7] EXTENSION : autres tags 'social' avec pattern MAJIC trompeuse")
print("=" * 78)

# Hypothese : pour chaque cle taggee social, comparer :
# - L'adresse MAJIC qui contient le bailleur HLM dominant
# - L'adresse light (la cle)
# Si l'adresse MAJIC HLM != adresse light cle, c'est suspect : MAJIC agrege
# sous le libelle d'adresse de la cle des lots qui sont en realite sur
# une adresse voisine (parcelle commune mais bati distinct).

enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

# Verifier les 209 cles social
suspects = []
for cle, v in assigns.items():
    if (v or {}).get("type") != "social":
        continue
    a = by_cle.get(cle)
    if not a:
        continue
    e = enrich_by_cle.get(cle)
    if not e:
        continue
    # Pour chaque cle, voir si la majic_adresses contient une adresse
    # differente de la cle (= MAJIC pointe vers un voisin)
    majic_addrs = e.get("majic_adresses") or []
    if not majic_addrs:
        continue
    # Extraire le num+nom de la cle light
    parts = cle.split("|")
    if len(parts) != 3:
        continue
    num_cle = parts[0].strip().upper()
    voie_cle = parts[2].strip().upper()
    # Verifier si la PLUS IMPORTANTE adresse MAJIC est DIFFERENTE de la cle
    top_majic = majic_addrs[0]
    top_adr_raw = (top_majic.get("adresse") or "").strip().upper()
    # Normaliser : retirer les espaces multiples
    top_adr = " ".join(top_adr_raw.split())
    # Verifier si top_adr contient num_cle et voie_cle (partiel)
    match_num = num_cle in top_adr.split() if num_cle else False
    match_voie = any(w in top_adr for w in voie_cle.split() if len(w) > 2)
    if not (match_num and match_voie):
        # Top MAJIC est sur autre adresse -> suspect
        suspects.append({
            "cle": cle, "top_majic": top_adr,
            "top_lots": top_majic.get("lots"),
            "all_majic": [(m.get("adresse"), m.get("lots"))
                           for m in majic_addrs[:3]],
            "nb_log_bdnb": a.get("nb_log_bdnb"),
            "immat": (co_by_cle.get(cle) or {}).get("numero_immatriculation") \
                     or a.get("numero_immatriculation"),
            "bgid": a.get("batiment_groupe_id"),
        })

# Trier par nb_log DESC
suspects.sort(key=lambda r: -(r["nb_log_bdnb"] or 0))
print(f"\n  {len(suspects)} cles social ou l'adresse MAJIC top != adresse cle "
      f"(suspect agregation trompeuse) :\n")
if suspects:
    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'immat':12s} {'top MAJIC adresse + lots'}")
    print("  " + "-" * 124)
    for i, r in enumerate(suspects, 1):
        all_ma = "; ".join(f"{lots}@{adr[:25]}"
                           for adr, lots in r["all_majic"][:3])
        print(f"  {i:>3} {r['cle']:32s} {r['nb_log_bdnb'] or 0:>6} "
              f"{r['immat'] or '-':12s} {all_ma}")
else:
    print("  Aucun cas suspect detecte par cette heuristique.")
