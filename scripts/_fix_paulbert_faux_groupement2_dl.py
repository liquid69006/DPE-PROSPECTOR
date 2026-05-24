#!/usr/bin/env python3
"""Corrige le 2e faux-groupement '148/158/188/202/290 RUE PAUL BERT' (DL).

Suite du commit 185aaa7 : 5 cles supplementaires partagent le meme
bgid faux WPVN-TN1Z-KE2S (=  MAURICE FLANDIN BDNB) avec leur propre
ancre 148 + label fictif '148/158/188/202/290 RUE PAUL BERT'.
Aucune copro RNC, nb_log_bdnb=None pour les 5 -> delta parc strict 0.

ACTION (calque sur commit 185aaa7) :
  (a) 148 PAUL BERT (ANCRE) :
        strip _fusion_auto_label, _fusion_auto_sources
        batiment_groupe_id = None
        _ilot='X' preserve
  (b) 158/188/202/290 PAUL BERT (4 SOURCES) :
        strip _fusion_auto, _fusion_cible (et variantes _fusion_auto_target,
        _fusion_auto_source, _fusion_auto_sources, _fusion_auto_label si present)
        batiment_groupe_id = None
        _ilot='X' preserve

Dry-run par defaut. '--apply' ecrit + backup .prepaulbertfaux2.bak.
"""
import argparse, json, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".prepaulbertfaux2.bak")

BG_TARGET = "bdnb-bg-WPVN-TN1Z-KE2S"
ANCRE_CLE = "148|RUE|PAUL BERT"
SRC_CLES  = ["158|RUE|PAUL BERT", "188|RUE|PAUL BERT",
             "202|RUE|PAUL BERT", "290|RUE|PAUL BERT"]
ALL_CIBLES = [ANCRE_CLE] + SRC_CLES

FIELDS_ANCRE_STRIP = ("_fusion_auto_label", "_fusion_auto_sources")
FIELDS_SRC_STRIP   = ("_fusion_auto", "_fusion_cible", "_fusion_auto_target",
                      "_fusion_auto_source", "_fusion_auto_sources",
                      "_fusion_auto_label")


def to_int(x):
    try: return int(x)
    except Exception: return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    ad_by_cle = {a.get("cle"): a for a in ad}

    print("=" * 95)
    print(f"  FIX faux-groupement 148/158/188/202/290 PAUL BERT  "
          f"({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 95)

    missing = [c for c in ALL_CIBLES if c not in ad_by_cle]
    if missing:
        print(f"  ! cible(s) introuvable(s) : {missing}")
        sys.exit(2)

    # Etat avant
    print()
    print(f"  -- ETAT AVANT FIX --")
    for cle in ALL_CIBLES:
        a = ad_by_cle[cle]
        print(f"  {cle:24s}  bgid={a.get('batiment_groupe_id')!r:>32}  _ilot={a.get('_ilot')!r}")
        for k in ("_fusion_auto","_fusion_cible","_fusion_auto_label",
                  "_fusion_auto_sources","nb_log_bdnb","nb_lots_habitation",
                  "numero_immatriculation"):
            v = a.get(k)
            if v not in (None, "", [], {}):
                print(f"      {k:24s} = {v!r:.140}")

    # Delta parc
    n_log = sum(to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in ALL_CIBLES)
    n_lot = sum(to_int(ad_by_cle[c].get("nb_lots_habitation")) for c in ALL_CIBLES)
    immats = [ad_by_cle[c].get("numero_immatriculation") for c in ALL_CIBLES
              if ad_by_cle[c].get("numero_immatriculation")]
    print()
    print(f"  -- DELTA PARC ESTIME --")
    print(f"    Somme nb_log_bdnb des 5 cles : {n_log}")
    print(f"    Somme nb_lots_habitation     : {n_lot}")
    print(f"    Immat RNC sur les 5 cles     : {immats or 'aucun'}")
    if n_log == 0 and n_lot == 0 and not immats:
        print(f"    -> strict parc-neutre.")

    # Verif voisins meme bgid post-fix
    voisins_apres = [a for a in ad
                     if a.get("batiment_groupe_id") == BG_TARGET
                     and a.get("cle") not in ALL_CIBLES]
    print()
    print(f"  -- Voisins meme bgid {BG_TARGET[-9:]} apres fix --")
    if not voisins_apres:
        print(f"    AUCUN voisin -> bgid {BG_TARGET[-9:]} disparait du light DL post-fix")
    else:
        for v in voisins_apres:
            print(f"    {v.get('cle'):42s}")

    # Plan d'edition
    print()
    print(f"  -- PLAN D'EDITION --")
    for cle in ALL_CIBLES:
        a = ad_by_cle[cle]
        is_ancre = (cle == ANCRE_CLE)
        strip = FIELDS_ANCRE_STRIP if is_ancre else FIELDS_SRC_STRIP
        bg_change = a.get("batiment_groupe_id") is not None
        present = [f for f in strip if f in a and a[f] not in (None, "", [], {})]
        role = "ANCRE" if is_ancre else "SOURCE"
        print(f"    {cle:24s} ({role})")
        if bg_change: print(f"      bgid {a['batiment_groupe_id'][-9:]} -> None")
        for f in present: print(f"      strip {f}")
        if not bg_change and not present:
            print(f"      (no-op : deja propre)")

    if not args.apply:
        print()
        print("=" * 95)
        print("  DRY-RUN OK - rerunner avec --apply pour ecrire")
        print("=" * 95)
        return

    # APPLY
    print()
    print("=" * 95)
    print("  APPLY")
    print("=" * 95)
    shutil.copy2(LIGHT, BAK)
    print(f"  Backup : {BAK.name}")
    for cle in ALL_CIBLES:
        a = ad_by_cle[cle]
        a["batiment_groupe_id"] = None
        strip = FIELDS_ANCRE_STRIP if cle == ANCRE_CLE else FIELDS_SRC_STRIP
        for f in strip:
            if f in a: a.pop(f, None)
    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"  Light ecrit : {LIGHT.name}")
    print()
    print(">>> APPLY OK -- 5 cles devenues hr-ancres independantes")


if __name__ == "__main__":
    main()
