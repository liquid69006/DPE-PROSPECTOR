#!/usr/bin/env python3
"""Affiche TOP N ECLATEMENT non-encore-fixes apres post-traitement
des 6 megas + EMERGENCE LAFAYETTE. Reutilise la logique de
_audit_eclatements_dl.py (cache _audit_bdnb_adr_cache.json) +
filtre fauto_resolves_to.
"""
import json, sys, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
CACHE = ROOT / "data" / "_audit_bdnb_adr_cache.json"

# ---------- Normalisation (reutilise audit script) ----------
TYPE_MAP = {
    "RUE":"RUE","R":"RUE","AVENUE":"AVENUE","AV":"AVENUE","AVE":"AVENUE",
    "BOULEVARD":"BOULEVARD","BD":"BOULEVARD","BVD":"BOULEVARD",
    "COURS":"COURS","CRS":"COURS","PLACE":"PLACE","PL":"PLACE",
    "IMPASSE":"IMPASSE","IMP":"IMPASSE","ALLEE":"ALLEE","ALL":"ALLEE",
    "PASSAGE":"PASSAGE","PSGE":"PASSAGE","PASS":"PASSAGE","CITE":"CITE",
    "QUAI":"QUAI","SQUARE":"SQUARE","SQ":"SQUARE","MONTEE":"MONTEE","MTE":"MONTEE",
    "ROUTE":"ROUTE","RTE":"ROUTE","CHEMIN":"CHEMIN","CH":"CHEMIN",
    "GRANDE":"GRANDE","VILLA":"VILLA","RAMPE":"RAMPE","TRAVERSE":"TRAVERSE",
    "ESPLANADE":"ESPLANADE","ESPL":"ESPLANADE",
}
PARTICLES = {"de","la","le","les","du","des","d'","l'","au","aux"}
SAINT_MAP = {"saint":"ST","sainte":"STE","st":"ST","ste":"STE"}


def strip_accents(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")


def normalize_voie_words(words):
    out = []
    for w in words:
        for sub in w.split("-"):
            wl = strip_accents(sub).lower().rstrip(".")
            if not wl: continue
            if wl in PARTICLES: continue
            if wl in SAINT_MAP: out.append(SAINT_MAP[wl])
            else: out.append(strip_accents(sub).upper())
    return out


def normalize_libelle(lib):
    if not lib: return None
    parts = lib.replace(",", " ").split()
    if len(parts) < 3: return None
    num = parts[0]
    if num.endswith(".0"): num = num[:-2]
    if not num[0].isdigit(): return None
    idx = 1
    if idx < len(parts) and parts[idx].lower() in ("bis","ter","quater"):
        suff = {"bis":"B","ter":"T","quater":"Q"}[parts[idx].lower()]
        num += suff
        idx += 1
    if idx >= len(parts): return None
    type_raw = strip_accents(parts[idx]).upper().rstrip(".")
    type_canon = TYPE_MAP.get(type_raw)
    if not type_canon: return None
    idx += 1
    raw = []
    while idx < len(parts):
        w = parts[idx]
        if w.isdigit() and len(w) == 5: break
        raw.append(w); idx += 1
    if not raw: return None
    voie_words = normalize_voie_words(raw)
    if not voie_words: return None
    return f"{num}|{type_canon}|{' '.join(voie_words)}"


def normalize_variants(lib):
    base = normalize_libelle(lib)
    if not base: return None, []
    var_words2 = []
    for w in base.split("|",2)[2].split():
        if w == "ST": var_words2.append("SAINT")
        elif w == "STE": var_words2.append("SAINTE")
        else: var_words2.append(w)
    num, type_canon = base.split("|",2)[:2]
    var2 = f"{num}|{type_canon}|{' '.join(var_words2)}"
    return base, [var2] if var2 != base else []


def lookup_cle(cle_norm, variants, ad_by_cle):
    if cle_norm in ad_by_cle: return cle_norm, ad_by_cle[cle_norm]
    for v in variants:
        if v in ad_by_cle: return v, ad_by_cle[v]
    return None, None


def to_int(x):
    try: return int(x)
    except: return 0


# ---------- Data ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
ad_by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}
cache = json.loads(CACHE.read_text(encoding="utf-8"))

ancres_rnc = []
for c in co:
    immat = c.get("numero_immatriculation")
    cle   = c.get("cle_adresse") or ""
    if not immat or not cle: continue
    a = ad_by_cle.get(cle)
    if not a: continue
    bg = a.get("batiment_groupe_id")
    if not bg: continue
    ancres_rnc.append({"cle": cle, "immat": immat, "bgid": bg,
                       "nb_log_bdnb": to_int(a.get("nb_log_bdnb")),
                       "nom_copro": c.get("nom_copropriete"),
                       "lots_tot": c.get("nb_lots_total"),
                       "lots_hab": c.get("nb_lots_habitation")})


def fauto_resolves_to(cle, ancre_cle, ad_by_cle, max_depth=4):
    cur = cle
    for _ in range(max_depth):
        a = ad_by_cle.get(cur)
        if not a: return False
        fc = a.get("_fusion_cible")
        if not fc: return False
        if fc == ancre_cle: return True
        if " / " in fc or "/" in fc:
            anc_parts = ancre_cle.split("|")
            if len(anc_parts) == 3:
                anc_num, anc_type, anc_voie = anc_parts
                fc_up = fc.upper()
                if anc_num in fc_up and anc_voie in fc_up: return True
        cur = fc
        if cur not in ad_by_cle: return False
    return False


eclatements = []
for a_anc in ancres_rnc:
    bg_anc = a_anc["bgid"]
    cle_anc = a_anc["cle"]
    for ban in cache.get(bg_anc, []):
        base, variants = normalize_variants(ban["libelle"])
        if not base: continue
        if base == cle_anc or any(v == cle_anc for v in variants): continue
        matched_cle, a_in_light = lookup_cle(base, variants, ad_by_cle)
        if not a_in_light: continue
        bg_in_light = a_in_light.get("batiment_groupe_id")
        if bg_in_light == bg_anc: continue
        fa = a_in_light.get("_fusion_auto")
        if fa and fauto_resolves_to(matched_cle, cle_anc, ad_by_cle): continue
        eclatements.append({
            "cle_norm": matched_cle,
            "libelle": ban["libelle"],
            "cle_bgid": bg_in_light,
            "cle_bdnb": to_int(a_in_light.get("nb_log_bdnb")),
            "cle_immat_actuel": a_in_light.get("numero_immatriculation"),
            "cle_match": a_in_light.get("_bdnb_match"),
            "cle_fauto": fa,
            "cle_fcible": a_in_light.get("_fusion_cible"),
            "ancre_cle": cle_anc,
            "ancre_immat": a_anc["immat"],
            "ancre_bgid": bg_anc,
            "ancre_bdnb": a_anc["nb_log_bdnb"],
            "ancre_lots_t": a_anc.get("lots_tot"),
            "ancre_lots_h": a_anc.get("lots_hab"),
            "ancre_nom": a_anc.get("nom_copro"),
        })

# Dedup par (cle_norm, ancre_cle)
seen = set(); dedup = []
for e in eclatements:
    k = (e["cle_norm"], e["ancre_cle"])
    if k in seen: continue
    seen.add(k); dedup.append(e)

# Tri par ancre_bdnb desc
dedup.sort(key=lambda x: -(x["ancre_bdnb"] or 0))

# Filtre minimum : ancre_bdnb > 0 (priorise les ancres signifiantes)
prio = [e for e in dedup if (e["ancre_bdnb"] or 0) > 0]

print("=" * 110)
print(f"TOP 30 ECLATEMENT BDNB NON-RESOLUS  ({len(dedup)} total apres exclusion deja-fixes)")
print(f"  (filtre : ancre_bdnb > 0 = {len(prio)} prioritaires)")
print("=" * 110)

def mech_suggestion(e):
    bg_diff = e["cle_bgid"] != e["ancre_bgid"]
    if e["cle_immat_actuel"]:
        return f"WARN-2nd-ancre (cle a immat {e['cle_immat_actuel']} != ancre {e['ancre_immat']}) - 2 SDC distincts ?"
    if e.get("cle_fauto"):
        return f"REBIND _fusion_cible (actuelle='{e['cle_fcible']}' -> ancre) + bgid switch"
    return "RE-FUSE Cambronne (bgid switch + _fusion_auto + cible)"

for i, e in enumerate(prio[:30], 1):
    print()
    print(f"#{i:02d}  {e['cle_norm']:36s}  (libelle BAN: '{e['libelle']}')")
    print(f"     ANCRE     : {e['ancre_cle']:36s}  immat={e['ancre_immat']}  "
          f"nom='{(e['ancre_nom'] or '')[:32]}'  lots={e['ancre_lots_t']}/{e['ancre_lots_h']}  "
          f"bdnb_anc={e['ancre_bdnb']}")
    print(f"     LIGHT cur : bgid=...{(e['cle_bgid'] or '?')[-9:] if e['cle_bgid'] else '?'}  "
          f"bdnb={e['cle_bdnb']}  immat={e['cle_immat_actuel'] or '-'}  "
          f"match='{e['cle_match']}'  fauto={e['cle_fauto']}")
    if e["cle_fcible"]:
        print(f"     fauto_cible actuel : '{e['cle_fcible']}'")
    print(f"     bgid ancre : ...{e['ancre_bgid'][-9:]}  (a faire migrer le cle vers)")
    print(f"     MECANISME : {mech_suggestion(e)}")

# Rapport texte
out = ROOT / "data" / "_audit_eclatements_dl_top30_restants.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write(f"TOP 30 ECLATEMENT non-resolus DL (post-fix 6 megas + EMERGENCE LAFAYETTE)\n")
    f.write(f"Total : {len(dedup)} eclatements ({len(prio)} avec ancre_bdnb > 0)\n\n")
    for i, e in enumerate(prio[:30], 1):
        f.write(f"#{i:02d}  cle_eclatee = {e['cle_norm']}\n")
        f.write(f"     ancre = {e['ancre_cle']}  immat={e['ancre_immat']}  "
                f"nom='{e['ancre_nom']}'  lots={e['ancre_lots_t']}/{e['ancre_lots_h']}\n")
        f.write(f"     light_bgid = {e['cle_bgid']}  vs  ancre_bgid = {e['ancre_bgid']}\n")
        f.write(f"     cle_actuel : bdnb={e['cle_bdnb']}, immat={e['cle_immat_actuel']}, "
                f"match={e['cle_match']}, fauto={e['cle_fauto']}, fcible={e['cle_fcible']}\n")
        f.write(f"     mecanisme : {mech_suggestion(e)}\n\n")
print()
print(f"Rapport ecrit : {out}")
