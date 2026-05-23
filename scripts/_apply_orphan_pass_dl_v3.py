#!/usr/bin/env python3
"""Option B - Pass orphan BDNB pour DL : sandbox v3.

Au lieu de regenerer toute la pipeline (qui ecraserait les fix manuels
cherrypick + propag + refuse), on applique la passe orphelin de maniere
NON-DESTRUCTIVE :
  1. Lit le current light (1326 adresses, tous fix manuels appliques)
  2. Identifie les 58 bgids BDNB residentiels orphelins (absents du light)
  3. Construit pour chacun une cle 'NUM|TYPE|VOIE' depuis libelle_adr_ban
  4. Compose un dict adresse compatible schema light
  5. Ecrit le tout vers data/secteur_dl_light_v3.json (sandbox)

Pas d'ecriture sur le light actuel. Diff v3 vs current affiche.

NOTE FUTURE : pour application durable, integrer cette passe a la fin
de main() dans make_light.py (HORS-REPO) avant le json.dump final.
Pattern equivalent : iter BDNB, dedup contre bgids deja referencer dans
adr list, append adresse compose pour chaque orphan.
"""
import json, re, sys, math, urllib.request, time, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BDNB = Path(r"C:\Users\Station 5\bdnb_dauphine_lacassagne.json")
V3 = ROOT / "data" / "secteur_dl_light_v3.json"
UA = "Mozilla/5.0 diag/1.0"

# Normalisation voie (meme convention make_light)
TV_MAP = {
    "RUE":"RUE","R":"RUE","AVENUE":"AVENUE","AV":"AVENUE","AVE":"AVENUE",
    "BOULEVARD":"BOULEVARD","BD":"BOULEVARD","BLD":"BOULEVARD","BOUL":"BOULEVARD",
    "COURS":"COURS","CRS":"COURS",
    "IMPASSE":"IMPASSE","IMP":"IMPASSE",
    "PLACE":"PLACE","PL":"PLACE",
    "ALLEE":"ALLEE","ALL":"ALLEE",
    "PASSAGE":"PASSAGE","PAS":"PASSAGE",
    "CHEMIN":"CHEMIN","CH":"CHEMIN","CHE":"CHEMIN",
    "QUAI":"QUAI","QU":"QUAI",
    "ROUTE":"ROUTE","RTE":"ROUTE",
    "SQUARE":"SQUARE","SQ":"SQUARE",
    "MONTEE":"MONTEE","MTE":"MONTEE",
    "GRANDE RUE":"GRANDE RUE","GR":"GRANDE RUE",
    "TERRASSE":"TERRASSE","TSSE":"TERRASSE",
    "VILLA":"VILLA","VLA":"VILLA",
}
ARTICLES = {"DE","DES","DU","D","LA","LE","LES","L","AUX"}
SAINTS = {"SAINT":"ST","SAINTE":"STE","SAINTES":"STES","SAINTS":"STS"}
BIS = {"B":"B","BIS":"B","T":"T","TER":"T","Q":"Q","QUATER":"Q","A":"A","C":"C","D":"D"}

def _noacc(s):
    """Normalise NFD + supprime marques accent (cf. make_light pattern).
    Couvre toutes lettres minuscules/majuscules avec accents (e/E + diacritiques)."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def parse_ban_label(label):
    """'237 Rue Paul Bert 69003 Lyon 3e' -> ('237'/'15T', 'RUE', 'PAUL BERT') ou None."""
    if not label: return None
    s = _noacc(label.strip()).upper()
    # Strip cp+commune
    s = re.sub(r"\s+\d{5}\b.*$", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = s.split()
    if not toks: return None
    # Num + suffix optionnel
    m = re.match(r"^(\d+)([A-Z]?)$", toks[0])
    if not m: return None
    num = str(int(m.group(1)))
    sfx = m.group(2)
    if sfx and sfx not in BIS: sfx = ""
    toks = toks[1:]
    # Suffix autonome (BIS/TER) - sinon = part of voie
    if not sfx and toks and toks[0] in BIS:
        sfx = BIS[toks[0]]
        toks = toks[1:]
    # Type voie
    if not toks: return None
    tv = TV_MAP.get(toks[0], None)
    if not tv: return None
    toks = toks[1:]
    # Strip articles
    while toks and toks[0] in ARTICLES:
        toks = toks[1:]
    # SAINT/SAINTE
    toks = [SAINTS.get(t, t) for t in toks]
    voie = " ".join(toks).strip()
    if not voie: return None
    return (num + sfx), tv, voie

def hav(la1, lo1, la2, lo2):
    R = 6371000.0
    r = math.pi / 180
    dla = (la2 - la1) * r
    dlo = (lo2 - lo1) * r
    x = (math.sin(dla / 2) ** 2
         + math.cos(la1 * r) * math.cos(la2 * r) * math.sin(dlo / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))

# --- Load light current ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
N_AD0 = len(ad)
N_CO0 = len(co)
print(f"Current light : {N_AD0} adresses, {N_CO0} copros")

light_bgids = set()
light_cles = set()
for a in ad:
    bg = a.get("batiment_groupe_id")
    if bg: light_bgids.add(bg)
    cle = a.get("cle")
    if cle: light_cles.add(cle)

# Indices pour code_iris assignment : utiliser adresse light la plus proche
ad_with_coord = [a for a in ad if a.get("longitude") and a.get("latitude") and a.get("code_iris")]

def nearest_iris(lon, lat):
    """Retourne code_iris de l'adresse light la plus proche."""
    best, best_d = None, 1e9
    for a in ad_with_coord:
        d = hav(lat, lon, a["latitude"], a["longitude"])
        if d < best_d:
            best_d = d; best = a["code_iris"]
    return best, best_d

# --- Load BDNB snapshot + filtre orphelins ---
bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
orph = []
for b in bdnb:
    if b.get("batiment_groupe_id") in light_bgids: continue
    if (b.get("usage_principal_bdnb_open") or "").strip() != "Résidentiel collectif": continue
    if (b.get("nb_log") or 0) < 3: continue
    orph.append(b)
orph.sort(key=lambda b: -(b.get("nb_log") or 0))
print(f"Orphelins BDNB residentiels nb_log >= 3 : {len(orph)}")

# --- Construction des nouvelles adresses ---
appended = []
skipped_parse = []
collisions_cle = []
MARKER = "fix_bdnb_orphelin_dl_2026-05-23"

for b in orph:
    label = b.get("libelle_adr_principale_ban") or ""
    parsed = parse_ban_label(label)
    if not parsed:
        skipped_parse.append((b.get("batiment_groupe_id"), label))
        continue
    num, tv, voie = parsed
    cle = f"{num}|{tv}|{voie}"
    if cle in light_cles:
        collisions_cle.append((cle, b.get("batiment_groupe_id")))
        continue
    lon = b.get("lon"); lat = b.get("lat")
    iris, dist_m = nearest_iris(lon, lat) if (lon and lat) else (None, None)
    # Composer dict adresse (champs essentiels du schema light)
    adr_new = {
        "cle": cle,
        "adresse": label,
        "longitude": lon,
        "latitude": lat,
        "code_iris": iris,
        "_coord_source": "bdnb_orphelin",
        "dans_majic": False,
        "sci_proprietaire": "inconnu",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": None,
        "_syndic_src": None,
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "taux_rotation": None,
        "classement_rotation": "Aucune vente",
        "nb_log_bdnb": b.get("nb_log"),
        "annee_construction": b.get("annee_construction"),
        "classe_dpe": b.get("classe_bilan_dpe"),
        "type_batiment": b.get("type_batiment_dpe"),
        "type_chauffage": b.get("type_energie_chauffage"),
        "batiment_groupe_id": b.get("batiment_groupe_id"),
        "_bdnb_match": "bdnb_orphelin",
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Aucune vente",
        "_taux_logement_src": "bdnb_orphelin_no_dvf",
        "usage_principal_bdnb": b.get("usage_principal_bdnb_open"),
        "_usage_bdnb_src": "bdnb_orphelin_pass",
        "_injection_bdnb_orphelin": MARKER,
        "_iris_dist_m": round(dist_m, 1) if dist_m is not None else None,
    }
    doc["adresses"].append(adr_new)
    light_cles.add(cle)
    light_bgids.add(b.get("batiment_groupe_id"))
    appended.append((cle, b.get("nb_log"), b.get("batiment_groupe_id"), iris))

print()
print(f"  Adresses orphelines ajoutees : {len(appended)}")
print(f"  Skipped (parse BAN echec)     : {len(skipped_parse)}")
print(f"  Collisions cle (deja light)   : {len(collisions_cle)}")
if skipped_parse:
    print(f"  Detail parse echecs :")
    for bg, lab in skipped_parse[:10]:
        print(f"    {bg}  {lab!r}")
if collisions_cle:
    print(f"  Detail collisions :")
    for cle, bg in collisions_cle[:10]:
        print(f"    {cle} (bgid {bg})")

# --- Calcul parc UI avant/apres ---
USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
def parc_ui(adresses, copros):
    co_by_cle = {c.get("cle_adresse"): c for c in copros if c.get("cle_adresse")}
    by_bgid = {}
    for a in adresses:
        if a.get("_fusion_auto"): continue
        bgid = a.get("batiment_groupe_id") or "<NB>" + (a.get("cle") or "")
        cm = co_by_cle.get(a.get("cle"))
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid: by_bgid[bgid] = max(by_bgid[bgid], n)
        else: by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

# Avant : doc avant les appends (impossible car deja appended).
# On le calcule sur l'ancien light reload
doc_avant = json.loads(LIGHT.read_text(encoding="utf-8"))
parc_av, n_bg_av = parc_ui(doc_avant["adresses"], doc_avant["coproprietes"])
parc_ap, n_bg_ap = parc_ui(doc["adresses"], doc["coproprietes"])

# --- Sauvegarde sandbox v3 ---
with V3.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print()
print(f"  Sandbox v3 ecrit : {V3.name}  ({len(doc['adresses'])} adresses, {len(doc['coproprietes'])} copros)")

# --- Bilan ---
print()
print("=" * 90)
print(f"DELTA v3 vs current DL")
print("=" * 90)
print(f"  Adresses : {N_AD0} -> {len(doc['adresses'])}  ({len(doc['adresses'])-N_AD0:+d})")
print(f"  Copros   : {N_CO0} -> {len(doc['coproprietes'])}  ({len(doc['coproprietes'])-N_CO0:+d})")
print(f"  Parc UI  : {parc_av} -> {parc_ap}  ({parc_ap-parc_av:+d})")
print(f"  Bgids actifs : {n_bg_av} -> {n_bg_ap}  ({n_bg_ap-n_bg_av:+d})")
print()
# Distribution IRIS
from collections import Counter
iris_cnt = Counter(a[3] for a in appended)
print(f"  Distribution IRIS des ajouts :")
for iris, n in sorted(iris_cnt.items(), key=lambda x: -x[1]):
    print(f"    {iris} : {n}")
# Top 10 ajouts
print()
print(f"  Top 10 cles ajoutees (par nb_log) :")
appended.sort(key=lambda a: -(a[1] or 0))
for cle, n, bg, iris in appended[:10]:
    print(f"    {cle:36s}  log={n:>3d}  bgid=...{(bg or '-')[-9:]}  iris={iris}")
print()
print(f"  Sandbox preserve : {V3}")
print(f"  Current preserve : {LIGHT}  (INCHANGE)")
print("=" * 90)
