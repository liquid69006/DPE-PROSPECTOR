#!/usr/bin/env python3
"""Detecteur noms ambigus (Piege 5, PIPELINE.md §6) - READ-ONLY, secteur-agnostique, 100% offline.

Signale les proprietaires dont le LIBELLE est "social-sounding" (lexique de
mots composes) MAIS dont la forme juridique n'est PAS un vrai bailleur
(is_hlm_social=False). Cas de reference : 227 FELIX FAURE = "ASSOCIATION DE
L HOTEL SOCIAL" (asso de droit prive, copro classique, NI mono NI social).

Source : majic_locaux2_2025.parquet (denomination + forme_juridique_libelle +
groupe_personne_libelle) ; parcelles via enrich. N'ecrit JAMAIS en KV.

Garde-fous : skip owner si is_hlm_social (vrai bailleur coherent) ; skip
adresse deja sociale (pct lots HLM >= cfg.social_pct_min) ; skip cle arbitree
(cfg.social_overrides).

Usage : python scripts/_detect_noms_ambigus.py --secteur <slug>
"""
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from secteur_config import load_secteur, slugs  # source unique de verite

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"

# Lexique social-sounding : mots COMPOSES (precis). "HABITAT"/"SOCIAL" seuls
# sont volontairement EXCLUS : les vrais bailleurs (Paris Habitat, GRANDLYON
# HABITAT...) sont deja captes par is_hlm_social via gp/forme ; pas de double
# signal cote denomination -> precision sans bruit.
SOCIAL_LEXICON = (
    "HOTEL SOCIAL", "LOGEMENT SOCIAL", "RESIDENCE SOCIALE",
    "HABITATIONS SOCIALES", "FOYER", "MAISON RELAIS",
    "PENSION DE FAMILLE", "SOLIDARITE", "AIDE AU LOGEMENT",
    "ASSOCIATION DE L HABITAT",
)


def _norm(s):
    """Majuscule + apostrophes->espaces + espaces collapses (matching robuste)."""
    s = (s or "").upper().replace("'", " ")
    return re.sub(r"\s+", " ", s).strip()


def is_hlm_social(gp_lib, denomination, forme):
    """Copie pure de _scan_majic_kv_untagged_dl.py : un VRAI bailleur ?"""
    g = (gp_lib or "").lower()
    d = (denomination or "").lower()
    f = (forme or "").lower()
    if "office hlm" in g or " hlm" in g or g.startswith("hlm"):
        return True
    if " hlm " in d or "hlm-" in d or "habitat" in d or "logement social" in d:
        return True
    if "office public" in f or "office hlm" in f:
        return True
    return False


def matches_social(denomination):
    """1er mot du lexique present dans la denomination, sinon None."""
    d = _norm(denomination)
    for w in SOCIAL_LEXICON:
        if _norm(w) in d:
            return w
    return None


def load_light(cfg):
    return json.loads(cfg.light.read_text(encoding="utf-8"))["adresses"]


def load_enrich_parcelles(cfg):
    if not cfg.enrich_majic.exists():
        return {}
    e = json.loads(cfg.enrich_majic.read_text(encoding="utf-8"))
    return {r["cle"]: (r.get("parcelles_bdnb") or []) for r in e.get("results", [])}


def load_override_cles(cfg):
    if not cfg.social_overrides.exists():
        return set()
    o = json.loads(cfg.social_overrides.read_text(encoding="utf-8"))
    return {x.get("cle") for x in o.get("overrides", []) if x.get("cle")}


def owners_by_parcelle(cfg):
    """{parcelle_bdnb: {siren: {denom, forme, gp, lots}}} via bulk MAJIC (P+E)."""
    pref = cfg.pref_by_commune()
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", cfg.dep),
        ("code_commune", "in", cfg.code_commune),    # LISTE (multi-commune)
    ])
    df = tbl.to_pandas()
    df = df[df["code_droit"].isin({"P", "E"})].copy()
    df["numero_siren"] = df["numero_siren"].fillna("-")
    df["_pref"] = df["code_commune"].astype(str).map(pref)
    df = df[df["_pref"].notna()]
    df["_parc"] = (df["_pref"] + df["section"].astype(str)
                   + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
    out = defaultdict(dict)
    for (parc, sir), sub in df.groupby(["_parc", "numero_siren"]):
        out[parc][str(sir)] = {
            "denom": str(sub["denomination"].iloc[0] or ""),
            "forme": str(sub["forme_juridique_libelle"].iloc[0] or ""),
            "gp": str(sub["groupe_personne_libelle"].iloc[0] or ""),
            "lots": int(len(sub)),
        }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", default="dauphine-lacassagne",
                        help="slug secteur (defaut: dauphine-lacassagne)")
    args = parser.parse_args()
    cfg = load_secteur(args.secteur)

    print("=" * 78)
    print(f"DETECT NOMS AMBIGUS {cfg.short.upper()}  (Piege 5, offline)")
    print("=" * 78)

    ad = load_light(cfg)
    parcs_by_cle = load_enrich_parcelles(cfg)
    override_cles = load_override_cles(cfg)
    print(f"  adresses light : {len(ad)} | overrides exclus : {len(override_cles)}")
    print("  lecture MAJIC bulk...")
    own = owners_by_parcelle(cfg)
    print(f"  parcelles MAJIC indexees : {len(own)}")

    ambigus = []
    n_scanned = n_skip_social = 0
    for a in ad:
        if a.get("_fusion_auto"):
            continue
        cle = a.get("cle") or ""
        if not cle or cle in override_cles:
            continue
        parcs = parcs_by_cle.get(cle) or []
        if not parcs:
            continue
        owners = {}
        for p in parcs:
            for sir, o in own.get(p, {}).items():
                if sir in owners:
                    owners[sir]["lots"] += o["lots"]
                else:
                    owners[sir] = dict(o)
        if not owners:
            continue
        n_scanned += 1
        # garde-fou : adresse deja sociale (pct lots HLM)
        tot = sum(o["lots"] for o in owners.values())
        hlm = sum(o["lots"] for o in owners.values()
                  if is_hlm_social(o["gp"], o["denom"], o["forme"]))
        if tot and hlm * 100.0 / tot >= cfg.social_pct_min:
            n_skip_social += 1
            continue
        # flag owners : libelle social-sounding ET pas vrai bailleur
        for sir, o in owners.items():
            mot = matches_social(o["denom"])
            if mot and not is_hlm_social(o["gp"], o["denom"], o["forme"]):
                ambigus.append({
                    "cle": cle,
                    "adresse": a.get("adresse") or cle.replace("|", " "),
                    "siren": sir, "denomination": o["denom"],
                    "forme_juridique": o["forme"], "groupe_personne": o["gp"],
                    "lots": o["lots"], "total_lots_pm": tot,
                    "pct_proprio": round(o["lots"] * 100.0 / tot, 1) if tot else 0,
                    "mot_declencheur": mot,
                    "is_hlm_social": False,
                    "raison": "libelle social-sounding mais forme non-bailleur",
                    "status": "to_arbitrate",
                })

    out = {
        "metadata": {
            "secteur": cfg.slug, "short": cfg.short,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "offline",
            "total_adresses_scannees": n_scanned,
            "total_ambigus": len(ambigus),
            "total_skip_deja_social": n_skip_social,
            "total_exclus_overrides": len(override_cles),
        },
        "ambigus": ambigus,
    }
    outp = cfg.light.parent / f"_detect_noms_ambigus_{cfg.short}.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> ambigus={len(ambigus)} (skip deja-social={n_skip_social})")
    print(f"  ecrit : {outp.name}")


if __name__ == "__main__":
    main()
