#!/usr/bin/env python3
"""Lecture centralisee de la config par secteur (data/secteurs.json).

SOURCE UNIQUE DE VERITE : tout outil pipeline passe par load_secteur(slug).
- Aucun module ne doit lire data/secteurs.json directement (pas de json.load
  ailleurs) -> ce helper est le seul point d'entree.
- secteurs.json est lu UNE SEULE FOIS par process (cache memoire @lru_cache).

Champs geo multi-valeurs (code_commune / rnc_dep_prefix / bdnb_dep_prefix /
codes_postaux) sont exposes EN LISTES, alignees par index, pour supporter les
secteurs multi-communes (ex MP = 75115 + 75107). 'dep' reste scalaire (un
secteur appartient a un seul departement). cf. secteurs.json _meta.geo_lists_note.
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # racine = parent de scripts/
SECTEURS_JSON = ROOT / "data" / "secteurs.json"

# back-compat CLI : enrich_*.py utilisaient les slugs underscore.
_SLUG_ALIASES = {
    "dauphine_lacassagne": "dauphine-lacassagne",
    "motte_picquet": "motte-picquet",
}


@lru_cache(maxsize=1)
def _load_all():
    with open(SECTEURS_JSON, encoding="utf-8") as f:
        return json.load(f)


def canonical_slug(slug):
    """Normalise vers la forme tiret (cle de secteurs.json)."""
    return _SLUG_ALIASES.get(slug, slug)


def slugs():
    """Liste des slugs valides (hors _meta)."""
    return [k for k in _load_all() if not k.startswith("_")]


class SecteurConfig:
    """Vue typee de la config d'un secteur + chemins resolus en absolu."""

    def __init__(self, slug, raw):
        self.slug = slug
        self.raw = raw
        self.short = raw["short"]
        g = raw["geo"]
        self.dep             = g["dep"]                     # scalaire (1 secteur = 1 dep)
        self.code_commune    = list(g["code_commune"])      # LISTE
        self.rnc_dep_prefix  = list(g["rnc_dep_prefix"])    # LISTE
        self.bdnb_dep_prefix = list(g["bdnb_dep_prefix"])   # LISTE
        self.codes_postaux   = list(g["codes_postaux"])     # LISTE
        m = raw["metier"]
        self.hlm_needles    = tuple(m["hlm_needles"])
        self.public_non_hlm = tuple(m["public_non_hlm"])
        self.social_pct_min       = m["seuils"]["social_pct_min"]
        self.mut_apt_per_year_min = m["seuils"]["mut_apt_per_year_min"]
        p = raw["paths"]                                    # data/* relatifs a ROOT
        self.light            = ROOT / p["light"]
        self.kv_local         = ROOT / p["kv_local"]
        self.social_overrides = ROOT / p["social_overrides"]
        # Liste "resolus" nom_ambigu (cles tranchees non-social, exclues du
        # re-flag). Optionnel : None si non configure (repli gracieux, pas de
        # crash ; ex. secteur sans liste encore).
        self.nom_ambigu_resolus = (ROOT / p["nom_ambigu_resolus"]
                                    if p.get("nom_ambigu_resolus") else None)
        # Override light->bgid_ban autoritaire (manche II bgidB). Optionnel :
        # None si non configure (repli gracieux, secteur-agnostique, comme
        # nom_ambigu_resolus). Consomme par _detect_bgid_suspects.py (S3).
        self.bgid_resolus = (ROOT / p["bgid_resolus"]
                             if p.get("bgid_resolus") else None)
        # Cles bgid revues/acceptees par l'humain (Phase 2, gate verdict-scope
        # cote pipeline). Optionnel : None si non configure (repli gracieux).
        self.arbitres = (ROOT / p["arbitres"] if p.get("arbitres") else None)
        self.enrich_majic     = ROOT / p["enrich_majic"]
        self.cache_bg         = ROOT / p["cache_bg"]
        self.dvf_path         = Path(p["dvf_path"])         # deja absolu

    @property
    def is_dl(self):
        return self.slug == "dauphine-lacassagne"

    # zip alignes commune <-> prefixe BDNB (multi-commune)
    def pref_by_commune(self):
        """{ code_commune: bdnb_dep_prefix } aligne par index.
        DL : {'383': '69383000'} ; MP : {'115':'75115000','107':'75107000'}."""
        return dict(zip(self.code_commune, self.bdnb_dep_prefix))


@lru_cache(maxsize=None)
def load_secteur(slug):
    """Charge la config d'un secteur. Accepte tiret OU underscore (back-compat)."""
    slug = canonical_slug(slug)
    allcfg = _load_all()
    if slug not in allcfg:
        raise SystemExit(f"[secteur_config] slug inconnu: {slug!r}. "
                         f"Valides: {slugs()}")
    return SecteurConfig(slug, allcfg[slug])
