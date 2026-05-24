#!/usr/bin/env python3
"""Assignation ilots 82+83+84 DL :
- ILOT 82 : manuel sur 27|AVENUE|LACASSAGNE + meme-bgid FA fauto
- ILOTS 83+84 : point-in-polygon strict depuis 'Secteur DL - new.kml'
  uniquement pour adresses _ilot='X' (pas de snap, pas d'override).
"""
import json, sys, shutil, xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

from shapely.geometry import Polygon, Point

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.preilots82_83_84.bak"
KML   = Path(r"C:/Users/Station 5/Downloads/Secteur DL - new.kml")

NS = {"kml": "http://www.opengis.net/kml/2.2"}


def parse_kml_polygons(p):
    root = ET.fromstring(p.read_text(encoding="utf-8"))
    out = {}
    for pm in root.findall(".//kml:Placemark", NS):
        name_el = pm.find("kml:name", NS)
        name = (name_el.text if name_el is not None else "").strip()
        polys = []
        for poly_el in pm.findall(".//kml:Polygon", NS):
            coords_el = poly_el.find(
                ".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
            if coords_el is None or not coords_el.text: continue
            pts = []
            for tok in coords_el.text.strip().split():
                parts = tok.split(",")
                if len(parts) < 2: continue
                pts.append((float(parts[0]), float(parts[1])))
            if len(pts) >= 3:
                polys.append(Polygon(pts))
        if name and polys:
            out[name] = polys
    return out


# ---------- Load ----------
print(f"[load] {LIGHT}")
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
md = doc.setdefault("metadata", {})
by_cle = {(a.get("cle") or ""): a for a in ad}
print(f"  {len(ad)} adresses light")

polys_by_name = parse_kml_polygons(KML)
print(f"[KML new] polygones : {sorted(polys_by_name.keys())} "
      f"({sum(len(v) for v in polys_by_name.values())} polygones total)")


# ---------- ILOT 82 manuel ----------
print()
print("=" * 90)
print("ILOT 82 - assignation manuelle (27 LACASSAGNE + meme bgid FA fauto)")
print("=" * 90)
ANC = "27|AVENUE|LACASSAGNE"
a27 = by_cle.get(ANC)
if not a27:
    sys.exit(f"  [ERR] {ANC} absent du light")
bg27 = a27.get("batiment_groupe_id")
print(f"  ancre : {ANC}  bgid={bg27}  ilot actuel={a27.get('_ilot')!r}")

# Toutes les adresses sur ce bgid + adresses fauto vers cette ancre
same_bg = [a for a in ad if a.get("batiment_groupe_id") == bg27]
fauto_to_27 = [a for a in ad if a.get("_fusion_cible") == ANC and a not in same_bg]
targets_82 = same_bg + fauto_to_27
print(f"  same bgid : {len(same_bg)}  | fauto vers 27 LAC (autres bgids) : {len(fauto_to_27)}")
print(f"  TOTAL adresses a tagger ilot=82 : {len(targets_82)}")
print()

assigned_82 = []
for a in targets_82:
    old = a.get("_ilot")
    a["_ilot"] = "82"
    cle = a.get("cle") or ""
    fa = "FA->%s" % a.get("_fusion_cible") if a.get("_fusion_auto") else "ancre"
    assigned_82.append((cle, old, fa))
    print(f"  {cle:42s}  ilot {old!r} -> '82'  ({fa})")


# ---------- ILOTS 83 + 84 point-in-polygon strict ----------
print()
print("=" * 90)
print("ILOTS 83 + 84 - point-in-polygon strict (uniquement _ilot='X')")
print("=" * 90)
polys83 = polys_by_name.get("83", [])
polys84 = polys_by_name.get("84", [])
print(f"  polygones 83 : {len(polys83)}  ;  polygones 84 : {len(polys84)}")

n_x_total = sum(1 for a in ad if a.get("_ilot") == "X")
print(f"  adresses _ilot='X' candidates : {n_x_total}")
print()

assigned_83 = []
assigned_84 = []
multi_match = []
n_x_remaining = 0

for a in ad:
    if a.get("_ilot") != "X": continue
    lon = a.get("longitude"); lat = a.get("latitude")
    if lon is None or lat is None:
        n_x_remaining += 1
        continue
    pt = Point(lon, lat)
    hit_83 = any(p.covers(pt) for p in polys83)
    hit_84 = any(p.covers(pt) for p in polys84)
    cle = a.get("cle") or ""
    if hit_83 and hit_84:
        multi_match.append(cle)
        # Aucune assignation auto si conflit (strict)
        n_x_remaining += 1
    elif hit_83:
        a["_ilot"] = "83"; assigned_83.append(cle)
    elif hit_84:
        a["_ilot"] = "84"; assigned_84.append(cle)
    else:
        n_x_remaining += 1

print(f"  ILOT 83 : {len(assigned_83)} adresses assignees")
for c in sorted(assigned_83): print(f"    {c}")
print()
print(f"  ILOT 84 : {len(assigned_84)} adresses assignees")
for c in sorted(assigned_84): print(f"    {c}")
print()
if multi_match:
    print(f"  CONFLITS (multi 83+84) : {len(multi_match)} (laissees _ilot='X')")
    for c in multi_match: print(f"    {c}")
print()
print(f"  _ilot='X' restant : {n_x_remaining} (hors polygones strict)")


# ---------- Metadata + Save ----------
md["_correctif_ilots_82_83_84"] = {
    "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "ilot_82": {
        "method": "manuel sur 27 LACASSAGNE + meme-bgid + fauto cible",
        "ancre": ANC, "bgid": bg27,
        "count": len(assigned_82),
        "assigned": [{"cle": c, "old_ilot": o, "src": s} for c, o, s in assigned_82],
    },
    "ilot_83_84": {
        "method": "point-in-polygon strict KML 'Secteur DL - new.kml'",
        "kml": str(KML),
        "polygones_83": len(polys83), "polygones_84": len(polys84),
        "candidates_x": n_x_total,
        "assigned_83": assigned_83, "assigned_84": assigned_84,
        "multi_match_skip": multi_match,
        "remaining_x": n_x_remaining,
    },
}

if BAK.exists():
    print(f"\n  [warn] backup existant -> ecrase")
shutil.copy2(LIGHT, BAK)
print(f"\n  [bak] {BAK.name}")
LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  [OK] LIGHT ecrit ({len(ad)} adresses)")
print()
print("=" * 90)
print(f"RESUME : ilot82={len(assigned_82)}  ilot83={len(assigned_83)}  "
      f"ilot84={len(assigned_84)}  conflits={len(multi_match)}  X_restant={n_x_remaining}")
print("=" * 90)
