"""
Enrichissement du snapshot BDNB depuis l'API live (correctif de fond).

La passe live (scripts/verif_rnc_bdnb_live.py) a montre que le snapshot
local data/bdnb_dauphine_lacassagne.json omet 23 batiments rattaches par
le live BDNB a 20 copros du secteur (~1276 lgts). Ce script recupere ces
batiments via l'API ouverte (batiment_groupe_complet + batiment_groupe_rnc)
et les injecte dans le snapshot, au schema existant.

Subtilite : la BDNB a UN numero_immat_principal par batiment, mais la
relation est many-to-many (rel_batiment_groupe_rnc). Nos copros ont ete
trouvees via la relation ; certaines ne sont PAS le principal du batiment
(ex. W8VN principal=AB0219808 mais notre copro=AB0222935). Tout le
pipeline aval (verif/fix) clef sur numero_immat_principal -> on injecte
avec l'immat de LA COPRO SECTEUR (depuis le sidecar), en conservant le
principal BDNB d'origine dans _numero_immat_principal_bdnb pour tracabilite.

Source : data/_rnc_bdnb_live_missing.json (sidecar immat->bgid).
Lecture seule par defaut. --apply ecrit le snapshot (+ .bak).

Usage :
  python scripts/enrich_snapshot_from_live.py            # DRY-RUN
  python scripts/enrich_snapshot_from_live.py --apply
"""

import sys
import json
import time
import collections
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
SIDECAR = ROOT / "data" / "_rnc_bdnb_live_missing.json"
API = "https://api.bdnb.io/v1/bdnb/donnees"
PAUSE = 0.2

# Champs du schema snapshot disponibles dans batiment_groupe_complet
SEL = ("batiment_groupe_id,libelle_adr_principale_ban,nb_log,"
       "annee_construction,type_batiment_dpe,classe_bilan_dpe,"
       "usage_principal_bdnb_open,surface_emprise_sol,nb_niveau,"
       "hauteur_mean,type_energie_chauffage,numero_immat_principal")
SCHEMA = ["batiment_groupe_id", "libelle_adr_principale_ban",
          "numero_immat_principal", "nb_log", "nb_log_rnc",
          "annee_construction", "type_batiment_dpe", "classe_bilan_dpe",
          "usage_principal_bdnb_open", "surface_emprise_sol", "nb_niveau",
          "hauteur_mean", "type_energie_chauffage", "lon", "lat"]


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dpe-enrich/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return []


def main():
    apply = "--apply" in sys.argv
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))   # immat -> [bgid]
    snap = json.loads(BDNB.read_text(encoding="utf-8"))
    snap_bgids = {r["batiment_groupe_id"] for r in snap}

    # bgid -> immat copro secteur (depuis le sidecar)
    bg_to_immat, conflits = {}, []
    for im, bgids in sidecar.items():
        for bg in bgids:
            if bg in bg_to_immat and bg_to_immat[bg] != im:
                conflits.append((bg, bg_to_immat[bg], im))
            bg_to_immat[bg] = im

    cibles = [bg for bg in bg_to_immat if bg not in snap_bgids]
    deja = [bg for bg in bg_to_immat if bg in snap_bgids]

    records, echecs = [], []
    for bg in sorted(cibles):
        comp = get_json(f"{API}/batiment_groupe_complet"
                        f"?batiment_groupe_id=eq.{bg}&select={SEL}")
        time.sleep(PAUSE)
        rnc = get_json(f"{API}/batiment_groupe_rnc"
                       f"?batiment_groupe_id=eq.{bg}&select=nb_log")
        time.sleep(PAUSE)
        if not comp:
            echecs.append(bg)
            continue
        c = comp[0]
        immat_secteur = bg_to_immat[bg]
        rec = {k: None for k in SCHEMA}
        for k in SCHEMA:
            if k in c:
                rec[k] = c[k]
        rec["nb_log_rnc"] = (rnc[0].get("nb_log") if rnc else None)
        rec["_numero_immat_principal_bdnb"] = c.get("numero_immat_principal")
        rec["numero_immat_principal"] = immat_secteur     # clef pipeline aval
        rec["_source"] = "api_live"
        records.append(rec)

    assert not any(r["batiment_groupe_id"] in snap_bgids for r in records), \
        "COLLISION : bgid deja dans le snapshot"

    tot_log = sum((r.get("nb_log") or 0) for r in records)
    print("=" * 68)
    print("ENRICHISSEMENT SNAPSHOT BDNB DEPUIS API LIVE")
    print("=" * 68)
    print(f"Mode                         : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Snapshot actuel              : {len(snap)} batiments")
    print(f"Copros sidecar               : {len(sidecar)}")
    print(f"bgid cibles                  : {len(cibles)}")
    print(f"  deja presents (ignores)    : {len(deja)}")
    print(f"  recuperes                  : {len(records)}")
    print(f"  echecs API                 : {len(echecs)} {echecs or ''}")
    print(f"Conflits bgid multi-immat    : {len(conflits)} {conflits or ''}")
    print(f"Logements ajoutes (nb_log)   : {tot_log}")
    print("-" * 68)
    for r in sorted(records, key=lambda x: -(x.get("nb_log") or 0)):
        print(f"  {r['batiment_groupe_id']} | immat={r['numero_immat_principal']}"
              f" (bdnb={r['_numero_immat_principal_bdnb']}) | "
              f"nb_log={r.get('nb_log')} | {str(r.get('libelle_adr_principale_ban'))[:42]}")
    print("=" * 68)

    if not apply:
        print("DRY-RUN : snapshot non modifie. --apply pour ecrire.")
        return

    bak = BDNB.with_suffix(".json.bak")
    bak.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    snap.extend(records)
    BDNB.write_text(json.dumps(snap, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"Sauvegarde : {bak.name}")
    print(f"Ecrit : {BDNB.name} ({len(snap)} batiments, +{len(records)})")


if __name__ == "__main__":
    main()
