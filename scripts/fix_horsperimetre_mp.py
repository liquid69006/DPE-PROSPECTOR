"""
Correctif : adresses HORS-PERIMETRE dans le light Motte-Picquet.

Diagnostic (cf. ETAPE 1-3) : des mutations DVF de voies REELLEMENT
hors du sous-secteur Motte-Picquet ont ete mal geocodees (effondrement
BAN : dizaines de numeros distincts -> 1 SEULE coordonnee de repli)
sur un point qui tombe PAR HASARD dans le polygone -> le filtre
point-in-polygon ne les rejette pas. Voies concernees :
  - RUE DE SEVRES  : reelle 6e/7e (Duroc), hors secteur (9 entrees)
  - RUE DE L EGLISE: reelle 15e ouest (Javel), hors sous-secteur ;
    cas explicitement cite dans make_light_motte_picquet.py (4)
  - AVENUE DU MAINE: reelle 14e/15e (Montparnasse), hors secteur (21)
  - 9002||METRO DUPLEIX : code voie DVF fictif (9002) = artefact
    metro non geocodable (1)
AUCUNE de ces 35 adresses n'est RNC (0 copro) -> pas de cas
"RNC hors-polygone" ; ce sont des artefacts DVF/BDNB-gps purs.

Reparation du graphe de fusion (bgid partages avec du LEGIT) :
  - une adresse GARDEE dont _fusion_cible est supprimee -> on la
    DE-FUSIONNE (rendue standalone, ventes propres intactes).
  - une adresse GARDEE (principale) listant une supprimee dans
    _fusion_auto_sources -> on purge la reference (cosmetique).
Ex. 5 RUE MARIO NIKIS (legit, _bdnb_match=num_voie, in-secteur)
etait auto-fusionnee dans l'artefact 5 AVENUE MAINE -> de-fusionnee.

NB : metros 9001/9005/9007 + 9001 ALLEE/RUE suivent le meme pattern
mais sont HORS scope demande -> listes en ADVISORY, non supprimes
(decision utilisateur).

Cible : data/secteur_motte_picquet_light.json. Backup
.prehorsperim.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_horsperimetre_mp.py            # DRY-RUN
  python scripts/fix_horsperimetre_mp.py --apply
"""

import re
import sys
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prehorsperim.bak"

# Voies REELLEMENT hors sous-secteur (nom de voie normalise, type ignore)
STREETS_HORS = {"SEVRES", "EGLISE", "MAINE"}
# Codes voie DVF fictifs / artefacts non geocodables (cle exacte)
PHANTOM_CLES = {"9002||METRO DUPLEIX"}


def _norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s
                    if unicodedata.category(c) != "Mn").upper().strip()


def _nomvoie(cle):
    p = (cle or "").split("|")
    return p[2] if len(p) > 2 else ""


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    A = light.get("adresses", [])
    C = light.get("coproprietes", [])
    cle_adr = {c.get("cle_adresse") for c in C if c.get("cle_adresse")}

    excl = [a for a in A
            if _norm(_nomvoie(a["cle"])) in STREETS_HORS
            or a["cle"] in PHANTOM_CLES]
    exclset = {a["cle"] for a in excl}

    # Securite : aucune adresse exclue ne doit porter une copro RNC
    rnc_hit = [a["cle"] for a in excl
               if a.get("numero_immatriculation") or a["cle"] in cle_adr]

    kept = [a for a in A if a["cle"] not in exclset]
    # 1) adresses GARDEES de-fusionnees (cible supprimee)
    defus = [k for k in kept if k.get("_fusion_cible") in exclset]
    # 2) principaux GARDES dont _fusion_auto_sources reference une exclue
    srcclean = [k for k in kept
                if k.get("_fusion_auto_sources")
                and any(s in exclset for s in k["_fusion_auto_sources"])]

    vt = sum(a.get("nb_ventes_total") or 0 for a in excl)
    vl = sum(a.get("nb_ventes_logement") or 0 for a in excl)
    by_street = {}
    for a in excl:
        k = ("9002 METRO" if a["cle"] in PHANTOM_CLES
             else _norm(_nomvoie(a["cle"])))
        by_street.setdefault(k, []).append(a["cle"])

    # Advisory : memes artefacts hors scope demande
    adv = []
    for a in A:
        if a["cle"] in exclset:
            continue
        p0 = a["cle"].split("|")[0]
        if re.fullmatch(r"900[0-9]", p0) or "METRO " in a["cle"].upper():
            adv.append(a["cle"])

    print("=" * 72)
    print("CORRECTIF HORS-PERIMETRE Motte-Picquet  "
          f"({'APPLY' if apply else 'DRY-RUN'})")
    print("=" * 72)
    print(f"Adresses a EXCLURE : {len(excl)} / {len(A)}")
    for st, cles in sorted(by_street.items()):
        print(f"  [{st}] {len(cles)} :")
        for c in sorted(cles):
            a = next(x for x in excl if x["cle"] == c)
            print(f"     {c:<30} vt={a.get('nb_ventes_total')} "
                  f"vl={a.get('nb_ventes_logement')} "
                  f"logb={a.get('nb_log_bdnb')} bg="
                  f"{(a.get('batiment_groupe_id') or '')[-8:]} "
                  f"match={a.get('_bdnb_match')}")
    print("-" * 72)
    print(f"Securite copro RNC dans exclus : "
          f"{rnc_hit if rnc_hit else 'AUCUNE (0 cas RNC hors-polygone)'}")
    print(f"Adresses GARDEES a DE-FUSIONNER (cible supprimee) : "
          f"{[k['cle'] for k in defus] or 'aucune'}")
    print(f"Principaux GARDES a purger (_fusion_auto_sources) : "
          f"{[k['cle'] for k in srcclean] or 'aucun'}")
    print(f"Ventes retirees (hors-secteur) : nb_ventes_total={vt} "
          f"nb_ventes_logement={vl}")
    print(f"Adresses apres : {len(A) - len(excl)}")
    print("-" * 72)
    print(f"ADVISORY (meme pattern, HORS scope demande, NON supprime) : "
          f"{len(adv)}")
    for c in sorted(adv):
        print(f"     {c}")
    print("=" * 72)

    if rnc_hit:
        print("ABORT : une adresse exclue porte une copro RNC "
              "(verifier d'abord).")
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    if not excl:
        print("Rien a exclure (idempotent : deja applique ?).")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    # Reparation graphe de fusion AVANT suppression
    for k in defus:
        k["_fusion_auto"] = False
        k["_fusion_cible"] = None
    for k in srcclean:
        rest = [s for s in k["_fusion_auto_sources"] if s not in exclset]
        if rest:
            k["_fusion_auto_sources"] = rest
        else:
            k.pop("_fusion_auto_sources", None)
            k.pop("_fusion_auto_label", None)

    light["adresses"] = [a for a in A if a["cle"] not in exclset]

    # Garde-fou post : aucune cible orpheline restante
    rem = {a["cle"] for a in light["adresses"]}
    orph = [a["cle"] for a in light["adresses"]
            if a.get("_fusion_cible") and a["_fusion_cible"] not in rem]
    if orph:
        BAK.unlink()
        raise SystemExit(f"ABORT : cibles orphelines restantes {orph} "
                         f"(backup retire, aucune ecriture).")

    meta = light.setdefault("metadata", {})
    meta["_correctif_horsperimetre"] = (
        f"{len(excl)} adresses HORS-PERIMETRE retirees : RUE DE SEVRES "
        f"(6e/7e), RUE DE L EGLISE (15e ouest), AVENUE DU MAINE "
        f"(14e/15e) -- voies reelles hors sous-secteur, DVF mal "
        f"geocode (effondrement BAN sur point intra-polygone) -- + "
        f"9002 METRO DUPLEIX (code voie DVF fictif). 0 copro RNC "
        f"impactee. Ventes hors-secteur retirees : {vt} brut / {vl} "
        f"strict. Graphe fusion repare ({len(defus)} de-fusion, "
        f"{len(srcclean)} purge sources). Metros 9001/9005/9007 + "
        f"9001 ALLEE/RUE meme pattern NON retires (hors scope).")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(excl)} adresses retirees, "
          f"graphe fusion repare)")


if __name__ == "__main__":
    main()
