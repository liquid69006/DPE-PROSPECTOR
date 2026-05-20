"""
Correctif COSMETIQUE CAS A — Etiquetage 83 BD GRENELLE + INJECT
32/34 RUE DUPLEIX label-only. Confirmation terrain user 2026-05-20.

Pattern ETIQUETAGE pur (Clouet/Garibaldi/Violet) + INJECT label-only
(variante Suffren label-only). Aucune copro RNC active sur ce bati.

Contexte :
  - Bati BDNB bgid 5KST-PABL-LAUP (parcelle 75115000DJ0019, 1910,
    31 nb_log_bdnb, Residentiel collectif) couvre 3 facades BAN
    confirmees par BDNB pivot : 83 BD GRENELLE, 32 RUE DUPLEIX,
    34 RUE DUPLEIX (libelle_adr_principale_ban = '83 Grenelle').
  - 0 copro RNC active (BDNB rel_RNC bgid 5KST = 0 rows ; RNC live
    tabular-api 3ea8e2c3 par voie '83 grenelle'/'32 dupleix'/'34
    dupleix' + ref_cad DJ/0019 = 0 hit). Probable mono-propriete /
    foncière institutionnelle (vente bloc DVF 30/04/2021 6 200 000 EUR
    sur 14 lots = 13 appartements + 1 local commercial 170 m²).
  - Label actuel '83/85 BOULEVARD GRENELLE' est INCORRECT : le 85
    GRENELLE est sur le bati VOISIN S543 (Tertiaire, parcelle DH/01)
    selon BDNB pivot+rel_adresse. Le 85 sera traite en CAS B
    (re-point bgid 5KST -> S543).

Actions de ce correctif (parc-neutre, cosmetique) :
  1. INJECT `32|RUE|DUPLEIX` entry minimaliste fused vers 83 (bgid
     5KST clone MIRROR, BAN cle 75115_3006_00032).
  2. INJECT `34|RUE|DUPLEIX` entry minimaliste fused vers 83 (BAN
     cle 75115_3006_00034).
  3. Update `_fusion_auto_label` 83 : '83/85 BOULEVARD GRENELLE'
     -> '83 BD GRENELLE / 32-34 RUE DUPLEIX' (le 85 retire au
     CAS B). Pour eviter conflit avec CAS B, on conserve le 85
     dans _fusion_auto_sources pour le moment (CAS B le retirera).
  4. Update `_fusion_auto_sources` 83 : ajout 32 + 34 DUPLEIX.

Effet parc (modele renderSecteur Sec 6) :
  - bgid 5KST : reste a 31 nb_log_bdnb (via 83 GRENELLE ancre,
    Residentiel collectif, pas de copro -> bgBdnb=31). 32 + 34
    DUPLEIX injectes sont fused -> exclus de bgBdnb. Inchange.
  - Delta parc = 0 (STRICTEMENT NEUTRE).

Aucune vente DVF aux 32/34 DUPLEIX (verifie). Filet de securite si
mutations futures.

Source-of-truth a porter dans make_light_motte_picquet.py :
  - ALIAS_RNC += { '32|RUE|DUPLEIX': '83|BOULEVARD|GRENELLE',
                    '34|RUE|DUPLEIX': '83|BOULEVARD|GRENELLE' }
  - Note : 85|BOULEVARD|GRENELLE doit etre EXCLU des aliases vers
    83 (le 85 appartient au bati VOISIN S543 - cf CAS B).

Cible : data/secteur_motte_picquet_light.json. Backup
.pregrendupA.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_grenelle_dupleix_casA.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_grenelle_dupleix_casA.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.pregrendupA.bak"

ANCHOR = "83|BOULEVARD|GRENELLE"
NEW_CLES = [("32|RUE|DUPLEIX", "32 RUE DUPLEIX"),
            ("34|RUE|DUPLEIX", "34 RUE DUPLEIX")]
LABEL = "83 BD GRENELLE / 32-34 RUE DUPLEIX"


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


def build_inject(new_cle, new_adr, anchor_entry):
    """Entry adresses[] minimaliste clone du bati ancre (bgid 5KST)."""
    return {
        "cle": new_cle,
        "adresse": new_adr,
        "longitude": anchor_entry.get("longitude"),
        "latitude": anchor_entry.get("latitude"),
        "code_iris": anchor_entry.get("code_iris"),
        "_coord_source": "inject_label_only_grendup",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": None,
        "_syndic_src": None,
        "numero_immatriculation": None,
        "nb_lots_habitation": None,
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation": 0.0,
        "classement_rotation": "Fige",
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Figé",
        "nb_log_bdnb": anchor_entry.get("nb_log_bdnb"),
        "annee_construction": anchor_entry.get("annee_construction"),
        "classe_dpe": anchor_entry.get("classe_dpe"),
        "type_batiment": anchor_entry.get("type_batiment"),
        "type_chauffage": anchor_entry.get("type_chauffage"),
        "batiment_groupe_id": anchor_entry.get("batiment_groupe_id"),
        "_bdnb_match": "ban_inject_label_only",
        "_taux_logement_src": "filtre_habitation",
        "usage_principal_bdnb": anchor_entry.get("usage_principal_bdnb"),
        "_usage_bdnb_src": anchor_entry.get("_usage_bdnb_src"),
        "_fusion_auto": True,
        "_fusion_cible": ANCHOR,
        "_fusion_auto_sources": None,
    }


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}

    abort = []
    da = by.get(ANCHOR)
    if da is None:
        abort.append(f"ancre absente : {ANCHOR}")
    if da and da.get("_fusion_auto") and da.get("_fusion_cible"):
        abort.append(f"ancre {ANCHOR} elle-meme fusionnee")
    for cle, _ in NEW_CLES:
        if by.get(cle) is not None:
            abort.append(f"entry {cle} deja presente (idempotence)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pda = pby.get(ANCHOR)

    injected = []
    label_changed = None
    if not abort and pda is not None:
        for cle, adr in NEW_CLES:
            new_entry = build_inject(cle, adr, pda)
            patched["adresses"].append(new_entry)
            pby[cle] = new_entry
            injected.append(cle)
        cur = list(pda.get("_fusion_auto_sources") or [])
        for cle in injected:
            if cle not in cur:
                cur.append(cle)
        pda["_fusion_auto_sources"] = sorted(set(cur))
        old_label = pda.get("_fusion_auto_label")
        pda["_fusion_auto_label"] = LABEL
        label_changed = (old_label, LABEL)

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX GRENELLE/DUPLEIX CAS A (etiquetage 83 + INJECT 32/34) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCRE         : {ANCHOR}  bgid={da and da.get('batiment_groupe_id')}")
    print(f"  Copro RNC     : aucune (0 hit RNC live, 0 rel_RNC BDNB)")
    print(f"  INJECT        : {injected}")
    if label_changed:
        print(f"  Label updated : {label_changed[0]!r} -> {label_changed[1]!r}")
    if pda:
        print(f"  _fusion_auto_sources : {da.get('_fusion_auto_sources') or []} -> "
              f"{pda.get('_fusion_auto_sources') or []}")
        print(f"    (Note : '85|BOULEVARD|GRENELLE' sera RETIRE par le CAS B "
              "= bgid different)")
    print("-" * 78)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc STRICTEMENT NEUTRE).")
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 78)

    if abort:
        print("ABORT (gardes) :")
        for x in abort:
            print("  - " + x)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not injected:
        print("Idempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_grenelle_dupleix_casA"] = (
        "CAS A : etiquetage bati 83 GRENELLE + INJECT 32/34 RUE "
        "DUPLEIX label-only (BAN 75115_3006_00032 + _00034). Bati "
        "BDNB 5KST-PABL-LAUP (parcelle 75115000DJ0019, 1910, 31 "
        "nb_log_bdnb, Residentiel collectif) couvre 3 facades BAN "
        "(BDNB pivot l_libelle_adr). 0 copro RNC active (vente bloc "
        "DVF 30/04/2021 6.2M EUR sur 14 lots = mono-propriete/"
        "fonciere). Pattern ETIQUETAGE Clouet/Garibaldi + INJECT "
        "label-only. Label '83/85 BOULEVARD GRENELLE' -> "
        f"'{LABEL}'. Parc {parc0}->{parc1} STRICTEMENT NEUTRE "
        "(32/34 DUPLEIX fused, exclus de bgBdnb). ALIAS_RNC a "
        "porter : {'32|RUE|DUPLEIX': '83|BOULEVARD|GRENELLE', "
        "'34|RUE|DUPLEIX': '83|BOULEVARD|GRENELLE'} dans "
        "make_light_motte_picquet.py. Le 85 GRENELLE sera RETIRE "
        "du _fusion_auto_sources par CAS B (re-point bgid 5KST -> "
        "S543 Tertiaire).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+{len(injected)} entries injectees, "
          "label update)")


if __name__ == "__main__":
    main()
