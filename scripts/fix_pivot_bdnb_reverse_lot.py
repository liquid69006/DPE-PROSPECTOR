"""
Correctif LOT — RE-POINT pivot BDNB REVERSE. Issu de
`scripts/pipeline_bdnb_pivot_reverse.py` (audit_pivot_bdnb_reverse.md).

26 orphelines DVF dont l'API BDNB `batiment_groupe_complet` (sur le
bgid de la COPRO RNC) revele que l'orph fait partie du meme bati que
la copro — pattern miroir (Acollas-type) ou parc-neutre. La passe
forward du pivot (orph -> bgid orph -> copros) rate ces cas car les
bgids light divergent.

Mecanisme : MIROIR BGID (adoption MIRROR : bgid + nblog + usage +
champs BDNB derives) + fusion forward + absorption de chaine.
L'orphelin et ses sources de fusion-bgid heritees deviennent
simultanement secondaires de la copro ancre. Pattern strictement
identique a `fix_pivot_bdnb_lot.py` + `fix_mp_voie_abrev.py`.

PARC : miroir bgid -> retrait du BDNB phantom de l'orph (= un bati
BDNB qui apparaissait separement mais qui est en realite couvert par
la copro RNC voisine via ses lots syndicaux). Conforme PIPELINE Sec 6
"lots RNC prioritaire". Effet net = somme des nblog_bdnb des orphs
qui contribuaient au parc (- valeurs documentees par parc_model).
Le script ABORT si delta inattendu (> +0).

Cas appliques (24 DL + 2 MP) :
DL :
  30|RUE|ETIENNE RICHERAND -> 28|RUE|ETIENNE RICHERAND AA0358655 (12 v_log)
  8|RUE|CLAUDIUS PIONCHON -> 12|RUE|ST SIDOINE AB2206571 (9 v_log)
  29|RUE|STE ANNE DE BARABAN -> 27|RUE|STE ANNE DE BARABAN AA1700848 (6 v_log)
  11|RUE|RIBOUD -> 11|RUE|MAURICE FLANDIN AA1456987 (5 v_log)
  16|RUE|ETIENNE RICHERAND -> 22|RUE|ST ANTOINE AA1601434 (4 v_log)
  31|RUE|STE ANNE DE BARABAN -> 27|RUE|STE ANNE DE BARABAN AA1700848 (4 v_log)
  47|RUE|PROFESSEUR PAUL SISLEY -> 16|RUE|GUILLOUD AA7407463 (4 v_log)
  22|RUE|LOUIS JASSERON -> 18|RUE|LOUIS JASSERON AB1570571 (4 v_log)
  4|RUE|JEAN RENOIR -> 38|RUE|JEANNE HACHETTE AB6374961 (4 v_log)
  4|RUE|MARCEL PEHU -> 28|RUE|ST PHILIPPE AC2574101 (4 v_log)
  51|AVENUE|GEORGES POMPIDOU -> 18|RUE|LOUIS JASSERON AB1570571 (3 v_log)
  5|RUE|JEAN PIERRE LEVY -> 1|RUE|JEAN PIERRE LEVY AB3947009 (3 v_log)
  6|RUE|METALLURGIE -> 9|RUE|DAVID AB3954260 (3 v_log)
  10|RUE|TERNOIS -> 23|RUE|RIBOUD AA1991660 (2 v_log)
  325|RUE|PAUL BERT -> 2|RUE|ST EUSEBE AB0287870 (2 v_log)
  124|RUE|ANTOINE CHARIAL -> 11|RUE|ST EUSEBE AB1809680 (2 v_log)
  11|RUE|DAVID -> 9|RUE|DAVID AB3954260 (2 v_log)
  10|RUE|METALLURGIE -> 9|RUE|DAVID AB3954260 (2 v_log)
  10|RUE|TEINTURIERS -> 104|RUE|BARABAN AC1218890 (2 v_log)
  4|RUE|MAURICE FLANDIN -> 234|COURS|LAFAYETTE AC8608747 (2 v_log)
  277|RUE|PAUL BERT -> 76|RUE|ANTOINE CHARIAL AA1694256 (1 v_log)
  279|RUE|PAUL BERT -> 76|RUE|ANTOINE CHARIAL AA1694256 (1 v_log)
  69|RUE|BARABAN -> 61|RUE|BARABAN AB2515468 (1 v_log)
  24|AVENUE|LACASSAGNE -> 24||ET 24 BIS AVENUE LACASSAGNE AG1556893 (1 v_log)
MP :
  22|RUE|FEDERATION -> 20|RUE|FEDERATION AA0398420 (4 v_log)
  11||CITE THURE -> 15|RUE|GRAMME AJ1220698 (3 v_log)

Cible : data/secteur_*_light.json. Backup .prepivotrev.bak. Dry-run par
defaut.

Usage :
  python scripts/fix_pivot_bdnb_reverse_lot.py
  python scripts/fix_pivot_bdnb_reverse_lot.py --apply
  SECTEUR=motte_picquet python scripts/fix_pivot_bdnb_reverse_lot.py
  SECTEUR=motte_picquet python scripts/fix_pivot_bdnb_reverse_lot.py --apply
"""

import os
import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
SHORT = "dauphine" if SECTEUR == "dauphine_lacassagne" else "motte"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prepivotrev.bak"
REPORT = ROOT / "data" / f"dryrun_pivot_bdnb_reverse_{SHORT}.md"

CASES = {
    "dauphine_lacassagne": [
        ("30|RUE|ETIENNE RICHERAND", "28|RUE|ETIENNE RICHERAND", "AA0358655"),
        ("8|RUE|CLAUDIUS PIONCHON", "12|RUE|ST SIDOINE", "AB2206571"),
        ("29|RUE|STE ANNE DE BARABAN", "27|RUE|STE ANNE DE BARABAN", "AA1700848"),
        ("11|RUE|RIBOUD", "11|RUE|MAURICE FLANDIN", "AA1456987"),
        ("16|RUE|ETIENNE RICHERAND", "22|RUE|ST ANTOINE", "AA1601434"),
        ("31|RUE|STE ANNE DE BARABAN", "27|RUE|STE ANNE DE BARABAN", "AA1700848"),
        ("47|RUE|PROFESSEUR PAUL SISLEY", "16|RUE|GUILLOUD", "AA7407463"),
        ("22|RUE|LOUIS JASSERON", "18|RUE|LOUIS JASSERON", "AB1570571"),
        ("4|RUE|JEAN RENOIR", "38|RUE|JEANNE HACHETTE", "AB6374961"),
        ("4|RUE|MARCEL PEHU", "28|RUE|ST PHILIPPE", "AC2574101"),
        ("51|AVENUE|GEORGES POMPIDOU", "18|RUE|LOUIS JASSERON", "AB1570571"),
        ("5|RUE|JEAN PIERRE LEVY", "1|RUE|JEAN PIERRE LEVY", "AB3947009"),
        ("6|RUE|METALLURGIE", "9|RUE|DAVID", "AB3954260"),
        ("10|RUE|TERNOIS", "23|RUE|RIBOUD", "AA1991660"),
        ("325|RUE|PAUL BERT", "2|RUE|ST EUSEBE", "AB0287870"),
        ("124|RUE|ANTOINE CHARIAL", "11|RUE|ST EUSEBE", "AB1809680"),
        ("11|RUE|DAVID", "9|RUE|DAVID", "AB3954260"),
        ("10|RUE|METALLURGIE", "9|RUE|DAVID", "AB3954260"),
        ("10|RUE|TEINTURIERS", "104|RUE|BARABAN", "AC1218890"),
        ("4|RUE|MAURICE FLANDIN", "234|COURS|LAFAYETTE", "AC8608747"),
        ("277|RUE|PAUL BERT", "76|RUE|ANTOINE CHARIAL", "AA1694256"),
        ("279|RUE|PAUL BERT", "76|RUE|ANTOINE CHARIAL", "AA1694256"),
        ("69|RUE|BARABAN", "61|RUE|BARABAN", "AB2515468"),
        ("24|AVENUE|LACASSAGNE", "24||ET 24 BIS AVENUE LACASSAGNE",
         "AG1556893"),
    ],
    "motte_picquet": [
        ("22|RUE|FEDERATION", "20|RUE|FEDERATION", "AA0398420"),
        ("11||CITE THURE", "15|RUE|GRAMME", "AJ1220698"),
    ],
}

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
    cases = CASES.get(SECTEUR, [])
    if not cases:
        print(f"Aucun cas pour SECTEUR={SECTEUR}")
        return
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}
    chain_in = {}
    for a in light["adresses"]:
        fc = a.get("_fusion_cible")
        if fc:
            chain_in.setdefault(fc, []).append(a["cle"])

    abort = []
    for orph, anc, immat in cases:
        s, da = by.get(orph), by.get(anc)
        cp = cbc.get(anc)
        if s is None:
            abort.append(f"orph absent : {orph}")
        if da is None:
            abort.append(f"anc absent : {anc}")
        if cp is None or cp.get("numero_immatriculation") != immat:
            abort.append(f"copro {immat} introuvable sur {anc} "
                         f"(got {cp and cp.get('numero_immatriculation')})")
        if da and da.get("_fusion_auto") and da.get("_fusion_cible"):
            abort.append(f"anc {anc} elle-meme fusionnee")
        if s and s.get("_fusion_auto") and s.get("_fusion_cible") == anc:
            abort.append(f"idempotent : {orph} deja fuse vers {anc}")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    rows = []
    for orph, anc, immat in cases:
        s, da = pby.get(orph), pby.get(anc)
        if s is None or da is None:
            continue
        cp = cbc.get(anc) or {}
        ch = list(chain_in.get(orph, []))
        bg_avant = s.get("batiment_groupe_id")
        nblog_avant = s.get("nb_log_bdnb")
        vlog_s = s.get("nb_ventes_logement") or 0
        vtot_s = s.get("nb_ventes_total") or 0
        # adoption MIRROR
        for k in MIRROR:
            s[k] = da.get(k)
        s["_bdnb_match"] = "immat"
        if syn_ok(da.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = da.get("syndic")
            s["_syndic_src"] = (da.get("_syndic_src") or "rnc") + "_grp"
        s["_fusion_auto"] = True
        s["_fusion_cible"] = anc
        s["_fusion_auto_sources"] = None
        # chaine : aussi vers anc, adoption MIRROR (meme bgid que orph
        # avant -> meme nouvelle valeur)
        for cx in ch:
            if cx in [c[0] for c in cases]:
                continue
            x = pby.get(cx)
            if x is None:
                continue
            for k in MIRROR:
                x[k] = da.get(k)
            x["_bdnb_match"] = "immat"
            if syn_ok(da.get("syndic")) and not syn_ok(x.get("syndic")):
                x["syndic"] = da.get("syndic")
                x["_syndic_src"] = (da.get("_syndic_src") or "rnc") + "_grp"
            x["_fusion_auto"] = True
            x["_fusion_cible"] = anc
            x["_fusion_auto_sources"] = None
        new_srcs = sorted(set(
            (da.get("_fusion_auto_sources") or []) + [orph] + ch))
        da["_fusion_auto_sources"] = new_srcs
        da.setdefault("_fusion_auto_label", None)
        rows.append({
            "orph": orph, "anc": anc, "immat": immat,
            "lots": cp.get("nb_lots_habitation"),
            "copro_nom": cp.get("nom_copropriete"),
            "syndic": cp.get("syndic"),
            "vlog": vlog_s, "vtot": vtot_s,
            "bg_avant": bg_avant, "nblog_avant": nblog_avant,
            "bg_apres": s.get("batiment_groupe_id"),
            "chain": ch,
        })

    parc1, contrib1 = parc_model(patched)
    vtot_log = sum(r["vlog"] for r in rows)
    vtot_all = sum(r["vtot"] for r in rows)

    # bgids dont la contribution change
    bg_changes = []
    for bg in set(contrib0) | set(contrib1):
        a0, k0 = contrib0.get(bg, (0, "-"))
        a1, k1 = contrib1.get(bg, (0, "ABSENT"))
        if a0 != a1:
            bg_changes.append((bg, a0, k0, a1, k1))

    L = [f"# DRY-RUN — RE-POINT pivot BDNB REVERSE — {SECTEUR}\n",
         f"Mode : **{'APPLY' if apply else 'DRY-RUN'}** · "
         f"re-points = **{len(rows)}** ({len(cases)} cibles + chaines "
         "automatiques)\n",
         f"Parc (modele renderSecteur Sec 6) : **{parc0} -> {parc1} "
         f"(delta {parc1 - parc0:+d})**. Net = retrait des BDNB "
         "phantoms des orphelins (= batis BDNB que la copro RNC couvre "
         "deja conceptuellement via ses lots syndicaux, conforme "
         'PIPELINE Sec 6 "lots RNC prioritaire").\n',
         f"Ventes relocalisees au rendu (champs INCHANGES) : {vtot_log}"
         f" v_log / {vtot_all} v_tot pour les orphelins (+ chaines).\n",
         "| # | orph (cle) | v_log | bgid avant | -> ancre copro | "
         "immat | lots | nom copro | syndic | chaine absorbee |",
         "|--:|---|--:|---|---|---|--:|---|---|---|"]
    for i, r in enumerate(sorted(rows, key=lambda x: -x["vlog"]), 1):
        chs = ", ".join(f"`{c.replace('|', chr(92)+'|')}`"
                        for c in r["chain"]) or "(aucune)"
        L.append(
            f"| {i} | `{r['orph'].replace('|', chr(92)+'|')}` | "
            f"{r['vlog']} | `...{(r['bg_avant'] or '')[-12:]}` | "
            f"`{r['anc'].replace('|', chr(92)+'|')}` | "
            f"{r['immat']} | {r['lots']} | "
            f"{(r['copro_nom'] or '-')[:24]} | "
            f"{(r['syndic'] or '-')[:18]} | {chs} |")
    if bg_changes:
        L.append("\n## bgids dont la contribution parc change\n")
        L.append("| bgid | avant | apres | delta |\n|---|---|---|--:|")
        for bg, a0, k0, a1, k1 in sorted(bg_changes,
                                          key=lambda x: (x[3] - x[1])):
            L.append(f"| `...{bg[-12:]}` | {a0} ({k0}) | "
                     f"{a1} ({k1}) | {a1 - a0:+d} |")
    if abort:
        L += ["\n## ⚠ GARDES — apply BLOQUE\n", "| anomalie |", "|---|"]
        L += [f"| {a} |" for a in abort]
    L.append("\n---\n*scripts/fix_pivot_bdnb_reverse_lot.py - dry-run "
             "par defaut.*")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print("=" * 80)
    print(f"PIVOT BDNB REVERSE — {SECTEUR} — "
          f"{'APPLY' if apply else 'DRY-RUN'} · {len(rows)} cas")
    print("=" * 80)
    for r in sorted(rows, key=lambda x: -x["vlog"]):
        print(f"  {r['orph']:34s} -> {r['anc']:32s} "
              f"{r['immat']} {r['lots']:>4} lots  vlog={r['vlog']:>2}"
              f"  chain={len(r['chain'])}")
    print("-" * 80)
    print(f"Parc modele : {parc0} -> {parc1} (delta {parc1-parc0:+d})")
    if bg_changes:
        print(f"bgids changes : {len(bg_changes)}")
    print(f"Rapport : {REPORT.name}")
    print("=" * 80)

    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    cas_txt = "; ".join(f"{r['orph']}->{r['anc']}({r['immat']})"
                        for r in rows)
    meta["_correctif_pivot_reverse"] = (
        f"{len(rows)} re-points pivot BDNB reverse ({SECTEUR}) - "
        "copros RNC dont le bgid (via cle_adresse) reclame des "
        "adresses BAN qui sont des orphelines DVF hors-RNC. Forward "
        "ratait ces cas (bgids light divergents). Pattern miroir-bgid "
        "(adoption MIRROR + fusion + absorption chaine). "
        f"Parc {parc0}->{parc1} ({parc1-parc0:+d}) = retrait BDNB "
        "phantoms des orphs conforme PIPELINE Sec 6. Cas: " + cas_txt)
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(rows)} re-points)")


if __name__ == "__main__":
    main()
