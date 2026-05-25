#!/usr/bin/env python3
"""Light DL : patch usage_principal_bdnb manquant sur 76 adresses cherrypick.

Bug systemique : le cherrypick_indice_de_repetition_2026-05-23 a injecte
76 adresses suffixees (B/A/C/D/T/Q) dans le light sans propager le champ
usage_principal_bdnb. Resultat : asymetrie d'affichage UI (logements
visibles dans la cellule logCell via getEffectiveLog mais NON comptes
dans bgBdnbResid/iloL car usageResid(a)===false sans le champ).

Conditions de detection (3 simultanees) :
  1. _injection_indice present et non null
  2. usage_principal_bdnb absent ou null
  3. nb_log_bdnb > 0 ET type_batiment in ('appartement','immeuble')
     -> garantit residentiel collectif (par construction du criterium)

Patch chirurgical text-based : pour chaque cle detectee, recherche
sa ligne d'ancre dans le light, puis scan forward jusqu'a la ligne
'\"type_chauffage\":', insertion d'une nouvelle ligne juste apres
avec l'indent identique (6 espaces). Aucune re-serialisation du JSON
-> preserve le formatage byte-pour-byte sauf les +76 lignes ajoutees.

Idempotent : si une cle a deja usage_principal_bdnb, elle est SKIP.

Usage :
  python scripts/_fix_usage_bdnb_76_dl.py
"""
import json, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = LIGHT.with_suffix(LIGHT.suffix + ".preusagebdnb76.bak")
INDENT = "      "                          # 6 espaces (niveau adresse)
NEW_LINE = INDENT + '"usage_principal_bdnb": "Résidentiel collectif",\n'

print("=" * 90)
print("Light DL patch : usage_principal_bdnb manquant sur les 76 cherrypick")
print("=" * 90)

# 1. Detection des cibles
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
cibles = []
deja_ok = []
for a in doc["adresses"]:
    if not a.get("_injection_indice"): continue
    if (a.get("nb_log_bdnb") or 0) <= 0: continue
    if a.get("type_batiment") not in ("appartement", "immeuble"): continue
    if a.get("usage_principal_bdnb"):
        deja_ok.append(a.get("cle"))
        continue
    cibles.append(a)
cles_a_patcher = set(a.get("cle") for a in cibles)
print(f"  Adresses light total : {len(doc['adresses'])}")
print(f"  Cibles a patcher     : {len(cibles)}")
print(f"  Deja correctes (skip): {len(deja_ok)}")
if not cibles:
    print("  IDEMPOTENT : rien a patcher"); sys.exit(0)

# 2. Backup
shutil.copy2(LIGHT, BAK)
print(f"  Backup light : {BAK.name}")

# 3. Lecture text + patch chirurgical
lines = LIGHT.read_text(encoding="utf-8").splitlines(keepends=True)
patched = 0
errs = []
i = 0
while i < len(lines):
    line = lines[i]
    # Detection ancre : ligne '      "cle": "XXX",'
    if '"cle":' in line and line.strip().startswith('"cle"'):
        # Parser la cle exacte
        try:
            cle_val = line.split('"cle":', 1)[1].strip().rstrip(",").strip().strip('"')
        except Exception:
            i += 1; continue
        if cle_val in cles_a_patcher:
            # Scan forward (max 60 lignes) pour trouver '      "type_chauffage":'
            j = i + 1
            target = None
            while j < min(i + 60, len(lines)):
                if '"type_chauffage":' in lines[j] and lines[j].strip().startswith('"type_chauffage"'):
                    target = j
                    break
                # Securite : si on tombe sur une nouvelle cle, on a depasse
                if '"cle":' in lines[j] and lines[j].strip().startswith('"cle"'):
                    break
                j += 1
            if target is None:
                errs.append((cle_val, "type_chauffage line not found"))
            else:
                lines.insert(target + 1, NEW_LINE)
                patched += 1
                # Saut au-dela de la ligne inseree pour ne pas re-iterer
                i = target + 1
    i += 1

if errs:
    print(f"  ERRORS : {len(errs)} cles non patchees")
    for cle, why in errs: print(f"    {cle:<40} {why}")
print(f"  Patched : {patched} / {len(cibles)} cibles")

# 4. Reecriture
LIGHT.write_text("".join(lines), encoding="utf-8")
print(f"  Light reecrit : {LIGHT.name} ({LIGHT.stat().st_size:,} bytes)")

# 5. Verif post-patch
doc_after = json.loads(LIGHT.read_text(encoding="utf-8"))
ok_after = sum(1 for a in doc_after["adresses"] if a.get("cle") in cles_a_patcher
                and a.get("usage_principal_bdnb") == "Résidentiel collectif")
print(f"  Verif post-patch : {ok_after} / {len(cibles)} ont usage_principal_bdnb='Résidentiel collectif'")
if ok_after != len(cibles):
    print(f"!! ECHEC : {len(cibles)-ok_after} cles manquantes apres patch"); sys.exit(10)

# 6. Top 5 par nb_log_bdnb
sorted_cibles = sorted(cibles, key=lambda a: -(a.get("nb_log_bdnb") or 0))
print()
print("=" * 90)
print(f"  TOP 5 cibles patchees (par nb_log_bdnb DESC) :")
for a in sorted_cibles[:5]:
    print(f"    {a.get('cle'):<40} bdnb={a.get('nb_log_bdnb'):>4}  tbat={a.get('type_batiment')}")
print()
print(f"  Sigma nb_log_bdnb sur les {len(cibles)} cibles : {sum(a.get('nb_log_bdnb') or 0 for a in cibles)} lgts")
print("=" * 90)
print(f">>> SUCCES : {patched} cle(s) patchees, light +{patched} lignes")
print("=" * 90)
