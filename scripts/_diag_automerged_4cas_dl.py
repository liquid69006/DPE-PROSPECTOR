#!/usr/bin/env python3
"""Diag autoMerged 4 cas suspects (lecture seule).

Pour chaque cle ancre :
  1. Liste ses FA-sources (a.cle ou a._fusion_cible == ancre, _fusion_auto=True)
  2. Pour chaque FA-source, affiche :
     - cle, bgid, nb_ventes_logement, ventes_par_an_logement,
       ventes_par_an BRUT, nb_ventes_total BRUT
  3. Calcule autoMerged.ventes selon la formule UI :
     sum_y (vpa_logement de chaque FA-source)
  4. Verdict : pourquoi le filtre Sans ventes les a (ou pas) exclues
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
ANS = ("2021", "2022", "2023", "2024", "2025")

CIBLES = [
    "166|RUE|BARABAN",
    "170|AVENUE|FELIX FAURE",
    "74|RUE|DAUPHINE",
    "12|RUE|ESPERANCE",
]

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
by_cle = {(a.get("cle") or ""): a for a in ad}

# Index : cible -> [FA sources]
sources_par_cible = {}
for a in ad:
    if not a.get("_fusion_auto"):
        continue
    cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
    if not cible:
        continue
    sources_par_cible.setdefault(cible, []).append(a)

print("=" * 78)
print("DIAG autoMerged 4 cas suspects")
print("=" * 78)

for cle in CIBLES:
    a = by_cle.get(cle)
    print()
    print("=" * 78)
    print(f"ANCRE : {cle}")
    print("=" * 78)
    if not a:
        print("  ABSENT light")
        continue
    bg = a.get("batiment_groupe_id") or ""
    vlog_own = a.get("nb_ventes_logement") or 0
    vpa_log = a.get("ventes_par_an_logement") or {}
    vpa_brut = a.get("ventes_par_an") or {}
    nb_brut = a.get("nb_ventes_total") or 0
    print(f"  bgid               : {bg}")
    print(f"  nb_ventes_logement : {vlog_own}")
    print(f"  ventes_par_an_logement : {vpa_log}")
    print(f"  ventes_par_an BRUT     : {vpa_brut}")
    print(f"  nb_ventes_total BRUT   : {nb_brut}")
    print(f"  _taux_logement_src     : {a.get('_taux_logement_src')}")

    srcs = sources_par_cible.get(cle, [])
    print(f"\n  FA-sources pointant vers {cle} : {len(srcs)}")

    am_log = {y: 0 for y in ANS}
    am_brut = {y: 0 for y in ANS}
    for s in srcs:
        s_cle = s.get("cle")
        s_bg = s.get("batiment_groupe_id") or ""
        s_vlog = s.get("nb_ventes_logement") or 0
        s_vpa_log = s.get("ventes_par_an_logement") or {}
        s_vpa_brut = s.get("ventes_par_an") or {}
        s_nb_brut = s.get("nb_ventes_total") or 0
        s_src = s.get("_taux_logement_src") or ""
        print(f"    --- {s_cle} ---")
        print(f"        bgid (commun? {'OUI' if s_bg == bg else 'NON'}) : {s_bg}")
        print(f"        nb_ventes_logement : {s_vlog}")
        print(f"        ventes_par_an_logement : {s_vpa_log}")
        print(f"        ventes_par_an BRUT     : {s_vpa_brut}")
        print(f"        nb_ventes_total BRUT   : {s_nb_brut}")
        print(f"        _taux_logement_src     : {s_src}")
        for y in ANS:
            am_log[y] += (s_vpa_log.get(y) or 0)
            am_brut[y] += (s_vpa_brut.get(y) or 0)

    print(f"\n  ===> autoMerged.ventes (vpa_logement) : {am_log}")
    am_log_total = sum(am_log.values())
    print(f"  ===> total autoMerged logement : {am_log_total}")
    print(f"  ===> autoMerged.ventes (BRUT)        : {am_brut}")
    am_brut_total = sum(am_brut.values())
    print(f"  ===> total autoMerged BRUT     : {am_brut_total}")

    # Verdict filtre Sans ventes
    print(f"\n  VERDICT FILTRE :")
    keep = (vlog_own == 0
            and not any((vpa_log.get(y) or 0) > 0 for y in ANS)
            and not any(am_log[y] > 0 for y in ANS))
    print(f"    own ventes_par_an_logement vide : {not any((vpa_log.get(y) or 0) > 0 for y in ANS)}")
    print(f"    autoMerged logement vide       : {not any(am_log[y] > 0 for y in ANS)}")
    print(f"    autoMerged BRUT vide           : {not any(am_brut[y] > 0 for y in ANS)}")
    print(f"    -> RETENU dans pop 0-vente ? : {keep}")
    if keep:
        if am_brut_total > 0:
            print(f"    *** AGGREGATION FAIBLE *** : "
                  f"autoMerged BRUT = {am_brut_total} ventes "
                  f"mais autoMerged LOGEMENT = 0")
            print(f"    -> Les FA-sources ont des ventes BRUT mais leur "
                  f"strict (_logement) est resté à 0")
            print(f"    -> Cause probable : les FA-sources n'ont pas eu "
                  f"fix_taux_logement applique (champs *_logement vides)")
        elif am_brut_total == 0 and len(srcs) > 0:
            print(f"    *** vraie 0-vente meme avec FA en place *** : "
                  f"les FA-sources sont aussi a 0 ventes BRUT")
    else:
        print(f"    -> Aurait du etre exclue ; verifier")
