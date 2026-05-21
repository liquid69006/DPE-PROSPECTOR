"""
Correctif SURGICAL GROUPE Motte-Picquet - 2 corrections en une passe :

CORRECTION 1 - Jean Rey Suffren (confirme terrain user 2026-05-21)
=================================================================
  16 AVENUE SUFFREN + 26 AVENUE SUFFREN -> 24 AVENUE SUFFREN
  (AA2459444 'JEAN REY SUFFREN HABITATION', 346 lots tot / 222 hab,
   ATRIUM GESTION PARIS 15, parcelle DM/0044).

  Cas plus complexe que Cambronne standard :
  - 16 SUFFREN (bgid S2NN, usage 'Tertiaire', 171 nb_log_bdnb) a
    deja une chain : _fusion_auto_sources=['18 AVENUE SUFFREN'],
    label '16/18 AVENUE SUFFREN'. -> migration chain : 18 SUFFREN
    doit suivre 16 vers 24 (re-direction _fusion_cible=16 -> 24).
  - 26 SUFFREN (bgid KHLY, Resid coll 16 nb_log_bdnb, 1920) -> RE-FUSE
    direct vers 24.

  Pattern Cambronne RE-FUSE multi-bgid avec chain transfer.
  Adoption MIRROR bgid FKPP (= ancre 24). Sources finales de 24 :
  ['20', '22', '16', '18', '26'] AVENUE SUFFREN. Label etendu.

  AA2950632 'Syndicat Principal Jean Rey Suffren' (973 lots) n'est
  PAS utilise ici (couvre tertiaire + parkings, moins precis que
  AA2459444 sur l'habitation).

  Effet parc (modele Sec 6) :
    - bgid S2NN : 16 Tertiaire ne contribuait pas bgBdnb -> 0
      apres fusion. -0 lgt.
    - bgid KHLY : 26 Resid coll 16 nb_log_bdnb sort bgBdnb -> -16 lgts.
    - 18 SUFFREN deja fused : pas de changement parc.
  Total CORR 1 : -16 lgts.

CORRECTION 2 - 3 doublons orthographiques (parc quasi-neutre)
=============================================================
  (a) '1||VILLA DE LA CROIX NIVERT' -> '1||VILLA CROIX NIVERT'
      (AB7934631 '1 VILLA CROIX NIVERT', 51 lots / 21 habit).
      ALIAS 'DE' manquant : variante orthographique.
      MEME bgid CBNA -> RE-FUSE direct trivial. Parc-neutre
      (bgRncLots[CBNA]=21 dominait deja, bgBdnb[CBNA]=19 ignore).

  (b) '4||VILLA JUGE' -> '4|VILLA|JUGE' (AE8291015 '4/6 VILLA
      JUGE 75015 PARIS', 89 tot / 45 habit). Correction cle
      malformee : type voie vide dans orph vs renseigne dans
      copro RNC. ANCRE ABSENTE light (la cle '4|VILLA|JUGE'
      n'existe pas en adresses[], seulement comme cle_adresse
      de copro). Pattern different : CORRECTION cle_adresse copro
      = on rebinde la copro vers la cle de l'orph (l'orph devient
      ancre RNC). Propagation immat + nb_lots_habit sur orph.
      Effet : orph bgBdnb[MTHY]=46 sort -> bgRncLots[MTHY][copro]
      =45. Delta = -1 lgt (switch BDNB->RNC autoritaire).

  (c) '103|QUAI|JACQUES CHIRAC' -> '103|QUAI|BRANLY' (AD0591701
      '103 quai Branly 75015 Paris', 83 tot / 51 habit). Le quai
      a ete renomme BRANLY -> JACQUES CHIRAC en 2017 ; le snapshot
      RNC garde l'ancien nom 'BRANLY' mais BAN/adresses utilisent
      maintenant JACQUES CHIRAC. ANCRE ABSENTE light. Meme
      mecanisme que (b) : correction cle_adresse copro pour
      pointer vers '103|QUAI|JACQUES CHIRAC'.
      Effet : orph bgBdnb[XMXX]=33 sort -> bgRncLots[XMXX][copro]
      =51. Delta = +18 lgts (switch BDNB->RNC).

  Total CORR 2 : -1 +18 = +17 lgts.

DELTA PARC GLOBAL : -16 + 17 = +1 lgt (quasi-neutre).

Cible : data/secteur_motte_picquet_light.json.
Backup .prejrdoublons.bak. Dry-run par defaut.

Source-of-truth a porter make_light_motte_picquet.py :
  ALIAS_RNC += {
    '16|AVENUE|SUFFREN'           : '24|AVENUE|SUFFREN',
    '18|AVENUE|SUFFREN'           : '24|AVENUE|SUFFREN',
    '26|AVENUE|SUFFREN'           : '24|AVENUE|SUFFREN',
    '1||VILLA DE LA CROIX NIVERT' : '1||VILLA CROIX NIVERT',
  }
  # Cas (b) et (c) : corriger directement la cle_adresse cote
  # snapshot RNC, OU ajouter normalisation cle dans make_light.

Usage :
  PYTHONUTF8=1 python scripts/fix_mp_jeanrey_doublons.py            # DRY-RUN
  PYTHONUTF8=1 python scripts/fix_mp_jeanrey_doublons.py --apply
"""

import re
import sys
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BAK = ROOT / "data" / "secteur_motte_picquet_light.json.prejrdoublons.bak"

# CORRECTION 1 : RE-FUSE Cambronne avec chain transfer
ANC_JEANREY = "24|AVENUE|SUFFREN"
IMMAT_JEANREY = "AA2459444"
ORPHS_JEANREY = ["16|AVENUE|SUFFREN", "26|AVENUE|SUFFREN"]
LABEL_JEANREY = "20/22/24/26 SUFFREN + 16/18 SUFFREN (JEAN REY HABITATION)"

# CORRECTION 2 : (a) RE-FUSE meme bgid ; (b)(c) correction cle_adresse copro
DOUBLONS_REFUSE = [   # (orph, ancre, immat, label, contexte)
    ("1||VILLA DE LA CROIX NIVERT", "1||VILLA CROIX NIVERT",
     "AB7934631", "1 VILLA (DE LA) CROIX NIVERT (ALIAS DE)"),
]
DOUBLONS_REBIND = [   # (orph, ancienne_cle_copro, immat, raison)
    ("4||VILLA JUGE",            "4|VILLA|JUGE",
     "AE8291015", "type voie vide -> renseigne (4|VILLA|JUGE)"),
    ("103|QUAI|JACQUES CHIRAC",  "103|QUAI|BRANLY",
     "AD0591701", "renommage quai BRANLY -> JACQUES CHIRAC (2017)"),
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
    cbc = {c.get("cle_adresse"): c for c in light["coproprietes"]
           if c.get("cle_adresse")}
    co_by_immat = {c.get("numero_immatriculation"): c
                   for c in light["coproprietes"]
                   if c.get("numero_immatriculation")}

    abort = []
    # Verif CORR 1
    if ANC_JEANREY not in by:
        abort.append(f"CORR1 ancre {ANC_JEANREY} absente")
    cp_jr = cbc.get(ANC_JEANREY)
    if not cp_jr or cp_jr.get("numero_immatriculation") != IMMAT_JEANREY:
        abort.append(f"CORR1 copro {IMMAT_JEANREY} non sur {ANC_JEANREY}")
    for orph in ORPHS_JEANREY:
        a = by.get(orph)
        if a is None:
            abort.append(f"CORR1 orph {orph} absente")
        elif a.get("_fusion_auto") and a.get("_fusion_cible") != ANC_JEANREY:
            abort.append(f"CORR1 orph {orph} fused ailleurs "
                         f"-> {a.get('_fusion_cible')}")
    # Verif CORR 2 doublons-refuse (cas a)
    for orph, anc, immat, _ in DOUBLONS_REFUSE:
        if orph not in by:
            abort.append(f"CORR2a orph {orph} absente")
        if anc not in by:
            abort.append(f"CORR2a ancre {anc} absente")
        cp = cbc.get(anc)
        if not cp or cp.get("numero_immatriculation") != immat:
            abort.append(f"CORR2a copro {immat} non sur {anc}")
    # Verif CORR 2 doublons-rebind (cas b, c)
    for orph, old_cle, immat, _ in DOUBLONS_REBIND:
        if orph not in by:
            abort.append(f"CORR2b orph {orph} absente")
        cp = co_by_immat.get(immat)
        if not cp:
            abort.append(f"CORR2b copro {immat} introuvable")
        elif cp.get("cle_adresse") != old_cle:
            abort.append(f"CORR2b copro {immat} cle_adresse "
                         f"{cp.get('cle_adresse')!r} != {old_cle!r}")
        if by[orph].get("numero_immatriculation"):
            abort.append(f"CORR2b orph {orph} porte deja immat "
                         f"{by[orph].get('numero_immatriculation')}")

    parc0, contrib0 = parc_model(light)
    patched = copy.deepcopy(light)
    pby = {a["cle"]: a for a in patched["adresses"]}
    pcbc = {c.get("cle_adresse"): c for c in patched["coproprietes"]
            if c.get("cle_adresse")}
    pco_by_immat = {c.get("numero_immatriculation"): c
                    for c in patched["coproprietes"]
                    if c.get("numero_immatriculation")}

    moves_jr = []
    moves_doublons_a = []
    moves_doublons_b = []

    if not abort:
        # ------- CORR 1 Jean Rey -------
        pa_jr = pby[ANC_JEANREY]
        # Etape 1 : chain transfer pour 16 SUFFREN (qui a son propre
        # _fusion_auto_sources). Toutes les cles fused vers 16 doivent
        # etre re-pointees vers 24.
        chain_sources_jr = []
        for orph in ORPHS_JEANREY:
            s = pby.get(orph)
            existing = list(s.get("_fusion_auto_sources") or [])
            if existing:
                # cles fused vers cet orph -> migrer vers ancre 24
                for sub_cle in existing:
                    sub = pby.get(sub_cle)
                    if sub is not None:
                        sub["_fusion_cible"] = ANC_JEANREY
                        chain_sources_jr.append(sub_cle)
            # Re-fuse l'orph lui-meme
            for k in MIRROR:
                s[k] = pa_jr.get(k)
            s["_bdnb_match"] = "immat"
            if syn_ok(pa_jr.get("syndic")) and not syn_ok(s.get("syndic")):
                s["syndic"] = pa_jr.get("syndic")
                s["_syndic_src"] = (pa_jr.get("_syndic_src") or "rnc") + "_grp"
            s["_fusion_auto"] = True
            s["_fusion_cible"] = ANC_JEANREY
            s["_fusion_auto_sources"] = None
            s.pop("_fusion_auto_label", None)
            moves_jr.append(orph)
        # Update ancre 24 SUFFREN
        cur = list(pa_jr.get("_fusion_auto_sources") or [])
        all_sources = sorted(set(cur + moves_jr + chain_sources_jr))
        pa_jr["_fusion_auto_sources"] = all_sources
        pa_jr["_fusion_auto_label"] = LABEL_JEANREY

        # ------- CORR 2a RE-FUSE meme bgid (1 VILLA) -------
        for orph, anc, immat, label in DOUBLONS_REFUSE:
            s = pby[orph]; a = pby[anc]
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
            moves_doublons_a.append(orph)

        # ------- CORR 2b/c CORRECTION cle_adresse copro -------
        for orph, old_cle, immat, raison in DOUBLONS_REBIND:
            cp = pco_by_immat[immat]
            # Rebinde la copro vers la cle de l'orph (devient ancre)
            cp["cle_adresse"] = orph
            # Propage immat + lots_habit sur orph (= bug propag-immat similaire)
            s = pby[orph]
            s["numero_immatriculation"] = immat
            if cp.get("nb_lots_habitation"):
                s["nb_lots_habitation"] = cp["nb_lots_habitation"]
            if syn_ok(cp.get("syndic")) and not syn_ok(s.get("syndic")):
                s["syndic"] = cp["syndic"]
                s["_syndic_src"] = cp.get("_syndic_src") or "rnc"
            s["_bdnb_match"] = "immat"
            moves_doublons_b.append((orph, old_cle, immat, raison))

    parc1, contrib1 = parc_model(patched)
    delta = parc1 - parc0

    print("=" * 100)
    print(f"FIX MP LOT JEAN-REY + DOUBLONS - "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 100)
    print(f"CORR 1 : Jean Rey Suffren (ancre {ANC_JEANREY}, copro {IMMAT_JEANREY})")
    for orph in ORPHS_JEANREY:
        a0 = by.get(orph, {})
        print(f"  {orph:30s} -> {ANC_JEANREY}  "
              f"bgid_avant={(a0.get('batiment_groupe_id') or '')[8:12]}  "
              f"nb_log_bdnb={a0.get('nb_log_bdnb')}  "
              f"usage={a0.get('usage_principal_bdnb')!r}  "
              f"vlog={a0.get('nb_ventes_logement')}")
    pa_jr = pby[ANC_JEANREY] if not abort else None
    if pa_jr:
        print(f"  ancre {ANC_JEANREY} sources -> {pa_jr.get('_fusion_auto_sources')}")
        print(f"  ancre label                -> {pa_jr.get('_fusion_auto_label')!r}")
    print()
    print(f"CORR 2a : RE-FUSE meme bgid (1 VILLA CROIX NIVERT)")
    for orph, anc, immat, _ in DOUBLONS_REFUSE:
        a0 = by.get(orph, {})
        print(f"  {orph:30s} -> {anc:30s}  (immat {immat}, "
              f"bgid_meme={a0.get('batiment_groupe_id') == by.get(anc, {}).get('batiment_groupe_id')})")
    print()
    print(f"CORR 2b/c : CORRECTION cle_adresse copro (ancre absente light)")
    for orph, old_cle, immat, raison in DOUBLONS_REBIND:
        a0 = by.get(orph, {})
        print(f"  copro {immat} : cle_adresse {old_cle!r} -> {orph!r}")
        print(f"    {raison}")
        print(f"    orph bgid={(a0.get('batiment_groupe_id') or '')[8:12]} "
              f"nb_log_bdnb={a0.get('nb_log_bdnb')}")
    print("-" * 100)
    print("Impact bgid (deltas) :")
    bgs = sorted(set(list(contrib0.keys()) + list(contrib1.keys())))
    for bg in bgs:
        v0, k0 = contrib0.get(bg, (0, "-"))
        v1, k1 = contrib1.get(bg, (0, "-"))
        if v0 != v1 or k0 != k1:
            print(f"  bgid {bg} : {v0} ({k0}) -> {v1} ({k1}) "
                  f"= {v1 - v0:+d}")
    print("-" * 100)
    print(f"Parc MP : {parc0} -> {parc1} (delta {delta:+d})")
    print("=" * 100)

    if abort:
        print("ABORT (gardes) :")
        for w in abort:
            print(f"  - {w}")
        return
    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire.")
        return
    n_moves = len(moves_jr) + len(moves_doublons_a) + len(moves_doublons_b)
    if not n_moves:
        print("Idempotent : aucune modification.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = patched.setdefault("metadata", {})
    meta["_correctif_jeanrey_doublons"] = (
        f"Lot MP 2 corrections (1 passe) : CORR1 Jean Rey Suffren "
        f"(16+26 SUFFREN -> 24 SUFFREN AA2459444 JEAN REY HABITATION "
        f"346 lots, ATRIUM GESTION, parcelle DM/0044 ; chain "
        f"transfer 18 SUFFREN deja fused vers 16 re-direct vers 24, "
        f"label '20/22/24/26 SUFFREN + 16/18 SUFFREN HABITATION'). "
        f"CORR2 doublons orthographiques : (a) 1||VILLA DE LA CROIX "
        f"NIVERT -> 1||VILLA CROIX NIVERT (AB7934631, meme bgid CBNA, "
        f"ALIAS 'DE') ; (b) cle_adresse rebind 4|VILLA|JUGE -> 4||"
        f"VILLA JUGE (AE8291015, type voie vide -> renseigne) ; (c) "
        f"cle_adresse rebind 103|QUAI|BRANLY -> 103|QUAI|JACQUES "
        f"CHIRAC (AD0591701, renommage quai 2017). Parc "
        f"{parc0}->{parc1} ({delta:+d}). Source-of-truth a porter "
        f"make_light_motte_picquet.py : ALIAS_RNC + correction cle_"
        f"adresse snapshot RNC.")
    LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} ({len(moves_jr)} JR + "
          f"{len(moves_doublons_a)} doublon_a + "
          f"{len(moves_doublons_b)} cle_rebind)")


if __name__ == "__main__":
    main()
