"""
Correctif SURGICAL (lot, PARC-NEUTRE) : 4 copros RNC Motte-Picquet
dont l'entree mediane / une borne n'est pas enumeree au RNC (nom en
plage ou compl. tronquees) mais partage DEJA le bgid de la copro ->
fusion-bgid bloquee (bornes consommees par la fusion RNC). Meme
pattern que 41 RUE GUILLOUD (cf. fix_guilloud_range.py), instruit
cas par cas (aucune copro RNC distincte au n° manquant ; entree
hors-RNC active porteuse de ventes ; bgid COMMUN avec le principal).

Cas (immat copro -> src cle | principal cle) :
  AC6299499  61|AVENUE|SEGUR      -> 63|AVENUE|SEGUR   (SDC du 61/63)
  AF9892365  43|RUE|FONDARY       -> 45|RUE|FONDARY    (FONDARY 43/45)
  AA1834670  63|RUE|COMMERCE      -> 65|RUE|COMMERCE    (SDC 63/65)
  AF2096014  16|RUE|FREMICOURT    -> 18|RUE|FREMICOURT  (SDC 16-18)

Effet PARC : STRICTEMENT NEUTRE pour les 4 (chaque src partage deja
le bgid de sa copro -> deja dedupe aux lots RNC, PIPELINE 6). Seul
effet : ventes du src relocalisees au rendu sous l'immat copro, et
src sort des "hors-RNC actifs". Ventes secteur conservees.

Miroir EXACT d'une fusion RNC multi-numeros (comme le frere deja
fusionne, cf. Guilloud/Acollas) : src -> _fusion_auto=True /
_fusion_cible=principal ; syndic propage depuis le principal (_grp) ;
bgid / nb_log_bdnb / _bdnb_match / usage / ventes (autoritatifs)
INCHANGES. principal._fusion_auto_sources += src ; label recalcule
"n1/n2 TYPE NOM".

Source-of-truth : FUSION_RNC_EXTRA_NUMS += {AC6299499:{61},
AF9892365:{43}, AA1834670:{63}, AF2096014:{16}} dans
make_light_motte_picquet.py (hors depot). -> regen futur correct.

Garde-fou : ABORT global si un src n'a PAS le bgid de son principal
(l'effet ne serait plus parc-neutre -> revue manuelle requise).

Cible : data/secteur_motte_picquet_light.json. Backup
.prempranges.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_mp_ranges_pn.py            # DRY-RUN
  python scripts/fix_mp_ranges_pn.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prempranges.bak"

# (immat, src_cle, dst_cle)
CASES = [
    ("AC6299499", "61|AVENUE|SEGUR", "63|AVENUE|SEGUR"),
    ("AF9892365", "43|RUE|FONDARY", "45|RUE|FONDARY"),
    ("AA1834670", "63|RUE|COMMERCE", "65|RUE|COMMERCE"),
    ("AF2096014", "16|RUE|FREMICOURT", "18|RUE|FREMICOURT"),
]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def _lead(cle):
    m = re.match(r"\d+", cle or "")
    return int(m.group()) if m else None


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a.get("cle"): a for a in light.get("adresses", [])}
    co = light.get("coproprietes", [])

    plan = []
    for immat, scle, dcle in CASES:
        src, dst = by.get(scle), by.get(dcle)
        if not src or not dst:
            print(f"ABORT {immat} : adresse manquante "
                  f"(src={bool(src)} dst={bool(dst)}).")
            return
        cop = next((c for c in co if c.get("cle_adresse") == dcle), None)
        if not cop or cop.get("numero_immatriculation") != immat:
            print(f"ABORT {immat} : copro introuvable sur {dcle} "
                  f"(got {cop and cop.get('numero_immatriculation')}).")
            return
        if any(a.get("_fusion_cible") == scle for a in light["adresses"]):
            print(f"ABORT {immat} : une adresse est fusionnee DANS "
                  f"{scle} (fusionner perdrait ses ventes).")
            return
        if not src.get("batiment_groupe_id") \
                or src.get("batiment_groupe_id") != dst.get("batiment_groupe_id"):
            print(f"ABORT {immat} : bgid src {src.get('batiment_groupe_id')} "
                  f"!= principal {dst.get('batiment_groupe_id')} -> effet "
                  f"parc NON neutre, revue manuelle requise.")
            return
        plan.append((immat, scle, dcle, src, dst, cop))

    print("=" * 74)
    print("CORRECTIF SURGICAL (lot, PARC-NEUTRE) — 4 entrees medianes MP")
    print("=" * 74)
    print(f"Mode : {'APPLY' if apply else 'DRY-RUN'}")
    all_done = True
    for immat, scle, dcle, src, dst, cop in plan:
        cur = list(dst.get("_fusion_auto_sources") or [])
        new = sorted(set(cur) | {scle})
        nums = sorted({_lead(dcle)}
                      | {_lead(s) for s in new if _lead(s) is not None})
        p = dcle.split("|")
        lbl = "/".join(map(str, nums)) + (" " + p[1] if len(p) > 1 else "") \
            + (" " + p[2] if len(p) > 2 else "")
        done = src.get("_fusion_auto") is True \
            and src.get("_fusion_cible") == dcle and scle in cur
        all_done = all_done and done
        print("-" * 74)
        print(f"{immat}  {cop.get('nom_copropriete')!r}  "
              f"({cop.get('nb_lots_habitation')} lots, {cop.get('syndic')})")
        print(f"  src {scle} : bgid={src.get('batiment_groupe_id')} "
              f"(= principal, parc-neutre) v_log={src.get('nb_ventes_logement')} "
              f"vt={src.get('nb_ventes_total')} _fa={src.get('_fusion_auto')} "
              f"syndic={src.get('syndic')!r}  [deja={done}]")
        print(f"  -> _fusion_auto=True cible={dcle} ; syndic->"
              f"{dst.get('syndic')!r} _grp ; champs autoritatifs INCHANGES")
        print(f"  -> {dcle}._fusion_auto_sources {cur} -> {new}")
        print(f"  -> {dcle}._fusion_auto_label -> {lbl!r}")

    if not apply:
        print("=" * 74)
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if all_done:
        print("ABORT : les 4 cas deja appliques (idempotent).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    traces = []
    for immat, scle, dcle, src, dst, cop in plan:
        prop = syn_ok(dst.get("syndic"))
        src["_fusion_auto"] = True
        src["_fusion_cible"] = dcle
        if prop and not syn_ok(src.get("syndic")):
            src["syndic"] = dst.get("syndic")
            src["_syndic_src"] = (dst.get("_syndic_src") or "rnc") + "_grp"
        cur = list(dst.get("_fusion_auto_sources") or [])
        new = sorted(set(cur) | {scle})
        nums = sorted({_lead(dcle)}
                      | {_lead(s) for s in new if _lead(s) is not None})
        p = dcle.split("|")
        dst["_fusion_auto_sources"] = new
        dst["_fusion_auto_label"] = "/".join(map(str, nums)) \
            + (" " + p[1] if len(p) > 1 else "") \
            + (" " + p[2] if len(p) > 2 else "")
        traces.append(f"{immat} {scle}->{dcle} (v_log "
                      f"{src.get('nb_ventes_logement')})")

    meta = light.setdefault("metadata", {})
    meta["_correctif_mp_ranges"] = (
        "4 copros RNC MP dont l'entree mediane/borne n'est pas "
        "enumeree au RNC (nom plage / compl. tronquees) mais partage "
        "DEJA le bgid de la copro : rattachees chirurgicalement comme "
        "secondaires auto (miroir fusion RNC, comme 41 GUILLOUD). "
        "PARC STRICTEMENT INCHANGE (bgid deja commun -> deja dedupe "
        "aux lots RNC, PIPELINE 6) ; ventes relocalisees au rendu sous "
        "l'immat copro ; sortie des hors-RNC actifs ; ventes secteur "
        "conservees. Champs autoritatifs (bgid/nb_log_bdnb/_bdnb_match/"
        "usage/ventes) INCHANGES, syndic propage _grp. Cas : "
        + " ; ".join(traces) + ". Source-of-truth = "
        "FUSION_RNC_EXTRA_NUMS dans make_light_motte_picquet.py. "
        f"{2 * len(plan)} enregistrements touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print("=" * 74)
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(plan)} cas appliques, "
          f"parc strictement inchange)")


if __name__ == "__main__":
    main()
