"""
Correctif LOT — RE-POINT pivot BDNB (PARC-NEUTRE). Issu de
`scripts/pipeline_bdnb_pivot.py` / `data/audit_pivot_bdnb.md`.

12 orphelines DVF dont l'API BDNB `batiment_groupe_complet`
(`l_libelle_adr`) revele une copro RNC ancree sur une AUTRE adresse
BAN du MEME `batiment_groupe_id`, alors que la copro ancre est deja
visible (principal non fuse) dans le snapshot — `make_light` ne les
fusionne pas car la fusion-bgid est sautee (parite mixte ou ordre des
passes). Mecanisme : fusion forward parc-neutre (orphelin + sa chaine
de fusion deviennent secondaires de l'ancre copro).

ABSORPTION DE CHAINE : chaque orphelin a deja absorbe des voisins de
meme bgid+parite via la fusion-bgid auto (sources). Quand on re-pointe
l'orphelin vers l'ancre, on doit re-pointer aussi toute sa chaine pour
eviter les orphelins de chaine. Tous les membres partagent le bgid de
l'ancre -> ils deviennent simultanement secondaires de l'ancre.

PARC : strictement neutre (bgRncLots de l'ancre domine deja le bgid
par PIPELINE Sec 6 ; l'orphelin et sa chaine etaient BDNB-residentiels
sur le meme bgid -> bucket bgBdnb deja IGNORE par parc_model car
bg deja dans bgRncLots). Le script ABORT si delta != 0.

Cas exclus du lot (instruction individuelle requise) :
- `12 LOUIS JASSERON -> 17` (duplicate, on prend 13 via le visible)
- `18 ST ANTOINE -> 17 ST ANTOINE` (17 fuse vers 19 ST ANTOINE sur
  bgid DIFFERENT 7TYE-FUDZ-T2KQ : pas un cas pivot-meme-bgid)
- `156 GRENELLE -> 154 GRENELLE` (P2a deja ecarte 2026-05-20, BDNB
  89 -> RNC 35 = -54, RPLS suspect, attente verif Pappers/RPLS)

Cible : data/secteur_*_light.json. Backup .prepivot.bak.
DRY-RUN par defaut. PYTHONUTF8=1.

Usage :
  python scripts/fix_pivot_bdnb_lot.py            # DRY-RUN DL
  python scripts/fix_pivot_bdnb_lot.py --apply
  SECTEUR=motte_picquet python scripts/fix_pivot_bdnb_lot.py
  SECTEUR=motte_picquet python scripts/fix_pivot_bdnb_lot.py --apply
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
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prepivot.bak"
REPORT = ROOT / "data" / f"dryrun_pivot_bdnb_{SHORT}.md"

# (orphan_cle, anchor_cle, immat_attendu) - tous parc-neutre (meme bgid)
CASES = {
    "dauphine_lacassagne": [
        ("9|RUE|PROFESSEUR PAUL SISLEY", "7B|RUE|PROFESSEUR PAUL SISLEY",
         "AA0012898"),
        ("12|RUE|LOUIS JASSERON", "13|RUE|LOUIS JASSERON", "AC6278774"),
        ("14|RUE|ST MAXIMIN", "1|RUE|ROSSAN", "AB2460335"),
        ("38|RUE|BARABAN", "37|RUE|BARABAN", "AC9726381"),
        ("260|RUE|PAUL BERT", "264B|RUE|PAUL BERT", "AE1699040"),
        ("12|RUE|CARRY", "6|RUE|CARRY", "AC1825504"),
        ("48|RUE|ST MAXIMIN", "51|RUE|ST MAXIMIN", "AB2784080"),
        ("18|RUE|ETIENNE RICHERAND", "19|RUE|ETIENNE RICHERAND",
         "AG2447720"),
        ("10|RUE|DAUPHINE", "1|RUE|ST MAXIMIN", "AF0858860"),
        ("14|RUE|ST SIDOINE", "12|RUE|ST SIDOINE", "AB2206571"),
        ("46|RUE|ST MAXIMIN", "43|RUE|ST MAXIMIN", "AB1744747"),
    ],
    "motte_picquet": [
        ("3|PLACE|CAMBRONNE", "6|PLACE|CAMBRONNE", "AB5809108"),
    ],
}


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
    for bg in set(bgRncLots) | set(bgBdnb):
        parc += (sum(bgRncLots[bg].values()) if bg in bgRncLots
                 else bgBdnb.get(bg, 0))
    return parc


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
    # adresses fusionnees DANS chaque cle (chain map)
    chain_in = {}
    for a in light["adresses"]:
        if a.get("_fusion_cible"):
            chain_in.setdefault(a["_fusion_cible"], []).append(a["cle"])

    abort = []
    for orph, anc, immat in cases:
        s, da = by.get(orph), by.get(anc)
        cp = cbc.get(anc)
        if s is None:
            abort.append(f"orph absent : {orph}")
            continue
        if da is None:
            abort.append(f"anc absent : {anc}")
            continue
        if cp is None or cp.get("numero_immatriculation") != immat:
            abort.append(f"copro {immat} introuvable sur {anc} "
                         f"(got {cp and cp.get('numero_immatriculation')})")
        if da.get("_fusion_auto") and da.get("_fusion_cible"):
            abort.append(f"ancre {anc} elle-meme fusionnee "
                         f"(-> {da.get('_fusion_cible')})")
        if s.get("batiment_groupe_id") != da.get("batiment_groupe_id"):
            abort.append(f"bgid divergent : {orph} "
                         f"{s.get('batiment_groupe_id')} vs {anc} "
                         f"{da.get('batiment_groupe_id')}")
        # idempotence
        if s.get("_fusion_auto") and s.get("_fusion_cible") == anc:
            abort.append(f"idempotent : {orph} deja fuse vers {anc}")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    rows = []
    for orph, anc, immat in cases:
        s, da = pby.get(orph), pby.get(anc)
        if s is None or da is None:
            continue
        cp = cbc.get(anc) or {}
        ch = list(chain_in.get(orph, []))     # adresses fusees dans l'orph
        bg = s.get("batiment_groupe_id")
        # propagation syndic : si syndic ancre exploitable et orph sans
        if syn_ok(da.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = da.get("syndic")
            s["_syndic_src"] = (da.get("_syndic_src") or "rnc") + "_grp"
        # orphelin -> secondaire de l'ancre
        s["_fusion_auto"] = True
        s["_fusion_cible"] = anc
        s["_fusion_auto_sources"] = None
        # toute la chaine de l'orph -> secondaires de l'ancre (re-point)
        for cx in ch:
            x = pby.get(cx)
            if x is None:
                continue
            x["_fusion_auto"] = True
            x["_fusion_cible"] = anc
            x["_fusion_auto_sources"] = None
        # ancre absorbe orph + chaine (union avec existant)
        new_srcs = sorted(set(
            (da.get("_fusion_auto_sources") or []) + [orph] + ch))
        da["_fusion_auto_sources"] = new_srcs
        da.setdefault("_fusion_auto_label", None)
        rows.append({
            "orph": orph, "anc": anc, "immat": immat,
            "lots": cp.get("nb_lots_habitation"),
            "copro_nom": cp.get("nom_copropriete"),
            "syndic": cp.get("syndic"),
            "vlog_orph": s.get("nb_ventes_logement") or 0,
            "vtot_orph": s.get("nb_ventes_total") or 0,
            "vpa_orph": s.get("ventes_par_an") or {},
            "chain": ch, "bg": bg,
        })

    parc1 = parc_model(patched)
    neutral = (parc1 == parc0)
    vtot_log = sum(r["vlog_orph"] for r in rows)
    vtot_all = sum(r["vtot_orph"] for r in rows)

    L = [f"# DRY-RUN — RE-POINT pivot BDNB (parc-neutre) — {SECTEUR}\n",
         f"Mode : **{'APPLY' if apply else 'DRY-RUN'}** · "
         f"re-points = **{len(rows)}** (12 DL + 1 MP total ; ce "
         f"rapport = secteur courant)\n",
         f"Parc (modele renderSecteur §6) : **{parc0} -> {parc1} "
         f"(delta {parc1 - parc0:+d})** · "
         f"parc-neutre = {'OUI' if neutral else 'NON !!'}.\n",
         f"Ventes relocalisees au rendu (champs INCHANGES) : "
         f"{vtot_log} v_log / {vtot_all} v_tot (orphelins). Plus la "
         "chaine de fusion deja absorbee par chaque orph qui suit.\n",
         "| # | orph (cle) | v_log | -> ancre copro | immat | lots | "
         "chaine de fusion absorbee (sources de l'orph -> ancre) |",
         "|--:|---|--:|---|---|--:|---|"]
    for i, r in enumerate(sorted(rows, key=lambda x: -x["vlog_orph"]),
                          1):
        chs = ", ".join(f"`{c.replace('|', chr(92)+'|')}`"
                        for c in r["chain"]) or "(aucune)"
        L.append(
            f"| {i} | `{r['orph'].replace('|', chr(92)+'|')}` | "
            f"{r['vlog_orph']} | "
            f"`{r['anc'].replace('|', chr(92)+'|')}` | "
            f"{r['immat']} | {r['lots']} | {chs} |")
    if abort:
        L += ["\n## ⚠ GARDES — apply BLOQUE\n", "| anomalie |", "|---|"]
        L += [f"| {a} |" for a in abort]
    L.append("\n---\n*`scripts/fix_pivot_bdnb_lot.py` - dry-run par "
             "defaut, n'ecrit que ce rapport.*")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print("=" * 78)
    print(f"PIVOT BDNB RE-POINT — {SECTEUR} — "
          f"{'APPLY' if apply else 'DRY-RUN'} · {len(rows)} re-points")
    print("=" * 78)
    for r in sorted(rows, key=lambda x: -x["vlog_orph"]):
        print(f"  {r['orph']:34s} -> {r['anc']:34s} "
              f"{r['immat']} {r['lots']:>4} lots  vlog={r['vlog_orph']:>2}"
              f"  chain={r['chain'] or '[]'}")
    print("-" * 78)
    print(f"Parc modele : {parc0} -> {parc1} (delta {parc1-parc0:+d}, "
          f"neutre={'OUI' if neutral else 'NON'})")
    print(f"Rapport : {REPORT.name}")
    print("=" * 78)

    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie.")
        return
    if not neutral:
        print("ABORT : modele parc NON neutre -> lot non sur.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    cas_txt = "; ".join(f"{r['orph']}->{r['anc']}({r['immat']})"
                        for r in rows)
    meta["_correctif_pivot_bdnb"] = (
        f"{len(rows)} re-points pivot BDNB ({SECTEUR}) - copros RNC "
        "ancrees sur une AUTRE adresse BAN du meme bgid, revelees par "
        "API BDNB batiment_groupe_complet.l_libelle_adr (cf. "
        "scripts/pipeline_bdnb_pivot.py + data/audit_pivot_bdnb.md). "
        "Fusion forward avec absorption de chaine (orph + sources -> "
        f"ancre). Parc {parc0}->{parc1} (strictement neutre, meme "
        f"bgid). Cas appliques: {cas_txt}")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(rows)} re-points)")


if __name__ == "__main__":
    main()
