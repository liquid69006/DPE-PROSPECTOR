#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche G - re-geocodage BAN des orphelins d'ilot MONTCHAT.

Re-derive la liste des orphelins (adresse RENDUE, non-secondaire de fusion,
_ilot in {'X', None}) depuis le light POST-Manche-A, puis re-geocode chaque
orphelin via l'API BAN forward (type=housenumber). N'ecrit les nouvelles coords
(longitude/latitude) QUE si le match est fiable :
  - score >= 0.5
  - meme voie (normalisation : la voie BAN doit matcher la voie de la cle)
La cle invalide DENY '|RUE|CELLARD' est SKIPPEE (pas de geocodage).

Ordre garanti : (1) MAJ coords ici -> (2) re-attribution _ilot par
_apply_ilot_kml_montchat.py --apply --snap 15 (lance separement).

Dry-run par defaut. '--apply' ecrit le light (backup .premancheG.bak) avec les
coords mises a jour SEULEMENT (n'attribue PAS _ilot : c'est le role du script
ilot relance ensuite). Prints ASCII-safe (cp1252, aucun accent/emoji).

Sortie JSON detaillee : data/_regeocode_orphans_montchat.json (avant/apres).
"""
import argparse, json, re, sys, time, shutil, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_montchat_light.json"
BAK = LIGHT.with_suffix(LIGHT.suffix + ".premancheG.bak")
OUT = ROOT / "data" / "_regeocode_orphans_montchat.json"

DENY_CLES = {"|RUE|CELLARD"}            # cle invalide DENY (Manche A)
BAN = "https://api-adresse.data.gouv.fr/search/"
MIN_SCORE = 0.5

# INSEE (code_iris[:5]) -> code postal
INSEE_CP = {"69383": "69003", "69388": "69008"}

# bbox KML Montchat (lon/lat) pour flag hors-perimetre
BBOX = {"lon_min": 4.8698, "lon_max": 4.8983, "lat_min": 45.7404, "lat_max": 45.7549}


def rendered(a):
    return not (a.get("_fusion_auto") and (a.get("_fusion_cible") or a.get("_fusion_auto_target")))


def norm_voie(s):
    """Normalisation grossiere de nom de voie pour comparaison BAN <-> cle."""
    s = (s or "").upper()
    s = s.replace("'", " ").replace("-", " ")
    # retrait accents simples
    repl = {"E":"EÉÈÊË","A":"AÀÂÄ","I":"IÎÏ","O":"OÔÖ","U":"UÙÛÜ","C":"CÇ"}
    table = {}
    for base, variants in repl.items():
        for ch in variants:
            table[ch] = base
    s = "".join(table.get(ch, ch) for ch in s)
    # retrait des mots-types de voie pour comparer le coeur du nom
    s = re.sub(r"\b(RUE|AVENUE|AV|COURS|PLACE|PL|IMPASSE|ALLEE|BOULEVARD|BD|QUAI|MONTEE|CHEMIN|PASSAGE|VILLA|SQUARE)\b", " ", s)
    s = re.sub(r"\b(DE|DU|DES|LA|LE|LES|D|L|AU|AUX)\b", " ", s)
    # abreviations courantes voie <-> BAN
    s = re.sub(r"\bST\b", "SAINT", s)
    s = re.sub(r"\bSTE\b", "SAINTE", s)
    s = re.sub(r"\bDR\b", "DOCTEUR", s)
    s = re.sub(r"\bGAL\b", "GENERAL", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(s.split())


def parse_cle(cle):
    """NUM|TYPE|VOIE -> (num, type, voie). num peut etre vide (cle invalide)."""
    parts = cle.split("|")
    if len(parts) < 3:
        return None
    num = parts[0].strip()
    typ = parts[1].strip()
    voie = "|".join(parts[2:]).strip()
    return num, typ, voie


def ban_query(q):
    url = BAN + "?" + urllib.parse.urlencode({"q": q, "limit": 1, "type": "housenumber"})
    req = urllib.request.Request(url, headers={"User-Agent": "dpe-prospector-mancheG"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    feats = data.get("features") or []
    if not feats:
        return None
    f = feats[0]
    p = f["properties"]
    g = f["geometry"]
    return {
        "label": p.get("label"), "score": p.get("score"),
        "street": p.get("street") or p.get("name"), "city": p.get("city"),
        "citycode": p.get("citycode"), "type": p.get("type"),
        "lon": g["coordinates"][0], "lat": g["coordinates"][1],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]

    orphans = [a for a in ad if a.get("_ilot") in ("X", None) and rendered(a)]
    print("[ORPHANS] rendus (_ilot X/None) : %d" % len(orphans))

    results = []
    n_fiable = n_pas_match = n_skip = 0

    for a in orphans:
        cle = a.get("cle") or ""
        rec = {
            "cle": cle, "bgid": a.get("batiment_groupe_id"),
            "ilot_avant": a.get("_ilot"),
            "lon_avant": a.get("longitude"), "lat_avant": a.get("latitude"),
            "ban": None, "decision": None, "raison": None,
            "lon_apres": a.get("longitude"), "lat_apres": a.get("latitude"),
        }

        if cle in DENY_CLES:
            rec["decision"] = "SKIP_DENY"
            rec["raison"] = "cle invalide DENY (Manche A) - non geocodee"
            n_skip += 1
            results.append(rec)
            print("  SKIP_DENY  %-36s" % cle)
            continue

        pc = parse_cle(cle)
        if not pc or not pc[0]:
            rec["decision"] = "SKIP_NONUM"
            rec["raison"] = "numero absent dans la cle - non geocodable"
            n_skip += 1
            results.append(rec)
            print("  SKIP_NONUM %-36s" % cle)
            continue
        num, typ, voie = pc

        # INSEE depuis code_iris ; sinon teste 69003 puis 69008
        iris = str(a.get("code_iris") or "")
        cps = []
        if iris[:5] in INSEE_CP:
            cps = [INSEE_CP[iris[:5]]]
        else:
            cps = ["69003", "69008"]

        best = None
        for cp in cps:
            q = "%s %s %s Lyon" % (num, voie, cp)
            try:
                hit = ban_query(q)
            except Exception as e:
                hit = None
                rec["raison"] = "BAN erreur reseau: %s" % e
            time.sleep(0.12)
            if hit is None:
                continue
            # garde le meilleur score
            if best is None or (hit["score"] or 0) > (best["score"] or 0):
                best = hit
            # si match voie + score ok sur ce cp, stop
            if (hit["score"] or 0) >= MIN_SCORE and norm_voie(hit["street"]) == norm_voie(voie):
                best = hit
                break

        rec["ban"] = best
        if best is None:
            rec["decision"] = "PAS_MATCH"
            rec["raison"] = rec["raison"] or "BAN ne retourne rien"
            n_pas_match += 1
            results.append(rec)
            print("  PAS_MATCH  %-36s (BAN vide)" % cle)
            continue

        score = best["score"] or 0
        same_voie = norm_voie(best["street"]) == norm_voie(voie)
        if score >= MIN_SCORE and same_voie:
            rec["decision"] = "FIABLE"
            rec["raison"] = "score %.4f, voie BAN '%s' == cle '%s'" % (score, best["street"], voie)
            rec["lon_apres"] = best["lon"]
            rec["lat_apres"] = best["lat"]
            n_fiable += 1
            moved = (best["lon"] != rec["lon_avant"]) or (best["lat"] != rec["lat_avant"])
            print("  FIABLE     %-36s score=%.3f voie='%s' %s" % (
                cle, score, best["street"], "(coords inchangees)" if not moved else "(coords MAJ)"))
        else:
            rec["decision"] = "PAS_MATCH"
            if not same_voie:
                rec["raison"] = "voie BAN '%s' != cle '%s' (score %.4f) - coords inchangees" % (
                    best["street"], voie, score)
            else:
                rec["raison"] = "score faible %.4f < %.2f - coords inchangees" % (score, MIN_SCORE)
            n_pas_match += 1
            print("  PAS_MATCH  %-36s %s" % (cle, rec["raison"]))
        results.append(rec)

    # flag hors-bbox KML (sur coords apres, si dispo)
    for rec in results:
        lon = rec["lon_apres"]; lat = rec["lat_apres"]
        rec["hors_bbox"] = False
        if lon is not None and lat is not None:
            if not (BBOX["lon_min"] <= lon <= BBOX["lon_max"] and BBOX["lat_min"] <= lat <= BBOX["lat_max"]):
                rec["hors_bbox"] = True

    print()
    print("[BILAN regeocode] FIABLE=%d  PAS_MATCH=%d  SKIP=%d  (total %d)" % (
        n_fiable, n_pas_match, n_skip, len(orphans)))
    hb = [r for r in results if r.get("hors_bbox") and r["decision"] != "SKIP_DENY"]
    print("[BILAN regeocode] hors-bbox KML (apres) : %d" % len(hb))
    for r in hb:
        print("    hors-bbox %-36s lon=%s lat=%s" % (r["cle"], r["lon_apres"], r["lat_apres"]))

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[OUT] %s" % OUT.name)

    if not args.apply:
        print()
        print("DRY-RUN OK - rerunner avec --apply pour ecrire les coords FIABLE")
        return

    # APPLY : ecrit UNIQUEMENT les coords FIABLE (n'attribue PAS _ilot)
    shutil.copy2(LIGHT, BAK)
    print("[APPLY] backup : %s" % BAK.name)
    by_cle = {r["cle"]: r for r in results if r["decision"] == "FIABLE"}
    n_written = 0
    for a in ad:
        cle = a.get("cle") or ""
        r = by_cle.get(cle)
        if r is None:
            continue
        a["longitude"] = r["lon_apres"]
        a["latitude"] = r["lat_apres"]
        a["_coord_source"] = "ban_regeocode_mancheG"
        n_written += 1
    meta = doc.setdefault("metadata", {})
    meta["_correctif_regeocode_mancheG"] = (
        "Manche G : re-geocodage BAN housenumber des orphelins d'ilot ; "
        "%d coords FIABLE mises a jour (score>=%.2f + meme voie). "
        "_ilot re-attribue ensuite par _apply_ilot_kml_montchat.py --apply --snap 15. "
        "DENY/no-num/non-fiable inchanges." % (n_written, MIN_SCORE))
    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[APPLY] light ecrit : %d coords mises a jour" % n_written)
    print(">>> APPLY OK (coords seulement ; relancer _apply_ilot_kml_montchat.py)")


if __name__ == "__main__":
    main()
