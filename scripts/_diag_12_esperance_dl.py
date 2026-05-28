#!/usr/bin/env python3
"""Diag approfondi 12 ESPERANCE (Cambronne potentiel - lecture seule).

CONTEXTE : 12 ESPERANCE (25 log, bgid 4BJ1-EQDH-V7QL) a 0 vente,
voisins 11 (5 vlog) et 14 (3 vlog) vendent. Pre-classe par diag DVF
orphans comme "bgid partage mais FA absente". autoMerged[12] = None.

Trancher entre :
  - vrai Cambronne -> FUSION/RE-POINT si meme immat OU cross-RNC OU
    parcelle strictement commune
  - faux positif -> DISTINCT si immat differents + pas de cross-RNC

Sources (lecture seule) :
  - light JSON
  - cache _bgid_parcelle_dl.json
  - BDNB live (batiment_groupe_complet + rel_batiment_groupe_rnc +
    rel_batiment_groupe_adresse)
  - BAN api-adresse (autorite address -> bgid)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BGID_PARC = ROOT / "data" / "_bgid_parcelle_dl.json"

CIBLES = ["12|RUE|ESPERANCE", "11|RUE|ESPERANCE", "14|RUE|ESPERANCE",
          "13|RUE|ESPERANCE", "10|RUE|ESPERANCE"]


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


def bdnb_parcelles(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    try:
        return [p["parcelle_id"] for p in http_json(url)]
    except Exception as e:
        return []


def bdnb_pivot(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,"
           "l_libelle_adr,nb_log,nb_log_rnc,annee_construction,"
           "usage_principal_bdnb_open,numero_immat_principal,"
           "nb_adresse_valid_ban"
           f"&batiment_groupe_id=eq.{bg}")
    try:
        data = http_json(url, 20)
        return data[0] if data else None
    except Exception as e:
        return {"_err": str(e)}


def bdnb_rnc_pour_bg(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc"
           f"?batiment_groupe_id=eq.{bg}&select=numero_immatriculation")
    try:
        return [r.get("numero_immatriculation")
                for r in http_json(url)
                if r.get("numero_immatriculation")]
    except Exception:
        return []


# ---------- 1. State light ----------
print("=" * 78)
print("DIAG APPROFONDI : 12 RUE ESPERANCE  (lecture seule)")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}

bgid_parc_cache = {}
if BGID_PARC.exists():
    bgid_parc_cache = json.loads(BGID_PARC.read_text(encoding="utf-8"))

print("\n[1] Etat light :")
print(f"  {'cle':24s} {'bgid':35s} {'bdnb':>5} {'lots':>5} {'vlog':>5} "
      f"{'immat':12s} {'syndic / nom'}")
print("  " + "-" * 130)

bgs_seen = {}
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:24s} ABSENT light")
        continue
    bg = a.get("batiment_groupe_id") or ""
    bgs_seen[cle] = bg
    cp = co_by_cle.get(cle, {})
    immat = cp.get("numero_immatriculation") or a.get("numero_immatriculation") or "-"
    bdnb = a.get("nb_log_bdnb") or 0
    lots = cp.get("nb_lots_habitation") or "-"
    vlog = a.get("nb_ventes_logement") or 0
    nom = cp.get("nom_copropriete") or "-"
    syn = (cp.get("syndic") or a.get("syndic") or "-")[:20]
    print(f"  {cle:24s} {bg:35s} {bdnb:>5} {str(lots):>5} {vlog:>5} "
          f"{immat:12s} {syn} / {nom[:30]}")

# Verifier qui partage le bgid de 12
bg_12 = bgs_seen.get("12|RUE|ESPERANCE")
print(f"\n  bgid de 12 ESPERANCE = {bg_12}")
print(f"  Adresses light partageant ce bgid :")
for a in ad:
    if (a.get("batiment_groupe_id") or "") == bg_12:
        cp = co_by_cle.get(a.get("cle"), {})
        print(f"    {a.get('cle'):26s} bdnb={a.get('nb_log_bdnb')} "
              f"vlog={a.get('nb_ventes_logement') or 0}  "
              f"immat={cp.get('numero_immatriculation') or a.get('numero_immatriculation') or '-'}  "
              f"FA={a.get('_fusion_auto')} cible={a.get('_fusion_cible')}")

# ---------- 2. Parcelles BDNB ----------
print("\n[2] Parcelles BDNB par cle (cache local) :")
parcs_par_cle = {}
for cle, bg in bgs_seen.items():
    if not bg:
        continue
    parcs = bgid_parc_cache.get(bg) or []
    if not parcs:
        # Refetch live si cache vide
        parcs = bdnb_parcelles(bg)
        time.sleep(0.05)
    parcs_par_cle[cle] = parcs
    print(f"  {cle:24s} bg=...{bg[-9:]:9s} parcelles={parcs}")

# Verif intersection parcelles 12 vs 11/14
print(f"\n[2b] Intersection parcelles :")
parcs_12 = set(parcs_par_cle.get("12|RUE|ESPERANCE", []))
for other in ("11|RUE|ESPERANCE", "14|RUE|ESPERANCE",
              "13|RUE|ESPERANCE", "10|RUE|ESPERANCE"):
    po = set(parcs_par_cle.get(other, []))
    inter = parcs_12 & po
    print(f"  12 vs {other}  : commune={sorted(inter) or '(aucune)'}")

# ---------- 3. BAN -> BDNB autoritaire ----------
print("\n[3] BAN api-adresse autoritaire (cle_interop -> bgid BDNB) :")
ban_bgs = {}
for q in ("12 rue de l esperance 69003 Lyon",
          "11 rue de l esperance 69003 Lyon",
          "14 rue de l esperance 69003 Lyon",
          "13 rue de l esperance 69003 Lyon",
          "10 rue de l esperance 69003 Lyon"):
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
        ban_bgs.setdefault(name, []).extend(bgs)
        print(f"  {q:40s} BAN={bid} '{name}' type={typ} score={round(score, 4)} -> {bgs}")
    time.sleep(0.05)

# ---------- 4. BDNB pivot + rel_rnc autoritaire ----------
print("\n[4] BDNB pivot batiment_groupe_complet + rel_rnc :")
for cle, bg in bgs_seen.items():
    if not bg:
        continue
    piv = bdnb_pivot(bg)
    time.sleep(0.05)
    rnc_list = bdnb_rnc_pour_bg(bg)
    time.sleep(0.05)
    print(f"\n  {cle:24s} bg=...{bg[-9:]} :")
    if piv and not piv.get("_err"):
        print(f"    lib       = '{piv.get('libelle_adr_principale_ban','')}'")
        print(f"    nb_log    = {piv.get('nb_log')}  nb_log_rnc={piv.get('nb_log_rnc')}  "
              f"annee={piv.get('annee_construction')}")
        print(f"    immat principal = {piv.get('numero_immat_principal') or '-'}")
        print(f"    usage     = '{(piv.get('usage_principal_bdnb_open') or '')[:30]}'")
        print(f"    nb_adresses_BAN = {piv.get('nb_adresse_valid_ban')}")
        for x in piv.get("l_libelle_adr") or []:
            print(f"      . {x}")
    print(f"    rel_RNC declarees sur ce bg : {rnc_list}")

# ---------- 5. Cross-RNC entre les 3 cles ----------
print("\n[5] Cross-RNC entre 12, 11, 14 :")
immat_12 = (co_by_cle.get("12|RUE|ESPERANCE") or {}).get("numero_immatriculation") \
            or (by_cle.get("12|RUE|ESPERANCE") or {}).get("numero_immatriculation")
immat_11 = (co_by_cle.get("11|RUE|ESPERANCE") or {}).get("numero_immatriculation") \
            or (by_cle.get("11|RUE|ESPERANCE") or {}).get("numero_immatriculation")
immat_14 = (co_by_cle.get("14|RUE|ESPERANCE") or {}).get("numero_immatriculation") \
            or (by_cle.get("14|RUE|ESPERANCE") or {}).get("numero_immatriculation")
print(f"  immat 12 ESPERANCE : {immat_12}")
print(f"  immat 11 ESPERANCE : {immat_11}")
print(f"  immat 14 ESPERANCE : {immat_14}")
meme_immat = (immat_12 and immat_12 == immat_11) or (immat_12 and immat_12 == immat_14)
print(f"  -> meme immat 12=11 ou 12=14 ? : {meme_immat}")

# Verifier cross-RNC : immat declare sur bati ancre apparait sur bati voisin (ou inverse)
print("\n  Cross-RNC BDNB :")
rnc_by_bg = {}
for cle, bg in bgs_seen.items():
    if not bg:
        continue
    rnc_by_bg[(cle, bg)] = bdnb_rnc_pour_bg(bg)
    time.sleep(0.05)
print(f"    bg de 12 declare : {rnc_by_bg.get(('12|RUE|ESPERANCE', bgs_seen.get('12|RUE|ESPERANCE') or ''), [])}")
print(f"    bg de 11 declare : {rnc_by_bg.get(('11|RUE|ESPERANCE', bgs_seen.get('11|RUE|ESPERANCE') or ''), [])}")
print(f"    bg de 14 declare : {rnc_by_bg.get(('14|RUE|ESPERANCE', bgs_seen.get('14|RUE|ESPERANCE') or ''), [])}")

cross_rnc = False
if immat_12:
    for k, lst in rnc_by_bg.items():
        if k[0] in ("11|RUE|ESPERANCE", "14|RUE|ESPERANCE") and immat_12 in lst:
            cross_rnc = True
            print(f"    -> immat 12 ({immat_12}) declare sur bg de {k[0]} (cross-RNC!)")
if immat_11:
    bg_12 = bgs_seen.get("12|RUE|ESPERANCE")
    if immat_11 in rnc_by_bg.get(("12|RUE|ESPERANCE", bg_12 or ""), []):
        cross_rnc = True
        print(f"    -> immat 11 ({immat_11}) declare sur bg de 12 (cross-RNC!)")
if immat_14:
    bg_12 = bgs_seen.get("12|RUE|ESPERANCE")
    if immat_14 in rnc_by_bg.get(("12|RUE|ESPERANCE", bg_12 or ""), []):
        cross_rnc = True
        print(f"    -> immat 14 ({immat_14}) declare sur bg de 12 (cross-RNC!)")
print(f"\n  -> Cross-RNC BDNB detecte ? : {cross_rnc}")

# ---------- 6. Verdict ----------
parc_overlap_11 = bool(parcs_12 & set(parcs_par_cle.get("11|RUE|ESPERANCE", [])))
parc_overlap_14 = bool(parcs_12 & set(parcs_par_cle.get("14|RUE|ESPERANCE", [])))
meme_bg_11 = bg_12 == bgs_seen.get("11|RUE|ESPERANCE") and bool(bg_12)
meme_bg_14 = bg_12 == bgs_seen.get("14|RUE|ESPERANCE") and bool(bg_12)

print()
print("=" * 78)
print("VERDICT (sans appliquer)")
print("=" * 78)
print(f"  meme bgid 12=11           : {meme_bg_11}")
print(f"  meme bgid 12=14           : {meme_bg_14}")
print(f"  meme immat 12=11 ou 12=14 : {meme_immat}")
print(f"  parcelle commune 12-11    : {parc_overlap_11}")
print(f"  parcelle commune 12-14    : {parc_overlap_14}")
print(f"  cross-RNC BDNB autoritaire: {cross_rnc}")

# Decision
if meme_immat or cross_rnc:
    verdict = "FUSION (immat commun ou cross-RNC BDNB)"
elif parc_overlap_11 or parc_overlap_14:
    verdict = ("INCERTAIN_PARCELLE_COMMUNE (parcelle commune mais "
                "bgid+immat distincts) - inspection terrain")
elif meme_bg_11 or meme_bg_14:
    verdict = ("INCERTAIN_BGID_SEUL (bgid partage mais immat distincts, "
                "parcelle distincte) - probable artefact BDNB")
else:
    verdict = ("DISTINCT (aucun lien autoritaire entre 12 et voisins) - "
                "rejoint les vraies 0-vente cibles prospection")

print(f"\n  VERDICT : {verdict}")
