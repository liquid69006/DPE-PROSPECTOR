"""
Lot 2 RE-POINT pattern Fremicourt/Cambronne + propagation de chaine
(pattern fix_pivot_bdnb_lot) pour les cas restants vlog>=2 de
data/audit_copros_multiparcelles.md v2 — apres exclusion :
  - SKIP AB2926236 SAINT GERMAIN (260 PAUL BERT, suspect commercial
    nb_log_bdnb=1, cf. limites audit §3).
  - SKIP AB4859047 LE PARC SISLEY (ancre 74|RUE|DAUPHINE ABSENTE
    d'adresses[] - necessite injection prealable pattern Suffren,
    a traiter dans un fix dedie).

Cas applique :
  - AB4738928 SDC LE CARRE DES LYS (76 lots, FONCIA SAINT LOUIS) :
    23|RUE|ST MAXIMIN (ancre, bgid RBD4) <- 5|RUE|MARCEL PEHU (bgid
    GMWN divergent, _fas=['3|MARCEL PEHU'] = chaine a propager).
    Effet : dedup bgid GMWN entier (5 + 3 fuses), parc -32 (lots RNC
    autoritaires sur GMWN, PIPELINE Sec 6). 4 v_log relocalises depuis
    5 + 4 v_log absorbes via chaine 3 = 8 v_log total sous AB4738928.

  - AD5268305 BRICKS 1 (98 lots, FONCIA LYON) :
    '20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE' (ancre, cle composite
    issue de l'adresse RNC '20-20 BIS AVENUE LACASSAGNE 22 AVENUE
    LACASSAGNE', bgid NHQQ) <- 20|AVENUE|LACASSAGNE (bgid NHQQ =
    ancre, _fas=['22|LACASSAGNE'] = chaine a propager). 22|LACASSAGNE
    est sur bgid divergent 9DFR mais voisin de 21|LACASSAGNE
    (autre copro non-fusee). Effet : parc-neutre (NHQQ deja sature
    par AD5268305 cote RNC, 9DFR conserve 21 voisin). 2 v_log (de 22
    deja absorbees dans 20) relocalisees sous AD5268305.

Triple confirmation source-of-truth (audit data/audit_copros_multi-
parcelles.md, RNC ref_cadastrale_2/3, BDNB pivot l_libelle_adr).

Cible : data/secteur_dauphine_lacassagne_light.json. Backup
.premultidl2.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_multiparcelles_dl_lot2.py        # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_multiparcelles_dl_lot2.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.premultidl2.bak"

# (immat, ancre_cle, [orphelins_cles])
CASES = [
    ("AB4738928", "23|RUE|ST MAXIMIN", ["5|RUE|MARCEL PEHU"]),
    ("AD5268305", "20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE",
     ["20|AVENUE|LACASSAGNE"]),
]

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


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}
    # chaine inverse : pour chaque adresse, qui pointe vers elle ?
    chain_in = {}
    for a in light["adresses"]:
        if a.get("_fusion_cible"):
            chain_in.setdefault(a["_fusion_cible"], []).append(a["cle"])

    abort_global = []
    case_status = []
    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    for immat, anc, orphs in CASES:
        da = by.get(anc)
        cp = cbc.get(anc)
        pda = pby.get(anc)
        case_aborts = []

        if da is None:
            case_aborts.append(f"ancre absente : {anc}")
        if cp is None or cp.get("numero_immatriculation") != immat:
            case_aborts.append(
                f"copro {immat} introuvable sur {anc} (got "
                f"{cp and cp.get('numero_immatriculation')})")
        if da and da.get("_fusion_auto") and da.get("_fusion_cible"):
            case_aborts.append(
                f"ancre {anc} fusionnee elle-meme "
                f"(-> {da.get('_fusion_cible')})")

        actions = []     # par orph : statut + chain
        for o in orphs:
            s = by.get(o)
            if s is None:
                actions.append({"cle": o, "statut": "ABSENT",
                                "chain": []})
                case_aborts.append(f"orph {o} absent du light")
                continue
            if s.get("numero_immatriculation") \
                    and s["numero_immatriculation"] != immat:
                case_aborts.append(
                    f"orph {o} porte autre immat : "
                    f"{s['numero_immatriculation']}")
                actions.append({"cle": o, "statut": "AUTRE-IMMAT",
                                "chain": []})
                continue
            # idempotent ?
            if s.get("_fusion_auto") and s.get("_fusion_cible") == anc:
                actions.append({"cle": o, "statut": "DEJA-FUSE-OK",
                                "chain": []})
                continue
            # fuse vers autre cible => conflit (sauf si la cible est
            # elle-meme dans cette chaine, on absorbera)
            if s.get("_fusion_auto") and s.get("_fusion_cible") \
                    and s.get("_fusion_cible") != anc:
                # ok si la cible n'est pas un autre orph valide
                tgt = s.get("_fusion_cible")
                if tgt not in orphs and tgt != anc:
                    case_aborts.append(
                        f"orph {o} fuse vers {tgt} (collision)")
                    actions.append({"cle": o, "statut": "FUSE-CONFLIT",
                                    "chain": []})
                    continue
            # chaine a propager : tout ce qui pointe DANS l'orph
            ch = list(chain_in.get(o, []))
            actions.append({
                "cle": o, "statut": "A-RE-POINTER",
                "chain": ch,
                "bgid_orph": s.get("batiment_groupe_id"),
                "vlog_orph": s.get("nb_ventes_logement") or 0,
                "vtot_orph": s.get("nb_ventes_total") or 0,
                "nb_log_bdnb": s.get("nb_log_bdnb"),
            })

        # Appliquer dans patched
        moves_applied = []
        chain_applied = []
        if not case_aborts and pda is not None:
            for act in actions:
                if act["statut"] != "A-RE-POINTER":
                    continue
                o = act["cle"]
                s = pby.get(o)
                if s is None:
                    continue
                # adoption MIRROR de l'ancre
                for k in MIRROR:
                    s[k] = pda.get(k)
                s["_bdnb_match"] = "immat"
                if syn_ok(pda.get("syndic")) \
                        and not syn_ok(s.get("syndic")):
                    s["syndic"] = pda.get("syndic")
                    s["_syndic_src"] = \
                        (pda.get("_syndic_src") or "rnc") + "_grp"
                s["_fusion_auto"] = True
                s["_fusion_cible"] = anc
                s["_fusion_auto_sources"] = None
                moves_applied.append(o)
                # propager la chaine : chaque adresse qui pointait
                # dans o -> re-pointer vers anc
                for cx in act["chain"]:
                    x = pby.get(cx)
                    if x is None:
                        continue
                    x["_fusion_auto"] = True
                    x["_fusion_cible"] = anc
                    x["_fusion_auto_sources"] = None
                    chain_applied.append(cx)
            if moves_applied or chain_applied:
                cur = list(pda.get("_fusion_auto_sources") or [])
                new = sorted(set(cur + moves_applied + chain_applied))
                pda["_fusion_auto_sources"] = new
                pda.setdefault("_fusion_auto_label", None)

        if case_aborts:
            abort_global.extend(f"[{immat}] " + a for a in case_aborts)

        case_status.append({
            "immat": immat,
            "ancre": anc,
            "copro_nom": cp.get("nom_copropriete") if cp else "—",
            "copro_nlots": cp.get("nb_lots_habitation") if cp else None,
            "syndic": cp.get("syndic") if cp else None,
            "actions": actions,
            "moves_applied": moves_applied,
            "chain_applied": chain_applied,
            "aborts": case_aborts,
        })

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    # ─── Rapport ───
    print("=" * 78)
    print(f"FIX MULTI-PARCELLES DL LOT 2 — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    print(f"  Cas inclus : {len(CASES)}  "
          f"(skip AB4859047 ancre absente + AB2926236 commercial)")
    n_apply = sum(1 for c in case_status if c["moves_applied"])
    n_chain = sum(len(c["chain_applied"]) for c in case_status)
    n_abort = sum(1 for c in case_status if c["aborts"])
    print(f"  A appliquer : {n_apply}  ·  Chains absorbees : {n_chain}"
          f"  ·  Aborts : {n_abort}")
    print()
    for i, c in enumerate(case_status, 1):
        print(f"  {i}. {c['immat']:10s}  ancre={c['ancre']!r}")
        print(f"        nom={c['copro_nom']!r}  nlots={c['copro_nlots']}"
              f"  syndic={c['syndic']!r}")
        for act in c["actions"]:
            extra = ""
            if act["statut"] == "A-RE-POINTER":
                anc_bg = by.get(c["ancre"], {}).get("batiment_groupe_id")
                bg_mark = ("[bgid=ancre]" if act["bgid_orph"] == anc_bg
                           else f"[bgid divergent: {act['bgid_orph']}]")
                extra = (f"  vlog={act['vlog_orph']}/vtot={act['vtot_orph']}"
                         f"  nb_log_bdnb={act['nb_log_bdnb']}  "
                         f"{bg_mark}")
                if act["chain"]:
                    extra += f"\n          chain a propager : {act['chain']}"
            print(f"     -> {act['cle']:30s}  {act['statut']:14s}{extra}")
        if c["aborts"]:
            for a in c["aborts"]:
                print(f"     ! ABORT: {a}")
    print()
    print("-" * 78)
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "—"))
        v1, k1 = contrib1.get(bg, (0, "—"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc strictement neutre).")
    print(f"Parc DL : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 78)

    if abort_global:
        print("\nABORTS :")
        for a in abort_global:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if n_apply == 0:
        print("Idempotent : aucun re-point a appliquer.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    summary = "; ".join(
        f"{c['immat']}({len(c['moves_applied'])}+chain="
        f"{len(c['chain_applied'])})"
        for c in case_status if c["moves_applied"])
    meta["_correctif_multiparcelles_dl_lot2"] = (
        f"Lot 2 multi-parcelles DL : {n_apply} cas re-points + "
        f"{n_chain} chains absorbees (orphelins -> ancre RNC declaree "
        "par ref_cadastrale_2/3, cf. audit_copros_multiparcelles.md "
        f"v2). Pattern Fremicourt/Cambronne + propagation chaine "
        "(pattern fix_pivot_bdnb_lot). Skip AB4859047 (ancre 74 "
        "DAUPHINE absente) + AB2926236 (suspect commercial). Cas : "
        + summary + f". Parc {parc0}->{parc1} ({delta:+d}).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
