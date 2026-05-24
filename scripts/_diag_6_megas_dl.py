#!/usr/bin/env python3
"""Dry-run lecture seule : 6 mega-ensembles DL terrain user
(post-audit_eclatements_dl). Calcule etat actuel + mecanisme + delta parc.

E1 ALBERT THOMAS   (5/5B/7/7B/9)
E2 ANTOINE CHARIAL (27/29 AUBIGNY + 28/30 RICHERAND + 7/9/11/13/15/17 TERNOIS)
E3 LA VICTORIENNE  (4/6/8 PIONCHON + 15/17 ST VICTORIEN + 12/14/16/18/20 ST SIDOINE)
E4 LE BARABAN 1    (61/63/65/67/69 BARABAN + 10/12/14 LOUIS JASSERON)
E5 JEAN SORNAY     (76/78/78B/80/80B/82/84 CHARIAL + 277/279 PAUL BERT)
E6 LAFAYETTE BARABAN (30/32/34/36/38/40 BARABAN)
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"

ENSEMBLES = [
    {"id": "E1", "label": "ALBERT THOMAS (5/5B/7/7B/9)",
     "cles": ["5|COURS|ALBERT THOMAS", "5B|COURS|ALBERT THOMAS",
              "7|COURS|ALBERT THOMAS", "7B|COURS|ALBERT THOMAS",
              "9|COURS|ALBERT THOMAS"]},
    {"id": "E2", "label": "ANTOINE CHARIAL (AUBIGNY 27/29 + RICHERAND 28/30 + TERNOIS 7/9/11/13/15/17)",
     "cles": ["27|RUE|AUBIGNY", "29|RUE|AUBIGNY",
              "28|RUE|ETIENNE RICHERAND", "30|RUE|ETIENNE RICHERAND",
              "7|RUE|TERNOIS", "9|RUE|TERNOIS", "11|RUE|TERNOIS",
              "13|RUE|TERNOIS", "15|RUE|TERNOIS", "17|RUE|TERNOIS"]},
    {"id": "E3", "label": "LA VICTORIENNE (PIONCHON 4/6/8 + ST VICTORIEN 15/17 + ST SIDOINE 12-20)",
     "cles": ["4|RUE|CLAUDIUS PIONCHON", "6|RUE|CLAUDIUS PIONCHON",
              "8|RUE|CLAUDIUS PIONCHON",
              "15|RUE|ST VICTORIEN", "17|RUE|ST VICTORIEN",
              "12|RUE|ST SIDOINE", "14|RUE|ST SIDOINE",
              "16|RUE|ST SIDOINE", "18|RUE|ST SIDOINE",
              "20|RUE|ST SIDOINE"]},
    {"id": "E4", "label": "LE BARABAN 1 (BARABAN 61/63/65/67/69 + LOUIS JASSERON 10/12/14)",
     "cles": ["61|RUE|BARABAN", "63|RUE|BARABAN", "65|RUE|BARABAN",
              "67|RUE|BARABAN", "69|RUE|BARABAN",
              "10|RUE|LOUIS JASSERON", "12|RUE|LOUIS JASSERON",
              "14|RUE|LOUIS JASSERON"]},
    {"id": "E5", "label": "JEAN SORNAY (CHARIAL 76/78/78B/80/80B/82/84 + PAUL BERT 277/279)",
     "cles": ["76|RUE|ANTOINE CHARIAL", "78|RUE|ANTOINE CHARIAL",
              "78B|RUE|ANTOINE CHARIAL", "80|RUE|ANTOINE CHARIAL",
              "80B|RUE|ANTOINE CHARIAL", "82|RUE|ANTOINE CHARIAL",
              "84|RUE|ANTOINE CHARIAL",
              "277|RUE|PAUL BERT", "279|RUE|PAUL BERT"]},
    {"id": "E6", "label": "LAFAYETTE BARABAN (30/32/34/36/38/40 BARABAN)",
     "cles": ["30|RUE|BARABAN", "32|RUE|BARABAN", "34|RUE|BARABAN",
              "36|RUE|BARABAN", "38|RUE|BARABAN", "40|RUE|BARABAN"]},
]


def to_int(x):
    try: return int(x)
    except Exception: return 0


doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad_by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]
               if c.get("numero_immatriculation")}
print(f"[light]  {len(ad_by_cle)} adresses  {len(co_by_cle)} coproprietes")

kv = json.loads(KV.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
def kv_t(c):
    if c in assigns: return (assigns[c] or {}).get("type")
    if c in fusions: return f"fusion->{fusions[c]}"
    return None


# bgid -> [cles light]
bg_to_cles = {}
for a in doc["adresses"]:
    bg = a.get("batiment_groupe_id")
    if bg:
        bg_to_cles.setdefault(bg, []).append(a.get("cle") or "")


# ---------- RNC live lookup (par immat direct, cache simple) ----------
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
_rnc_cache = {}
def rnc_live(im):
    if im in _rnc_cache: return _rnc_cache[im]
    url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": im})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept":"application/json"}), timeout=30) as r:
            d = json.loads(r.read()).get("data", [])
        r = d[0] if d else {}
    except Exception as e:
        r = {"err": str(e)}
    _rnc_cache[im] = r
    time.sleep(0.1)
    return r


# ---------- Analyse par ensemble ----------
def safe_str(x, n=30):
    return (str(x)[:n]) if x is not None else ""


for ens in ENSEMBLES:
    print()
    print("=" * 112)
    print(f"  {ens['id']}  {ens['label']}")
    print("=" * 112)

    rows = []
    bgids_set = set()
    for c in ens["cles"]:
        a  = ad_by_cle.get(c)
        co = co_by_cle.get(c)
        if not a:
            rows.append({"cle": c, "absent": True}); continue
        bg = a.get("batiment_groupe_id") or ""
        if bg: bgids_set.add(bg)
        rows.append({
            "cle": c, "absent": False,
            "in_co": bool(co), "bgid": bg,
            "immat": a.get("numero_immatriculation") or "",
            "bdnb":  to_int(a.get("nb_log_bdnb")),
            "vlog":  to_int(a.get("nb_ventes_logement")),
            "match": a.get("_bdnb_match"),
            "fauto": a.get("_fusion_auto"),
            "fcible": a.get("_fusion_cible"),
            "kv":    kv_t(c),
            "co_nom": (co or {}).get("nom_copropriete"),
            "co_lt":  (co or {}).get("nb_lots_total"),
            "co_lh":  (co or {}).get("nb_lots_habitation"),
        })

    # Tableau detaille
    print(f"  {'cle':36s} | {'in_co':>5s} | {'bgid':14s} | {'immat':10s} | {'bdnb':>4s} | {'vlog':>4s} | {'match':22s} | {'fauto':>5s} | {'fcible':>22s} | KV")
    print("  " + "-" * 175)
    for r in rows:
        if r.get("absent"):
            print(f"  {r['cle']:36s} | (ABSENTE light)")
            continue
        bg9 = "..." + r["bgid"][-9:] if r["bgid"] else "-"
        im  = r["immat"] or "-"
        match = (r["match"] or "-")[:22]
        fc    = (r["fcible"] or "-")[:22]
        kvs   = r["kv"] or "(non-q)"
        print(f"  {r['cle']:36s} | {'YES' if r['in_co'] else 'no':>5s} | {bg9:14s} | "
              f"{im:10s} | {r['bdnb']:>4d} | {r['vlog']:>4d} | {match:22s} | {str(r['fauto']):>5s} | {fc:>22s} | {kvs}")
        if r["co_nom"]:
            print(f"     copro: '{safe_str(r['co_nom'],40)}'  lots_tot={r['co_lt']}  hab={r['co_lh']}")

    # Ancre = adresse avec immat. Si plusieurs, on prend celle avec le plus de bdnb.
    ancres = [r for r in rows if (not r.get("absent")) and r.get("immat")]
    ancres.sort(key=lambda r: -r["bdnb"])
    print()
    if not ancres:
        print("  [WARN] AUCUNE adresse ancre (immat) dans cet ensemble - INJECT pourrait etre requis")
    else:
        print(f"  ANCRES detectees ({len(ancres)}) :")
        for a in ancres:
            print(f"    {a['cle']:36s}  immat={a['immat']}  bgid=...{a['bgid'][-9:]}  "
                  f"bdnb={a['bdnb']}  copro_lots={a.get('co_lt')}/{a.get('co_lh')}")

    # RNC live pour les ancres
    print()
    for a in ancres:
        live = rnc_live(a["immat"])
        if live.get("err"):
            print(f"  RNC live {a['immat']}: ERR {live['err']}")
            continue
        nom = live.get("nom_usage_copropriete") or "-"
        lt  = live.get("nombre_total_lots")
        lh  = live.get("nombre_lots_usage_habitation")
        sy  = live.get("nom_personne_morale") or ""
        di  = live.get("date_premiere_immatriculation") or ""
        ar  = live.get("adresse_reference") or ""
        ac1 = live.get("adresse_complementaire_1") or ""
        ac2 = live.get("adresse_complementaire_2") or ""
        print(f"  RNC live {a['immat']}  nom='{nom[:36]}'  lots_tot={lt}  hab={lh}  syndic='{sy[:24]}'  date={di}")
        print(f"     adr_ref      : {ar}")
        if ac1: print(f"     adr_compl_1  : {ac1}")
        if ac2: print(f"     adr_compl_2  : {ac2}")

    # Distribution bgids actuels + classification mecanisme
    bgids_present = sorted({r["bgid"] for r in rows if (not r.get("absent")) and r["bgid"]})
    print()
    print(f"  BGIDS actuels distincts dans l'ensemble : {len(bgids_present)}")
    for bg in bgids_present:
        cles_dans_bg = [r["cle"] for r in rows if not r.get("absent") and r["bgid"] == bg]
        # adresses light AUTRES qui sont sur ce bgid (hors ensemble)
        autres = [c for c in bg_to_cles.get(bg, []) if c not in cles_dans_bg]
        bdnb_bg = max([r["bdnb"] for r in rows if not r.get("absent") and r["bgid"] == bg], default=0)
        print(f"    ...{bg[-9:]}  bdnb={bdnb_bg:>4d}  cles ds ens: {cles_dans_bg}  cles_hors_ens={len(autres)}")

    # Mecanisme propose
    print()
    print("  MECANISME PROPOSE :")
    if not ancres:
        print("    [SKIP] Pas d'ancre RNC - investigation supplementaire requise.")
        continue
    pivot = ancres[0]
    pivot_bgid = pivot["bgid"]
    print(f"    Pivot ANCRE : {pivot['cle']}  bgid=...{pivot_bgid[-9:]}  immat={pivot['immat']}")

    # Pour chaque autre adresse de l'ensemble : RE-FUSE si bgid != pivot, sinon deja-ok
    re_fuse_count = 0
    same_bg_count = 0
    inject_count  = 0
    other_immat   = 0
    for r in rows:
        if r.get("absent"):
            inject_count += 1
            print(f"    INJECT     {r['cle']:36s}  (label-only)")
            continue
        if r is pivot:
            print(f"    PIVOT      {r['cle']:36s}  (ancre)")
            continue
        if r.get("immat") and r["immat"] != pivot["immat"]:
            other_immat += 1
            print(f"    [WARN-2nd-ancre] {r['cle']:36s}  immat={r['immat']} != pivot {pivot['immat']} -- 2 SDC distincts ?")
            continue
        if r["bgid"] == pivot_bgid:
            same_bg_count += 1
            already = r.get("fauto")
            print(f"    SAME-BG    {r['cle']:36s}  (deja meme bgid, "
                  f"{'fauto=True' if already else 'a fauto si non deja'})")
        else:
            re_fuse_count += 1
            print(f"    RE-FUSE    {r['cle']:36s}  bgid ...{r['bgid'][-9:]} -> ...{pivot_bgid[-9:]}  "
                  f"(bdnb={r['bdnb']}, vlog={r['vlog']})")
    print(f"    >> Total : pivot=1, RE-FUSE={re_fuse_count}, SAME-BG={same_bg_count}, "
          f"INJECT={inject_count}, autre-immat={other_immat}")

    # Calcul delta parc
    # 1) Switch BDNB->RNC sur pivot : (RNC_lots - max(BDNB sur pivot bgid, 0))
    live = rnc_live(pivot["immat"])
    rnc_lots_tot = to_int(live.get("nombre_total_lots")) if not live.get("err") else 0
    rnc_lots_hab = to_int(live.get("nombre_lots_usage_habitation")) if not live.get("err") else 0
    rnc_pour_ui = rnc_lots_hab if rnc_lots_hab else rnc_lots_tot
    bdnb_pivot_bg = max([to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in bg_to_cles.get(pivot_bgid, [])
                         if c in ad_by_cle], default=0)
    snap_co = co_by_immat.get(pivot["immat"])
    snap_lt = to_int((snap_co or {}).get("nb_lots_total"))
    snap_lh = to_int((snap_co or {}).get("nb_lots_habitation"))
    snap_pour_ui = snap_lh if snap_lh else snap_lt
    # UI prend max RNC/BDNB par bgid. Effectif actuel = max(snap_pour_ui, bdnb_pivot_bg)
    cur_eff = max(snap_pour_ui, bdnb_pivot_bg)
    # Apres fix : possible patch copro avec rnc_pour_ui. Final eff = max(rnc_pour_ui, snap_pour_ui, bdnb_pivot_bg)
    final_eff = max(rnc_pour_ui, snap_pour_ui, bdnb_pivot_bg)
    delta_switch = final_eff - cur_eff

    # 2) Dedup bgids absorbes : pour chaque autre bgid de l'ensemble, si TOUTES ses adresses light vont vers le pivot, on dedup son bdnb
    delta_dedup = 0
    for bg in bgids_present:
        if bg == pivot_bgid: continue
        cles_dans_bg_ens = [r["cle"] for r in rows if not r.get("absent") and r["bgid"] == bg]
        autres = [c for c in bg_to_cles.get(bg, []) if c not in cles_dans_bg_ens]
        bdnb_bg = max([to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in bg_to_cles.get(bg, [])
                       if c in ad_by_cle], default=0)
        # Si autres adresses light restent sur ce bgid -> dedup 0 (bgid garde occupants)
        if autres:
            continue
        delta_dedup -= bdnb_bg

    print(f"    DELTA PARC : switch BDNB({bdnb_pivot_bg}) -> RNC({rnc_pour_ui}) = +{delta_switch}  "
          f"+ dedup bgids = {delta_dedup}  => TOTAL {delta_switch + delta_dedup:+d} log")
    print(f"      (snapshot copro pivot AC {pivot['immat']}: lots_tot={snap_lt} lots_hab={snap_lh})")


# ---------- Resume global ----------
print()
print("=" * 112)
print("RESUME 6 ENSEMBLES")
print("=" * 112)
print(f"  {'ID':>3s} | {'label':70s} | cles | in_co | hr | ab | ancres | bgids")
print("  " + "-" * 110)
for ens in ENSEMBLES:
    rows = []
    for c in ens["cles"]:
        a  = ad_by_cle.get(c)
        co = co_by_cle.get(c)
        if not a: rows.append({"absent": True}); continue
        rows.append({"absent": False, "in_co": bool(co),
                     "immat": a.get("numero_immatriculation") or "",
                     "bgid": a.get("batiment_groupe_id") or ""})
    n_in_co = sum(1 for r in rows if (not r.get("absent")) and r.get("in_co"))
    n_hr    = sum(1 for r in rows if (not r.get("absent")) and not r.get("in_co"))
    n_ab    = sum(1 for r in rows if r.get("absent"))
    n_anc   = sum(1 for r in rows if (not r.get("absent")) and r.get("immat"))
    bgs     = sorted({r['bgid'] for r in rows if (not r.get("absent")) and r['bgid']})
    label_short = ens['label'][:70]
    print(f"  {ens['id']:>3s} | {label_short:70s} | {len(ens['cles']):>4d} | {n_in_co:>5d} | {n_hr:>2d} | {n_ab:>2d} | {n_anc:>6d} | {len(bgs):>5d}")
