"""
_build_perimetre_part_dieu.py
─────────────────────────────────────────────────────────────────
ETAPE 1 du chantier "Part-Dieu NR" : derive le polygone de la zone
Part-Dieu PAR SOUSTRACTION et valide le resultat.

    PART_DIEU = contour(Lyon 3e) - Dauphine-Lacassagne - Montchat

Les deux polygones soustraits sont lus DANS scripts/majic_sci_2025.py
(ZONES) : c'est la seule geometrie qui fait foi pour le pipeline SCI.
Ne JAMAIS utiliser perimetre_montchat.json (derive du KML, buffer 40 m,
ecart de -0.4 % et non inclusif) sous peine de trous/recouvrements.

Sortie : data/_perimetre_part_dieu.json  (ecrite seulement avec --write)

Deviation de pattern assumee (decision Yann, cf. CLAUDE.md) : le polygone
vit dans un fichier externe, pas en dur dans le script, parce qu'il est
DERIVE (centaines de sommets) et non dessine a la main.

Divergence assumee : data/secteurs.json n'est PAS mis a jour. Il contient
deja les 2 autres zones en [lat, lon] inverse ; Part-Dieu n'a ni light,
ni KML d'ilotage, ni RNC/BDNB/DVF. A traiter separement si Secteur est
un jour etendu a ce quartier.

Usage :
  python scripts/_build_perimetre_part_dieu.py            # dry-run
  python scripts/_build_perimetre_part_dieu.py --write    # ecrit le JSON
  python scripts/_build_perimetre_part_dieu.py --no-geo   # saute le geocodage
"""

import argparse
import collections
import io
import json
import math
import os
import re
import sys
import urllib.request
from datetime import datetime

from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

# Console Windows en cp1252 : on force UTF-8 pour les noms de rue accentues.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ── Chemins ───────────────────────────────────────────────────────
ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SCRIPT_SCI = os.path.join(ICI, "majic_sci_2025.py")
OUT_JSON   = os.path.join(RACINE, "data", "_perimetre_part_dieu.json")
MAJIC      = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

# ── Source du contour : WFS IGN, meme service que make_light.py:128 ──
WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
       "&TYPENAMES=STATISTICALUNITS.IRIS:contours_iris"
       "&CQL_FILTER=code_insee=%2769383%27"
       "&OUTPUTFORMAT=application/json")

INSEE_3E   = "69383"
FORME_SCI  = "6540"
SEUIL_ELAG = 5000.0    # m2 : composantes plus petites = liseres parasites
TOL_CHEVAU = 100.0     # m2 : chevauchement tolere avant alerte


# ── Projection locale (pyproj absent) ─────────────────────────────
def projecteur(lat0):
    """Equirectangulaire centree : degres -> metres. Erreur < 0.3 % a cette latitude."""
    my = 111132.95 - 559.85 * math.cos(2 * math.radians(lat0)) \
         + 1.175 * math.cos(4 * math.radians(lat0))
    mx = 111412.84 * math.cos(math.radians(lat0)) \
         - 93.5 * math.cos(3 * math.radians(lat0))
    return mx, my


def aire_m2(geom, lat0):
    mx, my = projecteur(lat0)
    from shapely.affinity import scale
    return abs(scale(geom, xfact=mx, yfact=my, origin=(0, 0, 0)).area)


def km2(geom, lat0):
    return aire_m2(geom, lat0) / 1e6


# ── Lecture des 2 polygones de reference ──────────────────────────
def charger_zones_script():
    """Extrait ZONES de majic_sci_2025.py sans l'importer (evite pandas/pyarrow)."""
    src = io.open(SCRIPT_SCI, encoding="utf-8").read()
    bloc = src[src.index("ZONES = {"):src.index("BAN_URL")]
    out = {}
    for nom in ("Dauphiné-Lacassagne", "Montchat"):
        i = bloc.index('"%s"' % nom)
        j = bloc.index("Polygon([", i)
        k = bloc.index("])", j)
        pts = re.findall(r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]", bloc[j:k])
        out[nom] = Polygon([(float(a), float(b)) for a, b in pts])   # [lon, lat]
    return out


def charger_contour_3e():
    req = urllib.request.Request(WFS, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        fc = json.loads(r.read())
    iris = []
    for f in fc.get("features", []):
        g = shape(f["geometry"]).buffer(0)
        iris.append((f["properties"].get("code_iris"),
                     f["properties"].get("nom_iris"), g))
    return iris, unary_union([g for _, _, g in iris]).buffer(0)


# ── Parquet : couples (parcelle, siren) 6540 du 3e ────────────────
def charger_couples():
    import pyarrow.parquet as pq
    t = pq.read_table(MAJIC,
                      columns=["code_insee", "forme_juridique", "section",
                               "numero_parcelle", "numero_siren", "denomination",
                               "numero_voirie", "nature_voie", "nom_voie"],
                      filters=[("code_insee", "=", INSEE_3E),
                               ("forme_juridique", "=", FORME_SCI)])
    cols = {c: t.column(c).to_pylist() for c in t.schema.names}

    def pid(s, p):
        try:
            return "%s%s" % (str(s), str(int(p)).zfill(4))
        except (TypeError, ValueError):
            return "%s%s" % (str(s), str(p))

    def adr(i):
        num = str(cols["numero_voirie"][i] or "").strip().lstrip("0")
        nat = str(cols["nature_voie"][i] or "").strip()
        voie = str(cols["nom_voie"][i] or "").strip()
        for bad in ("nan", "None"):
            num = "" if num == bad else num
            nat = "" if nat == bad else nat
            voie = "" if voie == bad else voie
        return ("%s %s %s 69003" % (num, nat, voie)).strip()

    couples = {}
    for i in range(t.num_rows):
        cle = (pid(cols["section"][i], cols["numero_parcelle"][i]),
               str(cols["numero_siren"][i]))
        couples.setdefault(cle, {
            "adresse": adr(i),
            "voie": ("%s %s" % (cols["nature_voie"][i] or "",
                                cols["nom_voie"][i] or "")).strip(),
            "nom": cols["denomination"][i],
        })
    return couples


# ── Geocodage BAN : on reutilise la fonction eprouvee du pipeline ──
def geocoder(adresses):
    sys.path.insert(0, ICI)
    import majic_sci_2025 as M
    lons, lats, _ = M.geocoder_ban_batch(adresses)   # zones ignorees (2 zones only)
    return lons, lats


# ── Rapport lisible ───────────────────────────────────────────────
def zone_du_point(lon, lat, zones):
    """Retourne la LISTE des zones contenant le point (pour detecter 2+)."""
    if lon is None or lat is None:
        return []
    pt = Point(lon, lat)
    return [n for n, p in zones.items() if p.contains(pt)]


def main(write, faire_geo):
    lat0 = 45.755
    print("=" * 72)
    print("  ETAPE 1 — DERIVATION DU POLYGONE PART-DIEU (par soustraction)")
    print("=" * 72)

    print("\n[1/5] Polygones de reference (scripts/majic_sci_2025.py)")
    Z = charger_zones_script()
    DL, MT = Z["Dauphiné-Lacassagne"], Z["Montchat"]
    for n, p in Z.items():
        print("   %-22s sommets=%2d valide=%s  %.3f km2"
              % (n, len(p.exterior.coords) - 1, p.is_valid, km2(p, lat0)))
    chev_exist = DL.intersection(MT)
    print("   DL n Montchat (preexistant) : %.0f m2" % aire_m2(chev_exist, lat0))

    print("\n[2/5] Contour du 3e — WFS IGN contours_iris (code_insee=69383)")
    iris, TROIS = charger_contour_3e()
    print("   %d IRIS -> contour %s, %.3f km2" % (len(iris), TROIS.geom_type, km2(TROIS, lat0)))

    print("\n[3/5] Soustraction")
    brut = TROIS.difference(DL).difference(MT).buffer(0)
    parts = list(brut.geoms) if brut.geom_type == "MultiPolygon" else [brut]
    parts.sort(key=lambda g: -aire_m2(g, lat0))
    gardes, elagues = [], []
    for g in parts:
        (gardes if aire_m2(g, lat0) >= SEUIL_ELAG else elagues).append(g)
    PD = unary_union(gardes).buffer(0)
    print("   composantes brutes : %d" % len(parts))
    print("   gardees (>= %.0f m2) : %d" % (SEUIL_ELAG, len(gardes)))
    for g in gardes:
        print("      + %.4f km2" % km2(g, lat0))
    print("   elaguees (liseres) : %d  (total %.0f m2)"
          % (len(elagues), sum(aire_m2(g, lat0) for g in elagues)))
    for g in elagues[:12]:
        c = g.centroid
        print("      - %7.0f m2  centroide %.5f, %.5f" % (aire_m2(g, lat0), c.x, c.y))
    if len(elagues) > 12:
        print("      - ... +%d autres" % (len(elagues) - 12))
    print("   PART-DIEU : %s, %d sommets, %.3f km2"
          % (PD.geom_type,
             sum(len(g.exterior.coords) - 1 for g in (PD.geoms if PD.geom_type == "MultiPolygon" else [PD])),
             km2(PD, lat0)))

    ZONES3 = {"Dauphiné-Lacassagne": DL, "Montchat": MT, "Part-Dieu NR": PD}

    print("\n[4/5] CONTROLES")
    a3, adl, amt, apd = km2(TROIS, lat0), km2(DL, lat0), km2(MT, lat0), km2(PD, lat0)
    somme = adl + amt + apd - km2(chev_exist, lat0)
    ecart = 100.0 * (somme - a3) / a3
    print("   C1 surface : DL %.3f + MTC %.3f + PD %.3f - liser %.4f = %.3f vs 3e %.3f"
          % (adl, amt, apd, km2(chev_exist, lat0), somme, a3))
    print("      ecart %.2f %%  -> %s" % (ecart, "OK" if abs(ecart) < 1.0 else "ALERTE"))
    print("      PD dans la fourchette 1.7-2.1 km2 : %s" % ("OK" if 1.7 <= apd <= 2.1 else "ALERTE"))

    trou = TROIS.difference(unary_union([DL, MT, PD])).buffer(0)
    at = aire_m2(trou, lat0)
    print("   C2 trous   : %.0f m2 (%.3f %% du 3e)  -> %s"
          % (at, 100.0 * at / aire_m2(TROIS, lat0), "OK" if at < 0.01 * aire_m2(TROIS, lat0) else "ALERTE"))
    tp = list(trou.geoms) if trou.geom_type == "MultiPolygon" else ([trou] if not trou.is_empty else [])
    for g in sorted(tp, key=lambda x: -aire_m2(x, lat0))[:8]:
        if aire_m2(g, lat0) >= SEUIL_ELAG:
            c = g.centroid
            print("      trou residuel %.0f m2 centroide %.5f, %.5f" % (aire_m2(g, lat0), c.x, c.y))

    for n, p in (("DL", DL), ("Montchat", MT)):
        a = aire_m2(PD.intersection(p), lat0)
        print("   C3 PD n %-9s : %.1f m2  -> %s" % (n, a, "OK" if a < TOL_CHEVAU else "ALERTE"))

    if not faire_geo:
        print("   C4 : saute (--no-geo)")
        couples = {}
    else:
        print("   C4 couverture parcellaire (geocodage BAN des biens)")
        couples = charger_couples()
        print("      %d couples (parcelle, siren) 6540 sur le 3e" % len(couples))
        uniq = sorted({v["adresse"] for v in couples.values()})
        print("      %d adresses distinctes a geocoder" % len(uniq))
        lons, lats = geocoder(uniq)
        geo = {a: (lo, la) for a, lo, la in zip(uniq, lons, lats)}
        cpt = collections.Counter()
        for cle, v in couples.items():
            lo, la = geo.get(v["adresse"], (None, None))
            zs = zone_du_point(lo, la, ZONES3)
            v["zones"] = zs
            v["lon"], v["lat"] = lo, la
            cpt["echec_geo" if lo is None else ("%d_zone" % len(zs))] += 1
        print("      1 zone      : %d" % cpt["1_zone"])
        print("      0 zone      : %d  (hors des 3 polygones)" % cpt["0_zone"])
        print("      2+ zones    : %d  -> %s"
              % (cpt["2_zone"] + cpt["3_zone"], "OK" if (cpt["2_zone"] + cpt["3_zone"]) == 0 else "ALERTE"))
        print("      echec geoc. : %d  (BAN score <= 0.4 ou lot abandonne)" % cpt["echec_geo"])
        rep = collections.Counter(v["zones"][0] for v in couples.values() if v.get("zones"))
        print("      repartition : %s" % dict(rep))

    print("\n[5/5] VALIDATION LISIBLE — sections cadastrales et voies")
    if couples:
        parsec = collections.defaultdict(collections.Counter)
        voies  = collections.defaultdict(collections.Counter)
        for cle, v in couples.items():
            sec = cle[0][:2]
            z = v["zones"][0] if v.get("zones") else ("(hors zone)" if v["lon"] else "(geoc. echoue)")
            parsec[sec][z] += 1
            if z == "Part-Dieu NR" and v["voie"]:
                voies[sec][v["voie"]] += 1

        pures, cheval = [], []
        for sec, c in parsec.items():
            zs = {k for k in c if k.startswith(("Dauphiné", "Montchat", "Part-Dieu"))}
            if zs == {"Part-Dieu NR"}:
                pures.append(sec)
            elif "Part-Dieu NR" in zs and len(zs) > 1:
                cheval.append(sec)

        print("\n   ── SECTIONS 100 %% PART-DIEU (%d) ──" % len(pures))
        for sec in sorted(pures):
            top = ", ".join(v for v, _ in voies[sec].most_common(3))
            print("      %-4s %4d SCI  %s" % (sec, parsec[sec]["Part-Dieu NR"], top[:74]))

        print("\n   ── SECTIONS A CHEVAL ENTRE DEUX ZONES (%d) ──" % len(cheval))
        for sec in sorted(cheval):
            det = "  ".join("%s=%d" % (("PD" if k.startswith("Part") else
                                        "DL" if k.startswith("Dau") else
                                        "MTC" if k.startswith("Mont") else k), n)
                            for k, n in parsec[sec].most_common())
            top = ", ".join(v for v, _ in voies[sec].most_common(2))
            print("      %-4s %-34s %s" % (sec, det, top[:50]))

        hors = [c for c, v in couples.items() if v.get("lon") and not v.get("zones")]
        if hors:
            print("\n   ── COUPLES HORS DES 3 ZONES (%d) ──" % len(hors))
            for cle in hors[:10]:
                print("      %s %s  %s" % (cle[0], cle[1], couples[cle]["adresse"][:46]))
            if len(hors) > 10:
                print("      ... +%d autres" % (len(hors) - 10))

    print("\n   ── IRIS DU 3e ET ZONE DOMINANTE ──")
    for code, nom, g in sorted(iris, key=lambda t: t[0]):
        best, ba = "(aucune)", 0.0
        for n, p in ZONES3.items():
            a = aire_m2(g.intersection(p), lat0)
            if a > ba:
                best, ba = n, a
        tot = aire_m2(g, lat0)
        print("      %-10s %-30s %-22s %5.1f %%"
              % (code, (nom or "")[:30], best, 100.0 * ba / tot if tot else 0))

    payload = {
        "nom": "Part-Dieu NR",
        "_source": "derive : contour IRIS WFS IGN (code_insee=69383) moins "
                   "Dauphine-Lacassagne moins Montchat (polygones de scripts/majic_sci_2025.py)",
        "_script": "scripts/_build_perimetre_part_dieu.py",
        "_format": "[lon, lat] WGS84 — MEME convention que majic_sci_2025.py, "
                   "PAS celle de data/secteurs.json qui est en [lat, lon]",
        "_genere_le": datetime.now().isoformat(timespec="seconds"),
        "_surface_km2": round(apd, 4),
        "_seuil_elagage_m2": SEUIL_ELAG,
        "_composantes": len(gardes),
        "polygones": [[[round(x, 9), round(y, 9)] for x, y in g.exterior.coords]
                      for g in (PD.geoms if PD.geom_type == "MultiPolygon" else [PD])],
    }
    print("\n" + "=" * 72)
    if write:
        with io.open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("  ECRIT : %s" % OUT_JSON)
    else:
        print("  DRY-RUN — rien ecrit. Relancer avec --write pour produire :")
        print("           %s" % OUT_JSON)
    print("=" * 72)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="ecrit data/_perimetre_part_dieu.json")
    ap.add_argument("--no-geo", action="store_true", help="saute le geocodage BAN (controle C4)")
    a = ap.parse_args()
    main(a.write, not a.no_geo)
