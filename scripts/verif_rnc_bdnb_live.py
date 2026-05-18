"""
Passe de verification RNC -> BDNB *API LIVE* (LECTURE SEULE).

Objectif : valider que le snapshot local data/bdnb_dauphine_lacassagne.json
n'a pas filtre des batiments en amont. On interroge l'API ouverte BDNB
(api.bdnb.io, sans cle) table `rel_batiment_groupe_rnc` qui relie chaque
`batiment_groupe_id` a un `numero_immat` RNC. Pour chaque copro RNC du
secteur, on compare l'ensemble des bgid renvoyes par l'API LIVE a
l'ensemble du snapshot local.

Lecture seule : aucune ecriture de donnees. Sortie : stdout + rapport
data/verif_rnc_bdnb_live_report.md.

Requetes : filtre PostgREST `numero_immat=in.(...)` par lots -> ~14 GET.
"""

import json
import time
import collections
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
REPORT = ROOT / "data" / "verif_rnc_bdnb_live_report.md"

API = "https://api.bdnb.io/v1/bdnb/donnees"
PAUSE = 0.15
NON_RENSEIGNE = {"non connu", "", None}
# L'API ouverte plafonne les reponses anonymes a 10 lignes (limit/Range
# ignores, offset fonctionne). On interroge donc 1 immat par requete
# (eq.) : chaque copro a <=4 batiments -> jamais tronque.


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dpe-verif/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return []


def fetch_rel(immats):
    """immat -> {bgid} via rel_batiment_groupe_rnc, 1 requete eq. / immat."""
    out = collections.defaultdict(set)
    immats = sorted(set(immats))
    n = len(immats)
    for i, im in enumerate(immats, 1):
        rows, off = [], 0
        while True:                       # pagination defensive si == 10
            url = (f"{API}/rel_batiment_groupe_rnc"
                   f"?numero_immat=eq.{im}&offset={off}")
            page = get_json(url)
            rows += page
            if len(page) < 10:
                break
            off += 10
        for r in rows:
            bg = r.get("batiment_groupe_id")
            if bg:
                out[im].add(bg)
        if i % 50 == 0 or i == n:
            print(f"  {i:3}/{n} immats interroges")
        time.sleep(PAUSE)
    return out


def fetch_nb_log(bgids):
    """bgid -> nb_log via batiment_groupe_rnc, 1 requete eq. / bgid."""
    out = {}
    for bg in sorted(b for b in bgids if b):
        rows = get_json(f"{API}/batiment_groupe_rnc"
                        f"?batiment_groupe_id=eq.{bg}")
        if rows:
            out[bg] = rows[0].get("nb_log") or 0
        time.sleep(PAUSE)
    return out


def main():
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    light = json.loads(LIGHT.read_text(encoding="utf-8"))

    snap = collections.defaultdict(set)          # immat -> {bgid} snapshot
    for r in bdnb:
        im = r.get("numero_immat_principal")
        if im not in NON_RENSEIGNE:
            snap[im].add(r["batiment_groupe_id"])

    copros = {c["numero_immatriculation"]: c for c in light["coproprietes"]
              if c.get("numero_immatriculation")}
    immats = list(copros)
    print(f"Copros (immat) a verifier en LIVE : {len(immats)}")

    live = fetch_rel(immats)
    print(f"Immats avec >=1 relation live : {len(live)}")

    rows = []
    extra_bgids = set()
    for im in immats:
        s, l = snap.get(im, set()), live.get(im, set())
        only_live = l - s          # present API live, ABSENT du snapshot
        only_snap = s - l          # present snapshot, absent live
        if only_live or only_snap:
            extra_bgids |= only_live
            rows.append({
                "immat": im,
                "nom": copros[im].get("nom_copropriete"),
                "lots_rnc": copros[im].get("nb_lots_habitation_rnc"),
                "n_snap": len(s), "n_live": len(l),
                "only_live": sorted(only_live), "only_snap": sorted(only_snap),
            })

    nb_log = fetch_nb_log(extra_bgids) if extra_bgids else {}
    for r in rows:
        r["extra_log"] = sum(nb_log.get(g, 0) for g in r["only_live"])

    omissions = [r for r in rows if r["only_live"]]
    tot_extra_b = sum(len(r["only_live"]) for r in rows)
    tot_extra_l = sum(r["extra_log"] for r in rows)

    print("=" * 66)
    print("VERIFICATION RNC -> BDNB *API LIVE* vs snapshot local")
    print("=" * 66)
    print(f"Copros verifiees                  : {len(immats)}")
    print(f"Copros snapshot != live           : {len(rows)}")
    print(f"  dont snapshot a OMIS des bati    : {len(omissions)}")
    print(f"Batiments live absents du snapshot : {tot_extra_b} "
          f"(~{tot_extra_l} logements)")
    print(f"Batiments snapshot absents du live : "
          f"{sum(len(r['only_snap']) for r in rows)}")
    print("=" * 66)

    def tbl(rs, key, top=20):
        o = ["| # | Immat | Copropriete | snap | live | +bât | +lgts | "
             "bgid live manquants au snapshot |",
             "|--:|---|---|--:|--:|--:|--:|---|"]
        for i, r in enumerate(sorted(rs, key=key)[:top], 1):
            o.append(f"| {i} | {r['immat']} | {(r['nom'] or '—')[:34]} | "
                     f"{r['n_snap']} | {r['n_live']} | {len(r['only_live'])} | "
                     f"{r['extra_log']} | {' '.join(r['only_live']) or '—'} |")
        return "\n".join(o)

    md = ["# Vérification RNC → BDNB — API live vs snapshot (lecture seule)\n",
          "API ouverte `api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc` "
          "(sans clé), table de relation `numero_immat` ↔ "
          "`batiment_groupe_id`. Compare l'ensemble live à "
          "`data/bdnb_dauphine_lacassagne.json`.\n",
          "## Bilan\n", "| Indicateur | Valeur |", "|---|--:|",
          f"| Copros vérifiées | {len(immats)} |",
          f"| Copros snapshot ≠ live | {len(rows)} |",
          f"| **Copros où le snapshot a omis des bâtiments** | "
          f"**{len(omissions)}** |",
          f"| Bâtiments live absents du snapshot | {tot_extra_b} "
          f"(~{tot_extra_l} lgts) |",
          f"| Bâtiments snapshot absents du live | "
          f"{sum(len(r['only_snap']) for r in rows)} |",
          "\n## Top 20 — omissions du snapshot par logements\n",
          tbl(omissions, key=lambda x: (-x["extra_log"], -len(x["only_live"]))),
          "\n## Top 20 — omissions du snapshot par nombre de bâtiments\n",
          tbl(omissions, key=lambda x: (-len(x["only_live"]), -x["extra_log"])),
          ""]
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"Rapport écrit : {REPORT}")


if __name__ == "__main__":
    main()
