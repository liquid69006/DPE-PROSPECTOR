#!/usr/bin/env python3
"""Fix 21 RUE CLAUDIUS PIONCHON -> RE-FUSE vers 24/26 RUE CITE
(allee des poetes AA0823708) - Dauphine-Lacassagne.

Pattern Fondary RE-FUSE multi-bgid sur UNE seule parcelle DX0035
(identique a 139 DAUPHINE -> TERRASSES DU PRESIDENT).

Configuration confirmee (5 preuves convergentes) :
1. RNC live AA0823708 'allee des poetes' (SAGNIMORTE CONSEILS,
   372 lots / 126 hab) declare explicitement '21B r claudius pionchon'
   dans adresse_complementaire_1
2. Parcelle BDNB DX0035 identique pour les 3 batis :
   - JAVT-QG97-XWEW (21 PIONCHON, 35 lgts BDNB, 1991)
   - 1WGV-T5E8-T2X3 (24 CITE, 30 lgts, 1990, immat_principal AA0823708)
   - 558F-914A-J3ZK (26 CITE, 42 lgts, 1992)
3. SCI CAMAC partagee entre 21 PIONCHON et 24 CITE (meme bailleur)
4. Tailles coherentes : 35+30+42 BDNB = 107 lgts ~= 126 RNC hab
5. Periode construction 1990-1992 (ensemble phase)

Terrain confirme : 21 PIONCHON rattache 24/26 CITE = ensemble
immobilier, pas mono-propriete (malgre SCI CAMAC detectee).

OPS :
- RE-FUSE 21|RUE|CLAUDIUS PIONCHON : _fusion_auto=True,
  _fusion_cible='24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON'
- Etendre label 24 CITE ancre :
  '24/26 RUE CITE' -> '24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON'
  + sources += ['21|RUE|CLAUDIUS PIONCHON']

PAS d'INJECT copro (AA0823708 deja ancree cle 24 CITE).

Effets :
- adresses 1241 -> 1241 (0)
- hr-actifs UI 22 -> 21 (-1, 21 PIONCHON sort en FA)
- parc DL UI 22971 -> 22971 (strictement neutre, le bgid JAVT garde
  son fallback BDNB 35 ; T5E8 garde RNC 126 ; 914A garde fallback 42)
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre21pionchon.bak"

LABEL = "24/26 RUE CITE / 21B RUE CLAUDIUS PIONCHON"


def main():
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))
    if BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {BAK.name}")
    shutil.copy2(LIGHT, BAK)
    print(f"  [bak] {BAK.name}")

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_21_pionchon"):
        sys.exit("  [abort] _correctif_21_pionchon deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a21 = by_cle.get("21|RUE|CLAUDIUS PIONCHON")
    a24 = by_cle.get("24|RUE|CITE")
    if not a21:
        sys.exit("  [abort] 21|RUE|CLAUDIUS PIONCHON absent.")
    if not a24:
        sys.exit("  [abort] 24|RUE|CITE absent.")
    if a24.get("numero_immatriculation") != "AA0823708":
        print(f"  [warn] 24 CITE immat={a24.get('numero_immatriculation')} "
              f"!= AA0823708 (continue)")

    # 1. RE-FUSE 21 PIONCHON
    a21["_fusion_auto"] = True
    a21["_fusion_cible"] = LABEL
    a21["_bdnb_match"] = "correctif_21pionchon_re_fuse"
    print(f"  [RE-FUSE] 21|RUE|CLAUDIUS PIONCHON  _fusion_cible='{LABEL}'")

    # 2. Maj ancre 24 CITE
    a24["_fusion_auto_label"] = LABEL
    srcs = list(a24.get("_fusion_auto_sources") or [])
    if "21|RUE|CLAUDIUS PIONCHON" not in srcs:
        srcs.append("21|RUE|CLAUDIUS PIONCHON")
    a24["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]   24|RUE|CITE  label='{LABEL}'  sources={srcs}")

    md["_correctif_21_pionchon"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Fondary RE-FUSE multi-bgid une parcelle (DX0035)",
        "autorite": "RNC live AA0823708 adresse_complementaire_1='21B r "
                    "claudius pionchon' + BDNB rel_parcelle DX0035 = "
                    "JAVT-QG97-XWEW + T5E8-T2X3 + 914A-J3ZK + "
                    "SCI CAMAC partagee 21 PIONCHON / 24 CITE",
        "ops": "RE-FUSE 21|RUE|CLAUDIUS PIONCHON vers 24 CITE + "
               "extension label ancre",
        "snapshot_immat": "AA0823708 allee des poetes (372/126 hab, "
                          "SAGNIMORTE CONSEILS, cle 24 CITE inchangee)",
        "label": LABEL,
        "delta_parc_ui": 0,
        "terrain_confirme": "Ensemble immobilier 21 PIONCHON + 24/26 CITE, "
                            "NON mono-propriete (malgre SCI CAMAC detectee)",
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 RE-FUSE + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
