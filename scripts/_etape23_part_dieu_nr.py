"""
_etape23_part_dieu_nr.py
─────────────────────────────────────────────────────────────────
ETAPES 2, 3 et 4 du chantier "Part-Dieu NR". N'ECRIT JAMAIS
data/dauphine-lacassagne-sci.json — l'ecriture est l'etape 5.

  Etape 2 : candidats = couples (parcelle, siren) 6540 du 3e dont le
            BIEN tombe dans le polygone Part-Dieu (data/_perimetre_part_dieu.json)
  Etape 3 : enrichissement recherche-entreprises (siege / gerants / etat)
  Etape 4 : geocodage du SIEGE + arbitrage, puis 2 CSV pour Yann

ARBITRAGE DU SIEGE — seuil ASYMETRIQUE (regle metier 2) :
  On n'EXCLUT que si le geocodage est franc (score >= 0.60) ET que le
  point tombe dans Part-Dieu. Tout le reste est RETENU et marque
  siege_verifie=false avec un motif. Exclure a tort est la seule erreur
  couteuse (contrainte reglementaire entre agences).

Caches disque (reprenables, prefixe _ = artefact de pipeline) :
  data/_cache_ban_biens_pd.json
  data/_cache_entreprises_pd.json
  data/_cache_ban_sieges_pd.json

Sorties etape 4 (CSV ';' + BOM, Excel FR) :
  data/_part_dieu_nr_exclus.csv
  data/_part_dieu_nr_doute.csv
  data/_part_dieu_nr_candidats.json   (etat complet, entree de l'etape 5)

Usage :
  python scripts/_etape23_part_dieu_nr.py
"""

import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import http.client
from datetime import datetime

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
DATA   = os.path.join(RACINE, "data")
MAJIC  = r"C:\Users\Station 5\majic_locaux2_2025.parquet"
PERIM  = os.path.join(DATA, "_perimetre_part_dieu.json")

C_BIENS  = os.path.join(DATA, "_cache_ban_biens_pd.json")
C_ENT    = os.path.join(DATA, "_cache_entreprises_pd.json")
C_SIEGES = os.path.join(DATA, "_cache_ban_sieges_pd.json")

OUT_EXCLUS = os.path.join(DATA, "_part_dieu_nr_exclus.csv")
OUT_DOUTE  = os.path.join(DATA, "_part_dieu_nr_doute.csv")
OUT_ETAT   = os.path.join(DATA, "_part_dieu_nr_candidats.json")

BAN_CSV = "https://api-adresse.data.gouv.fr/search/csv/"
ENT_URL = "https://recherche-entreprises.api.gouv.fr/search"
PAUSE   = 0.22
SEUIL_BIEN  = 0.40      # identique au pipeline historique
SEUIL_SIEGE = 0.60      # plus strict : adresses de siege en texte libre
CSV_SEP = ";"
INSEE_3E, FORME_SCI = "69383", "6540"


# ── caches ────────────────────────────────────────────────────────
def charger(p):
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def sauver(p, d):
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


# ── geometrie ─────────────────────────────────────────────────────
def charger_polygones():
    d = json.load(io.open(PERIM, encoding="utf-8"))
    PD = unary_union([Polygon([(x, y) for x, y in ring]) for ring in d["polygones"]]).buffer(0)
    src = io.open(os.path.join(ICI, "majic_sci_2025.py"), encoding="utf-8").read()
    bloc = src[src.index("ZONES = {"):src.index("BAN_URL")]
    out = {}
    for nom in ("Dauphiné-Lacassagne", "Montchat"):
        i = bloc.index('"%s"' % nom)
        j = bloc.index("Polygon([", i)
        k = bloc.index("])", j)
        pts = re.findall(r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]", bloc[j:k])
        out[nom] = Polygon([(float(a), float(b)) for a, b in pts])
    return PD, out["Dauphiné-Lacassagne"], out["Montchat"], d.get("_surface_km2")


# ── BAN batch rendant le SCORE (le pipeline historique le jette) ──
def ban_batch(adresses, cache, label, cache_path):
    """Retourne {adresse: {lon, lat, score, label_ban}}. Cache disque, lots de 500."""
    todo = [a for a in adresses if a and a not in cache]
    print("   %s : %d adresses, %d deja en cache, %d a geocoder"
          % (label, len(adresses), len(adresses) - len(todo), len(todo)))
    ERRS = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)
    # BAN /search/csv/ rate-limite les gros lots enchaines : lots reduits +
    # respiration entre chaque. Constate le 2026-10-13 (HTTPError en serie).
    LOT = 200
    PAUSE_LOT = 2.0

    def appel(lot):
        # CSV correctement quote. Une adresse de siege peut contenir une virgule
        # ("LE BRITANNIA, ALLEE C 20 BD EUGENE DERUELLE ..."), ce qui faisait
        # repondre la BAN "400 Error in CSV file: TooManyFields" et empoisonnait
        # tout le lot, y compris apres sous-decoupage. majic_sci_2025.py:139-143
        # porte la meme faille, restee latente : les adresses de BIEN sont
        # construites depuis MAJIC et ne contiennent jamais de virgule.
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["adresse"])
        for a in lot:
            w.writerow([a.replace("\r", " ").replace("\n", " ")])
        payload = buf.getvalue().encode("utf-8")
        b = "----BAN_PD_BOUNDARY"
        body = (("--%s\r\n" % b)
                + 'Content-Disposition: form-data; name="data"; filename="a.csv"\r\n'
                + "Content-Type: text/csv\r\n\r\n").encode() + payload \
               + ("\r\n--%s--\r\n" % b).encode()
        req = urllib.request.Request(
            BAN_CSV, data=body,
            headers={"Content-Type": "multipart/form-data; boundary=%s" % b,
                     "User-Agent": "DPE-Prospector/1.0"}, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:
            txt = r.read().decode("utf-8")
        out = []
        for row in csv.DictReader(io.StringIO(txt)):
            try:
                lon = float(row.get("longitude") or row.get("result_longitude") or 0) or None
                lat = float(row.get("latitude") or row.get("result_latitude") or 0) or None
                sc = float(row.get("result_score") or 0)
            except (ValueError, TypeError):
                lon = lat = None
                sc = 0.0
            out.append({"lon": lon, "lat": lat, "score": sc,
                        "label_ban": (row.get("result_label") or "")[:120]})
        return out

    def traiter(lot):
        for t in range(3):
            try:
                res = appel(lot)
                if len(res) != len(lot):
                    res = (res + [{"lon": None, "lat": None, "score": 0.0, "label_ban": ""}]
                           * len(lot))[:len(lot)]
                return res
            except ERRS as e:
                print("      [!] lot %d adr. tentative %d/3 : %s" % (len(lot), t + 1, type(e).__name__))
                if t < 2:
                    time.sleep(2 * (t + 1))
        if len(lot) > 50:
            m = len(lot) // 2
            print("      -> sous-decoupage %d + %d" % (m, len(lot) - m))
            return traiter(lot[:m]) + traiter(lot[m:])
        print("      [x] lot abandonne (%d adr.)" % len(lot))
        return [{"echec": True}] * len(lot)

    for d0 in range(0, len(todo), LOT):
        lot = todo[d0:d0 + LOT]
        print("      lot %d/%d (%d)" % (d0 // LOT + 1, -(-len(todo) // LOT), len(lot)))
        for a, r in zip(lot, traiter(lot)):
            if not r.get("echec"):          # les echecs restent hors cache -> rejouables
                cache[a] = r
        sauver(cache_path, cache)
        time.sleep(PAUSE_LOT)
    return cache


# ── recherche-entreprises ─────────────────────────────────────────
def enrichir(sirens, cache):
    todo = [s for s in sirens if s not in cache]
    print("   SIREN : %d total, %d en cache, %d a interroger (~%.0f min)"
          % (len(sirens), len(sirens) - len(todo), len(todo), len(todo) * (PAUSE + 0.45) / 60))
    ok = vide = ech = saut = 0
    for i, s in enumerate(todo):
        if not s or not s.isdigit() or len(s) != 9:
            cache[s] = {"siege": "", "gerants": [], "actif": True, "statut": "pseudo_siren"}
            saut += 1
            continue
        res, last = None, None
        for t in range(3):
            try:
                req = urllib.request.Request("%s?q=%s&page=1&per_page=1" % (ENT_URL, s),
                                             headers={"User-Agent": "DPE-Prospector/1.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    res = json.loads(r.read())
                break
            except Exception as e:
                last = e
                if t < 2:
                    time.sleep(2 ** t)      # backoff 1 / 2 / 4
        if res is None:
            cache[s] = {"siege": "", "gerants": [], "actif": True,
                        "statut": "api_echec", "err": type(last).__name__}
            ech += 1
        else:
            rs = res.get("results") or []
            if not rs:
                cache[s] = {"siege": "", "gerants": [], "actif": True, "statut": "introuvable"}
                vide += 1
            else:
                info = rs[0]
                g = [{"nom": ("%s %s" % (d.get("prenoms", "") or "", d.get("nom", "") or "")).strip(),
                      "qualite": d.get("qualite", "")}
                     for d in (info.get("dirigeants") or [])
                     if d.get("type_dirigeant") == "personne physique"]
                cache[s] = {"siege": (info.get("siege") or {}).get("adresse", "") or "",
                            "gerants": g,
                            "actif": info.get("etat_administratif") == "A",
                            "statut": "ok"}
                ok += 1
        time.sleep(PAUSE)
        if (i + 1) % 100 == 0:
            sauver(C_ENT, cache)
            print("      %d/%d  (ok=%d introuvable=%d echec=%d pseudo=%d)"
                  % (i + 1, len(todo), ok, vide, ech, saut))
    sauver(C_ENT, cache)
    print("      TERMINE : ok=%d introuvable=%d echec=%d pseudo-SIREN=%d" % (ok, vide, ech, saut))
    return cache


# ── CSV ───────────────────────────────────────────────────────────
def ecrire_csv(path, entetes, lignes):
    def esc(v):
        s = "" if v is None else str(v)
        return '"%s"' % s.replace('"', '""') if (CSV_SEP in s or '"' in s or "\n" in s or "\r" in s) else s
    out = [CSV_SEP.join(esc(h) for h in entetes)]
    for L in lignes:
        out.append(CSV_SEP.join(esc(x) for x in L))
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\ufeff" + "\r\n".join(out) + "\r\n")


# ── main ──────────────────────────────────────────────────────────
def main():
    print("=" * 74)
    print("  ETAPES 2-3-4 — Part-Dieu NR   (AUCUNE ecriture du JSON SCI)")
    print("=" * 74)

    PD, DL, MT, surf = charger_polygones()
    print("\n[0] Polygone Part-Dieu : %.4f km2 (data/_perimetre_part_dieu.json)" % surf)

    # ── Etape 2 ───────────────────────────────────────────────────
    print("\n[ETAPE 2] Candidats — biens dans Part-Dieu")
    import pyarrow.parquet as pq
    t = pq.read_table(MAJIC,
                      columns=["code_insee", "forme_juridique", "section", "numero_parcelle",
                               "numero_siren", "denomination", "code_droit",
                               "numero_voirie", "nature_voie", "nom_voie", "millesime"],
                      filters=[("code_insee", "=", INSEE_3E), ("forme_juridique", "=", FORME_SCI)])
    c = {k: t.column(k).to_pylist() for k in t.schema.names}
    print("   %d locaux 6540 sur le 3e" % t.num_rows)

    def pid(s, p):
        try:
            return "%s%s" % (str(s), str(int(p)).zfill(4))
        except (TypeError, ValueError):
            return "%s%s" % (str(s), str(p))

    def adr(i):
        n = str(c["numero_voirie"][i] or "").strip().lstrip("0")
        a = str(c["nature_voie"][i] or "").strip()
        v = str(c["nom_voie"][i] or "").strip()
        for bad in ("nan", "None"):
            n = "" if n == bad else n
            a = "" if a == bad else a
            v = "" if v == bad else v
        return ("%s %s %s 69003" % (n, a, v)).strip()

    couples = {}
    for i in range(t.num_rows):
        k = (pid(c["section"][i], c["numero_parcelle"][i]), str(c["numero_siren"][i]))
        couples.setdefault(k, {"adresse_bien": adr(i), "sci_nom": c["denomination"][i],
                               "code_droit": c["code_droit"][i],
                               "millesime": int(c["millesime"][i] or 2025)})
    print("   %d couples (parcelle, siren)" % len(couples))

    cb = ban_batch(sorted({v["adresse_bien"] for v in couples.values()}),
                   charger(C_BIENS), "BIENS", C_BIENS)
    sauver(C_BIENS, cb)
    cand = {}
    for k, v in couples.items():
        g = cb.get(v["adresse_bien"]) or {}
        lo, la, sc = g.get("lon"), g.get("lat"), g.get("score") or 0.0
        if lo is None or sc <= SEUIL_BIEN:
            continue
        if PD.contains(Point(lo, la)):
            v.update(bien_lon=lo, bien_lat=la, bien_score=sc)
            cand[k] = v
    print("   CANDIDATS dans Part-Dieu : %d couples / %d SIREN distincts"
          % (len(cand), len({k[1] for k in cand})))

    # ── Etape 3 ───────────────────────────────────────────────────
    print("\n[ETAPE 3] Enrichissement recherche-entreprises")
    ce = enrichir(sorted({k[1] for k in cand}), charger(C_ENT))

    # ── Etape 4 ───────────────────────────────────────────────────
    print("\n[ETAPE 4] Geocodage des sieges + arbitrage")
    for k, v in cand.items():
        e = ce.get(k[1], {})
        v["siege_social"] = e.get("siege", "") or ""
        v["gerants"] = e.get("gerants", [])
        v["sci_active"] = "oui" if e.get("actif", True) else "non"
        v["_ent_statut"] = e.get("statut", "?")

    sieges = sorted({v["siege_social"] for v in cand.values()
                     if v["siege_social"].strip()
                     and "[NON-DIFFUSIBLE]" not in v["siege_social"]})
    cs = ban_batch(sieges, charger(C_SIEGES), "SIEGES", C_SIEGES)
    sauver(C_SIEGES, cs)

    exclus, doute, retenus = [], [], []
    for k, v in sorted(cand.items()):
        sg = v["siege_social"]
        st = v["_ent_statut"]
        g = cs.get(sg) or {}
        lo, la, sc = g.get("lon"), g.get("lat"), g.get("score") or 0.0
        v.update(siege_lon=lo, siege_lat=la, siege_score=round(sc, 3),
                 siege_label_ban=g.get("label_ban", ""))
        if st == "pseudo_siren":
            v["siege_statut"] = "pseudo_siren"
        elif not sg.strip():
            v["siege_statut"] = "adresse_vide"
        elif "[NON-DIFFUSIBLE]" in sg:
            v["siege_statut"] = "non_diffusible"
        elif lo is None or sc <= 0:
            v["siege_statut"] = "geocodage_echec"
        elif sc < SEUIL_SIEGE:
            v["siege_statut"] = "score_bas"
        elif PD.contains(Point(lo, la)):
            v["siege_statut"] = "EXCLU_siege_dans_part_dieu"
        else:
            v["siege_statut"] = "verifie_hors_zone"
        v["siege_verifie"] = (v["siege_statut"] == "verifie_hors_zone")
        if v["siege_statut"].startswith("EXCLU"):
            exclus.append((k, v))
        elif not v["siege_verifie"]:
            doute.append((k, v))
        else:
            retenus.append((k, v))

    # zone du siege, pour information dans le CSV des exclus
    def zone_siege(v):
        if v["siege_lon"] is None:
            return ""
        p = Point(v["siege_lon"], v["siege_lat"])
        for n, poly in (("Part-Dieu NR", PD), ("Dauphiné-Lacassagne", DL), ("Montchat", MT)):
            if poly.contains(p):
                return n
        return "hors 3e / ailleurs"

    ecrire_csv(OUT_EXCLUS,
               ["parcelle", "sci_nom", "sci_siren", "adresse_bien", "siege_social_brut",
                "siege_score", "siege_lon", "siege_lat", "siege_zone", "siege_label_ban",
                "sci_active", "code_droit"],
               [[k[0], v["sci_nom"], k[1], v["adresse_bien"], v["siege_social"],
                 v["siege_score"], v["siege_lon"], v["siege_lat"], zone_siege(v),
                 v["siege_label_ban"], v["sci_active"], v["code_droit"]]
                for k, v in exclus])

    ecrire_csv(OUT_DOUTE,
               ["parcelle", "sci_nom", "sci_siren", "adresse_bien", "siege_social_brut",
                "motif", "siege_score", "siege_lon", "siege_lat", "siege_label_ban",
                "sci_active", "code_droit"],
               [[k[0], v["sci_nom"], k[1], v["adresse_bien"], v["siege_social"],
                 v["siege_statut"], v["siege_score"], v["siege_lon"], v["siege_lat"],
                 v["siege_label_ban"], v["sci_active"], v["code_droit"]]
                for k, v in doute])

    with io.open(OUT_ETAT, "w", encoding="utf-8") as f:
        json.dump({"genere_le": datetime.now().isoformat(timespec="seconds"),
                   "seuil_bien": SEUIL_BIEN, "seuil_siege": SEUIL_SIEGE,
                   "candidats": [{"parcelle": k[0], "sci_siren": k[1], **v}
                                 for k, v in sorted(cand.items())]},
                  f, ensure_ascii=False, indent=1)

    print("\n" + "=" * 74)
    print("  RESULTAT")
    print("=" * 74)
    tot = len(cand)
    print("  candidats (bien dans Part-Dieu)      : %4d couples / %d SIREN"
          % (tot, len({k[1] for k in cand})))
    print("  EXCLUS (siege dans Part-Dieu, >=%.2f) : %4d  (%.1f %%)"
          % (SEUIL_SIEGE, len(exclus), 100.0 * len(exclus) / tot))
    print("  retenus siege VERIFIE hors zone      : %4d  (%.1f %%)"
          % (len(retenus), 100.0 * len(retenus) / tot))
    print("  retenus AU DOUTE (non verifie)       : %4d  (%.1f %%)"
          % (len(doute), 100.0 * len(doute) / tot))
    import collections
    print("     motifs :", dict(collections.Counter(v["siege_statut"] for _, v in doute)))
    print("  -> fiches a creer a l'etape 5        : %4d" % (len(retenus) + len(doute)))
    print()
    print("  CSV : %s" % OUT_EXCLUS)
    print("        %s" % OUT_DOUTE)
    print("  etat: %s" % OUT_ETAT)
    print("\n  AUCUNE ecriture de data/dauphine-lacassagne-sci.json (etape 5).")


if __name__ == "__main__":
    main()
