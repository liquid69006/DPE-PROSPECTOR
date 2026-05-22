#!/usr/bin/env python3
"""Diagnostic 3 ROSSAN + 10 ST MAXIMIN (parc BC0108) - 20 lgts BDNB
mais MAJIC 1 SIREN SAINT PHILIPPE = 2/2 lots. Lecture seule.
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = r'C:\Users\Station 5\majic_locaux2_2025.parquet'
MAJIC1 = r'C:\Users\Station 5\majic_locaux_2025.parquet'

print("=" * 76)
print("DIAG 3 ROSSAN + 10 ST MAXIMIN  (parc BC0108)")
print("=" * 76)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad, co = doc["adresses"], doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)

# [1] Light
print()
print("[1] Light - cles ROSSAN et ST MAXIMIN proches")
for cle in ("3|RUE|ROSSAN","5|RUE|ROSSAN","1|RUE|ROSSAN",
            "10|RUE|ST MAXIMIN","8|RUE|ST MAXIMIN","12|RUE|ST MAXIMIN"):
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:24s} ABSENT light"); continue
    bg = a.get("batiment_groupe_id") or ""
    flags = []
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
    if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
    if cle in co_by_cle: flags.append("COPRO")
    print(f"  {cle:24s} bgid=...{bg[-9:]} bdnb={a.get('nb_log_bdnb')} "
          f"vlog={a.get('nb_ventes_logement')} sci={a.get('sci_nom') or '-'}  {' '.join(flags)}")

# [2] Copros snapshot ROSSAN/MAXIMIN
print()
print("[2] Coproprietes RNC snapshot ROSSAN / ST MAXIMIN")
found = False
for c in co:
    cle = c.get("cle_adresse") or ""
    nom = c.get("nom_copropriete","") or ""
    if "ROSSAN" in cle or "MAXIMIN" in cle or "ROSSAN" in nom or "MAXIMIN" in nom:
        found = True
        print(f"  {cle:24s} {c.get('numero_immatriculation')} '{nom[:38]}' "
              f"tot={c.get('nb_lots_total')} hab={c.get('nb_lots_habitation')}")
if not found:
    print("  Aucune copro snapshot avec ROSSAN/MAXIMIN dans cle ou nom")

# [3] BAN -> BDNB autorite
print()
print("[3] BAN -> BDNB autoritaire pour 3 ROSSAN + 10 ST MAXIMIN + voisins")
def ban(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=2&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("features", [])
    except Exception: return []
def bdnb(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return [r2["batiment_groupe_id"] for r2 in json.loads(r.read())]
    except Exception: return []
for q in ["3 rue rossan 69003 Lyon","5 rue rossan 69003 Lyon","1 rue rossan 69003 Lyon",
          "10 rue saint maximin 69003 Lyon","8 rue saint maximin 69003 Lyon",
          "12 rue saint maximin 69003 Lyon"]:
    feats = ban(q)
    if feats:
        p = feats[0]["properties"]
        bgs = bdnb(p["id"])
        print(f"  {q:42s} BAN={p.get('id')} -> bgid {bgs}")
    else:
        print(f"  {q:42s} BAN 0 feature")
    time.sleep(0.05)

# [4] BDNB pivot bgid 3 ROSSAN
a3r = by_cle["3|RUE|ROSSAN"]
bg3r = a3r.get("batiment_groupe_id")
print()
print(f"[4] BDNB pivot bgid {bg3r} :")
url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
       "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
       "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
       "numero_immat_principal,nb_adresse_valid_ban"
       f"&batiment_groupe_id=in.({bg3r})")
with urllib.request.urlopen(url, timeout=15) as r:
    for row in json.loads(r.read()):
        print(f"  lib_principal='{row.get('libelle_adr_principale_ban','')}'")
        print(f"  nb_log={row.get('nb_log')}  nb_log_rnc={row.get('nb_log_rnc')}  "
              f"annee={row.get('annee_construction')}  immat={row.get('numero_immat_principal') or '-'}  "
              f"usage={(row.get('usage_principal_bdnb_open') or '')[:25]}")
        for x in row.get("l_libelle_adr") or []:
            print(f"    . {x}")

# [5] MAJIC complet sur BC0108
print()
print("[5] MAJIC locaux2 sur parcelle BC0108 (Personnes Morales seulement)")
tbl = pq.read_table(MAJIC, filters=[
    ("departement","=","69"),("code_commune","=","383"),
    ("section","=","BC"),("numero_parcelle","=",108)])
df = tbl.to_pandas()
print(f"  {len(df)} lots MAJIC PM")
if not df.empty:
    for _, r in df.iterrows():
        adr = (str(r.get('numero_voirie') or '').lstrip('0')
               + (r.get('indice_de_repetition') or '')
               + ' ' + (r.get('nature_voie') or '')
               + ' ' + (r.get('nom_voie') or ''))
        print(f"    bati={r.get('batiment','?'):2s} ent={r.get('entree','?')} "
              f"niv={r.get('niveau','?')} porte={r.get('porte','?')}  "
              f"adr='{adr.strip()}'  SIREN={r.get('numero_siren')}  "
              f"denom='{(r.get('denomination') or '')[:30]}'  "
              f"droit='{r.get('code_droit_libelle')}'")

# [5b] MAJIC locaux1 (foncier) - peut-etre y a-t-il aussi des PP ?
print()
print("[5b] MAJIC locaux1 (foncier 31 col) sur parcelle BC0108")
try:
    tbl1 = pq.read_table(MAJIC1, filters=[
        ("departement","=","69"),("code_commune","=","383"),
        ("section","=","BC"),("numero_parcelle","=",108)])
    df1 = tbl1.to_pandas()
    print(f"  {len(df1)} entrees MAJIC foncier")
    if not df1.empty:
        # Distribution droits + groupe_personne
        print(f"  Distribution code_droit_libelle :")
        for k, v in df1['code_droit_libelle'].value_counts().items():
            print(f"    {k}: {v}")
        print(f"  Distribution groupe_personne_libelle :")
        for k, v in df1['groupe_personne_libelle'].value_counts().items():
            print(f"    {k}: {v}")
        print(f"  Total contenance_parcelle_centiare : "
              f"{df1['contenance_parcelle_centiare'].iloc[0] if 'contenance_parcelle_centiare' in df1.columns else '?'}")
except Exception as e:
    print(f"  ERR: {e}")

# [6] RNC live scan parcelle BC0108
print()
print("[6] RNC live scan parcelle 69123383BC0108")
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
hits_count = 0
for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
    url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": "69123383BC0108"})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read()).get("data", [])
    except Exception as e:
        data = []
    for row in data:
        hits_count += 1
        print(f"  {col}: {row.get('numero_immatriculation')} "
              f"'{row.get('nom_usage_copropriete','')[:38]}'  "
              f"lots={row.get('nombre_total_lots')} "
              f"hab={row.get('nombre_lots_usage_habitation')}")
        print(f"    adr_ref='{row.get('adresse_reference','')[:80]}'")
        for k in ("adresse_complementaire_1","adresse_complementaire_2",
                  "adresse_complementaire_3","adresse_complementaire_4"):
            v = row.get(k)
            if v: print(f"    {k}='{v}'")
        print(f"    syndic={row.get('nom_personne_morale','')}  "
              f"mandat={row.get('mandat_en_cours','')}")
        print(f"    date_immat={row.get('date_immatriculation')}  "
              f"date_reglement={row.get('date_reglement_copropriete')}")
    time.sleep(0.05)
if hits_count == 0:
    print("  AUCUN hit RNC live sur cette parcelle")

# [7] SIREN SAINT PHILIPPE - autres biens
print()
print("[7] SIREN SAINT PHILIPPE - autres biens dans MAJIC dep 69")
if not df.empty and df['numero_siren'].notna().any():
    sir = str(df['numero_siren'].dropna().iloc[0])
    denom = df['denomination'].iloc[0]
    print(f"  SIREN = {sir} / denomination = {denom}")
    tbl_all = pq.read_table(MAJIC, filters=[
        ("departement","=","69"),("numero_siren","=",sir)])
    df_all = tbl_all.to_pandas()
    print(f"  Total lots MAJIC dep 69 : {len(df_all)}")
    if not df_all.empty:
        print(f"  Communes : {df_all['nom_commune'].value_counts().to_dict()}")
        parcs = df_all.groupby(['code_commune','section','numero_parcelle']).size().reset_index(name='nb')
        print(f"  Parcelles distinctes : {len(parcs)}")
        for _, r in parcs.iterrows():
            adr_p = df_all[(df_all['code_commune']==r['code_commune'])
                           & (df_all['section']==r['section'])
                           & (df_all['numero_parcelle']==r['numero_parcelle'])]
            first = adr_p.iloc[0]
            adr_s = (str(first.get('numero_voirie') or '').lstrip('0')
                     + (first.get('indice_de_repetition') or '')
                     + ' ' + (first.get('nature_voie') or '')
                     + ' ' + (first.get('nom_voie') or ''))
            print(f"    cmm={r['code_commune']} {r['section']}/{r['numero_parcelle']:04d} : "
                  f"{r['nb']} lot(s)  -  '{adr_s.strip()}'  ({first.get('nom_commune','')})")
