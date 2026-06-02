#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jointure spatiale KML -> _ilot dans secteur_montchat_light.json.

Calque generique de scripts/_apply_ilot_kml_dl.py, adapte a Montchat :
  - source = data/kml/Ilotage_Montchat.kml (134 polygones, 133 placemarks ;
    le placemark "162" porte 2 anneaux a unir, "118" apparait sur 2 placemarks).
  - FIXES KML :
      (1) refermer "162" : ses 2 anneaux (1 sliver triangulaire + le corps)
          sont UNIS (unary_union) en un seul polygone ferme ;
      (2) renommer le PLUS PETIT ilot "118" en "195" (2 placemarks portent
          "118" ; le plus petit en aire devient 195 -> noms uniques, 195 present).
  - snap orphelins parametrable (--snap M, defaut 5 m comme DL) ; mode
    --sweep affiche le tableau orphelins/snaps/cross-rue par rayon (5/10/15/25).

POLITIQUE (identique DL) :
  (1) Point-in-polygon direct -> _ilot = nom (apres fixes)
  (2) Hors polygone <= SNAP m -> snap au plus proche
  (3) Hors polygone > SNAP m -> _ilot = 'X' (hors-secteur / orphelin)
  (4) Bgids split (>=2 ilots) -> arbitrage MAJORITE (tie-break = centroide bati)
  (5) Adresses null/X au sein d'un bgid avec votes -> ilot majoritaire
  (6) Coords absentes -> _ilot = null

code_iris est CONSERVE intact (pose par make_light_montchat, sert aux stats).

Dry-run par defaut. '--apply' ecrit le light + backup .preilot.bak.
Detection cross-rue : tout snap > CROSS_RUE_WARN m (defaut 15) est rapporte
pour inspection (heuristique : un snap trop long traverse potentiellement une voie).
"""
import argparse, re, sys, json, math, shutil, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from shapely.ops import nearest_points, unary_union

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_montchat_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".preilot.bak")
KML   = ROOT / "data" / "kml" / "Ilotage_Montchat.kml"

NS = {"kml": "http://www.opengis.net/kml/2.2"}
CROSS_RUE_WARN = 15.0   # snap > ce seuil = a inspecter (cross-rue potentiel)


def parse_kml_montchat(p):
    """Parse le KML Montchat avec les 2 fixes.

    Retourne liste [(name, geometry)] avec noms uniques, "162" referme
    (anneaux unis) et le plus petit "118" renomme "195".
    """
    root = ET.fromstring(p.read_text(encoding="utf-8"))
    raw = []   # (name, [Polygon,...])
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
                parts = tok.split(",")
                if len(parts) < 2:
                    continue
                pts.append((float(parts[0]), float(parts[1])))
            # refermer l'anneau si necessaire (garde-fou)
            if len(pts) >= 3 and pts[0] != pts[-1]:
                pts.append(pts[0])
            if len(pts) >= 4:
                rings.append(Polygon(pts).buffer(0))
        if name and rings:
            raw.append((name, rings))

    # FIX 162 : unir les anneaux multiples d'un meme placemark
    merged = []   # (name, geom)
    for name, rings in raw:
        geom = unary_union(rings) if len(rings) > 1 else rings[0]
        geom = geom.buffer(0)
        merged.append((name, geom))

    # FIX 118->195 : renommer le PLUS PETIT des 2 placemarks "118" en "195"
    idx118 = [i for i, (nm, _) in enumerate(merged) if nm == "118"]
    if len(idx118) >= 2:
        smallest = min(idx118, key=lambda i: merged[i][1].area)
        nm, g = merged[smallest]
        merged[smallest] = ("195", g)
        print(f"[FIX] {len(idx118)} ilots '118' -> le plus petit (aire="
              f"{g.area:.3e}) renomme '195'")
    elif len(idx118) == 1:
        print("[FIX] un seul ilot '118' (rien a renommer en 195) !")
    else:
        print("[FIX] aucun ilot '118' trouve !")
    return merged


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))


# --- 1. Parse KML + fixes ---
ents = parse_kml_montchat(KML)
geoms = [g for _, g in ents]
names = [n for n, _ in ents]
tree = STRtree(geoms)
print(f"[KML] ilots (apres fixes) : {len(ents)}  (attendu 133 noms uniques)")
dup = [n for n, c in Counter(names).items() if c > 1]
print(f"[KML] noms dupliques restants : {dup if dup else 'aucun'}")
print(f"[KML] '195' present : {'195' in names} | '162' present : {'162' in names}")


def ilot_pip(lon, lat):
    pt = Point(lon, lat)
    for idx in tree.query(pt):
        if geoms[idx].covers(pt):
            return names[idx]
    return None


def ilot_snap(lon, lat, max_m):
    """Polygone le plus proche dans max_m. Retourne (nom, dist) ou (None, dist)."""
    pt = Point(lon, lat)
    best_idx, best_d = None, float("inf")
    deg_pad = max_m / 100000.0
    for idx in tree.query(Point(lon, lat).buffer(deg_pad)):
        g = geoms[idx]
        np_geom, _ = nearest_points(g, pt)
        d = haversine_m(lat, lon, np_geom.y, np_geom.x)
        if d < best_d:
            best_d, best_idx = d, idx
    if best_idx is not None and best_d <= max_m:
        return names[best_idx], best_d
    return (None, best_d if best_idx is not None else None)


# --- 2. Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
print(f"[light] adresses chargees : {len(ad)}")

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--snap", type=float, default=5.0)
ap.add_argument("--sweep", action="store_true",
                help="affiche le tableau orphelins par rayon, n'ecrit pas")
args, _ = ap.parse_known_args()


def classify_pass1(snap_max):
    res = {}
    n_pip = n_snap = n_x = n_null = 0
    snap_list = []
    for a in ad:
        cle = a.get("cle") or ""
        bg = a.get("batiment_groupe_id") or None
        lat = a.get("latitude"); lon = a.get("longitude")
        if lat is None or lon is None:
            res[cle] = {"ilot": None, "method": "null", "snap_d": None,
                        "lat": lat, "lon": lon, "bg": bg}
            n_null += 1
            continue
        il = ilot_pip(lon, lat)
        if il is not None:
            res[cle] = {"ilot": il, "method": "pip", "snap_d": 0.0,
                        "lat": lat, "lon": lon, "bg": bg}
            n_pip += 1
            continue
        snap_il, dist = ilot_snap(lon, lat, snap_max)
        if snap_il is not None:
            res[cle] = {"ilot": snap_il, "method": "snap", "snap_d": dist,
                        "lat": lat, "lon": lon, "bg": bg}
            n_snap += 1
            snap_list.append((cle, snap_il, dist))
            continue
        res[cle] = {"ilot": "X", "method": "x",
                    "snap_d": dist if dist is not None else None,
                    "lat": lat, "lon": lon, "bg": bg}
        n_x += 1
    return res, (n_pip, n_snap, n_x, n_null), snap_list


# --- SWEEP : tableau par rayon ---
if args.sweep:
    print()
    print("=" * 80)
    print("  TUNING SNAP - orphelins / snaps / cross-rue par rayon")
    print("=" * 80)
    print(f"  {'rayon':>6} | {'PIP':>5} | {'snap':>5} | {'orphelins(X)':>12} | "
          f"{'snap>15m':>9}")
    print("  " + "-" * 60)
    for r in (5, 10, 15, 25):
        _, (np_, ns_, nx_, nn_), sl = classify_pass1(float(r))
        cross = [(c, il, d) for c, il, d in sl if d > CROSS_RUE_WARN]
        print(f"  {r:>5}m | {np_:>5} | {ns_:>5} | {nx_:>12} | {len(cross):>9}")
        if cross:
            for c, il, d in sorted(cross, key=lambda x: -x[2])[:8]:
                print(f"          snap {c:36s} -> {il:>4} ({d:.1f}m)")
    print("=" * 80)
    sys.exit(0)


# --- 3. PASS 1 au rayon retenu ---
SNAP_MAX_M = args.snap
result_pass1, (n_pip, n_snap, n_x, n_null), snap_list = classify_pass1(SNAP_MAX_M)
print()
print(f"[PASS 1] snap retenu   : {SNAP_MAX_M:.0f} m")
print(f"[PASS 1] direct PIP    : {n_pip:>4} ({100*n_pip/len(ad):.1f}%)")
print(f"[PASS 1] snap <={SNAP_MAX_M:.0f}m    : {n_snap:>4} ({100*n_snap/len(ad):.1f}%)")
print(f"[PASS 1] X (>{SNAP_MAX_M:.0f}m)       : {n_x:>4} ({100*n_x/len(ad):.1f}%)")
print(f"[PASS 1] null (sans coords): {n_null:>4} ({100*n_null/len(ad):.1f}%)")
cross = [(c, il, d) for c, il, d in snap_list if d > CROSS_RUE_WARN]
print(f"[PASS 1] snaps > {CROSS_RUE_WARN:.0f}m (cross-rue a inspecter) : {len(cross)}")
for c, il, d in sorted(cross, key=lambda x: -x[2])[:10]:
    print(f"    {c:38s} -> ilot {il:>4} (snap={d:.2f}m)")

# --- PASS 2 : arbitrage per-bgid ---
print()
print("[PASS 2] arbitrage per-bgid (majorite + centroide tie-break)")
by_bgid = defaultdict(list)
for cle, info in result_pass1.items():
    if info["bg"]:
        by_bgid[info["bg"]].append(cle)

n_bgid_split = n_bgid_resolved = n_addr_changed = n_addr_null_lifted = 0
final_ilot = {cle: info["ilot"] for cle, info in result_pass1.items()}

for bg, cles in by_bgid.items():
    votes = Counter()
    coords = []
    for cle in cles:
        info = result_pass1[cle]
        if info["ilot"] is not None and info["ilot"] != "X":
            votes[info["ilot"]] += 1
        if info["lat"] is not None and info["lon"] is not None:
            coords.append((info["lon"], info["lat"]))
    if not votes:
        continue
    top = votes.most_common()
    is_split = len(set(votes.keys())) >= 2
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
            chosen = sorted({nm for nm, c in top if c == top[0][1]},
                            key=lambda s: (len(s), s))[0]
    if is_split:
        n_bgid_split += 1
    changed = 0
    for cle in cles:
        if final_ilot[cle] != chosen:
            old = final_ilot[cle]
            final_ilot[cle] = chosen
            n_addr_changed += 1
            if old in (None, "X"):
                n_addr_null_lifted += 1
            changed += 1
    if is_split and changed:
        n_bgid_resolved += 1

print(f"  bgids splits trouves  : {n_bgid_split}")
print(f"  bgids resolus         : {n_bgid_resolved}")
print(f"  adresses reassignees  : {n_addr_changed}  (dont {n_addr_null_lifted} null/X -> ilot)")

# --- 4. Stats finales ---
print()
print("=" * 80)
print("  RESULTATS FINAUX")
print("=" * 80)
dist_final = Counter()
n_x_final = n_null_final = 0
for cle, il in final_ilot.items():
    if il is None:
        n_null_final += 1
    elif il == "X":
        n_x_final += 1
    else:
        dist_final[il] += 1
uniq_names = set(names)
print(f"  Total adresses          : {len(final_ilot)}")
print(f"  Assignees a un ilot     : {sum(dist_final.values())} "
      f"({100*sum(dist_final.values())/len(final_ilot):.1f}%)")
print(f"  X (orphelin > snap)     : {n_x_final}")
print(f"  null (sans coords)      : {n_null_final}")
print(f"  ilots peuples           : {len(dist_final)} / {len(uniq_names)}")
vides = sorted(uniq_names - set(dist_final.keys()),
               key=lambda s: [int(t) if t.isdigit() else t
                              for t in re.split(r'(\d+)', s)])
print(f"  ilots VIDES             : {len(vides)} {vides if len(vides) <= 30 else vides[:30]}")
print(f"  '195' peuple ?          : {dist_final.get('195', 0)} adresses")
print(f"  '162' peuple ?          : {dist_final.get('162', 0)} adresses")
vals = sorted(dist_final.values())
import statistics
print(f"  adresses/ilot min/med/max : {vals[0]} / "
      f"{statistics.median(vals):.0f} / {vals[-1]}")
print()
print("  Distribution top 10 :")
for nm, n in sorted(dist_final.items(), key=lambda x: -x[1])[:10]:
    print(f"    ilot {nm:>5} : {n}")

# --- 5. Apply ---
if not args.apply:
    print()
    print("=" * 80)
    print("  DRY-RUN OK - rerunner avec --apply (et --snap M) pour ecrire")
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
    if cle not in final_ilot:
        continue
    a["_ilot"] = final_ilot[cle]   # None / 'X' / 'NN'
    n_written += 1
meta = doc.setdefault("metadata", {})
meta["_correctif_ilot_kml"] = (
    f"_ilot pose par point-in-polygon KML Ilotage_Montchat.kml "
    f"({len(uniq_names)} ilots, fixes 118->195 + 162 unifie), snap "
    f"{SNAP_MAX_M:.0f} m, {n_x_final} orphelins X, {n_null_final} null. "
    f"code_iris conserve (stats Filosofi/INSEE).")
LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
print(f"  Light ecrit : {LIGHT.name}  ({n_written} adresses tagguees _ilot)")
print(">>> APPLY OK")
