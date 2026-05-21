"""
Patch IN-PLACE du light pour reparer les 104 adresses MP creees par les
anciennes versions de fix_rnc_bdnb_attribution.py / fix_horsrnc_attribution.py
sans propagation immat + lots_habitation.

Cible : adresses ou _bdnb_match in {'immat_fix','immat_horsrnc_fix'} et
        numero_immatriculation absent.

Propagation depuis la copro liee par cle_adresse :
  - numero_immatriculation
  - nb_lots_habitation
  - syndic + _syndic_src (si non valide)
  - ventes_par_an_logement, nb_ventes_logement (depuis copro si dispo)
  - taux_rotation / classement_rotation (recalcul depuis nb_ventes_total)
  - taux_rotation_logement / classement_rotation_logement

Parc strictement neutre : parc_model utilisait deja co.get(cle).

Usage :
  PYTHONUTF8=1 python scripts/patch_light_propagate_immat_inplace.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/patch_light_propagate_immat_inplace.py --apply
"""

import re
import sys
import json
import copy
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "motte_picquet")
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prepropagimmat.bak"

# Markers historiques d'origine des broken adresses :
#   - 'immat' / 'num_voie' / 'gps'    : pivot make_light de base (DL bug
#     systemique : non-propagation sur cette branche)
#   - 'immat_fix'                     : fix_rnc_bdnb_attribution.py
#   - 'immat_horsrnc_fix'             : fix_horsrnc_attribution.py
#   - 'immat_live_fix'                : fix_invisible_insecteur_bgids.py
# Pas de filtre : on traite TOUTES les adresses broken (immat manquant
# alors qu'une copro est liee via cle_adresse). La logique de step 4
# protege les adresses deja OK.
TARGETS = None  # None = pas de filtre marker


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def classer(taux):
    if taux is None:
        return None
    if taux > 3:
        return "Très actif"
    if taux >= 2:
        return "Actif"
    if taux >= 1:
        return "Modéré"
    return "Figé"


def parc_model(light):
    ad = light["adresses"]
    co = {c["cle_adresse"]: c for c in light["coproprietes"]
          if c.get("cle_adresse")}
    RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    bgRncLots, bgBdnb, immatBg = {}, {}, {}
    for a in ad:
        if a["cle"] in fused:
            continue
        bg = a.get("batiment_groupe_id")
        cp = co.get(a["cle"])
        if bg and cp and (cp.get("nb_lots_habitation") or 0) > 0:
            im = cp.get("numero_immatriculation") or cp["cle_adresse"]
            immatBg.setdefault(im, bg)
            bgRncLots.setdefault(immatBg[im], {})[im] = \
                cp["nb_lots_habitation"]
        if bg and not cp and a.get("usage_principal_bdnb") in RESID \
                and (a.get("nb_log_bdnb") or 0) > 0 and bg not in bgBdnb:
            bgBdnb[bg] = a["nb_log_bdnb"]
    parc = 0
    for bg in set(bgRncLots) | set(bgBdnb):
        v = (sum(bgRncLots[bg].values()) if bg in bgRncLots
             else bgBdnb.get(bg, 0))
        parc += v
    return parc


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    cbc = {c.get("cle_adresse"): c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    cbc_p = {c.get("cle_adresse"): c for c in patched["coproprietes"]
             if c.get("cle_adresse")}

    cibles, broken_before, broken_after = [], 0, 0
    propag_count = 0
    for a in patched["adresses"]:
        if TARGETS is not None and a.get("_bdnb_match") not in TARGETS:
            continue
        if a.get("_fusion_auto"):
            continue
        cp = cbc_p.get(a["cle"])
        if not cp or not cp.get("numero_immatriculation"):
            continue
        # Cibles = adresses broken UNIQUEMENT (immat manquant cote adresse
        # alors qu'une copro liee a une immat). Evite recompute taux sur
        # les adresses OK (qui pourrait changer la valeur par effet bord).
        if a.get("numero_immatriculation"):
            continue
        broken_before += 1
        cibles.append((a, cp))

    moves = []
    for a, cp in cibles:
        before = {
            "immat": a.get("numero_immatriculation"),
            "nb_lots_habitation": a.get("nb_lots_habitation"),
            "taux": a.get("taux_rotation"),
            "syn": a.get("syndic"),
        }
        changed = False

        if not a.get("numero_immatriculation") and cp.get("numero_immatriculation"):
            a["numero_immatriculation"] = cp["numero_immatriculation"]
            changed = True

        nlog = cp.get("nb_lots_habitation") or 0
        if nlog > 0 and not a.get("nb_lots_habitation"):
            a["nb_lots_habitation"] = nlog
            changed = True

        # syndic seulement si l'adresse n'en a pas de valide
        if syn_ok(cp.get("syndic")) and not syn_ok(a.get("syndic")):
            a["syndic"] = cp["syndic"]
            a["_syndic_src"] = cp.get("_syndic_src") or "rnc"
            changed = True

        # Propage ventes_par_an_logement + nb_ventes_logement si copro les a
        # (copros generales : pas forcement, donc fallback ce qui est deja la)
        if cp.get("ventes_par_an_logement") and not a.get("ventes_par_an_logement"):
            a["ventes_par_an_logement"] = cp["ventes_par_an_logement"]
            changed = True
        if cp.get("nb_ventes_2021_2025") is not None \
                and a.get("nb_ventes_logement") in (None, 0):
            # Hypothese : copros generales ne ventilent pas logement, on garde
            # nb_ventes_logement tel quel
            pass

        # Recalcul taux + classement si on a maintenant nb_lots_habit
        nlog_now = a.get("nb_lots_habitation") or 0
        if nlog_now > 0:
            nbt = a.get("nb_ventes_total") or 0
            nbl = a.get("nb_ventes_logement") or 0
            tx = round(nbt / (5 * nlog_now / 100), 1) if nbt else 0.0
            txl = round(nbl / (5 * nlog_now / 100), 1) if nbl else 0.0
            if a.get("taux_rotation") != tx:
                a["taux_rotation"] = tx
                a["classement_rotation"] = classer(tx)
                changed = True
            if a.get("taux_rotation_logement") != txl:
                a["taux_rotation_logement"] = txl
                a["classement_rotation_logement"] = classer(txl)
                changed = True

        if changed:
            propag_count += 1
            after = {
                "immat": a.get("numero_immatriculation"),
                "nb_lots_habitation": a.get("nb_lots_habitation"),
                "taux": a.get("taux_rotation"),
                "syn": a.get("syndic"),
            }
            moves.append((a["cle"], before, after))

    # Compteur final BROKEN (= adresses sans immat alors qu'une copro liee existe)
    for a in patched["adresses"]:
        if a.get("_fusion_auto"):
            continue
        cp = cbc_p.get(a["cle"])
        if cp and cp.get("numero_immatriculation") \
                and not a.get("numero_immatriculation"):
            broken_after += 1

    parc1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 80)
    print(f"PATCH IN-PLACE PROPAGATION IMMAT - {SECTEUR} - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 80)
    print(f"  Adresses ciblees (broken : immat absent + cp lie via cle) : "
          f"{len(cibles)}")
    print(f"  Adresses BROKEN avant : {broken_before}")
    print(f"  Adresses modifiees    : {propag_count}")
    print(f"  Adresses BROKEN apres : {broken_after} (cible 0)")
    print(f"  Parc MP : {parc0} -> {parc1} (delta {delta:+d})  "
          f"[attendu : 0 strictement neutre]")
    print("-" * 80)
    print("Echantillon (10 premieres modifications) :")
    for cle, b, a in moves[:10]:
        print(f"  {cle:36s}  immat={b['immat']}->{a['immat']}  "
              f"lots={b['nb_lots_habitation']}->{a['nb_lots_habitation']}  "
              f"taux={b['taux']}->{a['taux']}")
    if len(moves) > 10:
        print(f"  ... (+{len(moves) - 10} autres)")
    print("=" * 80)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not propag_count:
        print("Idempotent : aucune modification.")
        return
    if delta != 0:
        print(f"ABORT : parc non-neutre (delta={delta}). "
              "Verifier la logique avant ecriture.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_propag_immat"] = (
        f"{propag_count} adresses creees par fix_rnc_bdnb_attribution.py "
        f"et fix_horsrnc_attribution.py (_bdnb_match in "
        f"{{'immat_fix','immat_horsrnc_fix'}}) repare en place : "
        "propagation numero_immatriculation + nb_lots_habitation + syndic "
        "(si manquant) + recalcul taux_rotation/classement depuis la copro "
        "liee par cle_adresse. Parc strictement neutre. Source-of-truth "
        "deja portee dans fix_rnc_bdnb_attribution.py et "
        "fix_horsrnc_attribution.py (construire_ligne enrichie). 104 cas "
        f"avant, {broken_after} apres.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
