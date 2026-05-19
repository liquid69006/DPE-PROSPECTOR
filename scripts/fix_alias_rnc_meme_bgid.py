"""
Correctif LOT — ALIAS_RNC "meme bgid" (PARC-NEUTRE) : sous-ensemble
A-fort/parc-sur de l'audit (cf. data/audit_horsrnc_dvf_*.md,
scripts/audit_horsrnc_dvf.py). DRY-RUN par defaut, n'ecrit RIEN
sans --apply. Parametre SECTEUR.

Cible = adresse hr-actif (renderSecteur : non fusionnee, cle != toute
cle_adresse copro, sans immat, nb_ventes_logement>0) dont la copro
RNC reelle est identifiee par PREUVE FORTE :
  a) BDNB rel_batiment_groupe_rnc (cache _horsrnc_bdnb_live*) ->
     immat present dans coproprietes[] ; OU
  b) variante orthographique EXACTE de cle_adresse (AYRES<->AIRES,
     GAL<->GENERAL, ST<->SAINT, particules...).
ET dont l'ancre (copro.cle_adresse) :
  - existe comme adresse du light (principal rendu reel),
  - n'est pas elle-meme fusionnee,
  - porte le MEME batiment_groupe_id que la cible  <<< parc-neutre
  - != la cible.
Gardes : aucune adresse deja fusionnee DANS la cible (sinon orphelin) ;
copro a un numero_immatriculation ; cible non deja fusionnee.

Effet (miroir make_light ALIAS_RNC, meme bgid -> AUCUNE adoption de
bgid/usage, contrairement a fix_dupleix) : cible._fusion_auto=True
/_fusion_cible=ancre ; ancre._fusion_auto_sources += cible ; syndic
propage seulement si ancre syn_ok & cible non (idem fix_armonial).
Champs autoritatifs (bgid/nb_log_bdnb/_bdnb_match/usage/ventes_*)
INCHANGES. Au rendu : ventes de la cible relocalisees sous la copro,
cible sortie des "hors-RNC actifs". **Parc STRICTEMENT inchange**
(bgRncLots domine deja ce bgid : modele exige delta == 0, ABORT
sinon).

Usage :
  python scripts/fix_alias_rnc_meme_bgid.py           # DRY-RUN
  SECTEUR=motte_picquet python scripts/fix_alias_rnc_meme_bgid.py
  python scripts/fix_alias_rnc_meme_bgid.py --apply   # (apres validation)
"""

import os
import re
import sys
import json
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
A = importlib.import_module("audit_horsrnc_dvf")   # voie_key/norm/parc_model

SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
SUF = "" if SECTEUR == "dauphine_lacassagne" else "_" + SECTEUR
SHORT = "dauphine" if SECTEUR == "dauphine_lacassagne" else "motte"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
CACHE_A = ROOT / "data" / f"_horsrnc_bdnb_live{SUF}.json"
BAK = ROOT / "data" / f"secteur_{SECTEUR}_light.json.prealiasbg.bak"
REPORT = ROOT / "data" / f"dryrun_alias_rnc_meme_bgid_{SHORT}.md"
NR = {"non connu", "", None}


def syn_ok(s):
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def collect(light, bdnb, cache_a):
    ad, co = light["adresses"], light["coproprietes"]
    by_cle = {}
    for a in ad:
        by_cle.setdefault(a["cle"], a)
    cbi = {c["numero_immatriculation"]: c for c in co
           if c.get("numero_immatriculation")}
    cbc = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    snap_pri = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                for r in bdnb}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    fused_into = {a.get("_fusion_cible") for a in ad
                  if a.get("_fusion_auto") and a.get("_fusion_cible")}

    cle_norm = {}
    for c in co:
        if c.get("cle_adresse"):
            cle_norm.setdefault(A.voie_key(c["cle_adresse"]), []).append(c)
    addr_cles = {a["cle"] for a in ad}
    vis_copros = [c for c in co if c.get("cle_adresse") in addr_cles
                  and c["cle_adresse"] not in fused and c.get("latitude")
                  and c.get("numero_immatriculation")]

    targets = [a for a in ad
               if a["cle"] not in fused and a["cle"] not in cbc
               and not a.get("numero_immatriculation")
               and (a.get("nb_ventes_logement") or 0) > 0]

    rows, skip = [], []
    for a in targets:
        cle, bg = a["cle"], a.get("batiment_groupe_id")
        c = None
        via = None
        # a) BDNB rel
        ims = set((cache_a.get(bg, {}) or {}).get("immats") or [])
        sp = snap_pri.get(bg)
        if sp not in NR:
            ims.add(sp)
        hit = [i for i in sorted(ims) if i in cbi]
        if hit:
            c, via = cbi[hit[0]], "a_bdnb"
        else:
            # b) variante ortho exacte cle_adresse
            cand = [x for x in cle_norm.get(A.voie_key(cle), [])
                    if x.get("numero_immatriculation")]
            if len(cand) == 1:
                c, via = cand[0], "b_norm(cle_adresse)"
            elif len(cand) > 1:
                skip.append((cle, "b_norm ambigu (>1 copro)"))
                continue
        if not c and a.get("latitude"):
            # c) copro visible meme voie la plus proche <30 m. La
            # securite parc ne depend PAS du chemin de resolution :
            # elle est garantie par le filtre meme-bgid plus bas.
            tnum, tvoie = A.voie_key(cle)
            best, bd = None, 30.0
            for cc in vis_copros:
                if A.voie_key(cc["cle_adresse"])[1] != tvoie:
                    continue
                dd = A.hav(a["latitude"], a["longitude"],
                           cc["latitude"], cc["longitude"])
                if dd < bd:
                    bd, best = dd, cc
            if best:
                c, via = best, f"c_gps({bd:.0f}m)"
        if not c:
            continue
        anc = c.get("cle_adresse")
        ao = by_cle.get(anc)
        # gardes parc-neutre + anti-collision
        if not anc or ao is None:
            skip.append((cle, f"ancre absente light ({anc})"))
            continue
        if anc == cle:
            continue
        if ao.get("batiment_groupe_id") != bg:
            continue                         # != bgid -> hors lot (miroir)
        if ao.get("_fusion_auto") and ao.get("_fusion_cible"):
            skip.append((cle, f"ancre {anc} elle-meme fusionnee"))
            continue
        if cle in fused_into:
            skip.append((cle, "une adresse est fusionnee DANS la cible"))
            continue
        rows.append({
            "cle": cle, "adresse": a.get("adresse"), "bg": bg, "via": via,
            "immat": c["numero_immatriculation"], "anchor": anc,
            "copro": c.get("nom_copropriete"), "syndic": c.get("syndic"),
            "lots": c.get("nb_lots_habitation"),
            "vlog": a.get("nb_ventes_logement") or 0,
            "vtot": a.get("nb_ventes_total") or 0,
            "vpa": a.get("ventes_par_an") or {},
            "anc_syndic": ao.get("syndic"),
        })
    return rows, skip, by_cle


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    cache_a = json.loads(CACHE_A.read_text(encoding="utf-8")) \
        if CACHE_A.exists() else {}

    rows, skip, by_cle = collect(light, bdnb, cache_a)

    # modele parc : doit etre STRICTEMENT neutre
    parc0 = A.parc_model(light["adresses"], light["coproprietes"])
    patched = json.loads(LIGHT.read_text(encoding="utf-8"))
    pby = {x["cle"]: x for x in patched["adresses"]}
    for r in rows:
        s, d = pby[r["cle"]], pby[r["anchor"]]
        s["_fusion_auto"] = True
        s["_fusion_cible"] = r["anchor"]
        d["_fusion_auto_sources"] = sorted(
            set((d.get("_fusion_auto_sources") or []) + [r["cle"]]))
    parc1 = A.parc_model(patched["adresses"], patched["coproprietes"])
    neutral = (parc1 == parc0)
    vtot_log = sum(r["vlog"] for r in rows)
    vtot_all = sum(r["vtot"] for r in rows)

    hdr = (f"# DRY-RUN — lot ALIAS_RNC meme bgid (parc-neutre) — "
           f"{SECTEUR}\n")
    out = [hdr,
           f"Mode : {'APPLY' if apply else 'DRY-RUN'} · cas={len(rows)} · "
           f"parc {parc0} -> {parc1} (delta {parc1-parc0:+d}) · "
           f"parc-neutre={'OUI' if neutral else 'NON !!'}\n",
           f"Ventes relocalisees : {vtot_log} v_log / {vtot_all} v_tot "
           "(5 ans). Champs ventes INCHANGES (relocalisation au rendu).\n",
           "| # | Adresse cible (cle) | v_log | v_tot | ventes/an "
           "| → copro ancre (cle_adresse) | immat | syndic | lots | via |",
           "|--:|---|--:|--:|---|---|---|---|--:|---|"]
    for i, r in enumerate(sorted(rows, key=lambda x: (-x["vlog"], x["cle"])),
                          1):
        vpa = " ".join(f"{y}:{r['vpa'].get(y,0)}"
                       for y in ("2021", "2022", "2023", "2024", "2025")
                       if r["vpa"].get(y))
        out.append(
            f"| {i} | `{r['cle']}` | {r['vlog']} | {r['vtot']} | {vpa or '—'} "
            f"| `{r['anchor']}` | {r['immat']} | "
            f"{(r['syndic'] or '—')[:26]} | {r['lots']} | {r['via']} |")
    if skip:
        out += ["\n## Cibles EXCLUES du lot (gardes)\n",
                "| cle | raison |", "|---|---|"]
        for c, why in sorted(skip):
            out.append(f"| `{c}` | {why} |")
    REPORT.write_text("\n".join(out), encoding="utf-8")

    print(f"=== {SECTEUR} ===  cas={len(rows)}  "
          f"parc {parc0}->{parc1} ({parc1-parc0:+d})  "
          f"neutre={'OUI' if neutral else 'NON'}  "
          f"vlog={vtot_log} vtot={vtot_all}  exclus={len(skip)}")
    print(f"rapport: {REPORT.name}")

    if not apply:
        print("DRY-RUN : aucun fichier modifie.")
        return
    if not neutral:
        print("ABORT : modele parc NON neutre -> lot non sur, pas d'apply.")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    lby = {a["cle"]: a for a in light["adresses"]}
    for r in rows:
        s, d = lby[r["cle"]], lby[r["anchor"]]
        s["_fusion_auto"] = True
        s["_fusion_cible"] = r["anchor"]
        if syn_ok(r["anc_syndic"]) and not syn_ok(s.get("syndic")):
            s["syndic"] = r["anc_syndic"]
            s["_syndic_src"] = (d.get("_syndic_src") or "rnc") + "_grp"
        d["_fusion_auto_sources"] = sorted(
            set((d.get("_fusion_auto_sources") or []) + [r["cle"]]))
        d.setdefault("_fusion_auto_label", None)
    light.setdefault("metadata", {})["_correctif_alias_bgid"] = (
        f"Lot ALIAS_RNC meme bgid (parc-neutre) : {len(rows)} adresses "
        "hors-RNC a ventes DVF rattachees a leur copro RNC (preuve forte "
        "BDNB-rel/ortho exacte, meme batiment_groupe_id). Ventes "
        "relocalisees, parc STRICTEMENT inchange.")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde {BAK.name} ; ecrit {LIGHT.name} ({len(rows)} cas)")


if __name__ == "__main__":
    main()
