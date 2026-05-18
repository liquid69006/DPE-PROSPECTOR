"""
ETAPE 4 (dry-run) : les copros secteur INVISIBLES detectees par la passe
hors-RNC -> BDNB sont-elles rattachables proprement ?

Pour chaque copro invisible (R_INV) on evalue, en repliquant EXACTEMENT
la dedup parc de renderSecteur() (index.html : cle bg:<bgid>, valeur =
somme des lots RNC des copros du bati, sinon nb_log_bdnb) :

  - bgid de rattachement (via l'adresse hors-RNC qui le porte)
  - collision SIBLING : une autre copro DEJA visible occupe-t-elle ce
    meme bgid ? -> rattacher ferait sommer ses lots a ceux deja comptes
    (risque de double comptage / inflation parc)
  - collision CLE : copro.cle_adresse est-il deja une cle d'adresse ?
    (par construction non, sinon elle serait visible — on verifie quand
     meme la forme base/suffixe)
  - impact parc : valeur bg AVANT (bgBdnb) vs APRES (somme lots RNC)

Verdict par copro : PROPRE / RISQUE-SIBLING / DEJA-COMPTE.
Lecture seule, aucune ecriture des fichiers de donnees.
"""

import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
CACHE = ROOT / "data" / "_horsrnc_bdnb_live.json"
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
OUT = ROOT / "data" / "rattach_horsrnc_dryrun.md"
NR = {"non connu", "", None}


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    ad, co = light["adresses"], light["coproprietes"]

    copro = {c["numero_immatriculation"]: c for c in co
             if c.get("numero_immatriculation")}
    snap_principal = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                      for r in bdnb}
    cle_adresse_exact = {c.get("cle_adresse") for c in co if c.get("cle_adresse")}
    addr_cles = {a.get("cle") for a in ad}

    def visible(im):
        c = copro.get(im)
        return bool(c) and c.get("cle_adresse") in addr_cles

    # immat live/snapshot par bgid
    bg_immats = {}
    for bg, ent in cache.items():
        s = set(ent.get("immats") or [])
        sp = snap_principal.get(bg)
        if sp not in NR:
            s.add(sp)
        bg_immats[bg] = s

    # --- Reproduction EXACTE de la dedup parc renderSecteur() ---
    # immatBg : immat -> 1er bgid ou la copro VISIBLE apparait (lots>0)
    # bgRncLots : bgid -> {immat: lots}   ; bgBdnb : bgid -> nb_log_bdnb
    coproByCle = {}
    for c in co:
        if c.get("cle_adresse"):
            coproByCle[c["cle_adresse"]] = c
    immatBg, bgRncLots, bgBdnb = {}, {}, {}
    for a in ad:
        bg = a.get("batiment_groupe_id")
        cp = coproByCle.get(a.get("cle"))
        im = (cp.get("numero_immatriculation") or cp.get("cle_adresse")
              or a.get("cle")) if cp else None
        lots = cp.get("nb_lots_habitation") if (
            cp and (cp.get("nb_lots_habitation") or 0) > 0) else 0
        if bg:
            if im and lots and lots > 0:
                immatBg.setdefault(im, bg)
                bgRncLots.setdefault(immatBg[im], {})[im] = lots
            if (a.get("nb_log_bdnb") or 0) > 0 and bg not in bgBdnb:
                bgBdnb[bg] = a["nb_log_bdnb"]

    def bgvalue(bg):
        if bgRncLots.get(bg):
            return sum(bgRncLots[bg].values())
        return bgBdnb.get(bg, 0)

    # adresses hors-RNC -> bgid
    hors = [a for a in ad if a.get("cle") not in cle_adresse_exact]
    bg_hors_addrs = collections.defaultdict(list)
    for a in hors:
        if a.get("batiment_groupe_id"):
            bg_hors_addrs[a["batiment_groupe_id"]].append(a)

    # copros invisibles reliees a un bgid hors-RNC (= R_INV)
    inv = {}
    for bg, addrs in bg_hors_addrs.items():
        for im in bg_immats.get(bg, ()):
            if im in copro and not visible(im):
                inv.setdefault(im, set()).add(bg)

    rows = []
    for im, bgs in inv.items():
        c = copro[im]
        lots = c.get("nb_lots_habitation_rnc") or c.get("nb_lots_habitation") or 0
        for bg in sorted(bgs):
            # copros DEJA visibles sur ce meme bgid (siblings)
            sib_vis = sorted(x for x in bg_immats.get(bg, ())
                             if x in copro and visible(x))
            # autres copros invisibles sur ce bgid
            sib_inv = sorted(x for x in bg_immats.get(bg, ())
                             if x in copro and not visible(x) and x != im)
            bv_before = bgvalue(bg)
            # APRES rattachement de toutes les copros (in)visibles du bati
            after_immats = {x for x in bg_immats.get(bg, ()) if x in copro
                            and (copro[x].get("nb_lots_habitation") or 0) > 0}
            bv_after = sum(copro[x]["nb_lots_habitation"] for x in after_immats) \
                if after_immats else bv_before
            cle_collision = (c.get("cle_adresse") in addr_cles)
            base = (c.get("cle_adresse") or "").split("#")[0]
            base_addr = base in addr_cles and base != c.get("cle_adresse")
            if sib_vis:
                verdict = "DEJA-COMPTE (bati deja compte via sibling visible)"
            elif cle_collision:
                verdict = "COLLISION-CLE"
            else:
                verdict = "PROPRE"
            rows.append({
                "immat": im, "nom": c.get("nom_copropriete"),
                "cle_adresse": c.get("cle_adresse"),
                "syndic": c.get("syndic"), "lots": lots, "bg": bg,
                "hors_addrs": [a.get("adresse") or a.get("cle")
                               for a in bg_hors_addrs[bg]],
                "sib_vis": [(x, copro[x].get("nom_copropriete"),
                             copro[x].get("nb_lots_habitation"))
                            for x in sib_vis],
                "sib_inv": sib_inv,
                "bv_before": bv_before, "bv_after": bv_after,
                "base_addr_exists": base_addr,
                "verdict": verdict,
            })

    rows.sort(key=lambda r: (r["verdict"], -r["lots"]))
    vc = collections.Counter(r["verdict"].split(" ")[0] for r in rows)
    n_copro = len({r["immat"] for r in rows})
    lots_propre = sum(r["lots"] for r in rows if r["verdict"] == "PROPRE")

    print("=" * 70)
    print("ETAPE 4 — rattachabilite des copros invisibles (dry-run)")
    print("=" * 70)
    print(f"Copros invisibles reliees par BDNB a une adr hors-RNC : {n_copro}")
    print(f"Lignes (copro × bgid)                                 : {len(rows)}")
    for k, v in vc.items():
        print(f"  {k:14} : {v}")
    print(f"Lots RNC rattachables PROPREMENT (sans collision)     : "
          f"{lots_propre}")
    print("=" * 70)

    def tbl(rs):
        o = ["| Copro (immat) | nom | cle_adresse | lots | bgid | "
             "adresses hors-RNC du bâti | sibling VISIBLE (→ déjà compté) | "
             "parc bg av.→ap. |",
             "|---|---|---|--:|---|---|---|---|"]
        for r in rs:
            sv = "<br>".join(f"{x[0]} {(x[1] or '')[:18]} ({x[2]})"
                             for x in r["sib_vis"]) or "—"
            ha = "<br>".join(r["hors_addrs"][:4]) + (
                f"<br>(+{len(r['hors_addrs'])-4})" if len(r["hors_addrs"]) > 4
                else "")
            o.append(
                f"| {r['immat']} | {(r['nom'] or '—')[:24]} | "
                f"`{r['cle_adresse']}` | {r['lots']} | `{r['bg']}` | {ha} | "
                f"{sv} | {r['bv_before']}→{r['bv_after']} |")
        return "\n".join(o)

    propre = [r for r in rows if r["verdict"] == "PROPRE"]
    deja = [r for r in rows if r["verdict"].startswith("DEJA")]
    coll = [r for r in rows if r["verdict"] == "COLLISION-CLE"]

    md = [
        "# ÉTAPE 4 — rattachabilité des copros invisibles (dry-run, "
        "lecture seule)\n",
        "Réplique la dedup parc exacte de `renderSecteur()` (clé "
        "`bg:<bgid>`, valeur = Σ lots RNC des copros du bâtiment sinon "
        "`nb_log_bdnb`). Aucune écriture.\n",
        "## Bilan\n", "| Verdict | Copros×bgid | Sens |", "|---|--:|---|",
        f"| **PROPRE** | {len(propre)} | bâti porté uniquement par des "
        "adresses hors-RNC : rattacher remplace `nb_log_bdnb` par les lots "
        "RNC (même clé `bg:`, **pas de double-comptage**) |",
        f"| **DÉJÀ-COMPTÉ** | {len(deja)} | un sibling RNC déjà visible "
        "occupe le même bâtiment : le bâti est déjà compté, rattacher "
        "**sommerait** les lots (inflation) — satellite/jumelle |",
        f"| **COLLISION-CLE** | {len(coll)} | `cle_adresse` déjà prise |",
        f"\nLots RNC rattachables proprement : **{lots_propre}** "
        f"({len({r['immat'] for r in propre})} copros).\n",
        "## PROPRE — rattachables sans collision ni double-comptage\n",
        tbl(propre) if propre else "_aucune_",
        "\n## DÉJÀ-COMPTÉ — bâti déjà compté via un sibling visible "
        "(NE PAS rattacher : double-comptage)\n",
        tbl(deja) if deja else "_aucune_",
        "\n## COLLISION-CLE\n",
        tbl(coll) if coll else "_aucune_",
        "",
    ]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"Rapport écrit : {OUT}")


if __name__ == "__main__":
    main()
