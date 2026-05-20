"""
Correctif SURGICAL — Motte-Picquet : `5|AVENUE|GAL DETRIE` (DVF
phantom, bgid GQAG, partagé avec 55 SUFFREN) actuellement **fusé à
tort** dans 55 SUFFREN par la fusion-bgid automatique. Confirmation
terrain utilisateur (2026-05-20) : le bâti 5 Av. Général Détrie est
distinct de 55 Av Suffren, copro propre AD5265665 (11 lots, PICHET
IMMOBILIER SERVICES). L'absence d'`ALIAS_RNC GAL→GENERAL` dans
make_light fait que la clé DVF abrégée résout via BDNB num_voie au
bgid GQAG (du voisin 55 Suffren), pas au bgid Y2Q8 (du vrai 5 Détrie).

Diag source : `data/diag_4_ensembles_mp.md` G2 (2026-05-20). Audit
amont : `data/audit_lacunes_pipeline.md` cause P1 (abréviation non
couverte par SUBS) + P2-like (bgid-fusion fait le mauvais regroupement).

Mécanisme : **ALIAS_RNC miroir bgid** (pattern A2 / fix_mp_voie_abrev).
La clé `5|AVENUE|GAL DETRIE` adopte les champs (bgid Y2Q8, usage,
nb_log_bdnb, …) de l'ancre `5|AVENUE|GENERAL DETRIE`, puis _fusion_auto
→ ancre. 55 SUFFREN perd 5 GAL DETRIE de son `_fusion_auto_sources`
et redevient un principal hr-active propre (sans fsrc erronée).

Effet parc (renderSecteur §6) :
  Avant : GQAG -> bgBdnb[GQAG]=15 (via 55 SUFFREN principal) ;
          Y2Q8 -> bgRncLots[AD5265665]=11 (via 5 GENERAL DETRIE).
  Après : GQAG inchangé (55 SUFFREN reste principal, bgBdnb=15) ;
          Y2Q8 inchangé (AD5265665=11) ; 5 GAL DETRIE adopte Y2Q8
          mais reste fusé → skip dans le parc.
  **Strictement parc-neutre** (le script ABORT si delta ≠ 0).

Ventes : 5 GAL DETRIE n'a AUCUNE vente (vlog=0, vtot=0). Pure
correction structurelle. Aucune relocalisation matérielle.

Source-of-truth à porter dans make_light_motte_picquet.py :
  ALIAS_RNC += { "5|AVENUE|GAL DETRIE": "5|AVENUE|GENERAL DETRIE" }

Cible : data/secteur_motte_picquet_light.json. Backup
.predetrie.bak. Dry-run par défaut.

Usage :
  python scripts/fix_detrie_repoint.py            # DRY-RUN
  python scripts/fix_detrie_repoint.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.predetrie.bak"

SRC_CLE = "5|AVENUE|GAL DETRIE"
DST_CLE = "5|AVENUE|GENERAL DETRIE"
IMMAT = "AD5265665"
OLD_PRINC = "55|AVENUE|SUFFREN"  # principal actuel qui héberge SRC à tort

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

    s = by.get(SRC_CLE)
    d = by.get(DST_CLE)
    op = by.get(OLD_PRINC)
    cp = cbc.get(DST_CLE)

    abort = []
    if s is None:
        abort.append(f"src absente : {SRC_CLE}")
    if d is None:
        abort.append(f"dst absente : {DST_CLE}")
    if op is None:
        abort.append(f"ancien principal absent : {OLD_PRINC}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {DST_CLE} "
                     f"(got {cp and cp.get('numero_immatriculation')})")
    if d and d.get("_fusion_auto") and d.get("_fusion_cible"):
        abort.append(f"dst {DST_CLE} elle-meme fusionnee "
                     f"(-> {d.get('_fusion_cible')})")
    # idempotence : si src deja fuse vers dst, on a deja fait
    already = (s and s.get("_fusion_auto") and
               s.get("_fusion_cible") == DST_CLE)
    chain_in_src = [a["cle"] for a in light["adresses"]
                    if a.get("_fusion_cible") == SRC_CLE]
    if chain_in_src:
        abort.append(f"chaine sous {SRC_CLE} : {chain_in_src} "
                     "(orphelins potentiels — investiguer)")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    ps = pby.get(SRC_CLE)
    pd = pby.get(DST_CLE)
    pop = pby.get(OLD_PRINC)

    before = {
        "src_bg": ps.get("batiment_groupe_id"),
        "src_fcible": ps.get("_fusion_cible"),
        "src_usage": ps.get("usage_principal_bdnb"),
        "src_nblog": ps.get("nb_log_bdnb"),
        "src_vlog": ps.get("nb_ventes_logement") or 0,
        "src_vtot": ps.get("nb_ventes_total") or 0,
        "op_fsrcs": list(pop.get("_fusion_auto_sources") or []),
        "dst_bg": pd.get("batiment_groupe_id"),
        "dst_fsrcs": list(pd.get("_fusion_auto_sources") or []),
    }
    if not already:
        # adoption miroir
        for k in MIRROR:
            ps[k] = pd.get(k)
        ps["_bdnb_match"] = "immat"
        if syn_ok(pd.get("syndic")) and not syn_ok(ps.get("syndic")):
            ps["syndic"] = pd.get("syndic")
            ps["_syndic_src"] = (pd.get("_syndic_src") or "rnc") + "_grp"
        ps["_fusion_auto"] = True
        ps["_fusion_cible"] = DST_CLE
        ps["_fusion_auto_sources"] = None
        # dst : ajoute SRC dans _fusion_auto_sources
        pd["_fusion_auto_sources"] = sorted(
            set((pd.get("_fusion_auto_sources") or []) + [SRC_CLE]))
        pd.setdefault("_fusion_auto_label", None)
        # ancien principal (55 SUFFREN) : retire SRC de fsrcs
        new_fsrcs = [x for x in (pop.get("_fusion_auto_sources") or [])
                     if x != SRC_CLE]
        pop["_fusion_auto_sources"] = new_fsrcs if new_fsrcs else None

    parc1 = parc_model(patched)
    neutral = (parc1 == parc0)
    after = {
        "src_bg": ps.get("batiment_groupe_id"),
        "src_fcible": ps.get("_fusion_cible"),
        "src_usage": ps.get("usage_principal_bdnb"),
        "src_nblog": ps.get("nb_log_bdnb"),
        "op_fsrcs": pop.get("_fusion_auto_sources"),
        "dst_fsrcs": pd.get("_fusion_auto_sources"),
    }

    print("=" * 72)
    print(f"FIX DETRIE RE-POINT — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 72)
    print(f"  SRC   : {SRC_CLE}")
    print(f"  DST   : {DST_CLE}  (copro {IMMAT} "
          f"{cp.get('nb_lots_habitation') if cp else '?'} lots, syndic "
          f"{cp.get('syndic') if cp else '?'!r})")
    print(f"  OLD_P : {OLD_PRINC}")
    print(f"  déjà appliqué : {already}")
    print("-" * 72)
    print("SRC AVANT :")
    for k in ("src_bg", "src_fcible", "src_usage", "src_nblog",
             "src_vlog", "src_vtot"):
        print(f"  {k:10s} = {before[k]!r}")
    print("SRC APRÈS :")
    for k in ("src_bg", "src_fcible", "src_usage", "src_nblog"):
        print(f"  {k:10s} = {after[k]!r}")
    print(f"OLD_P {OLD_PRINC} _fusion_auto_sources : "
          f"{before['op_fsrcs']} → {after['op_fsrcs']}")
    print(f"DST   {DST_CLE} _fusion_auto_sources : "
          f"{before['dst_fsrcs']} → {after['dst_fsrcs']}")
    print("-" * 72)
    print(f"Parc modèle : {parc0} → {parc1} (delta {parc1-parc0:+d}, "
          f"neutre = {'OUI' if neutral else 'NON !!'})")
    print("=" * 72)

    if abort:
        print("ABORT (gardes) :")
        for a in abort:
            print("  - " + a)
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifié.")
        return
    if already:
        print("Idempotent : déjà appliqué.")
        return
    if not neutral:
        print("ABORT : modèle parc NON neutre → fix non sûr.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe déjà.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_detrie"] = (
        f"Re-point {SRC_CLE} (DVF phantom, bgid GQAG partagé avec "
        f"{OLD_PRINC}) -> {DST_CLE} (copro {IMMAT} AD5265665 11 lots "
        "PICHET IMMOBILIER, bgid Y2Q8). ALIAS_RNC miroir bgid (pattern "
        "A2 / fix_mp_voie_abrev), confirmation terrain user 2026-05-20 "
        "(5 Détrie distinct de 55 Suffren). 55 SUFFREN perd la fsrc "
        f"erronée. Parc {parc0}->{parc1} (strictement neutre). Aucune "
        "vente relocalisée (src vlog=0). Source-of-truth = ALIAS_RNC "
        "make_light_motte_picquet.py.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Écrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
