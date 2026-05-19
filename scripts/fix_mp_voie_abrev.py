"""
Correctif SURGICAL — Motte-Picquet : 5 adresses DVF hors-RNC dont la
CLE abrege la voie (CAPT->CAPITAINE, GAL->GENERAL), non appariees au
RNC par make_light (jointure exacte cle_adresse / ALIAS_RNC, sans
normalisation). Copro PROUVEE immatriculee, presente au snapshot,
ancre rendue (audit data/audit_orphelines_bdnb_motte.md, 2026-05-19).

Mecanisme = ALIAS_RNC "miroir bgid" (A2, cf. fix_dupleix_phantom /
fix_mp_cibles_horsrnc A2) : la cle abregee adopte bgid/usage/bdnb de
l'ancre copro puis _fusion_auto -> ancre. Ventes relocalisees au
rendu, sortie des "hors-RNC actifs". Parc : modele renderSecteur §6
(dedup bg:bgid, lots RNC prioritaires) -> delta MESURE et explicite
(souvent 0 : le bgid GPS aveugle porte deja une copro RNC soeur qui
domine ; sinon retrait d'un DOUBLON BDNB, jamais une perte).

DEPENDANCES (chaine de fusion) : 4 des 5 cibles ont un fantome
auto-fusionne DANS elles ; le deplacer orphelinerait ce fantome
(_fusion_cible pointant une adresse elle-meme fusionnee). Chaque
fantome est donc RE-POINTE individuellement (PIPELINE §9.5) vers SA
copro reelle :
  1|RUE|CAPT SCOTT (8 v_log) -> 1|RUE|CAPITAINE SCOTT AF6894638
     (copro PROPRE, 27 lots — surtout PAS 3|CAPITAINE) ;
  5|RUE|GAL DE CASTELNAU (0 v) -> 5|RUE|GENERAL DE CASTELNAU
     AC0121202 (copro propre, 20 lots) ;
  6|RUE|GAL DE CASTELNAU (0 v) -> 4|RUE|GENERAL DE CASTELNAU
     (pas de copro propre, meme bgid que la cible 4) ;
  12|RUE|ALASSEUR (0 v) -> 8|RUE|GENERAL DE LARMINAT (pas de copro
     propre, angle/meme bgid que la cible 8).

Source-of-truth (a porter make_light_motte_picquet.py, hors depot) :
ALIAS_RNC += les 9 cle->ancre (les fantomes sans copro propre pointent
l'ancre soeur, idem |ALLEE|LEON BOURGEOIS -> 1|RUE|BUENOS AYRES).

Cible : data/secteur_motte_picquet_light.json. Backup .prevoieabrev.bak
(abort si present). DRY-RUN par defaut (rapport
data/dryrun_mp_voie_abrev.md). N'ecrit RIEN sans --apply.

Usage :
  python scripts/fix_mp_voie_abrev.py            # DRY-RUN
  python scripts/fix_mp_voie_abrev.py --apply     # (apres feu vert)
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prevoieabrev.bak"
REPORT = ROOT / "data" / "dryrun_mp_voie_abrev.md"

# (src_cle, anchor_cle, immat_attendu, role)  role: T=cible utilisateur,
# D=dependance (fantome chaine re-pointe vers SA copro)
MAP = [
    ("3|RUE|CAPT SCOTT",       "3|RUE|CAPITAINE SCOTT",      "AA8895435", "T"),
    ("4|RUE|GAL DE CASTELNAU", "4|RUE|GENERAL DE CASTELNAU", "AI7024987", "T"),
    ("7|RUE|GAL DE CASTELNAU", "7|RUE|GENERAL DE CASTELNAU", "AA4713186", "T"),
    ("8|RUE|GAL DE LARMINAT",  "8|RUE|GENERAL DE LARMINAT",  "AA9446949", "T"),
    ("11|RUE|GAL DE LARMINAT", "11|RUE|GENERAL DE LARMINAT", "AC8648685", "T"),
    ("1|RUE|CAPT SCOTT",       "1|RUE|CAPITAINE SCOTT",      "AF6894638", "D"),
    ("5|RUE|GAL DE CASTELNAU", "5|RUE|GENERAL DE CASTELNAU", "AC0121202", "D"),
    ("6|RUE|GAL DE CASTELNAU", "4|RUE|GENERAL DE CASTELNAU", "AI7024987", "D"),
    ("12|RUE|ALASSEUR",        "8|RUE|GENERAL DE LARMINAT",  "AA9446949", "D"),
]

MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def parc_model(light):
    """Replique renderSecteur §6 : dedup bgid, lots RNC prioritaires
    sinon nb_log_bdnb si bati residentiel."""
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
        parc += (sum(bgRncLots[bg].values()) if bg in bgRncLots
                 else bgBdnb.get(bg, 0))
    return parc


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    # ---- gardes (aucune ecriture si une assertion casse) ----
    abort = []
    for src, anc, immat, role in MAP:
        s, da = by.get(src), by.get(anc)
        cp = cbc.get(anc)
        if s is None:
            abort.append(f"cible absente : {src}")
            continue
        if da is None:
            abort.append(f"ancre absente light : {anc} (<- {src})")
            continue
        if cp is None or cp.get("numero_immatriculation") != immat:
            abort.append(
                f"copro {immat} introuvable sur {anc} "
                f"(got {cp and cp.get('numero_immatriculation')})")
        if da.get("_fusion_auto") and da.get("_fusion_cible"):
            abort.append(f"ancre {anc} elle-meme fusionnee "
                         f"(-> {da.get('_fusion_cible')})")
    anchors = {anc for _, anc, _, _ in MAP}
    srcs = {src for src, _, _, _ in MAP}
    if anchors & srcs:
        abort.append(f"ancre AUSSI cible (chaine) : {anchors & srcs}")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    rows = []
    for src, anc, immat, role in MAP:
        s, da = pby.get(src), pby.get(anc)
        if s is None or da is None:
            continue
        cp = cbc.get(anc) or {}
        before = {"bg": s.get("batiment_groupe_id"),
                  "usage": s.get("usage_principal_bdnb"),
                  "nblog": s.get("nb_log_bdnb"),
                  "fc": s.get("_fusion_cible"),
                  "vlog": s.get("nb_ventes_logement") or 0,
                  "vtot": s.get("nb_ventes_total") or 0,
                  "vpa": s.get("ventes_par_an") or {}}
        same_bg = s.get("batiment_groupe_id") == da.get("batiment_groupe_id")
        for k in MIRROR:
            s[k] = da.get(k)
        s["_bdnb_match"] = "immat"
        if syn_ok(da.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = da.get("syndic")
            s["_syndic_src"] = (da.get("_syndic_src") or "rnc") + "_grp"
        s["_fusion_auto"] = True
        s["_fusion_cible"] = anc
        s["_fusion_auto_sources"] = None     # une cible ne porte plus de src
        rows.append({
            "src": src, "anc": anc, "immat": immat, "role": role,
            "lots": cp.get("nb_lots_habitation"),
            "copro": cp.get("nom_copropriete"),
            "syndic": cp.get("syndic"),
            "mode": "même bgid (parc-neutre)" if same_bg
            else "miroir bgid (dédup)",
            **{f"b_{k}": v for k, v in before.items()}})

    # _fusion_auto_sources recalcule sur chaque ancre (union avec
    # l'existant legitime, ex. 3|RUE|GAL DE CASTELNAU deja sur l'ancre)
    incoming = {}
    for src, anc, _, _ in MAP:
        incoming.setdefault(anc, []).append(src)
    for anc, adds in incoming.items():
        da = pby.get(anc)
        if da is None:
            continue
        cur = list(da.get("_fusion_auto_sources") or [])
        da["_fusion_auto_sources"] = sorted(set(cur + adds))
        da.setdefault("_fusion_auto_label", None)

    parc1 = parc_model(patched)
    vlog_T = sum(r["b_vlog"] for r in rows if r["role"] == "T")
    vlog_D = sum(r["b_vlog"] for r in rows if r["role"] == "D")
    vtot_T = sum(r["b_vtot"] for r in rows if r["role"] == "T")
    vtot_D = sum(r["b_vtot"] for r in rows if r["role"] == "D")

    # ---- rapport ----
    L = [f"# DRY-RUN — MP abréviation de voie (ALIAS_RNC miroir bgid)\n",
         f"Mode : **{'APPLY' if apply else 'DRY-RUN'}** · "
         f"rattachements = **{len(rows)}** "
         f"(5 cibles utilisateur + {len(rows) - 5} dépendances chaîne)\n",
         f"Parc (modèle renderSecteur §6) : **{parc0} → {parc1} "
         f"(delta {parc1 - parc0:+d})**. Un delta ≤ 0 = retrait de "
         "doublons BDNB (la copro RNC reste comptée via ses lots à "
         "l'ancre), **jamais une perte de parc réel**.\n",
         f"Ventes relocalisées au rendu (champs ventes INCHANGÉS) : "
         f"cibles {vlog_T} v_log / {vtot_T} v_tot ; dépendances "
         f"{vlog_D} v_log / {vtot_D} v_tot.\n",
         "| # | rôle | cle (abrégée) | v_log | v_tot | ventes/an | → "
         "ancre copro | immat | lots | syndic | mode |",
         "|--:|:--:|---|--:|--:|---|---|---|--:|---|---|"]
    order = {"T": 0, "D": 1}
    for i, r in enumerate(sorted(
            rows, key=lambda x: (order[x["role"]], -x["b_vlog"], x["src"])),
            1):
        vpa = " ".join(f"{y}:{r['b_vpa'].get(y)}" for y in (
            "2021", "2022", "2023", "2024", "2025") if r["b_vpa"].get(y))
        L.append(
            f"| {i} | {r['role']} | `{r['src'].replace('|', chr(92)+'|')}` "
            f"| {r['b_vlog']} | {r['b_vtot']} | {vpa or '—'} | "
            f"`{r['anc'].replace('|', chr(92)+'|')}` | {r['immat']} | "
            f"{r['lots']} | {(r['syndic'] or '—')[:24]} | {r['mode']} |")
    if abort:
        L += ["\n## ⚠ GARDES — apply BLOQUÉ\n", "| anomalie |", "|---|"]
        L += [f"| {a} |" for a in abort]
    L.append("\n---\n*scripts/fix_mp_voie_abrev.py — dry-run par "
             "défaut, n'écrit que ce rapport.*")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print("=" * 72)
    print(f"MP VOIE ABRÉV — {'APPLY' if apply else 'DRY-RUN'} · "
          f"{len(rows)} rattachements (5 cibles + {len(rows)-5} dép.)")
    print("=" * 72)
    for r in sorted(rows, key=lambda x: (order[x["role"]], -x["b_vlog"])):
        print(f"  [{r['role']}] {r['src']:24s} -> {r['anc']:26s} "
              f"{r['immat']} {r['lots']:>3} lots  v_log={r['b_vlog']} "
              f"v_tot={r['b_vtot']}  [{r['mode']}]")
    print("-" * 72)
    print(f"Parc modèle renderSecteur §6 : {parc0} -> {parc1} "
          f"(delta {parc1 - parc0:+d})")
    print(f"Ventes relocalisées : cibles {vlog_T}/{vtot_T} · "
          f"dépendances {vlog_D}/{vtot_D} (champs INCHANGÉS)")
    print(f"Rapport : {REPORT.name}")
    print("=" * 72)

    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifié. Feu vert requis "
              "avant --apply.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe déjà.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_voie_abrev"] = (
        f"{len(rows)} adresses DVF MP a cle de voie abregee "
        "(CAPT->CAPITAINE, GAL->GENERAL) rattachees a leur copro RNC "
        "reelle (immatriculee, presente snapshot) via ALIAS_RNC miroir "
        "bgid : 5 cibles (3 Capt Scott->AA8895435, 4 Gal Castelnau->"
        "AI7024987, 7 Gal Castelnau->AA4713186, 8 Gal Larminat->"
        "AA9446949, 11 Gal Larminat->AC8648685) + 4 dependances chaine "
        "re-pointees vers LEUR copro (1 Capt Scott->AF6894638, 5 Gal "
        "Castelnau->AC0121202, 6 Gal Castelnau->AI7024987, 12 Alasseur"
        "->AA9446949). Ventes relocalisees au rendu (champs INCHANGES), "
        f"parc modele {parc0}->{parc1} ({parc1-parc0:+d} : retrait de "
        "doublons BDNB, pas une perte). Source-of-truth = ALIAS_RNC "
        "make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Écrit : {LIGHT.name} ({len(rows)} rattachements)")


if __name__ == "__main__":
    main()
