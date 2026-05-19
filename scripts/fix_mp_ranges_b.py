"""
Correctif SURGICAL (lot, Groupe B) : 2 copros RNC Motte-Picquet
dont une entree de la plage (nom RNC explicite) n'est pas enumeree
au RNC -> non fusionnee, reste "hors-RNC active". Instruits cas par
cas (aucune copro RNC distincte au n° manquant ; plage explicite ;
entree porteuse de ventes).

Cas (immat copro -> src cle | principal cle) :
  AB0577296  38|RUE|FEDERATION -> 32|RUE|FEDERATION   "32-42" 135 lots
  AA3511300  135|RUE|THEATRE   -> 133|RUE|THEATRE      "133-135" 43 lots

Effet PARC : MESURE PARC-NEUTRE (29060 -> 29060). Le src a un bgid
DISTINCT du principal, mais ce bgid est CO-OCCUPE par une AUTRE
copro RNC non fusionnee qui maintient le bucket parc bg:bgid :
  - 38 (bgid 2D39) co-occupe avec 37 = copro AD0544940
  - 135 (bgid VD62) co-occupe avec 134 = copro AD5373162
Donc fusionner l'entree ne retire PAS son bucket BDNB du parc (le
co-occupant le maintient) et ne retire pas non plus de
double-comptage : effet strictement neutre (≠ Acollas ou le bgid
n'avait pas de co-occupant RNC). Seul effet : ventes du src
relocalisees au rendu sous l'immat copro, src sort des "hors-RNC
actifs". Ventes secteur conservees.

NB B1 (AD5922125 "26/28 BD GARIBALDI") VOLONTAIREMENT EXCLU : copro
RNC = 3 lots hab seult, 26 = batiment residentiel distinct (15 log,
bgid PNXA SANS co-occupant) ; fusionner serait LOSSY (parc -15) +
attribution erronee -> laisse en l'etat.

Miroir d'une fusion RNC multi-numeros : src -> _fusion_auto=True /
_fusion_cible=principal ; syndic aligne sur le principal (_grp ;
135 THEATRE : syndic divergent = artefact BDNB) ; bgid /
nb_log_bdnb / _bdnb_match / usage / ventes (autoritatifs) INCHANGES.
principal._fusion_auto_sources += src ; label recalcule.

Source-of-truth : FUSION_RNC_EXTRA_NUMS += {AB0577296:{38},
AA3511300:{135}} dans make_light_motte_picquet.py (hors depot).

Cible : data/secteur_motte_picquet_light.json. Backup
.prempb.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_mp_ranges_b.py            # DRY-RUN
  python scripts/fix_mp_ranges_b.py --apply
"""

import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prempb.bak"

# (immat, src_cle, dst_cle, bgid_co_occupant_attendu)
CASES = [
    ("AB0577296", "38|RUE|FEDERATION", "32|RUE|FEDERATION",
     "37|RUE|FEDERATION"),
    ("AA3511300", "135|RUE|THEATRE", "133|RUE|THEATRE",
     "134|RUE|THEATRE"),
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
    for immat, scle, dcle, cocle in CASES:
        src, dst = by.get(scle), by.get(dcle)
        coa = by.get(cocle)
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
        # Garde parc-neutre : le bgid du src DOIT etre co-occupe par
        # une autre adresse non fusionnee (sinon effet != neutre).
        co_ok = (coa is not None
                 and coa.get("batiment_groupe_id") == src.get("batiment_groupe_id")
                 and not coa.get("_fusion_auto")
                 and coa.get("cle") != scle)
        if not co_ok:
            print(f"ABORT {immat} : co-occupant {cocle} n'assure pas la "
                  f"neutralite parc (bgid {coa and coa.get('batiment_groupe_id')} "
                  f"vs src {src.get('batiment_groupe_id')}, "
                  f"_fa={coa and coa.get('_fusion_auto')}) -> revue requise.")
            return
        plan.append((immat, scle, dcle, src, dst, cop, cocle))

    print("=" * 74)
    print("CORRECTIF SURGICAL (lot, Groupe B, PARC-NEUTRE mesure) — 2 cas")
    print("=" * 74)
    print(f"Mode : {'APPLY' if apply else 'DRY-RUN'}")
    all_done = True
    for immat, scle, dcle, src, dst, cop, cocle in plan:
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
              f"co-occupe par {cocle} (copro "
              f"{by[cocle].get('numero_immatriculation')}) -> parc-neutre "
              f"| nb_log_bdnb={src.get('nb_log_bdnb')} "
              f"v_log={src.get('nb_ventes_logement')} "
              f"vt={src.get('nb_ventes_total')} syndic={src.get('syndic')!r} "
              f"[deja={done}]")
        print(f"  -> _fusion_auto=True cible={dcle} ; syndic->"
              f"{dst.get('syndic')!r} _grp ; autoritatifs INCHANGES ; "
              f"parc INCHANGE (bucket maintenu par {cocle})")
        print(f"  -> {dcle}._fusion_auto_sources {cur} -> {new}")
        print(f"  -> {dcle}._fusion_auto_label -> {lbl!r}")

    if not apply:
        print("=" * 74)
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if all_done:
        print("ABORT : les 2 cas deja appliques (idempotent).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return

    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    traces = []
    for immat, scle, dcle, src, dst, cop, cocle in plan:
        prop = syn_ok(dst.get("syndic"))
        src["_fusion_auto"] = True
        src["_fusion_cible"] = dcle
        if prop and src.get("syndic") != dst.get("syndic"):
            # propage / aligne sur le principal (syndic du src absent
            # ou divergent = artefact BDNB ; meme regle que la fusion)
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
        traces.append(f"{immat} {scle}->{dcle} (parc-neutre via {cocle}, "
                       f"v_log {src.get('nb_ventes_logement')})")

    meta = light.setdefault("metadata", {})
    meta["_correctif_mp_ranges_b"] = (
        "2 copros RNC MP (plage explicite) dont une entree non "
        "enumeree au RNC : rattachees chirurgicalement comme "
        "secondaires auto (miroir fusion RNC). PARC MESURE INCHANGE "
        "(29060->29060) : bgid du src distinct du principal mais "
        "CO-OCCUPE par une autre copro RNC non fusionnee (38->bgid "
        "co-occupe par 37/AD0544940 ; 135->co-occupe par 134/"
        "AD5373162) qui maintient le bucket parc bg:bgid -> effet "
        "strictement neutre (ni dedup ni perte). Champs autoritatifs "
        "(bgid/nb_log_bdnb/_bdnb_match/usage/ventes) INCHANGES, syndic "
        "aligne _grp (135 THEATRE : syndic divergent = artefact BDNB). "
        "Ventes relocalisees au rendu sous l'immat copro, sortie des "
        "hors-RNC actifs, ventes secteur conservees. B1 AD5922125 "
        "'26/28 GARIBALDI' VOLONTAIREMENT EXCLU (copro 3 lots, bgid "
        "26 sans co-occupant -> fix lossy). Cas : " + " ; ".join(traces)
        + ". Source-of-truth = FUSION_RNC_EXTRA_NUMS dans "
        f"make_light_motte_picquet.py. {2 * len(plan)} enregistrements "
        "touches.")

    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print("=" * 74)
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(plan)} cas appliques, "
          f"parc strictement inchange)")


if __name__ == "__main__":
    main()
