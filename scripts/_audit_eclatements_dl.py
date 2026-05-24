#!/usr/bin/env python3
"""
Audit massif des eclatements make_light DL via BDNB rel_batiment_groupe_adresse.

Pour chaque ancre RNC du light DL :
  1. Recupere son bgid
  2. Requete BDNB rel_batiment_groupe_adresse(bgid) -> liste de cle_interop
     BAN + libelle_adresse
  3. Pour chaque libelle BAN :
     - Normalise en cle (NUM|TYPE|VOIE)
     - Look-up dans light :
       * MATCH : light a cette cle ET meme bgid -> OK
       * ECLATEMENT : light a cette cle mais bgid DIFFERENT -> pattern
         215 BONNEL / 2/4/6 VILLETTE (faux-matching make_light)
       * MISSING : light n'a pas cette cle (mais l'adresse postale existe en BAN)

Rapport texte : data/_audit_eclatements_dl.txt
  - resume global
  - top 20 par nb_log_bdnb decroissant pour ECLATEMENT
  - top 20 MISSING

Lecture seule sauf cache _audit_bdnb_adr_cache.json (nouveau fichier accumule).
"""
import json, os, sys, time, urllib.request, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
os.environ.setdefault("PYTHONUTF8", "1")

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
CACHE = ROOT / "data" / "_audit_bdnb_adr_cache.json"
REPORT = ROOT / "data" / "_audit_eclatements_dl.txt"

BDNB_ADR = "https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse?batiment_groupe_id=eq."


# ---------- Normalisation libelle BAN -> cle_adresse ----------
TYPE_MAP = {
    "RUE": "RUE", "R": "RUE",
    "AVENUE": "AVENUE", "AV": "AVENUE", "AVE": "AVENUE",
    "BOULEVARD": "BOULEVARD", "BD": "BOULEVARD", "BVD": "BOULEVARD",
    "COURS": "COURS", "CRS": "COURS",
    "PLACE": "PLACE", "PL": "PLACE",
    "IMPASSE": "IMPASSE", "IMP": "IMPASSE",
    "ALLEE": "ALLEE", "ALL": "ALLEE",
    "PASSAGE": "PASSAGE", "PSGE": "PASSAGE", "PASS": "PASSAGE",
    "CITE": "CITE",
    "QUAI": "QUAI",
    "SQUARE": "SQUARE", "SQ": "SQUARE",
    "MONTEE": "MONTEE", "MTE": "MONTEE",
    "ROUTE": "ROUTE", "RTE": "ROUTE",
    "CHEMIN": "CHEMIN", "CH": "CHEMIN",
    "GRANDE": "GRANDE",    # ex: "Grande Rue"
    "VILLA": "VILLA",
    "RAMPE": "RAMPE",
    "TRAVERSE": "TRAVERSE",
    "ESPLANADE": "ESPLANADE", "ESPL": "ESPLANADE",
}
PARTICLES = {"de", "la", "le", "les", "du", "des", "d'", "l'", "au", "aux"}
SAINT_MAP = {"saint": "ST", "sainte": "STE", "st": "ST", "ste": "STE"}


def strip_accents(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _normalize_voie_words(words):
    """Liste de mots -> liste normalisee (saint/hyphen/particles)."""
    out = []
    for w in words:
        # split hyphen pour gerer "Saint-Antoine" -> ["Saint","Antoine"]
        for sub in w.split("-"):
            wl = strip_accents(sub).lower().rstrip(".")
            if not wl: continue
            if wl in PARTICLES: continue
            if wl in SAINT_MAP:
                out.append(SAINT_MAP[wl])
            else:
                out.append(strip_accents(sub).upper())
    return out


def normalize_libelle(lib):
    """'224 Cours Lafayette 69003 ...' -> '224|COURS|LAFAYETTE'.
       Genere plusieurs variantes pour fuzzy match."""
    if not lib: return None
    parts = lib.replace(",", " ").split()
    if len(parts) < 3: return None
    # numero (strip '.0' suffix)
    num = parts[0]
    if num.endswith(".0"): num = num[:-2]
    if not num[0].isdigit(): return None
    idx = 1
    if idx < len(parts) and parts[idx].lower() in ("bis", "ter", "quater"):
        suff = {"bis": "B", "ter": "T", "quater": "Q"}[parts[idx].lower()]
        num += suff
        idx += 1
    if idx >= len(parts): return None
    type_raw = strip_accents(parts[idx]).upper().rstrip(".")
    type_canon = TYPE_MAP.get(type_raw)
    if not type_canon: return None
    idx += 1
    # voie raw : tous les tokens jusqu'au prochain code postal
    raw = []
    while idx < len(parts):
        w = parts[idx]
        if w.isdigit() and len(w) == 5: break
        raw.append(w)
        idx += 1
    if not raw: return None
    voie_words = _normalize_voie_words(raw)
    if not voie_words: return None
    return f"{num}|{type_canon}|{' '.join(voie_words)}"


def normalize_variants(lib):
    """Retourne (cle_principale, [variantes alternatives]).
       Variantes : avec particules / sans saint-> garder original."""
    base = normalize_libelle(lib)
    if not base: return None, []
    # Variante "particules conservees" : utilise le voie raw sans strip particles
    parts = lib.replace(",", " ").split()
    num, type_canon = base.split("|", 2)[:2]
    # extraire raw voie words
    idx = 1
    if idx < len(parts) and parts[idx].lower() in ("bis","ter","quater"): idx += 1
    if idx < len(parts):
        idx += 1  # skip type
    raw = []
    while idx < len(parts):
        w = parts[idx]
        if w.isdigit() and len(w) == 5: break
        raw.append(w)
        idx += 1
    # variante 1 : voie avec particules (separer hyphens)
    var1_words = []
    for w in raw:
        for sub in w.split("-"):
            wl = strip_accents(sub).lower()
            if not wl: continue
            if wl in SAINT_MAP:
                var1_words.append(SAINT_MAP[wl])
            else:
                var1_words.append(strip_accents(sub).upper())
    var1 = f"{num}|{type_canon}|{' '.join(var1_words)}" if var1_words else None
    # variante 2 : SAINT au lieu de ST (cas inverse)
    var2_words = [w.replace("ST ","SAINT ") if w == "ST" else
                  w.replace("STE ","SAINTE ") if w == "STE" else w
                  for w in base.split("|", 2)[2].split()]
    # Replace ST -> SAINT
    var2_words2 = []
    for w in base.split("|",2)[2].split():
        if w == "ST": var2_words2.append("SAINT")
        elif w == "STE": var2_words2.append("SAINTE")
        else: var2_words2.append(w)
    var2 = f"{num}|{type_canon}|{' '.join(var2_words2)}"
    variants = []
    for v in (var1, var2):
        if v and v != base and v not in variants:
            variants.append(v)
    return base, variants


def lookup_cle(cle_norm, variants, ad_by_cle):
    """Cherche cle_norm puis variants dans ad_by_cle. Retourne (cle_match, a) ou (None,None)."""
    if cle_norm in ad_by_cle: return cle_norm, ad_by_cle[cle_norm]
    for v in variants:
        if v in ad_by_cle: return v, ad_by_cle[v]
    return None, None


# ---------- Load light + KV (KV non utilise pour l'audit, mais affiche) ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]

# cle -> adresse (et bgid)
ad_by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

# ancres RNC : coproprietes avec immat ET cle_adresse presente en light
ancres_rnc = []
seen_bgids = {}
for c in co:
    immat = c.get("numero_immatriculation")
    cle   = c.get("cle_adresse") or ""
    if not immat or not cle: continue
    a = ad_by_cle.get(cle)
    if not a: continue
    bg = a.get("batiment_groupe_id")
    if not bg: continue
    ancres_rnc.append({"cle": cle, "immat": immat, "bgid": bg,
                       "nb_log_bdnb": a.get("nb_log_bdnb"),
                       "nom_copro": c.get("nom_copropriete")})
    seen_bgids.setdefault(bg, []).append(cle)

print(f"[light]   {len(ad)} adresses, {len(co)} coproprietes")
print(f"[ancres]  {len(ancres_rnc)} ancres RNC (cle in light)")
print(f"[bgids]   {len(seen_bgids)} bgids distincts (ancres RNC)")


# ---------- Cache BDNB rel_adresse ----------
cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
print(f"[cache]   {len(cache)} entrees existantes ({CACHE.name})")


def fetch_bdnb_adresses(bgid):
    if bgid in cache: return cache[bgid]
    try:
        url = f"{BDNB_ADR}{bgid}&limit=50"
        with urllib.request.urlopen(url, timeout=20) as r:
            rows = json.loads(r.read())
        out = []
        for row in rows:
            lib = row.get("libelle_adresse") or ""
            cleint = row.get("cle_interop_adr") or ""
            if lib:
                out.append({"libelle": lib, "cle_interop": cleint})
    except Exception as e:
        print(f"   ! BDNB adr err {bgid}: {e}")
        out = []
    cache[bgid] = out
    time.sleep(0.07)
    return out


# ---------- Boucle audit ----------
unique_bgids = sorted(seen_bgids.keys())
to_fetch = [b for b in unique_bgids if b not in cache]
print(f"[fetch]   {len(to_fetch)} bgids a interroger (sur {len(unique_bgids)})")
for i, bg in enumerate(to_fetch, 1):
    rows = fetch_bdnb_adresses(bg)
    if i % 50 == 0 or i == len(to_fetch):
        print(f"   {i}/{len(to_fetch)}  ...{bg[-9:]} -> {len(rows)} BAN")
# Persist cache
CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[cache]   sauve : {len(cache)} entrees")


# ---------- Analyse ----------
eclatements = []   # cle existe en light mais bgid different
missing = []       # cle NOT in light (BAN orpheline cote light)
match_ok = 0
no_norm = []       # normalisation a echoue
ancre_lookup = {}  # cle_ancre -> {bgid, immat, nb_log_bdnb}
for a in ancres_rnc:
    ancre_lookup[a["cle"]] = a

def fauto_resolves_to(cle, ancre_cle, ad_by_cle, max_depth=4):
    """Suit la chaine _fusion_cible de `cle` ; retourne True si elle
    aboutit a `ancre_cle` (ou contient ancre_cle dans un label compose)."""
    cur = cle
    for _ in range(max_depth):
        a = ad_by_cle.get(cur)
        if not a: return False
        fc = a.get("_fusion_cible")
        if not fc: return False
        if fc == ancre_cle: return True
        # label compose : ex "224 CRS LAFAYETTE / 215 RUE BONNEL"
        if " / " in fc or "/" in fc:
            # split + check si une partie contient ancre_cle numero+voie
            anc_parts = ancre_cle.split("|")
            if len(anc_parts) == 3:
                anc_num, anc_type, anc_voie = anc_parts
                fc_up = fc.upper()
                if anc_num in fc_up and anc_voie in fc_up:
                    return True
        cur = fc
        if cur not in ad_by_cle: return False
    return False


for a_anc in ancres_rnc:
    bg_anc = a_anc["bgid"]
    cle_anc = a_anc["cle"]
    for ban in cache.get(bg_anc, []):
        base, variants = normalize_variants(ban["libelle"])
        if not base:
            no_norm.append((bg_anc, ban["libelle"]))
            continue
        # ne pas auto-reporter l'ancre elle-meme
        if base == cle_anc or any(v == cle_anc for v in variants):
            match_ok += 1
            continue
        matched_cle, a_in_light = lookup_cle(base, variants, ad_by_cle)
        if not a_in_light:
            # MISSING : BDNB declare cette adresse dans le bati ancre, light ne l'a pas
            missing.append({
                "cle_norm": base,
                "libelle": ban["libelle"],
                "ancre_cle": cle_anc,
                "ancre_immat": a_anc["immat"],
                "ancre_bgid": bg_anc,
                "ancre_bdnb": a_anc["nb_log_bdnb"],
                "ancre_nom": a_anc.get("nom_copro"),
            })
        else:
            bg_in_light = a_in_light.get("batiment_groupe_id")
            if bg_in_light == bg_anc:
                match_ok += 1
            else:
                fa = a_in_light.get("_fusion_auto")
                fc = a_in_light.get("_fusion_cible")
                # Filtre : si fauto chain resoud vers ancre_cle, deja-fuse
                if fa and fauto_resolves_to(matched_cle, cle_anc, ad_by_cle):
                    match_ok += 1
                    continue
                eclatements.append({
                    "cle_norm": matched_cle,
                    "libelle": ban["libelle"],
                    "cle_bgid": bg_in_light,
                    "cle_bdnb": a_in_light.get("nb_log_bdnb"),
                    "cle_immat_actuel": a_in_light.get("numero_immatriculation"),
                    "cle_match": a_in_light.get("_bdnb_match"),
                    "cle_fauto": fa,
                    "cle_fcible": fc,
                    "ancre_cle": cle_anc,
                    "ancre_immat": a_anc["immat"],
                    "ancre_bgid": bg_anc,
                    "ancre_bdnb": a_anc["nb_log_bdnb"],
                    "ancre_nom": a_anc.get("nom_copro"),
                })


# ---------- Rapport ----------
lines = []
def w(s=""): lines.append(s)

w("=" * 110)
w(f"AUDIT ECLATEMENTS make_light DL  --  via BDNB rel_batiment_groupe_adresse")
w(f"  date scan : {time.strftime('%Y-%m-%d %H:%M:%S')}")
w("=" * 110)
w()
w("RESUME :")
w(f"  Ancres RNC scannees    : {len(ancres_rnc)}")
w(f"  Bgids distincts        : {len(unique_bgids)}")
w(f"  BAN libelles examines  : {sum(len(cache.get(b, [])) for b in unique_bgids)}")
w(f"  Normalisations OK      : {sum(1 for b in unique_bgids for ban in cache.get(b, []) if normalize_variants(ban['libelle'])[0])}")
w(f"  Normalisations echoues : {len(no_norm)}")
w(f"  MATCH (meme bgid)      : {match_ok}")
w(f"  ECLATEMENT (bgid diff) : {len(eclatements)}")
w(f"  MISSING (cle absente)  : {len(missing)}")
w()

# ---------- Top 20 ECLATEMENT par nb_log_bdnb (cote light) ----------
w("=" * 110)
w(f"TOP 20 ECLATEMENT (faux-matching make_light) -- tri par nb_log_bdnb cote ancre")
w("=" * 110)
ecl_sorted = sorted(eclatements,
                    key=lambda x: -(x.get("ancre_bdnb") or 0))
# Filtrer : ancre bdnb > 0 (priorise les bati avec poids reel)
ecl_priority = [e for e in ecl_sorted if (e.get("ancre_bdnb") or 0) > 0]
# Dedup par (cle_norm, ancre_cle) au cas ou
seen_pair = set()
ecl_dedup = []
for e in ecl_priority:
    k = (e["cle_norm"], e["ancre_cle"])
    if k in seen_pair: continue
    seen_pair.add(k)
    ecl_dedup.append(e)

if not ecl_dedup:
    w("  (aucun)")
for i, e in enumerate(ecl_dedup[:20], 1):
    w()
    w(f"#{i:02d}  {e['cle_norm']:38s}  (libelle BAN: '{e['libelle']}')")
    w(f"     ANCRE :   {e['ancre_cle']:38s}  bgid=...{e['ancre_bgid'][-9:]}  "
      f"immat={e['ancre_immat']}  nom={(e['ancre_nom'] or '')[:30]!r}  bdnb={e['ancre_bdnb']}")
    w(f"     LIGHT :   bgid=...{(e['cle_bgid'] or '?')[-9:] if e['cle_bgid'] else '?'}  "
      f"bdnb={e['cle_bdnb']}  immat={e['cle_immat_actuel'] or '-'}  match={e['cle_match']!r}  "
      f"fauto={e['cle_fauto']}")
    if e["cle_fcible"]:
        w(f"     fauto_cible actuel : {e['cle_fcible']!r}")

# ---------- Top 20 MISSING par nb_log_bdnb (ancre) ----------
w()
w("=" * 110)
w(f"TOP 20 MISSING (BAN signale par BDNB sur ancre, absente du light)")
w("=" * 110)
miss_sorted = sorted(missing, key=lambda x: -(x.get("ancre_bdnb") or 0))
# Dedup par (cle_norm, ancre_cle)
seen_pair = set()
miss_dedup = []
for m in miss_sorted:
    k = (m["cle_norm"], m["ancre_cle"])
    if k in seen_pair: continue
    seen_pair.add(k)
    miss_dedup.append(m)

if not miss_dedup:
    w("  (aucun)")
for i, m in enumerate(miss_dedup[:20], 1):
    w()
    w(f"#{i:02d}  {m['cle_norm']:38s}  (libelle BAN: '{m['libelle']}')")
    w(f"     ANCRE :   {m['ancre_cle']:38s}  bgid=...{m['ancre_bgid'][-9:]}  "
      f"immat={m['ancre_immat']}  nom={(m['ancre_nom'] or '')[:30]!r}  bdnb={m['ancre_bdnb']}")

# ---------- Sample des normalisations echouees (debug) ----------
w()
w("=" * 110)
w(f"SAMPLE NORMALISATIONS ECHOUES (top 15, debug)")
w("=" * 110)
seen_lib = set()
for bg, lib in no_norm:
    if lib in seen_lib: continue
    seen_lib.add(lib)
    if len(seen_lib) > 15: break
    w(f"  bgid=...{bg[-9:]}  libelle='{lib}'")

REPORT.write_text("\n".join(lines), encoding="utf-8")
print()
print("=" * 110)
print(f"Rapport ecrit : {REPORT}  ({len(lines)} lignes)")
print("=" * 110)
print()
# Affiche le resume sur stdout aussi
print("\n".join(lines[:14]))
