#!/usr/bin/env python3
"""Scan DVF sur les 85 cles suffixees DL (lecture seule).

Pour chaque cle suffixee, cherche mutations DVF par (No voie + B/T/Q + Voie norm).
Affiche cles avec >= 1 vente logement (Appartement/Maison + Nature='Vente').

Source : data/_triage_85_suffixes_dl.json + dvf_dauphine_lacassagne.json + KV local.
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","BD":"BOULEVARD","PL":"PLACE",
          "PAS":"PASSAGE","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI",
          "AVENUE":"AVENUE","COURS":"COURS","PASSAGE":"PASSAGE","PLACE":"PLACE"}

ARTICLES = re.compile(r"^(?:DU|DE|DES|LA|LE|L'|D')\s+")

def norm_voie(s):
    if not s: return ""
    s = str(s).upper().strip()
    s = (s.replace("É","E").replace("È","E").replace("Ê","E")
           .replace("À","A").replace("Â","A").replace("Î","I").replace("Ô","O")
           .replace("Û","U").replace("Ç","C"))
    s = re.sub(r"\bSAINTE\b","STE", s)
    s = re.sub(r"\bSAINT\b","ST", s)
    s = s.replace("-"," ").replace("'"," ")
    s = re.sub(r"\s+"," ", s).strip()
    while True:
        new = ARTICLES.sub("", s)
        if new == s: break
        s = new
    return s

def parse_cle(cle):
    m = re.match(r"^(\d+)([A-Z]*)\|([A-Z]+)\|(.+)$", cle)
    if not m: return None
    return m.group(1), m.group(2), m.group(3), m.group(4)

def fnum(v):
    if v is None: return None
    s = str(v).strip().replace(" ","").replace(",",".")
    try: return float(s)
    except: return None

# --- Charge ---
triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
SUFF_CLES = [d["cle"] for d in (triage.get("detail") or [])]
print(f"Suffixes a scanner : {len(SUFF_CLES)}")

kv = {}
if KV_LOCAL.exists():
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8")).get("assignments") or {}

print(f"Chargement DVF ...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
print(f"  {len(dvf)} mutations brutes")

# Index DVF par (num, suffix, tv_norm, voie_norm)
dvf_idx = defaultdict(list)
for m in dvf:
    no = str(m.get("No voie","") or "").strip().lstrip("0")
    bt = str(m.get("B/T/Q","") or "").strip().upper()
    tv = TV_MAP.get(str(m.get("Type de voie","") or "").strip().upper(), "")
    vo = norm_voie(m.get("Voie"))
    if not (no and tv and vo): continue
    dvf_idx[(no, bt, tv, vo)].append(m)
print(f"  Indexes : {len(dvf_idx)} adresses uniques")

# --- Scan ---
results = []
for cle in SUFF_CLES:
    parsed = parse_cle(cle)
    if not parsed: continue
    num, suffix, tv, voie = parsed
    voie_n = norm_voie(voie)
    muts = dvf_idx.get((num, suffix, tv, voie_n)) or []
    if not muts: continue
    # Filtre : ventes logement (Vente + Appartement|Maison)
    ventes_log = [m for m in muts
                  if (m.get("Nature mutation","") or "").strip() == "Vente"
                  and (m.get("Type local","") or "").strip() in ("Appartement","Maison")]
    # Aussi compter mutations distinctes (date+disposition+valeur)
    mut_keys_log = {(m.get("Date mutation"), m.get("No disposition"), m.get("Valeur fonciere"))
                    for m in ventes_log}
    if not mut_keys_log: continue
    # Aggregat par mutation
    by_mut = defaultdict(list)
    for m in ventes_log:
        by_mut[(m.get("Date mutation"), m.get("No disposition"), m.get("Valeur fonciere"))].append(m)
    results.append({
        "cle": cle,
        "nb_ventes": len(by_mut),
        "nb_appart_lots": len(ventes_log),
        "kv": kv.get(cle),
        "by_mut": by_mut,
    })

results.sort(key=lambda r: -r["nb_ventes"])
print()
print("=" * 90)
print(f"SCAN DVF - 85 suffixes DL : {len(results)} cles avec >= 1 vente logement")
print("=" * 90)
for r in results:
    print()
    kv_str = ""
    if r["kv"]:
        kv_str = f"  KV={r['kv'].get('type','?') if isinstance(r['kv'],dict) else r['kv']}"
    print(f"  {r['cle']:36s}  ventes={r['nb_ventes']:>2d}  appart_lots={r['nb_appart_lots']}{kv_str}")
    for k, lst in sorted(r["by_mut"].items()):
        date, dispo, val = k
        v = fnum(val)
        # Type lot first one
        tl = lst[0].get("Type local","?")
        n_pieces = sum(int(m.get("Nombre pieces principales","0") or 0) for m in lst)
        s_bati = sum(int(m.get("Surface reelle bati","0") or 0) for m in lst)
        lots = [m.get("1er lot","") for m in lst if m.get("1er lot","")]
        v_str = f"{v:>10,.0f}".replace(",", " ") if v is not None else "         ?"
        print(f"      {date}  val={v_str} EUR  type={tl:11s}  n_lots={len(lst)} surf={s_bati}m2 pieces={n_pieces}  lots#={','.join(lots[:3])}")

# Summary
print()
print("=" * 90)
total_ventes = sum(r["nb_ventes"] for r in results)
print(f"BILAN : {len(results)} cles avec ventes, {total_ventes} ventes logement total")
print(f"  Distribution KV des cles avec ventes :")
kv_dist = defaultdict(int)
for r in results:
    typ = (r["kv"].get("type") if isinstance(r["kv"], dict) else r["kv"]) or "(non qualifie)"
    kv_dist[typ] += 1
for t, n in sorted(kv_dist.items(), key=lambda x: -x[1]):
    print(f"    {t:24s} : {n}")
print("=" * 90)
