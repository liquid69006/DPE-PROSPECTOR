#!/usr/bin/env python3
"""hr-actifs DL avec scan parcelle live - enrichit cache + analyse."""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"
CACHE_BG = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc["adresses"]
co  = doc["coproprietes"]
kv  = json.loads(KV.read_text(encoding="utf-8"))
assignments = kv.get("assignments") or {}
fusions     = kv.get("fusions") or {}

cache_bg  = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}
cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8")) if CACHE_RNC.exists() else {}

def to_int(x):
    try: return int(x)
    except Exception: return 0

co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}
immat_secteur = {c.get("numero_immatriculation") for c in co if c.get("numero_immatriculation")}

# hr-actifs
hr_actifs = []
for a in ad:
    cle = a.get("cle") or ""
    if cle in co_by_cle: continue
    if a.get("numero_immatriculation"): continue
    if a.get("_fusion_auto"): continue
    if to_int(a.get("nb_ventes_logement")) <= 0: continue
    if to_int(a.get("nb_log_bdnb")) <= 1: continue
    hr_actifs.append(a)
hr_actifs.sort(key=lambda a: (-to_int(a.get("nb_ventes_logement")),
                               -to_int(a.get("nb_log_bdnb"))))

def qualif_kv(cle):
    if cle in assignments: return assignments[cle].get("type","?")
    if cle in fusions: return "fusion-src->" + fusions[cle]
    if cle in fusions.values(): return "fusion-tgt"
    return None

# --- Network helpers (reproduit logique scan_horsrnc_parcelle.py) ---
BDNB_PARC = "https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq."
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

def bdnb_to_rnc(bdnb_p):
    if not bdnb_p or len(bdnb_p) < 14: return None
    if bdnb_p[:2] == "69" and bdnb_p[5:8] == "000":
        return "69123383" + bdnb_p[8:]
    if bdnb_p[:2] == "75" and bdnb_p[5:8] == "000":
        return "75056" + bdnb_p[2:5] + bdnb_p[8:]
    return None

def fetch_bdnb_parcelles(bgid):
    if bgid in cache_bg: return cache_bg[bgid]
    url = BDNB_PARC + bgid
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            rows = json.loads(r.read())
        parcs = [x.get("parcelle_id") for x in rows if x.get("parcelle_id")]
    except Exception as e:
        print(f"   ! BDNB parcelle err {bgid}: {e}")
        parcs = []
    cache_bg[bgid] = parcs
    time.sleep(0.05)
    return parcs

def fetch_rnc_by_refcad(parc_rnc):
    if parc_rnc in cache_rnc: return cache_rnc[parc_rnc]
    seen = {}
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": parc_rnc})
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception as e:
            print(f"   ! RNC live err {col}={parc_rnc}: {e}")
            data = []
        for row in data:
            im = row.get("numero_immatriculation")
            if im and im not in seen:
                seen[im] = {
                    "immat": im,
                    "nom": row.get("nom_usage_copropriete") or "",
                    "syndic": row.get("nom_personne_morale") or "",
                    "adresse": row.get("adresse_reference") or "",
                    "nb_lots_total": row.get("nombre_total_lots"),
                    "nb_lots_habit": row.get("nombre_lots_usage_habitation"),
                    "ref_match_col": col,
                }
        time.sleep(0.08)
    out = list(seen.values())
    cache_rnc[parc_rnc] = out
    return out

# --- Enrichissement cache pour les bgids hr-actifs ---
print("=" * 110)
print("ENRICHISSEMENT cache parcelle (scan live) pour les 28 hr-actifs")
print("=" * 110)
to_query_bg = [a for a in hr_actifs
               if a.get("batiment_groupe_id") and a["batiment_groupe_id"] not in cache_bg]
print(f"  bgids a interroger BDNB rel_parcelle : {len(to_query_bg)}")
for a in to_query_bg:
    bg = a["batiment_groupe_id"]
    parcs = fetch_bdnb_parcelles(bg)
    print(f"    {bg[-9:]} -> {parcs or '(0 parcelle)'}")

# Pour chaque parcelle BDNB obtenue, query RNC si pas en cache
to_query_rnc = set()
for a in hr_actifs:
    for pb in cache_bg.get(a.get("batiment_groupe_id") or "", []):
        pr = bdnb_to_rnc(pb)
        if pr and pr not in cache_rnc:
            to_query_rnc.add(pr)
print(f"\n  parcelles RNC a interroger live (3 cols) : {len(to_query_rnc)}")
for pr in sorted(to_query_rnc):
    hits = fetch_rnc_by_refcad(pr)
    if hits:
        print(f"    {pr} -> {len(hits)} candidat(s)")
        for h in hits:
            in_sct = " [DEJA-SECTEUR]" if h["immat"] in immat_secteur else ""
            print(f"      {h['immat']}  '{h['nom'][:38]}'  lots_tot={h['nb_lots_total']} hab={h['nb_lots_habit']}{in_sct}")
    else:
        print(f"    {pr} -> 0 candidat")

# Persistance cache
CACHE_BG.write_text(json.dumps(cache_bg, ensure_ascii=False, indent=2), encoding="utf-8")
CACHE_RNC.write_text(json.dumps(cache_rnc, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n  Caches mis a jour : _bgid_parcelle_dl ({len(cache_bg)} entrees), "
      f"_scan_parc_rnc_dl ({len(cache_rnc)} entrees)")

# --- Tableau final ---
print()
print("=" * 110)
print("TABLEAU FINAL - 28 hr-actifs DL avec appairage RNC")
print("=" * 110)
print()
print(f"{'#':2s} | {'cle':32s} | {'vlog':4s} | {'bdnb':4s} | {'bgid':10s} | maj|sci|"
      f"{'SCI nom':18s}| {'KV':10s} | candidats RNC live")
print("-" * 158)

def rnc_cands(bgid):
    parcs = cache_bg.get(bgid) or []
    out, seen = [], set()
    for pb in parcs:
        pr = bdnb_to_rnc(pb)
        for h in (cache_rnc.get(pr) or []):
            im = h["immat"]
            if im in seen: continue
            seen.add(im)
            in_sct = im in immat_secteur
            out.append({"immat": im, "nom": h["nom"], "lots_tot": h["nb_lots_total"],
                        "lots_hab": h["nb_lots_habit"], "parc": pr, "in_secteur": in_sct})
    return out

for i, a in enumerate(hr_actifs, 1):
    cle = a.get("cle") or ""
    vlog = to_int(a.get("nb_ventes_logement"))
    bdnb = to_int(a.get("nb_log_bdnb"))
    bg = a.get("batiment_groupe_id") or ""
    bg9 = bg[-9:] if bg else "-"
    majic = "Y" if a.get("dans_majic") else "n"
    sci   = "Y" if a.get("sci_proprietaire") == "oui" else "n"
    sci_nom = (a.get("sci_nom") or "")[:17]
    q = qualif_kv(cle) or "(non q.)"
    cands = rnc_cands(bg)
    new_c = [c for c in cands if not c["in_secteur"]]
    in_c  = [c for c in cands if c["in_secteur"]]
    msg_parts = []
    if new_c:
        msg_parts.append(f">>> {len(new_c)} HORS-SCT")
        for c in new_c[:2]:
            msg_parts.append(f"{c['immat']}({c['lots_hab']}hab)")
    if in_c:
        msg_parts.append(f"[{len(in_c)} deja-sct]")
    if not cands and bg in cache_bg:
        msg_parts.append("0 hit parcelle")
    if not bg:
        msg_parts.append("orpheline")
    msg = " ".join(msg_parts) or "-"
    print(f"{i:2d} | {cle:32s} | {vlog:4d} | {bdnb:4d} | ...{bg9} | {majic}  | {sci}  |"
          f" {sci_nom:18s}| {q:10s} | {msg}")

# Resume
print()
print("=" * 110)
print("RESUME APPAIRAGE")
print("=" * 110)
n_qual = sum(1 for a in hr_actifs if qualif_kv(a.get('cle') or ''))
n_new_cand = sum(1 for a in hr_actifs if [c for c in rnc_cands(a.get("batiment_groupe_id") or "") if not c["in_secteur"]])
n_in_cand  = sum(1 for a in hr_actifs if [c for c in rnc_cands(a.get("batiment_groupe_id") or "") if c["in_secteur"]])
n_orph = sum(1 for a in hr_actifs if not a.get("batiment_groupe_id"))
n_nocand = sum(1 for a in hr_actifs if a.get("batiment_groupe_id") in cache_bg and not rnc_cands(a.get("batiment_groupe_id")))
print(f"  Total hr-actifs       : {len(hr_actifs)}")
print(f"  Deja qualifies KV     : {n_qual}")
print(f"  Candidats RNC nouveaux: {n_new_cand}  (potentiel INJECT/RE-FUSE)")
print(f"  Candidats deja-secteur: {n_in_cand}   (deja dans coproprietes[], appairage cle existante)")
print(f"  Sans hit parcelle     : {n_nocand}    (vraie hr-ancre sans copro RNC)")
print(f"  Sans bgid (orpheline) : {n_orph}")
