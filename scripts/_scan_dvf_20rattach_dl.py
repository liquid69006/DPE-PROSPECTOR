#!/usr/bin/env python3
"""Scan DVF sur les RATTACHABLES non qualifies KV DL (lecture seule).

Filtre triage : type=rattachable_rnc + KV=non-qualifie.
Pour chaque cle, scan DVF par (num + indice + voie) + lookup copro RNC mere.
Suggere une qualif KV.
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

TV_MAP = {"RUE":"RUE","AV":"AVENUE","CRS":"COURS","BD":"BOULEVARD","PL":"PLACE",
          "PAS":"PASSAGE","IMP":"IMPASSE","RTE":"ROUTE","ALL":"ALLEE","QUAI":"QUAI",
          "AVENUE":"AVENUE","COURS":"COURS","PASSAGE":"PASSAGE","PLACE":"PLACE"}
ARTICLES = re.compile(r"^(?:DU|DE|DES|LA|LE|L'|D')\s+")

BAILLEURS_SOCIAUX = [
    "CDC HABITAT","ALLIADE","GRAND LYON HABITAT","GRANDLYON HABITAT",
    "OPH ","OPH DE","OPHLM","HBM","HLM","HABITAT ET HUMANIS","DYNACITE",
    "EST METROPOLE HABITAT","SCIC HABITAT","ICF HABITAT","RHONE SAONE HABITAT",
    "ADOMA","FONCIERE LOGEMENT","ERILIA","CDC HAB","FRANCE LOGEMENT","SCI 3F",
    "IMMOBILIERE 3F","ALILA","NEXITY DOMAINES","SOLLAR","BATIGERE","NOVEDIS",
    "FREHA","SCIC RHONE-ALPES","SOCIETE LYONNAISE","OPHEOR","OPAC",
    "IMMOBILIERE RHONE ALPES","ICF SUD-EST","FONCIERE VESTA",
    "SA HLM","SA D'HLM","SA DE HLM","FONCIERE D'HABITAT ET HUM",
    "3F RESIDENCES","ACTION SOCIALE","IN'LI","HOSPICES CIVILS",
    "SA DE CONSTRUCTION DE LA VILLE","SEM DE CONSTRUCTION","COMMUNE DE LYON",
    "COMMUNAUTE URBAINE DE LYON","DEPARTEMENT DU RHONE","FONDATION ARALIS",
    "METROPOLE DE LYON",
]
def is_bs(d):
    if not d: return False
    s = str(d).upper()
    return any(k in s for k in BAILLEURS_SOCIAUX)

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
RATTACH = set(triage.get("rattachables_rnc") or [])
print(f"Triage rattachables_rnc : {len(RATTACH)}")

kv = {}
if KV_LOCAL.exists():
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8")).get("assignments") or {}
print(f"KV local : {len(kv)} assigns")

# Filtre : non qualifies
NON_QUALIF = sorted([c for c in RATTACH if c not in kv])
print(f"RATTACHABLES non qualifies KV : {len(NON_QUALIF)}")

# Light + copros mere
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
by_cle = {a.get("cle"): a for a in doc["adresses"]}
co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"] if c.get("numero_immatriculation")}

# DVF
print(f"Chargement DVF ...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
dvf_idx = defaultdict(list)
for m in dvf:
    no = str(m.get("No voie","") or "").strip().lstrip("0")
    bt = str(m.get("B/T/Q","") or "").strip().upper()
    tv = TV_MAP.get(str(m.get("Type de voie","") or "").strip().upper(), "")
    vo = norm_voie(m.get("Voie"))
    if not (no and tv and vo): continue
    dvf_idx[(no, bt, tv, vo)].append(m)
print(f"  {len(dvf)} mutations, {len(dvf_idx)} adresses uniques\n")

# --- Scan ---
results = []
for cle in NON_QUALIF:
    parsed = parse_cle(cle)
    if not parsed: continue
    num, suffix, tv, voie = parsed
    voie_n = norm_voie(voie)
    muts = dvf_idx.get((num, suffix, tv, voie_n)) or []
    ventes_log = [m for m in muts
                  if (m.get("Nature mutation","") or "").strip() == "Vente"
                  and (m.get("Type local","") or "").strip() in ("Appartement","Maison")]
    by_mut = defaultdict(list)
    for m in ventes_log:
        by_mut[(m.get("Date mutation"), m.get("No disposition"), m.get("Valeur fonciere"))].append(m)
    # Adresse light
    a = by_cle.get(cle, {})
    immat = a.get("numero_immatriculation")
    co_src = co_by_immat.get(immat, {}) if immat else {}
    results.append({
        "cle": cle,
        "nb_ventes": len(by_mut),
        "by_mut": by_mut,
        "immat": immat,
        "co_nom": co_src.get("nom_copropriete"),
        "co_syndic": co_src.get("syndic"),
        "co_hab": co_src.get("nb_lots_habitation"),
        "co_taux": co_src.get("taux_rotation_5ans"),
        "co_classement": co_src.get("classement_rotation"),
    })

results.sort(key=lambda r: -r["nb_ventes"])

# --- Suggestion qualif ---
def suggest(r):
    n = r["nb_ventes"]
    bs = is_bs(r["co_syndic"]) or is_bs(r["co_nom"])
    taux = r["co_taux"] or 0
    cls = r["co_classement"] or ""
    if n == 0:
        if bs: return "social", "0 vente + bailleur social → locatif pur"
        return "copro_non_immat", "0 vente + copro RNC → SDC standard"
    if n >= 5:
        return "copro_non_immat", f"{n} ventes actives → copro mixte (meme si bailleur social)"
    if n >= 3:
        if bs and "Tres" not in cls and taux < 15:
            return "social", f"{n} ventes mais bailleur social modere (taux {taux}%)"
        return "copro_non_immat", f"{n} ventes + activite -> copro mixte"
    # 1-2 ventes
    if bs and (taux or 0) < 10:
        return "social", f"{n} ventes faibles + bailleur social (taux {taux}%) -> locatif majoritaire"
    return "copro_non_immat", f"{n} ventes + non bailleur social -> SDC standard"

print("=" * 90)
print(f"SCAN DVF - 20 RATTACHABLES non qualifies KV DL")
print("=" * 90)
for r in results:
    qualif, just = suggest(r)
    bs_flag = " [BS]" if (is_bs(r["co_syndic"]) or is_bs(r["co_nom"])) else ""
    print()
    print(f"  {r['cle']:36s}  ventes={r['nb_ventes']:>2d}  immat={r['immat']}")
    print(f"    copro : '{(r['co_nom'] or '?')[:35]}'{bs_flag}  syndic='{(r['co_syndic'] or '-')[:40]}'")
    print(f"    {r['co_hab']} hab habit. | taux {r['co_taux']}% | classement={r['co_classement']!r}")
    if r["nb_ventes"]:
        for k in sorted(r["by_mut"].keys())[-5:]:  # 5 dernieres
            date, dispo, val = k
            v = fnum(val)
            lst = r["by_mut"][k]
            s_bati = sum(int(m.get("Surface reelle bati","0") or 0) for m in lst)
            pieces = sum(int(m.get("Nombre pieces principales","0") or 0) for m in lst)
            v_str = f"{v:>10,.0f}".replace(",", " ") if v else "         ?"
            print(f"      {date}  val={v_str} EUR  surf={s_bati}m2 pieces={pieces}  n_lots={len(lst)}")
    print(f"    >>> SUGGESTION : {qualif:18s}  ({just})")

# Bilan suggestions
print()
print("=" * 90)
print(f"BILAN SUGGESTIONS")
print("=" * 90)
sugg_dist = defaultdict(list)
for r in results:
    qualif, _ = suggest(r)
    sugg_dist[qualif].append(r["cle"])
for qualif, cles in sorted(sugg_dist.items()):
    print()
    print(f"  {qualif} ({len(cles)}) :")
    for c in cles:
        print(f"    - {c}")

# Stats globales
print()
print(f"  Total : {len(results)} cles | total ventes : {sum(r['nb_ventes'] for r in results)}")
print("=" * 90)
