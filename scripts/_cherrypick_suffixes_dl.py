#!/usr/bin/env python3
"""Cherry-pick les cles avec suffixe B/T/Q/A/C/D du sandbox v2 vers le light DL.

Source : data/secteur_dl_light_v2.json (sandbox post-patch indice_de_repetition)
Cible  : data/secteur_dauphine_lacassagne_light.json (current commited)

Regles :
  - N'injecte que les cles avec suffixe alphabetique (^\\d+[A-Z]\\|)
  - Que les cles ABSENTES du current (pas d'override)
  - Copie integrale de l'entry adresse depuis sandbox
  - 0 modification des cles existantes
  - 0 modification des coproprietes (pas de copro avec suffixe a injecter)

Backup avant injection + diff parc UI avant/apres.
"""
import json, re, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
CURRENT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
SANDBOX = ROOT / "data" / "secteur_dl_light_v2.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.precherrypick.bak"

SUFFIX_RX = re.compile(r"^(\d+)([A-Z])\|")

# ============================================================
# 1. Chargement
# ============================================================
print("=" * 90)
print("CHERRY-PICK suffixes B/T/Q/A/C/D sandbox v2 -> light current DL")
print("=" * 90)
doc_c = json.loads(CURRENT.read_text(encoding="utf-8"))
doc_s = json.loads(SANDBOX.read_text(encoding="utf-8"))
ad_c = doc_c["adresses"]
ad_s = doc_s["adresses"]
cles_c = {a.get("cle") for a in ad_c if a.get("cle")}
N0 = len(ad_c)  # snapshot AVANT mutation (ad_c sera mute par append)
print(f"  Current : {N0} adresses, {len(cles_c)} cles uniques")
print(f"  Sandbox : {len(ad_s)} adresses, {len({a.get('cle') for a in ad_s})} cles uniques")

# ============================================================
# 2. Identifier cles avec suffixe absentes du current
# ============================================================
by_cle_s = {a.get("cle"): a for a in ad_s if a.get("cle")}
sufkeys = [c for c in by_cle_s if SUFFIX_RX.match(c)]
new_sufkeys = [c for c in sufkeys if c not in cles_c]
print()
print(f"  Cles sandbox avec suffixe : {len(sufkeys)}")
print(f"  Cles sandbox suffixe NON dans current (cibles cherry-pick) : {len(new_sufkeys)}")
if len(new_sufkeys) != 85:
    print(f"  ATTENTION : {len(new_sufkeys)} != 85 attendu ({'+' if len(new_sufkeys) > 85 else ''}{len(new_sufkeys)-85})")

# Verification securite : aucune nouvelle cle ne doit collider avec une existante
collisions = [c for c in new_sufkeys if c in cles_c]
if collisions:
    print(f"  ERREUR : {len(collisions)} collisions detectees - stop"); sys.exit(2)

# ============================================================
# 3. Calcul parc UI avant (algo bgRncLots+bgBdnbResid dedup bgid)
# ============================================================
def calc_parc_ui(doc):
    """Reproduit l'algo UI : pour chaque bgid, prend max(nb_lots_habitation RNC,
    nb_log_bdnb residentiel) sur l'ancre primaire (premiere apparue).
    Approximation : ici simple sum sans dedup pour reference rapide,
    + sum dedup bgid (max nb_log_bdnb par bgid pour les ancres residentielles).
    """
    ad = doc["adresses"]
    co_by_cle = {c.get("cle_adresse"): c for c in doc["coproprietes"] if c.get("cle_adresse")}
    by_bgid = {}
    USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    parc_strict_logement = 0
    for a in ad:
        cle = a.get("cle") or ""
        if a.get("_fusion_auto"): continue  # FA dedup naturelle
        bgid = a.get("batiment_groupe_id") or "<NOBGID>" + cle  # singleton si no bgid
        # nb_lots RNC prioritaire si copro existe sur la cle
        cm = co_by_cle.get(cle)
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        # priorite RNC > BDNB resid > 0
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid:
            by_bgid[bgid] = max(by_bgid[bgid], n)
        else:
            by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

parc_av, n_bg_av = calc_parc_ui(doc_c)
print()
print(f"  Parc UI AVANT (algo dedup bgid, RNC>BDNB resid) :")
print(f"    Parc total : {parc_av} lgts sur {n_bg_av} bgids actifs")

# ============================================================
# 4. Backup
# ============================================================
shutil.copy2(CURRENT, BAK)
print()
print(f"  Backup ecrit : {BAK.name}")

# ============================================================
# 5. Injection
# ============================================================
print()
print(f"  Injection {len(new_sufkeys)} cles ...")
appended = []
for cle in new_sufkeys:
    entry = dict(by_cle_s[cle])  # copie shallow OK car valeurs immuables ou listes/dict simples
    # Tag d'origine pour tracage
    entry["_injection_indice"] = "cherrypick_indice_de_repetition_2026-05-23"
    doc_c["adresses"].append(entry)
    appended.append(cle)

# Verification : nb adresses augmente du bon delta
if len(doc_c["adresses"]) != N0 + len(new_sufkeys):
    print(f"  ERREUR : count adresses post-injection ({len(doc_c['adresses'])}) != {len(ad_c)} + {len(new_sufkeys)}"); sys.exit(3)

# ============================================================
# 6. Parc UI apres
# ============================================================
parc_ap, n_bg_ap = calc_parc_ui(doc_c)
print(f"  Parc UI APRES  : {parc_ap} lgts sur {n_bg_ap} bgids actifs")
print(f"  Delta parc : {parc_ap - parc_av:+d} lgts  |  bgids : {n_bg_ap - n_bg_av:+d}")

# Top 10 contributions parc (cles avec gros bdnb)
print()
print(f"  Top 10 contributions parc (cle, bdnb, bgid) :")
sorted_new = sorted(appended, key=lambda c: -(by_cle_s.get(c, {}).get("nb_log_bdnb") or 0))
for cle in sorted_new[:10]:
    e = by_cle_s.get(cle, {})
    print(f"    {cle:36s}  bdnb={e.get('nb_log_bdnb')}  bgid=...{(e.get('batiment_groupe_id') or '-')[-9:]}")

# Distribution suffixes injectes
from collections import Counter
suf_cnt = Counter(SUFFIX_RX.match(c).group(2) for c in appended)
print()
print(f"  Distribution suffixes injectes : {dict(suf_cnt)}")

# ============================================================
# 7. Sauvegarde
# ============================================================
with CURRENT.open("w", encoding="utf-8") as f:
    json.dump(doc_c, f, ensure_ascii=False, indent=2)

# Re-read verif
doc_check = json.loads(CURRENT.read_text(encoding="utf-8"))
n_ad_check = len(doc_check["adresses"])
n_co_check = len(doc_check["coproprietes"])
inj_count = sum(1 for a in doc_check["adresses"] if a.get("_injection_indice"))
print()
print(f"  Re-read verif : {n_ad_check} adresses ({N0 + len(new_sufkeys)} attendu) | "
      f"{n_co_check} copros (inchangees)")
print(f"  Cles injectees re-readables : {inj_count} (attendu {len(new_sufkeys)})")
if n_ad_check != N0 + len(new_sufkeys) or inj_count != len(new_sufkeys):
    print("  ERREUR re-read"); sys.exit(4)

# Verification 0 copro modifiee
if n_co_check != len(doc_c["coproprietes"]):
    print("  ERREUR : nb copros modifie"); sys.exit(5)

print()
print("=" * 90)
print(">>> CHERRY-PICK TERMINE")
print(f"    Light : {N0} -> {n_ad_check} adresses (+{len(new_sufkeys)})")
print(f"    Parc UI : {parc_av} -> {parc_ap} lgts (+{parc_ap-parc_av})")
print(f"    Backup : {BAK.name}")
print("=" * 90)
