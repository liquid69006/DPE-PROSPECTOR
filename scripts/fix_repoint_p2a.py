"""
Correctif SURGICAL — RE-POINT P2a : copros RNC ancrées enterrées sous
un fantôme DVF principal (auto-bgid-fusion a choisi le fantôme +
ventes comme principal au lieu de la copro `cle_adresse`). Audit
source : `scripts/audit_lacunes_pipeline.py` (P2a, 2026-05-20,
`data/audit_lacunes_pipeline.md`).

Pattern A3 (cf. `fix_mp_cibles_horsrnc.py` A3 = 38 Ch Floquet ↔ 6 Gal
Detrie). On INVERSE la fusion :
  ANCHOR (copro)  : _fusion_auto=None / _fusion_cible=None
                    _fusion_auto_sources = [PHANTOM] (devient principal)
  PHANTOM (DVF)   : _fusion_auto=True / _fusion_cible=ANCHOR
                    _fusion_auto_sources=None (devient secondaire)
Champs autoritatifs (bgid/nb_log_bdnb/usage/ventes_*) INCHANGÉS sur
les deux. Aucun ALIAS_RNC à ajouter : la source-of-truth est déjà le
critère `copro_by_cle` du tri principal fusion-bgid de make_light
(introduit pour Dupleix, étendu pour Floquet A3) — une regen future
résoudrait naturellement, sauf cas P2b (orphelin bgid-fusion :
addresse ajoutée par correctif post-make_light, autre piste).

Effet parc (modèle renderSecteur §6, dédup bgid + lots RNC
prioritaire) : pour CHAQUE cas, le bgid passe de `bgBdnb[bg] =
nb_log_bdnb du fantôme` (BDNB estimation) à `bgRncLots[immat] = lots
RNC de la copro` — switch BDNB→RNC. Delta = lots_RNC − nb_log_bdnb,
généralement faible (±)  ; négatif si la copro RNC est plus
restrictive (cas Grenelle 35 vs 89) = CORRECTION du sur-comptage
BDNB sur ce bgid (PIPELINE §6 stipule explicitement « lots RNC
prioritaire »). Net parc transparent et tracé.

5 cas (3 DL + 2 MP), parametrés par SECTEUR. Dry-run par défaut,
.prerepointp2a.bak. Idempotent (skip si déjà re-pointé). ABORT si
chaîne (autre addresse fusionnée DANS le phantôme : aucun cas
détecté pour le lot, vérifié 2026-05-20).

Usage :
  python scripts/fix_repoint_p2a.py            # DRY-RUN DL
  python scripts/fix_repoint_p2a.py --apply
  SECTEUR=motte_picquet python scripts/fix_repoint_p2a.py
  SECTEUR=motte_picquet python scripts/fix_repoint_p2a.py --apply
"""

import os
import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
SUF = "" if SECTEUR == "dauphine_lacassagne" else "_" + SECTEUR
SHORT = "dauphine" if SECTEUR == "dauphine_lacassagne" else "motte"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prerepointp2a.bak"
REPORT = ROOT / "data" / f"dryrun_repoint_p2a_{SHORT}.md"

# (phantom_cle, anchor_cle, immat_attendu) pour chaque secteur
CASES = {
    "dauphine_lacassagne": [
        ("53|RUE|ETIENNE RICHERAND", "51|RUE|ETIENNE RICHERAND",
         "AC3598851"),
        ("56|AVENUE|LACASSAGNE", "54|AVENUE|LACASSAGNE", "AA4814810"),
        ("316|RUE|PAUL BERT", "318|RUE|PAUL BERT", "AC6168629"),
    ],
    "motte_picquet": [
        ("9|RUE|GUESCLIN", "3|PASSAGE|GUESCLIN", "AB1748391"),
        # 156|BD|GRENELLE -> 154|BD|GRENELLE (AB1105360, 35 lots) :
        # ÉCARTÉ provisoirement (décision utilisateur 2026-05-20).
        # Switch BDNB(89) -> RNC(35) sur bgid F3HZ = -54 parc, magnitude
        # inédite pour 1 bgid. Le nom de la copro contient "MS103738"
        # (préfixe RPLS) -> hypothèse logement social hors-syndic. À
        # vérifier hors-bande (Pappers / RPLS) avant intégration.
        # ("156|BOULEVARD|GRENELLE", "154|BOULEVARD|GRENELLE",
        #  "AB1105360"),
    ],
}


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
        print(f"Aucun cas P2a pour SECTEUR={SECTEUR}")
        return
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    # ---- gardes ----
    abort = []
    for phan, anc, immat in cases:
        pa, aa, cp = by.get(phan), by.get(anc), cbc.get(anc)
        if pa is None:
            abort.append(f"phantom absent : {phan}")
        if aa is None:
            abort.append(f"anchor absent : {anc}")
        if cp is None or cp.get("numero_immatriculation") != immat:
            abort.append(
                f"copro {immat} introuvable sur {anc} "
                f"(got {cp and cp.get('numero_immatriculation')})")
        if pa and aa and pa.get("batiment_groupe_id") \
                != aa.get("batiment_groupe_id"):
            abort.append(
                f"bgid divergent : {phan} {pa.get('batiment_groupe_id')} "
                f"vs {anc} {aa.get('batiment_groupe_id')}")
        # chaîne : qq adresse fusionnée DANS le phantom autre que
        # l'anchor ? (orphelin si on re-pointe)
        chain = [a["cle"] for a in light["adresses"]
                 if a.get("_fusion_cible") == phan and a["cle"] != anc]
        if chain:
            abort.append(
                f"chaîne sous {phan} : {chain} (orphelins potentiels)")
        # idempotence : si l'anchor n'est plus fusionné, on a déjà fait
        already = (aa and not (aa.get("_fusion_auto")
                               and aa.get("_fusion_cible") == phan))
        if already:
            abort.append(f"idempotence : {anc} non fusé vers {phan} "
                         "(déjà re-pointé ?)")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    rows = []
    for phan, anc, immat in cases:
        pa, aa = pby.get(phan), pby.get(anc)
        if pa is None or aa is None:
            continue
        cp = cbc.get(anc) or {}
        # avant
        before_phan_fused = bool(pa.get("_fusion_auto"))
        before_phan_fsrcs = list(pa.get("_fusion_auto_sources") or [])
        bg = pa.get("batiment_groupe_id")
        # RE-POINT : anchor -> principal absorbant phantom
        anc_sources = sorted(set(
            [s for s in (aa.get("_fusion_auto_sources") or [])
             if s != phan] + [phan]))
        aa["_fusion_auto"] = None
        aa["_fusion_cible"] = None
        aa["_fusion_auto_sources"] = anc_sources
        aa.setdefault("_fusion_auto_label", None)
        # phantom devient secondaire
        pa["_fusion_auto"] = True
        pa["_fusion_cible"] = anc
        pa["_fusion_auto_sources"] = None
        # propagation syndic (anchor profite du phantom si syn_ok et
        # anchor sans, sinon inverse ; on aligne sur la convention
        # principal recolte sources)
        if syn_ok(pa.get("syndic")) and not syn_ok(aa.get("syndic")):
            aa["syndic"] = pa.get("syndic")
            aa["_syndic_src"] = (pa.get("_syndic_src") or "rnc") + "_grp"
        rows.append({
            "phan": phan, "anc": anc, "immat": immat,
            "lots": cp.get("nb_lots_habitation"),
            "nblog_bdnb_phan": pa.get("nb_log_bdnb"),
            "vlog_phan": pa.get("nb_ventes_logement") or 0,
            "vtot_phan": pa.get("nb_ventes_total") or 0,
            "vlog_anc": aa.get("nb_ventes_logement") or 0,
            "vtot_anc": aa.get("nb_ventes_total") or 0,
            "syndic": cp.get("syndic") or pa.get("syndic"),
            "copro_nom": cp.get("nom_copropriete"),
            "bg": bg, "anc_was_fused": True,
            "phan_was_principal": not before_phan_fused})

    parc1, contrib1 = parc_model(patched)

    L = [f"# DRY-RUN — RE-POINT P2a (copro RNC enterrée) — {SECTEUR}\n",
         f"Mode : **{'APPLY' if apply else 'DRY-RUN'}** · "
         f"re-points = **{len(rows)}**\n",
         f"Parc (modèle renderSecteur §6) : "
         f"**{parc0} → {parc1} (delta {parc1 - parc0:+d})**. Switch "
         "BDNB(estimation)→RNC(lots autoritaires) sur chaque bgid : "
         "delta = lots_RNC − nb_log_bdnb_phantom. Négatif = correction "
         "d'un sur-comptage BDNB (PIPELINE §6 stipule explicitement "
         "« lots RNC prioritaire »). Aucune vente perdue (relocalisation).\n",
         "| # | phantom (DVF) | v_log_phan | → ancre copro | immat | "
         "lots_RNC | nb_log_bdnb (phan) | Δ_parc bgid | mécanisme |",
         "|--:|---|--:|---|---|--:|--:|--:|---|"]
    for i, r in enumerate(rows, 1):
        b0, k0 = contrib0.get(r["bg"], (0, "—"))
        b1, k1 = contrib1.get(r["bg"], (0, "—"))
        L.append(
            f"| {i} | `{r['phan'].replace('|', chr(92)+'|')}` | "
            f"{r['vlog_phan']} | `{r['anc'].replace('|', chr(92)+'|')}` "
            f"| {r['immat']} | {r['lots']} | {r['nblog_bdnb_phan']} | "
            f"{b1 - b0:+d} ({b0} {k0} → {b1} {k1}) | RE-POINT |")
    L.append("")
    L.append("**Ventes relocalisées au rendu** (champs `ventes_*` "
             "**INCHANGÉS**) — chaque phantom devient secondaire de "
             "l'ancre, ses ventes apparaissent sous la copro RNC :")
    L.append("| phantom | v_log | v_tot | → copro | nom | syndic |")
    L.append("|---|--:|--:|---|---|---|")
    for r in rows:
        L.append(
            f"| `{r['phan'].replace('|', chr(92)+'|')}` | "
            f"{r['vlog_phan']} | {r['vtot_phan']} | "
            f"`{r['anc'].replace('|', chr(92)+'|')}` | "
            f"{(r['copro_nom'] or '')[:34]} | "
            f"{(r['syndic'] or '')[:24]} |")
    if abort:
        L += ["\n## ⚠ GARDES — apply BLOQUÉ\n", "| anomalie |", "|---|"]
        L += [f"| {a} |" for a in abort]
    L.append("\n---\n*`scripts/fix_repoint_p2a.py` — dry-run par "
             "défaut, n'écrit que ce rapport.*")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print("=" * 76)
    print(f"P2a RE-POINT — {SECTEUR} — {'APPLY' if apply else 'DRY-RUN'}"
          f" · {len(rows)} cas")
    print("=" * 76)
    for r in rows:
        b0, _ = contrib0.get(r["bg"], (0, ""))
        b1, _ = contrib1.get(r["bg"], (0, ""))
        print(f"  {r['phan']:30s} -> {r['anc']:30s} "
              f"{r['immat']} {r['lots']:>3} lots  "
              f"v_log_phan={r['vlog_phan']}  Δ_parc(bgid)={b1-b0:+d}")
    print("-" * 76)
    print(f"Parc modèle : {parc0} -> {parc1} (delta {parc1-parc0:+d})")
    print(f"Rapport : {REPORT.name}")
    print("=" * 76)

    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifié.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe déjà.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    cur = meta.get("_correctif_repoint_p2a")
    note = (f"{len(rows)} re-points P2a (copro RNC enterree sous "
            "fantome DVF principal) : "
            + ", ".join(f"{r['phan']}<-{r['anc']}({r['immat']})"
                        for r in rows)
            + f". Parc {parc0}->{parc1} ({parc1-parc0:+d}) = switch "
            "BDNB->RNC autoritaire (PIPELINE §6).")
    meta["_correctif_repoint_p2a"] = note if not cur else cur + " | " + note
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Écrit : {LIGHT.name} ({len(rows)} re-points)")


if __name__ == "__main__":
    main()
