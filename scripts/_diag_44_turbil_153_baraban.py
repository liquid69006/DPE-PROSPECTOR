#!/usr/bin/env python3
"""Diagnostic 44 RUE TURBIL + 153 RUE BARABAN (terrain : meme ensemble).
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = r'C:\Users\Station 5\majic_locaux2_2025.parquet'

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad, co = doc["adresses"], doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)
co_by_immat = {c.get("numero_immatriculation"): c
               for c in co if c.get("numero_immatriculation")}

print("=" * 76)
print("DIAG 44 RUE TURBIL + 153 RUE BARABAN")
print("=" * 76)

# [1] Etat light
print()
print("[1] Etat light :")
for cle in ("44|RUE|TURBIL","42|RUE|TURBIL","46|RUE|TURBIL",
            "153|RUE|BARABAN","151|RUE|BARABAN","155|RUE|BARABAN"):
    a = by_cle.get(cle)
    if not a:
        print(f"  {cle:24s} ABSENT light"); continue
    bg = a.get("batiment_groupe_id") or ""
    flags=[]
    if a.get("_fusion_auto"): flags.append("FA")
    if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label']}'")
    if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
    if cle in co_by_cle: flags.append("COPRO")
    print(f"  {cle:24s} bgid=...{bg[-9:]} bdnb={a.get('nb_log_bdnb')} "
          f"vlog={a.get('nb_ventes_logement')} sci={a.get('sci_nom') or '-'}  {' '.join(flags)}")

# [2] Copros TURBIL / BARABAN
print()
print("[2] Coproprietes RNC snapshot TURBIL / 150-160 BARABAN :")
for c in co:
    cle = c.get("cle_adresse") or ""
    nom = c.get("nom_copropriete","") or ""
    if "TURBIL" in cle or "TURBIL" in nom.upper():
        print(f"  TUR  {cle:24s} {c.get('numero_immatriculation')} '{nom[:38]}' tot={c.get('nb_lots_total')} hab={c.get('nb_lots_habitation')}")
    elif "BARABAN" in cle:
        n = cle.split("|")[0]
        try: nn = int(n.rstrip("B").rstrip("T"))
        except: nn = 0
        if 150 <= nn <= 160:
            print(f"  BAR  {cle:24s} {c.get('numero_immatriculation')} '{nom[:38]}' tot={c.get('nb_lots_total')} hab={c.get('nb_lots_habitation')}")

# [3] BAN -> BDNB autorite
print()
print("[3] BAN -> BDNB autoritaire :")
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
for q in ["44 rue turbil 69003 Lyon","42 rue turbil 69003 Lyon","46 rue turbil 69003 Lyon",
          "153 rue baraban 69003 Lyon","151 rue baraban 69003 Lyon","155 rue baraban 69003 Lyon"]:
    feats = ban(q)
    if feats:
        p = feats[0]["properties"]
        bgs = bdnb(p["id"])
        print(f"  {q:40s} BAN={p.get('id')} -> bgid {bgs}")
    else:
        print(f"  {q:40s} BAN 0 feature")
    time.sleep(0.05)

# [4] Pivot BDNB 44 TURBIL
a44 = by_cle.get("44|RUE|TURBIL")
if a44:
    bg44 = a44.get("batiment_groupe_id")
    print()
    print(f"[4] BDNB pivot bgid 44 TURBIL = {bg44} :")
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
           "numero_immat_principal,nb_adresse_valid_ban"
           f"&batiment_groupe_id=in.({bg44})")
    with urllib.request.urlopen(url, timeout=15) as r:
        for row in json.loads(r.read()):
            print(f"  lib_principal='{row.get('libelle_adr_principale_ban','')}'")
            print(f"  nb_log={row.get('nb_log')} nb_log_rnc={row.get('nb_log_rnc')}  "
                  f"annee={row.get('annee_construction')}  immat={row.get('numero_immat_principal') or '-'}")
            for x in row.get("l_libelle_adr") or []:
                print(f"    . {x}")
    # Parcelles BDNB
    url2 = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
            f"?batiment_groupe_id=eq.{bg44}")
    with urllib.request.urlopen(url2, timeout=15) as r:
        parc = json.loads(r.read())
    print(f"  Parcelles BDNB : {[p.get('parcelle_id') for p in parc]}")

# [5] MAJIC sur parcelle 44 TURBIL
print()
print("[5] MAJIC sur parcelle 44 TURBIL :")
if a44:
    parc_bdnb_44 = parc[0]['parcelle_id'] if parc else None
    if parc_bdnb_44:
        sec = parc_bdnb_44[8:10]; plan = int(parc_bdnb_44[10:])
        tbl = pq.read_table(MAJIC, filters=[
            ("departement","=","69"),("code_commune","=","383"),
            ("section","=",sec),("numero_parcelle","=",plan)])
        df = tbl.to_pandas()
        print(f"  parc {parc_bdnb_44} : {len(df)} lots MAJIC PM")
        if not df.empty:
            df['addr'] = (df['numero_voirie'].fillna('').astype(str).str.lstrip('0')
                          + df['indice_de_repetition'].fillna('').astype(str)
                          + ' ' + df['nature_voie'].fillna('') + ' '
                          + df['nom_voie'].fillna(''))
            adr_uniq = df['addr'].value_counts().to_dict()
            for adr, n in adr_uniq.items():
                print(f"    {n:3d} lot(s)  '{adr.strip()}'")
            sirens = df['numero_siren'].dropna().value_counts().to_dict()
            print(f"  SIRENs distincts : {len(sirens)}")
            for sir, n in sirens.items():
                denom = df[df['numero_siren']==sir]['denomination'].iloc[0]
                print(f"    {sir} : {n} lots  -  {denom[:40]}")

# [6] Pivot BDNB 153 BARABAN si present light
a153 = by_cle.get("153|RUE|BARABAN")
if a153:
    bg153 = a153.get("batiment_groupe_id")
    print()
    print(f"[6] BDNB pivot 153 BARABAN bgid {bg153} :")
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,annee_construction,numero_immat_principal"
           f"&batiment_groupe_id=in.({bg153})")
    with urllib.request.urlopen(url, timeout=15) as r:
        for row in json.loads(r.read()):
            print(f"  lib_principal='{row.get('libelle_adr_principale_ban','')}'")
            print(f"  nb_log={row.get('nb_log')}  annee={row.get('annee_construction')}  "
                  f"immat_principal={row.get('numero_immat_principal') or '-'}")
            for x in row.get("l_libelle_adr") or []:
                print(f"    . {x}")
    # Parcelles
    url2 = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
            f"?batiment_groupe_id=eq.{bg153}")
    with urllib.request.urlopen(url2, timeout=15) as r:
        parc153 = json.loads(r.read())
    print(f"  Parcelles BDNB : {[p.get('parcelle_id') for p in parc153]}")
    # MAJIC
    if parc153:
        p0 = parc153[0]['parcelle_id']
        sec = p0[8:10]; plan = int(p0[10:])
        tbl = pq.read_table(MAJIC, filters=[
            ("departement","=","69"),("code_commune","=","383"),
            ("section","=",sec),("numero_parcelle","=",plan)])
        df = tbl.to_pandas()
        print(f"\n  MAJIC parc {p0} : {len(df)} lots PM")
        if not df.empty:
            df['addr'] = (df['numero_voirie'].fillna('').astype(str).str.lstrip('0')
                          + df['indice_de_repetition'].fillna('').astype(str)
                          + ' ' + df['nature_voie'].fillna('') + ' '
                          + df['nom_voie'].fillna(''))
            for adr, n in df['addr'].value_counts().items():
                print(f"    {n:3d}  '{adr.strip()}'")
            print(f"  SIRENs distincts : {df['numero_siren'].nunique()}")
else:
    print()
    print("[6] 153 BARABAN ABSENT light - investigation BAN/BDNB seule")

# [7] RNC live scan parcelle 44 TURBIL
print()
print("[7] RNC live scan parcelle 44 TURBIL (et 153 BARABAN si differente)")
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
parcs_a_scanner = set()
if a44 and parc:
    for p in parc:
        pid = p['parcelle_id']
        rnc_p = "69123383" + pid[8:] if pid[:2]=="69" and pid[5:8]=="000" else pid
        parcs_a_scanner.add(rnc_p)
if a153 and parc153:
    for p in parc153:
        pid = p['parcelle_id']
        rnc_p = "69123383" + pid[8:] if pid[:2]=="69" and pid[5:8]=="000" else pid
        parcs_a_scanner.add(rnc_p)

for rnc_p in sorted(parcs_a_scanner):
    print(f"\n  parcelle RNC {rnc_p} :")
    hits = 0
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception: data = []
        for row in data:
            hits += 1
            print(f"    {col}: {row.get('numero_immatriculation')} '{row.get('nom_usage_copropriete','')[:38]}'  "
                  f"tot={row.get('nombre_total_lots')} hab={row.get('nombre_lots_usage_habitation')}")
            print(f"      adr_ref='{row.get('adresse_reference','')[:80]}'")
            for k in ("adresse_complementaire_1","adresse_complementaire_2",
                      "adresse_complementaire_3","adresse_complementaire_4"):
                v = row.get(k)
                if v: print(f"      {k}='{v}'")
        time.sleep(0.05)
    if hits == 0:
        print(f"    0 hit RNC live")
