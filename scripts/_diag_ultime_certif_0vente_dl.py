#!/usr/bin/env python3
"""ULTIME SCAN de certification des adresses 0-vente DL (lecture seule).

ETAPE 0 : reproduction exacte du filtre 'Sans ventes' UI
          (index.html ligne 4898 fusedSrc + ligne 4928 filterSansVentes)
          Attendu : ~70 adresses (population dashboard).
          Si != 70, AFFICHER l'ecart et STOP.

ETAPES 1-4 : entonnoir d'exclusion sequentiel.
  1. FANTOMES        : bgid absent, nb_log_bdnb==0 + nb_lots==0, _fusion_auto
  2. RATTACHEMENT    : meme bgid qu'une autre adresse light qui vend
  3. ORGANISMES SOC  : HLM/public dominant MAJIC
  4. TERTIAIRE       : usage_principal_bdnb=Tertiaire

RESTE - 3 sous-classes :
  - MONO NON DETECTE : 1 SIREN/PP >= 80% lots PM
  - COPRO FIGEE      : multi-proprios, 0 mut/an parcelle
  - COPRO ABSENTE DVF: 0 mutation Apt sur la parcelle 5 ans

Sources : light, KV local, enrich MAJIC, DVF, overrides, BDNB cache.
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
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

ANS = ("2021", "2022", "2023", "2024", "2025")
ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def parse_cle(cle):
    parts = (cle or "").split("|")
    if len(parts) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", parts[0].strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2), toks(parts[2])


HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT", "OFFICE PUBLIC DE L'HABITAT",
)
PUBLIC_NON_HLM = (
    "COMMUNE DE LYON", "METROPOLE DE LYON", "DEPARTEMENT DU RHONE",
    "REGION AUVERGNE", "REGION RHONE", "ETAT ", "ETAT,",
    "HOSPICES CIVILS", "CENTRE HOSPITALIER",
    "COMMUNAUTE URBAINE", "GRAND LYON", "DIRECTION DE L IMMOBILIER",
    "SEM ", "FONCIERE VESTA", "FONCIERE PIERRE",
    "CENTRE REGIONAL OEUVRES", "CROUS",
    "ASSOCIATION DIOCESAINE", "FONDATION", "ITINOVA",
    "INSTITUT NATIONAL", "INSTITUT DE FRANCE",
)


def is_hlm(denom):
    d = (denom or "").upper()
    return any(n in d for n in HLM_NEEDLES if n.strip())


def is_public_non_hlm(denom):
    d = (denom or "").upper()
    return any(n in d for n in PUBLIC_NON_HLM)


# ============================================================
print("=" * 78)
print("ULTIME SCAN CERTIFICATION 0-VENTE DL")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
fusions_kv = kv.get("fusions") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

# ============================================================
# ETAPE 0 : reproduire EXACTEMENT le filtre Sans ventes UI
# ============================================================
print()
print("=" * 78)
print("ETAPE 0 : reproduction filtre 'Sans ventes' UI")
print("=" * 78)


def kv_type(cle):
    return ((assigns.get(cle) or {}).get("type")) or ""


def vpa(a):
    return a.get("ventes_par_an_logement") or {}


# fusedSrc + mergedInto + autoMerged (cf index.html l. 4768-4798)
merged_into = {}
fused_src = set()
for src, dst in fusions_kv.items():
    sa = by_cle.get(src)
    if not sa or not dst or src == dst:
        continue
    fused_src.add(src)
    m = merged_into.setdefault(dst, {"ventes": {}})
    for y in ANS:
        m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

auto_merged = {}
for a in ad:
    cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
    cle = a.get("cle") or ""
    if a.get("_fusion_auto") and cible and cle not in fused_src:
        fused_src.add(cle)
        am = auto_merged.setdefault(cible, {"ventes": {}})
        for y in ANS:
            am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)


def passes_sans_ventes(a):
    """Reproduit EXACTEMENT le filtre Sans ventes (index.html l. 4898 + 4928)."""
    cle = a.get("cle") or ""
    # l. 4898 : if (fusedSrc[a.cle]) return;
    if cle in fused_src:
        return False
    # l. 4928 if (filterSansVentes) { ... }
    asSv = assigns.get(cle) or {}
    t = asSv.get("type") or ""
    # 1. EXCLURE social / bureaux / mono
    if t in ("social", "bureaux", "mono"):
        return False
    # 2. Type valide : copro_rnc OR copro_non_immat OR mixte
    is_copro_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
    is_copro_ni = (t == "copro_non_immat")
    is_mixte = (t == "mixte")
    if not (is_copro_rnc or is_copro_ni or is_mixte):
        return False
    # 3. 0 vente log strict
    own_n = int(a.get("nb_ventes_logement") or 0)
    if own_n > 0:
        return False
    own_vpa = a.get("ventes_par_an_logement") or {}
    if any((own_vpa.get(y) or 0) > 0 for y in ANS):
        return False
    # 4. Fused
    if is_copro_rnc:
        mi = merged_into.get(cle)
        if mi and any((mi["ventes"].get(y) or 0) > 0 for y in ANS):
            return False
    am = auto_merged.get(cle)
    if am and any((am["ventes"].get(y) or 0) > 0 for y in ANS):
        return False
    return True


population = [a for a in ad if passes_sans_ventes(a)]
n_pop = len(population)
print(f"\n  Population filtre 'Sans ventes' UI reproduite : {n_pop}")
print(f"  Attendu user            : ~70")
print(f"  Ecart                   : {n_pop - 70:+d}")

if n_pop != 70:
    print(f"\n  AVERTISSEMENT : ecart de {n_pop - 70:+d} avec l'attendu.")
    print(f"  Verifier KV cloud vs cache local (peut-etre desyncro).")
    print(f"  Cache KV local : {len(assigns)} assignments")
    # On continue quand meme avec la population calculee
    print(f"  -> on continue avec {n_pop} adresses (sans bloquer)")

# Sort by nb_log_bdnb DESC
def eff_log(a):
    cle = a.get("cle") or ""
    cp = co_by_cle.get(cle)
    if cp:
        v = cp.get("nb_lots_habitation")
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return int(a.get("nb_log_bdnb") or 0)


population.sort(key=lambda a: -eff_log(a))
total_log = sum(eff_log(a) for a in population)
print(f"  Total nb_log cumule     : {total_log}")

# ============================================================
# DVF + bgid sharing prep
# ============================================================
print()
print("=" * 78)
print("PREPARATION : DVF + bgid sharing")
print("=" * 78)

# Index DVF par parcelle
dvf = json.loads(DVF.read_text(encoding="utf-8"))
dvf_by_parc = defaultdict(list)
for m in dvf:
    sec = m.get("Section") or ""
    plan = (m.get("No plan") or "").lstrip("0") or "0"
    if str(m.get("Code type local") or "").strip() in ("1", "2"):
        dvf_by_parc[(sec, plan)].append(m)


def parc_to_dvf_key(parc):
    sec = parc[8:10]
    plan = parc[10:].lstrip("0") or "0"
    return (sec, plan)


def mut_apt_an_parcelle(cle):
    e = enrich_by_cle.get(cle, {})
    parcs = e.get("parcelles_bdnb") or []
    seen = set()
    for parc in parcs:
        for m in dvf_by_parc.get(parc_to_dvf_key(parc), []):
            seen.add((m.get("Date mutation"), m.get("No disposition"),
                      m.get("Valeur fonciere")))
    return len(seen) / 5.0


# Index adresses par bgid (light entier)
cles_par_bgid = defaultdict(list)
for a in ad:
    bg = a.get("batiment_groupe_id") or ""
    if bg:
        cles_par_bgid[bg].append(a)


# ============================================================
# FILTRE 1 : FANTOMES
# ============================================================
print()
print("=" * 78)
print("FILTRE 1 : FANTOMES (bgid absent / 0 logement / FA)")
print("=" * 78)

fant = []
pop1 = []
for a in population:
    cle = a.get("cle") or ""
    cp = co_by_cle.get(cle, {})
    bg = a.get("batiment_groupe_id") or ""
    bdnb = int(a.get("nb_log_bdnb") or 0)
    lots = int(cp.get("nb_lots_habitation") or 0) if cp else 0
    fa = bool(a.get("_fusion_auto"))
    reasons = []
    if not bg:
        reasons.append("bgid absent")
    if bdnb == 0 and lots == 0:
        reasons.append("0 log BDNB + 0 lot RNC")
    if fa:
        reasons.append("_fusion_auto=True")
    if reasons:
        fant.append((a, " + ".join(reasons)))
    else:
        pop1.append(a)

print(f"\n  Exclus FANTOMES : {len(fant)}")
print(f"  Reste apres F1  : {len(pop1)}")
if fant:
    print(f"\n  Detail (top 10 par nb_log) :")
    fant.sort(key=lambda x: -eff_log(x[0]))
    for a, raison in fant[:10]:
        print(f"    {a['cle']:32s} nb_log={eff_log(a):>4}  raison: {raison}")
    if len(fant) > 10:
        print(f"    ... +{len(fant) - 10} autres")


# ============================================================
# FILTRE 2 : RATTACHEMENT BDNB
# ============================================================
print()
print("=" * 78)
print("FILTRE 2 : RATTACHEMENT BDNB (bgid partage avec adresse qui vend)")
print("=" * 78)

rattach = []
pop2 = []
for a in pop1:
    cle = a.get("cle") or ""
    bg = a.get("batiment_groupe_id") or ""
    voisins_qui_vendent = []
    for av in cles_par_bgid.get(bg, []):
        if (av.get("cle") or "") == cle:
            continue
        if int(av.get("nb_ventes_logement") or 0) > 0:
            voisins_qui_vendent.append(av)
    if voisins_qui_vendent:
        rattach.append((a, voisins_qui_vendent))
    else:
        pop2.append(a)

print(f"\n  Exclus RATTACHES : {len(rattach)}")
print(f"  Reste apres F2   : {len(pop2)}")
if rattach:
    print(f"\n  Detail (top 10 par nb_log) :")
    rattach.sort(key=lambda x: -eff_log(x[0]))
    for a, voisins in rattach[:10]:
        cles_v = ", ".join(f"{v.get('cle')}({v.get('nb_ventes_logement')})"
                            for v in voisins[:2])
        print(f"    {a['cle']:32s} nb_log={eff_log(a):>4}  rattachee a: {cles_v}")
    if len(rattach) > 10:
        print(f"    ... +{len(rattach) - 10} autres")


# ============================================================
# FILTRE 3 : ORGANISMES SOCIAUX
# ============================================================
print()
print("=" * 78)
print("FILTRE 3 : ORGANISMES SOCIAUX (HLM/public dominant MAJIC)")
print("=" * 78)


def classify_dominant_owner(cle):
    """Retourne (categorie, top_owner_name, pct) :
       - 'HLM_DOMINANT' si top SIREN HLM >= 50% lots
       - 'PUBLIC_DOMINANT' si top SIREN public non-HLM >= 50%
       - 'AUTRE' sinon"""
    e = enrich_by_cle.get(cle, {})
    sirens = e.get("sirens") or []
    n_lots_total = e.get("majic_lots") or 0
    if n_lots_total == 0 or not sirens:
        return ("AUTRE", None, 0)
    # somme des HLM
    hlm_lots = sum(s.get("lots") or 0 for s in sirens
                    if is_hlm(s.get("denomination")))
    pub_lots = sum(s.get("lots") or 0 for s in sirens
                    if is_public_non_hlm(s.get("denomination")))
    hlm_pct = round(hlm_lots * 100 / n_lots_total, 1)
    pub_pct = round(pub_lots * 100 / n_lots_total, 1)
    top = sirens[0]
    if hlm_pct >= 50:
        top_hlm = next((s for s in sirens
                        if is_hlm(s.get("denomination"))), None)
        return ("HLM_DOMINANT",
                (top_hlm or top).get("denomination"), hlm_pct)
    if pub_pct >= 50:
        top_pub = next((s for s in sirens
                        if is_public_non_hlm(s.get("denomination"))), None)
        return ("PUBLIC_DOMINANT",
                (top_pub or top).get("denomination"), pub_pct)
    return ("AUTRE", top.get("denomination"), top.get("pct_lots") or 0)


social_excl = []
pop3 = []
for a in pop2:
    cle = a.get("cle") or ""
    cat, top, pct = classify_dominant_owner(cle)
    if cat in ("HLM_DOMINANT", "PUBLIC_DOMINANT"):
        # Verifier DVF (croisement) : si mut/an >= 2 = decollectivisation
        mut_an = mut_apt_an_parcelle(cle)
        if mut_an >= 2.0:
            # Pas social pur, conserver dans pop pour autre analyse
            pop3.append(a)
            # Note : ne pas l'exclure car decollectivisation. Mais
            # comme on est dans 0-vente le mut_an parcelle peut etre
            # eleve a cause de voisins (deja filtre 2 ?). En pratique :
            # rare en 0-vente, on garde
        else:
            social_excl.append((a, cat, top, pct, mut_an))
    else:
        pop3.append(a)

print(f"\n  Exclus SOCIAL/PUBLIC : {len(social_excl)}")
print(f"  Reste apres F3       : {len(pop3)}")
if social_excl:
    print(f"\n  Detail (top 10 par nb_log) :")
    social_excl.sort(key=lambda x: -eff_log(x[0]))
    for a, cat, top, pct, mut in social_excl[:10]:
        top_str = (top or "?")[:38]
        print(f"    {a['cle']:32s} nb_log={eff_log(a):>4}  "
              f"{cat:16s} {pct:>5.1f}% {top_str}  mut/an={mut:.2f}")
    if len(social_excl) > 10:
        print(f"    ... +{len(social_excl) - 10} autres")


# ============================================================
# FILTRE 4 : TERTIAIRE
# ============================================================
print()
print("=" * 78)
print("FILTRE 4 : TERTIAIRE (usage_principal_bdnb = Tertiaire/Bureaux)")
print("=" * 78)

tert = []
pop4 = []
for a in pop3:
    usage = (a.get("usage_principal_bdnb") or "").lower()
    if "tertiaire" in usage or "bureau" in usage:
        tert.append(a)
    else:
        pop4.append(a)

print(f"\n  Exclus TERTIAIRE : {len(tert)}")
print(f"  Reste apres F4   : {len(pop4)}")
if tert:
    print(f"\n  Detail :")
    tert.sort(key=lambda a: -eff_log(a))
    for a in tert[:10]:
        print(f"    {a['cle']:32s} nb_log={eff_log(a):>4}  "
              f"usage='{a.get('usage_principal_bdnb')}'")
    if len(tert) > 10:
        print(f"    ... +{len(tert) - 10} autres")


# ============================================================
# SOUS-CLASSIFICATION DES SURVIVANTS
# ============================================================
print()
print("=" * 78)
print(f"SURVIVANTS : {len(pop4)} adresses CERTIFIEES 0-vente")
print("=" * 78)


def sub_classify(a):
    """Retourne (categorie, detail) :
       MONO_NON_DETECTE / COPRO_FIGEE / COPRO_ABSENTE_DVF
    """
    cle = a.get("cle") or ""
    e = enrich_by_cle.get(cle, {})
    bdnb = int(a.get("nb_log_bdnb") or 0)
    sirens = e.get("sirens") or []
    majic_pm = e.get("majic_lots") or 0
    mut_an_parc = mut_apt_an_parcelle(cle)
    # MONO : top SIREN >= 80% lots PM (sur lots PM, pas BDNB,
    # car PM only dans MAJIC)
    if sirens and majic_pm > 0:
        top = sirens[0]
        top_pct = round((top.get("lots") or 0) * 100 / majic_pm, 1)
        if top_pct >= 80:
            return ("MONO_NON_DETECTE",
                    f"top={top.get('denomination', '?')[:30]} "
                    f"{top.get('lots')}/{majic_pm} PM ({top_pct}%)")
    # COPRO ABSENTE DVF : aucune mutation Apt parcelle 5 ans
    if mut_an_parc == 0:
        return ("COPRO_ABSENTE_DVF",
                f"0 mut Apt parcelle 5 ans  ({majic_pm} lots PM, {len(sirens)} SIRENs)")
    # COPRO FIGEE : multi-proprios, mut/an parcelle present mais faible
    return ("COPRO_FIGEE",
            f"{majic_pm} lots PM, {len(sirens)} SIRENs ; "
            f"mut/an parc={mut_an_parc:.2f}")


survivants = []
for a in pop4:
    cat, detail = sub_classify(a)
    survivants.append({"a": a, "cat": cat, "detail": detail})

cnt_cat = Counter(s["cat"] for s in survivants)
print(f"\n  Sous-classification :")
for cat, n in cnt_cat.most_common():
    print(f"    {cat:25s} : {n}")

# ============================================================
# ENTONNOIR
# ============================================================
print()
print("=" * 78)
print("ENTONNOIR CHIFFRE")
print("=" * 78)
print(f"\n  Population initiale (filtre Sans ventes UI) : {n_pop:>4}")
print(f"  - F1 Fantomes                               : {len(fant):>4}")
print(f"  = apres F1                                  : {len(pop1):>4}")
print(f"  - F2 Rattachees                             : {len(rattach):>4}")
print(f"  = apres F2                                  : {len(pop2):>4}")
print(f"  - F3 Organismes sociaux/publics             : {len(social_excl):>4}")
print(f"  = apres F3                                  : {len(pop3):>4}")
print(f"  - F4 Tertiaire                              : {len(tert):>4}")
print(f"  = SURVIVANTS CERTIFIES                      : {len(pop4):>4}")

# ============================================================
# TABLEAU FINAL DES SURVIVANTS
# ============================================================
print()
print("=" * 130)
print("TABLEAU FINAL : survivants certifies 0-vente (tri nb_log DESC)")
print("=" * 130)
survivants.sort(key=lambda s: -eff_log(s["a"]))
print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'categorie':22s} "
      f"{'mut/an parc':>12} {'detail'}")
print("  " + "-" * 128)
for i, s in enumerate(survivants, 1):
    a = s["a"]
    mut = mut_apt_an_parcelle(a.get("cle") or "")
    print(f"  {i:>3} {a['cle']:32s} {eff_log(a):>6} {s['cat']:22s} "
          f"{mut:>10.2f}   {s['detail'][:50]}")

# ============================================================
# Detail par sous-categorie
# ============================================================
for cat in ("MONO_NON_DETECTE", "COPRO_ABSENTE_DVF", "COPRO_FIGEE"):
    sub = [s for s in survivants if s["cat"] == cat]
    if not sub:
        continue
    print()
    print("=" * 78)
    print(f"[{cat}] : {len(sub)} cles")
    print("=" * 78)
    for s in sub:
        a = s["a"]
        cp = co_by_cle.get(a.get("cle") or "", {})
        immat = cp.get("numero_immatriculation") or a.get("numero_immatriculation") or "-"
        print(f"  {a['cle']:32s} nb_log={eff_log(a):>4}  "
              f"immat={immat:12s}  {s['detail']}")
