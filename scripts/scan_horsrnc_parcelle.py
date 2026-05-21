"""
SCAN ELARGI GENERIQUE Paris/Lyon : adresses hors-RNC ancres -> appairage
par parcelle cadastrale RNC live (lecture seule).

Generalise scan_horsrnc_parcelle_mp_full.py pour supporter MP et DL via
env var SECTEUR (defaut : motte_picquet).

Predicat hr-ancre :
  numero_immatriculation absent
  AND _fusion_auto falsy

Source parcelles :
  1. DVF (mutations_dvf) si l'adresse a des ventes -> Section + No plan
  2. BDNB rel_batiment_groupe_parcelle si pas de ventes (bgid -> parcelles)

Format parcelle BDNB et RNC (Paris/Lyon) :
  Paris  BDNB : 75XXX000YYZZZZ (XXX=arr 7e/15e)
  Paris  RNC  : 75056XXXYYZZZZ (INSEE Paris=056)
  Lyon   BDNB : 69XXX000YYZZZZ (XXX=arr 3e)
  Lyon   RNC  : 69123XXXYYZZZZ (INSEE Lyon=123)

Match in-secteur = copro dont immat dans light.coproprietes ET
cle_orphan != copro.cle_adresse (pas l'ancre RNC elle-meme).

Caches (par secteur) :
  data/_scan_parc_rnc_{secteur}.json   : parc_rnc -> [copros RNC live]
  data/_bgid_parcelle_{secteur}.json   : bgid -> [parcelles BDNB]

Usage :
  PYTHONUTF8=1 python scripts/scan_horsrnc_parcelle.py                       # MP (defaut)
  PYTHONUTF8=1 SECTEUR=dauphine_lacassagne python scripts/scan_horsrnc_parcelle.py
"""

import json
import re
import os
import collections
import urllib.request
import urllib.parse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "motte_picquet")
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
FULL = ROOT / "data" / f"secteur_{SECTEUR}.json"
SHORT = "mp" if SECTEUR == "motte_picquet" else "dl"
CACHE_RNC = ROOT / "data" / f"_scan_parc_rnc_{SHORT}.json"
CACHE_BG = ROOT / "data" / f"_bgid_parcelle_{SHORT}.json"
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
BDNB_PARC = ("https://api.bdnb.io/v1/bdnb/donnees/"
             "rel_batiment_groupe_parcelle?batiment_groupe_id=eq.")

# Compatibilite : MP avait un cache historique '_scan_parc_rnc_mp.json'
# (sans suffixe) qu'on relit s'il existe.
LEGACY_CACHE_RNC_MP = ROOT / "data" / "_scan_parc_rnc_mp.json"
LEGACY_CACHE_BG_MP = ROOT / "data" / "_bgid_parcelle_mp.json"
if SECTEUR == "motte_picquet":
    if not CACHE_RNC.exists() and LEGACY_CACHE_RNC_MP.exists():
        CACHE_RNC = LEGACY_CACHE_RNC_MP
    if not CACHE_BG.exists() and LEGACY_CACHE_BG_MP.exists():
        CACHE_BG = LEGACY_CACHE_BG_MP

# INSEE commune-mere par departement (codes RNC = INSEE-3 + arr)
COMMUNE_INSEE = {
    "75": "056",   # Paris
    "69": "123",   # Lyon
}

# Normalisation voie (extrait de fix_taux_logement.py)
ABBR = {
    "STE": "SAINTE", "ST": "SAINT", "GAL": "GENERAL", "GEN": "GENERAL",
    "GENL": "GENERAL", "DR": "DOCTEUR", "PR": "PROFESSEUR",
    "MAL": "MARECHAL", "MNE": "MADELEINE", "PCE": "PRINCE",
    "FG": "FAUBOURG", "GRDE": "GRANDE", "AYRES": "AIRES",
}
ART = {"DE", "DU", "DES", "LA", "LE", "L", "D", "AUX", "A", "ET"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(
        ABBR.get(t, t)
        for t in re.split(r"[^A-Z0-9]+", s)
        if t and t not in ART
    ))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else str(s or "")


def bdnb_to_rnc(bdnb_id):
    """75115000DI0003 -> 75056115DI0003 (Paris)
    69383000BD0064 -> 69123383BD0064 (Lyon).
    """
    if not bdnb_id or len(bdnb_id) < 14:
        return bdnb_id
    dep = bdnb_id[:2]
    insee = COMMUNE_INSEE.get(dep)
    if insee and bdnb_id[5:8] == "000":
        return f"{dep}{insee}{bdnb_id[2:5]}{bdnb_id[8:]}"
    return bdnb_id


def dvf_parcelle_rnc(code_dep, code_commune, section, no_plan):
    """Construit ref_cadastrale RNC depuis colonnes DVF (Paris/Lyon)."""
    if not (code_dep and code_commune and section and no_plan):
        return None
    plan = re.match(r"\d+", str(no_plan))
    if not plan:
        return None
    plan_4 = plan.group(0).zfill(4)
    sec = (section or "").strip().upper().rjust(2, "0")
    cd = str(code_dep).zfill(2)
    cc = str(code_commune).zfill(3)
    insee = COMMUNE_INSEE.get(cd)
    if insee:
        return f"{cd}{insee}{cc}{sec}{plan_4}"
    return f"{cd}{cc}{sec}{plan_4}"


def fetch_rnc_by_refcad(parc_rnc, cache):
    """Renvoie copros RNC live dont ref_cad_1|2|3 = parc_rnc."""
    if parc_rnc in cache:
        return cache[parc_rnc]
    seen = {}
    for col in ("reference_cadastrale_1",
                "reference_cadastrale_2",
                "reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": parc_rnc})
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception as e:
            print(f"  ! erreur RNC live {col}={parc_rnc} : {e}")
            data = []
        for row in data:
            im = row.get("numero_immatriculation")
            if im and im not in seen:
                seen[im] = {
                    "immat": im,
                    "nom": row.get("nom_usage_copropriete") or "",
                    "syndic": row.get("nom_personne_morale") or "",
                    "adresse": row.get("adresse_reference") or "",
                    "nb_lots_total": row.get("nombre_total_lots"),
                    "nb_lots_habit": row.get("nombre_lots_usage_habitation"),
                    "ref_match_col": col,
                }
        time.sleep(0.08)
    out = list(seen.values())
    cache[parc_rnc] = out
    return out


def fetch_bdnb_parcelles(bgid, cache):
    """Renvoie liste de parcelles BDNB pour bgid."""
    if bgid in cache:
        return cache[bgid]
    url = BDNB_PARC + bgid
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.loads(r.read())
        parcs = [x.get("parcelle_id") for x in rows
                 if x.get("parcelle_id")]
    except Exception as e:
        print(f"  ! erreur BDNB rel_parc bgid={bgid} : {e}")
        parcs = []
    cache[bgid] = parcs
    time.sleep(0.05)
    return parcs


def main():
    print("=" * 80)
    print(f"SCAN ELARGI hors-RNC ancres - SECTEUR={SECTEUR}")
    print("=" * 80)

    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))
    la = light["adresses"]
    co = light["coproprietes"]
    M = full["mutations_dvf"]

    immat_secteur = {c.get("numero_immatriculation")
                     for c in co if c.get("numero_immatriculation")}
    copro_by_immat = {c.get("numero_immatriculation"): c
                      for c in co if c.get("numero_immatriculation")}

    # Index DVF par (num, voie_tokens)
    mut_by_addr = collections.defaultdict(list)
    for m in M:
        k = (numof(m.get("No voie")), toks(m.get("Voie")))
        mut_by_addr[k].append(m)

    # Cibles hr-ancres
    cibles = []
    for a in la:
        if a.get("numero_immatriculation"):
            continue
        if a.get("_fusion_auto"):
            continue
        cibles.append(a)

    tot = len(cibles)
    with_ventes = sum(1 for a in cibles
                      if (a.get("nb_ventes_logement") or 0) > 0)
    with_bdnb = sum(1 for a in cibles
                    if (a.get("nb_log_bdnb") or 0) > 0)
    no_ventes_no_bdnb = sum(1 for a in cibles
                            if (a.get("nb_ventes_logement") or 0) == 0
                            and (a.get("nb_log_bdnb") or 0) == 0)
    with_bgid = sum(1 for a in cibles if a.get("batiment_groupe_id"))

    print(f"Total adresses hors-RNC ancres        : {tot}")
    print(f"  avec ventes_logement > 0            : {with_ventes}")
    print(f"  avec nb_log_bdnb > 0                : {with_bdnb}")
    print(f"  sans ventes ET sans nb_log_bdnb     : {no_ventes_no_bdnb}")
    print(f"  avec bgid (BDNB queryable)          : {with_bgid}")
    print()

    cache_rnc = {}
    if CACHE_RNC.exists():
        try:
            cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8"))
        except Exception:
            cache_rnc = {}
    cache_bg = {}
    if CACHE_BG.exists():
        try:
            cache_bg = json.loads(CACHE_BG.read_text(encoding="utf-8"))
        except Exception:
            cache_bg = {}

    print(f"Cache RNC live ({CACHE_RNC.name}) : {len(cache_rnc)} entries")
    print(f"Cache BDNB ({CACHE_BG.name})     : {len(cache_bg)} entries")
    print()

    matches = []
    api_rnc = api_bdnb = 0

    for i, a in enumerate(cibles, 1):
        cle = a["cle"]
        parts = cle.split("|")
        bgid = a.get("batiment_groupe_id")

        parcs_rnc = collections.OrderedDict()
        rows = mut_by_addr.get((numof(parts[0]), toks(parts[-1])), [])
        for m in rows:
            pid = dvf_parcelle_rnc(
                m.get("Code departement"),
                m.get("Code commune"),
                m.get("Section"),
                m.get("No plan"),
            )
            if pid:
                parcs_rnc[pid] = parcs_rnc.get(pid, 0) + 1

        if not parcs_rnc and bgid:
            before = len(cache_bg)
            parcs_bdnb = fetch_bdnb_parcelles(bgid, cache_bg)
            if len(cache_bg) > before:
                api_bdnb += 1
            for pb in parcs_bdnb:
                pr = bdnb_to_rnc(pb)
                if pr:
                    parcs_rnc[pr] = parcs_rnc.get(pr, 0)

        if not parcs_rnc:
            continue

        for pr, n_mut in parcs_rnc.items():
            before = len(cache_rnc)
            hits = fetch_rnc_by_refcad(pr, cache_rnc)
            if len(cache_rnc) > before:
                api_rnc += 1
            in_sect = [h for h in hits if h["immat"] in immat_secteur]
            for h in in_sect:
                copro_cle = copro_by_immat[h["immat"]].get("cle_adresse")
                if copro_cle == cle:
                    continue
                matches.append({
                    "cle_orph": cle,
                    "bgid_orph": (bgid or "")[8:12],
                    "syndic_orph": (a.get("syndic") or "-")[:18],
                    "nb_ventes_log": a.get("nb_ventes_logement") or 0,
                    "nb_log_bdnb": a.get("nb_log_bdnb") or 0,
                    "parc": pr,
                    "src_parc": "DVF" if rows else "BDNB",
                    "n_mut_parc": n_mut,
                    "copro_immat": h["immat"],
                    "copro_cle": copro_cle,
                    "copro_nom": (h["nom"] or "")[:38],
                    "copro_lots": h["nb_lots_habit"],
                    "copro_lots_tot": h["nb_lots_total"],
                    "ref_col": h["ref_match_col"],
                })

        if i % 25 == 0:
            print(f"  ... {i}/{tot} cibles scannees, "
                  f"{len(matches)} matches, "
                  f"API : {api_bdnb} BDNB + {api_rnc} RNC")
            try:
                CACHE_RNC.write_text(
                    json.dumps(cache_rnc, ensure_ascii=False, indent=1),
                    encoding="utf-8")
                CACHE_BG.write_text(
                    json.dumps(cache_bg, ensure_ascii=False, indent=1),
                    encoding="utf-8")
            except Exception:
                pass

    try:
        CACHE_RNC.write_text(
            json.dumps(cache_rnc, ensure_ascii=False, indent=1),
            encoding="utf-8")
        CACHE_BG.write_text(
            json.dumps(cache_bg, ensure_ascii=False, indent=1),
            encoding="utf-8")
    except Exception:
        pass

    print()
    print("=" * 80)
    print(f"TERMINE : {tot} cibles scannees ({SECTEUR})")
    print(f"  Appels BDNB neufs : {api_bdnb}")
    print(f"  Appels RNC live neufs : {api_rnc}")
    print(f"  Cache RNC final : {len(cache_rnc)}")
    print(f"  Cache BDNB final : {len(cache_bg)}")
    print(f"MATCHES TROUVES : {len(matches)}")
    print("=" * 80)
    if not matches:
        print(f"Aucun match parcelle entre hors-RNC ancres et copros RNC "
              f"du secteur {SECTEUR}.")
        return

    print()
    print("DETAIL DES MATCHES :")
    print(f"  {'Cle orpheline':28s}  {'bgid':5s}  {'src':5s}  "
          f"{'vL':>3s}  {'bdnb':>4s}  {'Parcelle':16s}  "
          f"{'Copro immat':12s}  {'Copro cle':22s}  "
          f"{'Lots':>5s}  {'Nom RNC'}")
    print("-" * 170)
    for h in matches:
        print(f"  {h['cle_orph']:28s}  {h['bgid_orph']:5s}  "
              f"{h['src_parc']:5s}  {h['nb_ventes_log']:>3}  "
              f"{h['nb_log_bdnb']:>4}  {h['parc']:16s}  "
              f"{h['copro_immat']:12s}  {(h['copro_cle'] or '-'):22s}  "
              f"{(h['copro_lots'] or 0) or '?':>5}  {h['copro_nom']}")

    print()
    print("REGROUPEMENT par copro RNC candidate :")
    print("-" * 80)
    by_immat = collections.defaultdict(list)
    for h in matches:
        by_immat[h["copro_immat"]].append(h)
    for im, hits in sorted(by_immat.items(), key=lambda kv: -len(kv[1])):
        h0 = hits[0]
        cles = sorted(set(h["cle_orph"] for h in hits))
        parcs = sorted(set(h["parc"] for h in hits))
        nv = sum(h["nb_ventes_log"] for h in hits)
        nb = sum(h["nb_log_bdnb"] for h in hits)
        print(f"  {im}  {h0['copro_nom']:40s}  ancre={h0['copro_cle']}  "
              f"lots_tot={h0['copro_lots_tot']}")
        print(f"    parcelles communes : {parcs}")
        print(f"    cles orphelines    : {cles} "
              f"(cumul {nv} vlog + {nb} nb_log_bdnb)")


if __name__ == "__main__":
    main()
