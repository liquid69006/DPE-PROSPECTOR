#!/usr/bin/env python3
"""Indicateur 'lots prives' par adresse exacte (lecture seule).

Objectif : reveler les ensembles HLM en decollectivisation (GLH vend
des lots aux locataires) en comptant pour CHAQUE adresse light (pas
la parcelle agregee) :
  - nb_lots_total : lots P+E habitation MAJIC sur l adresse exacte
  - nb_lots_social : prio HLM/social (denomination + groupe HLM)
  - nb_lots_prive  : nb_lots_total - nb_lots_social
  - pct_prive

ETAPE 1 : tester 28/30 ETIENNE RICHERAND + barres TERNOIS 7-17
          (verification : barres = 100% social attendu)
ETAPE 2 : etendre aux 209 cles taggees 'social', tri par
          nb_lots_prive DESC.
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
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else ""


def parse_cle(cle):
    """ '28|RUE|ETIENNE RICHERAND' -> ('28', '', toks('ETIENNE RICHERAND')) """
    p = cle.split("|")
    if len(p) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", p[0].upper())
    if not m:
        return None
    return m.group(1), m.group(2), toks(p[2])


HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "OPH ", " OPH",
    "DYNACITE", "3F RESIDENCES", "MGT", "ICF", "FONDATION ARALIS",
    "OPH DE LA METROPOLE", "OFFICE PUBLIC", "ETABLISSEMENT PUBLIC",
)
HLM_SIRENS = {
    "399898345",  # GRANDLYON HABITAT
    "813755949",  # OPH METROPOLE LYON
    "778596510",  # BATIGERE RHONE ALPES
    "960506152",  # ALLIADE HABITAT
    "552046484",  # CDC HABITAT
    "470801168",  # CDC HABITAT (var)
    "398115808",  # IMMOBILIERE RHONE ALPES
    "779537125",  # ALPES ISERE HABITAT
    "339804858",  # FONCIERE D'HABITAT ET HUM
    "200046977",  # METROPOLE DE LYON (fonciere)
}


def is_hlm_owner(row):
    """Detecte si la ligne MAJIC correspond a un proprietaire HLM/social."""
    siren = str(row.get("numero_siren") or "")
    if siren in HLM_SIRENS:
        return True
    dn = (str(row.get("denomination") or "")).upper()
    gp = (str(row.get("groupe_personne_libelle") or "")).upper()
    fj = (str(row.get("forme_juridique_libelle") or "")).upper()
    for n in HLM_NEEDLES:
        if n in dn or n in gp or n in fj:
            return True
    return False


def normalize_majic_num(row):
    """numero_voirie + indice_de_repetition (B/T/Q/A...)"""
    nv = row.get("numero_voirie")
    nv_str = ""
    if nv is not None:
        try:
            nv_str = str(int(nv))
        except (TypeError, ValueError):
            nv_str = str(nv).strip()
    rep = (row.get("indice_de_repetition") or "").strip().upper()
    return nv_str + rep


def normalize_majic_voie_toks(row):
    """toks(nom_voie) - on retire nature_voie pour rester aligne avec
    la cle light qui separe TYPE et VOIE."""
    nm = (row.get("nom_voie") or "")
    return toks(nm)


# ============================================================
print("=" * 78)
print("DIAG LOTS PRIVES PAR ADRESSE EXACTE  (lecture seule)")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}


def kv_type(cle):
    return ((assigns.get(cle) or {}).get("type")) or ""


# ============================================================
# Construire l ensemble des parcelles a interroger (pour les cles
# d interet : etape 1 + etape 2)
# ============================================================
TEST_CLES = [
    "28|RUE|ETIENNE RICHERAND",
    "30|RUE|ETIENNE RICHERAND",
    "7|RUE|TERNOIS",
    "9|RUE|TERNOIS",
    "11|RUE|TERNOIS",
    "13|RUE|TERNOIS",
    "15|RUE|TERNOIS",
    "17|RUE|TERNOIS",
]

# Toutes les cles social KV
social_cles = [c for c, v in assigns.items()
               if (v or {}).get("type") == "social" and c in by_cle]

# Union parcelles a query
all_parcels = set()
all_targets = set(TEST_CLES) | set(social_cles)
for cle in all_targets:
    e = enrich_by_cle.get(cle)
    if not e:
        continue
    for p in (e.get("parcelles_bdnb") or []):
        all_parcels.add(p)
print(f"\n  Total cles a analyser : {len(all_targets)} (test={len(TEST_CLES)}, "
      f"social KV={len(social_cles)})")
print(f"  Parcelles uniques a interroger MAJIC : {len(all_parcels)}")

# Query MAJIC une fois
sections = sorted({p[8:10] for p in all_parcels})
print(f"  Sections : {len(sections)} ({sections[:8]}{'...' if len(sections) > 8 else ''})")
print(f"  Query MAJIC...")
tbl = pq.read_table(MAJIC, filters=[
    ("departement", "=", "69"), ("code_commune", "=", "383"),
    ("section", "in", sections),
])
df = tbl.to_pandas()
df["_parc"] = ("69383000" + df["section"].astype(str)
               + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
df = df[df["_parc"].isin(all_parcels)].copy()
# Exclure mandataires/syndics : P+E uniquement
df = df[df["code_droit"].isin(["P", "E"])].copy()
print(f"  Rows P+E utiles : {len(df)}")

# Build index : (adresse_norm_key, parcelle) -> list of rows
# adresse_norm_key = (num_with_suffix, voie_toks)
df["_num_norm"] = df.apply(normalize_majic_num, axis=1)
df["_voie_toks"] = df.apply(normalize_majic_voie_toks, axis=1)
df["_hlm"] = df.apply(is_hlm_owner, axis=1)


def compute_for_cle(cle):
    """Pour une cle light, retourne dict avec nb_lots_total/social/prive
    + breakdown par SIREN/owner."""
    e = enrich_by_cle.get(cle)
    parcels = (e.get("parcelles_bdnb") if e else None) or []
    parsed = parse_cle(cle)
    if not parsed or not parcels:
        return None
    num_base, suffix, voie_toks = parsed
    num_with_suffix = num_base + suffix  # ex '28', '11B', '20T'

    # Filter df : meme parcelle + num + voie
    sub = df[
        (df["_parc"].isin(parcels))
        & (df["_num_norm"] == num_with_suffix)
        & (df["_voie_toks"] == voie_toks)
    ]
    n_tot = len(sub)
    n_social = int(sub["_hlm"].sum())
    n_prive = n_tot - n_social
    # Breakdown par SIREN
    if n_tot > 0:
        sub_g = (sub.groupby(["numero_siren", "denomination",
                              "code_droit", "_hlm"], dropna=False)
                 .size().reset_index(name="lots")
                 .sort_values("lots", ascending=False))
        sirens_detail = sub_g.head(8).to_dict("records")
    else:
        sirens_detail = []
    return {
        "cle": cle, "parcels": parcels,
        "num": num_with_suffix, "voie_toks": voie_toks,
        "n_lots_total": n_tot,
        "n_lots_social": n_social,
        "n_lots_prive": n_prive,
        "pct_prive": round(n_prive * 100 / n_tot, 1) if n_tot else 0,
        "sirens_detail": sirens_detail,
    }


# ============================================================
# ETAPE 1 - 28/30 ETIENNE RICHERAND + barres TERNOIS
# ============================================================
print()
print("=" * 78)
print("ETAPE 1 - 28/30 ETIENNE RICHERAND + barres 7-17 TERNOIS")
print("=" * 78)

for cle in TEST_CLES:
    r = compute_for_cle(cle)
    print(f"\n  --- {cle} ---")
    if r is None:
        print(f"      ABSENT light ou pas de parcelle")
        continue
    print(f"      parcelles : {r['parcels']}")
    print(f"      num={r['num']}  voie_toks={r['voie_toks']}")
    print(f"      nb_lots_total  : {r['n_lots_total']}")
    print(f"      nb_lots_social : {r['n_lots_social']}")
    print(f"      nb_lots_prive  : {r['n_lots_prive']}")
    print(f"      pct_prive      : {r['pct_prive']}%")
    if r["sirens_detail"]:
        print(f"      Top SIRENs sur l'adresse exacte :")
        for s in r["sirens_detail"]:
            tag = "HLM" if s["_hlm"] else "PRIVE"
            dn = str(s.get("denomination") or "-")[:32]
            print(f"        {str(s.get('numero_siren') or '-'):10s} "
                  f"{str(s['code_droit']):2s} {s['lots']:>4} {tag:5s} {dn}")

# ============================================================
# ETAPE 2 - 209 cles social, tri nb_lots_prive DESC
# ============================================================
print()
print("=" * 78)
print(f"ETAPE 2 - Toutes cles social KV ({len(social_cles)} cles) ; tri "
      f"nb_lots_prive DESC")
print("=" * 78)

results = []
for cle in social_cles:
    r = compute_for_cle(cle)
    if r is None:
        results.append({"cle": cle, "n_lots_total": 0,
                        "n_lots_social": 0, "n_lots_prive": 0,
                        "pct_prive": 0, "sirens_detail": [],
                        "absent": True})
        continue
    r["absent"] = False
    results.append(r)

results.sort(key=lambda r: (-r["n_lots_prive"], -r["n_lots_total"]))

decollect = [r for r in results if r["n_lots_prive"] > 0]
purs = [r for r in results if r["n_lots_prive"] == 0
        and r["n_lots_total"] > 0]
absents = [r for r in results if r["n_lots_total"] == 0]

print(f"\n  social avec lots prives > 0 (decollectivisation) : {len(decollect)}")
print(f"  social purs (0 lots prives sur adresse exacte)    : {len(purs)}")
print(f"  social sans donnees MAJIC adresse exacte          : {len(absents)}")

# Tableau decollectivisation
print()
print(f"  {'#':>3} {'cle':32s} {'tag':10s} {'tot':>5} {'soc':>5} "
      f"{'priv':>5} {'%priv':>6} {'top private SIREN'}")
print("  " + "-" * 130)
for i, r in enumerate(decollect, 1):
    if r.get("absent"):
        continue
    # Identifier top SIREN prive
    top_priv = next((s for s in r["sirens_detail"] if not s["_hlm"]), None)
    top_str = ""
    if top_priv:
        dn = str(top_priv.get("denomination") or "")[:35]
        top_str = f"{top_priv['lots']:>3} @ {dn}"
    bdnb = (by_cle.get(r["cle"], {}) or {}).get("nb_log_bdnb") or 0
    print(f"  {i:>3} {r['cle']:32s} {'social':10s} {r['n_lots_total']:>5} "
          f"{r['n_lots_social']:>5} {r['n_lots_prive']:>5} "
          f"{r['pct_prive']:>5.1f}% {top_str}")

# Resume
total_prive_all = sum(r["n_lots_prive"] for r in decollect)
print()
print("=" * 78)
print("RECAP")
print("=" * 78)
print(f"  social cles totales         : {len(social_cles)}")
print(f"  decollect (>0 lots prives)  : {len(decollect)}")
print(f"  totaux lots prives detectes : {total_prive_all}")
print(f"  social purs (0 priv)        : {len(purs)}")
print(f"  social sans MAJIC adresse   : {len(absents)}")

if absents:
    print(f"\n  Sample des social sans MAJIC adresse exacte (top 10) :")
    for r in absents[:10]:
        print(f"    {r['cle']}")
