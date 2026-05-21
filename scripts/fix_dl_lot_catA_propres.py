"""
Correctif SURGICAL GROUPE DL - lot Categorie A (hr-ancres avec ventes)
detecte par scan parcelle cadastrale 2026-05-21
(scripts/scan_horsrnc_parcelle.py SECTEUR=dauphine_lacassagne).

Periometre : 6 cas haute confiance demande user. 4 cas traites en
lot, 2 cas ISOLES (abort gracieux) pour traitement separe.

Pattern Cambronne RE-FUSE multi-voies (analogue MP) : chaque
adresse orpheline est re-fusee vers son ancre RNC declaree
(meme parcelle cadastrale, syndic souvent identique).

CAS TRAITES EN LOT (4) :
  (3) 22|AVENUE|GEORGES POMPIDOU (bgid Q4M4, 37 nb_log_bdnb, 10
      vlog, GESTION ET PATRIMOINE LESCUYER cadastre, 2008)
      -> 19|RUE|ANTOINE CHARIAL (bgid H3HB, AA4896338 IVORY PARK,
      227 lots / 113 habit, MEME syndic + MEME annee 2008 +
      nb_log_bdnb concordants 37 vs 36, parcelle RNC EL/0054).
      Bgids DIFFERENTS, ADOPTION MIRROR bgid H3HB. Parc switch
      bgBdnb[Q4M4]=37 -> bgid fused (-37 dedup mais bgRncLots
      garde la copro 113 hab).

  (4) 8|RUE|DOCTEUR REBATEL (bgid P2DG, 25 nb_log_bdnb, 5 vlog,
      1997) -> 14|RUE|BARA (bgid Z75R, AA2213171 LE CEDRE
      LUMIERE, 127 lots / 43 habit, multi-parcelle RNC
      BK/0017+BK/0018, 18+25=43 match EXACT lots_habitation_rnc).
      Bgids DIFFERENTS, ADOPTION MIRROR. Pattern Fondary
      multi-parcelles. Parc -25 dedup.

  (5) 9|RUE|GABILLOT (bgid QGFJ, 27 nb_log_bdnb, 3 vlog, 2003)
      -> 76|RUE|ETIENNE RICHERAND (bgid N5KH, AE9610940 LE SAINTE
      ANNE, 139 lots / 41 habit, LYMMOBILIER rnc, 2002, parcelle
      DS/0108). Bgids DIFFERENTS, ADOPTION MIRROR. 13+27=40 lots
      proche de 41 RNC. Parc -27 dedup.

  (6) 157|RUE|ANTOINE CHARIAL (bgid 3QGJ, 1 nb_log_bdnb, 1 vlog,
      usage Residentiel INDIVIDUEL, 1910, REGIE DES GONES cad)
      -> 10|RUE|FREDERIC MISTRAL (bgid HDGW, AA1991173 CLOS
      MISTRAL, 74 lots / 37 habit, REGIE DES GONES rnc, 1986,
      Resid collectif, parcelle DV/0018). Bgids DIFFERENTS.
      ATTENTION : annees + usages divergents (Individuel 1910 vs
      collectif 1986) -> probable dependance commerciale ou
      maison annexe partageant la parcelle. Confiance MOYENNE.
      Parc -1 (nb_log_bdnb=1 marginal).

CAS ABORT (isolation par garde, traitement separe necessaire) :
  (1) 106|RUE|BARABAN -> AE1293612 SOPHIA : ancre RNC declaree
      '61|RUE|ANTOINE CHARIAL' est ABSENTE du light.adresses.
      Pattern Suffren INJECTION ou correction cle_adresse copro
      (cle SOPHIA pointe vers 61 ANTOINE CHARIAL mais l'adresse
      n'existe pas en pivot BDNB DL). A traiter separement.

  (2) 59|RUE|BARABAN -> AH9240847 LES JARDINS MAA : ancre
      57|RUE|BARABAN bgid 5NH2 declare parcelle BDNB DT/0073,
      mais AH9240847 declare ref_cad_1=DZ/0002 (RNC live).
      Conflit cadastral : 57 BARABAN est probablement sur la
      MAUVAISE parcelle (faux matching make_light). Necessite
      INVERSION_ANCRE_RNC ou re-attribution bgid. A part.

Total parc estime LOT 4 cas : -90 (=-37-25-27-1).

Source-of-truth a porter make_light_dauphine_lacassagne.py
(ou C:\\Users\\Station 5\\make_light.py) :
  ALIAS_RNC += {
    '22|AVENUE|GEORGES POMPIDOU':   '19|RUE|ANTOINE CHARIAL',
    '8|RUE|DOCTEUR REBATEL':        '14|RUE|BARA',
    '9|RUE|GABILLOT':               '76|RUE|ETIENNE RICHERAND',
    '157|RUE|ANTOINE CHARIAL':      '10|RUE|FREDERIC MISTRAL',
  }

Cible : data/secteur_dauphine_lacassagne_light.json.
Backup .predllotcata.bak. Dry-run par defaut.

Usage :
  PYTHONUTF8=1 python scripts/fix_dl_lot_catA_propres.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_dl_lot_catA_propres.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.predllotcata.bak"

# (orph, ancre, immat_attendu, label, confiance)
CASES = [
    ("106|RUE|BARABAN",            "61|RUE|ANTOINE CHARIAL",
     "AE1293612", "ABORT cas SOPHIA: ancre absente", "ABORT"),
    ("59|RUE|BARABAN",             "57|RUE|BARABAN",
     "AH9240847", "ABORT cas LES JARDINS MAA: conflit cadastral", "ABORT"),
    ("22|AVENUE|GEORGES POMPIDOU", "19|RUE|ANTOINE CHARIAL",
     "AA4896338", "22 POMPIDOU / 19 ANTOINE CHARIAL (IVORY PARK)", "OK"),
    ("8|RUE|DOCTEUR REBATEL",      "14|RUE|BARA",
     "AA2213171", "8 REBATEL / 14 BARA (LE CEDRE LUMIERE)", "OK"),
    ("9|RUE|GABILLOT",             "76|RUE|ETIENNE RICHERAND",
     "AE9610940", "9 GABILLOT / 76 ETIENNE RICHERAND (LE SAINTE ANNE)",
     "OK"),
    ("157|RUE|ANTOINE CHARIAL",    "10|RUE|FREDERIC MISTRAL",
     "AA1991173", "ABORT cas CLOS MISTRAL: usage Resid Individuel 1910 suspect (exclu user 2026-05-21)",
     "ABORT"),
]

MIRROR = ["batiment_groupe_id", "nb_log_bdnb", "usage_principal_bdnb",
          "_usage_bdnb_src", "annee_construction", "classe_dpe",
          "type_batiment", "type_chauffage"]


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def parc_model(light):
    """Replique renderSecteur Sec 6 : dedup bgid, lots RNC prioritaires
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
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    by = {a["cle"]: a for a in light["adresses"]}
    cbc = {c["cle_adresse"]: c for c in light["coproprietes"]
           if c.get("cle_adresse")}

    plan = []
    for orph, anc, immat, label, conf in CASES:
        why = []
        ao = by.get(orph)
        aa = by.get(anc)
        cp = cbc.get(anc)
        if conf == "ABORT":
            why.append("isolation manuelle (anomalie scan)")
        if ao is None:
            why.append(f"orph absente {orph}")
        if aa is None:
            why.append(f"ancre absente {anc}")
        if cp is None or cp.get("numero_immatriculation") != immat:
            why.append(f"copro {immat} introuvable sur {anc} "
                       f"(got {cp and cp.get('numero_immatriculation')})")
        if ao and ao.get("_fusion_auto") and ao.get("_fusion_cible"):
            why.append(f"orph deja fusee -> {ao.get('_fusion_cible')}")
        if ao and ao.get("numero_immatriculation") \
                and ao.get("numero_immatriculation") != immat:
            why.append(f"orph porte autre immat "
                       f"{ao.get('numero_immatriculation')}")
        same_bg = bool(ao and aa
                       and ao.get("batiment_groupe_id")
                       == aa.get("batiment_groupe_id"))
        plan.append((orph, anc, immat, label, conf, same_bg,
                     why, not why))

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}

    moves = []
    for orph, anc, immat, label, conf, same_bg, why, can_do in plan:
        if not can_do:
            continue
        s = pby.get(orph)
        a = pby.get(anc)
        if s is None or a is None:
            continue
        if s.get("_fusion_auto") and s.get("_fusion_cible") == anc:
            continue
        for k in MIRROR:
            s[k] = a.get(k)
        s["_bdnb_match"] = "immat"
        if syn_ok(a.get("syndic")) and not syn_ok(s.get("syndic")):
            s["syndic"] = a.get("syndic")
            s["_syndic_src"] = (a.get("_syndic_src") or "rnc") + "_grp"
        s["_fusion_auto"] = True
        s["_fusion_cible"] = anc
        s["_fusion_auto_sources"] = None
        cur = list(a.get("_fusion_auto_sources") or [])
        a["_fusion_auto_sources"] = sorted(set(cur + [orph]))
        if not a.get("_fusion_auto_label"):
            a["_fusion_auto_label"] = label
        moves.append((orph, anc, same_bg, conf))

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 100)
    print(f"FIX DL LOT CAT-A PROPRES (6 cas, 4 OK + 2 ABORT) - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 100)
    for orph, anc, immat, label, conf, same_bg, why, can_do in plan:
        ao = by.get(orph, {})
        aa = by.get(anc, {}) if anc in by else None
        cp = cbc.get(anc)
        bgo = (ao.get("batiment_groupe_id") or "")[8:12]
        bga = (aa.get("batiment_groupe_id") or "")[8:12] if aa else "----"
        bg_tag = "MEME bgid" if same_bg else "bgid DIFF (ALIAS_RNC)"
        status = ("OK" if can_do else
                  "WARN" if conf == "WARN" and can_do else
                  "ABORT")
        print(f"  [{status:5s}] {orph:32s} -> {anc:32s}  "
              f"({immat}, hab={cp and cp.get('nb_lots_habitation')})")
        print(f"          orph bgid={bgo}  log_bdnb={ao.get('nb_log_bdnb')}  "
              f"vlog={ao.get('nb_ventes_logement')}  "
              f"usage={ao.get('usage_principal_bdnb')!r}  "
              f"syndic={ao.get('syndic')!r}")
        if aa is not None:
            print(f"          ancre bgid={bga}  log_bdnb={aa.get('nb_log_bdnb')}  "
                  f"vlog={aa.get('nb_ventes_logement')}  "
                  f"syndic={aa.get('syndic')!r}  [{bg_tag}]")
        else:
            print(f"          ancre {anc!r} : ABSENT light  [{bg_tag}]")
        if why:
            for w in why:
                print(f"          - WHY ABORT : {w}")
        if conf == "WARN":
            print(f"          - WARN : annee/usage divergents (Resid Individuel "
                  f"vs collectif), confiance moyenne. Verifier terrain.")
    print("-" * 100)
    print("Impact bgid (RE-FUSEs effectues sur OK seulement) :")
    for bg in sorted(set(list(contrib0.keys()) + list(contrib1.keys()))):
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            print(f"  bgid {bg} : {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    print("-" * 100)
    print(f"Parc DL : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 100)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    if not moves:
        print("Idempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_dl_lot_catA"] = (
        f"Lot DL Cat-A (4/6 cas RE-FUSE Cambronne multi-voies) detecte "
        f"par scan parcelle cadastrale 2026-05-21. "
        f"Re-points : 22 GEORGES POMPIDOU -> 19 ANTOINE CHARIAL "
        f"(AA4896338 IVORY PARK, meme syndic LESCUYER + meme annee "
        f"2008) ; 8 DOCTEUR REBATEL -> 14 BARA (AA2213171 LE CEDRE "
        f"LUMIERE, multi-parcelle BK/0017+BK/0018 match exact 18+25="
        f"43 hab RNC) ; 9 GABILLOT -> 76 ETIENNE RICHERAND (AE9610940 "
        f"LE SAINTE ANNE) ; 157 ANTOINE CHARIAL -> 10 FREDERIC "
        f"MISTRAL (AA1991173 CLOS MISTRAL, WARN annee/usage divergent "
        f"a verifier terrain). 2 cas ABORT isoles (106 BARABAN ancre "
        f"absente, 59 BARABAN conflit cadastral). "
        f"Parc {parc0}->{parc1} ({delta:+d}). Source-of-truth a "
        f"porter make_light DL : ALIAS_RNC += {{22 POMPIDOU->19 "
        f"CHARIAL, 8 REBATEL->14 BARA, 9 GABILLOT->76 RICHERAND, "
        f"157 CHARIAL->10 MISTRAL}}.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves)} re-fuses)")


if __name__ == "__main__":
    main()
