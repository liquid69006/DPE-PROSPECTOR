#!/usr/bin/env python3
"""Fix 139 RUE DAUPHINE -> RE-FUSE vers 238/240 AVENUE FELIX FAURE
(Dauphine-Lacassagne). Pattern Fondary RE-FUSE multi-bgid sur une
seule parcelle.

CONFIGURATION terrain :
- Parcelle unique DN0039 (BDNB 69383000DN0039 = RNC 69123383DN0039)
  heberge 2 batis BDNB distincts :
  HQ5A-SU4G (139 DAUPH 20 lgts 1991, mono-adresse BAN)
  MU33-65VW (238/240 FF 29 lgts 1992, immat_principal AB1862135)
- 1 copropriete physique :
  Snapshot : AB1862135 LES TERRASSES DU PRESIDENT (2019-03-13, 169
  lots, cle '238|AVENUE|FELIX FAURE', label '238/240 AV FELIX FAURE')
  Live    : AJ6692420 TERRASSES DU PRESIDENT (2026-03-16, 169 lots,
  meme entite physique re-immatriculee suite a expiration mandat
  syndic AB1862135 le 2026-03-30)
- RNC AJ6692420 explicite l'autorite multi-adresses :
  adresse_reference        : 238 Avenue Felix Faure
  adresse_complementaire_1 : 240 Avenue Felix Faure
  adresse_complementaire_2 : 139 Rue du Dauphine

OPS :
  1. RE-FUSE 139|RUE|DAUPHINE : _fusion_auto=True,
     _fusion_cible='238/240 AV FELIX FAURE / 139 RUE DAUPHINE'
  2. Etendre label 238 FF ancre :
     '238/240 AV FELIX FAURE'
     -> '238/240 AV FELIX FAURE / 139 RUE DAUPHINE'
     + sources += ['139|RUE|DAUPHINE']

PAS d'INJECT copro (snapshot AB1862135 reste autorite ; la re-immat
AJ6692420 est un sujet de refresh global RNC, hors scope).

EFFETS :
- adresses 1241 -> 1241 (0)
- hr-actifs UI 24 -> 23 (139 sort en FA)
- parc DL UI 22964 -> 22964 (strictement neutre, HQ5A garde BDNB 20
  fallback, MU33 garde RNC 65)
"""
import json, sys, shutil
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pre139dauph.bak"

LABEL = "238/240 AVENUE FELIX FAURE / 139 RUE DAUPHINE"


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
    if md.get("_correctif_139_dauphine"):
        sys.exit("  [abort] _correctif_139_dauphine deja present.")

    by_cle = {(a.get("cle") or ""): a for a in ad}
    a139 = by_cle.get("139|RUE|DAUPHINE")
    a238 = by_cle.get("238|AVENUE|FELIX FAURE")
    if not a139:
        sys.exit("  [abort] 139|RUE|DAUPHINE absent.")
    if not a238:
        sys.exit("  [abort] 238|AVENUE|FELIX FAURE absent.")
    if a238.get("numero_immatriculation") != "AB1862135":
        print(f"  [warn] 238 FF immat={a238.get('numero_immatriculation')} != AB1862135 (continue)")

    # 1. RE-FUSE 139
    a139["_fusion_auto"] = True
    a139["_fusion_cible"] = LABEL
    a139["_bdnb_match"] = "correctif_139dauph_re_fuse"
    print(f"  [RE-FUSE] 139|RUE|DAUPHINE  _fusion_cible='{LABEL}'")

    # 2. Maj ancre 238 FF
    a238["_fusion_auto_label"] = LABEL
    srcs = list(a238.get("_fusion_auto_sources") or [])
    if "139|RUE|DAUPHINE" not in srcs:
        srcs.append("139|RUE|DAUPHINE")
    a238["_fusion_auto_sources"] = srcs
    print(f"  [LABEL]   238|AVENUE|FELIX FAURE  label='{LABEL}'  sources={srcs}")

    md["_correctif_139_dauphine"] = {
        "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pattern": "Fondary RE-FUSE multi-bgid une parcelle (DN0039)",
        "autorite": "RNC live AJ6692420 + BDNB rel_parcelle DN0039 = HQ5A+MU33",
        "ops": "RE-FUSE 139|RUE|DAUPHINE vers 238 FF + extension label ancre",
        "snapshot_immat": "AB1862135 LES TERRASSES DU PRESIDENT (cle 238 FF inchangee)",
        "re_immat_live": "AJ6692420 TERRASSES DU PRESIDENT (2026-03-16, "
                         "mandat AB1862135 expire 2026-03-30) - meme entite "
                         "physique 169 lots, sujet refresh RNC separe",
        "label": LABEL,
        "delta_parc_ui": 0,
    }

    LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print()
    print("  [OK] 1 RE-FUSE + 1 LABEL appliques.")


if __name__ == "__main__":
    main()
