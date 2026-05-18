"""
Correctif ADDITIF : propage `usage_principal_bdnb_open` du snapshot
BDNB (data/bdnb_<secteur>.json) vers chaque adresse du light, sous la
cle `usage_principal_bdnb` (jointure exacte par batiment_groupe_id).

Contexte (voir data/diag_bdnb_horsrnc.md) : le light ne portait aucun
champ d'usage ; `type_batiment` ne separe pas residentiel/tertiaire.
Le snapshot bdnb_<sec>.json contient deja usage_principal_bdnb_open a
100 % des bgid (1238/1238 Dauphine, 1305/1305 Motte). Le propager
permettra la regle d'affichage logements (residentiel -> nb_log_bdnb,
tertiaire/secondaire/dependance/inconnu -> 0) SANS appel reseau.

-> Strategie NON DESTRUCTIVE, purement ADDITIVE :
  - ajoute `usage_principal_bdnb` (valeur snapshot, ou null si bgid
    absent du snapshot / pas de bgid)
  - ajoute `_usage_bdnb_src` = "snapshot" | "absent"
  - n'ecrase AUCUN champ existant ; le dashboard (index.html) ne lit
    pas encore ce champ -> rendu INCHANGE (preuve via
    test_render_secteur.js). Bascule de l'affichage = etape SEPAREE
    (modif index.html), hors scope.

Cible : data/secteur_<SECTEUR>_light.json. Backup distinct
.preusage.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/propage_usage_bdnb.py            # DRY-RUN
  python scripts/propage_usage_bdnb.py --apply
  SECTEUR=motte_picquet python scripts/propage_usage_bdnb.py --apply
"""

import os
import sys
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.preusage.bak"


def main():
    apply = "--apply" in sys.argv
    if not LIGHT.exists() or not BDNB.exists():
        print(f"ABORT : fichier manquant ({LIGHT.name} / {BDNB.name}).")
        return

    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    snap = {r["batiment_groupe_id"]: r.get("usage_principal_bdnb_open")
            for r in bdnb if r.get("batiment_groupe_id")}
    la = light.get("adresses", [])

    dist = collections.Counter()
    n_set = n_absent = n_already = 0
    for a in la:
        if "usage_principal_bdnb" in a:
            n_already += 1
        bg = a.get("batiment_groupe_id")
        if bg and bg in snap:
            val, src = snap[bg], "snapshot"
            n_set += 1
        else:
            val, src = None, "absent"
            n_absent += 1
        dist[val] += 1
        if apply:
            a["usage_principal_bdnb"] = val
            a["_usage_bdnb_src"] = src

    print("=" * 72)
    print("CORRECTIF ADDITIF - propagation usage_principal_bdnb (snapshot)")
    print("=" * 72)
    print(f"Secteur                           : {SECTEUR}")
    print(f"Mode                              : "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print(f"Adresses                          : {len(la)}")
    print(f"  usage propage (snapshot)        : {n_set}")
    print(f"  bgid absent du snapshot (null)  : {n_absent}")
    print(f"  champ deja present (re-run)     : {n_already}")
    print(f"Champs existants SURCHARGES ?     : NON (additif seulement)")
    print("-" * 72)
    print("Distribution usage_principal_bdnb :")
    for k, v in dist.most_common():
        print(f"  {str(k):<26} : {v}")
    print("=" * 72)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire "
              "(champs usage_principal_bdnb / _usage_bdnb_src AJOUTES).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja "
              f"(re-run -> supprimer le .bak d'abord si voulu).")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = light.setdefault("metadata", {})
    meta["_correctif_usage_bdnb"] = (
        f"Champs ADDITIFS usage_principal_bdnb (valeur snapshot "
        f"bdnb_{SECTEUR}.json:usage_principal_bdnb_open, jointure "
        f"batiment_groupe_id) + _usage_bdnb_src ajoutes ; {n_set} adr "
        f"renseignees, {n_absent} sans bgid/snapshot (null). Aucun champ "
        f"existant modifie. Dashboard inchange (index.html ne lit pas "
        f"encore usage_principal_bdnb) ; regle d'affichage logements "
        f"residentiel/tertiaire = modif index.html separee.")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} "
          f"(usage_principal_bdnb / _usage_bdnb_src ajoutes)")


if __name__ == "__main__":
    main()
