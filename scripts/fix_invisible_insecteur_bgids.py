"""
Correctif ciblé : copros secteur invisibles dont le bâtiment EST déjà
dans le snapshot (en secteur) mais rattaché à un autre
`numero_immat_principal` (immat jumelle). Cf. data/verif_rnc_bdnb_live_report.md.

On NE touche PAS :
  - les bgid hors secteur (Villeurbanne 69100 / Lyon 4e 69004 / vides) ;
  - les bgid déjà dans une adresse (déjà comptés) ;
  - les copros déjà visibles (éviter double-rendu / swap de bâtiment).

Cibles dérivées du sidecar data/_rnc_bdnb_live_missing.json recroisé au
snapshot + light (reproductible, pas de constantes). Classement :
  CLEAN   : clé copro libre + bgid in-secteur absent des adresses
            -> injection d'une ligne adresses (approche des 42).
  SKIP_*  : non corrigé, raison explicite.

Lecture seule par défaut. --apply écrit le light (+ .bak).

Usage :
  python scripts/fix_invisible_insecteur_bgids.py            # DRY-RUN
  python scripts/fix_invisible_insecteur_bgids.py --apply
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
SIDECAR = ROOT / "data" / "_rnc_bdnb_live_missing.json"


def cle_to_adresse(cle):
    return " ".join(p for p in (cle or "").split("|") if p != "").strip()


def construire_ligne(copro, bg, cle, adresse):
    vpa = copro.get("ventes_par_an") or {}
    return {
        "cle": cle, "adresse": adresse,
        "longitude": copro.get("longitude"), "latitude": copro.get("latitude"),
        "code_iris": copro.get("code_iris"),
        "_coord_source": "rnc_immat_fix", "dans_majic": False,
        "sci_proprietaire": "non", "sci_nom": None, "sci_siren": None,
        "syndic": copro.get("syndic"), "_syndic_src": copro.get("_syndic_src"),
        "ventes_par_an": vpa,
        "nb_ventes_total": sum(vpa.values()) if vpa else 0,
        "nb_log_bdnb": bg.get("nb_log"),
        "annee_construction": bg.get("annee_construction"),
        "classe_dpe": bg.get("classe_bilan_dpe"),
        "type_batiment": bg.get("type_batiment_dpe"),
        "type_chauffage": bg.get("type_energie_chauffage"),
        "batiment_groupe_id": bg["batiment_groupe_id"],
        "_bdnb_match": "immat_live_fix",
    }


def main():
    apply = "--apply" in sys.argv
    snap = json.loads(BDNB.read_text(encoding="utf-8"))
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))

    bg = {r["batiment_groupe_id"]: r for r in snap}
    cp = light["coproprietes"]
    ad = light["adresses"]
    cp_by_immat = {c["numero_immatriculation"]: c for c in cp
                   if c.get("numero_immatriculation")}
    cles_adr = {a.get("cle") for a in ad}
    secteur_bgids = {a["batiment_groupe_id"] for a in ad
                     if a.get("batiment_groupe_id")}
    cbc = {c["cle_adresse"]: c for c in cp if c.get("cle_adresse")}

    plan = []
    for im, bgids in sidecar.items():
        c = cp_by_immat.get(im)
        for g in bgids:
            r = bg.get(g)
            row = {"immat": im, "nom": c.get("nom_copropriete") if c else None,
                   "bgid": g, "cle": c.get("cle_adresse") if c else None}
            if r is None:
                row["statut"] = "SKIP_HORS_SNAPSHOT (hors secteur / vide)"
            elif not str(r.get("libelle_adr_principale_ban") or "").strip() \
                    .endswith("Arrondissement") and "69003" not in \
                    str(r.get("libelle_adr_principale_ban") or ""):
                row["statut"] = "SKIP_HORS_SECTEUR"
            elif g in secteur_bgids:
                row["statut"] = "SKIP_DEJA_COMPTE (bgid déjà dans une adresse)"
            elif not c or not c.get("cle_adresse"):
                row["statut"] = "SKIP_COPRO_INCONNUE"
            elif c["cle_adresse"] in cles_adr:
                owner = cbc.get(c["cle_adresse"])
                same = owner and owner.get("numero_immatriculation") == im
                row["statut"] = (
                    "SKIP_COPRO_DEJA_VISIBLE (clé prise par cette copro — "
                    "2e bâtiment = fusion, pas invisibilité)" if same
                    else "SKIP_CLE_PRISE_AUTRE_COPRO (cas B3, hors scope)")
            else:
                row["statut"] = "CLEAN"
                row["_bg"] = r
                row["_copro"] = c
            plan.append(row)

    clean = [p for p in plan if p["statut"] == "CLEAN"]
    assert all(p["bgid"] not in secteur_bgids for p in clean), "collision bgid"
    assert len({p["bgid"] for p in clean}) == len(clean), "bgid en double"
    assert len({p["cle"] for p in clean}) == len(clean), "cle en double"

    print("=" * 70)
    print("CORRECTIF CIBLE — copros invisibles, bâti in-secteur déjà au snapshot")
    print("=" * 70)
    print(f"Mode               : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Lignes adresses    : {len(ad)}")
    print(f"Cibles sidecar     : {sum(len(v) for v in sidecar.values())} bgid")
    print(f"A INJECTER (CLEAN) : {len(clean)}")
    tot = sum((p["_bg"].get("nb_log") or 0) for p in clean)
    print(f"Logements ajoutés  : {tot}")
    print("-" * 70)
    for p in plan:
        flag = "  >> " if p["statut"] == "CLEAN" else "     "
        extra = (f" | bgid={p['bgid']} nb_log={p['_bg'].get('nb_log')} "
                 f"cle={p['cle']}" if p["statut"] == "CLEAN" else "")
        print(f"{flag}{p['immat']} | {str(p['nom'])[:26]:26} | "
              f"{p['statut']}{extra}")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : light non modifié. --apply pour écrire.")
        return
    if not clean:
        print("Rien à appliquer.")
        return

    bak = LIGHT.with_suffix(".json.bak")
    bak.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    for p in clean:
        c, r = p["_copro"], p["_bg"]
        ad.append(construire_ligne(c, r, c["cle_adresse"],
                                   cle_to_adresse(c["cle_adresse"])))
    meta = light.setdefault("metadata", {})
    meta.setdefault("stats_globales", {})["nb_adresses_croisement"] = len(ad)
    meta["_correctif_invisible_insecteur"] = (
        f"{len(clean)} adresses injectées (bgid in-secteur présent au "
        f"snapshot sous immat jumelle, _bdnb_match=immat_live_fix).")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {bak.name}")
    print(f"Écrit : {LIGHT.name} ({len(ad)} adresses, +{len(clean)})")


if __name__ == "__main__":
    main()
