#!/usr/bin/env python3
"""Diag + DVF des 12 mega-ensembles confirmes terrain (E7-E18).
Lecture seule. Aucune modification."""
import json, os, sys, time, unicodedata, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
os.environ.setdefault("PYTHONUTF8", "1")

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
FULL  = ROOT / "data" / "secteur_dauphine_lacassagne.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"

# (id, label, ancre cle, ancre immat, cles ensemble)
ENSEMBLES = [
    {"id":"E7", "label":"LES JARDINS DE BABYLONE",
     "ancre":"27|RUE|STE ANNE DE BARABAN", "immat":"AA1700848",
     "cles":["27|RUE|STE ANNE DE BARABAN","29|RUE|STE ANNE DE BARABAN",
             "31|RUE|STE ANNE DE BARABAN","33|RUE|CLAUDIUS PIONCHON"]},
    {"id":"E8", "label":"177 FELIX FAURE",
     "ancre":"177|AVENUE|FELIX FAURE", "immat":"AB3274529",
     "cles":["177|AVENUE|FELIX FAURE","177B|AVENUE|FELIX FAURE","177T|AVENUE|FELIX FAURE"]},
    {"id":"E9", "label":"LACASSAGNE DAVID",
     "ancre":"9|RUE|DAVID", "immat":"AB3954260",
     "cles":["9|RUE|DAVID","11|RUE|DAVID",
             "2|RUE|METALLURGIE","6|RUE|METALLURGIE","8|RUE|METALLURGIE",
             "10|RUE|METALLURGIE","12|RUE|METALLURGIE"]},
    {"id":"E10","label":"L'HERMITAGE",
     "ancre":"27|RUE|GUILLOUD", "immat":"AB3360401",
     "cles":["25|RUE|GUILLOUD","27|RUE|GUILLOUD","29|RUE|GUILLOUD","31|RUE|GUILLOUD"]},
    {"id":"E11","label":"LE CARRE ST ANTOINE",
     "ancre":"35|RUE|ST ANTOINE", "immat":"AC6493506",
     "cles":["3|RUE|ETIENNE RICHERAND","5|RUE|ETIENNE RICHERAND","35|RUE|ST ANTOINE"]},
    {"id":"E12","label":"HORIZON MONPLAISIR",
     "ancre":"66|AVENUE|LACASSAGNE", "immat":"AE8227266",
     "cles":["7|RUE|BARA","64|AVENUE|LACASSAGNE","64B|AVENUE|LACASSAGNE",
             "66|AVENUE|LACASSAGNE"]},
    {"id":"E13","label":"SAINT MARC I",
     "ancre":"42|RUE|ST MAXIMIN", "immat":"AA2505634",
     "cles":["42|RUE|ST MAXIMIN","44|RUE|ST MAXIMIN","46|RUE|ST MAXIMIN",
             "48|RUE|ST MAXIMIN","50|RUE|ST MAXIMIN"]},
    {"id":"E14","label":"LES VICTORINES",
     "ancre":"14|RUE|ST VICTORIEN", "immat":"AC3805199",
     "cles":["2|RUE|LOUIS JASSERON","14|RUE|ST VICTORIEN"]},
    {"id":"E15","label":"CLOSERIE DES TILLEULS II",
     "ancre":"7|RUE|FRANCOIS GILLET", "immat":"AA4868378",
     "cles":["5|RUE|FRANCOIS GILLET","7|RUE|FRANCOIS GILLET",
             "9|RUE|FRANCOIS GILLET","11|RUE|FRANCOIS GILLET",
             "13|RUE|FRANCOIS GILLET"]},
    {"id":"E16","label":"PAVILLON DU DAUPHIN",
     "ancre":"89|RUE|DAUPHINE", "immat":"AC9350984",
     "cles":["14|RUE|CARRY","89|RUE|DAUPHINE","93|RUE|DAUPHINE"]},
    {"id":"E17","label":"LES JARDINS DU PRESIDENT (extension)",
     "ancre":"57|RUE|ETIENNE RICHERAND", "immat":"AA1888700",
     "cles":["57|RUE|ETIENNE RICHERAND","36|AVENUE|GEORGES POMPIDOU",
             "3|RUE|TEINTURIERS"]},
    {"id":"E18","label":"LES JARDINS DE CHARIAL (mega-11 adresses)",
     "ancre":"22|RUE|ST ANTOINE", "immat":"AA1601434",
     "cles":["14|RUE|ETIENNE RICHERAND","16|RUE|ETIENNE RICHERAND",
             "18|RUE|ETIENNE RICHERAND","20|RUE|ETIENNE RICHERAND",
             "22|RUE|ETIENNE RICHERAND","24|RUE|ETIENNE RICHERAND",
             "22|RUE|ST ANTOINE","24|RUE|ST ANTOINE","26|RUE|ST ANTOINE",
             "28|RUE|ST ANTOINE","30|RUE|ST ANTOINE"]},
]


def to_int(x):
    try: return int(x)
    except: return 0


# ---------- DVF normalisation tokens ----------
PARTICLES={"de","du","la","le","les","des","d'","l'","au","aux"}
SAINT_MAP={"saint":"ST","sainte":"STE","st":"ST","ste":"STE"}
def strip_accents(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")
def voie_tokens(voie):
    out=set()
    for tok in voie.replace("-"," ").split():
        wl=strip_accents(tok).lower().rstrip(".")
        if not wl: continue
        if wl in PARTICLES: continue
        if wl in SAINT_MAP: out.add(SAINT_MAP[wl])
        else: out.add(strip_accents(tok).upper())
    return out
def cle_to_filter(cle):
    num,_t,voie=cle.split("|",2)
    suff=""
    if num and num[-1].isalpha(): suff=num[-1].upper(); num=num[:-1]
    return num,suff,voie_tokens(voie)
def date_iso(d):
    try:
        j,mo,a=d.split("/"); return f"{a}-{mo}-{j}"
    except: return d


# ---------- Load ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]; co = doc["coproprietes"]
ad_by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}
print(f"[light]   {len(ad_by_cle)} adresses  {len(co)} coproprietes")

kv = json.loads(KV.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
def kv_t(c):
    if c in assigns: return (assigns[c] or {}).get("type")
    if c in fusions: return f"fusion->{fusions[c]}"
    return None

# bg -> [cles]
bg_to_cles = defaultdict(list)
for a in ad:
    bg = a.get("batiment_groupe_id")
    if bg: bg_to_cles[bg].append(a.get("cle") or "")

# Mutations DVF
full = json.loads(FULL.read_text(encoding="utf-8"))
mutations = full.get("mutations_dvf") or []
print(f"[DVF]     {len(mutations)} mutations totales DL")

# RNC live cache simple
_rnc={}
RID="3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB=f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
def rnc_live(im):
    if im in _rnc: return _rnc[im]
    url=TAB+"?"+urllib.parse.urlencode({"numero_immatriculation__exact":im})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept":"application/json"}), timeout=30) as r:
            d=json.loads(r.read()).get("data",[])
        r= d[0] if d else {}
    except Exception as e:
        r={"err":str(e)}
    _rnc[im]=r
    time.sleep(0.1)
    return r


# ---------- Analyse par ensemble ----------
total_dvf = 0
total_delta = 0

for ens in ENSEMBLES:
    print()
    print("=" * 112)
    print(f"  {ens['id']}  {ens['label']}  ancre={ens['ancre']}  immat={ens['immat']}")
    print("=" * 112)

    a_anc = ad_by_cle.get(ens["ancre"])
    if not a_anc:
        print(f"  [SKIP] ancre absente"); continue
    bg_anc = a_anc.get("batiment_groupe_id") or ""
    print(f"  ANCRE light : bgid=...{bg_anc[-9:]}  bdnb_anc={a_anc.get('nb_log_bdnb')}  "
          f"immat={a_anc.get('numero_immatriculation')}")

    co_entry = co_by_immat.get(ens["immat"])
    if co_entry:
        print(f"  copro snapshot : nom='{co_entry.get('nom_copropriete')!r}'  "
              f"lots_tot={co_entry.get('nb_lots_total')}  hab={co_entry.get('nb_lots_habitation')}  "
              f"syndic='{(co_entry.get('syndic') or '')[:24]}'")
    rl = rnc_live(ens["immat"])
    if not rl.get("err"):
        print(f"  RNC live     : nom='{rl.get('nom_usage_copropriete')!r}'  "
              f"lots_tot={rl.get('nombre_total_lots')}  hab={rl.get('nombre_lots_usage_habitation')}")
        ar = rl.get("adresse_reference") or ""
        ac1 = rl.get("adresse_complementaire_1") or ""
        ac2 = rl.get("adresse_complementaire_2") or ""
        if ar: print(f"     adr_ref    : {ar}")
        if ac1: print(f"     adr_compl_1: {ac1}")
        if ac2: print(f"     adr_compl_2: {ac2}")

    # Etat de chaque cle
    print()
    print(f"  {'cle':36s} | {'in_co':>5s} | {'bgid':14s} | {'immat':12s} | {'bdnb':>4s} | {'fauto':>5s} | {'fcible':22s} | match")
    print("  " + "-" * 145)

    rows = []
    bg_visites = defaultdict(list)
    for c in ens["cles"]:
        a = ad_by_cle.get(c)
        if not a:
            print(f"  {c:36s} | (ABSENTE light)")
            rows.append({"cle":c,"absent":True}); continue
        bg = a.get("batiment_groupe_id") or ""
        bg9 = "..." + bg[-9:] if bg else "-"
        im = a.get("numero_immatriculation") or "-"
        fc = (a.get("_fusion_cible") or "-")[:22]
        match = (a.get("_bdnb_match") or "-")[:24]
        is_anc = (c == ens["ancre"])
        kvtag = kv_t(c) or "(non-q)"
        print(f"  {c:36s} | {'YES' if c in {x.get('cle_adresse') for x in co} else 'no':>5s} | "
              f"{bg9:14s} | {im:12s} | {to_int(a.get('nb_log_bdnb')):>4d} | "
              f"{str(a.get('_fusion_auto')):>5s} | {fc:22s} | {match}  [{kvtag}]")
        rows.append({"cle":c,"absent":False,"is_anc":is_anc,"bgid":bg,
                     "immat":a.get("numero_immatriculation"),
                     "bdnb":to_int(a.get("nb_log_bdnb")),
                     "fauto":a.get("_fusion_auto"),
                     "fcible":a.get("_fusion_cible"),
                     "match":a.get("_bdnb_match"),
                     "kv":kv_t(c)})
        if not is_anc and bg:
            bg_visites[bg].append(c)

    # Mecanisme par cle
    print()
    print("  MECANISME PROPOSE :")
    re_fuse_n = rebind_n = same_bg_n = warn_n = inject_n = 0
    for r in rows:
        if r.get("absent"):
            print(f"    INJECT     {r['cle']:36s}  (label-only)")
            inject_n += 1; continue
        if r.get("is_anc"):
            print(f"    PIVOT      {r['cle']:36s}  (ancre)")
            continue
        if r["immat"] and r["immat"] != ens["immat"]:
            warn_n += 1
            print(f"    WARN-2nd   {r['cle']:36s}  immat={r['immat']} != pivot {ens['immat']} -- 2 SDC ?")
            continue
        if r["bgid"] == bg_anc:
            same_bg_n += 1
            print(f"    SAME-BG    {r['cle']:36s}  (deja meme bgid, fauto={r['fauto']})")
        elif r.get("fauto"):
            rebind_n += 1
            print(f"    REBIND     {r['cle']:36s}  bgid ...{r['bgid'][-9:]} -> ...{bg_anc[-9:]}  "
                  f"fcible '{r['fcible']}' -> '{ens['ancre']}'")
        else:
            re_fuse_n += 1
            print(f"    RE-FUSE    {r['cle']:36s}  bgid ...{r['bgid'][-9:]} -> ...{bg_anc[-9:]}  "
                  f"cible='{ens['ancre']}'")
    print(f"    >> Total : pivot=1, RE-FUSE={re_fuse_n}, REBIND={rebind_n}, "
          f"SAME-BG={same_bg_n}, INJECT={inject_n}, WARN-2nd={warn_n}")

    # Delta parc
    delta_dedup = 0
    for bg, cles_part in bg_visites.items():
        if bg == bg_anc: continue
        all_cles_bg = bg_to_cles[bg]
        restantes = [c for c in all_cles_bg if c not in cles_part]
        bdnb_bg = max([to_int(ad_by_cle[c].get("nb_log_bdnb")) for c in all_cles_bg
                       if c in ad_by_cle], default=0)
        if not restantes and bdnb_bg:
            delta_dedup -= bdnb_bg
            print(f"    bgid ...{bg[-9:]} : SUPPRIME bdnb={bdnb_bg} -> -{bdnb_bg}")
    snap_lh = to_int((co_entry or {}).get("nb_lots_habitation"))
    rnc_h = to_int(rl.get("nombre_lots_usage_habitation")) if not rl.get("err") else 0
    bdnb_anc = to_int(a_anc.get("nb_log_bdnb"))
    cur_eff = max(snap_lh, bdnb_anc)
    final_eff = max(rnc_h, snap_lh, bdnb_anc)
    delta_switch = final_eff - cur_eff
    delta_total = delta_dedup + delta_switch
    total_delta += delta_total
    print(f"    DELTA : dedup={delta_dedup}  switch=+{delta_switch}  (snap_lh={snap_lh} bdnb_anc={bdnb_anc} rnc_h={rnc_h})  "
          f"=> {delta_total:+d} log")

    # DVF count
    cle_filters = {c: cle_to_filter(c) for c in ens["cles"]}
    nv_set = {f[0] for f in cle_filters.values()}
    n_dvf = 0
    last_date = ""
    by_cle_dvf = defaultdict(int)
    for m in mutations:
        nv=str(m.get("No voie","")).strip()
        if nv not in nv_set: continue
        btq=str(m.get("B/T/Q","")).strip().upper()
        v_toks=voie_tokens(str(m.get("Voie","")).strip())
        for cle,(n,s,vs) in cle_filters.items():
            if nv==n and btq==s and vs==v_toks:
                n_dvf += 1
                by_cle_dvf[cle] += 1
                d = date_iso(m.get("Date mutation",""))
                if d > last_date: last_date = d
                break
    total_dvf += n_dvf
    print(f"    DVF : {n_dvf} mutations total (derniere : {last_date or '-'})")
    if by_cle_dvf:
        top = sorted(by_cle_dvf.items(), key=lambda kv: -kv[1])[:3]
        for c, n in top:
            print(f"       {c:36s} : {n} ventes")


print()
print("=" * 112)
print(f"GRAND TOTAL : delta parc estime = {total_delta:+d} log  |  DVF mutations cumules = {total_dvf}")
print("=" * 112)
