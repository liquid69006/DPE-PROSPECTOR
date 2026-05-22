#!/usr/bin/env python3
"""Diagnostic 4 RUE TERNOIS (SCI PIETRA) + 45 AV POMPIDOU (SCI MAESTRIMMO)
- meme methodologie que diag PIONCHON/CITE :
  1. Etat light + voisins
  2. SCI Prospector hits sur la cle + voisins
  3. BDNB pivot pour bgid + parcelle
  4. RNC live scan parcelle (copros couvrantes)
"""
import json, sys, urllib.parse, urllib.request, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
SCI = ROOT / "data" / "dauphine-lacassagne-sci.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
sci_data = json.loads(SCI.read_text(encoding="utf-8")).get("sci") or []
by_cle = {(a.get("cle") or ""): a for a in ad}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in co}

RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

def bdnb_to_rnc(p):
    if p[:2]=="69" and p[5:8]=="000": return "69123383" + p[8:]
    return p

def scan_parcelle(rnc_p):
    out = []
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": rnc_p})
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                d = json.loads(r.read()).get("data", [])
        except Exception as e:
            d = []
        for row in d:
            out.append({"col": col, "immat": row.get("numero_immatriculation"),
                        "nom": row.get("nom_usage_copropriete",""),
                        "lots_tot": row.get("nombre_total_lots"),
                        "lots_hab": row.get("nombre_lots_usage_habitation"),
                        "adr_ref": row.get("adresse_reference",""),
                        "adr_compl1": row.get("adresse_complementaire_1",""),
                        "adr_compl2": row.get("adresse_complementaire_2","")})
        time.sleep(0.05)
    return out

def diag_cible(label, target_cle, target_sci_name, voisin_pattern, voisin_nums):
    """target_cle = ex '4|RUE|TERNOIS' ; voisin_pattern = 'TERNOIS'"""
    print("=" * 80)
    print(f"DIAG : {label}  ({target_cle}, SCI {target_sci_name})")
    print("=" * 80)
    a = by_cle.get(target_cle)
    if not a:
        print(f"  CIBLE ABSENTE LIGHT"); return
    print()
    print("[1] Etat cible :")
    for k in ("batiment_groupe_id","nb_log_bdnb","nb_ventes_logement",
              "nb_ventes_total","numero_immatriculation","syndic","_syndic_src",
              "_bdnb_match","_fusion_auto","_fusion_cible","_fusion_auto_label",
              "_fusion_auto_sources","sci_proprietaire","sci_nom","annee_construction"):
        v = a.get(k)
        if v not in (None,"",[],{},0,0.0):
            print(f"    {k}: {v}")

    print()
    print(f"[2] Voisins {voisin_pattern} dans light (nums {voisin_nums[0]}-{voisin_nums[-1]}) :")
    for nv in voisin_nums:
        for cle in by_cle:
            if voisin_pattern in cle and cle.startswith(f"{nv}|"):
                v = by_cle[cle]
                bg = v.get("batiment_groupe_id") or ""
                flags=[]
                if v.get("_fusion_auto"): flags.append("FA")
                if v.get("_fusion_auto_label"): flags.append(f"label='{v['_fusion_auto_label']}'")
                if v.get("numero_immatriculation"): flags.append(f"immat={v['numero_immatriculation']}")
                if cle in co_by_cle: flags.append("COPRO")
                sci_n = (v.get('sci_nom') or '')[:18]
                print(f"  {cle:32s} bgid=...{bg[-9:]} bdnb={v.get('nb_log_bdnb')} "
                      f"vlog={v.get('nb_ventes_logement')} sci={sci_n} {' '.join(flags)}")

    print()
    print(f"[3] SCI Prospector hits sur cible :")
    # Parser cle adresse_bien -> light cle (meme algo que UI)
    import re
    ABBR={'AV':'AVENUE','R':'RUE','BD':'BOULEVARD','BLD':'BOULEVARD',
          'PL':'PLACE','IMP':'IMPASSE','CRS':'COURS','QU':'QUAI','SQ':'SQUARE',
          'ALL':'ALLEE','CHE':'CHEMIN','CH':'CHEMIN','MTE':'MONTEE',
          'PAS':'PASSAGE','TSSE':'TERRASSE','VLA':'VILLA','RTE':'ROUTE',
          'GR':'GRANDE RUE','AVE':'AVENUE','BOUL':'BOULEVARD'}
    ART={'DE','DES','DU','D','LA','LE','LES','L','AUX'}
    ACC = str.maketrans('ÉÈÊËÀÂÔÎÏÇÛÙéèêëàâôîïçûù','EEEEAAOIICUUEEEEAAOIICUU')
    def parse(adr):
        if not adr: return None
        s = str(adr).upper().translate(ACC)
        s = re.sub(r'\s+\d{5}.*$', '', s)
        s = re.sub(r'[^\w\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        toks = s.split()
        if not toks: return None
        m = re.match(r'^(\d+)([A-Z]+)?$', toks[0])
        if not m: return None
        num = m.group(1)
        suff = m.group(2) or ''
        if suff in ('B','BIS','BS'): num+='B'
        elif suff in ('T','TER'): num+='T'
        toks = toks[1:]
        if not toks: return None
        typV = ABBR.get(toks[0], toks[0])
        toks = toks[1:]
        while toks and toks[0] in ART: toks=toks[1:]
        return f"{num}|{typV}|{' '.join(toks)}"
    n_hit_cible = 0
    n_hit_voisin = 0
    for s in sci_data:
        k = parse(s.get('adresse_bien'))
        if k == target_cle:
            n_hit_cible += 1
            print(f"  CIBLE: {s.get('sci_nom'):28s} SIREN={s.get('sci_siren')}  "
                  f"actif={s.get('sci_active')}  biens={s.get('nb_biens_total')}  "
                  f"parc={s.get('parcelle')}")
        elif k and voisin_pattern in k and k.split('|')[0].rstrip('B').isdigit():
            n = int(k.split('|')[0].rstrip('B'))
            if n in voisin_nums:
                n_hit_voisin += 1
                # Limit to first 3
                if n_hit_voisin <= 3:
                    print(f"  voisin {k:30s} : {s.get('sci_nom'):26s} parc={s.get('parcelle')}")
    print(f"  ({n_hit_cible} SCI sur cible + {n_hit_voisin} SCI voisins)")

    # BDNB pivot
    print()
    print(f"[4] BDNB pivot + parcelle pour bgid {a.get('batiment_groupe_id')} :")
    bg = a.get("batiment_groupe_id")
    url = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
           "?select=batiment_groupe_id,libelle_adr_principale_ban,l_libelle_adr,"
           "nb_log,nb_log_rnc,annee_construction,numero_immat_principal"
           f"&batiment_groupe_id=in.({bg})")
    with urllib.request.urlopen(url, timeout=15) as r:
        rows = json.loads(r.read())
    for row in rows:
        print(f"  lib_principal='{row.get('libelle_adr_principale_ban','')}'")
        print(f"  nb_log={row.get('nb_log')} nb_log_rnc={row.get('nb_log_rnc')}  "
              f"annee={row.get('annee_construction')}  immat_principal={row.get('numero_immat_principal') or '-'}")
        for x in row.get("l_libelle_adr") or []:
            print(f"    . {x}")
    url2 = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle"
            f"?batiment_groupe_id=eq.{bg}")
    with urllib.request.urlopen(url2, timeout=15) as r:
        parc = json.loads(r.read())
    parcs = [p.get("parcelle_id") for p in parc]
    print(f"  Parcelles BDNB : {parcs}")

    print()
    print(f"[5] RNC live scan parcelle (copros candidates) :")
    for pb in parcs:
        pr = bdnb_to_rnc(pb)
        hits = scan_parcelle(pr)
        print(f"  parcelle {pr} : {len(hits)} hit(s)")
        for h in hits:
            print(f"    {h['col'][-1]}: {h['immat']} '{h['nom'][:38]}'  "
                  f"lots={h['lots_tot']} hab={h['lots_hab']}")
            if h.get('adr_ref'): print(f"       adr_ref='{h['adr_ref']}'")
            if h.get('adr_compl1'): print(f"       compl1='{h['adr_compl1']}'")
            if h.get('adr_compl2'): print(f"       compl2='{h['adr_compl2']}'")

# ===== CAS 1 : 4 TERNOIS (SCI PIETRA, 80 lgts BDNB) =====
diag_cible("PIETRA / 4 TERNOIS (80 lgts BDNB)",
           "4|RUE|TERNOIS", "PIETRA",
           "TERNOIS", list(range(1, 16)))

print()
# ===== CAS 2 : 45 POMPIDOU (SCI MAESTRIMMO, 61 lgts BDNB) =====
diag_cible("MAESTRIMMO / 45 AVENUE GEORGES POMPIDOU (61 lgts BDNB)",
           "45|AVENUE|GEORGES POMPIDOU", "MAESTRIMMO",
           "POMPIDOU", list(range(30, 71)))
