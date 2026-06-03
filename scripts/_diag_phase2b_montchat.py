#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diag read-only Phase 2b Montchat : orphelins restants + ilots vides.

Reproduit la passe d'ilotage (PIP -> snap 15 -> arbitrage bgid) du light
courant, puis :
  - liste les orphelins X/null RESTANTS (cle + bgid + raison)
  - pour chaque ilot VIDE : croise copros RNC + adresses light dont les coords
    tombent DANS le polygone mais ne sont pas affectees a cet ilot (= trou),
    vs aucune donnee (= probablement non-residentiel / equipement).

AUCUNE ecriture. Prints ASCII-safe.
"""
import sys, json, math, re
from pathlib import Path
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from shapely.ops import nearest_points, unary_union

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_montchat_light.json"
FULL = ROOT / "data" / "secteur_montchat.json"
KML = ROOT / "data" / "kml" / "Ilotage_Montchat.kml"
NS = {"kml": "http://www.opengis.net/kml/2.2"}
SNAP = 15.0


def hav(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))


def parse_kml(p):
    root = ET.fromstring(p.read_text(encoding="utf-8"))
    raw = []
    for pm in root.findall(".//kml:Placemark", NS):
        n = pm.find("kml:name", NS)
        name = (n.text if n is not None else "").strip()
        rings = []
        for poly_el in pm.findall(".//kml:Polygon", NS):
            c = poly_el.find(".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
            if c is None or not c.text:
                continue
            pts = []
            for tok in c.text.strip().split():
                pa = tok.split(",")
                if len(pa) >= 2:
                    pts.append((float(pa[0]), float(pa[1])))
            if len(pts) >= 3 and pts[0] != pts[-1]:
                pts.append(pts[0])
            if len(pts) >= 4:
                rings.append(Polygon(pts).buffer(0))
        if name and rings:
            raw.append((name, rings))
    merged = []
    for name, rings in raw:
        g = unary_union(rings) if len(rings) > 1 else rings[0]
        merged.append((name, g.buffer(0)))
    idx118 = [i for i, (nm, _) in enumerate(merged) if nm == "118"]
    if len(idx118) >= 2:
        smallest = min(idx118, key=lambda i: merged[i][1].area)
        merged[smallest] = ("195", merged[smallest][1])
    return merged


ents = parse_kml(KML)
geoms = [g for _, g in ents]
names = [n for n, _ in ents]
tree = STRtree(geoms)
poly_by_name = {n: g for n, g in ents}


def ilot_pip(lon, lat):
    pt = Point(lon, lat)
    for idx in tree.query(pt):
        if geoms[idx].covers(pt):
            return names[idx]
    return None


def ilot_snap(lon, lat, max_m):
    pt = Point(lon, lat)
    best_idx, best_d = None, float("inf")
    deg_pad = max_m / 100000.0
    for idx in tree.query(Point(lon, lat).buffer(deg_pad)):
        np_geom, _ = nearest_points(geoms[idx], pt)
        d = hav(lat, lon, np_geom.y, np_geom.x)
        if d < best_d:
            best_d, best_idx = d, idx
    if best_idx is not None and best_d <= max_m:
        return names[best_idx], best_d
    return None, (best_d if best_idx is not None else None)


doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]

# PASS 1
res = {}
for a in ad:
    cle = a.get("cle") or ""
    bg = a.get("batiment_groupe_id") or None
    lat = a.get("latitude"); lon = a.get("longitude")
    if lat is None or lon is None:
        res[cle] = {"ilot": None, "method": "null", "lat": lat, "lon": lon, "bg": bg, "snap_d": None}
        continue
    il = ilot_pip(lon, lat)
    if il is not None:
        res[cle] = {"ilot": il, "method": "pip", "lat": lat, "lon": lon, "bg": bg, "snap_d": 0.0}
        continue
    sil, dist = ilot_snap(lon, lat, SNAP)
    if sil is not None:
        res[cle] = {"ilot": sil, "method": "snap", "lat": lat, "lon": lon, "bg": bg, "snap_d": dist}
        continue
    res[cle] = {"ilot": "X", "method": "x", "lat": lat, "lon": lon, "bg": bg, "snap_d": dist}

pass1_x = sum(1 for v in res.values() if v["ilot"] == "X")
pass1_null = sum(1 for v in res.values() if v["ilot"] is None)
print(f"[PASS1] X={pass1_x} null={pass1_null} (orphelins avant arbitrage={pass1_x+pass1_null})")

# PASS 2 arbitrage bgid
by_bgid = defaultdict(list)
for cle, info in res.items():
    if info["bg"]:
        by_bgid[info["bg"]].append(cle)
final = {cle: info["ilot"] for cle, info in res.items()}
lifted = []
for bg, cles in by_bgid.items():
    votes = Counter()
    coords = []
    for cle in cles:
        info = res[cle]
        if info["ilot"] is not None and info["ilot"] != "X":
            votes[info["ilot"]] += 1
        if info["lat"] is not None and info["lon"] is not None:
            coords.append((info["lon"], info["lat"]))
    if not votes:
        continue
    top = votes.most_common()
    if len(top) == 1 or top[0][1] > top[1][1]:
        chosen = top[0][0]
    else:
        if coords:
            clon = sum(p[0] for p in coords) / len(coords)
            clat = sum(p[1] for p in coords) / len(coords)
            ic = ilot_pip(clon, clat)
            tied = {nm for nm, c in top if c == top[0][1]}
            chosen = ic if ic in tied else sorted(tied, key=lambda s: (len(s), s))[0]
        else:
            chosen = sorted({nm for nm, c in top if c == top[0][1]}, key=lambda s: (len(s), s))[0]
    for cle in cles:
        if final[cle] != chosen:
            old = final[cle]
            final[cle] = chosen
            if old in (None, "X"):
                lifted.append((cle, bg, old, chosen))

post_x = sum(1 for v in final.values() if v == "X")
post_null = sum(1 for v in final.values() if v is None)
print(f"[PASS2] orphelins resolus par arbitrage bgid = {len(lifted)}")
print(f"[POST ] X={post_x} null={post_null} (orphelins restants={post_x+post_null})")

# Orphelins RESTANTS avec raison
print()
print("=== ORPHELINS RESTANTS (cle | bgid | raison) ===")
# bgids ayant au moins un vote (ilot reel)
bgid_has_vote = set()
for bg, cles in by_bgid.items():
    if any(res[c]["ilot"] not in (None, "X") for c in cles):
        bgid_has_vote.add(bg)
restants = [(cle, final[cle]) for cle in final if final[cle] in (None, "X")]
def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s) or "")]
for cle, il in sorted(restants, key=lambda x: natkey(x[0])):
    info = res[cle]
    bg = info["bg"]
    if il is None:
        reason = "pas de coords (null)"
    elif not bg:
        reason = "pas de bgid (orphelin isole)"
    elif bg not in by_bgid or all(res[c]["ilot"] in (None, "X") for c in by_bgid[bg]):
        n_same = len(by_bgid.get(bg, []))
        reason = f"bgid entierement orphelin ({n_same} adr du bgid, 0 votee)"
    else:
        reason = "anomalie (bgid a des votes mais non applique)"
    sd = info.get("snap_d")
    sds = f" snap_nearest={sd:.1f}m" if isinstance(sd, (int, float)) else ""
    bgs = bg[-12:] if bg else "-"
    print(f"  {cle:42s} | {bgs:12s} | ilot={str(il):4s} | {reason}{sds}")

# === ILOTS VIDES ===
dist_final = Counter()
for il in final.values():
    if il not in (None, "X"):
        dist_final[il] += 1
vides = sorted(set(names) - set(dist_final.keys()), key=natkey)
print()
print(f"=== ILOTS VIDES : {len(vides)} -> {vides} ===")

# charge copros + adresses FULL pour croiser
full = json.loads(FULL.read_text(encoding="utf-8"))
copros = full.get("coproprietes", [])
full_ad = full.get("adresses", [])


def get_ll(o):
    lon = o.get("_longitude") or o.get("long") or o.get("longitude")
    lat = o.get("_latitude") or o.get("lat") or o.get("latitude")
    try:
        return float(lon), float(lat)
    except (TypeError, ValueError):
        return None, None


for v in vides:
    g = poly_by_name[v]
    ct = g.centroid
    # span en m
    minx, miny, maxx, maxy = g.bounds
    R = 6371000.0
    w = math.radians(maxx-minx)*R*math.cos(math.radians((miny+maxy)/2))
    h = math.radians(maxy-miny)*R
    # copros RNC dans le polygone
    cin = []
    for c in copros:
        lon, lat = get_ll(c)
        if lon is None:
            continue
        if g.covers(Point(lon, lat)):
            cin.append(c.get("_numero_immatriculation") or c.get("numero_d_immatriculation"))
    # adresses FULL dans le polygone
    ain = []
    for a in full_ad:
        lon, lat = get_ll(a)
        if lon is None:
            continue
        if g.covers(Point(lon, lat)):
            ain.append(a.get("cle"))
    # adresses LIGHT (toutes, peu importe leur _ilot) dont les coords tombent dedans
    lin = []
    for a in ad:
        lat = a.get("latitude"); lon = a.get("longitude")
        if lat is None or lon is None:
            continue
        if g.covers(Point(lon, lat)):
            lin.append((a.get("cle"), final.get(a.get("cle") or "")))
    status = "VIDE LEGITIME (probablement equipement/non-residentiel)" if not (cin or ain or lin) \
        else f"TROU A INVESTIGUER ({len(cin)} copros RNC + {len(ain)} adr FULL + {len(lin)} adr LIGHT dans le polygone)"
    print(f"  ilot {v}: centroid=({ct.x:.6f},{ct.y:.6f}) span~{w:.0f}m x {h:.0f}m area={g.area:.3e}")
    print(f"    copros_RNC_in={len(cin)} adr_FULL_in={len(ain)} adr_LIGHT_in={len(lin)} -> {status}")
    if cin[:5]:
        print(f"    copros: {cin[:5]}")
    if ain[:5]:
        print(f"    adr_FULL: {ain[:5]}")
    if lin[:5]:
        print(f"    adr_LIGHT(cle,_ilot): {lin[:5]}")

print()
print(f"[FINAL] ilots peuples={len(dist_final)}/{len(set(names))} vides={len(vides)}")
print(f"[FINAL] 195 peuple={dist_final.get('195',0)} | 162 peuple={dist_final.get('162',0)}")
