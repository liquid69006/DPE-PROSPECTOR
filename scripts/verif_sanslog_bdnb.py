"""
Passe : adresses SANS logements du dashboard -> rapprochement BDNB
(LECTURE SEULE).

"Sans logements" = definition fidele au filtre du dashboard
(index.html:2137-2141) : NON (nb_log_bdnb>0) ET NON (copro liee via
coproByCle[a.cle] avec nb_lots_habitation>0).

Le snapshot local ne porte que le nb_log RNC (=0 par construction pour
ces adresses hors-RNC) : on interroge donc l'API ouverte BDNB.
  - batiment_groupe_ffo_bat  -> nb_log (fichiers fonciers / cadastre),
    usage_niveau_1_txt, nb_niveau, annee_construction
  - batiment_groupe_dpe_representatif_logement -> presence d'un DPE
    logement (signal residentiel) + type_batiment

Classement ETAPE 4 :
  A  BDNB confirme des logements (ffo nb_log>0 ou DPE logement present)
     -> donnee a mettre a jour
  B  adresse voisine AVEC logements (meme bgid qu'une adr avec lgts,
     OU < 30 m) -> doublon / entree secondaire potentielle
  C  BDNB confirme 0 logement (tertiaire / commerce / parking) -> normal
  D  inconnu (aucune donnee BDNB exploitable, pas de voisin) -> manuel

Cache reseau : data/_sanslog_bdnb_live.json (reprenable).
Sortie : stdout + data/verif_sanslog_bdnb_report.md. Aucune ecriture
des fichiers de donnees.
"""

import json
import time
import math
import collections
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
CACHE = ROOT / "data" / "_sanslog_bdnb_live.json"
REPORT = ROOT / "data" / "verif_sanslog_bdnb_report.md"

API = "https://api.bdnb.io/v1/bdnb/donnees"
PAUSE = 0.12
NR = {"non connu", "", None}


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dpe-verif/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return []


def fetch_bg(bg):
    ffo = get_json(f"{API}/batiment_groupe_ffo_bat?batiment_groupe_id=eq.{bg}")
    time.sleep(PAUSE)
    dpe = get_json(f"{API}/batiment_groupe_dpe_representatif_logement"
                   f"?batiment_groupe_id=eq.{bg}")
    time.sleep(PAUSE)
    f = ffo[0] if ffo else {}
    d = dpe[0] if dpe else {}
    return {
        "ffo_nb_log": f.get("nb_log"),
        "ffo_usage": f.get("usage_niveau_1_txt"),
        "ffo_nb_niveau": f.get("nb_niveau"),
        "ffo_annee": f.get("annee_construction"),
        "dpe_present": bool(d),
        "dpe_type": d.get("type_batiment_dpe") if d else None,
    }


def haversine(a, b):
    R = 6371000.0
    (la1, lo1), (la2, lo2) = a, b
    p = math.radians
    dla, dlo = p(la2 - la1), p(lo2 - lo1)
    x = (math.sin(dla / 2) ** 2 + math.cos(p(la1)) * math.cos(p(la2))
         * math.sin(dlo / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    ad, co = light["adresses"], light["coproprietes"]
    coproByCle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    snap = {r["batiment_groupe_id"]: r for r in bdnb}

    def lots(a):
        cp = coproByCle.get(a.get("cle"))
        return (cp.get("nb_lots_habitation") or 0) if cp else 0

    def has_log(a):
        return (a.get("nb_log_bdnb") or 0) > 0 or lots(a) > 0

    sans = [a for a in ad if not has_log(a)]
    avec = [a for a in ad if has_log(a)]
    bgids = sorted({a["batiment_groupe_id"] for a in sans
                    if a.get("batiment_groupe_id")})
    no_bg = [a for a in sans if not a.get("batiment_groupe_id")]

    # bgid -> adresse(s) AVEC logements sur ce meme bgid (1ere = libelle)
    bg_avec = collections.defaultdict(list)
    for a in avec:
        if a.get("batiment_groupe_id"):
            bg_avec[a["batiment_groupe_id"]].append(
                a.get("adresse") or a.get("cle"))
    # bgid -> nb adresses SANS log (complexes multi-entrees)
    bg_sans = collections.Counter(a["batiment_groupe_id"] for a in sans
                                  if a.get("batiment_groupe_id"))

    avec_gps = [((a["latitude"], a["longitude"]), a) for a in avec
                if a.get("latitude") and a.get("longitude")]

    print(f"Adresses totales         : {len(ad)}")
    print(f"Adresses SANS logements  : {len(sans)}")
    print(f"  avec batiment_groupe_id: {len(sans) - len(no_bg)}")
    print(f"  sans batiment_groupe_id: {len(no_bg)}")
    print(f"bgid distincts a verifier: {len(bgids)}")

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [b for b in bgids if b not in cache]
    print(f"bgid a interroger en LIVE: {len(todo)} (cache {len(cache)})")
    for i, bg in enumerate(todo, 1):
        cache[bg] = fetch_bg(bg)
        if i % 20 == 0 or i == len(todo):
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                             encoding="utf-8")
            print(f"  {i:3}/{len(todo)} bgid live")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    rows = []
    for a in sans:
        bg = a.get("batiment_groupe_id")
        ent = cache.get(bg, {})
        s = snap.get(bg, {})
        ffo_log = ent.get("ffo_nb_log")
        # voisin AVEC logements : meme bgid prioritaire, sinon < 30 m
        same_bg = len(bg_avec.get(bg, [])) > 0
        same_bg_addr = bg_avec[bg][0] if same_bg else None
        near, ndist = None, None
        if a.get("latitude") and a.get("longitude"):
            best = 1e9
            for (g, av) in avec_gps:
                dd = haversine((a["latitude"], a["longitude"]), g)
                if dd < best:
                    best, near = dd, av
            ndist = round(best) if near else None
        # classement (priorite A > B > C > D). La proximite geo seule est
        # trop faible en tissu urbain dense -> NON promue en doublon ;
        # seul le PARTAGE de batiment_groupe_id avec une adresse AVEC
        # logements est un vrai signal de doublon structurel.
        usage_connu = bool(ent.get("ffo_usage")
                           or s.get("usage_principal_bdnb_open")
                           or s.get("type_batiment_dpe")
                           or ent.get("ffo_nb_niveau"))
        if (ffo_log or 0) > 0 or ent.get("dpe_present"):
            cat = "A"                       # BDNB confirme des logements
        elif same_bg:
            cat = "B"                       # meme bati qu'une adr avec lgts
        elif usage_connu:
            cat = "C"                       # BDNB qualifie : non residentiel
        else:
            cat = "D"                       # aucune donnee BDNB -> manuel
        rows.append({
            "cle": a.get("cle"), "adresse": a.get("adresse") or a.get("cle"),
            "bg": bg, "match": a.get("_bdnb_match"),
            "ffo_log": ffo_log, "ffo_usage": ent.get("ffo_usage"),
            "ffo_niv": ent.get("ffo_nb_niveau"), "ffo_an": ent.get("ffo_annee"),
            "dpe": ent.get("dpe_present"), "dpe_type": ent.get("dpe_type"),
            "snap_usage": s.get("usage_principal_bdnb_open"),
            "snap_type": s.get("type_batiment_dpe"),
            "same_bg_avec": same_bg, "same_bg_addr": same_bg_addr,
            "near": near.get("adresse") if near else None,
            "ndist": ndist, "n_sans_meme_bg": bg_sans.get(bg, 1),
            "cat": cat,
        })

    by = collections.Counter(r["cat"] for r in rows)
    print("=" * 70)
    print("BILAN — adresses sans logements vs BDNB (live, lecture seule)")
    print("=" * 70)
    for k in "ABCD":
        print(f"  {k} : {by.get(k,0)}")
    print("=" * 70)

    def tbl(rs, cols):
        head = "| Adresse | bgid | " + cols + " |"
        sep = "|---|---|" + "---|" * (cols.count("|") + 1)
        o = [head, sep]
        for r in sorted(rs, key=lambda x: x["cle"]):
            if cols.startswith("ffo nb_log"):
                line = (f"{r['ffo_log'] if r['ffo_log'] is not None else '—'} | "
                        f"{r['ffo_usage'] or r['snap_usage'] or '—'} | "
                        f"{r['snap_type'] or r['dpe_type'] or '—'} | "
                        f"niv {r['ffo_niv'] or '—'} | DPE {'oui' if r['dpe'] else 'non'}")
            else:
                line = (f"{r['same_bg_addr'] or '—'} | "
                        f"{r['ndist'] if r['ndist'] is not None else '—'} m | "
                        f"{r['ffo_usage'] or r['snap_type'] or '—'}")
            o.append(f"| {r['adresse']} | `{r['bg']}` | {line} |")
        return "\n".join(o)

    A = [r for r in rows if r["cat"] == "A"]
    B = [r for r in rows if r["cat"] == "B"]
    C = [r for r in rows if r["cat"] == "C"]
    D = [r for r in rows if r["cat"] == "D"]

    md = [
        "# Adresses sans logements → rapprochement BDNB (live, lecture "
        "seule)\n",
        "« Sans logements » = filtre dashboard exact "
        "(`!(nb_log_bdnb>0) && !(copro.nb_lots_habitation>0)`). Le snapshot "
        "local ne porte que le `nb_log` RNC (=0 ici) → API ouverte "
        "`batiment_groupe_ffo_bat` (nb_log fichiers fonciers, usage) + "
        "`batiment_groupe_dpe_representatif_logement` (DPE logement).\n",
        "## Bilan\n", "| Catégorie | Adresses |", "|---|--:|",
        f"| **A** BDNB confirme des logements (donnée à corriger) | "
        f"**{len(A)}** |",
        f"| **B** voisin/​même bâti avec logements (doublon potentiel) | "
        f"{len(B)} |",
        f"| **C** BDNB confirme 0 logement (tertiaire/commerce/parking) | "
        f"{len(C)} |",
        f"| **D** inconnu (à qualifier manuellement) | {len(D)} |",
        f"\nTotal : {len(rows)} adresses sans logements, "
        f"{len(bgids)} bâtiments distincts. {len(no_bg)} sans bgid.\n",
        "## A — BDNB confirme des logements (à mettre à jour)\n",
        tbl(A, "ffo nb_log | usage | type | niveaux | DPE") if A
        else "_aucune_",
        "\n## B — même `batiment_groupe_id` qu'une adresse AVEC logements "
        "(doublon structurel : entrée secondaire du même bâtiment)\n",
        tbl(B, "adresse AVEC lgts (même bgid) | dist géo | usage")
        if B else "_aucune_",
        "\n## C — BDNB confirme 0 logement (tertiaire/commerce/parking : "
        "normal) — échantillon 40\n",
        f"_{len(C)} adresses → bâtiments non résidentiels qualifiés par "
        "BDNB. Plusieurs n° de rue d'un même immeuble de bureaux/commerce "
        "= normal._\n",
        tbl(C[:40], "ffo nb_log | usage | type | niveaux | DPE") if C
        else "_aucune_",
        "\n## D — inconnu (qualification manuelle)\n",
        tbl(D, "ffo nb_log | usage | type | niveaux | DPE") if D
        else "_aucune_",
        "",
    ]
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"Rapport écrit : {REPORT}")
    print(f"Cache         : {CACHE}")


if __name__ == "__main__":
    main()
