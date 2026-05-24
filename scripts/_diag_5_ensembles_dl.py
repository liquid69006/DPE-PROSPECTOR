#!/usr/bin/env python3
"""
Dry-run lecture seule : 5 ensembles immobiliers DL confirmes terrain.

Pour chaque ensemble :
  - bgid de chaque adresse (mono / multi)
  - numero_immatriculation RNC declare sur 1 des adresses ?
  - parcelles BDNB et conversion RNC ref_cad
  - candidats RNC live (snapshot vs ref_cad live)
  - status make_light (_bdnb_match, _fusion_auto)
  - KV live qualif courante
  - Mecanisme propose : RE-FUSE / INJECT / REBIND / LABEL / SKIP
  - Delta parc estime (lots BDNB potentiellement dedupliques ou switch)

Sources :
  - LIGHT  : data/secteur_dauphine_lacassagne_light.json
  - KV     : API live (TOKEN env DPE_TOKEN ou argv1)
  - BDNB   : cache _bgid_parcelle_dl.json + fetch live si manquant
  - RNC    : cache _scan_parc_rnc_dl.json + fetch live ref_cad si manquant
"""
import json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
os.environ.setdefault("PYTHONUTF8", "1")

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
CACHE_BG  = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"

API   = "https://dpe-prospector-api.yann-bufferne.workers.dev"
TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

ENSEMBLES = [
    {"id": 1, "label": "3 MAURICE FLANDIN ensemble 3/5/7",
     "cles": ["3|RUE|MAURICE FLANDIN",
              "5|RUE|MAURICE FLANDIN",
              "7|RUE|MAURICE FLANDIN"]},
    {"id": 2, "label": "15 RICHERAND + 13 RICHERAND + 36 ST ANTOINE",
     "cles": ["15|RUE|ETIENNE RICHERAND",
              "13|RUE|ETIENNE RICHERAND",
              "36|RUE|ST ANTOINE"]},
    {"id": 3, "label": "7 METALLURGIE + 180 FELIX FAURE",
     "cles": ["7|RUE|METALLURGIE",
              "180|AVENUE|FELIX FAURE"]},
    {"id": 4, "label": "125 DAUPHINE + 228/230 FELIX FAURE",
     "cles": ["125|RUE|DAUPHINE",
              "228|AVENUE|FELIX FAURE",
              "230|AVENUE|FELIX FAURE"]},
    {"id": 5, "label": "4 TERNOIS + 93 BELLECOMBE + 18 ST ANTOINE",
     "cles": ["4|RUE|TERNOIS",
              "93|RUE|BELLECOMBE",
              "18|RUE|ST ANTOINE"]},
]


def to_int(x):
    try: return int(x)
    except Exception: return 0


# ---------- 1. KV live ----------
kv = {"assignments": {}, "fusions": {}}
if TOKEN:
    req = urllib.request.Request(
        f"{API}/secteur-assignments/dauphine-lacassagne",
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": UA,
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            kv = json.loads(r.read())
        print(f"[KV live] assignments={len(kv.get('assignments') or {})}  "
              f"fusions={len(kv.get('fusions') or {})}")
    except Exception as e:
        print(f"[KV live] err: {e} - fallback local")
        kv = json.loads((ROOT / "data" / "_kv_assign_dl.json").read_text(encoding="utf-8"))
else:
    kv = json.loads((ROOT / "data" / "_kv_assign_dl.json").read_text(encoding="utf-8"))
    print(f"[KV local] assignments={len(kv.get('assignments') or {})}")
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
fusion_tgts = set(fusions.values())


def kv_type(cle):
    if cle in assigns: return (assigns[cle] or {}).get("type")
    if cle in fusions: return f"fusion-src->{fusions[cle]}"
    if cle in fusion_tgts: return "fusion-tgt"
    return None


# ---------- 2. light ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad_by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
immat_secteur = {c.get("numero_immatriculation") for c in doc["coproprietes"]
                 if c.get("numero_immatriculation")}
print(f"[light]   {len(ad_by_cle)} adresses, {len(co_by_cle)} coproprietes")


# ---------- 3. Caches BDNB + RNC ----------
cache_bg  = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}
cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8")) if CACHE_RNC.exists() else {}

BDNB_PARC = ("https://api.bdnb.io/v1/bdnb/donnees/"
             "rel_batiment_groupe_parcelle?batiment_groupe_id=eq.")
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
    if not bgid: return []
    if bgid in cache_bg: return cache_bg[bgid]
    try:
        with urllib.request.urlopen(BDNB_PARC + bgid, timeout=20) as r:
            parcs = [x.get("parcelle_id") for x in json.loads(r.read()) if x.get("parcelle_id")]
    except Exception as e:
        print(f"   ! BDNB parcelle err {bgid}: {e}")
        parcs = []
    cache_bg[bgid] = parcs
    time.sleep(0.05)
    return parcs


def fetch_rnc_by_refcad(parc_rnc):
    if not parc_rnc: return []
    if parc_rnc in cache_rnc: return cache_rnc[parc_rnc]
    seen = {}
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": parc_rnc})
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
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
                    "nom":     row.get("nom_usage_copropriete") or "",
                    "syndic":  row.get("nom_personne_morale") or "",
                    "adresse": row.get("adresse_reference") or "",
                    "lots_tot": row.get("nombre_total_lots"),
                    "lots_hab": row.get("nombre_lots_usage_habitation"),
                    "date_immat": row.get("date_premiere_immatriculation") or "",
                    "ref_col": col,
                }
        time.sleep(0.08)
    out = list(seen.values())
    cache_rnc[parc_rnc] = out
    return out


def addr_dump(cle):
    """Snapshot info pour une adresse de l'ensemble."""
    a  = ad_by_cle.get(cle)
    co = co_by_cle.get(cle)
    if not a and not co:
        return {"cle": cle, "absent": True}
    bg = (a or {}).get("batiment_groupe_id") or ""
    immat = (a or {}).get("numero_immatriculation") or (co or {}).get("numero_immatriculation") or ""
    parcs_bg = fetch_bdnb_parcelles(bg) if bg else []
    return {
        "cle":   cle,
        "absent": False,
        "in_light": bool(a),
        "in_co":   bool(co),
        "bgid":  bg,
        "immat": immat,
        "nom_copro": (co or {}).get("nom_usage_copropriete") or "",
        "lots_tot": (co or {}).get("nombre_total_lots"),
        "lots_hab": (co or {}).get("nombre_lots_usage_habitation"),
        "syndic":  (co or {}).get("nom_personne_morale") or "",
        "bdnb":  to_int((a or {}).get("nb_log_bdnb")),
        "vlog":  to_int((a or {}).get("nb_ventes_logement")),
        "rot":   (a or {}).get("taux_rotation_logement"),
        "bdnb_match": (a or {}).get("_bdnb_match"),
        "fauto":      (a or {}).get("_fusion_auto"),
        "fauto_tgt":  (a or {}).get("_fusion_auto_tgt"),
        "sci":   (a or {}).get("sci_proprietaire") == "oui",
        "sci_n": (a or {}).get("sci_nom"),
        "parcs_bg": parcs_bg,
        "parcs_rnc": [bdnb_to_rnc(p) for p in parcs_bg if bdnb_to_rnc(p)],
        "kv":    kv_type(cle),
    }


# ---------- 4. Enrichissement cache pour les ensembles ----------
print()
print("=" * 110)
print("ENRICHISSEMENT cache (BDNB rel_parcelle + RNC live ref_cad) pour les 5 ensembles")
print("=" * 110)
all_bgids = []
for ens in ENSEMBLES:
    for c in ens["cles"]:
        a = ad_by_cle.get(c)
        if a and a.get("batiment_groupe_id"): all_bgids.append(a["batiment_groupe_id"])
new_bg = [b for b in all_bgids if b not in cache_bg]
print(f"  bgids a interroger BDNB rel_parcelle : {len(new_bg)} (sur {len(set(all_bgids))} uniques)")
for bg in new_bg:
    parcs = fetch_bdnb_parcelles(bg)
    print(f"    ...{bg[-9:]} -> {parcs}")

# RNC live pour les parcelles nouvelles
new_rnc = set()
for bg in set(all_bgids):
    for pb in cache_bg.get(bg, []):
        pr = bdnb_to_rnc(pb)
        if pr and pr not in cache_rnc: new_rnc.add(pr)
print(f"  parcelles RNC a interroger live   : {len(new_rnc)}")
for pr in sorted(new_rnc):
    hits = fetch_rnc_by_refcad(pr)
    print(f"    {pr} -> {len(hits)} cand(s)")

# Persistance caches
if new_bg or new_rnc:
    CACHE_BG.write_text(json.dumps(cache_bg, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE_RNC.write_text(json.dumps(cache_rnc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  caches persistes.")


# ---------- 5. Affichage detaille par ensemble ----------
print()
for ens in ENSEMBLES:
    print("=" * 110)
    print(f"ENSEMBLE #{ens['id']}  {ens['label']}")
    print("=" * 110)

    rows = [addr_dump(c) for c in ens["cles"]]

    # Tableau synoptique
    print(f"  {'cle':38s} | {'in_co':>5s} | {'bgid (last 9)':14s} | "
          f"{'immat':10s} | {'bdnb':>4s} | {'vlog':>4s} | {'parcs BDNB':30s} | {'match':10s} | KV")
    print("  " + "-" * 150)
    for r in rows:
        if r.get("absent"):
            print(f"  {r['cle']:38s} | (ABSENTE)")
            continue
        bg9 = ("..." + r['bgid'][-9:]) if r['bgid'] else "-"
        immat = r['immat'] or "-"
        parcs = ",".join(r['parcs_bg']) or "-"
        print(f"  {r['cle']:38s} | {'YES' if r['in_co'] else 'no':>5s} | "
              f"{bg9:14s} | {immat:10s} | {r['bdnb']:>4d} | {r['vlog']:>4d} | "
              f"{parcs:30s} | {(r.get('bdnb_match') or '-'):10s} | {r['kv'] or '(non-q)'}")
        if r.get("nom_copro"):
            print(f"     -> RNC declaree : '{r['nom_copro'][:50]}'  lots_tot={r['lots_tot']}  "
                  f"hab={r['lots_hab']}  syndic='{r['syndic'][:30]}'")
        if r.get("sci"):
            print(f"     -> SCI proprio : {r['sci_n']}")
        if r.get("fauto"):
            print(f"     -> _fusion_auto : True (tgt={r.get('fauto_tgt')})")

    # Diag bgids
    bgids = sorted({r['bgid'] for r in rows if not r.get("absent") and r['bgid']})
    print()
    print(f"  bgids distincts : {len(bgids)}  ({', '.join('...' + b[-9:] for b in bgids) or '-'})")
    # Diag parcelles
    parcs_all = set()
    for r in rows:
        if not r.get("absent"):
            for p in r['parcs_bg']: parcs_all.add(p)
    print(f"  parcelles BDNB unique : {len(parcs_all)}  ({', '.join(sorted(parcs_all)) or '-'})")

    # RNC live hits aggregates
    seen_im = set()
    cands_all = []
    for r in rows:
        if r.get("absent"): continue
        for pr in r['parcs_rnc']:
            for h in (cache_rnc.get(pr) or []):
                if h["immat"] in seen_im: continue
                seen_im.add(h["immat"])
                h2 = dict(h); h2["in_secteur"] = h["immat"] in immat_secteur; h2["parc"] = pr
                cands_all.append(h2)
    print(f"  RNC live cands sur parcelles : {len(cands_all)}")
    for h in cands_all:
        tag = " [DEJA-SECTEUR]" if h["in_secteur"] else " >>> NOUVEAU"
        lt = h.get("lots_tot", h.get("nb_lots_total"))
        lh = h.get("lots_hab", h.get("nb_lots_habit"))
        di = h.get("date_immat") or "?"
        col = h.get("ref_col", h.get("ref_match_col", "?"))
        print(f"    {tag}  {h['immat']}  '{(h['nom'] or '')[:38]}'  "
              f"lots_tot={lt} hab={lh}  immat={di}  parc={h['parc']}  col={col[-1] if col else '?'}")

    # Mecanisme propose
    print()
    print("  MECANISME PROPOSE :")
    # Adresses ancres (in_co)
    ancres   = [r for r in rows if not r.get("absent") and r["in_co"]]
    ancres_im = [r for r in rows if not r.get("absent") and r["immat"]]
    horsrnc  = [r for r in rows if not r.get("absent") and not r["in_co"] and not r["immat"]]
    absents  = [r for r in rows if r.get("absent")]
    fautos   = [r for r in rows if not r.get("absent") and r.get("fauto")]
    n_bg     = len(bgids)
    n_parc   = len(parcs_all)
    new_cand = [h for h in cands_all if not h["in_secteur"]]
    deja     = [h for h in cands_all if h["in_secteur"]]

    if ancres_im:
        anc = ancres_im[0]
        print(f"    >> ANCRE RNC : {anc['cle']}  immat={anc['immat']}  "
              f"({anc['lots_tot']}/{anc['lots_hab']})  bgid=...{anc['bgid'][-9:]}")
        for r in horsrnc:
            same_bg   = (r["bgid"] == anc["bgid"])
            same_parc = bool(set(r["parcs_bg"]) & set(anc["parcs_bg"]))
            if same_bg:
                mech = "RE-FUSE simple (meme bgid)"
            elif same_parc:
                mech = "RE-FUSE Cambronne multi-bgid (parcelle commune)"
            elif r["parcs_bg"] and anc["parcs_bg"]:
                mech = "RE-FUSE Fondary (parcelles distinctes meme ensemble - VERIF TERRAIN)"
            else:
                mech = "LABEL/INJECT (parcelles incompletes)"
            print(f"       {r['cle']:38s} -> {mech}  "
                  f"(bdnb={r['bdnb']}, vlog={r['vlog']}, dedup estime ~-{r['bdnb']} log)")
        for r in absents:
            print(f"       {r['cle']:38s} -> INJECT label-only (absente du snapshot)")
    elif new_cand:
        c = new_cand[0]
        print(f"    >> ANCRE RNC NOUVELLE (live) : {c['immat']}  '{c['nom'][:34]}'  "
              f"parc={c['parc']}")
        print(f"       -> INJECT copro + attribuer a l'adresse pivote (lots_tot={c.get('lots_tot')}/"
              f"hab={c.get('lots_hab')})")
        for r in rows:
            if r.get("absent"): continue
            if r["in_co"]:    continue
            print(f"       {r['cle']:38s} -> RE-FUSE/LABEL apres INJECT (bdnb={r['bdnb']})")
    else:
        # Pas d'immat snapshot, pas de RNC live -> ETIQUETAGE pur (pattern Clouet/Garibaldi)
        print(f"    >> Aucune copro RNC (ni snapshot ni live)  -> pattern ETIQUETAGE")
        if not horsrnc:
            pass
        else:
            print(f"       Choisir une ancre interne (pivot = la plus 'haute' bdnb) :")
            horsrnc.sort(key=lambda r: -r["bdnb"])
            pivot = horsrnc[0]
            print(f"         pivot pressenti : {pivot['cle']} (bdnb={pivot['bdnb']}, "
                  f"bgid=...{pivot['bgid'][-9:] if pivot['bgid'] else '-'})")
            for r in horsrnc[1:]:
                same_bg = (r["bgid"] == pivot["bgid"])
                same_parc = bool(set(r["parcs_bg"]) & set(pivot["parcs_bg"]))
                if same_bg:
                    mech = "RE-FUSE simple (meme bgid)  + label etendu"
                elif same_parc:
                    mech = "RE-FUSE Cambronne (parcelle commune) + label etendu"
                else:
                    mech = "LABEL pur (sans dedup) - parcelles distinctes, garder bdnb separes"
                print(f"         {r['cle']:38s} -> {mech} "
                      f"(dedup estime ~-{r['bdnb'] if (same_bg or same_parc) else 0} log)")
            for r in absents:
                print(f"         {r['cle']:38s} -> INJECT label-only (absente snapshot)")

    # Delta parc estime brut
    print()
    rnc_lots = 0
    if ancres_im:
        rnc_lots = ancres_im[0].get("lots_hab") or ancres_im[0].get("lots_tot") or 0
    elif new_cand:
        rnc_lots = new_cand[0].get("lots_hab") or new_cand[0].get("lots_tot") or 0
    bdnb_hr = sum(r["bdnb"] for r in horsrnc)
    bdnb_anc = sum(r["bdnb"] for r in ancres)
    if ancres_im or new_cand:
        print(f"  DELTA PARC estime : RNC={rnc_lots}  bdnb_ancre={bdnb_anc}  bdnb_hr={bdnb_hr}  "
              f"-> ~{(rnc_lots or bdnb_anc) - bdnb_anc - bdnb_hr:+d} log "
              f"(switch BDNB->RNC, hr fuses)")
    else:
        # pattern etiquetage : pivot interne, dedup uniquement si same_bg/same_parc
        # cf logique ci-dessus
        print(f"  DELTA PARC estime : ETIQUETAGE (calcul fin = somme des '-bdnb' des RE-FUSE seuls)")

    print()


# ---------- 6. Resume global ----------
print("=" * 110)
print("RESUME GLOBAL 5 ENSEMBLES")
print("=" * 110)
for ens in ENSEMBLES:
    rows = [addr_dump(c) for c in ens["cles"]]
    n_in_co = sum(1 for r in rows if not r.get("absent") and r["in_co"])
    n_hr    = sum(1 for r in rows if not r.get("absent") and not r["in_co"])
    n_ab    = sum(1 for r in rows if r.get("absent"))
    bgs     = sorted({r['bgid'] for r in rows if not r.get("absent") and r['bgid']})
    parcs   = sorted({p for r in rows if not r.get("absent") for p in r['parcs_bg']})
    immats  = [r['immat'] for r in rows if not r.get("absent") and r['immat']]
    print(f"  #{ens['id']}  cles={len(ens['cles'])} (in_co={n_in_co} hr={n_hr} ab={n_ab})  "
          f"bgids={len(bgs)}  parcs={len(parcs)}  immats_snapshot={len(immats)}")
