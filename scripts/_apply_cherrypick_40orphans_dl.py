#!/usr/bin/env python3
"""Cherry-pick 40 orphans BDNB + scan DVF + analyse RE-FUSE/INJECT (lecture + ecriture).

ETAPE 1 : Backup current + cherry-pick 40 nouvelles cles depuis sandbox v3
ETAPE 2 : Scan DVF par adresse exacte pour chaque orphan
ETAPE 3 : Detection RE-FUSE bgid + INJECT/ATTRIB RNC (via parcelle BDNB live)
"""
import json, re, sys, shutil, urllib.parse, urllib.request, time
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
V3 = ROOT / "data" / "secteur_dl_light_v3.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
BAK = LIGHT.with_suffix(LIGHT.suffix + ".preorphan40.bak")

RID_RNC = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID_RNC}/data/"
UA = "Mozilla/5.0 diag/1.0"

# Normalisation voie (cf scripts precedents)
TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","BD":"BOULEVARD","PL":"PLACE",
          "PAS":"PASSAGE","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI",
          "AVENUE":"AVENUE","COURS":"COURS","PASSAGE":"PASSAGE","PLACE":"PLACE",
          "IMPASSE":"IMPASSE","BOULEVARD":"BOULEVARD","ROUTE":"ROUTE"}
ARTICLES = re.compile(r"^(?:DU|DE|DES|LA|LE|L'|D')\s+")
def norm_voie(s):
    if not s: return ""
    s = str(s).upper().strip()
    s = (s.replace("É","E").replace("È","E").replace("Ê","E")
           .replace("À","A").replace("Â","A").replace("Î","I").replace("Ô","O")
           .replace("Û","U").replace("Ç","C"))
    s = re.sub(r"\bSAINTE\b","STE", s); s = re.sub(r"\bSAINT\b","ST", s)
    s = s.replace("-"," ").replace("'"," ")
    s = re.sub(r"\s+"," ", s).strip()
    while True:
        new = ARTICLES.sub("", s)
        if new == s: break
        s = new
    return s
def parse_cle(cle):
    m = re.match(r"^(\d+)([A-Z]*)\|([A-Z]+)\|(.+)$", cle)
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None
def fnum(v):
    if v is None: return None
    s = str(v).strip().replace(" ","").replace(",",".")
    try: return float(s)
    except: return None
def fail(msg):
    print(); print("!"*90); print(f"!  ECHEC : {msg}"); print("!"*90); sys.exit(10)

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)[:120]}

PARC_CACHE = {}
def bdnb_parc(bg):
    if bg in PARC_CACHE: return PARC_CACHE[bg]
    url = f"https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}"
    d = http_get(url)
    parcs = [x.get("parcelle_id") for x in (d if isinstance(d, list) else [])
             if x.get("parcelle_id")]
    PARC_CACHE[bg] = parcs
    time.sleep(0.05)
    return parcs

def bdnb_to_rnc(p):
    if len(p)>=8 and p[:2]=="69" and p[5:8]=="000":
        return "69123383"+p[8:]
    return p

RNC_CACHE = {}
def scan_rnc_parc(rnc_p):
    if rnc_p in RNC_CACHE: return RNC_CACHE[rnc_p]
    seen = {}
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        d = http_get(url, timeout=20)
        rows = (d or {}).get("data", []) if isinstance(d, dict) else []
        for row in rows:
            im = row.get("numero_immatriculation")
            if im and im not in seen: seen[im] = row
        time.sleep(0.04)
    res = list(seen.values())
    RNC_CACHE[rnc_p] = res
    return res

# ============================================================
# ETAPE 1 : cherry-pick
# ============================================================
print("=" * 90)
print("ETAPE 1 - Cherry-pick 40 orphans v3 -> current")
print("=" * 90)
doc_cur = json.loads(LIGHT.read_text(encoding="utf-8"))
doc_v3 = json.loads(V3.read_text(encoding="utf-8"))
ad_cur = doc_cur["adresses"]
ad_v3 = doc_v3["adresses"]
co_cur = doc_cur["coproprietes"]
N0 = len(ad_cur)
N_CO = len(co_cur)

cles_cur = {a.get("cle") for a in ad_cur if a.get("cle")}
# Orphans = v3 marqued _injection_bdnb_orphelin
orph_in_v3 = [a for a in ad_v3 if a.get("_injection_bdnb_orphelin")]
# Filtre : pas deja dans current (safety)
to_append = [a for a in orph_in_v3 if a.get("cle") not in cles_cur]
print(f"  Current : {N0} adresses, {N_CO} copros")
print(f"  V3      : {len(ad_v3)} adresses, {len(doc_v3['coproprietes'])} copros")
print(f"  Orphans marques v3 : {len(orph_in_v3)}")
print(f"  A appender (non collide current) : {len(to_append)}")

# Backup
shutil.copy2(LIGHT, BAK)
print(f"  Backup : {BAK.name}")

# Append
for a in to_append:
    doc_cur["adresses"].append(a)
print(f"  Apres append : {len(doc_cur['adresses'])} adresses")

# Write
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc_cur, f, ensure_ascii=False, indent=2)
print(f"  Ecriture light.json OK")

# Verif
doc_check = json.loads(LIGHT.read_text(encoding="utf-8"))
if len(doc_check["adresses"]) != N0 + len(to_append):
    fail(f"count post-write : {len(doc_check['adresses'])} != {N0}+{len(to_append)}")
if len(doc_check["coproprietes"]) != N_CO:
    fail(f"copros modifiees : {N_CO} -> {len(doc_check['coproprietes'])}")
n_orph_check = sum(1 for a in doc_check["adresses"]
                   if a.get("_injection_bdnb_orphelin") == "fix_bdnb_orphelin_dl_2026-05-23")
print(f"  Verif : {n_orph_check} cles avec marker orphan (attendu >= {len(to_append)})")
print(f"  >>> ETAPE 1 OK : light {N0} -> {len(doc_check['adresses'])} (+{len(to_append)})")

# Mise a jour by_cle pour etape 3
by_cle_cur = {a.get("cle"): a for a in doc_cur["adresses"]}
ancre_bgids_native = defaultdict(list)  # bgid -> [cle, ...] des ancres natives (non orphan/inject)
for a in doc_cur["adresses"]:
    if a.get("_injection_bdnb_orphelin"): continue  # exclure les nouveaux orphans
    if a.get("_injection_indice"): continue         # exclure les cherrypicked suffixes
    bg = a.get("batiment_groupe_id")
    if bg: ancre_bgids_native[bg].append(a.get("cle"))

co_by_immat = {c.get("numero_immatriculation"): c for c in co_cur if c.get("numero_immatriculation")}

# ============================================================
# ETAPE 2 : scan DVF
# ============================================================
print()
print("=" * 90)
print("ETAPE 2 - Scan DVF sur 40 orphans (lecture seule)")
print("=" * 90)
dvf = json.loads(DVF.read_text(encoding="utf-8"))
dvf_idx = defaultdict(list)
for m in dvf:
    no = str(m.get("No voie","") or "").strip().lstrip("0")
    bt = str(m.get("B/T/Q","") or "").strip().upper()
    tv = TV_MAP.get(str(m.get("Type de voie","") or "").strip().upper(), "")
    vo = norm_voie(m.get("Voie"))
    if not (no and tv and vo): continue
    dvf_idx[(no, bt, tv, vo)].append(m)
print(f"  DVF indexes : {len(dvf_idx)} adresses uniques")

dvf_results = []
for a in to_append:
    cle = a.get("cle")
    p = parse_cle(cle)
    if not p: continue
    num, suffix, tv, voie = p
    voie_n = norm_voie(voie)
    muts = dvf_idx.get((num, suffix, tv, voie_n), [])
    ventes_log = [m for m in muts
                  if (m.get("Nature mutation","") or "").strip() == "Vente"
                  and (m.get("Type local","") or "").strip() in ("Appartement","Maison")]
    by_mut = defaultdict(list)
    for m in ventes_log:
        by_mut[(m.get("Date mutation"), m.get("No disposition"), m.get("Valeur fonciere"))].append(m)
    if by_mut:
        dvf_results.append({"cle": cle, "bdnb": a.get("nb_log_bdnb"),
                            "bgid": a.get("batiment_groupe_id"),
                            "nb_ventes": len(by_mut), "by_mut": by_mut})

dvf_results.sort(key=lambda r: -r["nb_ventes"])
print()
print(f"  {len(dvf_results)} orphans avec >= 1 vente logement / {len(to_append)} total")
print(f"  Total ventes : {sum(r['nb_ventes'] for r in dvf_results)}")
print()
for r in dvf_results:
    print(f"  {r['cle']:36s}  ventes={r['nb_ventes']:>2d}  bdnb={r['bdnb']}  bgid=...{(r['bgid'] or '-')[-9:]}")
    for k in sorted(r["by_mut"].keys())[-3:]:
        date, dispo, val = k
        v = fnum(val)
        lst = r["by_mut"][k]
        s = sum(int(m.get("Surface reelle bati","0") or 0) for m in lst)
        pieces = sum(int(m.get("Nombre pieces principales","0") or 0) for m in lst)
        v_str = f"{v:>10,.0f}".replace(",", " ") if v else "         ?"
        print(f"      {date}  val={v_str} EUR  surf={s}m2 pieces={pieces}  n_lots={len(lst)}")
    # Suggestion qualif KV
    n = r["nb_ventes"]
    if n >= 5: sugg = "copro_non_immat (actif)"
    elif n >= 2: sugg = "copro_non_immat"
    else: sugg = "copro_non_immat (1 vente)"
    print(f"      >>> KV suggestion : {sugg}")

# ============================================================
# ETAPE 3 : RE-FUSE bgid + RNC parcelle
# ============================================================
print()
print("=" * 90)
print("ETAPE 3 - Detection RE-FUSE bgid + RNC INJECT/ATTRIB (live BDNB+RNC)")
print("=" * 90)
print()

# Sous-set d'analyse RNC : top 20 par bdnb (eviter trop d'API calls)
top_for_rnc = sorted(to_append, key=lambda a: -(a.get("nb_log_bdnb") or 0))[:20]
print(f"  Analyse RNC : top 20 orphans par nb_log (eviter saturation API)")
print()

REFUSE_BGID = []  # orphans avec bgid present dans ancre native
RNC_CANDIDATES = []  # orphans avec copro RNC sur la meme parcelle

# RE-FUSE bgid (toutes les 40)
for a in to_append:
    bg = a.get("batiment_groupe_id")
    if not bg: continue
    if bg in ancre_bgids_native:
        REFUSE_BGID.append((a.get("cle"), ancre_bgids_native[bg]))

print(f"  RE-FUSE bgid detectes (orphan bgid = bgid ancre native) : {len(REFUSE_BGID)}")
for cle, ancres in REFUSE_BGID:
    print(f"    {cle:36s} -> ancres natives : {ancres}")
if not REFUSE_BGID:
    print("    (aucun - chaque orphan a un bgid distinct des ancres natives, comme attendu)")

# RNC INJECT/ATTRIB via parcelle (top 20)
print()
print(f"  Scan parcelle BDNB + RNC live (top 20 orphans) ...")
for a in top_for_rnc:
    bg = a.get("batiment_groupe_id")
    cle = a.get("cle")
    bdnb = a.get("nb_log_bdnb")
    parcs = bdnb_parc(bg) if bg else []
    rnc_hits = []
    for p in parcs:
        rnc_p = bdnb_to_rnc(p)
        for h in scan_rnc_parc(rnc_p):
            im = h.get("numero_immatriculation")
            if not im: continue
            sct = "DEJA-SCT" if im in co_by_immat else "HORS-SCT"
            rnc_hits.append((im, h.get("nom_usage_copropriete","")[:40],
                             h.get("nombre_total_lots"),
                             h.get("nombre_lots_usage_habitation") or h.get("nombre_lots_habitation_bureaux_commerces"),
                             sct))
    if rnc_hits:
        RNC_CANDIDATES.append({"cle": cle, "bdnb": bdnb, "bgid": bg,
                                "parcs": parcs, "rnc_hits": rnc_hits})

print()
print(f"  Orphans avec RNC live sur parcelle BDNB : {len(RNC_CANDIDATES)} / {len(top_for_rnc)} testes")
print()
for r in RNC_CANDIDATES:
    print(f"  {r['cle']:36s}  bdnb={r['bdnb']}  parcs={r['parcs']}")
    for im, nom, tot, hab, sct in r["rnc_hits"]:
        print(f"    -> {im} '{nom}'  tot={tot} hab={hab}  [{sct}]")

# --- Bilan ---
print()
print("=" * 90)
print(f"BILAN ETAPES 1-3")
print("=" * 90)
print(f"  ETAPE 1 cherry-pick : light {N0} -> {N0 + len(to_append)} adresses (+{len(to_append)})")
print(f"  ETAPE 2 DVF         : {len(dvf_results)} / {len(to_append)} avec ventes ({sum(r['nb_ventes'] for r in dvf_results)} total)")
print(f"  ETAPE 3 RE-FUSE     : {len(REFUSE_BGID)} (orphan bgid match ancre native)")
print(f"  ETAPE 3 RNC live    : {len(RNC_CANDIDATES)} candidats INJECT/ATTRIB / {len(top_for_rnc)} testes")
print(f"  Backup : {BAK.name}")
print("=" * 90)
