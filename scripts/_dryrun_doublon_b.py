#!/usr/bin/env python3
"""DRYRUN doublon B : faux-matchings 4/6/8/13 RUE DAUPHINE (DL).

CONCLUSION DIAGNOSTIC :
- 75JZ-QX89 (103 lgts, 1949) = HBM 7/9/11/13 RUE DAUPHINE (impair)
  Le pivot l_libelle_adr ne montrait que les variantes B-suffixes
  ('7B/9B/11B/13B') ; les numeros sans B sont resolus par
  rel_batiment_groupe_adresse vers le MEME 75JZ (autorite).
- 11 DAUPHINE est CORRECTEMENT sur 75JZ (qualifie 'social' KV = HBM
  confirme annees 50, 103 lgts).
- Le faux-matching concerne 4 (pair), 6 (pair), 8 (pair Tertiaire) et
  13 (impair, faussement attribue a RMZ8 = bati Tertiaire 15 DAUPH).

11 modifs (4 RE-POINT + restructurations chaines) :
  - 4 DAUPH  : 75JZ -> 936T-G73D  (81 lgts, 1985, ancre '4/6' conservee)
  - 6 DAUPH  : 75JZ -> 936T-G73D  (FA->4)
  - 8 DAUPH  : L1N7 -> 6G9Q-X4H2  (Tertiaire, nb_log=None ; detache
               de '_fusion_cible=1|RUE|ST MAXIMIN' incoherent)
  - 13 DAUPH : RMZ8 -> 75JZ       (HBM ; ex-ancre '13/15' degradee)
  - 10 DAUPH : retire label '8/10' (mono-num)
  - 11 DAUPH : etend label '7/9/11' -> '7/9/11/13 RUE DAUPHINE'
  - 13 DAUPH : devient FA fused vers chaine 75JZ ancree 11
  - 15 DAUPH : retire FA + _fusion_cible (ex-fused vers 13, RMZ8 mono)

INTOUCHE legitime :
  - 7, 9, 11 (deja sur 75JZ correct)
  - 2 DAUPH (immat AG8595613 NHFZ-3KHY)
  - 14 DAUPH (immat AB0228890 RESIDENCE THEMIS)
  - 2 ST THEODORE (deja ancre 936T-G73D, garde son statut)
  - 12 DAUPH (BAN imprecis, copro RNC nommee "120 DAUPHINE" = a investiguer separement)
"""
import json, sys, copy
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
by_cle = {a.get("cle") or "": a for a in ad}

def to_int(x):
    try: return int(x)
    except Exception: return 0

# Bgids verifies via BAN -> BDNB rel_batiment_groupe_adresse
S75JZ = "bdnb-bg-L2AS-75JZ-QX89"   # HBM 7/9/11/13 - 103 lgts 1949 R-coll
S936T = "bdnb-bg-BJ9A-936T-G73D"   # 4/6 DAUPH + 2/8 ST-THEODORE - 81 lgts 1985
S6G9Q = "bdnb-bg-CPR3-6G9Q-X4H2"   # 8 DAUPH + 3/9 ST-THEODORE - Tertiaire
SL1N7 = "bdnb-bg-RTNL-L1N7-K12Y"   # 10 DAUPH + 1 ST-MAXIMIN - 14 lgts 1975
SRMZ8 = "bdnb-bg-AUY1-RMZ8-PAUT"   # 15 DAUPH SEUL - 1 lgt Tertiaire 1974

print("=" * 76)
print("DRYRUN doublon B - DAUPHINE 4-15 (faux-matchings)")
print("=" * 76)
print()

# AVANT
print("AVANT - inventaire bgids cibles dans light:")
for label, bg in [("75JZ (HBM impair 7-13)", S75JZ),
                  ("936T (pair 4/6 + 2 ST-T)", S936T),
                  ("6G9Q (8 DAUPH Tertiaire)", S6G9Q),
                  ("L1N7 (10 DAUPH + 1 ST-M)", SL1N7),
                  ("RMZ8 (15 DAUPH Tertiaire)", SRMZ8)]:
    cles = [a.get("cle") for a in ad if a.get("batiment_groupe_id") == bg]
    print(f"  {label:30s} ({bg[-9:]}) : {len(cles)} adr -> {cles}")
print()

# Simulation
ad_after = copy.deepcopy(ad)
by_after = {a.get("cle") or "": a for a in ad_after}

# 1. RE-POINT 4 -> 936T
a4 = by_after["4|RUE|DAUPHINE"]
a4["batiment_groupe_id"] = S936T
a4["nb_log_bdnb"] = 81
a4["annee_construction"] = 1985
a4["_bdnb_match"] = "correctif_doublon_b_re_point"
# garde label '4/6 RUE DAUPHINE' + sources=[6]

# 2. RE-POINT 6 -> 936T
a6 = by_after["6|RUE|DAUPHINE"]
a6["batiment_groupe_id"] = S936T
a6["nb_log_bdnb"] = 81
a6["annee_construction"] = 1985
a6["_bdnb_match"] = "correctif_doublon_b_re_point"
# FA conserve, cible "4/6" deja correcte

# 3. RE-POINT 8 -> 6G9Q (Tertiaire)
a8 = by_after["8|RUE|DAUPHINE"]
a8["batiment_groupe_id"] = S6G9Q
a8["nb_log_bdnb"] = None       # Tertiaire pas de nb_log
a8["annee_construction"] = None
a8["_bdnb_match"] = "correctif_doublon_b_re_point"
# Retire _fusion_cible="1|RUE|ST MAXIMIN" incoherent
a8.pop("_fusion_auto", None)
a8.pop("_fusion_cible", None)
a8["usage_principal_bdnb"] = "Tertiaire"
a8["_usage_bdnb_src"] = "correctif_doublon_b"

# 4. RE-POINT 13 -> 75JZ
a13 = by_after["13|RUE|DAUPHINE"]
a13["batiment_groupe_id"] = S75JZ
a13["nb_log_bdnb"] = 103
a13["annee_construction"] = 1949
a13["_bdnb_match"] = "correctif_doublon_b_re_point"
# Retire ancre '13/15' + sources -> devient FA fused vers 11
a13.pop("_fusion_auto_label", None)
a13.pop("_fusion_auto_sources", None)
a13["_fusion_auto"] = True
a13["_fusion_cible"] = "7/9/11/13 RUE DAUPHINE"

# 5. 10 DAUPH : retire label '8/10' (8 detache)
a10 = by_after["10|RUE|DAUPHINE"]
a10.pop("_fusion_auto_label", None)
a10.pop("_fusion_auto_sources", None)

# 6. 11 DAUPH : etend label
a11 = by_after["11|RUE|DAUPHINE"]
a11["_fusion_auto_label"] = "7/9/11/13 RUE DAUPHINE"
srcs = list(a11.get("_fusion_auto_sources") or [])
if "13|RUE|DAUPHINE" not in srcs:
    srcs.append("13|RUE|DAUPHINE")
a11["_fusion_auto_sources"] = srcs

# 7. 15 DAUPH : retire FA (ex-fused vers 13 ancre supprimee)
a15 = by_after["15|RUE|DAUPHINE"]
a15.pop("_fusion_auto", None)
a15.pop("_fusion_cible", None)

# Print ops
print("OPERATIONS :")
ops = [
    ("RE-POINT", "4|RUE|DAUPHINE",  "75JZ-QX89 -> 936T-G73D  (103 1949 -> 81 1985)"),
    ("RE-POINT", "6|RUE|DAUPHINE",  "75JZ-QX89 -> 936T-G73D  (FA->4 conservee)"),
    ("RE-POINT", "8|RUE|DAUPHINE",  "L1N7-K12Y -> 6G9Q-X4H2  (Tertiaire, _fusion_cible nettoyee)"),
    ("RE-POINT", "13|RUE|DAUPHINE", "RMZ8-PAUT -> 75JZ-QX89  (ancre '13/15' -> FA chaine 11)"),
    ("LABEL", "10|RUE|DAUPHINE",    "retire label '8/10' (mono-num)"),
    ("LABEL", "11|RUE|DAUPHINE",    "etend '7/9/11' -> '7/9/11/13 RUE DAUPHINE'"),
    ("LABEL", "15|RUE|DAUPHINE",    "retire FA + _fusion_cible (RMZ8 mono-num)"),
]
for kind, cle, det in ops:
    print(f"  [{kind:8s}] {cle:18s}  {det}")
print()

# Parc strict logement
def parc_strict(ad_list):
    total, seen = 0, set()
    for a in ad_list:
        nb = to_int(a.get("nb_lots_habitation"))
        if nb > 0:
            total += nb
            continue
        bg = a.get("batiment_groupe_id") or ""
        if bg and bg in seen:
            continue
        if bg: seen.add(bg)
        total += to_int(a.get("nb_log_bdnb"))
    return total

p_av = parc_strict(ad)
p_ap = parc_strict(ad_after)
print(f"Parc DL strict logement : {p_av} -> {p_ap}  (delta {p_ap - p_av:+d})")
print(f"Adresses light : {len(ad)} -> {len(ad_after)}  (delta {len(ad_after)-len(ad):+d})")
print()

# APRES
print("APRES - inventaire bgids cibles dans light:")
for label, bg in [("75JZ (HBM impair 7-13)", S75JZ),
                  ("936T (pair 4/6 + 2 ST-T)", S936T),
                  ("6G9Q (8 DAUPH Tertiaire)", S6G9Q),
                  ("L1N7 (10 DAUPH + 1 ST-M)", SL1N7),
                  ("RMZ8 (15 DAUPH Tertiaire)", SRMZ8)]:
    cles = [a.get("cle") for a in ad_after if a.get("batiment_groupe_id") == bg]
    print(f"  {label:30s} ({bg[-9:]}) : {len(cles)} adr -> {cles}")
print()
print(">>> AUCUNE MODIFICATION ECRITE. Validation utilisateur requise.")
