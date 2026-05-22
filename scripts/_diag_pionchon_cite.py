#!/usr/bin/env python3
"""Diagnostic 21 CLAUDIUS PIONCHON + 24/26 RUE DE LA CITE (DL).

Terrain : ensemble immobilier ; PAS de mono-propriete malgre SCI CAMAC
detectee sur 21 PIONCHON.

Verifier :
1. Etat light pour les 3 cles
2. Toutes coproprietes sur cles CITE / PIONCHON
3. Pivot BDNB pour identifier bgid commun
4. RNC live ref_cad pour copro couvrante eventuelle
"""
import json, sys, urllib.parse, urllib.request, time, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)

# === 1. Etat light pour les 3 cles ===
print("=" * 80)
print("[1] Etat light - 3 cles cibles")
print("=" * 80)
targets = ["21|RUE|CLAUDIUS PIONCHON", "24|RUE|CITE", "26|RUE|CITE"]
# Aussi tester variantes
variants = ["24|RUE|DE LA CITE","26|RUE|DE LA CITE","24|RUE|CITE","26|RUE|CITE",
            "21|RUE|CLAUDIUS PIONCHON","21|R|CLAUDIUS PIONCHON"]
found = []
for cle in by_cle:
    if "PIONCHON" in cle and "21" in cle.split("|")[0]:
        found.append(cle)
    if "CITE" in cle and cle.split("|")[0] in ("24","26"):
        found.append(cle)

print(f"\nCles light contenant PIONCHON/CITE proches :")
for cle in sorted(set(found)):
    a = by_cle[cle]
    bg = a.get("batiment_groupe_id") or ""
    print(f"\n  '{cle}' :")
    for k in ("batiment_groupe_id","nb_log_bdnb","nb_ventes_logement",
              "nb_ventes_total","numero_immatriculation","nb_lots_habitation",
              "syndic","_syndic_src","_bdnb_match","_fusion_auto",
              "_fusion_cible","_fusion_auto_label","_fusion_auto_sources",
              "sci_proprietaire","sci_nom","longitude","latitude","dans_majic",
              "annee_construction"):
        v = a.get(k)
        if v not in (None,"",[],{},0,0.0):
            print(f"    {k}: {v}")

# Toutes adresses light contenant 'CITE' ou 'PIONCHON'
print()
print("=== Voisins CITE / PIONCHON (light) ===")
for a in ad:
    cle = a.get("cle") or ""
    if "PIONCHON" in cle or ("CITE" in cle and "|" in cle):
        n = cle.split("|")[0]
        bg = a.get("batiment_groupe_id") or "-"
        flags = []
        if a.get("_fusion_auto"): flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
        if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
        if cle in co_by_cle: flags.append("COPRO")
        print(f"  {cle:34s} bgid=...{bg[-9:]} bdnb={a.get('nb_log_bdnb')} "
              f"vlog={a.get('nb_ventes_logement')} {' '.join(flags)}")

# === 2. Copros RNC sur cles CITE / PIONCHON ===
print()
print("=" * 80)
print("[2] Coproprietes RNC sur cles CITE / PIONCHON")
print("=" * 80)
for cle in sorted(co_by_cle):
    if "CITE" in cle or "PIONCHON" in cle:
        for c in co_by_cle[cle]:
            print(f"\n  {cle:34s} :")
            for k in ("numero_immatriculation","nom_copropriete","syndic",
                      "_syndic_src","nb_lots_total","nb_lots_habitation",
                      "adresse"):
                v = c.get(k)
                if v not in (None,""):
                    print(f"    {k}: {str(v)[:120]}")

# === 3. Pivot BDNB pour bgid de 21 PIONCHON ===
print()
print("=" * 80)
print("[3] Pivot BDNB et parcelle pour bgid de 21 PIONCHON")
print("=" * 80)
a21 = by_cle.get("21|RUE|CLAUDIUS PIONCHON")
if not a21:
    print("  21 PIONCHON ABSENT !")
else:
    bg21 = a21.get("batiment_groupe_id")
    print(f"  bgid={bg21}")
    # BDNB live : pivot l_libelle_adr + parcelles
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
           "numero_immat_principal,nb_adresse_valid_ban"
           f"&batiment_groupe_id=in.({bg21})")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            rows = json.loads(r.read())
        for row in rows:
            print(f"  lib_principal='{row.get('libelle_adr_principale_ban','')}'")
            print(f"  nb_log={row.get('nb_log')} nb_log_rnc={row.get('nb_log_rnc')}  "
                  f"annee={row.get('annee_construction')}  "
                  f"usage={(row.get('usage_principal_bdnb_open') or '')[:25]}")
            print(f"  immat_principal={row.get('numero_immat_principal') or '-'}")
            print(f"  l_libelle_adr ({len(row.get('l_libelle_adr') or [])}) :")
            for x in row.get("l_libelle_adr") or []:
                print(f"    . {x}")
    except Exception as e:
        print(f"  ERR: {e}")

    # Parcelles BDNB
    url2 = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
            f"?batiment_groupe_id=eq.{bg21}")
    with urllib.request.urlopen(url2, timeout=15) as r:
        parc = json.loads(r.read())
    print(f"\n  Parcelles BDNB : {[p.get('parcelle_id') for p in parc]}")

    # BAN -> BDNB pour 24/26 CITE
    print(f"\n[3b] BAN -> BDNB autoritaire pour 24/26 CITE")
    for q in ["21 rue claudius pionchon 69003 Lyon",
              "24 rue de la cite 69003 Lyon",
              "26 rue de la cite 69003 Lyon",
              "22 rue de la cite 69003 Lyon",
              "28 rue de la cite 69003 Lyon"]:
        url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
        with urllib.request.urlopen(url, timeout=15) as r:
            feats = json.loads(r.read()).get("features", [])
        if feats:
            p = feats[0]["properties"]
            cle_ban = p.get("id","")
            # query BDNB
            urlb = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
                    f"?cle_interop_adr=eq.{urllib.parse.quote(cle_ban)}&select=batiment_groupe_id")
            try:
                with urllib.request.urlopen(urlb, timeout=15) as r:
                    bgs = [r2["batiment_groupe_id"] for r2 in json.loads(r.read())]
            except Exception: bgs = []
            print(f"  '{q}'")
            print(f"     BAN={cle_ban}  label='{p.get('label','')}'  -> bgid {bgs}")
        time.sleep(0.05)

# === 4. RNC live scan parcelle (cache si dispo) ===
print()
print("=" * 80)
print("[4] RNC live scan parcelle pour bgid 21 PIONCHON")
print("=" * 80)
CACHE_BG = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"
cache_bg = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}
cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8")) if CACHE_RNC.exists() else {}
if a21:
    bg21 = a21.get("batiment_groupe_id")
    parcs_bdnb = cache_bg.get(bg21, [])
    print(f"\n  bgid 21 PIONCHON parcelles BDNB cache : {parcs_bdnb}")
    if not parcs_bdnb:
        # Query live
        url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
               f"?batiment_groupe_id=eq.{bg21}")
        with urllib.request.urlopen(url, timeout=15) as r:
            parc = json.loads(r.read())
        parcs_bdnb = [p.get("parcelle_id") for p in parc]
        print(f"  bgid 21 PIONCHON parcelles BDNB live : {parcs_bdnb}")
    # Convert + query RNC
    for pb in parcs_bdnb:
        pr = "69123383" + pb[8:] if pb[:2]=="69" and pb[5:8]=="000" else pb
        print(f"\n  parcelle RNC {pr} :")
        hits = cache_rnc.get(pr)
        if hits is None:
            # Live
            hits = []
            RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
            TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
            for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
                url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": pr})
                with urllib.request.urlopen(url, timeout=20) as r:
                    data = json.loads(r.read()).get("data", [])
                for row in data:
                    hits.append({
                        "immat": row.get("numero_immatriculation"),
                        "nom": row.get("nom_usage_copropriete",""),
                        "lots_tot": row.get("nombre_total_lots"),
                        "lots_hab": row.get("nombre_lots_usage_habitation"),
                        "col": col,
                    })
                time.sleep(0.05)
        if hits:
            for h in hits:
                print(f"    {h.get('col','?'):26s} {h.get('immat')}  '{h.get('nom','')[:38]}'  "
                      f"lots={h.get('lots_tot')} hab={h.get('lots_hab')}")
        else:
            print(f"    0 hit RNC live sur cette parcelle")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print("  Verification finale a partir des resultats ci-dessus :")
print("  - 21 PIONCHON et 24/26 CITE ont-ils le meme bgid BDNB ?")
print("  - Une copro RNC declare-t-elle ref_cad correspondante ?")
print("  - Si oui : pattern Cambronne RE-FUSE ; sinon : ETIQUETAGE label seul.")
