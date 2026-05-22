#!/usr/bin/env python3
"""Diagnostic doublon C: 155+156 FELIX FAURE (bgid EBHY).

Phase 1 (lecture seule) :
- Etat actuel des adresses 149, 151, 155, 156, 158 FELIX FAURE
  + 26 LACASSAGNE (tous candidats EBHY ou faux-matching)
- Resolution BDNB live des vrais bgid via libelle_adr_principale_ban
  (filtre ilike) pour 156 + 158 + 149 + 26 LACASSAGNE
- Verification metadata._correctif_* anterieur sur ces cles
"""
import json, sys, urllib.parse, urllib.request, time, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad  = doc.get("adresses") or []
co  = doc.get("coproprietes") or []
md  = doc.get("metadata") or {}

CIBLES = [
    "149|AVENUE|FELIX FAURE",
    "151|AVENUE|FELIX FAURE",
    "155|AVENUE|FELIX FAURE",
    "156|AVENUE|FELIX FAURE",
    "158|AVENUE|FELIX FAURE",
    "26|AVENUE|LACASSAGNE",
]

by_cle = {(a.get("cle") or ""): a for a in ad}

print("=" * 72)
print("DIAGNOSTIC doublon C - 155/156 FELIX FAURE (bgid EBHY)")
print("=" * 72)
print()
print("[1] Etat actuel des 6 cles dans le light")
for cle in CIBLES:
    a = by_cle.get(cle)
    if not a:
        print(f"  - {cle:30s}  ABSENTE")
        continue
    bg = a.get("batiment_groupe_id") or ""
    bg9 = bg[-9:] if bg else ""
    print(f"  - {cle:30s}  bgid=...{bg9}  nb_log_bdnb={a.get('nb_log_bdnb')}  "
          f"vlog={a.get('nb_ventes_logement')}  immat={a.get('numero_immatriculation') or '-'}")
    if a.get("_fusion_auto_label"):
        print(f"      label='{a['_fusion_auto_label']}'  sources={a.get('_fusion_auto_sources')}")
    if a.get("_fusion_auto"):
        print(f"      _fusion_auto=True (fused dans une chaine)")
    if a.get("_bdnb_match"):
        print(f"      _bdnb_match={a['_bdnb_match']}")

# Verif correctif anterieur
print()
print("[2] Verification metadata._correctif_* prealable")
corr_keys = [k for k in md.keys() if k.startswith("_correctif")]
print(f"  metadata._correctif_* presents : {len(corr_keys)}")
felix_corr = [k for k in corr_keys if "FELIX" in k.upper() or "EBHY" in k.upper() or "156" in k]
for k in felix_corr:
    print(f"  - {k}: {md[k] if isinstance(md[k], str) else json.dumps(md[k], ensure_ascii=False)[:200]}")
if not felix_corr:
    print("  -> aucun correctif anterieur sur Felix Faure/EBHY/156")

# Verif copro RNC sur les cles
print()
print("[3] Coproprietes RNC sur ces cles (cle_adresse)")
co_by_cle = {}
for c in co:
    cle = c.get("cle_adresse") or ""
    co_by_cle.setdefault(cle, []).append(c)
for cle in CIBLES:
    lst = co_by_cle.get(cle, [])
    if lst:
        for c in lst:
            print(f"  - {cle:30s}  {c.get('numero_immatriculation')}  {c.get('nom_copropriete','')[:50]}")
    else:
        print(f"  - {cle:30s}  (aucune copro RNC)")

# Resolution BDNB live des bgids reels
print()
print("[4] Resolution BDNB live (libelle_adr_principale_ban ilike)")
print("  Query: api.bdnb.io rel_batiment_groupe_adresse + bati complet")
BDNB_URL = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
            "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
            "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open"
            "&libelle_adr_principale_ban=ilike.")

QUERIES = [
    ("156 avenue felix faure 69003*", "156 FELIX FAURE"),
    ("158 avenue felix faure 69003*", "158 FELIX FAURE"),
    ("149 avenue felix faure 69003*", "149 FELIX FAURE"),
    ("26 avenue lacassagne 69003*", "26 LACASSAGNE"),
    ("151 avenue felix faure 69003*", "151 FELIX FAURE (controle)"),
    ("155 avenue felix faure 69003*", "155 FELIX FAURE (controle)"),
]

results = {}
for pat, label in QUERIES:
    url = BDNB_URL + urllib.parse.quote(pat)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.loads(r.read())
    except Exception as e:
        print(f"  ! erreur {label}: {e}")
        rows = []
    results[label] = rows
    print(f"\n  >> {label}")
    if not rows:
        print(f"     0 row (orphelin BDNB ou pattern non match)")
    for row in rows[:5]:
        bg = row.get("batiment_groupe_id","")
        bg9 = bg[-9:] if bg else ""
        print(f"     bgid=...{bg9}  nb_log={row.get('nb_log')}  nb_log_rnc={row.get('nb_log_rnc')}  "
              f"annee={row.get('annee_construction')}  usage={(row.get('usage_principal_bdnb_open') or '')[:25]}")
        print(f"       lib_principal='{row.get('libelle_adr_principale_ban','')}'")
        ll = row.get("l_libelle_adr") or []
        if ll and len(ll) <= 6:
            for x in ll: print(f"         . {x}")
        elif ll:
            for x in ll[:4]: print(f"         . {x}")
            print(f"         . (... +{len(ll)-4})")
    time.sleep(0.15)

print()
print("[5] Resume des bgids reels detectes")
target_bgids = {}
for label, rows in results.items():
    if rows:
        target_bgids[label] = rows[0].get("batiment_groupe_id")
    else:
        target_bgids[label] = None
for label, bg in target_bgids.items():
    print(f"  - {label:32s} -> {bg or 'ORPHELIN BDNB'}")
