#!/usr/bin/env python3
"""Corrige le faux-groupement 37/71/163/205/257/293 RUE PAUL BERT (DL).

Le bgid bdnb-bg-WPVN-TN1Z-KE2S est en realite le bati
112/114/118 RUE MAURICE FLANDIN (verifie via BDNB l_libelle_adr).
make_light a fallback en proximite GPS sur ce bati pour 6 adresses
PAUL BERT sans bati BDNB strict -> faux-fusion en label
'37/71/163/205/257/293 RUE PAUL BERT'.

ACTION :
  (a) 71 PAUL BERT (ANCRE) :
        - retirer _fusion_auto_label, _fusion_auto_sources
        - mettre batiment_groupe_id = None
        - garder _ilot='X'
  (b) 37/163/205/257/293 PAUL BERT (5 SOURCES FUSION) :
        - retirer _fusion_auto, _fusion_cible (et _fusion_auto_target
          si present), _fusion_auto_source(s) si present
        - mettre batiment_groupe_id = None
        - garder _ilot='X'
  (c) Les 3 vraies adresses 112/114/118 MAURICE FLANDIN restent
        intactes (gardent le bgid WPVN-TN1Z-KE2S) -> parc du bati
        correctement compte sur LEUR ilot reel apres fix.

Backup avant ecriture. Dry-run par defaut. '--apply' pour ecrire.
"""
import argparse, json, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".prepaulbertfaux.bak")

BG_TARGET = "bdnb-bg-WPVN-TN1Z-KE2S"
ANCRE_CLE = "71|RUE|PAUL BERT"
SRC_CLES  = ["37|RUE|PAUL BERT", "163|RUE|PAUL BERT", "205|RUE|PAUL BERT",
             "257|RUE|PAUL BERT", "293|RUE|PAUL BERT"]
ALL_CIBLES = [ANCRE_CLE] + SRC_CLES

# Champs a strip
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
    print(f"  FIX faux-groupement PAUL BERT  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 95)

    # Verif presence des 6 cibles
    missing = [c for c in ALL_CIBLES if c not in ad_by_cle]
    if missing:
        print(f"  ! cible(s) introuvable(s) : {missing}")
        sys.exit(2)

    # Avant fix : agregats sur ces 6 + vraies MAURICE FLANDIN partageant le bgid
    print()
    print(f"  -- ETAT AVANT FIX --")
    for cle in ALL_CIBLES:
        a = ad_by_cle[cle]
        print(f"  {cle}")
        for k in ("batiment_groupe_id","_ilot","_fusion_auto","_fusion_cible",
                  "_fusion_auto_label","_fusion_auto_sources","_fusion_auto_target",
                  "nb_log_bdnb","nb_lots_habitation","numero_immatriculation",
                  "latitude","longitude"):
            v = a.get(k)
            if v not in (None, "", [], {}):
                print(f"    {k:24s} = {v!r:.140}")
        print()

    # Voisins meme bgid (= les vraies MAURICE FLANDIN ?)
    print(f"  -- Voisins meme bgid {BG_TARGET[-9:]} (vraies adresses MAURICE FLANDIN) --")
    voisins = [a for a in ad
               if a.get("batiment_groupe_id") == BG_TARGET
               and a.get("cle") not in ALL_CIBLES]
    if not voisins:
        print(f"    (AUCUN voisin meme bgid -> apres fix, bgid disparait du light)")
    else:
        for v in voisins:
            print(f"    {v.get('cle'):42s} _ilot={v.get('_ilot')!r}  "
                  f"nb_log_bdnb={v.get('nb_log_bdnb')}  immat={v.get('numero_immatriculation')!r:>14}  "
                  f"lat={v.get('latitude')} lon={v.get('longitude')}")
    print()

    # Estim delta parc
    # bgValue[bgid] = depend de bgRncLots (somme lots RNC) ou bgBdnbResid (max nb_log_bdnb)
    # Le bati MAURICE FLANDIN reste intact -> bgValue inchange.
    # Les 6 PAUL BERT n'ont nb_log_bdnb=0/None et nb_lots_habitation=0/None -> 0 perte.
    n_log_lost = sum(to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in ALL_CIBLES)
    n_lots_lost = sum(to_int(ad_by_cle[c].get("nb_lots_habitation")) for c in ALL_CIBLES)
    immats_lost = [ad_by_cle[c].get("numero_immatriculation") for c in ALL_CIBLES
                   if ad_by_cle[c].get("numero_immatriculation")]
    print(f"  -- DELTA PARC ESTIME --")
    print(f"    Somme nb_log_bdnb des 6 cles      : {n_log_lost}  (a 'perdre' cote PAUL BERT)")
    print(f"    Somme nb_lots_habitation des 6    : {n_lots_lost}")
    print(f"    Immat RNC sur les 6 cles          : {immats_lost or 'aucun'}")
    print(f"    Bati MAURICE FLANDIN ({len(voisins)} adresses voisines)")
    print(f"      -> conserve bgid {BG_TARGET[-9:]} (parc intact, juste re-credite au bon ilot)")
    print()
    if n_log_lost == 0 and n_lots_lost == 0 and not immats_lost:
        print(f"  Conclusion : strict parc-neutre cote total secteur.")
        print(f"  Seul effet = re-credit du parc MAURICE FLANDIN du faux ilot 'X'")
        print(f"  (via 71 PAUL BERT actuel) vers l'ilot reel via les 3 voisines MAURICE FLANDIN.")

    # Plan d'edition
    print()
    print(f"  -- PLAN D'EDITION --")
    for cle in ALL_CIBLES:
        a = ad_by_cle[cle]
        is_ancre = (cle == ANCRE_CLE)
        strip = FIELDS_ANCRE_STRIP if is_ancre else FIELDS_SRC_STRIP
        bg_change = a.get("batiment_groupe_id") is not None
        present_to_strip = [f for f in strip if f in a and a[f] not in (None, "", [], {})]
        role = "ANCRE" if is_ancre else "SOURCE"
        print(f"    {cle:24s} ({role})")
        if bg_change: print(f"      bgid {a['batiment_groupe_id'][-9:]} -> None")
        if present_to_strip:
            for f in present_to_strip:
                print(f"      strip {f}")
        if not bg_change and not present_to_strip:
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
            if f in a:
                a.pop(f, None)

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"  Light ecrit : {LIGHT.name}")
    print()
    print(">>> APPLY OK -- les 6 cles sont desormais hr-ancres independantes")
    print(f"   (bgid=None, _ilot='X', sans label fusion fictif).")


if __name__ == "__main__":
    main()
