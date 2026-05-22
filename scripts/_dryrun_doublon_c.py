#!/usr/bin/env python3
"""DRYRUN doublon C: 155+156 FELIX FAURE (bgid EBHY) - simulation complete.

Periode : pair 150-162 FF (faux-matching DBFL+EBHY+EZPF) + impair 151 FF
+ INJECT 149 FF. NE TOUCHE PAS 26 LACASSAGNE (programme 2022 fused 24/26
via copro RNC immat 6YKR-D8DU = autorite legitime).

Mecanisme :
- RE-POINT 150, 152, 154 (FA->148) : bgid DBFL -> 59S6-3RB7
- RE-POINT 156 (ancre fuse 158)    : bgid EBHY  -> 59S6-3RB7
- RE-POINT 158 (FA->156)           : bgid EBHY  -> 59S6-3RB7
- RE-POINT 160                     : bgid EZPF  -> 59S6-3RB7
- RE-POINT 151 (DBFL faux-match)   : bgid DBFL  -> EBHY (cas A integre)
- INJECT 149 label-only            : nouvelle adresse FA->155 EBHY
- Retire label '148/150/152/154' sur 148 : devient mono-num
- Nouvelle ancre 162 (deja 59S6) : label '150/152/154/156/158/160/162 FELIX FAURE'
  src = [150,152,154,156,158,160] FF
- Ancre 155 EBHY (nouveau label) : '149/151/155 FELIX FAURE' src=[149,151] FF
- 156 ancien-ancre : devient FA -> 162 (avec maj label/src)
- 158 ancien-FA -> 156 : devient FA -> 162

Adresses touchees : 148(-label), 150, 151, 152, 154, 155(+label), 156, 158,
160, 162(+label), 149(INJECT).
Total : 11 adresses modifiees.
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

# Bgids cibles (autorite BAN)
EBHY = "bdnb-bg-V431-EBHY-Y74D"   # 67 lgts, 1992, impair angle 149/151/155 + faux pivot 26 LAC
S59S6 = "bdnb-bg-AVBW-59S6-3RB7"  # 51 lgts, 1995, pair 150-162
DBFL  = "bdnb-bg-AX5E-DBFL-VSF4"  # 463 lgts, 1972, 148 seul
EZPF  = "bdnb-bg-DGQE-EZPF-8JC4"  # 13 lgts, 1880, lib=161 FF (impair)

# Snapshot AVANT
print("=" * 76)
print("DRYRUN doublon C - simulation complete")
print("=" * 76)
print()
print("AVANT - inventaire bgids cibles dans light:")
for label, bg in [("EBHY (vrai impair)", EBHY), ("59S6 (vrai pair)", S59S6),
                  ("DBFL (148 mega)", DBFL), ("EZPF (161 impair)", EZPF)]:
    cles = [a.get("cle") for a in ad if a.get("batiment_groupe_id") == bg]
    print(f"  {label:24s} ({bg[-9:]}) : {len(cles)} adresse(s) -> {cles}")
print()

# Operations en simulation
ops = []

# 1. RE-POINT vers 59S6 (cote pair)
RE_TO_59S6 = ["150|AVENUE|FELIX FAURE", "152|AVENUE|FELIX FAURE",
              "154|AVENUE|FELIX FAURE", "156|AVENUE|FELIX FAURE",
              "158|AVENUE|FELIX FAURE", "160|AVENUE|FELIX FAURE"]
for cle in RE_TO_59S6:
    a = by_cle.get(cle)
    if not a:
        ops.append((cle, "MANQUE_LIGHT", "skip"))
        continue
    bg_old = a.get("batiment_groupe_id")
    if bg_old == S59S6:
        ops.append((cle, "DEJA_OK", "skip"))
        continue
    ops.append((cle, "RE-POINT", f"{bg_old[-9:]} -> {S59S6[-9:]}"))

# 2. RE-POINT 151 -> EBHY (cote impair)
a151 = by_cle.get("151|AVENUE|FELIX FAURE")
ops.append(("151|AVENUE|FELIX FAURE", "RE-POINT",
            f"{a151['batiment_groupe_id'][-9:]} -> {EBHY[-9:]}"))

# 3. INJECT 149 label-only
ops.append(("149|AVENUE|FELIX FAURE", "INJECT",
            f"label-only FA->155 EBHY"))

# 4. Restructuration chaines fusion
print("OPERATIONS (11 attendues) :")
for cle, kind, detail in ops:
    print(f"  [{kind:10s}] {cle:30s} {detail}")
print()
print("CHAINES FUSION post-fix :")
print("  148 FF (DBFL ancre) : label retire (148 seul, ex-label '148/150/152/154')")
print("  162 FF (59S6 ancre) : NOUVEAU label '150/152/154/156/158/160/162 FELIX FAURE'")
print("                       NOUVEAU sources=[150,152,154,156,158,160]")
print("  155 FF (EBHY ancre) : NOUVEAU label '149/151/155 FELIX FAURE'")
print("                       NOUVEAU sources=[149,151]")
print("  156 FF              : ex-ancre -> FA=True _fusion_cible='150/152/154/.../162'")
print("                       label/sources retires")
print("  150,152,154,158,160 : FA=True _fusion_cible='150/152/154/.../162'")
print("  151, 149 (INJECT)   : FA=True _fusion_cible='149/151/155 FELIX FAURE'")
print()

# --- Calcul Delta parc (dedup-bgid strict logement) ---
def parc_strict(ad_list):
    """Reproduit la logique parc DL strict logement (dedup bgid)."""
    total = 0
    seen = set()
    for a in ad_list:
        nb_log = to_int(a.get("nb_lots_habitation"))
        if nb_log > 0:
            total += nb_log
            continue
        bg = a.get("batiment_groupe_id") or ""
        if bg and bg in seen:
            continue
        if bg:
            seen.add(bg)
        total += to_int(a.get("nb_log_bdnb"))
    return total

# Construction snapshot APRES
ad_after = copy.deepcopy(ad)
by_after = {a.get("cle") or "": a for a in ad_after}

# 1. RE-POINT 150/152/154/156/158/160 -> 59S6 + maj nb_log_bdnb=51
for cle in RE_TO_59S6:
    a = by_after.get(cle)
    if not a: continue
    a["batiment_groupe_id"] = S59S6
    a["nb_log_bdnb"] = 51
    a["annee_construction"] = 1995
    a["_bdnb_match"] = "correctif_doublon_c_re_point"

# 2. RE-POINT 151 -> EBHY + maj nb_log_bdnb=67
a151 = by_after.get("151|AVENUE|FELIX FAURE")
a151["batiment_groupe_id"] = EBHY
a151["nb_log_bdnb"] = 67
a151["annee_construction"] = 1992
a151["_bdnb_match"] = "correctif_doublon_c_re_point"

# 3. INJECT 149 (clone de 155 mais FA label-only)
a155 = by_after.get("155|AVENUE|FELIX FAURE")
a149 = {
    "cle": "149|AVENUE|FELIX FAURE",
    "adresse": "149 AVENUE FELIX FAURE",
    "longitude": a155.get("longitude"),
    "latitude": a155.get("latitude"),
    "code_iris": a155.get("code_iris"),
    "_coord_source": "clone_doublon_c",
    "dans_majic": False,  # absente MAJIC par definition
    "sci_proprietaire": "non",
    "ventes_par_an": {},
    "nb_ventes_total": 0,
    "nb_log_bdnb": 67,
    "annee_construction": 1992,
    "classe_dpe": a155.get("classe_dpe"),
    "type_batiment": "immeuble",
    "type_chauffage": a155.get("type_chauffage"),
    "batiment_groupe_id": EBHY,
    "_bdnb_match": "correctif_doublon_c_inject",
    "_fusion_auto": True,
    "_fusion_cible": "149/151/155 FELIX FAURE",
    "ventes_par_an_logement": {},
    "nb_ventes_logement": 0,
    "taux_rotation_logement": 0.0,
    "classement_rotation_logement": "Fige",
    "_taux_logement_src": "copie_sans_dependance",
    "usage_principal_bdnb": "Residentiel collectif",
    "_usage_bdnb_src": "correctif_doublon_c",
}
ad_after.append(a149)

# 4. Restructuration chaines fusion
# 148 : retirer label/sources
a148 = by_after["148|AVENUE|FELIX FAURE"]
a148.pop("_fusion_auto_label", None)
a148.pop("_fusion_auto_sources", None)

# 162 : nouvelle ancre 59S6
a162 = by_after["162|AVENUE|FELIX FAURE"]
a162["_fusion_auto_label"] = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"
a162["_fusion_auto_sources"] = [
    "150|AVENUE|FELIX FAURE","152|AVENUE|FELIX FAURE",
    "154|AVENUE|FELIX FAURE","156|AVENUE|FELIX FAURE",
    "158|AVENUE|FELIX FAURE","160|AVENUE|FELIX FAURE",
]

# 155 : nouvelle ancre EBHY
a155b = by_after["155|AVENUE|FELIX FAURE"]
a155b["_fusion_auto_label"] = "149/151/155 AVENUE FELIX FAURE"
a155b["_fusion_auto_sources"] = ["149|AVENUE|FELIX FAURE","151|AVENUE|FELIX FAURE"]

# 156 : devient FA fused vers 162 (perd ancre)
a156 = by_after["156|AVENUE|FELIX FAURE"]
a156.pop("_fusion_auto_label", None)
a156.pop("_fusion_auto_sources", None)
a156["_fusion_auto"] = True
a156["_fusion_cible"] = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"

# 150/152/154 : FA cible passe de '148/150/152/154' a la nouvelle chaine 162
for cle in ["150|AVENUE|FELIX FAURE","152|AVENUE|FELIX FAURE","154|AVENUE|FELIX FAURE"]:
    a = by_after[cle]
    a["_fusion_auto"] = True
    a["_fusion_cible"] = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"

# 158 : FA cible nouvelle chaine 162
a158 = by_after["158|AVENUE|FELIX FAURE"]
a158["_fusion_auto"] = True
a158["_fusion_cible"] = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"

# 160 : FA cible nouvelle chaine 162
a160 = by_after["160|AVENUE|FELIX FAURE"]
a160["_fusion_auto"] = True
a160["_fusion_cible"] = "150/152/154/156/158/160/162 AVENUE FELIX FAURE"

# 151 : FA cible nouvelle chaine 155 EBHY
a151b = by_after["151|AVENUE|FELIX FAURE"]
a151b["_fusion_auto"] = True
a151b["_fusion_cible"] = "149/151/155 AVENUE FELIX FAURE"

# Recalcul parc
parc_avant = parc_strict(ad)
parc_apres = parc_strict(ad_after)

print("PARC DL strict logement (dedup bgid) :")
print(f"  AVANT  : {parc_avant}")
print(f"  APRES  : {parc_apres}")
print(f"  DELTA  : {parc_apres - parc_avant:+d}")
print()
print(f"Adresses light : {len(ad)} -> {len(ad_after)}  (+1 INJECT 149)")
print()

# Snapshot APRES par bgid
print("APRES - inventaire bgids cibles dans light:")
for label, bg in [("EBHY (vrai impair)", EBHY), ("59S6 (vrai pair)", S59S6),
                  ("DBFL (148 mega)", DBFL), ("EZPF (161 impair)", EZPF)]:
    cles = [a.get("cle") for a in ad_after if a.get("batiment_groupe_id") == bg]
    print(f"  {label:24s} ({bg[-9:]}) : {len(cles)} adresse(s) -> {cles}")
print()
print("VERIFICATIONS :")
print(f"  - DBFL n'a plus que 148 (mega 463 lgts)         : "
      f"{'OUI' if [a.get('cle') for a in ad_after if a.get('batiment_groupe_id')==DBFL] == ['148|AVENUE|FELIX FAURE'] else 'NON'}")
print(f"  - EZPF n'a plus aucune adresse light (orpheline) : "
      f"{'OUI' if not [a.get('cle') for a in ad_after if a.get('batiment_groupe_id')==EZPF] else 'NON'}")
print(f"  - 59S6 a 7 adresses (150-162 pairs)              : "
      f"{'OUI' if len([a for a in ad_after if a.get('batiment_groupe_id')==S59S6])==7 else 'NON'}")
print(f"  - EBHY a 3 adresses (149,151,155)                : "
      f"{'OUI' if len([a for a in ad_after if a.get('batiment_groupe_id')==EBHY])==3 else 'NON'}")
print()
print(">>> AUCUNE MODIFICATION ECRITE. Validation utilisateur requise avant patch.")
