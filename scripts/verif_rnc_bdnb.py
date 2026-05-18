"""
Passe de verification globale RNC -> BDNB (LECTURE SEULE).

Pour chaque copropriete RNC "liee" a la BDNB (numero d'immatriculation
present dans le snapshot BDNB), on compare l'ensemble des
batiment_groupe_id que la BDNB rattache a ce numero d'immatriculation
avec ceux references par une adresse du jeu de donnees secteur.

L'ecart se decompose en DEUX problemes distincts qu'il ne faut pas
confondre :

  CATEGORIE A — Vraie fusion manquante
    La copro est presente dans le jeu (au moins un de ses bgid BDNB est
    reference par une adresse), mais la BDNB attribue a son immat un ou
    plusieurs bgid SUPPLEMENTAIRES non fusionnes. -> cible directe de la
    "passe de fusion".

  CATEGORIE B — Adresse copro absente du croisement
    AUCUN bgid BDNB de l'immat n'est reference par une adresse : la/les
    adresse(s) de la copro ne sont pas entrees dans le croisement des
    1166 adresses. Ce n'est pas un defaut de fusion mais un trou amont
    (geocodage / jointure adresse), generalement a fort volume de lgts.

Source : snapshot local data/bdnb_dauphine_lacassagne.json (aucun appel
reseau). Ne modifie aucun fichier de donnees. Sortie : stdout + rapport
Markdown data/verif_rnc_bdnb_report.md.
"""

import json
import collections
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
REPORT = ROOT / "data" / "verif_rnc_bdnb_report.md"

NON_RENSEIGNE = {"non connu", "", None}


def charger():
    return (json.loads(BDNB.read_text(encoding="utf-8")),
            json.loads(LIGHT.read_text(encoding="utf-8")))


def analyser(bdnb, light):
    bg_meta = {}
    immat_to_bg = collections.defaultdict(set)
    for r in bdnb:
        bgid = r["batiment_groupe_id"]
        bg_meta[bgid] = r
        im = r.get("numero_immat_principal")
        if im not in NON_RENSEIGNE:
            immat_to_bg[im].add(bgid)

    secteur_bgids = {a["batiment_groupe_id"]
                     for a in light["adresses"] if a.get("batiment_groupe_id")}

    rows = []
    for c in light["coproprietes"]:
        im = c.get("numero_immatriculation")
        if not im or im not in immat_to_bg:
            continue
        bset = immat_to_bg[im]
        present = bset & secteur_bgids
        missing = bset - secteur_bgids
        if not missing:
            continue
        cat = "A" if present else "B"
        rows.append({
            "cat": cat,
            "immat": im,
            "nom": c.get("nom_copropriete"),
            "cle_adresse": c.get("cle_adresse"),
            "lots_rnc": c.get("nb_lots_habitation_rnc"),
            "n_bdnb": len(bset),
            "n_present": len(present),
            "n_missing": len(missing),
            "missing_log": sum((bg_meta[g].get("nb_log") or 0) for g in missing),
            "missing_adr": [
                (g, bg_meta[g].get("libelle_adr_principale_ban"),
                 bg_meta[g].get("nb_log") or 0)
                for g in sorted(missing)
            ],
        })
    return rows, bg_meta, secteur_bgids, len(light["coproprietes"]), len(immat_to_bg)


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").upper().strip())


def _numbase(n):
    m = re.match(r"\d+", n or "")
    return m.group(0) if m else (n or "")


def _haversine(a, b):
    R = 6371000.0
    (la1, lo1), (la2, lo2) = a, b
    p = math.radians
    dla, dlo = p(la2 - la1), p(lo2 - lo1)
    x = (math.sin(dla / 2) ** 2
         + math.cos(p(la1)) * math.cos(p(la2)) * math.sin(dlo / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))


def diagnostiquer_B(rows_B, light):
    """Sous-classe la categorie B en 4 causes racines."""
    ad = light["adresses"]
    ad_by_cle = {a.get("cle"): a for a in ad}
    ad_gps = [(a.get("latitude"), a.get("longitude")) for a in ad
              if a.get("latitude") and a.get("longitude")]
    cle_by_idx = [a for a in ad if a.get("latitude") and a.get("longitude")]
    cp_by_immat = {c.get("numero_immatriculation"): c
                   for c in light["coproprietes"]}

    buckets = {"B1a": [], "B1b": [], "B2": [], "B3": []}
    for r in rows_B:
        cle = r["cle_adresse"]
        c = cp_by_immat.get(r["immat"], {})
        if cle in ad_by_cle:
            buckets["B3"].append(r)            # cle exacte deja prise (autre copro)
            continue
        fuzzy = None
        if cle and cle.count("|") == 2:
            num, _typ, name = cle.split("|")
            for k in ad_by_cle:
                if k.count("|") == 2:
                    kn, _kt, knm = k.split("|")
                    if _numbase(kn) == _numbase(num) and _norm(knm) == _norm(name):
                        fuzzy = k
                        break
        if fuzzy:
            r["_voisin"] = fuzzy
            buckets["B2"].append(r)            # bis/ter ou type de voie replie
            continue
        la, lo = c.get("latitude"), c.get("longitude")
        best, near = 1e9, None
        if la and lo:
            for (al, ao), arow in zip(ad_gps, cle_by_idx):
                dd = _haversine((la, lo), (al, ao))
                if dd < best:
                    best, near = dd, arow
        r["_dist"] = round(best) if near else None
        r["_near"] = near.get("cle") if near else None
        if near and best <= 25:
            buckets["B1b"].append(r)           # numero absent, voisin <25m
        else:
            buckets["B1a"].append(r)           # vrai trou isole
    return buckets


def fmt_diag(rows, cols, top=None):
    out = ["| Immat | Copropriété | clé_adresse RNC | " + cols + " |",
           "|---|---|---|---|"]
    for r in (rows if top is None else rows[:top]):
        extra = (f"{r.get('_voisin','')}" if "_voisin" in r
                 else f"{r.get('_near','')} (~{r.get('_dist','?')} m)"
                 if "_dist" in r else "")
        out.append(f"| {r['immat']} | {(r['nom'] or '—')[:36]} | "
                   f"`{r['cle_adresse']}` | {extra} |")
    return "\n".join(out)


def fmt_table(rows, key, top=20):
    out = ["| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | "
           "Lgts manq. | Bâtiments manquants |",
           "|--:|---|---|---|--:|--:|--:|--:|---|"]
    for i, r in enumerate(sorted(rows, key=key)[:top], 1):
        det = "<br>".join(f"`{g}` {adr} ({log} log)"
                          for g, adr, log in r["missing_adr"]) or "—"
        out.append(
            f"| {i} | {r['immat']} | {(r['nom'] or '—')[:38]} | "
            f"`{r['cle_adresse']}` | {r['n_bdnb']} | {r['n_present']} | "
            f"{r['n_missing']} | {r['missing_log']} | {det} |")
    return "\n".join(out)


def main():
    bdnb, light = charger()
    rows, bg_meta, secteur_bgids, n_copros, n_immat_bdnb = analyser(bdnb, light)

    A = [r for r in rows if r["cat"] == "A"]
    B = [r for r in rows if r["cat"] == "B"]
    snap = set(bg_meta)

    def s(rs, k):
        return sum(r[k] for r in rs)

    print("=" * 66)
    print("VERIFICATION RNC -> BDNB  (snapshot local, lecture seule)")
    print("=" * 66)
    print(f"Copros RNC (light)                            : {n_copros}")
    print(f"Immat distincts dans le snapshot BDNB         : {n_immat_bdnb}")
    print(f"Copros liees a ecart (total)                  : {len(rows)}")
    print(f"  A. Vraie fusion manquante                   : {len(A):3}  "
          f"-> {s(A,'n_missing')} bat / {s(A,'missing_log')} lgts")
    print(f"  B. Adresse copro absente du croisement      : {len(B):3}  "
          f"-> {s(B,'n_missing')} bat / {s(B,'missing_log')} lgts")
    print(f"bgid snapshot inutilises par une adresse      : {len(snap - secteur_bgids)}")
    print(f"bgid secteur absents du snapshot              : {len(secteur_bgids - snap)}")
    print("=" * 66)

    md = ["# Vérification globale RNC → BDNB — bilan (lecture seule)\n",
          "Source : snapshot local `data/bdnb_dauphine_lacassagne.json` "
          "(aucun appel API, reproductible via `scripts/verif_rnc_bdnb.py`). "
          "Lien RNC↔BDNB = `numero_immat_principal`. Un `batiment_groupe_id` "
          "est *manquant* s'il n'est référencé par **aucune** adresse du jeu "
          "secteur.\n",
          "## Bilan chiffré\n",
          "| Indicateur | Valeur |", "|---|--:|",
          f"| Copros RNC (light) | {n_copros} |",
          f"| Immat distincts dans le snapshot BDNB | {n_immat_bdnb} |",
          f"| Copros liées avec écart | {len(rows)} |",
          f"| **A. Vraie fusion manquante** | **{len(A)} copros · "
          f"{s(A,'n_missing')} bât · {s(A,'missing_log')} lgts** |",
          f"| **B. Adresse copro absente du croisement** | **{len(B)} copros · "
          f"{s(B,'n_missing')} bât · {s(B,'missing_log')} lgts** |",
          f"| bgid snapshot inutilisés par une adresse | {len(snap - secteur_bgids)} |",
          f"| bgid secteur absents du snapshot | {len(secteur_bgids - snap)} |",
          "\n> **A** = cible directe d'une passe de fusion (copro déjà dans le "
          "jeu, bâtiment BDNB supplémentaire non rattaché). **B** = trou amont "
          "de croisement d'adresses (la copro n'a aucune adresse dans les 1166) "
          "— à corriger côté géocodage/jointure, pas par fusion.\n",
          "## Catégorie A — vraies fusions manquantes (toutes, "
          f"{len(A)} copros)\n",
          fmt_table(A, key=lambda x: (-x["missing_log"], -x["n_missing"]),
                    top=len(A)),
          "\n## Catégorie B — top 20 par logements manquants\n",
          fmt_table(B, key=lambda x: (-x["missing_log"], -x["n_missing"])),
          "\n## Catégorie B — top 20 par nombre de bâtiments manquants\n",
          fmt_table(B, key=lambda x: (-x["n_missing"], -x["missing_log"])),
          ""]

    bk = diagnostiquer_B(B, light)
    md += [
        "\n## Diagnostic catégorie B — causes racines\n",
        "| Sous-cause | Copros | Nature |", "|---|--:|---|",
        f"| **B1b** numéro copro absent des 1166, voisin même rue <25 m "
        f"| {len(bk['B1b'])} | univers d'adresses incomplet (bâti pourtant "
        f"présent en BDNB par immat) |",
        f"| **B1a** vrai trou isolé (aucune adresse 1166 < 25 m) "
        f"| {len(bk['B1a'])} | rue mal couverte / clé malformée |",
        f"| **B2** bis/ter ou type de voie replié sur le numéro de base "
        f"| {len(bk['B2'])} | normalisation de clé trop agressive |",
        f"| **B3** une adresse partagée par 2 copros "
        f"| {len(bk['B3'])} | modèle 1 clé → 1 bgid (collision) |",
        "\n> **Cause dominante (B1a+B1b = "
        f"{len(bk['B1a']) + len(bk['B1b'])} copros)** : les 1166 adresses ont "
        "été bâties à partir des lignes mutations/sources, pas exhaustivement "
        "depuis les adresses de référence RNC. Une copro sans mutation DVF "
        "récente à son numéro exact n'a aucune ligne adresse — alors que son "
        "bâtiment existe en BDNB via `numero_immat_principal`. **B2/B3 ("
        f"{len(bk['B2']) + len(bk['B3'])})** : la clé `NUM|TYPE|RUE` à un seul "
        "bgid perd le bis/ter et les adresses partagées.\n",
        "### B1b — numéro absent, adresse 1166 voisine (<25 m)\n",
        fmt_diag(bk["B1b"], "adresse 1166 la plus proche"),
        "\n### B1a — vrai trou isolé\n",
        fmt_diag(bk["B1a"], "adresse 1166 la plus proche"),
        "\n### B2 — bis/ter / type de voie replié\n",
        fmt_diag(bk["B2"], "clé 1166 absorbante"),
        "\n### B3 — adresse partagée par 2 copros\n",
        fmt_diag(bk["B3"], "—"),
        "\n## Recommandation\n",
        "Court-circuiter le croisement d'adresses pour l'attribution "
        "RNC↔BDNB : quand une copro a un lien propre `numero_immat_principal` "
        "en BDNB, rattacher directement ses `batiment_groupe_id` par immat "
        "(corrige B1a/B1b/B2, ~38/42). Pour B3, indexer les adresses par "
        "`(clé, immat)` au lieu de la clé seule afin de représenter deux "
        "copros à une même adresse postale.\n",
    ]
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"Rapport écrit : {REPORT}")


if __name__ == "__main__":
    main()
