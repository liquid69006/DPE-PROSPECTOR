#!/usr/bin/env python3
"""Scan bgids BDNB orphelins du light DL (lecture seule).

Definition orphelin :
  - bgid dans bdnb_dauphine_lacassagne.json (snapshot local)
  - usage_principal_bdnb_open = 'Residentiel collectif'
  - nb_log >= 3
  - ABSENT du light DL actuel (aucune adresse light ne reference ce bgid)

Pour chaque orphelin : details BDNB + parcelle (BDNB live) + presence MAJIC + DVF.

Affiche top 20 par nb_log decroissant.
"""
import json, re, sys, urllib.request, time
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BDNB = Path(r"C:\Users\Station 5\bdnb_dauphine_lacassagne.json")
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
MAJIC_PARQ = Path(r"C:\Users\Station 5\majic_locaux2_2025.parquet")
MAJIC_FONC = Path(r"C:\Users\Station 5\majic_locaux_2025.parquet")

UA = "Mozilla/5.0 diag/1.0"

# --- Load light : extraire les bgids deja referencer ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
light_bgids = set()
for a in doc["adresses"]:
    bg = a.get("batiment_groupe_id")
    if bg: light_bgids.add(bg)
print(f"Light DL : {len(doc['adresses'])} adresses, {len(light_bgids)} bgids distincts referencees")

# --- Load BDNB snapshot ---
bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
print(f"BDNB snapshot DL : {len(bdnb)} bgids")

# --- Filtre orphelins ---
orph = []
for b in bdnb:
    if b.get("batiment_groupe_id") in light_bgids: continue
    usage = (b.get("usage_principal_bdnb_open") or "").strip()
    nb = b.get("nb_log") or 0
    if usage != "Résidentiel collectif": continue
    if nb < 3: continue
    orph.append(b)
print(f"  Filtres residentiel + nb_log >= 3 + absent light : {len(orph)} orphelins")
orph.sort(key=lambda b: -(b.get("nb_log") or 0))

# --- BDNB live : parcelles par bgid (top 20 + cache) ---
print()
print(f"Recuperation parcelles BDNB live pour top {min(len(orph),20)} orphelins ...")
PARC_CACHE = {}
def bdnb_parc(bg):
    if bg in PARC_CACHE: return PARC_CACHE[bg]
    url = f"https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.{bg}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            rs = json.loads(r.read())
        parcs = [x.get("parcelle_id") for x in rs if x.get("parcelle_id")]
    except Exception as e:
        parcs = []
    PARC_CACHE[bg] = parcs
    time.sleep(0.06)
    return parcs

top20 = orph[:20]
for b in top20:
    b["_parcs"] = bdnb_parc(b["batiment_groupe_id"])

# --- MAJIC locaux1 + locaux2 : verif presence par parcelle ---
import pyarrow.parquet as pq
print("Chargement MAJIC locaux1 (foncier) + locaux2 (lots) commune 69383 ...")
tbl_f = pq.read_table(str(MAJIC_FONC), filters=[("departement","=","69"),("code_commune","=","383")])
df_f = tbl_f.to_pandas()
tbl_l = pq.read_table(str(MAJIC_PARQ), filters=[("departement","=","69"),("code_commune","=","383")])
df_l = tbl_l.to_pandas()
print(f"  MAJIC fonc : {len(df_f)} entrees ({df_f[['section','numero_parcelle']].drop_duplicates().shape[0]} parcelles)")
print(f"  MAJIC lots : {len(df_l)} entrees ({df_l[['section','numero_parcelle']].drop_duplicates().shape[0]} parcelles)")

def parc_in_majic(parc_id, df):
    """parc_id = '69383000DS0100' -> match section DS + numero 100."""
    if not parc_id or len(parc_id) < 14: return 0
    sec = parc_id[8:10]
    try: num = int(parc_id[10:])
    except: return 0
    m = df[(df['section']==sec) & (df['numero_parcelle']==num)]
    return len(m)

# --- DVF : verif presence par libelle BAN ---
print("Chargement DVF DL pour verif ventes par adresse...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))

TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","BD":"BOULEVARD","PL":"PLACE",
          "PAS":"PASSAGE","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI"}
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

# Index DVF par (num, suffix, tv_norm, voie_norm)
dvf_idx = defaultdict(int)
for m in dvf:
    no = str(m.get("No voie","") or "").strip().lstrip("0")
    bt = str(m.get("B/T/Q","") or "").strip().upper()
    tv = TV_MAP.get(str(m.get("Type de voie","") or "").strip().upper(), "")
    vo = norm_voie(m.get("Voie"))
    if not (no and tv and vo): continue
    nat = (m.get("Nature mutation","") or "").strip()
    tl  = (m.get("Type local","") or "").strip()
    if nat == "Vente" and tl in ("Appartement","Maison"):
        dvf_idx[(no, bt, tv, vo)] += 1

def parse_ban_label(label):
    """'237 Rue Paul Bert 69003 Lyon 3e Arrondissement' -> (237, '', RUE, 'PAUL BERT')."""
    if not label: return None
    m = re.match(r"^(\d+)([A-Za-z]?)\s+(\S+)\s+(.+?)\s+\d{5}\s", label.strip())
    if not m: return None
    num = m.group(1)
    suffix = (m.group(2) or "").upper()
    tv = TV_MAP.get(m.group(3).upper(), m.group(3).upper())
    voie = norm_voie(m.group(4))
    return num, suffix, tv, voie

# --- Display ---
print()
print("=" * 110)
print(f"TOP 20 BGIDs BDNB ORPHELINS DU LIGHT DL (residentiel collectif, nb_log >= 3)")
print("=" * 110)
print(f"  {'#':>2s} {'bgid':<28s} {'adresse BAN':<48s} {'log':>4s} {'an':>5s} {'parc':<14s} {'maj':>3s} {'ven':>3s}")
print("  " + "-" * 108)

for i, b in enumerate(top20, 1):
    bg = b["batiment_groupe_id"]
    addr = (b.get("libelle_adr_principale_ban") or "")[:46]
    parcs = b.get("_parcs") or []
    parc1 = parcs[0] if parcs else ""
    # MAJIC presence
    n_maj_f = parc_in_majic(parc1, df_f) if parc1 else 0
    n_maj_l = parc_in_majic(parc1, df_l) if parc1 else 0
    maj_str = "OUI" if (n_maj_f or n_maj_l) else "non"
    # DVF presence par adresse parsed
    parsed = parse_ban_label(b.get("libelle_adr_principale_ban") or "")
    nv = dvf_idx.get(parsed, 0) if parsed else 0
    nv_str = str(nv) if nv else "-"
    parc_short = parc1[8:] if parc1 else "?"
    annee = str(b.get('annee_construction') or '?')
    print(f"  {i:>2d} {bg[-26:]:<28s} {addr:<48s} {b.get('nb_log',0):>4d} {annee:>5s} {parc_short:<14s} {maj_str:>3s} {nv_str:>3s}")

print()
# Bilan
print("=" * 110)
n_par_maj = sum(1 for b in top20 if (b.get('_parcs') and parc_in_majic(b['_parcs'][0], df_f) + parc_in_majic(b['_parcs'][0], df_l) > 0))
n_par_dvf = sum(1 for b in top20 if parse_ban_label(b.get('libelle_adr_principale_ban','')) and dvf_idx.get(parse_ban_label(b.get('libelle_adr_principale_ban','')), 0) > 0)
print(f"BILAN top 20 orphelins :")
print(f"  Total orphelins        : {len(orph)} (snapshot {len(bdnb)})")
print(f"  Affiches               : {len(top20)}")
print(f"  Avec parcelle MAJIC    : {n_par_maj}")
print(f"  Avec ventes DVF        : {n_par_dvf}")
print(f"  Total nb_log top 20    : {sum(b.get('nb_log',0) for b in top20)} lgts")
print()
total_lgts = sum(b.get('nb_log',0) for b in orph)
print(f"  Si TOUS les orphelins inclus -> +{len(orph)} adresses, +{total_lgts} lgts potentiels")
print("=" * 110)
