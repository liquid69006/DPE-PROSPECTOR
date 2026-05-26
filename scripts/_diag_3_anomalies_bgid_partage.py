#!/usr/bin/env python3
"""Diag 3 anomalies bgid partage suspect (0 vente sur cle + voisin bgid vend) :
  #4  13 RUE ST VICTORIEN   (bgid 9SJM-2V31-SHKZ partage avec 2 LOUIS JASSERON + 14 ST VICTORIEN)
  #15 11 RUE BARA            (bgid commun avec 12 BARA qui vend 4 Apt)
  #19 2  RUE RIBOUD          (bgid YAR9-LWKG-N28H partage avec 2B RIBOUD deja patche)

Verifie pour chaque cle :
  [1] etat light (cle + ancres + voisins)
  [2] copros snapshot (cle + voisinage immat)
  [3] BAN -> BDNB autorite (cle_interop + bgid retourne)
  [4] BDNB pivot batiment_groupe_complet (lib, nb_log, l_libelle_adr, parcelles)
  [5] MAJIC parcelles (lots PM, adresses, SIRENs)
  [6] RNC live scan parcelles (ref_cad_1/2/3 -> immat + nom usage)
"""
import json, sys, urllib.parse, urllib.request, time, re
from pathlib import Path
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
MAJIC = r'C:\Users\Station 5\majic_locaux2_2025.parquet'
RID   = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB   = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad, co = doc["adresses"], doc["coproprietes"]
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {}
for c in co:
    co_by_cle.setdefault(c.get("cle_adresse") or "", []).append(c)
co_by_immat = {c.get("numero_immatriculation"): c
               for c in co if c.get("numero_immatriculation")}

CAS = [
    ("#4  13 RUE ST VICTORIEN", [
        "13|RUE|ST VICTORIEN", "14|RUE|ST VICTORIEN", "12|RUE|ST VICTORIEN",
        "11|RUE|ST VICTORIEN", "2|RUE|LOUIS JASSERON", "4|RUE|LOUIS JASSERON",
    ], [
        ("13 rue saint victorien 69003 Lyon",),
        ("14 rue saint victorien 69003 Lyon",),
        ("2 rue louis jasseron 69003 Lyon",),
    ]),
    ("#15 11 RUE BARA", [
        "11|RUE|BARA", "12|RUE|BARA", "10|RUE|BARA", "9|RUE|BARA", "13|RUE|BARA",
    ], [
        ("11 rue bara 69003 Lyon",),
        ("12 rue bara 69003 Lyon",),
    ]),
    ("#19 2 RUE RIBOUD", [
        "2|RUE|RIBOUD", "2B|RUE|RIBOUD", "4|RUE|RIBOUD", "1|RUE|RIBOUD",
    ], [
        ("2 rue riboud 69003 Lyon",),
        ("2B rue riboud 69003 Lyon",),
        ("2 bis rue riboud 69003 Lyon",),
    ]),
]


def ban(q):
    url = "https://api-adresse.data.gouv.fr/search/?limit=3&q=" + urllib.parse.quote(q)
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read()).get("features", [])


def bdnb_for_cleban(cle):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle)}&select=batiment_groupe_id")
    with urllib.request.urlopen(url, timeout=15) as r:
        return [r2["batiment_groupe_id"] for r2 in json.loads(r.read())]


def parcs_for_bg(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
           f"?batiment_groupe_id=eq.{bg}")
    with urllib.request.urlopen(url, timeout=15) as r:
        return [p["parcelle_id"] for p in json.loads(r.read())]


def pivots_for_bgs(bgs):
    if not bgs:
        return []
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,usage_principal_bdnb_open,"
           "numero_immat_principal,nb_adresse_valid_ban"
           f"&batiment_groupe_id=in.({','.join(sorted(bgs))})")
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def bdnb_to_rnc(p):
    return "69123383" + p[8:] if p[:2] == "69" and p[5:8] == "000" else p


def rnc_scan_parcelle(rnc_p):
    out = []
    for col in ("reference_cadastrale_1", "reference_cadastrale_2", "reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read()).get("data", [])
        for row in data:
            out.append((col, row))
        time.sleep(0.05)
    return out


def majic_parcelle(parc):
    sec = parc[8:10]
    plan = int(parc[10:])
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", "69"), ("code_commune", "=", "383"),
        ("section", "=", sec), ("numero_parcelle", "=", plan),
    ])
    return tbl.to_pandas()


for titre, cles_a_voir, requetes_ban in CAS:
    print("=" * 78)
    print(titre)
    print("=" * 78)

    # [1] light
    print("\n[1] etat light :")
    bgs_set = set()
    for cle in cles_a_voir:
        a = by_cle.get(cle)
        if not a:
            print(f"  {cle:32s} ABSENT light")
            continue
        bg = a.get("batiment_groupe_id") or ""
        if bg:
            bgs_set.add(bg)
        flags = []
        if a.get("_fusion_auto"):  flags.append("FA")
        if a.get("_fusion_auto_label"): flags.append(f"label='{a['_fusion_auto_label'][:40]}'")
        if a.get("_fusion_cible"): flags.append(f"cible='{a['_fusion_cible']}'")
        if a.get("numero_immatriculation"): flags.append(f"immat={a['numero_immatriculation']}")
        if cle in co_by_cle:        flags.append("COPRO")
        usage = (a.get("usage_principal_bdnb") or "-")[:18]
        print(f"  {cle:32s} bgid=...{bg[-9:]}  bdnb={a.get('nb_log_bdnb')} "
              f"vlog={a.get('nb_ventes_logement')} lots_hab={a.get('nb_lots_habitation') or '-'} "
              f"syndic='{(a.get('syndic') or '-')[:18]}'  usage='{usage}'  {' '.join(flags)}")

    # [1b] toutes les autres adresses du meme bgid
    print("\n[1b] autres adresses light partageant un bgid :")
    for bg in sorted(bgs_set):
        cles_bg = [(a.get("cle") or "") for a in ad if a.get("batiment_groupe_id") == bg]
        cles_bg = [c for c in cles_bg if c not in cles_a_voir]
        if cles_bg:
            print(f"  bgid ...{bg[-9:]} :")
            for c in cles_bg:
                a = by_cle[c]
                print(f"    + {c:30s} bdnb={a.get('nb_log_bdnb')} vlog={a.get('nb_ventes_logement')} immat={a.get('numero_immatriculation') or '-'} FA={a.get('_fusion_auto')}")

    # [2] copros snapshot voisinage
    print("\n[2] copros snapshot voisinage :")
    voie_tokens = set()
    for cle in cles_a_voir:
        parts = cle.split("|")
        if len(parts) == 3:
            voie_tokens.add(parts[2])
    for c in co:
        cle_c = c.get("cle_adresse") or ""
        nom = (c.get("nom_copropriete") or "")
        match = any(t in cle_c for t in voie_tokens) or any(t in nom.upper() for t in voie_tokens)
        if match:
            print(f"  {cle_c:32s} {c.get('numero_immatriculation')} '{nom[:35]}' "
                  f"tot={c.get('nb_lots_total')} hab={c.get('nb_lots_habitation')} "
                  f"syndic='{(c.get('syndic') or '-')[:25]}'")

    # [3] BAN -> BDNB autorite
    print("\n[3] BAN -> BDNB autoritaire :")
    for (q,) in requetes_ban:
        try:
            feats = ban(q)
        except Exception as e:
            print(f"  {q:42s} ERR BAN {e}")
            continue
        if not feats:
            print(f"  {q:42s} BAN 0 feature")
            continue
        for f in feats[:2]:
            p = f["properties"]
            try:
                bgs = bdnb_for_cleban(p["id"])
            except Exception as e:
                bgs = [f"ERR {e}"]
            print(f"  {q:42s} BAN={p.get('id')} ({p.get('name','')}) -> bgid {bgs}")
            for bg in bgs:
                if isinstance(bg, str) and bg.startswith("BAT"):
                    bgs_set.add(bg)
        time.sleep(0.05)

    # [4] BDNB pivot
    print("\n[4] BDNB pivot :")
    try:
        pivots = pivots_for_bgs(bgs_set)
    except Exception as e:
        pivots = []
        print(f"  ERR pivot {e}")
    for p in pivots:
        print(f"\n  {p.get('batiment_groupe_id','')[-9:]} :")
        print(f"    lib='{p.get('libelle_adr_principale_ban','')}'")
        print(f"    nb_log={p.get('nb_log')}  nb_log_rnc={p.get('nb_log_rnc')}  "
              f"annee={p.get('annee_construction')}  immat={p.get('numero_immat_principal') or '-'}")
        print(f"    usage={p.get('usage_principal_bdnb_open','')[:30]}  nb_adresses_BAN={p.get('nb_adresse_valid_ban')}")
        for x in p.get("l_libelle_adr") or []:
            print(f"      . {x}")

    # parcelles par bg
    parcs_par_bg = {}
    for bg in sorted(bgs_set):
        try:
            parcs_par_bg[bg] = parcs_for_bg(bg)
        except Exception as e:
            parcs_par_bg[bg] = []
            print(f"  ERR parcelles {bg} : {e}")
    print("\n  parcelles par bgid :")
    for bg, parcs in parcs_par_bg.items():
        print(f"    {bg} -> {parcs}")

    # [5] MAJIC
    print("\n[5] MAJIC parcelles :")
    all_parcs = set()
    for parcs in parcs_par_bg.values():
        all_parcs.update(parcs)
    for parc in sorted(all_parcs):
        try:
            df = majic_parcelle(parc)
        except Exception as e:
            print(f"  parc {parc} ERR MAJIC {e}")
            continue
        print(f"\n  parc {parc} : {len(df)} lots PM")
        if not df.empty:
            df["addr"] = (df["numero_voirie"].fillna("").astype(str).str.lstrip("0")
                          + df["indice_de_repetition"].fillna("").astype(str)
                          + " " + df["nature_voie"].fillna("")
                          + " " + df["nom_voie"].fillna(""))
            for adr, n in df["addr"].value_counts().items():
                print(f"    {n:3d}  '{adr.strip()}'")
            sirens = df["numero_siren"].dropna().value_counts().to_dict()
            print(f"    SIRENs : {len(sirens)}")
            for sir, n in list(sirens.items())[:5]:
                denom = df[df["numero_siren"] == sir]["denomination"].iloc[0]
                print(f"      {sir}: {n} lots  {denom[:30]}")

    # [6] RNC live scan parcelles
    print("\n[6] RNC live scan parcelles :")
    for parc in sorted(all_parcs):
        rnc_p = bdnb_to_rnc(parc)
        print(f"\n  parcelle RNC {rnc_p} :")
        try:
            rows = rnc_scan_parcelle(rnc_p)
        except Exception as e:
            print(f"    ERR {e}")
            continue
        if not rows:
            print("    0 hit RNC live")
            continue
        for col, row in rows:
            in_sct = " [DEJA-SCT]" if row.get("numero_immatriculation") in co_by_immat else " [HORS-SCT]"
            print(f"    {col[-1]}: {row.get('numero_immatriculation')} '{row.get('nom_usage_copropriete','')[:35]}'  "
                  f"tot={row.get('nombre_total_lots')} hab={row.get('nombre_lots_usage_habitation')}{in_sct}")
            if row.get("adresse_reference"):
                print(f"       adr_ref='{row.get('adresse_reference')}'")
            for k in ("adresse_complementaire_1", "adresse_complementaire_2",
                      "adresse_complementaire_3", "adresse_complementaire_4"):
                v = row.get(k)
                if v:
                    print(f"       {k}='{v}'")

    print()
