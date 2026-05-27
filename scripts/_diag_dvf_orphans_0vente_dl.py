#!/usr/bin/env python3
"""Diag DVF orphelines sur adresses DL a 0 vente logement (lecture seule).

CONTEXTE : la jointure DVF->adresse light est faite par libelle adresse
normalise (NUM[BTQ]|TYPE|VOIE), fidelite ~94.7%. Des ventes existent
peut-etre dans dvf_dauphine_lacassagne.json brut mais ne sont pas
jointes a ces adresses (suffixes B/T/Q orphelins, voies tronquees,
voisins multi-bgid).

ETAPES :
  1. Population : adresses light avec nb_ventes_logement == 0
  2. Recherche orphelines : ELARGI cle (sans B/T/Q, ortho tolerante,
     voisin +/-2)
  3. Sous-classification residu via MAJIC (social/mono/anomalie)
  4. 3 blocs : [A] orphelines recuperables  [B] 0-vente explique
     [C] anomalie residuelle inexpliquee

LECTURE SEULE. Aucun patch ni modif du light.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

ANS = ("2021", "2022", "2023", "2024", "2025")

# Memes regles que fix_taux_logement.py pour reproduire la normalisation
ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else ""


def parse_cle_light(cle):
    """'12T|RUE|GUILLOUD' -> (num_base='12', suffix='T', voie_toks)."""
    p = cle.split("|")
    if len(p) != 3:
        return None
    raw = p[0].strip().upper()
    m = re.match(r"^(\d+)([A-Z]*)$", raw)
    if not m:
        return None
    return m.group(1), m.group(2), toks(p[2])


def yr(m):
    d = m.get("Date mutation") or ""
    return d[-4:] if len(d) >= 4 else "?"


def is_logement(m):
    """Code type local : 1=Maison, 2=Appartement. On garde Apt+Maison."""
    return str(m.get("Code type local") or "").strip() in ("1", "2")


# ---------- 1. Population ----------
print("=" * 78)
print("DIAG DVF ORPHELINES sur 0-vente DL  (lecture seule)")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}

# KV local pour reproduire le filtre 'Sans ventes' UI
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
fusions_kv = kv.get("fusions") or {}
print(f"\n[0] KV local : {len(assigns)} assignments, "
      f"{len(fusions_kv)} fusions manuelles")


def kv_type(cle):
    return ((assigns.get(cle) or {}).get("type")) or ""


# ============================================================
# REPLIQUE EXACTE DU FILTRE 'Sans ventes' UI (index.html ligne 4928-4948)
# ============================================================

# vpaOf (strict) : ventes_par_an_logement
def vpa(a):
    return a.get("ventes_par_an_logement") or {}


# fusedSrc + mergedInto (KV fusions manuelles)
merged_into = {}
fused_src = set()
for src, dst in fusions_kv.items():
    sa = by_cle.get(src)
    if not sa or not dst or src == dst:
        continue
    fused_src.add(src)
    m = merged_into.setdefault(dst, {"ventes": {}, "srcs": []})
    m["srcs"].append(src)
    for y in ANS:
        m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

# autoMerged (BDNB _fusion_auto + _fusion_cible/_fusion_auto_target)
auto_merged = {}
for a in ad:
    cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
    cle = a.get("cle") or ""
    if a.get("_fusion_auto") and cible and cle not in fused_src:
        fused_src.add(cle)
        am = auto_merged.setdefault(cible, {"ventes": {}, "srcs": []})
        am["srcs"].append(cle)
        for y in ANS:
            am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

print(f"    fused_src (FA + KV fusions) : {len(fused_src)}")
print(f"    mergedInto recipients        : {len(merged_into)}")
print(f"    autoMerged recipients        : {len(auto_merged)}")


# Adresses light a 0 vente logement, filtre Sans ventes UI complet :
#   - exclu fusedSrc (FA + KV fusions sources)
#   - exclu type KV in {social, bureaux, mono}
#   - inclut type valide : copro_rnc (coproByCle ou immat) OU
#     copro_non_immat OU mixte (autres types -> exclu)
#   - 0 vente logement own (nb_ventes_logement + ventes_par_an_logement)
#   - 0 vente mergedInto.ventes (KV fusions)
#   - 0 vente autoMerged.ventes (BDNB FA -> ancre)
pop = []
exclu_fa = exclu_kv_tag = exclu_no_type = exclu_has_vente = 0
exclu_merged_into = exclu_auto_merged = 0
for a in ad:
    cle = a.get("cle") or ""
    if cle in fused_src:
        exclu_fa += 1
        continue
    t = kv_type(cle)
    if t in ("social", "bureaux", "mono"):
        exclu_kv_tag += 1
        continue
    is_copro_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
    is_copro_ni = (t == "copro_non_immat")
    is_mixte = (t == "mixte")
    if not (is_copro_rnc or is_copro_ni or is_mixte):
        exclu_no_type += 1
        continue
    vlog = int(a.get("nb_ventes_logement") or 0)
    if vlog > 0:
        exclu_has_vente += 1
        continue
    vpa_log = a.get("ventes_par_an_logement") or {}
    if any((vpa_log.get(y) or 0) > 0 for y in ANS):
        exclu_has_vente += 1
        continue
    # mergedInto (KV fusions) - seulement si copro RNC
    if is_copro_rnc:
        mi = merged_into.get(cle)
        if mi and any((mi["ventes"].get(y) or 0) > 0 for y in ANS):
            exclu_merged_into += 1
            continue
    # autoMerged (BDNB FA)
    am = auto_merged.get(cle)
    if am and any((am["ventes"].get(y) or 0) > 0 for y in ANS):
        exclu_auto_merged += 1
        continue
    pop.append(a)

n_pop = len(pop)
sum_log = sum(int(a.get("nb_log_bdnb") or 0) for a in pop)
print(f"\n[1] Population 0-vente DL (filtre 'Sans ventes' UI COMPLET)")
print(f"    adresses retenues             : {n_pop}")
print(f"    somme nb_log_bdnb             : {sum_log} logements")
print(f"    exclus fusedSrc (FA+KV)       : {exclu_fa}")
print(f"    exclus social/bureaux/mono    : {exclu_kv_tag}")
print(f"    exclus type non valide        : {exclu_no_type}")
print(f"    exclus nb_ventes_log>0 propre : {exclu_has_vente}")
print(f"    exclus mergedInto (KV)        : {exclu_merged_into}")
print(f"    exclus autoMerged (BDNB FA)   : {exclu_auto_merged}")

# ---------- 2. Index DVF brut ----------
print("\n[2] Chargement DVF brut...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))
print(f"    mutations brutes : {len(dvf)}")

# Index DVF : (num_str, voie_toks) -> list[mutations]
dvf_by_key = defaultdict(list)
# Index DVF logement uniquement (Apt + Maison) : (num_str, voie_toks)
dvf_log_by_key = defaultdict(list)
# Index DVF par voie_toks pour scan voisins
dvf_by_voie_toks = defaultdict(list)
for m in dvf:
    nv = numof(m.get("No voie"))
    if not nv:
        continue
    vt = toks(m.get("Voie") or "")
    if not vt:
        continue
    dvf_by_key[(nv, vt)].append(m)
    dvf_by_voie_toks[vt].append(m)
    if is_logement(m):
        dvf_log_by_key[(nv, vt)].append(m)


def dedup_mutations(rows):
    """Dedup par (Date mutation, No disposition, Valeur fonciere) = une
    mutation unique peut apparaitre N fois (1 ligne par lot)."""
    seen = set()
    out = []
    for m in rows:
        sig = (m.get("Date mutation"), m.get("No disposition"),
               m.get("Valeur fonciere"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(m)
    return out


# ---------- 3. Match elargi par adresse ----------
print("\n[3] Match DVF elargi (sans-suffixe, ortho-tolerant, voisin +/-2)...")

records = []  # par adresse : tous les infos pour classement
for a in pop:
    cle = a["cle"]
    parsed = parse_cle_light(cle)
    bdnb = int(a.get("nb_log_bdnb") or 0)
    bg = a.get("batiment_groupe_id") or ""
    usage = a.get("usage_principal_bdnb") or ""
    is_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
    immat = (co_by_cle.get(cle) or {}).get("numero_immatriculation") \
            or a.get("numero_immatriculation")

    if parsed is None:
        records.append({"cle": cle, "bdnb": bdnb, "usage": usage,
                        "bg": bg, "is_rnc": is_rnc, "immat": immat,
                        "match_type": "CLE_MALFORMEE", "n_mut_log": 0,
                        "years": Counter(), "neighbors": []})
        continue

    num_base, suffix, voie_toks = parsed
    key = (num_base, voie_toks)

    # 3a) match exact (num_base, voie_toks) - capture variantes B/T/Q
    rows_exact = dedup_mutations(dvf_log_by_key.get(key, []))

    # 3c) Voisin +/-2 meme voie (numerique)
    neighbors = []
    try:
        n_int = int(num_base)
        for delta in (-2, -1, 1, 2):
            nn = str(n_int + delta)
            nrows = dedup_mutations(dvf_log_by_key.get((nn, voie_toks), []))
            if nrows:
                neighbors.append((nn, len(nrows),
                                  sorted({yr(m) for m in nrows})))
    except (ValueError, TypeError):
        pass

    n_mut_log = len(rows_exact)
    years = Counter(yr(m) for m in rows_exact)

    # Determine match type :
    #   ORPHAN_RECOVERABLE  : rows_exact > 0 (variantes B/T/Q ou ortho recoupent)
    #   BGD_PARTAGE_VOISIN  : 0 hit propre mais voisin +/-2 vend
    #   AUCUN_DVF_LOGEMENT  : ni propre ni voisin
    if n_mut_log > 0:
        match_type = "ORPHAN_RECOVERABLE"
    elif neighbors:
        match_type = "BGD_PARTAGE_VOISIN"
    else:
        match_type = "AUCUN_DVF_LOGEMENT"

    records.append({
        "cle": cle, "bdnb": bdnb, "usage": usage, "bg": bg,
        "is_rnc": is_rnc, "immat": immat,
        "match_type": match_type,
        "n_mut_log": n_mut_log,
        "years": years,
        "neighbors": neighbors,
        "num_base": num_base, "suffix": suffix, "voie_toks": voie_toks,
    })

# Tri par nb_log DESC
records.sort(key=lambda r: -r["bdnb"])

# Stats etape 2
ct = Counter(r["match_type"] for r in records)
print(f"    {dict(ct)}")
n_orphan = ct["ORPHAN_RECOVERABLE"]
n_bgd = ct["BGD_PARTAGE_VOISIN"]
n_none = ct["AUCUN_DVF_LOGEMENT"]
print(f"    [A] ORPHAN_RECOVERABLE : {n_orphan}")
print(f"    [B+C] AUCUN DVF logement (a sous-classifier)   : {n_none}")
print(f"    [BGD?] voisin vend mais ancre 0                : {n_bgd}")


# ---------- 3b. Pre-classification BGD_PARTAGE_VOISIN ----------
print("\n[3b] Pre-classification BGD_PARTAGE_VOISIN "
      "(FUSION_DEJA_FA / DISTINCT / INCERTAIN)...")

# Charger cache parcelles BDNB local
BGID_PARC = ROOT / "data" / "_bgid_parcelle_dl.json"
bgid_parc = {}
if BGID_PARC.exists():
    bgid_parc = json.loads(BGID_PARC.read_text(encoding="utf-8"))

# Index light : (type_voie, voie_toks) -> [(num_int, raw_num, cle, a)]
voie_to_cles = defaultdict(list)
for a in ad:
    cle = a.get("cle") or ""
    p = cle.split("|")
    if len(p) != 3:
        continue
    m = re.match(r"^(\d+)", p[0])
    if not m:
        continue
    voie_to_cles[(p[1], p[2])].append(
        (int(m.group(1)), p[0], cle, a)
    )


def find_voisin_cles_qui_vendent(cle_ancre):
    """Pour cle_ancre, retourne liste de cles voisines (+/-2 meme voie)
    qui ont nb_ventes_logement > 0 (own ou via autoMerged)."""
    p = cle_ancre.split("|")
    if len(p) != 3:
        return []
    m = re.match(r"^(\d+)", p[0])
    if not m:
        return []
    num_a = int(m.group(1))
    type_v, voie_n = p[1], p[2]
    out = []
    for num_v, _, cle_v, av in voie_to_cles.get((type_v, voie_n), []):
        if cle_v == cle_ancre:
            continue
        if abs(num_v - num_a) > 2:
            continue
        vlog_own = av.get("nb_ventes_logement") or 0
        if vlog_own > 0:
            out.append(("own", cle_v, av))
            continue
        # OR la cle voisine peut etre une FA-source dont les ventes sont
        # transferees ailleurs - on les recupere via les srcs de autoMerged
        # (pattern : 164 FA -> 166, donc 164 a vlog>0 propre, deja capture).
    return out


bgd_pre_class = {}  # cle ancre -> (verdict, raison, voisins_info)
for r in records:
    if r["match_type"] != "BGD_PARTAGE_VOISIN":
        continue
    cle = r["cle"]
    bg_a = r["bg"]
    immat_a = r["immat"]
    parc_a = set(bgid_parc.get(bg_a, [])) if bg_a else set()
    voisins = find_voisin_cles_qui_vendent(cle)

    if not voisins:
        # Edge case : neighbors detected via DVF but pas dans light index
        bgd_pre_class[cle] = ("INCERTAIN", "voisin DVF mais pas dans light", [])
        continue

    meme_bgid = any(av.get("batiment_groupe_id") == bg_a and bg_a
                    for _, _, av in voisins)
    voisin_immats = set()
    voisin_bgids_diff = []
    for _, cle_v, av in voisins:
        bg_v = av.get("batiment_groupe_id") or ""
        cp_v = co_by_cle.get(cle_v, {})
        imv = cp_v.get("numero_immatriculation") or av.get("numero_immatriculation")
        if imv:
            voisin_immats.add(imv)
        if bg_v and bg_v != bg_a:
            voisin_bgids_diff.append(bg_v)
    meme_immat = bool(immat_a) and immat_a in voisin_immats
    parc_overlap = False
    for bg_v in voisin_bgids_diff:
        pv = set(bgid_parc.get(bg_v, []))
        if pv & parc_a:
            parc_overlap = True
            break

    # Verdict
    if meme_bgid:
        # FA pas en place (sinon exclu autoMerged) mais bgid commun
        # = candidat FA manquante (rare apres autoMerged exclusion,
        # mais peut arriver si voisin FA->autre cle).
        verdict = "FUSION_DEJA_FA"
        reason = ("voisin partage bgid mais autoMerged n'a pas declenche "
                  "(verifier _fusion_cible)")
    elif meme_immat:
        verdict = "FUSION_IMMAT"
        reason = "meme immat RNC sur voisin -> meme copro multi-bgid"
    elif parc_overlap:
        verdict = "INCERTAIN"
        reason = "parcelle BDNB commune -> investiguer Cambronne"
    elif bg_a and voisin_bgids_diff:
        verdict = "DISTINCT"
        reason = "bgid+immat+parcelles disjoints -> vrais voisins separes"
    else:
        verdict = "INCERTAIN"
        reason = "donnees insuffisantes (bgid manquant ?)"

    bgd_pre_class[cle] = (verdict, reason,
                           [(cle_v, av.get("nb_ventes_logement") or 0)
                            for _, cle_v, av in voisins])

# Stats
bgd_ct = Counter(v for v, _, _ in bgd_pre_class.values())
print(f"    BGD_PARTAGE_VOISIN classes : {dict(bgd_ct)}")

# ---------- 4. Sous-classification MAJIC ----------
print("\n[4] Sous-classification MAJIC (residu sans DVF logement)...")
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

# Re-query parquet MAJIC pour code_droit + HLM ?  TROP LENT pour 120 cles.
# On utilise une heuristique sur enrich.sirens : detecter HLM via
# denomination contenant 'HABITAT'/'HLM'/'GRANDLYON'/'ALLIADE'/'BATIGERE'/
# 'CDC HABITAT'/'IMMOBILIERE RHONE'/'FONCIERE' (PM principalement). On
# n'a pas code_droit (Emphyteote vs Proprietaire) -> approximation :
# si SIREN HLM detecte avec pct >= 20% -> tag SOCIAL probable.
HLM_NEEDLES = (
    "HABITAT", " HLM", "HLM ", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH ", "FONCIERE HABITAT",
)


def detect_hlm(sirens):
    """Retourne (lots_hlm_total, top_hlm_denom or None)."""
    if not sirens:
        return 0, None
    lots_hlm = 0
    top = None
    top_lots = 0
    for s in sirens:
        dn = (s.get("denomination") or "").upper()
        if any(n in dn for n in HLM_NEEDLES):
            lots_hlm += s.get("lots") or 0
            if (s.get("lots") or 0) > top_lots:
                top_lots = s.get("lots") or 0
                top = s
    return lots_hlm, top


def detect_top_prive(sirens, hlm_set):
    """Top SIREN non-HLM. Retourne (siren_obj, pct_lots) ou (None, 0)."""
    if not sirens:
        return None, 0
    candidates = [s for s in sirens
                  if (s.get("denomination") or "").upper()
                  not in hlm_set]
    candidates = [s for s in candidates
                  if not any(n in (s.get("denomination") or "").upper()
                             for n in HLM_NEEDLES)]
    if not candidates:
        return None, 0
    top = max(candidates, key=lambda s: s.get("lots") or 0)
    return top, top.get("pct_lots") or 0


def subclassify(rec):
    """Retourne (bloc, reason). bloc in {SOCIAL, MONO, ANOMALIE}."""
    e = enrich_by_cle.get(rec["cle"])
    if not e:
        return "ANOMALIE", "pas dans enrich (parc inconnu)"
    sirens = e.get("sirens") or []
    n_lots = e.get("majic_lots") or 0
    lots_hlm, top_hlm = detect_hlm(sirens)
    social_pct = round(lots_hlm * 100 / n_lots, 1) if n_lots else 0
    if social_pct >= 60:
        return "SOCIAL", (f"HLM {top_hlm['denomination'][:25]} "
                          f"social_pct={social_pct}%")
    # MONO : 1 SIREN >= 80% lots PM ET >= 80% BDNB
    bdnb = rec["bdnb"]
    if sirens:
        top = max(sirens, key=lambda s: s.get("lots") or 0)
        top_pct_pm = top.get("pct_lots") or 0
        top_lots = top.get("lots") or 0
        top_pct_bdnb = round(top_lots * 100 / bdnb, 1) if bdnb > 0 else 0
        # exclure HLM du top mono
        dn = (top.get("denomination") or "").upper()
        is_hlm = any(n in dn for n in HLM_NEEDLES)
        if (not is_hlm) and top_pct_pm >= 80 and top_pct_bdnb >= 80:
            return "MONO", (f"top SIREN {top['denomination'][:25]} "
                            f"{top_pct_pm}% PM / {top_pct_bdnb}% BDNB")
    return "ANOMALIE", f"social_pct={social_pct}% top_PM_inadequat"


for r in records:
    if r["match_type"] in ("AUCUN_DVF_LOGEMENT", "BGD_PARTAGE_VOISIN"):
        bloc, reason = subclassify(r)
        r["bloc_subclass"] = bloc
        r["bloc_reason"] = reason
    else:
        r["bloc_subclass"] = None
        r["bloc_reason"] = None

# ---------- 5. Blocs final ----------
A = [r for r in records if r["match_type"] == "ORPHAN_RECOVERABLE"]
B = [r for r in records if r.get("bloc_subclass") in ("SOCIAL", "MONO")]
C = [r for r in records if r.get("bloc_subclass") == "ANOMALIE"]
# Sous-decomposition C par BGD_PARTAGE preclass
C_BGD_PARTAGE = [r for r in C if r["match_type"] == "BGD_PARTAGE_VOISIN"]
C_AUCUN = [r for r in C if r["match_type"] == "AUCUN_DVF_LOGEMENT"]
# Pour les BGD_PARTAGE, on les regroupe par verdict pre-class
def bgd_verdict(r):
    return bgd_pre_class.get(r["cle"], ("INCONNU", "", []))[0]
C_BGD_DISTINCT = [r for r in C_BGD_PARTAGE if bgd_verdict(r) == "DISTINCT"]
C_BGD_INCERTAIN = [r for r in C_BGD_PARTAGE if bgd_verdict(r) == "INCERTAIN"]
C_BGD_FUSION = [r for r in C_BGD_PARTAGE if bgd_verdict(r).startswith("FUSION")]
C_BGD_AUTRE = [r for r in C_BGD_PARTAGE if r not in C_BGD_DISTINCT
                and r not in C_BGD_INCERTAIN and r not in C_BGD_FUSION]


def fmt_years(yc):
    if not yc:
        return ""
    return " ".join(f"{y}:{n}" for y, n in sorted(yc.items()))


def majic_top(rec, max_sirens=2):
    e = enrich_by_cle.get(rec["cle"])
    if not e:
        return "-"
    sirens = (e.get("sirens") or [])[:max_sirens]
    n = e.get("majic_lots") or 0
    if not sirens:
        return f"({n} lots PM, 0 SIREN)"
    parts = [f"{s.get('denomination', '?')[:22]}({s.get('lots')}/{s.get('pct_lots')}%)"
             for s in sirens]
    return f"[{n} lots PM] " + " | ".join(parts)


print()
print("=" * 78)
print(f"[A] VENTES ORPHELINES RECUPERABLES  ({len(A)} adresses)")
print("=" * 78)
print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'mut':>4} {'annees':25s} {'type'}")
print("  " + "-" * 80)
for i, r in enumerate(A, 1):
    typ = "exact (variantes B/T/Q ou ortho)" if r["suffix"] else "exact (no-suffix vs DVF suffixes)"
    print(f"  {i:>3} {r['cle']:32s} {r['bdnb']:>6} {r['n_mut_log']:>4} "
          f"{fmt_years(r['years']):25s} {typ}")

print()
print("=" * 78)
print(f"[B] 0-VENTE EXPLIQUE (SOCIAL / MONO patrimonial)  ({len(B)} adresses)")
print("=" * 78)
print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'bloc':7s} {'voisin':22s} {'reason'}")
print("  " + "-" * 124)
for i, r in enumerate(B, 1):
    voisin = ""
    if r["neighbors"]:
        nb_str = ",".join(f"{nn}({nm})" for nn, nm, _ in r["neighbors"][:2])
        voisin = nb_str
    print(f"  {i:>3} {r['cle']:32s} {r['bdnb']:>6} {r['bloc_subclass']:7s} "
          f"{voisin:22s} {r['bloc_reason']}")

print()
print("=" * 78)
print(f"[C] ANOMALIE  ({len(C)} adresses) - decomposition :")
print(f"     C-BGD_FUSION     (fusion potentielle, FA manquante)  : {len(C_BGD_FUSION)}")
print(f"     C-BGD_INCERTAIN  (parcelle commune, Cambronne ?)     : {len(C_BGD_INCERTAIN)}")
print(f"     C-BGD_DISTINCT   (vrais voisins separes, 0-vente reel) : {len(C_BGD_DISTINCT)}")
print(f"     C-BGD_AUTRE      (donnees insuffisantes)              : {len(C_BGD_AUTRE)}")
print(f"     C-AUCUN          (pas de DVF +/-2, vraie 0-vente isolee) : {len(C_AUCUN)}")
print("=" * 78)


def afficher_bloc(titre, lst):
    if not lst:
        return
    print()
    print(f"--- {titre} ({len(lst)} adresses) ---")
    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'usage':22s} {'voisin (vlog)':25s} "
          f"{'verdict':14s} {'top proprios'}")
    print("  " + "-" * 154)
    for i, r in enumerate(lst, 1):
        voisin = ""
        if r["neighbors"]:
            nb_str = ",".join(f"{nn}({nm})" for nn, nm, _ in r["neighbors"][:2])
            voisin = nb_str
        verdict_str = ""
        if r["match_type"] == "BGD_PARTAGE_VOISIN":
            v, _, _ = bgd_pre_class.get(r["cle"], ("?", "", []))
            verdict_str = v
        print(f"  {i:>3} {r['cle']:32s} {r['bdnb']:>6} {r['usage'][:22]:22s} "
              f"{voisin[:25]:25s} {verdict_str:14s} {majic_top(r)}")


afficher_bloc("[C-BGD_FUSION] Fusion potentielle (FA manquante)", C_BGD_FUSION)
afficher_bloc("[C-BGD_INCERTAIN] Parcelle commune, Cambronne suspect", C_BGD_INCERTAIN)
afficher_bloc("[C-BGD_DISTINCT] Voisins separes, 0-vente reel", C_BGD_DISTINCT)
afficher_bloc("[C-BGD_AUTRE] Donnees insuffisantes", C_BGD_AUTRE)
afficher_bloc("[C-AUCUN] Vraies 0-vente isolees (aucun DVF +/-2)", C_AUCUN)


# Statistiques finales
print()
print("=" * 78)
print("RECAP")
print("=" * 78)
print(f"  Population 0-vente   : {n_pop} adresses ({sum_log} log BDNB)")
print(f"  [A] RECUPERABLES     : {len(A)} adresses "
      f"({sum(r['n_mut_log'] for r in A)} mutations Apt+Maison rattachables)")
print(f"  [B] EXPLIQUE         : {len(B)} adresses "
      f"(SOCIAL={sum(1 for r in B if r['bloc_subclass']=='SOCIAL')}, "
      f"MONO={sum(1 for r in B if r['bloc_subclass']=='MONO')})")
print(f"  [C] ANOMALIE         : {len(C)} adresses")
print(f"      [C-BGD_FUSION]    : {len(C_BGD_FUSION)} (FA manquante a appliquer)")
print(f"      [C-BGD_INCERTAIN] : {len(C_BGD_INCERTAIN)} (Cambronne potentiel)")
print(f"      [C-BGD_DISTINCT]  : {len(C_BGD_DISTINCT)} (vrais voisins, 0-vente reel)")
print(f"      [C-BGD_AUTRE]     : {len(C_BGD_AUTRE)} (autre)")
print(f"      [C-AUCUN]         : {len(C_AUCUN)} (aucun DVF +/-2)")
print()
print("LECTURE SEULE. Pas de patch.")
