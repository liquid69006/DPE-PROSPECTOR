"""
Correctif SURGICAL — Rattachement 6 AVENUE DE CHAMPAUBERT a LE
VILLAGE SUISSE (AA0529289, ancre 78|AVENUE|SUFFREN, ATRIUM GESTION).
Confirmation terrain user 2026-05-21.

Pattern Cambronne / re-fusion manquante (faux match make_light :
adresse orpheline sur bon bgid mais sans _fusion_auto).

Triple confirmation source-of-truth :
  - BDNB pivot bgid 2HH6-SVYC-U9D4 (parcelle 75115000DH0022, 1968,
    Resid coll) : l_libelle_adr = 13 facades BAN incluant '6 Avenue
    De Champaubert'. nb_log=233, nb_log_rnc=321 = somme AA0529289
    (320 lots) + AB8263709 (1 lot satellite).
  - BDNB rel_RNC bgid 2HH6 : AA0529289 + AB8263709 (les 2 copros
    presentes - AA0529289 est le syndicat principal, AB8263709 lot
    satellite isole mandat fini).
  - Donnees light deja en place :
    * 6|AVENUE|CHAMPAUBERT actuel = bgid 2HH6 (correct), nb_log_bdnb
      =233 (match exact AA0529289), syndic ATRIUM GESTION cadastre
      = match exact AA0529289. Seul defaut : _fusion_auto absent.
    * 78|AVENUE|SUFFREN ancre AA0529289 ATRIUM 320 lots hab, sources
      =['76|AVENUE|SUFFREN'], label '76/78 AVENUE SUFFREN'.

ANOMALIE LIGHT (corrigee par ce fix) :
  - 6|AVENUE|CHAMPAUBERT bgid OK mais orpheline (pas dans
    _fusion_auto_sources de 78 SUFFREN, pas _fusion_auto=True).
    Faux matching make_light : adresse identifiee bgid 2HH6 par GPS
    (_bdnb_match=gps) mais pas rattachee a l'ancre RNC.

Mecanisme : RE-FUSE pattern Cambronne. 6 CHAMPAUBERT recoit
_fusion_auto=True + _fusion_cible=78|AVENUE|SUFFREN. Syndic
'ATRIUM GESTION' deja present (cadastre) -> _syndic_src 'cadastre'
-> 'rnc_grp' (cohrent avec autres fused). bgid 2HH6 inchange (deja
correct). Ancre 78 SUFFREN : sources et label etendus.

Effet parc (modele renderSecteur Sec 6) :
  - bgid 2HH6 : reste a 320 lots RNC (via 78 SUFFREN + AA0529289
    dans bgRncLots, RNC autoritaire prioritaire).
  - Le 6 CHAMPAUBERT avant fix n'apportait DEJA rien a bgBdnb car
    bgid 2HH6 est en bgRncLots -> RNC prioritaire (filtre code
    'bg not in bgBdnb').
  -> Delta parc = 0 (STRICTEMENT NEUTRE), uniquement rapprochement
     visuel et cohrence de la fusion.

Ventes : aucune DVF au 6 CHAMPAUBERT (0 vlog). Aucun impact.

Source-of-truth a porter dans make_light_motte_picquet.py (hors-repo) :
  - ALIAS_RNC += { '6|AVENUE|CHAMPAUBERT': '78|AVENUE|SUFFREN' }

Bonus optionnel (PAS dans ce fix, a traiter separement) :
  - 10 facades absentes a INJECT label-only (4/8/10/12/14 CHAMPAUBERT
    + 11/13/15/17 ALASSEUR + 76B SUFFREN)
  - Correction bgid 9|RUE|ALASSEUR (ALS2 -> 2HH6, faux matching)

Cible : data/secteur_motte_picquet_light.json. Backup
.prechampaubert6.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_champaubert_6_village_suisse.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_champaubert_6_village_suisse.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prechampaubert6.bak"

ANCHOR = "78|AVENUE|SUFFREN"
IMMAT = "AA0529289"
ORPH = "6|AVENUE|CHAMPAUBERT"
NEW_LABEL = "76/78 AVENUE SUFFREN / 6 AVENUE DE CHAMPAUBERT"


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


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
    contrib = {}
    for bg in set(bgRncLots) | set(bgBdnb):
        v = (sum(bgRncLots[bg].values()) if bg in bgRncLots
             else bgBdnb.get(bg, 0))
        parc += v
        contrib[bg] = (v, "RNC" if bg in bgRncLots else "BDNB")
    return parc, contrib


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    abort = []
    da = by.get(ANCHOR)
    do = by.get(ORPH)
    cp = cbc.get(ANCHOR)
    if da is None:
        abort.append(f"ancre absente : {ANCHOR}")
    if do is None:
        abort.append(f"orphelin absent : {ORPH}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANCHOR}")
    if da and do and da.get("batiment_groupe_id") != do.get("batiment_groupe_id"):
        abort.append(f"bgid divergent ancre {da.get('batiment_groupe_id')} "
                     f"vs orphelin {do.get('batiment_groupe_id')}")
    if do and do.get("_fusion_auto") and do.get("_fusion_cible") == ANCHOR:
        abort.append(f"deja fused (idempotence)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pda = pby.get(ANCHOR)
    pdo = pby.get(ORPH)

    re_fused = False
    old_label = old_sources = None
    if not abort and pda and pdo:
        # Re-fuse orphelin
        pdo["_fusion_auto"] = True
        pdo["_fusion_cible"] = ANCHOR
        pdo["_fusion_auto_sources"] = None
        # Bascule src syndic cadastre -> rnc_grp (cohrence avec autres fused)
        if pdo.get("_syndic_src") == "cadastre" and syn_ok(pdo.get("syndic")):
            pdo["_syndic_src"] = "rnc_grp"
        # Update ancre : _fusion_auto_sources + label
        old_sources = list(pda.get("_fusion_auto_sources") or [])
        new_sources = sorted(set(old_sources + [ORPH]))
        pda["_fusion_auto_sources"] = new_sources
        old_label = pda.get("_fusion_auto_label")
        pda["_fusion_auto_label"] = NEW_LABEL
        re_fused = True

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 80)
    print(f"FIX 6 CHAMPAUBERT -> VILLAGE SUISSE - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 80)
    print(f"  ANCRE     : {ANCHOR}  copro {IMMAT} '{cp and cp.get('nom_copropriete')}'")
    print(f"  Syndic    : {(cp and cp.get('syndic')) or '-'} ({cp and cp.get('nb_lots_habitation')} lots hab)")
    print(f"  Bgid      : {da and da.get('batiment_groupe_id')}")
    print(f"  ORPHELIN  : {ORPH}  bgid={do and do.get('batiment_groupe_id')}")
    print(f"             nb_log_bdnb={do and do.get('nb_log_bdnb')} "
          f"syndic={(do and do.get('syndic')) or '-'}")
    print(f"  Action    : re-fuse {ORPH} -> {ANCHOR}")
    print(f"             _syndic_src cadastre -> rnc_grp")
    print(f"  Ancre sources : {old_sources} -> "
          f"{pda.get('_fusion_auto_sources') if pda else 'n/a'}")
    print(f"  Ancre label   : {old_label!r} -> "
          f"{pda.get('_fusion_auto_label') if pda else 'n/a'!r}")
    print("-" * 80)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) = {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc STRICTEMENT NEUTRE).")
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 80)

    if abort:
        print("\nABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("\nDRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not re_fused:
        print("\nIdempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"\nABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_champaubert_6_village_suisse"] = (
        "6 AVENUE DE CHAMPAUBERT re-fuse vers 78|AVENUE|SUFFREN (ancre "
        f"VILLAGE SUISSE AA0529289 ATRIUM GESTION, 320 lots hab). "
        "Confirmation terrain user 2026-05-21. Pattern Cambronne / re-"
        "fusion manquante : 6 CHAMPAUBERT etait orpheline (bgid 2HH6-"
        "SVYC-U9D4 correct + nb_log_bdnb=233 match exact + syndic ATRIUM "
        "GESTION cadastre match exact) mais sans _fusion_auto. Triple "
        "confirmation : BDNB pivot bgid 2HH6 l_libelle_adr inclut '6 "
        "Avenue De Champaubert' (13 facades VILLAGE SUISSE) + BDNB rel_"
        "RNC 2HH6 = AA0529289 + AB8263709 (lot satellite mandat fini) + "
        "nb_log_bdnb 233 = match AA0529289 233. _syndic_src cadastre -> "
        "rnc_grp. Ancre 78 SUFFREN _fusion_auto_sources passe ['76 "
        "SUFFREN'] -> ['6 CHAMPAUBERT', '76 SUFFREN'] + label '76/78 "
        f"AVENUE SUFFREN' -> '{NEW_LABEL}'. Parc {parc0}->{parc1} "
        "STRICTEMENT NEUTRE (bgid 2HH6 deja en bgRncLots via 78 SUFFREN "
        "+ AA0529289, RNC autoritaire prioritaire PIPELINE Sec 6 ; le 6 "
        "CHAMPAUBERT avant fix n'apportait deja rien a bgBdnb car bgid "
        "2HH6 deja occupe par RNC). 10 facades absentes (4/8/10/12/14 "
        "CHAMPAUBERT + 11/13/15/17 ALASSEUR + 76B SUFFREN) + correction "
        "bgid 9 ALASSEUR (ALS2 -> 2HH6) a traiter separement (bonus). "
        "ALIAS_RNC a porter : {'6|AVENUE|CHAMPAUBERT': '78|AVENUE|"
        "SUFFREN'} dans make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\nSauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
