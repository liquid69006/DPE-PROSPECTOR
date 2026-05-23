#!/usr/bin/env python3
"""Triage des 85 cles suffixees injectees DL (lecture seule).

Pour chaque cle, determine :
  1. RNC parcelle - copro RNC sur la meme parcelle BDNB ? (pattern Suffren/Cambronne)
  2. BDNB bgid - meme bgid qu'une ancre existante du current ? (RE-FUSE possible)
  3. Mono - ratio MAJIC top SIREN >= 90% ?
  4. Social - bailleur HLM/OPH/SA HLM dominant ?
  5. Tertiaire - usage_principal_bdnb = Tertiaire ?

Triage final : Rattachable RNC | Mono | Social | Tertiaire | Copro_non_immat probable.
"""
import json, re, sys, urllib.parse, urllib.request, time
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC_PARQUET = Path(r'C:\Users\Station 5\majic_locaux2_2025.parquet')

RID_RNC = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID_RNC}/data/"
UA = "Mozilla/5.0 triage-script/1.0"

import pyarrow.parquet as pq

# --- Helpers ---
BAILLEURS_SOCIAUX = [
    "CDC HABITAT","ALLIADE HABITAT","GRAND LYON HABITAT","GRANDLYON HABITAT",
    "OPH ","OPH DE","OPHLM","HBM","HLM","HABITAT ET HUMANIS","DYNACITE",
    "EST METROPOLE HABITAT","SCIC HABITAT","ICF HABITAT","RHONE SAONE HABITAT",
    "ADOMA","FONCIERE LOGEMENT","ERILIA","CDC HAB","FRANCE LOGEMENT","SCI 3F",
    "IMMOBILIERE 3F","ALILA","NEXITY DOMAINES","SOLLAR","BATIGERE","NOVEDIS",
    "FREHA","SCIC RHONE-ALPES","SOCIETE LYONNAISE","OPHEOR","OPAC",
    "IMMOBILIERE RHONE ALPES","ICF SUD-EST",
    "SA HLM","SA D'HLM","SA DE HLM",
    "FONCIERE D'HABITAT ET HUM","3F RESIDENCES","ACTION SOCIALE","IN'LI",
    "FONCIERE VESTA","HOSPICES CIVILS","SA DE CONSTRUCTION DE LA VILLE",
    "SEM DE CONSTRUCTION","COMMUNE DE LYON","COMMUNAUTE URBAINE DE LYON",
    "DEPARTEMENT DU RHONE","FONDATION ARALIS","METROPOLE DE LYON",
]
def is_bs(d):
    if not d: return False
    s = str(d).upper()
    return any(k in s for k in BAILLEURS_SOCIAUX)

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_error": str(e)[:120]}

def bdnb_parc(bg):
    """Retourne liste de parcelles BDNB pour un bgid (cache local)."""
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    d = http_get(url)
    if isinstance(d, dict) and "_error" in d: return []
    return [p.get("parcelle_id") for p in d if p.get("parcelle_id")]

def bdnb_to_rnc(p):
    if p[:2] == "69" and p[5:8] == "000":
        return "69123383" + p[8:]
    return p

# Cache parcelles par bgid (pour eviter API repeat)
PARC_CACHE = {}
def get_parcelles(bgid):
    if not bgid: return []
    if bgid in PARC_CACHE: return PARC_CACHE[bgid]
    parcs = bdnb_parc(bgid)
    PARC_CACHE[bgid] = parcs
    time.sleep(0.06)
    return parcs

# Cache scan parcelle RNC
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
            if im and im not in seen:
                seen[im] = row
        time.sleep(0.05)
    res = list(seen.values())
    RNC_CACHE[rnc_p] = res
    return res

def parse_cle_suffix(cle):
    """('15T','RUE','DAUPHINE') -> ('15','T','RUE','DAUPHINE') ou None."""
    m = re.match(r"^(\d+)([A-Z])\|([A-Z]+)\|(.+)$", cle)
    if not m: return None
    return m.group(1), m.group(2), m.group(3), m.group(4)

# --- Load light ---
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {a.get("cle"): a for a in ad}
co_by_immat = {c.get("numero_immatriculation"): c for c in co if c.get("numero_immatriculation")}

# Index des bgids par ancre du current (avant injection cherrypick)
ancre_bgids = defaultdict(list)
for a in ad:
    if a.get("_injection_indice"): continue  # exclure les cles injectees
    bgid = a.get("batiment_groupe_id")
    if bgid: ancre_bgids[bgid].append(a.get("cle"))

# Adresses injectees (les 85)
injected = [a for a in ad if a.get("_injection_indice")]
print(f"  Light DL : {len(ad)} adresses dont {len(injected)} injectees ({len(co)} copros)")

# --- MAJIC parquet : lots par cle suffixee ---
print()
print("Charge MAJIC DL parquet pour analyse SIREN par cle suffixee ...")
tbl = pq.read_table(str(MAJIC_PARQUET), filters=[
    ("departement","=","69"),("code_commune","=","383")])
df = tbl.to_pandas()

# Index MAJIC par (num+suffixe, type, voie normalisee)
def norm_voie_majic(s):
    if not s: return ""
    s = str(s).upper().strip()
    s = s.replace("-", " ").replace("'", " ")
    # SAINTE/SAINT -> STE/ST
    s = re.sub(r"\bSAINTE\b", "STE", s)
    s = re.sub(r"\bSAINT\b",  "ST",  s)
    # Strip articles
    s = re.sub(r"^(DU|DE|DES|LA|LE|L|D|AUX)\s+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","PAS":"PASSAGE","PL":"PLACE",
          "BD":"BOULEVARD","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI"}
df["_num_str"] = df["numero_voirie"].fillna("").astype(str).str.lstrip("0")
df["_indice"] = df["indice_de_repetition"].fillna("").astype(str).str.strip().str.upper()
df["_tv"] = df["nature_voie"].fillna("").map(lambda x: TV_MAP.get(str(x).strip().upper(), ""))
df["_voie"] = df["nom_voie"].fillna("").map(norm_voie_majic)

# --- Triage ---
RATTACHABLE_RNC = []  # match parcelle RNC live (Suffren/Cambronne)
RE_FUSE_BGID   = []  # meme bgid qu'une ancre existante (parent FA)
MONO_MAJIC     = []  # ratio MAJIC top SIREN >= 90%
SOCIAL         = []  # bailleur HLM/OPH/SA HLM dominant
TERTIAIRE      = []  # usage BDNB = Tertiaire
COPRO_NON_IMMAT = []  # le reste

print()
print(f"Analyse des 85 cles injectees ...")
print()

results = []
for a in injected:
    cle = a.get("cle") or ""
    parsed = parse_cle_suffix(cle)
    if not parsed:
        print(f"  SKIP cle non-parseable : {cle}"); continue
    num, indice, tv, voie = parsed
    bgid = a.get("batiment_groupe_id") or ""
    usage = a.get("usage_principal_bdnb") or ""
    bdnb = a.get("nb_log_bdnb") or 0

    # 1. Parcelles BDNB du bgid
    parcs = get_parcelles(bgid) if bgid else []
    # 2. Scan RNC live sur ces parcelles
    rnc_hits = []
    for p in parcs:
        rnc_p = bdnb_to_rnc(p)
        hits = scan_rnc_parc(rnc_p)
        for h in hits:
            im = h.get("numero_immatriculation")
            if im not in co_by_immat:  # copro absente du secteur snapshot
                rnc_hits.append((im, h.get("nom_usage_copropriete",""), h.get("nombre_total_lots"),
                                 h.get("nombre_lots_usage_habitation") or h.get("nombre_lots_habitation_bureaux_commerces"),
                                 "HORS-SCT"))
            else:
                rnc_hits.append((im, h.get("nom_usage_copropriete",""), h.get("nombre_total_lots"),
                                 h.get("nombre_lots_usage_habitation") or h.get("nombre_lots_habitation_bureaux_commerces"),
                                 "DEJA-SCT"))

    # 3. MAJIC par cle suffixee
    m = df[(df["_num_str"] == num) & (df["_indice"] == indice) &
           (df["_tv"] == tv) & (df["_voie"] == voie)]
    n_lots = len(m)
    sirens = m["numero_siren"].dropna().value_counts()
    top_siren = None; top_lots = 0; top_denom = ""; pct_top = 0.0
    if len(sirens):
        top_siren = sirens.index[0]
        top_lots = int(sirens.iloc[0])
        denoms = m[m["numero_siren"]==top_siren]["denomination"].dropna().unique()
        top_denom = denoms[0] if len(denoms) else "?"
        pct_top = (100.0 * top_lots / n_lots) if n_lots else 0.0
    n_sirens = int(sirens.shape[0]) if len(sirens) else 0

    # 4. Detection BDNB bgid match ancre existante
    bgid_parents_current = [c for c in ancre_bgids.get(bgid, []) if c not in (cle, a.get("_fusion_cible"))]

    is_tert = "TERTIAIRE" in usage.upper().replace("É","E")
    is_mono = (pct_top >= 90.0 and n_lots > 0)
    is_social = (is_bs(top_denom) and pct_top >= 80.0)

    rec = {
        "cle": cle, "bgid": bgid, "bdnb": bdnb, "usage": usage,
        "parcs": parcs, "rnc_hits": rnc_hits,
        "majic_lots": n_lots, "n_sirens": n_sirens,
        "top_siren": top_siren, "top_lots": top_lots, "top_denom": top_denom,
        "pct_top": pct_top, "is_tert": is_tert, "is_mono": is_mono, "is_social": is_social,
        "bgid_parents_current": bgid_parents_current,
    }
    results.append(rec)

    # Triage : ordre de priorite
    if rnc_hits:
        RATTACHABLE_RNC.append(rec)
    elif is_tert:
        TERTIAIRE.append(rec)
    elif is_social:
        SOCIAL.append(rec)
    elif is_mono:
        MONO_MAJIC.append(rec)
    elif bgid_parents_current:
        RE_FUSE_BGID.append(rec)
    else:
        COPRO_NON_IMMAT.append(rec)

# Display
def dump(label, items, max_show=None):
    print()
    print("#" * 90)
    print(f"# {label} ({len(items)})")
    print("#" * 90)
    if not items:
        print("  (vide)"); return
    items.sort(key=lambda r: -(r["bdnb"] or 0))
    n_show = max_show or len(items)
    for r in items[:n_show]:
        rnc_str = ""
        if r["rnc_hits"]:
            ims = ",".join(h[0] + ("@" + h[4]) for h in r["rnc_hits"][:2])
            rnc_str = f"  RNC=[{ims}]"
        majic_str = ""
        if r["majic_lots"]:
            majic_str = f"  MAJIC={r['top_lots']}/{r['majic_lots']}({int(r['pct_top'])}%){r['n_sirens']}s {r['top_denom'][:25]!r}"
        bp = ""
        if r["bgid_parents_current"]:
            bp = f"  parent_bgid=[{','.join(r['bgid_parents_current'][:2])}]"
        print(f"  {r['cle']:36s}  bdnb={r['bdnb']:>3d}  usage={r['usage'][:20]:20s}{majic_str}{rnc_str}{bp}")
    if max_show and len(items) > max_show:
        print(f"  ... (+{len(items) - max_show} autres)")

dump("RATTACHABLES RNC (copro RNC live sur parcelle BDNB)", RATTACHABLE_RNC)
dump("RE-FUSE BGID (meme bgid qu'ancre existante - propagation FA possible)", RE_FUSE_BGID)
dump("MONO confirme MAJIC (1 SIREN >= 90%)", MONO_MAJIC, max_show=30)
dump("SOCIAL (bailleur HLM/OPH/SA HLM dominant)", SOCIAL)
dump("TERTIAIRE (usage BDNB)", TERTIAIRE)
dump("COPRO_NON_IMMAT probable (le reste)", COPRO_NON_IMMAT, max_show=30)

# Stats
print()
print("=" * 90)
print(f"BILAN TRIAGE 85 cles injectees DL")
print("=" * 90)
print(f"  RATTACHABLES RNC               : {len(RATTACHABLE_RNC):3d}")
print(f"  RE-FUSE BGID                   : {len(RE_FUSE_BGID):3d}")
print(f"  MONO confirme MAJIC            : {len(MONO_MAJIC):3d}")
print(f"  SOCIAL                         : {len(SOCIAL):3d}")
print(f"  TERTIAIRE                      : {len(TERTIAIRE):3d}")
print(f"  COPRO_NON_IMMAT probable       : {len(COPRO_NON_IMMAT):3d}")
print(f"  TOTAL                          : {len(RATTACHABLE_RNC)+len(RE_FUSE_BGID)+len(MONO_MAJIC)+len(SOCIAL)+len(TERTIAIRE)+len(COPRO_NON_IMMAT):3d} / 85")
print()
print(f"  Cache parcelles BDNB : {len(PARC_CACHE)} bgids")
print(f"  Cache RNC parcelle   : {len(RNC_CACHE)} parcelles")

# Sauvegarde detail
OUT = ROOT / "data" / "_triage_85_suffixes_dl.json"
OUT.write_text(json.dumps({
    "n_total": len(injected),
    "rattachables_rnc": [r["cle"] for r in RATTACHABLE_RNC],
    "re_fuse_bgid":     [r["cle"] for r in RE_FUSE_BGID],
    "mono_majic":       [r["cle"] for r in MONO_MAJIC],
    "social":           [r["cle"] for r in SOCIAL],
    "tertiaire":        [r["cle"] for r in TERTIAIRE],
    "copro_non_immat":  [r["cle"] for r in COPRO_NON_IMMAT],
    "detail": [
        {"cle": r["cle"], "bgid": r["bgid"], "bdnb": r["bdnb"], "usage": r["usage"],
         "parcs": r["parcs"],
         "rnc_hits": [{"immat": h[0], "nom": h[1], "tot": h[2], "hab": h[3], "in_sct": h[4]}
                      for h in r["rnc_hits"]],
         "majic_lots": r["majic_lots"], "n_sirens": r["n_sirens"],
         "top_siren": r["top_siren"], "top_lots": r["top_lots"], "top_denom": r["top_denom"],
         "pct_top": r["pct_top"], "is_tert": r["is_tert"], "is_mono": r["is_mono"],
         "is_social": r["is_social"], "bgid_parents_current": r["bgid_parents_current"]}
        for r in results
    ],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print(f"  Detail sauvegarde : {OUT.name}")
