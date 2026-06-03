"""
VERSION MONTCHAT de scripts/fix_invisible_insecteur_bgids.py (Manche B1).

Copie re-pointee : chemins Montchat, sidecar _rnc_bdnb_live_missing_montchat.json,
metadata _correctif_invisible_montchat. AUCUNE table ALIAS / constante DL.

Differences avec l'original DL (toutes documentees) :
  - BDNB / LIGHT / SIDECAR re-pointes sur _montchat.
  - Garde geographique : l'original DL acceptait un row dont
    libelle_adr_principale_ban se termine par "Arrondissement" OU contient
    "69003". Montchat est aussi en CP 69003 (Lyon 3e) -> la garde 69003
    reste correcte ici. On la conserve telle quelle (parametree par la
    constante CP_GUARD pour la lisibilite).
  - Backup : ECRIT dans secteur_montchat_light.json.premancheB1.bak SEULEMENT
    s'il n'existe pas deja (la passe horsrnc_montchat, lancee AVANT, l'a
    normalement deja cree = etat pre-B1). On ne l'ecrase jamais.

La separation DL/Montchat ne repose PAS sur le CP (69003 commun) mais sur :
  (a) le sidecar _rnc_bdnb_live_missing_montchat.json (immats des copros
      Montchat uniquement), (b) la cle_adresse libre DANS CE light,
  (c) le bgid absent des adresses DE CE light. Aucun bgid DL ne peut donc
  etre injecte ici.

Usage :
  PYTHONUTF8=1 python scripts/fix_invisible_insecteur_bgids_montchat.py          # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_invisible_insecteur_bgids_montchat.py --apply
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = "montchat"
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
SIDECAR = ROOT / "data" / f"_rnc_bdnb_live_missing_{SECTEUR}.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.premancheB1.bak"
CP_GUARD = "69003"   # Lyon 3e (Montchat = CP 69003, comme DL)


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
        "numero_immatriculation": copro.get("numero_immatriculation"),
        "nb_lots_habitation": copro.get("nb_lots_habitation"),
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
            lab = str(r.get("libelle_adr_principale_ban") or "") if r else ""
            if r is None:
                row["statut"] = "SKIP_HORS_SNAPSHOT (hors secteur / vide)"
            elif not lab.strip().endswith("Arrondissement") \
                    and CP_GUARD not in lab:
                row["statut"] = "SKIP_HORS_SECTEUR"
            elif g in secteur_bgids:
                row["statut"] = "SKIP_DEJA_COMPTE (bgid deja dans une adresse)"
            elif not c or not c.get("cle_adresse"):
                row["statut"] = "SKIP_COPRO_INCONNUE"
            elif c["cle_adresse"] in cles_adr:
                owner = cbc.get(c["cle_adresse"])
                same = owner and owner.get("numero_immatriculation") == im
                row["statut"] = (
                    "SKIP_COPRO_DEJA_VISIBLE (cle prise par cette copro -- "
                    "2e batiment = fusion, pas invisibilite)" if same
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
    print("CORRECTIF MONTCHAT -- copros invisibles, bati in-secteur au snapshot")
    print("=" * 70)
    print(f"Mode               : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Lignes adresses    : {len(ad)}")
    print(f"Cibles sidecar     : {sum(len(v) for v in sidecar.values())} bgid")
    print(f"A INJECTER (CLEAN) : {len(clean)}")
    tot = sum((p["_bg"].get("nb_log") or 0) for p in clean)
    print(f"Logements ajoutes  : {tot}")
    print("-" * 70)
    for p in plan:
        flag = "  >> " if p["statut"] == "CLEAN" else "     "
        extra = (f" | bgid={p['bgid']} nb_log={p['_bg'].get('nb_log')} "
                 f"cle={p['cle']}" if p["statut"] == "CLEAN" else "")
        print(f"{flag}{p['immat']} | {str(p['nom'])[:26]:26} | "
              f"{p['statut']}{extra}")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : light non modifie. --apply pour ecrire.")
        return
    if not clean:
        print("Rien a appliquer.")
        return

    if not BAK.exists():
        BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"Sauvegarde : {BAK.name}")
    else:
        print(f"Backup {BAK.name} deja present (pre-B1) -- conserve.")
    for p in clean:
        c, r = p["_copro"], p["_bg"]
        ad.append(construire_ligne(c, r, c["cle_adresse"],
                                   cle_to_adresse(c["cle_adresse"])))
    meta = light.setdefault("metadata", {})
    meta.setdefault("stats_globales", {})["nb_adresses_croisement"] = len(ad)
    meta["_correctif_invisible_montchat"] = (
        f"{len(clean)} adresses injectees (bgid in-secteur present au "
        f"snapshot sous immat jumelle, _bdnb_match=immat_live_fix).")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Ecrit : {LIGHT.name} ({len(ad)} adresses, +{len(clean)})")


if __name__ == "__main__":
    main()
