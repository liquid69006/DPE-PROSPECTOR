"""
Correctif SURGICAL — RE-POINT 156 BD GRENELLE -> 154 BD GRENELLE
(AB1105360 "PARIS MOTTE PICQUET GRENELLE - MS103738", 35 lots). 5e cas
P2a precedemment ecarte (decision 2026-05-20) puis re-instruit via
pivot BDNB + RNC live (2026-05-20).

CONTEXTE BDNB COMPLET (bgid F3HZ-H1TK-FPME) :
  - Complexe immobilier 2011, 10 niveaux, 1228 m2 au sol, 89 logements
    BDNB ; usage_principal = "Residentiel collectif".
  - 12 adresses BAN : 152/154/156/158 BD GRENELLE + 35/37/37b/39/39b/
    39t Rue Fremicourt + 1/3 ruelle au pere fragile.
  - Une seule copro RNC : AB1105360 au 154 BD GRENELLE (35 lots hab).
    Probe RNC live exhaustive (FREMICOURT/FRAGILE 75015) = 0 copro
    additionnelle sur ce bgid.
  - Les 54 logements manquants (89 BDNB - 35 RNC) sont structurellement
    hors-syndicat : RPLS/HLM probable (prefixe "MS103738" dans le nom
    copro suggere identifiant RPLS), foncieres institutionnelles, ou
    unites non encore immatriculees.

ETAT ACTUEL : 154 (copro AB1105360) fusee a tort dans le phantom 156
(qui a + de ventes). La copro est INVISIBLE dans le dashboard, bgid
F3HZ compte 89 BDNB (estimation totale du bati) au lieu des 35 lots
syndiques.

MECANISME : RE-POINT inversion (pattern A3 / fix_repoint_p2a /
fix_mp_cibles_horsrnc). 154 redevient principal absorbant 156. Champs
autoritatifs INCHANGES.

PARC : F3HZ passe de bgBdnb=89 (via 156 phantom) a bgRncLots
[AB1105360]=35 (via 154 copro) = **delta -54 = CORRECTION
STRUCTURELLE PIPELINE Sec 6 "lots RNC prioritaire"** (BDNB sur-compte
le bati entier, RNC ne reflete que la copro syndicale ; le -54 = 54
unites reelles hors-syndic, pas une perte fictive). Documente.

VENTES : 156 (6 v_log / 6 v_tot) relocalisees au rendu sous AB1105360.
154 (0 v_log) reste a 0. Champs ventes INCHANGES (relocalisation).

Cible : data/secteur_motte_picquet_light.json. Backup .pregrenelle.bak.
Dry-run par defaut.

Usage :
  python scripts/fix_grenelle_repoint.py            # DRY-RUN
  python scripts/fix_grenelle_repoint.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.pregrenelle.bak"

PHAN_CLE = "156|BOULEVARD|GRENELLE"
ANC_CLE = "154|BOULEVARD|GRENELLE"
IMMAT = "AB1105360"


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

    pa = by.get(PHAN_CLE)
    aa = by.get(ANC_CLE)
    cp = cbc.get(ANC_CLE)
    abort = []
    if pa is None:
        abort.append(f"phantom absent : {PHAN_CLE}")
    if aa is None:
        abort.append(f"anchor absent : {ANC_CLE}")
    if cp is None or cp.get("numero_immatriculation") != IMMAT:
        abort.append(f"copro {IMMAT} introuvable sur {ANC_CLE} "
                     f"(got {cp and cp.get('numero_immatriculation')})")
    if pa and aa and pa.get("batiment_groupe_id") \
            != aa.get("batiment_groupe_id"):
        abort.append(f"bgid divergent : {PHAN_CLE} "
                     f"{pa.get('batiment_groupe_id')} vs {ANC_CLE} "
                     f"{aa.get('batiment_groupe_id')}")
    # chaine dans phantom (devrait juste etre ANC ; pas d'autre orphelin)
    chain = [a["cle"] for a in light["adresses"]
             if a.get("_fusion_cible") == PHAN_CLE and a["cle"] != ANC_CLE]
    if chain:
        abort.append(f"chaine sous {PHAN_CLE} hors anchor : {chain}")
    already = (aa and not (aa.get("_fusion_auto")
                           and aa.get("_fusion_cible") == PHAN_CLE))
    if already:
        abort.append(f"idempotence : {ANC_CLE} non fuse vers {PHAN_CLE} "
                     "(deja re-pointe ?)")

    parc0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pa2 = pby.get(PHAN_CLE)
    aa2 = pby.get(ANC_CLE)
    if not abort:
        # RE-POINT inversion : anchor devient principal, phantom secondaire
        aa2["_fusion_auto"] = None
        aa2["_fusion_cible"] = None
        aa2["_fusion_auto_sources"] = sorted(set(
            (aa2.get("_fusion_auto_sources") or []) + [PHAN_CLE]))
        aa2.setdefault("_fusion_auto_label", None)
        pa2["_fusion_auto"] = True
        pa2["_fusion_cible"] = ANC_CLE
        pa2["_fusion_auto_sources"] = None
        # syndic : si copro syn_ok et phantom sans
        if syn_ok(cp.get("syndic")) and not syn_ok(aa2.get("syndic")):
            aa2["syndic"] = cp.get("syndic")
            aa2["_syndic_src"] = "rnc_grp"
    parc1 = parc_model(patched)

    print("=" * 76)
    print(f"GRENELLE RE-POINT — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 76)
    print(f"  PHANTOM : {PHAN_CLE}  bgid={pa and pa.get('batiment_groupe_id')}"
          f"  vlog={pa and pa.get('nb_ventes_logement')}"
          f"  nblog_bdnb={pa and pa.get('nb_log_bdnb')}")
    print(f"  ANCHOR  : {ANC_CLE}  copro {IMMAT} "
          f"{cp and cp.get('nb_lots_habitation')} lots  "
          f"nom={(cp and cp.get('nom_copropriete'))!r}")
    print(f"  Parc modele F3HZ : "
          f"bgBdnb={pa and pa.get('nb_log_bdnb')} (phantom 156) -> "
          f"bgRncLots[{IMMAT}]={cp and cp.get('nb_lots_habitation')} "
          "(anchor 154 visible)")
    print(f"  Parc total MP : {parc0} -> {parc1} (delta {parc1-parc0:+d})")
    print(f"  Note : delta -54 = CORRECTION structurelle (PIPELINE Sec 6, "
          "lots RNC prioritaire). BDNB 89 sur-compte le complexe entier "
          "(12 adresses BAN, 10 niveaux, 2011), AB1105360 ne couvre que "
          "les 35 lots syndiques ; les 54 unites manquantes sont reelles "
          "mais structurellement hors-syndic (RPLS/HLM probable, prefixe "
          "MS103738 dans nom).")
    print("=" * 76)
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
    meta["_correctif_grenelle"] = (
        f"Re-point 156|BD|GRENELLE -> 154|BD|GRENELLE (AB1105360 35 "
        "lots syndiques, MS103738). 5e cas P2a (precedemment ecarte "
        "2026-05-20, re-instruit avec contexte BDNB complet) : bgid "
        "F3HZ-H1TK-FPME = complexe 2011 12 adresses BAN, 89 BDNB-log "
        "dont seulement 35 syndiques RNC. 156 (6 v_log) relocalisees "
        f"sous AB1105360. Parc {parc0}->{parc1} ({parc1-parc0:+d}) = "
        "correction structurelle PIPELINE Sec 6 (lots RNC prioritaire "
        "sur estimation BDNB du complexe entier). Les 54 unites "
        "manquantes sont structurellement hors-syndicat (RPLS/HLM "
        "probable, foncieres institutionnelles, non-imm), aucune copro "
        "RNC additionnelle trouvee sur Fremicourt/Pere Fragile 75015.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name}")


if __name__ == "__main__":
    main()
