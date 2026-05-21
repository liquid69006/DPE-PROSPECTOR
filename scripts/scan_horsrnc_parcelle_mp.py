"""
SCAN LECTURE SEULE Motte-Picquet : adresses hors-RNC actives avec
ventes -> appairage par parcelle cadastrale contre coproprietes RNC.

Predicat hr-actif (= renderSecteur, audit_horsrnc_dvf) :
  numero_immatriculation absent
  AND _fusion_auto falsy
  AND cle pas presente dans coproByCle
  AND nb_ventes_logement > 0

Pour chaque cible :
  1. Recupere parcelles DVF via mutations_dvf (Section + No plan, commune)
  2. Construit parcelle_id BDNB '<dep5><commune>000<sec><plan4>'
  3. Interroge RNC live tabular-api sur ref_cad_1/2/3
  4. Filtre copros DONT immat existe dans light.coproprietes (in-secteur)
  5. Affiche match (adresse / copro candidate / parcelle / ventes)

Cache disque pour les requetes parcelles -> data/_scan_parc_rnc_mp.json
PYTHONUTF8=1, prints ASCII-safe.
"""

import json
import re
import collections
import urllib.request
import urllib.parse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
FULL = ROOT / "data" / "secteur_motte_picquet.json"
CACHE = ROOT / "data" / "_scan_parc_rnc_mp.json"
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

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


def parcelle_id_rnc(code_dep, code_commune, section, no_plan):
    """Construit ref_cadastrale RNC : '<INSEE5><arr3><sec2><plan4>'
    Format observe Paris : '75056115DI0003' (INSEE 75056 + arr 115).
    Pour DVF Paris : code_dep='75', code_commune='115' -> insee='75056', arr=cc.
    """
    if not (code_dep and code_commune and section and no_plan):
        return None
    plan = re.match(r"\d+", str(no_plan))
    if not plan:
        return None
    plan_4 = plan.group(0).zfill(4)
    sec = (section or "").strip().upper().rjust(2, "0")
    cd = str(code_dep).zfill(2)
    cc = str(code_commune).zfill(3)
    # Paris : 75 -> INSEE 75056 + arrondissement (DVF code_commune)
    if cd == "75":
        return f"75056{cc}{sec}{plan_4}"
    # Hors Paris : INSEE = dep + commune (approximation, verifier au cas par cas)
    return f"{cd}{cc}{sec}{plan_4}"


def fetch_rnc_by_refcad(parc_id, cache):
    """Renvoie liste de copros RNC live dont ref_cad_1|2|3 = parc_id.
    Resultats dedupliques par numero_immatriculation."""
    if parc_id in cache:
        return cache[parc_id]
    seen = {}
    for col in ("reference_cadastrale_1",
                "reference_cadastrale_2",
                "reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": parc_id})
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception as e:
            print(f"  ! erreur fetch {col}={parc_id} : {e}")
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
        time.sleep(0.1)
    out = list(seen.values())
    cache[parc_id] = out
    return out


def main():
    print("=" * 80)
    print("SCAN hors-RNC actives -> appairage parcelle cadastrale (lecture seule)")
    print("=" * 80)

    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))
    la = light["adresses"]
    co = light["coproprietes"]
    M = full["mutations_dvf"]

    # Set des immat in-secteur (filtrage RNC live)
    immat_secteur = {c.get("numero_immatriculation")
                     for c in co if c.get("numero_immatriculation")}
    cle_to_copro = {c.get("cle_adresse"): c
                    for c in co if c.get("cle_adresse")}

    # Index mutations par (num, voie_tokens) -> parcelles
    mut_by_addr = collections.defaultdict(list)
    for m in M:
        k = (numof(m.get("No voie")), toks(m.get("Voie")))
        mut_by_addr[k].append(m)

    # Cache disque
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    # Cibles hr-actives
    cibles = []
    for a in la:
        if a.get("numero_immatriculation"):
            continue
        if a.get("_fusion_auto"):
            continue
        cle = a.get("cle")
        if not cle or cle in cle_to_copro:
            continue
        nvl = a.get("nb_ventes_logement") or 0
        if nvl <= 0:
            continue
        cibles.append(a)

    print(f"Cibles hr-actives (ventes_log > 0) : {len(cibles)}")
    print()

    matches = []
    cache_dirty = False

    for i, a in enumerate(cibles, 1):
        cle = a["cle"]
        parts = cle.split("|")
        rows = mut_by_addr.get((numof(parts[0]), toks(parts[-1])), [])
        if not rows:
            continue

        # Distinct parcelles pour cette adresse
        parcs = collections.OrderedDict()
        for m in rows:
            pid = parcelle_id_rnc(
                m.get("Code departement"),
                m.get("Code commune"),
                m.get("Section"),
                m.get("No plan"),
            )
            if pid:
                parcs[pid] = parcs.get(pid, 0) + 1

        if not parcs:
            continue

        # Recherche RNC live pour chaque parcelle
        for pid, n_mut in parcs.items():
            hits = fetch_rnc_by_refcad(pid, cache)
            if pid in cache and pid not in {k for k, _ in parcs.items()
                                            if k in cache}:
                cache_dirty = True
            else:
                cache_dirty = True
            in_sect = [h for h in hits if h["immat"] in immat_secteur]
            if in_sect:
                for h in in_sect:
                    # Ne reporter que si copro RNC pas deja ancre sur CETTE cle
                    copro_cle = None
                    for c in co:
                        if c.get("numero_immatriculation") == h["immat"]:
                            copro_cle = c.get("cle_adresse")
                            break
                    if copro_cle == cle:
                        continue
                    matches.append({
                        "cle_orpheline": cle,
                        "bgid_orph": (a.get("batiment_groupe_id") or "")[8:12],
                        "syndic_orph": (a.get("syndic") or "-")[:18],
                        "nb_ventes_log": a.get("nb_ventes_logement"),
                        "nb_log_bdnb": a.get("nb_log_bdnb"),
                        "parc": pid,
                        "n_mut_parc": n_mut,
                        "copro_immat": h["immat"],
                        "copro_cle": copro_cle,
                        "copro_nom": h["nom"][:38],
                        "copro_lots": h["nb_lots_habit"],
                        "ref_col": h["ref_match_col"],
                    })

        if i % 10 == 0:
            print(f"  ... {i}/{len(cibles)} cibles scannees, {len(matches)} matches cumules")
            if cache_dirty:
                try:
                    CACHE.write_text(
                        json.dumps(cache, ensure_ascii=False, indent=1),
                        encoding="utf-8")
                    cache_dirty = False
                except Exception:
                    pass

    # Sauvegarde cache finale
    try:
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    except Exception:
        pass

    print()
    print("=" * 80)
    print(f"MATCHES TROUVES : {len(matches)}")
    print("=" * 80)
    if not matches:
        print("Aucun match parcelle entre hors-RNC ventes et copros RNC du secteur.")
        return

    # Affichage
    print(f"  {'Cle orpheline':28s}  {'bgid':5s}  {'vL':>3s}  "
          f"{'Parcelle':16s}  {'Copro immat':12s}  {'Copro cle':22s}  "
          f"{'Lots':>5s}  {'Nom RNC'}")
    print("-" * 150)
    for h in matches:
        print(f"  {h['cle_orpheline']:28s}  {h['bgid_orph']:5s}  "
              f"{(h['nb_ventes_log'] or 0):>3}  {h['parc']:16s}  "
              f"{h['copro_immat']:12s}  {(h['copro_cle'] or '-'):22s}  "
              f"{(h['copro_lots'] or 0):>5}  {h['copro_nom']}")

    # Regroupement par copro candidate
    print()
    print("REGROUPEMENT par copro RNC candidate :")
    print("-" * 80)
    by_immat = collections.defaultdict(list)
    for h in matches:
        by_immat[h["copro_immat"]].append(h)
    for im, hits in sorted(by_immat.items(), key=lambda kv: -len(kv[1])):
        h0 = hits[0]
        cles = sorted(set(h["cle_orpheline"] for h in hits))
        parcs = sorted(set(h["parc"] for h in hits))
        nv = sum((h["nb_ventes_log"] or 0) for h in hits)
        print(f"  {im}  {h0['copro_nom']:40s}  ancre={h0['copro_cle']}")
        print(f"    parcelles communes : {parcs}")
        print(f"    cles orphelines    : {cles} (cumul {nv} ventes)")


if __name__ == "__main__":
    main()
