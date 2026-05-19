"""
Correctif SURGICAL : copro RNC AB1301613 "4-10, AVENUE EMILE ACOLLAS"
(Motte-Picquet) — entrees 4 & 6 detachees.

Constat (diagnostic ; hors-pattern du scan paires — cf.
data/PIPELINE.md §4 FUSION_RNC_EXTRA_NUMS / §5 chaine MP) :
  - RNC AB1301613 : nom "4-10, AVENUE EMILE ACOLLAS", reference
    "10 Avenue Emile Acollas", 160 lots hab, syndic ANDRE GRIFFATON.
    nombre_d_adresses_complementaires=6 mais l'open-data n'expose que
    adresse_complementaire_1/2/3, TOUTES = "8-10 AVENUE EMILE ACOLLAS".
  - La fusion RNC multi-numeros de make_light ne parse JAMAIS le nom
    (peu fiable) : elle ne deduit que {8,10} des champs structures ->
    seul 8|AVENUE|EMILE ACOLLAS est fusionne dans 10 (AB1301613).
  - 4 & 6 Avenue Emile Acollas restent des adresses hors-RNC (BDNB
    num_voie) : immat=None, bgid propres, 16 / 18 log BDNB, 6 / 4
    ventes logement -> apparaissent comme "hors-RNC actifs" alors
    qu'elles appartiennent a AB1301613 (meme ligne d'immeuble,
    lat 48.8523->48.8520, meme IRIS ; cf. frere 8 deja fusionne).
  - Hors-pattern du scan de paires (paire meme n°+voie, type
    different) : ici plage "4-10" tronquee cote RNC -> non detecte.

Cote Suffren (67/69/71 -> AD6326128 "IMM.248/65-71 SUFFREN",
CABINET BALZANO) : DEJA correctement fusionne (compl. RNC = 67/69/71).
Copro DISTINCTE -> NON touchee ici.

Source-of-truth : FUSION_RNC_EXTRA_NUMS += {"AB1301613": {4, 6}} dans
make_light_motte_picquet.py (hors depot) — reinjection des numeros
manquants dans le GROUPE DE FUSION RNC (et non via ALIAS_RNC : on
mime exactement le chemin du frere 8, sans toucher inutilement
bgid/bdnb des entrees). -> regen futur correct.

Effet PARC (mesure, NON neutre) : conforme PIPELINE 6 RNC-prioritaire.
Une fois 4 & 6 fusionnees sous AB1301613, renderSecteur compte la
copro par bg:bgid = 160 lots RNC (autoritatif) et NE compte plus les
buckets BDNB autonomes de 4 (16) et 6 (18) -> parc secteur -34 lgts.
Ce -34 RETIRE un double-comptage : 16+18 logements BDNB (approx.
emprise batie) qui se superposaient aux 160 lots RNC de la MEME
copro. Comportement IDENTIQUE au frere 8 (deja fusionne, deja
subsume). Ventes integralement CONSERVEES (relocalisees au rendu
sous AB1301613). Decision validee : "laisser tel quel, conforme 6"
= on ne contourne pas la dedup §6, on l'applique (RNC > BDNB).

Ici (light deja patche), reproduction chirurgicale SANS regen
destructif : 4 & 6 Avenue Emile Acollas deviennent secondaires auto
de 10 (AB1301613), EXACTEMENT comme le frere 8 :
  - _fusion_auto=True / _fusion_cible=10|AVENUE|EMILE ACOLLAS
  - syndic propage depuis le principal (ANDRE GRIFFATON, _grp)
  - bgid / nb_log_bdnb / _bdnb_match / usage / ventes (champs
    autoritatifs) : INCHANGES dans la donnee. Au RENDU : ventes
    relocalisees sous AB1301613, 4/6 sortent des "hors-RNC actifs",
    et leurs 16+18 BDNB sont subsumes par les 160 RNC (parc -34).
  - 10._fusion_auto_sources : ['8'] -> ['4','6','8'] ;
    _fusion_auto_label -> "4/6/8/10 AVENUE EMILE ACOLLAS".
3 enregistrements touches (4, 6, 10).

Cible : data/secteur_motte_picquet_light.json. Backup
.preacollas.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_acollas_range.py            # DRY-RUN
  python scripts/fix_acollas_range.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.preacollas.bak"
SRC_CLES = ["4|AVENUE|EMILE ACOLLAS", "6|AVENUE|EMILE ACOLLAS"]
DST_CLE = "10|AVENUE|EMILE ACOLLAS"
IMMAT = "AB1301613"            # 4-10, AVENUE EMILE ACOLLAS


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def _lead(cle):
    m = re.match(r"\d+", cle or "")
    return int(m.group()) if m else None


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a.get("cle"): a for a in light.get("adresses", [])}
    dst = by.get(DST_CLE)
    srcs = [(k, by.get(k)) for k in SRC_CLES]

    missing = [k for k, a in srcs if not a] + ([] if dst else [DST_CLE])
    if missing:
        print(f"ABORT : adresse(s) manquante(s) : {missing}.")
        return
    cop = next((c for c in light.get("coproprietes", [])
                if c.get("cle_adresse") == DST_CLE), None)
    if not cop or cop.get("numero_immatriculation") != IMMAT:
        print(f"ABORT : copro {IMMAT} introuvable sur {DST_CLE} "
              f"(got {cop and cop.get('numero_immatriculation')}).")
        return
    # Aucune adresse ne doit etre auto-fusionnee DANS 4 ou 6
    # (fusionner 4/6 ailleurs perdrait alors ses ventes au rendu).
    bad = [a.get("cle") for a in light["adresses"]
           if a.get("_fusion_cible") in SRC_CLES]
    if bad:
        print(f"ABORT : adresses auto-fusionnees dans 4/6 : {bad}.")
        return

    prop_syn = syn_ok(dst.get("syndic"))
    cur_srcs = list(dst.get("_fusion_auto_sources") or [])
    new_srcs = sorted(set(cur_srcs) | set(SRC_CLES))
    # Label miroir make_light : tous les numeros (principal + secs).
    all_nums = sorted({_lead(DST_CLE)}
                      | {_lead(s) for s in new_srcs if _lead(s) is not None})
    parts = DST_CLE.split("|")
    t, nm = (parts[1], parts[2]) if len(parts) == 3 else ("", "")
    new_label = "/".join(str(n) for n in all_nums) \
        + (" " + t if t else "") + (" " + nm if nm else "")

    done = all(a.get("_fusion_auto") is True
               and a.get("_fusion_cible") == DST_CLE for _, a in srcs) \
        and set(SRC_CLES).issubset(set(cur_srcs))

    print("=" * 70)
    print("CORRECTIF SURGICAL — 4 & 6 AVENUE EMILE ACOLLAS -> copro "
          "AB1301613")
    print("=" * 70)
    print(f"Mode                 : {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Deja applique        : {done}")
    print(f"Copro cible          : {cop.get('nom_copropriete')} "
          f"({IMMAT}) — {cop.get('nb_lots_habitation')} lots — "
          f"syndic {cop.get('syndic')}")
    print("-" * 70)
    for k, a in srcs:
        print(f"src {k}  AVANT :")
        print(f"  bgid={a.get('batiment_groupe_id')} "
              f"_bdnb_match={a.get('_bdnb_match')} "
              f"nb_log_bdnb={a.get('nb_log_bdnb')} "
              f"usage={a.get('usage_principal_bdnb')!r}")
        print(f"  syndic={a.get('syndic')!r} "
              f"_fusion_auto={a.get('_fusion_auto')} "
              f"_fusion_cible={a.get('_fusion_cible')} "
              f"nb_ventes_total={a.get('nb_ventes_total')} "
              f"nb_ventes_logement={a.get('nb_ventes_logement')}")
    print("Transformation (miroir fusion RNC multi-n°, comme frere 8) :")
    print(f"  champs autoritatifs (bgid/nb_log_bdnb/_bdnb_match/usage) "
          f"-> INCHANGES dans la donnee")
    print(f"  _fusion_auto/cible  -> True / {DST_CLE}")
    print(f"  syndic              -> {dst.get('syndic')!r} "
          f"{'(propage _grp)' if prop_syn else '(NON propage)'}")
    print(f"  ventes (DVF/auto)   : CONSERVEES (relocalisees au rendu "
          f"sous {IMMAT} ; 4/6 sortent des hors-RNC actifs)")
    print(f"  parc                : -34 lgts attendu (16+18 BDNB "
          f"subsumes par 160 RNC, dedup §6, comme frere 8)")
    print(f"  10._fusion_auto_sources : {cur_srcs} -> {new_srcs}")
    print(f"  10._fusion_auto_label   : "
          f"{dst.get('_fusion_auto_label')!r} -> {new_label!r}")
    print("=" * 70)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if done:
        print("ABORT : correctif deja applique (idempotent).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    for _k, a in srcs:
        a["_fusion_auto"] = True
        a["_fusion_cible"] = DST_CLE
        if prop_syn and not syn_ok(a.get("syndic")):
            a["syndic"] = dst.get("syndic")
            a["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"
        # bgid / nb_log_bdnb / _bdnb_match / usage / ventes : INTACTS.

    dst["_fusion_auto_sources"] = new_srcs
    dst["_fusion_auto_label"] = new_label

    meta = light.setdefault("metadata", {})
    meta["_correctif_acollas"] = (
        "Copro RNC AB1301613 '4-10, AVENUE EMILE ACOLLAS' (160 lots, "
        "ANDRE GRIFFATON) : adresses_complementaires RNC tronquees a "
        "'8-10' (open-data 3 slots) -> make_light ne deduisait que "
        "{8,10}. 4 & 6 AVENUE EMILE ACOLLAS rattachees chirurgicalement "
        "comme secondaires auto de 10 (miroir exact du frere 8) : "
        "champs autoritatifs (bgid/nb_log_bdnb/_bdnb_match/usage/ventes) "
        "INCHANGES dans la donnee. Au rendu : ventes (4: 8 brut/6 "
        "strict ; 6: 4/4) CONSERVEES, relocalisees sous AB1301613, 4/6 "
        "sorties des 'hors-RNC actifs'. Parc secteur -34 lgts "
        "(29094->29060) : les 16+18 logements BDNB de 4/6 (approx. "
        "emprise) etaient un double-comptage des 160 lots RNC de la "
        "MEME copro -> subsumes (RNC-prioritaire, PIPELINE 6 ; "
        "identique au frere 8 deja subsume). Ventes secteur inchangees "
        "(729,0 brut / 549,8 strict). 10._fusion_auto_sources -> "
        "['4','6','8'], label '4/6/8/10 AVENUE EMILE ACOLLAS'. Cote "
        "Suffren (67/69/71 -> AD6326128, copro DISTINCTE) deja correct, "
        "NON touche. Source-of-truth = FUSION_RNC_EXTRA_NUMS dans "
        "make_light_motte_picquet.py. 3 enregistrements touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (4 & 6 AVENUE EMILE ACOLLAS -> "
          f"secondaires de {DST_CLE} ; ventes conservees/relocalisees ; "
          f"parc -34 dedup §6)")


if __name__ == "__main__":
    main()
