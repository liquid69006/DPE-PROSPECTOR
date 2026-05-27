#!/usr/bin/env python3
"""Controle des 27 cles reclassees social->mixte/copro_non_immat.

Verifie qu'aucune n'est un FAUX POSITIF du biais "mutations parcelle
attribuees aux FA-sources" (cf 11 DAUPHINE zone grise).

LECTURE SEULE.

Pour chaque cle parmi les 27 :
  1. Est-elle FA-source (_fusion_auto=True) ?
  2. Si oui, vers quelle ancre pointe _fusion_cible ?
  3. mut Apt 5 ans a son ADRESSE EXACTE (pas la parcelle)
  4. mut Apt 5 ans sur la PARCELLE (ce que comptait l'ancien diag)
  5. Verdict : reclassement justifie ?
       - ANCRE avec own ventes > 0   -> justifie
       - FA-source avec 0 own ventes -> FAUX POSITIF du diag (sans
         impact metier puisque sumVpa(FA)=0 dans sctGen)
       - FA-source avec own ventes > 0 -> a investiguer
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")

ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def parse_cle(cle):
    parts = cle.split("|")
    if len(parts) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", parts[0].strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2), toks(parts[2])


def parcelle_to_dvf_key(parc):
    sec = parc[8:10]
    plan = parc[10:].lstrip("0") or "0"
    return (sec, plan)


# ============================================================
print("=" * 78)
print("CONTROLE DES 27 RECLASSEES social->mixte/copro_non_immat")
print("=" * 78)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
by_cle = {(a.get("cle") or ""): a for a in ad}
kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
enrich_by_cle = {r["cle"]: r for r in enrich["results"]}
overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
ov_by_cle = {o["cle"]: o for o in overrides.get("overrides", [])}

# ---------- Index DVF ----------
print("\n  Chargement DVF...")
dvf = json.loads(DVF.read_text(encoding="utf-8"))

# 1) Index DVF par adresse EXACTE (No voie + B/T/Q + voie_toks)
dvf_exact = defaultdict(list)
# 2) Index DVF par parcelle (Section + plan)
dvf_by_parc = defaultdict(list)
for m in dvf:
    if str(m.get("Code type local") or "").strip() not in ("1", "2"):
        continue
    # Adresse exacte
    nv = (m.get("No voie") or "").strip()
    if nv:
        try:
            nv_int = int(nv)
            btq = (m.get("B/T/Q") or "").strip().upper()
            vt = toks(m.get("Voie") or "")
            if vt:
                dvf_exact[(nv_int, btq, vt)].append(m)
        except (TypeError, ValueError):
            pass
    # Parcelle
    sec = m.get("Section") or ""
    plan = (m.get("No plan") or "").lstrip("0") or "0"
    if sec:
        dvf_by_parc[(sec, plan)].append(m)


def dedup(rows):
    seen = set()
    out = []
    for m in rows:
        sig = (m.get("Date mutation"), m.get("No disposition"),
               m.get("Valeur fonciere"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(m)
    return out


def mut_exact(cle):
    parsed = parse_cle(cle)
    if not parsed:
        return 0
    num, suffix, vt = parsed
    return len(dedup(dvf_exact.get((num, suffix, vt), [])))


def mut_parcelle(cle):
    e = enrich_by_cle.get(cle, {})
    parcs = e.get("parcelles_bdnb") or []
    seen = set()
    for parc in parcs:
        for m in dvf_by_parc.get(parcelle_to_dvf_key(parc), []):
            seen.add((m.get("Date mutation"), m.get("No disposition"),
                      m.get("Valeur fonciere")))
    return len(seen)


# ---------- Boucle de controle ----------
print()
print(f"  Cles reclassees a controler : {len(ov_by_cle)}")
print()

results = []
for cle, ov in ov_by_cle.items():
    a = by_cle.get(cle, {})
    cp = co_by_cle.get(cle, {})
    fa = bool(a.get("_fusion_auto"))
    cible = a.get("_fusion_cible") or a.get("_fusion_auto_target") or ""
    own_vlog = a.get("nb_ventes_logement") or 0
    own_vpa = a.get("ventes_par_an_logement") or {}
    me = mut_exact(cle)
    mp = mut_parcelle(cle)
    me_an = me / 5
    mp_an = mp / 5
    cur_tag = (assigns.get(cle) or {}).get("type", "(absent)")
    new_tag = ov.get("new_tag")

    # Verdict
    if not fa:
        # Ancre : reclassement justifie si own ventes > 0 OU pct_corrige < 60
        if own_vlog > 0 or me_an >= 2:
            verdict = "JUSTIFIE (ancre avec ventes propres)"
        else:
            # ancre sans ventes propres et pct_corrige bas
            verdict = "JUSTIFIE (ancre pct<60%)"
    else:
        # FA-source
        if own_vlog == 0 and me_an == 0:
            verdict = "FAUX POSITIF (FA-source 0 vente propre)"
        elif own_vlog > 0 or me_an > 0:
            verdict = "JUSTIFIE (FA-source avec ventes propres)"
        else:
            verdict = "A REVOIR (FA-source cas particulier)"

    results.append({
        "cle": cle, "fa": fa, "cible_fa": cible,
        "own_vlog": own_vlog, "own_vpa": own_vpa,
        "mut_exact_5": me, "mut_exact_an": me_an,
        "mut_parc_5": mp, "mut_parc_an": mp_an,
        "cur_tag": cur_tag, "new_tag": new_tag,
        "verdict": verdict,
        "pct_cor": ov.get("social_pct_corrige"),
    })

# Tri : ancres d'abord (justifies), puis FA-sources
results.sort(key=lambda r: (r["fa"], -r["mut_exact_an"], -r["own_vlog"]))

# ---------- Tableau global ----------
print("=" * 130)
print("TABLEAU : 27 cles reclassees, tri (ancres d'abord par ventes propres)")
print("=" * 130)
print(f"  {'#':>3} {'cle':32s} {'FA?':>3} {'cible_FA':24s} "
      f"{'own_v':>5} {'me/an':>7} {'mp/an':>7} {'verdict'}")
print("  " + "-" * 128)
for i, r in enumerate(results, 1):
    fa_flag = "OUI" if r["fa"] else "non"
    cible = (r["cible_fa"] or "-")[:22]
    print(f"  {i:>3} {r['cle']:32s} {fa_flag:>3} {cible:24s} "
          f"{r['own_vlog']:>5} {r['mut_exact_an']:>6.2f} "
          f"{r['mut_parc_an']:>6.2f} {r['verdict']}")

# ---------- Decompte ----------
print()
print("=" * 78)
print("DECOMPTE PAR VERDICT")
print("=" * 78)
ct = Counter(r["verdict"] for r in results)
for v, n in ct.most_common():
    print(f"  {v:50s} : {n}")

# ---------- FA-sources detaillees ----------
fa_in_27 = [r for r in results if r["fa"]]
if fa_in_27:
    print()
    print("=" * 78)
    print(f"FA-SOURCES IDENTIFIEES DANS LES 27 RECLASSEES ({len(fa_in_27)})")
    print("=" * 78)
    print(f"  {'cle':32s} {'cible_FA':24s} {'own_v':>5} {'me/an':>7} {'mp/an':>7} {'verdict'}")
    print("  " + "-" * 110)
    for r in fa_in_27:
        cible = (r["cible_fa"] or "-")[:22]
        print(f"  {r['cle']:32s} {cible:24s} "
              f"{r['own_vlog']:>5} {r['mut_exact_an']:>6.2f} "
              f"{r['mut_parc_an']:>6.2f} {r['verdict']}")

# ---------- Liste a revoir ----------
to_revoir = [r for r in results if "FAUX POSITIF" in r["verdict"]
              or "A REVOIR" in r["verdict"]]
print()
print("=" * 78)
print(f"CLES A REVOIR ({len(to_revoir)})")
print("=" * 78)
if not to_revoir:
    print("\n  AUCUNE : tous les 27 reclassements sont JUSTIFIES.")
else:
    for r in to_revoir:
        print(f"\n  {r['cle']}")
        print(f"    new_tag       : {r['new_tag']}  (depuis social)")
        print(f"    FA-source     : {r['fa']}  cible={r['cible_fa']}")
        print(f"    own ventes_log: {r['own_vlog']}  vpa={r['own_vpa']}")
        print(f"    mut/an exacte : {r['mut_exact_an']:.2f}  "
              f"(parcelle {r['mut_parc_an']:.2f})")
        print(f"    pct_corrige   : {r['pct_cor']}")
        print(f"    VERDICT : {r['verdict']}")

# ---------- Top 6 confirmes (commande user) ----------
print()
print("=" * 78)
print("CONFIRMATION DES 6 GROS CAS (consigne user)")
print("=" * 78)
CONFIRMS = ["28|RUE|ETIENNE RICHERAND", "12|RUE|ST SIDOINE",
            "59|RUE|BARABAN", "22|RUE|ST ANTOINE",
            "128|RUE|ANTOINE CHARIAL", "191|AVENUE|FELIX FAURE"]
for cle in CONFIRMS:
    r = next((x for x in results if x["cle"] == cle), None)
    if not r:
        print(f"  {cle:32s} : NON TROUVE dans les 27 reclassees")
        continue
    fa_flag = "OUI" if r["fa"] else "non"
    own_status = ("PROPRES > 0" if r["own_vlog"] > 0
                   else "0 PROPRES (FA-source attendue)")
    print(f"  {cle:32s} FA={fa_flag} own_ventes={r['own_vlog']:>3} "
          f"({own_status}) -> {r['verdict']}")
