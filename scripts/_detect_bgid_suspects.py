#!/usr/bin/env python3
"""Detecteur bgid suspects (Piege 4, PIPELINE.md §6) - READ-ONLY, secteur-agnostique.

Offline-first : 3 signaux candidats sur {light, enrich, cache bgid}, puis
validation LIVE BAN+BDNB UNIQUEMENT sur les candidats (pas tout le secteur).
N'ecrit JAMAIS en KV. Alimente la pile orange "a arbitrer" (jalon etape 4).

Signaux offline :
  S1 parite_opposee : bgid partage entre n° pair ET impair de la MEME voie
     (un bati enjambe rarement la rue -> artefact geocodage, cf 12 ESPERANCE).
     Garde-fou : voie >= 6 adresses ET type voie hors {PLACE/SQUARE/ALLEE/
     IMPASSE/CARREFOUR} (conventions pair/impair peu fiables, places).
  S2 faux_match_majic : majic_adresses non vide ET n° cible absent.
  S3 live_required : bgid absent du cache / parcelle inconnue -> signale SANS
     appel API (arbitrage humain decide).

Validation LIVE (candidats S1/S2 seulement) : BAN adresse -> cle_interop ->
BDNB rel_batiment_groupe_adresse -> bgid autoritaire ; si != bgid_light ->
"confirmed" (+ cross-RNC pour le score). Cache persistant
data/_cache_ban_bgid_<short>.json (re-runs rapides).

Garde-fou commun : skip toute cle deja arbitree (cfg.social_overrides).

Usage : python scripts/_detect_bgid_suspects.py --secteur <slug> [--no-live]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from secteur_config import load_secteur, slugs  # source unique de verite

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKIP_TYPES_S1 = {"PLACE", "SQUARE", "ALLEE", "IMPASSE", "CARREFOUR"}
MIN_VOIE_ADDR = 6
THROTTLE = 0.05


def parse_cle(cle):
    """'NUM[suffix]|TYPE|VOIE' -> (num:int, suffix, type, voie) ou None."""
    p = (cle or "").split("|")
    if len(p) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", p[0].strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2), p[1], p[2]


def bgid_norm(bg):
    return (bg or "").replace("bdnb-bg-", "").strip().upper()


def _lead_num(addr):
    m = re.match(r"^(\d+)", (addr or "").strip())
    return int(m.group(1)) if m else -1


# ---------- chargement ----------
def load_light(cfg):
    doc = json.loads(cfg.light.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}
    return ad, by_cle, co_by_cle


def load_enrich(cfg):
    if not cfg.enrich_majic.exists():
        return {}
    e = json.loads(cfg.enrich_majic.read_text(encoding="utf-8"))
    return {r["cle"]: r for r in e.get("results", [])}


def load_cache_bg(cfg):
    if cfg.cache_bg.exists():
        return json.loads(cfg.cache_bg.read_text(encoding="utf-8"))
    return {}


def load_override_cles(cfg):
    if not cfg.social_overrides.exists():
        return set()
    o = json.loads(cfg.social_overrides.read_text(encoding="utf-8"))
    return {x.get("cle") for x in o.get("overrides", []) if x.get("cle")}


def load_bgid_resolus(cfg):
    """Override light->bgid_ban autoritaire (manche II bgidB). {cle: bgid_ban}.
    Repli gracieux : {} si non configure / fichier absent (secteur-agnostique,
    comme nom_ambigu_resolus). Les cles _meta/_* sont ignorees."""
    p = getattr(cfg, "bgid_resolus", None)
    if not p or not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in d.items()
            if not k.startswith("_") and isinstance(v, str)}


def load_kv_tags(cfg):
    """Tags KV locaux {cle: type} (miroir cfg.kv_local) pour le garde-fou M1.
    Repli gracieux : {} si fichier absent."""
    if not cfg.kv_local.exists():
        return {}
    kv = json.loads(cfg.kv_local.read_text(encoding="utf-8"))
    return {c: (info or {}).get("type")
            for c, info in (kv.get("assignments", {}) or {}).items()
            if (info or {}).get("type")}


# ---------- signaux offline ----------
def signal_candidats(ad, enrich, cache_bg, override_cles,
                     resolus=None, kv_tags=None, co_cles=None):
    """Retourne {cle: {signaux:set, bgid_light, voisins:set, statut}}."""
    resolus = resolus or {}
    kv_tags = kv_tags or {}
    co_cles = co_cles or set()
    cand = {}
    per_voie = defaultdict(list)   # (type,voie) -> [(num,cle,bgid)]
    for a in ad:
        if a.get("_fusion_auto"):
            continue
        cle = a.get("cle") or ""
        if not cle or cle in override_cles:
            continue
        pc = parse_cle(cle)
        if not pc:
            continue
        num, _suf, typ, voie = pc
        per_voie[(typ, voie)].append((num, cle, a.get("batiment_groupe_id") or ""))

    # S1 : parite opposee partageant un bgid (voie>=6, type fiable)
    for (typ, voie), lst in per_voie.items():
        if len(lst) < MIN_VOIE_ADDR or typ in SKIP_TYPES_S1:
            continue
        by_bg = defaultdict(list)
        for num, cle, bg in lst:
            if bg:
                by_bg[bg].append((num, cle))
        for bg, items in by_bg.items():
            if len({n % 2 for n, _ in items}) == 2:   # pair ET impair
                for _num, cle in items:
                    c = cand.setdefault(cle, {"signaux": set(), "bgid_light": bg,
                                              "voisins": set(), "statut": "candidat"})
                    c["signaux"].add("parite_opposee")
                    c["voisins"].update(oc for _, oc in items if oc != cle)

    # S2 : faux-match MAJIC (cible absente des adresses MAJIC de sa parcelle)
    for a in ad:
        if a.get("_fusion_auto"):
            continue
        cle = a.get("cle") or ""
        if not cle or cle in override_cles:
            continue
        rec = enrich.get(cle)
        majic = (rec or {}).get("majic_adresses") or []
        if not majic:        # no_majic / no_parcelle -> non exploitable ici
            continue
        pc = parse_cle(cle)
        if not pc:
            continue
        if not any(_lead_num(m.get("adresse")) == pc[0] for m in majic):
            c = cand.setdefault(cle, {"signaux": set(),
                                      "bgid_light": a.get("batiment_groupe_id") or "",
                                      "voisins": set(), "statut": "candidat"})
            c["signaux"].add("faux_match_majic")

    # S3 : live_required (bgid absent cache / parcelle inconnue) sans signal S1/S2
    for a in ad:
        if a.get("_fusion_auto"):
            continue
        cle = a.get("cle") or ""
        if not cle or cle in override_cles or cle in cand:
            continue
        # bgid effectif : override resolus (bgid_ban autoritaire) prioritaire
        # sur le bgid light (perime/vide). manche II bgidB.
        bg = resolus.get(cle) or a.get("batiment_groupe_id") or ""
        parcs = ((enrich.get(cle) or {}).get("parcelles_bdnb")
                 or cache_bg.get(bg) or [])
        if not bg or not parcs:
            # (M1) bgid confirme (resolus) + decision KV posee -> ne plus
            # flaguer malgre 0 parcelle (empty_confirmed type 10 ST MARC).
            if cle in resolus and kv_tags.get(cle):
                continue
            # (RNC) copro RNC immatriculee -> ancree RNC, hors perimetre S3
            # (n'est pas hors-RNC). Sort proprement, reste untagged (252B).
            if a.get("numero_immatriculation") or cle in co_cles:
                continue
            cand[cle] = {"signaux": {"bgid_absent_cache"}, "bgid_light": bg,
                         "voisins": set(), "statut": "live_required"}
    return cand


# ---------- LIVE (BAN + BDNB ; generiques, repris de _diag_12_esperance) ----------
def http_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "dpe-detect/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ban_search(q, limit=2):
    url = ("https://api-adresse.data.gouv.fr/search/?limit="
           f"{limit}&q=" + urllib.parse.quote(q))
    try:
        return http_json(url).get("features", [])
    except Exception:
        return []


def bdnb_bg_for_ban(cle_interop):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse"
           f"?cle_interop_adr=eq.{urllib.parse.quote(cle_interop)}"
           "&select=batiment_groupe_id")
    try:
        return [r["batiment_groupe_id"] for r in http_json(url)]
    except Exception:
        return []


def bdnb_rnc_pour_bg(bg):
    url = ("https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc"
           f"?batiment_groupe_id=eq.{urllib.parse.quote(bg)}"
           "&select=numero_immatriculation")
    try:
        return [r.get("numero_immatriculation") for r in http_json(url)
                if r.get("numero_immatriculation")]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", default="dauphine-lacassagne",
                        help="slug secteur (defaut: dauphine-lacassagne)")
    parser.add_argument("--no-live", action="store_true",
                        help="signaux offline seulement, aucun appel BAN/BDNB")
    args = parser.parse_args()
    cfg = load_secteur(args.secteur)

    print("=" * 78)
    print(f"DETECT BGID SUSPECTS {cfg.short.upper()}  "
          f"(live={'non' if args.no_live else 'oui'})")
    print("=" * 78)

    ad, by_cle, co_by_cle = load_light(cfg)
    enrich = load_enrich(cfg)
    cache_bg = load_cache_bg(cfg)
    override_cles = load_override_cles(cfg)
    resolus = load_bgid_resolus(cfg)            # override light->bgid_ban (manche II)
    kv_tags = load_kv_tags(cfg)                  # tags KV miroir (garde-fou M1)
    co_cles = set(co_by_cle)                     # cles RNC (garde-fou RNC-skip)
    print(f"  adresses light : {len(ad)} | enrich : {len(enrich)} | "
          f"overrides exclus : {len(override_cles)} | bgid_resolus : {len(resolus)}"
          f" | kv_tags : {len(kv_tags)}")

    cand = signal_candidats(ad, enrich, cache_bg, override_cles,
                            resolus=resolus, kv_tags=kv_tags, co_cles=co_cles)
    n_cand = sum(1 for c in cand.values() if c["statut"] == "candidat")
    n_live_req = sum(1 for c in cand.values() if c["statut"] == "live_required")
    print(f"  candidats offline : {n_cand} | live_required : {n_live_req}")

    ban_cache_path = cfg.light.parent / f"_cache_ban_bgid_{cfg.short}.json"
    ban_cache = {}
    if ban_cache_path.exists():
        ban_cache = json.loads(ban_cache_path.read_text(encoding="utf-8"))

    pc_post = cfg.codes_postaux[0] if cfg.codes_postaux else ""
    suspects = []
    n_conf = n_ref = n_indet = 0

    for cle, c in cand.items():
        a = by_cle.get(cle, {})
        adresse = a.get("adresse") or cle.replace("|", " ")
        bgid_light = c["bgid_light"]
        parcs = ((enrich.get(cle) or {}).get("parcelles_bdnb")
                 or cache_bg.get(bgid_light) or [])
        entry = {
            "cle": cle, "adresse": adresse,
            "bgid_light": bgid_light, "bgid_ban": None,
            "signaux": sorted(c["signaux"]),
            "bgid_group_voisins": sorted(c["voisins"]),
            "parcelles_light": parcs,
            "cross_rnc": None, "verdict": c["statut"], "score": None,
            "raison": "", "status": "to_arbitrate",
        }
        if c["statut"] == "live_required":
            entry["raison"] = "bgid absent cache / parcelle inconnue - validation manuelle"
            suspects.append(entry)
            continue
        if args.no_live:
            entry["verdict"] = "candidat_offline"
            entry["raison"] = "signal(s) offline ; live non lance (--no-live)"
            suspects.append(entry)
            continue

        # --- validation live ---
        q = f"{adresse} {pc_post}".strip()
        if q in ban_cache:
            res = ban_cache[q]
        else:
            feats = ban_search(q, limit=2)
            time.sleep(THROTTLE)
            cle_interop = None
            for f in feats:
                if f.get("properties", {}).get("type") == "housenumber":
                    cle_interop = f["properties"].get("id")
                    break
            bgs = bdnb_bg_for_ban(cle_interop) if cle_interop else []
            if cle_interop:
                time.sleep(THROTTLE)
            res = {"cle_interop": cle_interop, "bgs": bgs}
            ban_cache[q] = res

        bgs = res.get("bgs") or []
        bgs_norm = {bgid_norm(b) for b in bgs}
        if not bgs_norm:
            entry["verdict"] = "live_indetermine"
            entry["raison"] = "BAN/BDNB muet (pas de housenumber ou bgid)"
            n_indet += 1
            suspects.append(entry)
        elif bgid_norm(bgid_light) in bgs_norm:
            entry["verdict"] = "refuted"          # BAN confirme le light -> pas suspect
            n_ref += 1
        else:
            bgid_ban = bgs[0]
            entry["bgid_ban"] = bgid_ban
            entry["verdict"] = "confirmed"
            immat = ((co_by_cle.get(cle) or {}).get("numero_immatriculation")
                     or a.get("numero_immatriculation"))
            cross = False
            if immat and bgid_ban:
                cross = immat in bdnb_rnc_pour_bg(bgid_ban)
                time.sleep(THROTTLE)
            entry["cross_rnc"] = cross
            entry["score"] = "high" if cross else "medium"
            entry["raison"] = ("bgid different du BAN autoritaire"
                               + (" + cross-RNC" if cross else ""))
            n_conf += 1
            suspects.append(entry)

    ban_cache_path.write_text(json.dumps(ban_cache, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    out = {
        "metadata": {
            "secteur": cfg.slug, "short": cfg.short,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "offline" if args.no_live else "offline+live",
            "total_candidats_offline": n_cand,
            "total_confirmes_live": n_conf,
            "total_refutes": n_ref,
            "total_live_indetermine": n_indet,
            "total_live_required": n_live_req,
            "total_exclus_overrides": len(override_cles),
        },
        "suspects": suspects,
    }
    outp = cfg.light.parent / f"_detect_bgid_suspects_{cfg.short}.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> confirmes={n_conf} refutes={n_ref} indetermine={n_indet} "
          f"live_required={n_live_req}")
    print(f"  ecrit : {outp.name}")


if __name__ == "__main__":
    main()
