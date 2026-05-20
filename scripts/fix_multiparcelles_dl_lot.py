"""
Lot RE-POINT pattern Fremicourt/Cambronne pour les 7 copros DL haute
priorite (vlog >= 4) identifiees par data/audit_copros_multiparcelles.md.

Skip AB2926236 SAINT GERMAIN -> 260 PAUL BERT (suspect : nb_log_bdnb=1,
probablement local commercial pas copro, cf. limites audit §3).

Mecanisme par cas : pour chaque (ancre, orphelins[], immat) :
  - VERIF gardes : ancre existe, immat correct sur ancre, orphelins
    sans autre immat conflictuel, orphelins fusionnes vers une autre
    cible -> ABORT, copro ancre non fusionnee elle-meme.
  - DETECTION etat :
    * IDEMPOTENT si tous orphelins ont deja _fa=True / _fc=ancre.
    * Sinon RE-POINT pattern Fremicourt (adoption MIRROR bgid +
      _fusion_auto=True + _fusion_cible=ancre + chaine absorbee).
  - PARC : calcul avant/apres global. Si bgid orph identique a
    ancre = parc-neutre direct ; si different = dedup (bucket bgBdnb
    de l'orph disparait si plus d'adresse non-fusee dessus).

Cible : data/secteur_dauphine_lacassagne_light.json. Backup
.premultidl.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_multiparcelles_dl_lot.py        # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_multiparcelles_dl_lot.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.premultidl.bak"

# (immat, ancre_cle, [orphelins_cles])
CASES = [
    ("AA0157016", "11|RUE|DAHLIAS",           ["13|RUE|DAHLIAS"]),
    ("AA4417416", "10|AVENUE|LACASSAGNE",     ["12|AVENUE|LACASSAGNE"]),
    ("AB7739527", "42|AVENUE|LACASSAGNE",     ["44|AVENUE|LACASSAGNE"]),
    ("AB7363229", "50|RUE|DAUPHINE",          ["52|RUE|DAUPHINE", "54|RUE|DAUPHINE"]),
    ("AB8349037", "9|RUE|ROGER BRECHAN",      ["11|RUE|ROGER BRECHAN"]),
    ("AC9350984", "89|RUE|DAUPHINE",          ["93|RUE|DAUPHINE"]),
    ("AH7871353", "24|RUE|CLAUDIUS PIONCHON",
     ["26|RUE|CLAUDIUS PIONCHON", "28|RUE|CLAUDIUS PIONCHON"]),
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

    # Analyse globale par cas
    abort_global = []
    case_status = []        # par cas : etat actuel
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

        # Etat des orphelins
        orph_states = []     # par orph : (cle, statut, action)
        applies = []         # orphs a re-pointer dans patched
        for o in orphs:
            s = by.get(o)
            if s is None:
                orph_states.append({"cle": o, "statut": "ABSENT",
                                    "action": "skip"})
                case_aborts.append(f"orph {o} absent du light")
                continue
            # collisions immat
            if s.get("numero_immatriculation") \
                    and s["numero_immatriculation"] != immat:
                case_aborts.append(
                    f"orph {o} porte autre immat : "
                    f"{s['numero_immatriculation']}")
                orph_states.append({"cle": o, "statut": "AUTRE-IMMAT",
                                    "action": "skip"})
                continue
            # idempotence : deja fuse vers la bonne ancre
            if s.get("_fusion_auto") and s.get("_fusion_cible") == anc:
                orph_states.append({
                    "cle": o, "statut": "DEJA-FUSE-OK",
                    "action": "noop",
                    "bgid_orph": s.get("batiment_groupe_id"),
                    "vlog": s.get("nb_ventes_logement") or 0,
                    "nb_log_bdnb": s.get("nb_log_bdnb"),
                })
                continue
            # fuse vers AUTRE cible : conflit
            if s.get("_fusion_auto") and s.get("_fusion_cible") \
                    and s.get("_fusion_cible") != anc:
                case_aborts.append(
                    f"orph {o} fuse vers {s.get('_fusion_cible')} "
                    f"(!= {anc})")
                orph_states.append({"cle": o, "statut": "FUSE-CONFLIT",
                                    "action": "skip"})
                continue
            # cas a appliquer
            orph_states.append({
                "cle": o, "statut": "A-RE-POINTER",
                "action": "apply",
                "bgid_orph": s.get("batiment_groupe_id"),
                "vlog": s.get("nb_ventes_logement") or 0,
                "nb_log_bdnb": s.get("nb_log_bdnb"),
            })
            applies.append(o)

        # Appliquer dans patched
        moves_applied = []
        if not case_aborts and pda is not None:
            for o in applies:
                s = pby.get(o)
                if s is None:
                    continue
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
            if moves_applied:
                cur = list(pda.get("_fusion_auto_sources") or [])
                pda["_fusion_auto_sources"] = \
                    sorted(set(cur + moves_applied))
                pda.setdefault("_fusion_auto_label", None)

        if case_aborts:
            abort_global.extend(f"[{immat}] " + a for a in case_aborts)

        case_status.append({
            "immat": immat,
            "ancre": anc,
            "copro_nom": cp.get("nom_copropriete") if cp else "—",
            "copro_nlots": cp.get("nb_lots_habitation") if cp else None,
            "syndic": cp.get("syndic") if cp else None,
            "orph_states": orph_states,
            "moves_applied": moves_applied,
            "aborts": case_aborts,
        })

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    # ─── Rapport ───
    print("=" * 76)
    print(f"FIX MULTI-PARCELLES DL — LOT 7 CAS — "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 76)
    print(f"  Total cas : {len(CASES)}")
    cas_apply = sum(1 for c in case_status if c["moves_applied"])
    cas_noop = sum(1 for c in case_status
                   if not c["moves_applied"] and not c["aborts"])
    cas_abort = sum(1 for c in case_status if c["aborts"])
    print(f"  A appliquer : {cas_apply}  ·  Idempotent : {cas_noop} "
          f"·  Aborts : {cas_abort}")
    print()
    print(f"{'#':>2}  {'immat':10s}  {'ancre':32s}  "
          f"{'nlots':>5}  syndic")
    for i, c in enumerate(case_status, 1):
        print(f" {i}. {c['immat']:10s}  {c['ancre']:32s}  "
              f"{c['copro_nlots'] or '—':>5}  "
              f"{(c['syndic'] or '—')[:30]}")
        for o in c["orph_states"]:
            bg_marker = ""
            if o.get("bgid_orph"):
                # marquer si meme bgid que ancre
                anc_bg = by.get(c["ancre"], {}).get("batiment_groupe_id")
                if o["bgid_orph"] == anc_bg:
                    bg_marker = " [bgid=ancre]"
                else:
                    bg_marker = f" [bgid divergent]"
            extra = ""
            if "vlog" in o:
                extra = (f" vlog={o['vlog']} "
                         f"nb_log_bdnb={o['nb_log_bdnb']}")
            print(f"      - {o['cle']:32s} {o['statut']:14s} "
                  f"action={o['action']:5s}{bg_marker}{extra}")
        if c["aborts"]:
            for a in c["aborts"]:
                print(f"      ! ABORT: {a}")
    print()
    print("-" * 76)
    # Contrib changes
    bg_changes = []
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "—"))
        v1, k1 = contrib1.get(bg, (0, "—"))
        if v0 != v1 or k0 != k1:
            bg_changes.append((bg, v0, k0, v1, k1))
    if bg_changes:
        print("Bgids impactes :")
        for bg, v0, k0, v1, k1 in bg_changes:
            print(f"  {bg}: {v0} ({k0}) -> {v1} ({k1}) = "
                  f"{v1 - v0:+d}")
    else:
        print("Aucun bgid impacte (parc strictement neutre).")
    print(f"Parc DL : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 76)

    if abort_global:
        print("\nABORTS :")
        for a in abort_global:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if cas_apply == 0:
        print("Idempotent : tous les cas deja fusionnes, "
              "aucun fichier modifie.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    summary = "; ".join(
        f"{c['immat']}({len(c['moves_applied'])})"
        for c in case_status if c["moves_applied"])
    meta["_correctif_multiparcelles_dl_lot"] = (
        f"Lot multi-parcelles DL : {cas_apply} cas re-points "
        f"(orphelin -> ancre RNC declaree par ref_cadastrale_2/3, "
        "cf. data/audit_copros_multiparcelles.md). Pattern "
        "Fremicourt/Cambronne. Cas applique : " + summary +
        f". Parc {parc0}->{parc1} ({delta:+d}).")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
