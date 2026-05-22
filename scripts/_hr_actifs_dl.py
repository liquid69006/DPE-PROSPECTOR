#!/usr/bin/env python3
"""Liste les hr-actifs UI Dauphine-Lacassagne (vlog>0 && nb_log_bdnb>1)
croises avec qualifications KV et appairage RNC live (scan parcelle).

Step 1 : lit KV deja telecharge dans data/_kv_assign_dl.json
Step 2 : isole hr-actifs (!coproByCle && !immat && !_fa)
Step 3 : pour chaque non-qualifie, scan parcelle via caches
         _bgid_parcelle_dl.json + _scan_parc_rnc_dl.json
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"
CACHE_BG = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc["adresses"]
co  = doc["coproprietes"]
kv  = json.loads(KV.read_text(encoding="utf-8"))
assignments = kv.get("assignments") or {}
fusions     = kv.get("fusions") or {}

try:
    cache_bg = json.loads(CACHE_BG.read_text(encoding="utf-8"))
except Exception:
    cache_bg = {}
try:
    cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8"))
except Exception:
    cache_rnc = {}

def to_int(x):
    try: return int(x)
    except Exception: return 0

# Index copros par cle, par immat (pour eviter duplications)
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}
immat_secteur = {c.get("numero_immatriculation") for c in co if c.get("numero_immatriculation")}

# --- Identifier hr-actifs UI ---
hr_actifs = []
for a in ad:
    cle = a.get("cle") or ""
    if cle in co_by_cle: continue
    if a.get("numero_immatriculation"): continue
    if a.get("_fusion_auto"): continue
    if to_int(a.get("nb_ventes_logement")) <= 0: continue
    if to_int(a.get("nb_log_bdnb")) <= 1: continue
    hr_actifs.append(a)

# Tri par nb_ventes_logement decroissant (puis nb_log_bdnb desc)
hr_actifs.sort(key=lambda a: (-to_int(a.get("nb_ventes_logement")),
                               -to_int(a.get("nb_log_bdnb"))))

# --- Lyon DVF parcelle convert: 69383000XXNNNN -> 69123383XXNNNN ---
def bdnb_to_rnc(bdnb_p):
    if not bdnb_p or len(bdnb_p) < 14:
        return None
    if bdnb_p[:2] == "69" and bdnb_p[5:8] == "000":
        return "69123383" + bdnb_p[8:]
    if bdnb_p[:2] == "75" and bdnb_p[5:8] == "000":
        return "75056" + bdnb_p[2:5] + bdnb_p[8:]
    return None

def qualif_kv(cle):
    if cle in assignments:
        return assignments[cle].get("type", "?")
    if cle in fusions:
        return "fusion-src->" + fusions[cle]
    if cle in fusions.values():
        return "fusion-tgt"
    return None

def rnc_candidates(bgid):
    """Renvoie liste de copros RNC live trouvees via parcelle cache.
    Filtre celles deja dans le secteur (immat present) pour ne pas
    proposer un appairage qui existe deja."""
    parcs_bdnb = cache_bg.get(bgid) or []
    out = []
    seen = set()
    for pb in parcs_bdnb:
        pr = bdnb_to_rnc(pb)
        if not pr: continue
        hits = cache_rnc.get(pr) or []
        for h in hits:
            im = h.get("immat")
            if not im or im in seen: continue
            seen.add(im)
            in_secteur = im in immat_secteur
            out.append({
                "immat": im,
                "nom": h.get("nom",""),
                "syndic": h.get("syndic",""),
                "parcelle_rnc": pr,
                "parcelle_bdnb": pb,
                "nb_lots_total": h.get("nb_lots_total"),
                "nb_lots_habit": h.get("nb_lots_habit"),
                "ref_col": h.get("ref_match_col"),
                "in_secteur": in_secteur,
            })
    return out

# --- Affichage tableau ---
print("=" * 110)
print("HR-ACTIFS UI Dauphine-Lacassagne (vlog>0 && nb_log_bdnb>1)")
print("=" * 110)
print()
print(f"Total : {len(hr_actifs)} adresses")
print(f"KV : {len(assignments)} assignments + {len(fusions)} fusions")
print()

# Distribution KV courante
from collections import Counter
counts = Counter()
for a in hr_actifs:
    q = qualif_kv(a.get("cle") or "")
    counts[q or "(non qualifie)"] += 1
print("Distribution qualifications KV (sur les hr-actifs) :")
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {k:24s} : {v}")
print()

# Tableau detaille
print("-" * 110)
print("# | cle                              | vlog | bdnb | bgid           | majic | sci | usage           | KV")
print("-" * 110)
for i, a in enumerate(hr_actifs, 1):
    cle = a.get("cle") or ""
    vlog = to_int(a.get("nb_ventes_logement"))
    bdnb = to_int(a.get("nb_log_bdnb"))
    bg = a.get("batiment_groupe_id") or ""
    bg9 = bg[-9:] if bg else "-"
    majic = "Y" if a.get("dans_majic") else "n"
    sci = "Y" if a.get("sci_proprietaire") == "oui" else "n"
    sci_nom = a.get("sci_nom") or ""
    usage = (a.get("usage_principal_bdnb") or "")[:14]
    q = qualif_kv(cle) or "(non qualif)"
    print(f"{i:2d}| {cle:32s} | {vlog:4d} | {bdnb:4d} | ...{bg9} | {majic}     | {sci}   | {usage:15s} | {q}")
print("-" * 110)

# --- Step 3 : non-qualifies avec scan parcelle ---
non_q = [a for a in hr_actifs if not qualif_kv(a.get("cle") or "")]
print()
print("=" * 110)
print(f"STEP 3 - Appairage RNC live pour {len(non_q)} non-qualifies")
print("=" * 110)
print()
print("(via caches _bgid_parcelle_dl.json + _scan_parc_rnc_dl.json)")
print()

no_cache_count = 0
no_hit_count = 0
hit_count = 0

for i, a in enumerate(non_q, 1):
    cle = a.get("cle") or ""
    bgid = a.get("batiment_groupe_id") or ""
    bg9 = bgid[-9:] if bgid else "-"
    vlog = to_int(a.get("nb_ventes_logement"))
    bdnb = to_int(a.get("nb_log_bdnb"))
    sci = a.get("sci_nom") or ""
    usage = (a.get("usage_principal_bdnb") or "")[:20]

    print(f"  [{i:2d}] {cle:32s}  vlog={vlog} bdnb={bdnb}  bgid=...{bg9}  usage={usage}")
    if sci:
        print(f"        SCI: {sci}")

    if not bgid:
        print("        -> Pas de bgid (orpheline) : appairage impossible via parcelle")
        no_cache_count += 1
        print()
        continue

    if bgid not in cache_bg:
        print(f"        -> bgid PAS DANS CACHE _bgid_parcelle_dl ; necessite scan parcelle live")
        no_cache_count += 1
        print()
        continue

    parcs = cache_bg[bgid]
    cands = rnc_candidates(bgid)

    if not cands:
        print(f"        Parcelles BDNB : {parcs}")
        print(f"        -> 0 candidat RNC sur ces parcelles (scan deja effectue)")
        no_hit_count += 1
    else:
        hit_count += 1
        print(f"        Parcelles BDNB : {parcs}")
        new_cands = [c for c in cands if not c["in_secteur"]]
        in_cands  = [c for c in cands if c["in_secteur"]]
        if new_cands:
            print(f"        >>> {len(new_cands)} CANDIDAT(S) RNC HORS-SECTEUR (potentiel INJECT/RE-FUSE) :")
            for c in new_cands:
                print(f"            {c['immat']}  '{c['nom'][:38]}'  lots_tot={c['nb_lots_total']} hab={c['nb_lots_habit']}  cad={c['ref_col']}={c['parcelle_rnc']}")
                if c['syndic']:
                    print(f"              syndic: {c['syndic'][:60]}")
        if in_cands:
            print(f"        ... {len(in_cands)} candidat(s) deja-secteur (ne pas re-injecter)")
            for c in in_cands:
                print(f"            {c['immat']} (deja dans coproprietes[])  '{c['nom'][:35]}'")
    print()

# --- Mecanisme suggere par categorie ---
print("=" * 110)
print("RESUME APPAIRAGE")
print("=" * 110)
print(f"  Non-qualifies analyses        : {len(non_q)}")
print(f"  Avec candidat RNC hors-secteur: {hit_count}")
print(f"  Sans candidat (scan vide)     : {no_hit_count}")
print(f"  Sans bgid OU bgid pas en cache: {no_cache_count}")
