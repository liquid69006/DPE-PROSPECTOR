#!/usr/bin/env python3
"""Fix 106 RUE BARABAN -> RE-FUSE vers 61 RUE ANTOINE CHARIAL
(SOPHIA AE1293612) - Dauphine-Lacassagne. Pattern Cambronne RE-FUSE
classique sur cote impair non-postal BAN.

CONFIGURATION terrain :
- 106 BARABAN (bgid 4XAJ-TVQA, BDNB 61 lgts) est cote postal BAN
- 61 ANTOINE CHARIAL (meme bgid, declare adresse_reference RNC) est
  cote secondaire NON-postal BAN (anomalie BAN)
- Parcelle unique RNC ref_cad_1=69123383DS0005 = parc BDNB DS0005
- Copro AE1293612 SOPHIA (73 lots tot / 60 hab, syndic REGIE CENTRALE
  IMMOBILIERE, date_immat 2018-12-20) deja dans coproprietes[] avec
  cle_adresse '61|RUE|ANTOINE CHARIAL' mais ORPHELINE (aucune adresse
  light sur cette cle avant ce fix)

OPS :
  1. INJECT 61|RUE|ANTOINE CHARIAL en adresses[] (clone-based depuis
     106 BARABAN, bgid identique 4XAJ-TVQA) + propagation copro RNC
  2. RE-FUSE 106|RUE|BARABAN : _fusion_auto=True, _fusion_cible label

EFFETS :
- hr-actifs UI 25 -> 24 (106 sort)
- adresses 1240 -> 1241 (+1 INJECT)
- parc DL (algo UI) 22965 -> 22964 (-1, RNC 60 lots ecrase BDNB 61
  sur bgid 4XAJ-TVQA)
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre106baraban.bak"

LABEL = "61 RUE ANTOINE CHARIAL / 106 RUE BARABAN"


def main():
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co = doc["coproprietes"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_106_baraban"):
        sys.exit("  [abort] _correctif_106_baraban deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    co_by_immat = {c.get("numero_immatriculation"): c for c in co
                   if c.get("numero_immatriculation")}

    a106 = by_cle.get("106|RUE|BARABAN")
    if not a106:
        sys.exit("  [abort] 106|RUE|BARABAN absent du light.")
    if "61|RUE|ANTOINE CHARIAL" in by_cle:
        sys.exit("  [abort] 61|RUE|ANTOINE CHARIAL deja en adresses[].")
    c_sophia = co_by_immat.get("AE1293612")
    if not c_sophia:
        sys.exit("  [abort] copro AE1293612 SOPHIA absente.")
    if c_sophia.get("cle_adresse") != "61|RUE|ANTOINE CHARIAL":
        print(f"  [warn] copro SOPHIA cle_adresse='{c_sophia.get('cle_adresse')}' "
              f"!= '61|RUE|ANTOINE CHARIAL' (patch quand meme)")

    # 1. INJECT 61|RUE|ANTOINE CHARIAL
    a61 = {
        "cle": "61|RUE|ANTOINE CHARIAL",
        "adresse": "61 RUE ANTOINE CHARIAL",
        "longitude": a106.get("longitude"),
        "latitude": a106.get("latitude"),
        "code_iris": a106.get("code_iris"),
        "_coord_source": "clone_106baraban",
        "dans_majic": False,
        "sci_proprietaire": "non",
        "sci_nom": "",
        "sci_siren": "",
        "syndic": c_sophia.get("syndic"),
        "_syndic_src": c_sophia.get("_syndic_src") or "rnc",
        "ventes_par_an": {},
        "nb_ventes_total": 0,
        "nb_log_bdnb": a106.get("nb_log_bdnb"),
        "annee_construction": a106.get("annee_construction"),
        "classe_dpe": a106.get("classe_dpe"),
        "type_batiment": a106.get("type_batiment"),
        "type_chauffage": a106.get("type_chauffage"),
        "batiment_groupe_id": a106.get("batiment_groupe_id"),
        "_bdnb_match": "correctif_106baraban_inject_ancre_rnc",
        "ventes_par_an_logement": {},
        "nb_ventes_logement": 0,
        "taux_rotation_logement": 0.0,
        "classement_rotation_logement": "Fige",
        "_taux_logement_src": "copie_sans_dependance",
        "usage_principal_bdnb": a106.get("usage_principal_bdnb"),
        "_usage_bdnb_src": "clone_106baraban",
        # Propagation copro RNC
        "numero_immatriculation": "AE1293612",
        "nb_lots_habitation": c_sophia.get("nb_lots_habitation"),
        "taux_rotation": c_sophia.get("taux_rotation_5ans"),
        "classement_rotation": c_sophia.get("classement_rotation"),
        # Etiquetage chaine
        "_fusion_auto_label": LABEL,
        "_fusion_auto_sources": ["106|RUE|BARABAN"],
    }
    ad.append(a61)
    print(f"  [INJECT]  61|RUE|ANTOINE CHARIAL  bgid={a106['batiment_groupe_id'][-9:]}  "
          f"immat=AE1293612  nb_lots_habit={c_sophia.get('nb_lots_habitation')}")

    # 2. RE-FUSE 106 BARABAN
    a106["_fusion_auto"] = True
    a106["_fusion_cible"] = LABEL
    a106["_bdnb_match"] = "correctif_106baraban_re_fuse"
    print(f"  [RE-FUSE] 106|RUE|BARABAN  _fusion_cible='{LABEL}'")

    md["_correctif_106_baraban"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Cambronne RE-FUSE classique (cote impair non-postal BAN)",
        "autorite": "RNC live AE1293612 + BDNB rel_parcelle DS0005 + diag_106_baraban",
        "ops": "INJECT 61|RUE|ANTOINE CHARIAL clone-based + RE-FUSE 106|RUE|BARABAN",
        "immat": "AE1293612 SOPHIA",
        "lots_tot": 73,
        "lots_habit": 60,
        "syndic": c_sophia.get("syndic"),
        "parcelle": "69123383DS0005",
        "label": LABEL,
        "delta_parc_ui": -1,
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 INJECT + 1 RE-FUSE appliques.")


if __name__ == "__main__":
    main()
