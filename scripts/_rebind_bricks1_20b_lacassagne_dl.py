#!/usr/bin/env python3
"""Rebind cle malformee BRICKS 1 (DL).

Avant :
  '20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE' (cle malformee, coords erronees,
   immat AD5268305 BRICKS 1, dans coproprietes[], target des fusions 20+22)
  '20B|AVENUE|LACASSAGNE' (cle propre, meme bgid, meme immat, coords correctes)
  '20|AVENUE|LACASSAGNE'  (fusion src -> malformee)
  '22|AVENUE|LACASSAGNE'  (fusion src -> malformee, bgid different mais fix hors scope)

Apres :
  '20B|AVENUE|LACASSAGNE' (cle canonique, devient ancre fusion BRICKS 1)
  '20|AVENUE|LACASSAGNE'  (fusion src -> 20B|...)
  '22|AVENUE|LACASSAGNE'  (fusion src -> 20B|...)
  -- cle malformee SUPPRIMEE de doc['adresses']

ACTIONS LIGHT :
  (1) Sur 20B|AVENUE|LACASSAGNE :
        ajouter _fusion_auto_sources = ['20|...', '22|...'] (info preservee)
        (les autres champs immat/lots_hab/bgid sont deja corrects)
  (2) Sur 20|AVENUE|LACASSAGNE :
        _fusion_cible malformee -> 20B|AVENUE|LACASSAGNE
  (3) Sur 22|AVENUE|LACASSAGNE :
        _fusion_cible malformee -> 20B|AVENUE|LACASSAGNE
  (4) Sur coproprietes[] :
        cle_adresse malformee -> 20B|AVENUE|LACASSAGNE
  (5) Supprimer la cle malformee de doc['adresses']

ACTION KV :
  RIEN (la cle malformee n'a pas de tag KV).
  Note : 20B|AVENUE|LACASSAGNE a un tag 'copro_non_immat' INCORRECT
  (elle a un immat AD5268305) -- laisse tel quel par directive,
  fix separe a faire.

Dry-run par defaut. '--apply' ecrit + backup .prerebindbricks1.bak.
Strict parc-neutre (la malformee et 20B ont les memes donnees, suppression
de la malformee = 0 perte ; immat AD5268305 reste sur 20B).
"""
import argparse, json, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".prerebindbricks1.bak")

CLE_MAL = "20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE"
CLE_CAN = "20B|AVENUE|LACASSAGNE"
CLE_20  = "20|AVENUE|LACASSAGNE"
CLE_22  = "22|AVENUE|LACASSAGNE"


def to_int(x):
    try: return int(x)
    except Exception: return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc.get("coproprietes") or []

    ad_by_cle = {a.get("cle"): a for a in ad}
    co_idx = {i: c for i, c in enumerate(co)}

    print("=" * 95)
    print(f"  REBIND BRICKS 1 cle malformee  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 95)

    # Verifications
    a_mal = ad_by_cle.get(CLE_MAL)
    a_can = ad_by_cle.get(CLE_CAN)
    a_20  = ad_by_cle.get(CLE_20)
    a_22  = ad_by_cle.get(CLE_22)
    if not a_mal: print(f"  ! malformee absente : {CLE_MAL!r}"); sys.exit(2)
    if not a_can: print(f"  ! canonique absente : {CLE_CAN!r}"); sys.exit(2)
    if not a_20:  print(f"  ! 20 LACASSAGNE absente"); sys.exit(2)
    if not a_22:  print(f"  ! 22 LACASSAGNE absente"); sys.exit(2)

    # Verif identite immat / lots_hab entre malformee et canonique
    if a_mal.get("numero_immatriculation") != a_can.get("numero_immatriculation"):
        print(f"  ! immat divergent : mal={a_mal.get('numero_immatriculation')!r} "
              f"vs can={a_can.get('numero_immatriculation')!r}")
        sys.exit(3)
    if a_mal.get("nb_lots_habitation") != a_can.get("nb_lots_habitation"):
        print(f"  ! lots_hab divergent : mal={a_mal.get('nb_lots_habitation')} "
              f"vs can={a_can.get('nb_lots_habitation')}")
        sys.exit(3)
    if a_mal.get("batiment_groupe_id") != a_can.get("batiment_groupe_id"):
        print(f"  ! bgid divergent : mal={a_mal.get('batiment_groupe_id')} "
              f"vs can={a_can.get('batiment_groupe_id')}")
        sys.exit(3)
    print(f"  Coherence verifiee : immat={a_can.get('numero_immatriculation')!r}, "
          f"lots_hab={a_can.get('nb_lots_habitation')}, "
          f"bgid={a_can.get('batiment_groupe_id')[-9:]} (identiques sur mal/can)")

    # Plan d'edition
    print()
    print("  -- PLAN D'EDITION --")
    print(f"  (1) {CLE_CAN}")
    print(f"      ajouter _fusion_auto_sources = ['{CLE_20}', '{CLE_22}']")
    print(f"      coords inchangees : ({a_can.get('latitude')}, {a_can.get('longitude')}) "
          f"(deja correctes)")
    print(f"  (2) {CLE_20}")
    print(f"      _fusion_cible : {a_20.get('_fusion_cible')!r:.80} -> {CLE_CAN!r}")
    print(f"  (3) {CLE_22}")
    print(f"      _fusion_cible : {a_22.get('_fusion_cible')!r:.80} -> {CLE_CAN!r}")
    co_hits = [(i, c) for i, c in co_idx.items() if c.get("cle_adresse") == CLE_MAL]
    print(f"  (4) coproprietes[] : {len(co_hits)} entree(s) avec cle_adresse={CLE_MAL!r}")
    for i, c in co_hits:
        print(f"      idx {i} immat={c.get('numero_immatriculation')!r:>14} -> cle_adresse={CLE_CAN!r}")
    print(f"  (5) SUPPRIMER {CLE_MAL!r}")
    print(f"      bgid {a_mal.get('batiment_groupe_id')[-9:]} coords ERRONEES "
          f"({a_mal.get('latitude')}, {a_mal.get('longitude')})")

    # Verif aucune autre cle ne reference la malformee comme cible
    autres_refs = []
    for a in ad:
        cle = a.get("cle")
        if cle in (CLE_MAL, CLE_20, CLE_22): continue
        if a.get("_fusion_cible") == CLE_MAL:
            autres_refs.append(cle)
    if autres_refs:
        print(f"  !! ATTENTION : {len(autres_refs)} autres cles referencent la malformee :")
        for c in autres_refs: print(f"     {c!r}")

    # Delta parc estim
    print()
    print(f"  -- DELTA PARC ESTIME --")
    print(f"  Suppression cle malformee : strict 0 (les donnees BRICKS 1 sont preservees")
    print(f"  sur la cle canonique 20B|LACASSAGNE qui porte deja immat AD5268305 / 98 lots).")

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

    # (1) 20B|LACASSAGNE : ajouter _fusion_auto_sources
    a_can["_fusion_auto_sources"] = [CLE_20, CLE_22]
    print(f"  (1) {CLE_CAN} : _fusion_auto_sources = ['{CLE_20}', '{CLE_22}']")

    # (2) 20|LACASSAGNE : update _fusion_cible
    a_20["_fusion_cible"] = CLE_CAN
    print(f"  (2) {CLE_20} : _fusion_cible -> {CLE_CAN!r}")

    # (3) 22|LACASSAGNE : update _fusion_cible
    a_22["_fusion_cible"] = CLE_CAN
    print(f"  (3) {CLE_22} : _fusion_cible -> {CLE_CAN!r}")

    # (4) coproprietes[] : update cle_adresse
    n_co_upd = 0
    for c in co:
        if c.get("cle_adresse") == CLE_MAL:
            c["cle_adresse"] = CLE_CAN
            n_co_upd += 1
    print(f"  (4) coproprietes[] : {n_co_upd} cle_adresse mis a jour")

    # (5) Supprimer la cle malformee de doc['adresses']
    n_avant = len(ad)
    doc["adresses"] = [a for a in ad if a.get("cle") != CLE_MAL]
    n_apres = len(doc["adresses"])
    n_supp = n_avant - n_apres
    print(f"  (5) Suppression cle malformee : {n_avant} -> {n_apres} adresses (-{n_supp})")
    if n_supp != 1:
        print(f"  !! ATTENTION : {n_supp} adresses supprimees au lieu de 1")

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print()
    print(f"  Light ecrit : {LIGHT.name}")
    print()
    print(">>> APPLY OK")


if __name__ == "__main__":
    main()
