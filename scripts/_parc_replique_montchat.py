"""
Replicateur PARC `secL` (Manche B1) -- PORT FIDELE de la replique 2-passes
de scripts/test_render_secteur.js lignes 357-433 (REBASE 2026-05-31,
post-refactor renderSecteur 2026-05-24).

Raison d'etre : le test_render_secteur.js EXTRAIT renderSecteur() d'index.html
par plages de lignes CODEES EN DUR (gotcha documente MEMORY). Ces plages ont
DERIVE (index.html edite depuis le 2026-05-31) -> le test leve actuellement
"Unexpected token '}'" AVANT de calculer secL, et ce, sur DL ET Montchat
(breakage PRE-EXISTANT, hors perimetre Manche B1 -- on ne touche pas index.html).

On reproduit donc ici le bloc `expected` du test (sa SOURCE D'AUTORITE interne
pour secL : la regle parc 2-passes), verbatim. Sur le light Montchat pre-B1
il doit rendre 15809 (== valeur secL Manche A). Lecture seule.

Usage : PYTHONUTF8=1 python scripts/_parc_replique_montchat.py [chemin_light]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data" / "secteur_montchat_light.json"

RESID = {"Residentiel collectif", "Residentiel individuel",
         "Résidentiel collectif", "Résidentiel individuel"}


def parc(path, asg=None):
    asg = asg or {}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    sd_ad = d.get("adresses", [])
    co = d.get("coproprietes", [])
    cbc = {}
    for c in co:
        if c.get("cle_adresse"):
            cbc[c["cle_adresse"]] = c

    def uResid(a):
        return bool(a) and (a.get("usage_principal_bdnb") in RESID)

    def effLog(a):
        t = (asg.get(a.get("cle")) or {}).get("type")
        if t == "mono":
            return 1
        if t in ("social", "bureaux"):
            return 0
        return a.get("nb_log_bdnb")

    shown = [a for a in sd_ad
             if not (a.get("_fusion_auto")
                     and (a.get("_fusion_cible") or a.get("_fusion_auto_target")))]

    immatBg, bgRnc, bgResid = {}, {}, {}
    for a in shown:
        bg = a.get("batiment_groupe_id") or None
        c = cbc.get(a.get("cle"))
        im = (c.get("numero_immatriculation") or c.get("cle_adresse")
              or a.get("cle")) if c else None
        if a.get("_nb_lots_habitation_override") is not None:
            lots = a["_nb_lots_habitation_override"]
        else:
            lots = c["nb_lots_habitation"] if (
                c and (c.get("nb_lots_habitation") or 0) > 0) else 0
        if bg and im and lots and lots > 0:
            if immatBg.get(im) is None:
                immatBg[im] = bg
            bgRnc.setdefault(immatBg[im], {})[im] = lots

    for a in shown:
        bg = a.get("batiment_groupe_id") or None
        c = cbc.get(a.get("cle"))
        if not bg or c or not uResid(a) or not ((a.get("nb_log_bdnb") or 0) > 0):
            continue
        t = (asg.get(a.get("cle")) or {}).get("type")
        if t in ("mono", "social", "bureaux"):
            continue
        if bgResid.get(bg) is None or a["nb_log_bdnb"] > bgResid[bg]:
            bgResid[bg] = a["nb_log_bdnb"]

    for a in shown:
        bg = a.get("batiment_groupe_id") or None
        c = cbc.get(a.get("cle"))
        if not bg or c or not uResid(a) or not ((a.get("nb_log_bdnb") or 0) > 0):
            continue
        if bgResid.get(bg) is not None:
            continue
        e = effLog(a)
        if e and e > 0:
            bgResid[bg] = e

    bgVal = {}
    for bg in set(list(bgRnc.keys()) + list(bgResid.keys())):
        if bgRnc.get(bg):
            bgVal[bg] = sum(bgRnc[bg].values())
        else:
            bgVal[bg] = bgResid.get(bg) or 0

    seen = set()
    expected = 0
    for a in shown:
        c = cbc.get(a.get("cle"))
        rnc = bool(c)
        k = None
        v = 0
        bg = a.get("batiment_groupe_id")
        if bg and (bgVal.get(bg) or 0) > 0 and (rnc or (effLog(a) or 0) > 0):
            k = "bg:" + bg
            v = bgVal.get(bg) or 0
        elif rnc:
            im = c.get("numero_immatriculation") or c.get("cle_adresse") or a.get("cle")
            if immatBg.get(im):
                k = "bg:" + immatBg[im]
                v = bgVal.get(immatBg[im]) or 0
            else:
                k = "rnc:" + str(im)
                if a.get("_nb_lots_habitation_override") is not None:
                    v = a["_nb_lots_habitation_override"]
                else:
                    v = c["nb_lots_habitation"] if (c.get("nb_lots_habitation") or 0) > 0 else 0
        elif uResid(a) and (a.get("nb_log_bdnb") or 0) > 0:
            k = "adr:" + str(a.get("cle"))
            v = effLog(a)
        if k and v and v > 0 and k not in seen:
            seen.add(k)
            expected += v
    return expected, len(shown)


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT)
    val, nshown = parc(p)
    print(f"parc secL (replique 2-passes) = {val}  (shown={nshown})  [{Path(p).name}]")
