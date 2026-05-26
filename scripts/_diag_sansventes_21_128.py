#!/usr/bin/env python3
"""Diag 'Sans ventes' DL adresses 21-128 (lecture seule).

Reproduit le filtre UI 'Sans ventes' (index.html ligne 4928) :
  - exclu social / bureaux / mono (KV)
  - type valide : copro RNC (coproByCle ou immat orphelin) OU copro_non_immat
    OU mixte (KV)
  - 0 vente logement strict (own nb_ventes_logement + ventes_par_an_logement)
  - 0 vente fused mergedInto (KV fusions) ni autoMerged (BDNB FA)

Trie par nb_log DESC, saute top 20 (deja diagnostique), traite les 108
restantes.

Pour chaque cle, sonde mutations DVF 2021-2025 par 3 methodes :
  M1 EXACT     : DVF (No voie + B/T/Q) + Voie normalisee
  M2 APPROCHE  : DVF (No voie +/-1) + meme Voie
  M3 BGID      : autres adresses light meme batiment_groupe_id
                 -> somme nb_ventes_logement (5 ans, deja pre-agrege)

Classification :
  PURE_0          : M1.Apt+Maison = 0 ET M2.Apt+Maison = 0 ET M3.vlog = 0
  VOISIN          : M1.Apt+Maison = 0 ET M2.Apt+Maison > 0 ET M3.vlog = 0
  BGD_PARTAGE     : M3.vlog > 0  (autres adresses meme bgid qui vendent)
  LOCAL_COMMERCIAL: M1.Local commercial > 0 mais Apt+Maison = 0

Affiche : BGD_PARTAGE + LOCAL_COMMERCIAL + tout autre cas
non-PURE_0/VOISIN, trie par nb_log DESC.

Sources lecture seule :
  - LIGHT : data/secteur_dauphine_lacassagne_light.json
  - KV    : API live /secteur-assignments/dauphine-lacassagne
  - DVF   : C:/Users/Station 5/dvf_dauphine_lacassagne.json
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
TOKEN = os.environ.get("DPE_JWT") or ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ANS = ("2021", "2022", "2023", "2024", "2025")


def to_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def to_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


# ---------- 1. KV live ----------
try:
    req = urllib.request.Request(
        f"{API}/secteur-assignments/dauphine-lacassagne",
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": UA,
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        kv = json.loads(r.read())
    assignments = kv.get("assignments") or {}
    fusions = kv.get("fusions") or {}
    print(f"[KV live] assignments={len(assignments)}  fusions={len(fusions)}")
except Exception as e:
    print(f"[KV ERR] {e} -- fallback assignments=fusions={{}}")
    assignments, fusions = {}, {}


# ---------- 2. light ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}
by_cle = {(a.get("cle") or ""): a for a in ad}
print(f"[light]   adresses={len(ad)}  coproprietes={len(co)}")


# ---------- 3. mergedInto + autoMerged ----------
# vpaOf strict (5-year ventes_par_an_logement)
def vpa(a):
    return a.get("ventes_par_an_logement") or {}


merged_into = {}
fused_src = set()
for src, dst in fusions.items():
    sa = by_cle.get(src)
    if not sa or not dst or src == dst:
        continue
    fused_src.add(src)
    m = merged_into.setdefault(dst, {"count": 0, "ventes": {}})
    m["count"] += 1
    for y in ANS:
        m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

auto_merged = {}
for a in ad:
    cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
    if a.get("_fusion_auto") and cible and a.get("cle") not in fused_src:
        fused_src.add(a.get("cle"))
        am = auto_merged.setdefault(cible, {"count": 0, "ventes": {}})
        am["count"] += 1
        for y in ANS:
            am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)


def kv_type(cle):
    return ((assignments.get(cle) or {}).get("type")) or None


# ---------- 4. filtre 'Sans ventes' ----------
def sans_ventes_ok(a):
    cle = a.get("cle") or ""
    # UI render line 4898 : fusedSrc adresses excluded avant filtre
    if cle in fused_src:
        return False
    t = kv_type(cle)
    if t in ("social", "bureaux", "mono"):
        return False
    is_copro_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
    is_copro_ni = (t == "copro_non_immat")
    is_mixte = (t == "mixte")
    if not (is_copro_rnc or is_copro_ni or is_mixte):
        return False
    own_n = to_int(a.get("nb_ventes_logement"))
    if own_n > 0:
        return False
    own_vpa = a.get("ventes_par_an_logement") or {}
    if any((own_vpa.get(y) or 0) > 0 for y in ANS):
        return False
    mi = merged_into.get(cle) if is_copro_rnc else None
    if mi and any((mi["ventes"].get(y) or 0) > 0 for y in ANS):
        return False
    am = auto_merged.get(cle)
    if am and any((am["ventes"].get(y) or 0) > 0 for y in ANS):
        return False
    return True


# nb_log effectif (cf renderSecteur)
def eff_log(a):
    cle = a.get("cle") or ""
    if cle in co_by_cle:
        c = co_by_cle[cle]
        v = c.get("nb_lots_habitation")
        if v is not None:
            return to_int(v)
    return to_int(a.get("nb_log_bdnb"))


candidates = [a for a in ad if sans_ventes_ok(a)]
candidates.sort(key=lambda a: (-eff_log(a), a.get("cle") or ""))
print(f"[filtre]  Sans ventes total = {len(candidates)}")
TOP_N = 20
print(f"[skip]    top {TOP_N} deja diagnostiques -> reste {max(0, len(candidates)-TOP_N)}")


# ---------- 5. DVF index ----------
print("[dvf]     chargement...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
print(f"[dvf]     mutations = {len(dvf)}")


def norm_voie(s):
    if not s:
        return ""
    s = str(s).upper().strip()
    s = s.replace("-", " ").replace("'", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bSAINTE\b", "STE", s)
    s = re.sub(r"\bSAINT\b", "ST", s)
    return s.strip()


# Indexer DVF par voie normalisee
dvf_by_voie = defaultdict(list)
for m in dvf:
    v = norm_voie(m.get("Voie") or "")
    if v:
        dvf_by_voie[v].append(m)


def code_local(m):
    """1=Maison, 2=Apt, 3=Dep, 4=Local commercial."""
    return (m.get("Code type local") or "").strip()


def parse_cle(cle):
    """Decompose 'NUM[B...]|TYPE|VOIE' -> (num_int, suffix, voie_norm)."""
    parts = cle.split("|")
    if len(parts) != 3:
        return None, "", ""
    num_part = parts[0].strip().upper()
    voie_n = norm_voie(parts[2])
    m = re.match(r"^(\d+)([A-Z]*)$", num_part)
    if not m:
        return None, "", voie_n
    return int(m.group(1)), m.group(2), voie_n


def dvf_match(num_int, suffix, voie_n, tol=0):
    """Retourne dict {1: count_maison, 2: count_apt, 3: count_dep, 4: count_loc}
    sur DVF filtre par (no_voie, B/T/Q) ; tol=0 exact, tol=1 voisin +/-1."""
    out = {"1": 0, "2": 0, "3": 0, "4": 0}
    for m in dvf_by_voie.get(voie_n, []):
        no = (m.get("No voie") or "").strip()
        if not no:
            continue
        try:
            no_int = int(no)
        except Exception:
            continue
        if tol == 0:
            if no_int != num_int:
                continue
            btq = (m.get("B/T/Q") or "").strip().upper()
            if (btq or "") != (suffix or ""):
                continue
        else:
            if abs(no_int - num_int) != 1:
                continue
        c = code_local(m)
        if c in out:
            out[c] += 1
    return out


# ---------- 6. bgid sharing index ----------
by_bgid = defaultdict(list)
for a in ad:
    bg = a.get("batiment_groupe_id") or ""
    if bg:
        by_bgid[bg].append(a)


def m3_bgid(a):
    """Somme nb_ventes_logement des autres adresses meme bgid (5 ans, light)."""
    bg = a.get("batiment_groupe_id") or ""
    if not bg:
        return 0, []
    sib = []
    tot = 0
    for o in by_bgid[bg]:
        if (o.get("cle") or "") == (a.get("cle") or ""):
            continue
        v = to_int(o.get("nb_ventes_logement"))
        if v > 0:
            tot += v
            sib.append((o.get("cle"), v, bool(o.get("_fusion_auto"))))
    return tot, sib


# ---------- 7. boucle classification ----------
results = []
for idx, a in enumerate(candidates[TOP_N:], start=TOP_N + 1):
    cle = a.get("cle") or ""
    num_int, suffix, voie_n = parse_cle(cle)
    if num_int is None:
        results.append({
            "rank": idx, "cle": cle, "nb_log": eff_log(a),
            "klass": "CLE_MALFORMEE", "m1": None, "m2": None,
            "m3_tot": 0, "m3_sib": [],
            "bgid": a.get("batiment_groupe_id"),
        })
        continue
    m1 = dvf_match(num_int, suffix, voie_n, tol=0)
    m2 = dvf_match(num_int, suffix, voie_n, tol=1)
    m3_tot, m3_sib = m3_bgid(a)

    m1_log = m1["1"] + m1["2"]
    m2_log = m2["1"] + m2["2"]
    m1_com = m1["4"]

    if m3_tot > 0:
        klass = "BGD_PARTAGE"
    elif m1_log == 0 and m2_log == 0 and m1_com > 0:
        klass = "LOCAL_COMMERCIAL"
    elif m1_log == 0 and m2_log > 0:
        klass = "VOISIN"
    elif m1_log == 0 and m2_log == 0 and m1_com == 0:
        klass = "PURE_0"
    else:
        klass = "ANOMALIE"  # m1_log > 0 mais filtre l'a laisse passer
    results.append({
        "rank": idx, "cle": cle, "nb_log": eff_log(a),
        "klass": klass, "m1": m1, "m2": m2, "m1_log": m1_log,
        "m2_log": m2_log, "m1_com": m1_com,
        "m3_tot": m3_tot, "m3_sib": m3_sib,
        "bgid": a.get("batiment_groupe_id") or "",
        "immat": a.get("numero_immatriculation"),
        "copro_immat": (co_by_cle.get(cle) or {}).get("numero_immatriculation"),
        "copro_nom": (co_by_cle.get(cle) or {}).get("nom_copropriete"),
    })


# ---------- 8. resumes ----------
from collections import Counter
ct = Counter(r["klass"] for r in results)
print()
print("=" * 78)
print(f"  Classification 108 candidates (rangs 21-{TOP_N+len(results)}) :")
print("=" * 78)
for k, n in ct.most_common():
    print(f"    {k:20s} : {n}")
print()


# ---------- 9. detail BGD_PARTAGE + anomalies ----------
def fmt_m(m):
    if not m:
        return "-"
    return f"M=1:{m['1']} 2:{m['2']} 3:{m['3']} 4:{m['4']}"


def voie_of(cle):
    p = cle.split("|")
    return p[2] if len(p) == 3 else cle


# BGD_PARTAGE
bgd = sorted([r for r in results if r["klass"] == "BGD_PARTAGE"],
             key=lambda r: -r["nb_log"])
print("=" * 78)
print(f"  BGD_PARTAGE ({len(bgd)} cas) - tri nb_log DESC")
print("=" * 78)
for r in bgd:
    immat = r["copro_immat"] or r["immat"] or "-"
    nom = (r["copro_nom"] or "")[:35]
    print(f"\n  #{r['rank']:3d}  {r['cle']:34s}  nb_log={r['nb_log']:3d}  bgid=...{(r['bgid'] or '')[-9:]}")
    print(f"        copro={immat} '{nom}'")
    print(f"        M1 exact {fmt_m(r['m1'])}   M2 +/-1 {fmt_m(r['m2'])}")
    print(f"        M3 bgid sum_vlog={r['m3_tot']} sibs:")
    for cle_s, vlog, fa in sorted(r["m3_sib"], key=lambda x: -x[1])[:10]:
        flag = " FA" if fa else ""
        print(f"          - {cle_s:34s} vlog={vlog}{flag}")

# LOCAL_COMMERCIAL
loc = sorted([r for r in results if r["klass"] == "LOCAL_COMMERCIAL"],
             key=lambda r: -r["nb_log"])
print()
print("=" * 78)
print(f"  LOCAL_COMMERCIAL ({len(loc)} cas) - mutations Local commercial uniquement")
print("=" * 78)
for r in loc:
    immat = r["copro_immat"] or r["immat"] or "-"
    nom = (r["copro_nom"] or "")[:35]
    print(f"\n  #{r['rank']:3d}  {r['cle']:34s}  nb_log={r['nb_log']:3d}  bgid=...{(r['bgid'] or '')[-9:]}")
    print(f"        copro={immat} '{nom}'")
    print(f"        M1 exact {fmt_m(r['m1'])}   M2 +/-1 {fmt_m(r['m2'])}")

# ANOMALIE (M1.Apt+Maison > 0 mais filtre a laisse passer = incoherence)
ano = sorted([r for r in results if r["klass"] == "ANOMALIE"],
             key=lambda r: -r["nb_log"])
if ano:
    print()
    print("=" * 78)
    print(f"  ANOMALIE ({len(ano)} cas) - M1 Apt+Maison > 0 mais 0 ventes light "
          "(incoherence DVF/light)")
    print("=" * 78)
    for r in ano:
        print(f"\n  #{r['rank']:3d}  {r['cle']:34s}  nb_log={r['nb_log']:3d}  bgid=...{(r['bgid'] or '')[-9:]}")
        print(f"        M1 exact {fmt_m(r['m1'])}   M2 +/-1 {fmt_m(r['m2'])}   M3 bgid {r['m3_tot']}")

# CLE_MALFORMEE
cma = [r for r in results if r["klass"] == "CLE_MALFORMEE"]
if cma:
    print()
    print("=" * 78)
    print(f"  CLE_MALFORMEE ({len(cma)}) - num inextractable du cle")
    print("=" * 78)
    for r in cma:
        print(f"  #{r['rank']:3d}  '{r['cle']}'  nb_log={r['nb_log']}  bgid=...{(r['bgid'] or '')[-9:]}")

print()
print("=" * 78)
print(f"  PURE_0    : {ct.get('PURE_0', 0)} cibles prospection (silencieux)")
print(f"  VOISIN    : {ct.get('VOISIN', 0)} cas voisin +/-1 vend (silencieux)")
print("=" * 78)
