#!/usr/bin/env python3
"""Jointure spatiale KML -> _ilot dans secteur_dauphine_lacassagne_light.json.

POLITIQUE :
  (1) Point-in-polygon direct -> _ilot = nom apres rename
  (2) Hors polygone <= 5 m -> snap au plus proche
  (3) Hors polygone > 5 m -> _ilot = 'X'
  (4) Bgids split (>=2 ilots distincts) -> arbitrage MAJORITE,
      tie-breaker = polygone contenant le CENTROIDE du bati (lat/lon moyens
      des adresses du bgid avec coords valides hors malformees)
  (5) Adresses null/X au sein d'un bgid avec votes -> ilot majoritaire
  (6) Cle malformee '20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE' :
      _ilot = null, exclue des votes de son bgid (NHQQ-8MZ7-KS1W)

Renames KML : 3A->3, 3B->13, X->11 (avant la valeur 'X' fallback ci-dessus).

Dry-run par defaut. '--apply' ecrit le light + backup .preilot.bak.
"""
import argparse, re, sys, json, math, shutil, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from shapely.ops import nearest_points

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".preilot.bak")
KML_NR = Path(r"C:/Users/Station 5/Downloads/Secteur DL - non rayé.kml")
KML_R  = Path(r"C:/Users/Station 5/Downloads/Secteur DL - rayé.kml")

RENAME = {"3A": "3", "3B": "13", "X": "11"}
NS = {"kml": "http://www.opengis.net/kml/2.2"}
SNAP_MAX_M = 5.0
MALFORMED_CLE = "20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE"


def parse_kml(p):
    root = ET.fromstring(p.read_text(encoding="utf-8"))
    out = []
    for pm in root.findall(".//kml:Placemark", NS):
        n = pm.find("kml:name", NS)
        raw = (n.text if n is not None else "").strip()
        name = RENAME.get(raw, raw)
        for poly_el in pm.findall(".//kml:Polygon", NS):
            c = poly_el.find(".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
            if c is None or not c.text: continue
            pts = []
            for tok in c.text.strip().split():
                parts = tok.split(",")
                if len(parts) < 2: continue
                pts.append((float(parts[0]), float(parts[1])))
            if len(pts) >= 3:
                out.append((name, Polygon(pts)))
    return out


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))


def degree_to_meters_approx(lon1, lat1, lon2, lat2):
    """Distance approx en m (utilise haversine sur lon,lat)."""
    return haversine_m(lat1, lon1, lat2, lon2)


# --- 1. Parse KML ---
ents = parse_kml(KML_NR) + parse_kml(KML_R)
geoms = [g for _, g in ents]
names = [n for n, _ in ents]
tree = STRtree(geoms)
print(f"[KML] polygones parses : {len(ents)}  (attendu 81)")

def ilot_pip(lon, lat):
    """Point-in-polygon strict. Retourne nom ou None."""
    pt = Point(lon, lat)
    for idx in tree.query(pt):
        if geoms[idx].covers(pt):
            return names[idx]
    return None


def ilot_snap(lon, lat, max_m=SNAP_MAX_M):
    """Cherche le polygone le plus proche dans max_m (mesures via centroide arc)."""
    pt = Point(lon, lat)
    best_idx, best_d = None, float("inf")
    # On scanne large : tous les polygones dont la bbox est a portee
    # approx (max_m / 111000 deg ~ 4.5e-5 deg pour 5m)
    deg_pad = max_m / 100000.0  # marge large 100km/deg, conservative
    bbox = (lon - deg_pad, lat - deg_pad, lon + deg_pad, lat + deg_pad)
    for idx in tree.query(Point(lon, lat).buffer(deg_pad)):
        g = geoms[idx]
        # nearest point en deg, puis distance haversine reelle
        np_geom, _ = nearest_points(g, pt)
        d = haversine_m(lat, lon, np_geom.y, np_geom.x)
        if d < best_d:
            best_d, best_idx = d, idx
    if best_idx is not None and best_d <= max_m:
        return names[best_idx], best_d
    return None, best_d if best_idx is not None else None


# --- 2. Apply policy ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
print(f"[light] adresses chargees : {len(ad)}")

# Pass 1 : direct PIP + snap5m + 'X' fallback + skip malformee
PASS1_IL_PIP = "pip"
PASS1_IL_SNAP = "snap"
PASS1_IL_X = "x"
PASS1_IL_NULL = "null"
PASS1_IL_MALFORMED = "malformed"

result_pass1 = {}    # cle -> {ilot, method, snap_d, lat, lon, bg}
n_pip = n_snap = n_x = n_null = n_mal = 0
snap_list = []  # liste pour log : (cle, ilot, dist)

for a in ad:
    cle = a.get("cle") or ""
    bg = a.get("batiment_groupe_id") or None
    lat = a.get("latitude"); lon = a.get("longitude")
    if cle == MALFORMED_CLE:
        result_pass1[cle] = {"ilot": None, "method": PASS1_IL_MALFORMED,
                              "snap_d": None, "lat": lat, "lon": lon, "bg": bg}
        n_mal += 1
        continue
    if lat is None or lon is None:
        result_pass1[cle] = {"ilot": None, "method": PASS1_IL_NULL,
                              "snap_d": None, "lat": lat, "lon": lon, "bg": bg}
        n_null += 1
        continue
    # PIP
    ilot = ilot_pip(lon, lat)
    if ilot is not None:
        result_pass1[cle] = {"ilot": ilot, "method": PASS1_IL_PIP,
                              "snap_d": 0.0, "lat": lat, "lon": lon, "bg": bg}
        n_pip += 1
        continue
    # Snap
    snap_ilot, dist = ilot_snap(lon, lat)
    if snap_ilot is not None:
        result_pass1[cle] = {"ilot": snap_ilot, "method": PASS1_IL_SNAP,
                              "snap_d": dist, "lat": lat, "lon": lon, "bg": bg}
        n_snap += 1
        snap_list.append((cle, snap_ilot, dist))
        continue
    # X
    result_pass1[cle] = {"ilot": "X", "method": PASS1_IL_X,
                          "snap_d": dist if dist is not None else None,
                          "lat": lat, "lon": lon, "bg": bg}
    n_x += 1

print()
print(f"[PASS 1] direct PIP    : {n_pip:>4} ({100*n_pip/len(ad):.1f}%)")
print(f"[PASS 1] snap <=5m     : {n_snap:>4} ({100*n_snap/len(ad):.1f}%)")
print(f"[PASS 1] X (>5m)       : {n_x:>4} ({100*n_x/len(ad):.1f}%)")
print(f"[PASS 1] null (sans coords): {n_null:>4} ({100*n_null/len(ad):.1f}%)")
print(f"[PASS 1] malformee skip: {n_mal:>4}")
if snap_list:
    print(f"  Sample snap (max 8) :")
    for cle, il, d in sorted(snap_list, key=lambda x: -x[2])[:8]:
        print(f"    {cle:38s} -> ilot {il:>3} (snap={d:.2f}m)")

# Pass 2 : per-bgid arbitration
print()
print("[PASS 2] arbitrage per-bgid (majorite + centroide tie-break)")

# Grouper par bgid
by_bgid = defaultdict(list)
for cle, info in result_pass1.items():
    if info["bg"]:
        by_bgid[info["bg"]].append(cle)

n_bgid_total = len(by_bgid)
n_bgid_split = 0
n_bgid_resolved = 0
n_addr_changed = 0
n_addr_null_lifted = 0  # null/X promu via bgid

final_ilot = {cle: info["ilot"] for cle, info in result_pass1.items()}
arbitration_log = []

for bg, cles in by_bgid.items():
    # Votes = ilots reels (str numerique 1..81), exclut 'X', None, malformee
    votes = Counter()
    coords_pour_centroide = []
    for cle in cles:
        info = result_pass1[cle]
        if info["method"] == PASS1_IL_MALFORMED:
            continue  # exclus des votes
        if info["ilot"] is not None and info["ilot"] != "X":
            votes[info["ilot"]] += 1
        if info["lat"] is not None and info["lon"] is not None:
            coords_pour_centroide.append((info["lon"], info["lat"]))

    distinct_real = set(votes.keys())
    is_split = len(distinct_real) >= 2

    # Determinant : si 0 votes -> rien a faire (toutes X/null)
    if not votes:
        continue
    # Une seule valeur dominante ?
    top = votes.most_common()
    if len(top) == 1 or top[0][1] > top[1][1]:
        chosen = top[0][0]
        tie = False
    else:
        # Tie : centroide du bati
        tie = True
        if coords_pour_centroide:
            clon = sum(p[0] for p in coords_pour_centroide) / len(coords_pour_centroide)
            clat = sum(p[1] for p in coords_pour_centroide) / len(coords_pour_centroide)
            ilot_centroide = ilot_pip(clon, clat)
            # Si centroide dans un polygone parmi les top -> on prend
            tied_top = {nm for nm, c in top if c == top[0][1]}
            if ilot_centroide in tied_top:
                chosen = ilot_centroide
            else:
                # fallback : 1er top alphabetique stable
                chosen = sorted(tied_top, key=lambda s: (len(s), s))[0]
        else:
            chosen = sorted({nm for nm, c in top if c == top[0][1]},
                            key=lambda s: (len(s), s))[0]

    if is_split:
        n_bgid_split += 1

    # Applique chosen aux adresses du bgid (sauf malformee)
    changed = []
    for cle in cles:
        info = result_pass1[cle]
        if info["method"] == PASS1_IL_MALFORMED:
            continue
        if final_ilot[cle] != chosen:
            old = final_ilot[cle]
            final_ilot[cle] = chosen
            n_addr_changed += 1
            if old in (None, "X"): n_addr_null_lifted += 1
            changed.append((cle, old, chosen))

    if is_split:
        n_bgid_resolved += 1
        arbitration_log.append({
            "bg": bg, "votes": dict(top), "tie": tie,
            "chosen": chosen, "n_changed": len(changed), "changed": changed[:5]})

print(f"  bgids total           : {n_bgid_total}")
print(f"  bgids splits trouves  : {n_bgid_split}")
print(f"  bgids resolus         : {n_bgid_resolved}")
print(f"  adresses reassignees  : {n_addr_changed}  (dont {n_addr_null_lifted} null/X -> ilot)")

# Sample arbitrage tie
ties = [a for a in arbitration_log if a["tie"]]
if ties:
    print()
    print(f"  Ties (centroide tie-break) : {len(ties)}")
    for t in ties[:5]:
        print(f"    bgid={t['bg'][-9:]} votes={t['votes']} -> chose '{t['chosen']}' "
              f"(n_changed={t['n_changed']})")

# --- 3. Stats finales ---
print()
print("=" * 80)
print("  RESULTATS FINAUX")
print("=" * 80)
dist_final = Counter()
n_x_final = n_null_final = 0
for cle, il in final_ilot.items():
    if il is None: n_null_final += 1
    elif il == "X": n_x_final += 1
    else: dist_final[il] += 1
print(f"  Total adresses : {len(final_ilot)}")
print(f"  Assignees a ilot 1..81 : {sum(dist_final.values())} "
      f"({100*sum(dist_final.values())/len(final_ilot):.1f}%)")
print(f"  X (hors-secteur)       : {n_x_final}")
print(f"  null                   : {n_null_final}  (incluant {n_mal} malformee)")
print()

def natkey(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s or "")]
print(f"  Distribution top 10 :")
for nm, n in sorted(dist_final.items(), key=lambda x: -x[1])[:10]:
    print(f"    ilot {nm:>4} : {n}")

# --- 4. Apply (--apply) ---
ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
args, _ = ap.parse_known_args()
if not args.apply:
    print()
    print("=" * 80)
    print("  DRY-RUN OK - rerunner avec --apply pour ecrire le light")
    print("=" * 80)
    sys.exit(0)

print()
print("=" * 80)
print("  APPLY")
print("=" * 80)
shutil.copy2(LIGHT, BAK)
print(f"  Backup : {BAK.name}")

n_written = 0
for a in doc["adresses"]:
    cle = a.get("cle") or ""
    if cle not in final_ilot: continue
    il = final_ilot[cle]
    a["_ilot"] = il  # None / 'X' / 'NN' string
    n_written += 1

LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
print(f"  Light ecrit : {LIGHT.name}  ({n_written} adresses tagguees _ilot)")
print()
print(">>> APPLY OK")
