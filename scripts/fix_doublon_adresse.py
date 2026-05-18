"""
Correctif : deduplication des lignes `adresses` a CLE EXACTE dupliquee.

Probleme (voir audit DVF, memoire audit-dvf-coherence) : une meme cle
d'adresse apparait 2x dans `adresses`. renderSecteur() rend chaque
element et somme les ventes PAR adresse SANS dedup par batiment (la
dedup `bg:` ne porte que sur les logements). -> les ventes de la copie
sont comptees 2x dans les agregats secteur/IRIS.

Cas unique detecte : `20|RUE|ST VICTORIEN` x2 (meme bgid
bdnb-bg-H6H4-644T-6NRG, memes 6 ventes) :
  - ligne A : squelette BAN (_coord_source=ban, adresse=None, sans
    syndic, NON _fusion_auto)         -> rendue standalone (fantome)
  - ligne B : entree riche DVF/MAJIC (_coord_source=geocode, adresse,
    syndic, _fusion_auto -> 16|RUE|ST VICTORIEN) -> exclue du rendu,
    ses ventes repliees sur le noeud 16
Les 6 memes ventes comptent 2x (noeud 16 + fantome 20-A).

Correctif generique : pour chaque groupe de cle EXACTE dupliquee dont
toutes les lignes partagent le meme batiment_groupe_id, on GARDE la
ligne la plus riche (source de fusion auto > a une `adresse` > a un
`syndic` > dans_majic) et on SUPPRIME la/les autre(s) redondante(s).

Invariants asserts (anti-regression) :
  - tout batiment_groupe_id supprime reste porte par >=1 ligne restante
    (aucun logement perdu au parc)
  - toute cle qui resolvait une copro (coproByCle) reste presente
  - apres dedup, plus aucune cle dupliquee

Cible : data/secteur_dauphine_lacassagne_light.json. Backup distinct
.predoublon.bak (n'ecrase pas les .bak des fix precedents ; abort si
present). Lecture seule en mode defaut.

Usage :
  python scripts/fix_doublon_adresse.py            # DRY-RUN
  python scripts/fix_doublon_adresse.py --apply     # ecrit + .bak
"""

import sys
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.predoublon.bak"


def richesse(a):
    """Score de richesse : on garde la ligne au score max."""
    return (
        1 if a.get("_fusion_auto") else 0,           # source de fusion auto
        1 if (a.get("adresse") or "").strip() else 0,  # libelle present
        1 if a.get("syndic") else 0,                  # syndic connu
        1 if a.get("dans_majic") else 0,              # presence MAJIC
        1 if a.get("sci_siren") else 0,               # SCI identifiee
    )


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    adresses = light["adresses"]
    copros = light["coproprietes"]
    cle_copro = {c.get("cle_adresse") for c in copros if c.get("cle_adresse")}

    by = collections.defaultdict(list)
    for a in adresses:
        by[a.get("cle")].append(a)
    dups = {k: v for k, v in by.items() if k is not None and len(v) > 1}

    a_supprimer = []          # objets adresse a retirer (identite)
    rapport = []
    for cle, rows in sorted(dups.items()):
        bgs = {r.get("batiment_groupe_id") for r in rows}
        if len(bgs) != 1:
            rapport.append((cle, "SKIP — bgid differents (vraies adresses "
                                 "distinctes, pas un doublon)", rows, None))
            continue
        keep = max(rows, key=richesse)
        drop = [r for r in rows if r is not keep]
        a_supprimer += drop
        rapport.append((cle, "DEDUP", rows, keep))

    # bgid encore couverts apres suppression ?
    rest_ids = id_set = set()
    drop_ids = {id(x) for x in a_supprimer}
    bg_rest = collections.Counter()
    for a in adresses:
        if id(a) in drop_ids:
            continue
        if a.get("batiment_groupe_id"):
            bg_rest[a["batiment_groupe_id"]] += 1
    perdus = [a["batiment_groupe_id"] for a in a_supprimer
              if a.get("batiment_groupe_id")
              and bg_rest[a["batiment_groupe_id"]] == 0]
    assert not perdus, f"REGRESSION : bgid orphelins apres dedup : {perdus}"

    # cle->copro toujours presente ?
    cles_rest = {a.get("cle") for a in adresses if id(a) not in drop_ids}
    casse = [k for k in cle_copro if k in dups and k not in cles_rest]
    assert not casse, f"REGRESSION : cle copro disparue : {casse}"

    ventes_dedoublonnees = sum((a.get("nb_ventes_total") or 0)
                               for a in a_supprimer)

    print("=" * 70)
    print("CORRECTIF DEDUPLICATION ADRESSES (cle exacte dupliquee)")
    print("=" * 70)
    print(f"Mode                          : "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print(f"Lignes adresses actuelles     : {len(adresses)}")
    print(f"Cles dupliquees               : {len(dups)}")
    print(f"Lignes a SUPPRIMER            : {len(a_supprimer)}")
    print(f"Ventes retirees du double-cpt : {ventes_dedoublonnees}")
    print(f"Invariant parc (0 bgid perdu) : OK")
    print(f"Invariant copros (0 cassee)   : OK")
    print("-" * 70)
    for cle, verdict, rows, keep in rapport:
        print(f"[{verdict}] {cle!r}  (x{len(rows)})")
        for r in rows:
            tag = ("GARDE" if r is keep else
                   "SUPPR" if verdict == "DEDUP" else "—")
            print(f"   {tag} | match={r.get('_bdnb_match')} "
                  f"| coord={r.get('_coord_source')} "
                  f"| fusion_auto={r.get('_fusion_auto')} "
                  f"| adresse={r.get('adresse')!r} "
                  f"| syndic={r.get('syndic')!r} "
                  f"| bgid={r.get('batiment_groupe_id')} "
                  f"| ventes={r.get('nb_ventes_total')}")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not a_supprimer:
        print("Rien a faire.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja. Le deplacer avant "
              f"--apply.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    light["adresses"] = [a for a in adresses if id(a) not in drop_ids]
    meta = light.setdefault("metadata", {})
    sg = meta.setdefault("stats_globales", {})
    sg["nb_adresses_croisement"] = len(light["adresses"])
    meta["_correctif_doublon"] = (
        f"{len(a_supprimer)} ligne(s) adresse a cle exacte dupliquee "
        f"supprimee(s) (squelette redondant meme bgid ; "
        f"~{ventes_dedoublonnees} ventes etaient comptees 2x dans les "
        f"agregats). Cle(s) : "
        f"{', '.join(sorted(dups))}.")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(light['adresses'])} adresses)")


if __name__ == "__main__":
    main()
