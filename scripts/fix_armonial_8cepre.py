"""
Correctif COMPLEMENT — Injection `8|RUE|CEPRE` dans ARMONIAL I
(AA0646265). Confirmation terrain user 2026-05-20 (re-confirmation
d'une session anterieure) : `2/4/6/8 RUE CEPRE + 20 RUE MIOLLIS` =
ARMONIAL I.

Contexte (fix_armonial_pair_cepre.py applique dans commit anterieur) :
  - 2/4/6 RUE CEPRE et 20 MIOLLIS deja fused vers
    16|BOULEVARD|GARIBALDI (AA0646265, 592 lots hab, ancre LJRN).
  - 8|RUE|CEPRE explicitement laisse de cote : 'ABSENT (pas de DVF,
    juste BAN/BDNB) -> traite au niveau source-of-truth pour future
    regen'. ALIAS_RNC porte dans make_light_motte_picquet.py.

Ce script COMPLEMENTAIRE injecte le 8|RUE|CEPRE comme entry
adresses[] minimaliste pour visibilite terrain immediate (sans
attendre la prochaine regen).

Sources de verite :
  - BAN : 8 Rue Cepre 75015 Paris -> cle_interop 75115_1646_00008
    (existence batiment 4e numero pair RUE CEPRE confirmee).
  - RNC AA0646265 ARMONIAL I : nb_compl=14 (open data tronque a 3
    slots, 11 cachees) -> 8 CEPRE fait partie des adresses cachees.
  - BDNB pivot LJRN-ABEM-2VT5 (= bgid ancre ARMONIAL) :
    l_libelle_adr ne mentionne pas explicitement 8 CEPRE (BAN
    rel_adresse limite a 10 lignes API), mais les 2/4/6 CEPRE deja
    fused via _bdnb_match=immat (decision pattern ARMONIAL : le
    grand ensemble couvre les 4 numeros pair Cepre).

Mecanisme : INJECT_LABEL_ONLY (variante pattern Suffren label-only).
Entry minimaliste sans MAJIC/DVF/RNC, _fusion_auto=True _fusion_cible
=16|BOULEVARD|GARIBALDI, adoption MIRROR du bati LJRN (bgid + champs
BDNB autoritatifs depuis l'ancre).

Effet parc attendu : STRICTEMENT NEUTRE.
  - bgid LJRN : deja contribue 592 (RNC AA0646265 via 16 GARIBALDI),
    inchange. Le 8 CEPRE injecte est fused -> exclu de bgBdnb.
  - Aucun autre bgid touche.
  -> Delta parc = 0.

Aucune vente DVF au 8 CEPRE -> aucune mutation relocalisee. Si une
future vente apparait au 8 CEPRE, elle sera correctement routee vers
AA0646265 ARMONIAL I.

Source-of-truth a porter (deja documente par commit anterieur) :
  - ALIAS_RNC += { '8|RUE|CEPRE': '16|BOULEVARD|GARIBALDI' } dans
    make_light_motte_picquet.py (idempotent avec fix_armonial_pair).

Cible : data/secteur_motte_picquet_light.json. Backup
.prearmonial3.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_armonial_8cepre.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_armonial_8cepre.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prearmonial3.bak"

ANCHOR = "16|BOULEVARD|GARIBALDI"
IMMAT = "AA0646265"
NEW_CLE = "8|RUE|CEPRE"

# Adoption MIRROR du bati LJRN (clone champs BDNB depuis l'ancre)
MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


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


def build_inject_entry(anchor_entry):
    """Construit l'entry minimaliste 8|RUE|CEPRE clone du bati LJRN."""
    return {
        "cle": NEW_CLE,
        "adresse": "8 RUE CEPRE",
        # Coordonnees : clone ancre (decalage negligeable a l'echelle
        # du grand ensemble ARMONIAL I)
        "longitude": anchor_entry.get("longitude"),
        "latitude": anchor_entry.get("latitude"),
        "code_iris": anchor_entry.get("code_iris"),
        "_coord_source": "inject_label_only_armonial",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": anchor_entry.get("syndic"),
        "_syndic_src": (anchor_entry.get("_syndic_src") or "rnc")
                       + "_grp",
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
        "_bdnb_match": "immat_inject_label_only",
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
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    abort = []
    da = by.get(ANCHOR)
    cp = cbc.get(ANCHOR)
    if da is None:
        abort.append(f"ancre absente : {ANCHOR}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANCHOR} "
                     f"(got {cp and cp.get('numero_immatriculation')})")
    if by.get(NEW_CLE) is not None:
        abort.append(f"entry {NEW_CLE} deja presente (diagnostic "
                     "obsolete, idempotence)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pda = pby.get(ANCHOR)

    inject_done = False
    if not abort and pda is not None:
        new_entry = build_inject_entry(pda)
        patched["adresses"].append(new_entry)
        pby[NEW_CLE] = new_entry
        # ancre absorbe la nouvelle source
        cur = list(pda.get("_fusion_auto_sources") or [])
        if NEW_CLE not in cur:
            cur.append(NEW_CLE)
            pda["_fusion_auto_sources"] = sorted(set(cur))
        inject_done = True

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 78)
    print(f"FIX ARMONIAL I - inject 8|RUE|CEPRE - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  ANCRE   : {ANCHOR}  copro {IMMAT} ARMONIAL I")
    print(f"  Lots hab: {cp and cp.get('nb_lots_habitation')}")
    print(f"  Syndic  : {(cp and cp.get('syndic')) or '-'}")
    print(f"  Bgid    : {da and da.get('batiment_groupe_id')}")
    print(f"  Action  : INJECT {NEW_CLE} (entry minimaliste, fused -> "
          "ANCRE, parc-neutre)")
    print(f"  Inject done : {inject_done}")
    if inject_done:
        before_sources = (da.get("_fusion_auto_sources") or [])
        after_sources = (pda.get("_fusion_auto_sources") or [])
        print(f"  _fusion_auto_sources : {len(before_sources)} -> "
              f"{len(after_sources)} (ajout '{NEW_CLE}')")
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
    if not inject_done:
        print("ABORT : aucune injection appliquee.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_armonial_8cepre"] = (
        f"Complement ARMONIAL I (AA0646265, 592 lots) : injection "
        f"{NEW_CLE} comme entry adresses[] minimaliste, fused -> "
        f"{ANCHOR}, adoption MIRROR depuis l'ancre (bgid LJRN, "
        "Tertiaire 1976). Pattern INJECT_LABEL_ONLY (variante "
        "Suffren label-only). 8 CEPRE etait explicitement laisse de "
        "cote par fix_armonial_pair_cepre.py (commit anterieur) "
        "comme 'absent light, traite source-of-truth' ; cette "
        "injection donne visibilite terrain immediate sans attendre "
        "la prochaine regen. BAN confirme 75115_1646_00008. Aucune "
        "DVF au 8 CEPRE -> 0 vente relocalisee. Parc "
        f"{parc0}->{parc1} (STRICTEMENT NEUTRE) car bgid LJRN deja "
        "attribue a ARMONIAL via immat (PIPELINE Sec 6 RNC "
        "prioritaire). Source-of-truth a porter : ALIAS_RNC += "
        "{'8|RUE|CEPRE': '16|BOULEVARD|GARIBALDI'} dans make_light_"
        "motte_picquet.py (idempotent avec fix_armonial_pair).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (+1 entry injectee)")


if __name__ == "__main__":
    main()
