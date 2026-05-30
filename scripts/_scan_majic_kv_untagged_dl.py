#!/usr/bin/env python3
"""Scan MAJIC exhaustif des adresses light DL sans tag KV.

Pour chaque adresse light (hors FA, sans type KV manuel) :
  1. Recupere parcelles BDNB via _enrich_majic_dl_full.json
  2. Interroge MAJIC parquet (code_droit Proprietaire/Emphyteote, exclut
     Syndic/Mandataire)
  3. Calcule social_pct (gestion via emphyteote HLM ou propriete HLM)
  4. Classifie :
       social_pct >= 60 OU Emphyteote HLM   -> SOCIAL
       social_pct 20-60                      -> MIXTE
       1 SIREN prive >= 80                   -> MONO
       usage_principal_bdnb = Tertiaire      -> BUREAUX
       sinon                                  -> laisser
  5. Affiche tableau pre-patch, trie nb_log_bdnb DESC

Sources lecture seule :
  - data/secteur_dauphine_lacassagne_light.json
  - data/_enrich_majic_dl_full.json   (parcelles_bdnb + sirens cached)
  - data/_kv_assign_dl.json           (tags KV locaux)
  - majic_locaux2_2025.parquet        (code_droit + groupe_personne_libelle)

Mode : --dry (display only, defaut)   ou   --apply (POST KV atomique)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from secteur_config import load_secteur  # source unique de verite (data/secteurs.json)

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"   # source nationale, tous secteurs

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
# JWT lu depuis env DPE_JWT, requis uniquement en mode --apply.
JWT = os.environ.get("DPE_JWT") or ""
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")

# Globals secteur-dependants : peuples par _init_secteur() depuis secteurs.json.
LIGHT = KV_LOCAL = ENRICH = OVERRIDES = DVF = AGENCE = None
DEP = None                               # scalaire (1 secteur = 1 dep)
CODE_COMMUNE = BDNB_PREFIX = None        # LISTES (multi-commune)
SOCIAL_PCT_MIN = MUT_PER_YEAR_MIN = None


def _init_secteur(slug):
    global LIGHT, KV_LOCAL, ENRICH, OVERRIDES, DVF, AGENCE
    global DEP, CODE_COMMUNE, BDNB_PREFIX, SOCIAL_PCT_MIN, MUT_PER_YEAR_MIN
    global HLM_NEEDLE_RE, PUBLIC_NEEDLE_RE
    cfg = load_secteur(slug)
    LIGHT, KV_LOCAL, ENRICH = cfg.light, cfg.kv_local, cfg.enrich_majic
    OVERRIDES, DVF, AGENCE  = cfg.social_overrides, cfg.dvf_path, cfg.slug
    DEP = cfg.dep
    CODE_COMMUNE, BDNB_PREFIX = cfg.code_commune, cfg.bdnb_dep_prefix
    SOCIAL_PCT_MIN, MUT_PER_YEAR_MIN = cfg.social_pct_min, cfg.mut_apt_per_year_min
    # Needles HLM secteur (secteurs.json[metier.hlm_needles]). Matching par
    # LIMITE DE MOT (\b...\b) et NON sous-chaine nue : evite les faux positifs
    # type "adoma" dans CADOMAT/VECADOMAX ou "oph" dans SOPHIE/CLAUNOPHI.
    # Repli gracieux sur None si absent/vide (ex MP _TODO) -> is_hlm_social
    # retombe sur les seules sous-chaines hardcodees, sans crash.
    HLM_NEEDLE_RE = _compile_needles(getattr(cfg, "hlm_needles", None))
    # Idem pour les owners publics non-HLM (SEM, Departement, Foncieres
    # publiques, Hospices, CROUS...). Meme repli gracieux None.
    PUBLIC_NEEDLE_RE = _compile_needles(getattr(cfg, "public_non_hlm", None))
    return cfg


def _compile_needles(needles):
    """Compile une alternation \\b(...)\\b a partir des needles (strip+lower,
    dedup). Renvoie None si aucune needle exploitable."""
    cleaned = sorted({n.strip().lower()
                      for n in (needles or ()) if n and n.strip()})
    if not cleaned:
        return None
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in cleaned)
                      + r")\b")


# Defaut module-level : si _init_secteur pas encore appele (import direct des
# helpers), pas de needle -> comportement historique.
HLM_NEEDLE_RE = None
PUBLIC_NEEDLE_RE = None


# ---------- Helpers ----------
def normalize_gp(s):
    return (s or "").lower()


def is_hlm_social(gp_lib, denomination, forme):
    g = normalize_gp(gp_lib)
    d = normalize_gp(denomination)
    f = normalize_gp(forme)
    # Sous-chaines hardcodees historiques (conservees telles quelles).
    if "office hlm" in g or " hlm" in g or g.startswith("hlm"):
        return True
    if " hlm " in d or "hlm-" in d or "habitat" in d or "logement social" in d:
        return True
    if "office public" in f or "office hlm" in f:
        return True
    # UNION : needles HLM du secteur (secteurs.json), matching \b...\b. Capte
    # les bailleurs dont le nom ne contient pas "habitat/hlm" (ADOMA, IN'LI,
    # OPH, SACVL, ERILIA...). Repli gracieux : HLM_NEEDLE_RE=None si non config.
    if HLM_NEEDLE_RE is not None:
        if HLM_NEEDLE_RE.search(f"{d} {g} {f}"):
            return True
    return False


def is_public(gp_lib, forme, denomination=""):
    g = normalize_gp(gp_lib)
    f = normalize_gp(forme)
    d = normalize_gp(denomination)
    # Sous-chaines hardcodees historiques (conservees telles quelles).
    if "etablissements publics" in g or u"établissements publics" in g:
        return True
    if "collectivit" in f or "publique" in f or "etat" in g:
        return True
    if "metropole" in normalize_gp(forme) or "commune" in g:
        return True
    # UNION : needles public-non-HLM du secteur (secteurs.json), matching
    # \b...\b. Capte SEM / Departement / Foncieres publiques / Hospices...
    # dont le nom est dans la DENOMINATION. Repli gracieux : None si non config.
    if PUBLIC_NEEDLE_RE is not None:
        if PUBLIC_NEEDLE_RE.search(f"{d} {g} {f}"):
            return True
    return False


def is_sci_or_prive(gp_lib, denomination, forme):
    g = normalize_gp(gp_lib)
    d = normalize_gp(denomination)
    f = normalize_gp(forme)
    if d.startswith("sci ") or d.startswith("scic ") or " sci " in d:
        return True
    if "soci" in f or "sas" in f or "sarl" in f:
        return True
    if "soci" in g and "publics" not in g:
        return True
    return False


def is_pp(gp_lib):
    g = normalize_gp(gp_lib)
    return "personne physique" in g or "personnes physiques" in g


def classify_siren(gp_lib, denomination, forme):
    if is_hlm_social(gp_lib, denomination, forme):
        return "HLM"
    if is_public(gp_lib, forme, denomination):
        return "PUBLIC"
    if is_pp(gp_lib):
        return "PP"
    if is_sci_or_prive(gp_lib, denomination, forme):
        return "PRIVE"
    return "AUTRE"


# ---------- Normalisation voie (pour DVF adresse exacte) ----------
_ABBR_VOIE = {"SAINT": "ST", "SAINTE": "STE",
              "DOCTEUR": "DR", "PROFESSEUR": "PR"}
_ART_VOIE = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A",
             "AU", "AUX", "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(_ABBR_VOIE.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in _ART_VOIE))


def parse_cle(cle):
    """ 'NUM[B/T/A...]|TYPE|VOIE' -> (num_int, suffix_upper, voie_toks). """
    parts = (cle or "").split("|")
    if len(parts) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", parts[0].strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2), toks(parts[2])


def build_dvf_exact_index():
    """Indexe les mutations Apt+Maison par (num_int, B/T/Q, voie_toks).
    Renvoie un dict pour lookup O(1) ; mutations distinctes via dedup
    par (Date, No disposition, Valeur fonciere)."""
    dvf = json.loads(DVF.read_text(encoding="utf-8"))
    idx = defaultdict(list)
    for m in dvf:
        if str(m.get("Code type local") or "").strip() not in ("1", "2"):
            continue
        nv = (m.get("No voie") or "").strip()
        if not nv:
            continue
        try:
            nv_int = int(nv)
        except (TypeError, ValueError):
            continue
        btq = (m.get("B/T/Q") or "").strip().upper()
        vt = toks(m.get("Voie") or "")
        if not vt:
            continue
        idx[(nv_int, btq, vt)].append(m)
    return idx


def mut_apt_an_exact(cle, dvf_idx):
    """Mutations Apt+Maison /an a l'ADRESSE EXACTE du cle.
    Jamais a la parcelle : evite le biais quand la parcelle contient
    plusieurs batiments (HLM + prive voisin).
    Pour une FA-source legit avec own_ventes > 0 (ex 84B), DVF a des
    rows avec son suffixe -> match.
    Pour une cle sans suffixe (ex 28), seules les rows avec B/T/Q vide
    matchent : '28' ne capture PAS '28B' (isolation stricte par cle)."""
    parsed = parse_cle(cle)
    if not parsed:
        return 0.0
    num, suffix, vt = parsed
    seen = set()
    for m in dvf_idx.get((num, suffix, vt), []):
        sig = (m.get("Date mutation"), m.get("No disposition"),
               m.get("Valeur fonciere"))
        seen.add(sig)
    return len(seen) / 5.0


def load_overrides():
    """Charge _social_overrides_dl.json -> dict {cle: ov_info}.
    Vide si fichier absent."""
    if not OVERRIDES.exists():
        return {}
    try:
        ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        return {o["cle"]: o for o in ov.get("overrides", [])
                if o.get("cle")}
    except Exception as e:
        print(f"  [warn] _social_overrides_dl.json illisible : {e}")
        return {}


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", default="dauphine-lacassagne",
                        help="slug secteur (defaut: dauphine-lacassagne)")
    parser.add_argument("--apply", action="store_true",
                        help="POST KV atomique apres affichage")
    parser.add_argument("--json", default=None,
                        help="exporte rows[] (classification complete) vers ce chemin JSON")
    parser.add_argument("--ignore-kv", action="store_true",
                        help="banc d'essai tag-aveugle : ne PAS skipper les cles "
                             "deja taggees en KV, re-deriver reco pour TOUTES "
                             "(defaut OFF = comportement historique inchange). "
                             "A utiliser avec --json vers un fichier DEDIE "
                             "(ex _scan_rows_full.json), jamais l'export pipeline.")
    args = parser.parse_args()
    cfg = _init_secteur(args.secteur)

    # 1. Inputs
    print("=" * 78)
    print(f"SCAN MAJIC KV UNTAGGED {cfg.short.upper()}")
    print("=" * 78)

    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
    assigns = kv.get("assignments", {})
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}

    # Charge overrides (filet anti-regression : ces cles ne doivent
    # JAMAIS etre re-taguees social par un recalcul automatique)
    overrides_by_cle = load_overrides()

    # Charge + indexe DVF (pour signal anti faux-positif social)
    dvf_idx = build_dvf_exact_index()

    print(f"  light adresses     : {len(ad)}")
    print(f"  KV local assigns   : {len(assigns)}")
    print(f"  enrich majic rows  : {len(enrich_by_cle)}")
    print(f"  social overrides   : {len(overrides_by_cle)} cles protegees "
          f"(dvf_decollect)")
    print(f"  dvf adresses uniques indexees : {len(dvf_idx)}")

    # 2. Candidates : raffinement FA-source a 2 conditions
    # - EXCLURE si _fusion_auto=True AND own_ventes==0 (facade fictive,
    #   DVF n'utilise pas son suffixe : ex 11 DAUPHINE 25B/27B/.../55D,
    #   2B DAUPHINE). Les inclure introduirait le biais parcelle-vs-cle.
    # - GARDER si _fusion_auto=True AND own_ventes>0 (FA-source legit,
    #   DVF reconnait son suffixe : ex 84B DAUPHINE 9 ventes propres).
    # - Skip les cles deja taggees (pas de re-tag).
    candidates = []
    n_excl_fa_phantom = 0
    n_fa_legit_kept = 0
    n_excl_already_tagged = 0
    for a in ad:
        cle = a.get("cle") or ""
        is_fa = bool(a.get("_fusion_auto"))
        own_vlog = int(a.get("nb_ventes_logement") or 0)
        if is_fa and own_vlog == 0:
            n_excl_fa_phantom += 1
            continue
        if is_fa and own_vlog > 0:
            n_fa_legit_kept += 1
        t = ((assigns.get(cle) or {}).get("type")) or ""
        if t and not args.ignore_kv:
            n_excl_already_tagged += 1
            continue
        candidates.append(a)
    print(f"  exclus FA fictive (own=0)    : {n_excl_fa_phantom}")
    print(f"  FA legit incluses (own>0)    : {n_fa_legit_kept}")
    print(f"  exclus deja taggees           : {n_excl_already_tagged}")
    print(f"  candidates total              : {len(candidates)}")

    # 3. Collect parcelles (from enrich cache when possible)
    needed_parcels = set()
    cle_to_parcels = {}
    for a in candidates:
        cle = a["cle"]
        e = enrich_by_cle.get(cle)
        parcs = (e.get("parcelles_bdnb") if e else None) or []
        cle_to_parcels[cle] = parcs
        for p in parcs:
            needed_parcels.add(p)
    print(f"  parcelles uniques  : {len(needed_parcels)}")

    # 4. MAJIC global query
    sections = sorted({p[8:10] for p in needed_parcels})
    parcel_nums = sorted({int(p[10:]) for p in needed_parcels})
    print(f"  sections MAJIC     : {len(sections)} ({sections[:8]}{'...' if len(sections) > 8 else ''})")
    print(f"  MAJIC parquet query global...")
    tbl = pq.read_table(MAJIC, filters=[
        ("departement", "=", DEP),
        ("code_commune", "in", CODE_COMMUNE),      # LISTE (multi-commune: MP=115+107)
        ("section", "in", sections),
    ])
    df = tbl.to_pandas()
    # Filter to relevant parcelles ; prefixe BDNB resolu PAR COMMUNE
    _pref_by_commune = dict(zip(CODE_COMMUNE, BDNB_PREFIX))   # DL: {'383':'69383000'}
    df["_parc"] = (df["code_commune"].astype(str).map(_pref_by_commune)
                   + df["section"].astype(str)
                   + df["numero_parcelle"].apply(lambda x: f"{int(x):04d}"))
    df = df[df["_parc"].isin(needed_parcels)].copy()
    # Exclude syndic/mandataire (only Proprietaire + Emphyteote count)
    keep_droits = {"P", "E"}
    df = df[df["code_droit"].isin(keep_droits)].copy()
    print(f"  MAJIC rows utiles  : {len(df)} (code_droit P+E)")

    # 5. Aggregate by parcelle x (siren, code_droit, denomination, gp, forme)
    aggreg = defaultdict(lambda: defaultdict(int))
    meta = {}  # (siren, code_droit) -> meta
    for _, row in df.iterrows():
        parc = row["_parc"]
        sir = str(row["numero_siren"] or "-")
        dr = str(row["code_droit"] or "-")
        gp = str(row["groupe_personne_libelle"] or "")
        dn = str(row["denomination"] or "")
        fj = str(row["forme_juridique_libelle"] or "")
        key = (sir, dr)
        aggreg[parc][key] += 1
        meta[key] = {"gp": gp, "dn": dn, "fj": fj,
                     "class": classify_siren(gp, dn, fj),
                     "droit_lib": str(row["code_droit_libelle"] or "")}

    # 6. Classify each candidate
    rows = []
    for a in candidates:
        cle = a["cle"]
        parcs = cle_to_parcels.get(cle) or []
        bdnb = a.get("nb_log_bdnb") or 0
        vlog = a.get("nb_ventes_logement") or 0
        usage = a.get("usage_principal_bdnb") or ""
        is_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))

        # Aggreger les owners sur l'union des parcelles
        owner_lots = defaultdict(int)
        for p in parcs:
            for k, n in aggreg.get(p, {}).items():
                owner_lots[k] += n
        n_tot = sum(owner_lots.values())

        # Calcul social_pct
        # Regle : si Emphyteote HLM present, social_pct = lots geres par
        # emphyteote HLM / total lots emphyteote (gestion). Sinon
        # social_pct = lots HLM proprietaires / total.
        droits_present = {k[1] for k in owner_lots}
        emphy_lots = sum(n for k, n in owner_lots.items() if k[1] == "E")
        emphy_hlm_lots = sum(n for k, n in owner_lots.items()
                             if k[1] == "E" and meta[k]["class"] == "HLM")
        prop_lots = sum(n for k, n in owner_lots.items() if k[1] == "P")
        prop_hlm_lots = sum(n for k, n in owner_lots.items()
                            if k[1] == "P" and meta[k]["class"] == "HLM")

        if emphy_lots > 0:
            social_lots = emphy_hlm_lots
            denom = emphy_lots
        else:
            social_lots = prop_hlm_lots
            denom = prop_lots if prop_lots > 0 else n_tot
        social_pct = round(social_lots * 100 / denom, 1) if denom else 0.0

        # Top SIREN prive (pour MONO)
        prive_owners = [(k, n) for k, n in owner_lots.items()
                        if meta[k]["class"] in ("PRIVE", "AUTRE", "PP")]
        if prive_owners:
            top_p = max(prive_owners, key=lambda x: x[1])
            # pct relatif aux lots PM uniquement (compatible heuristique
            # MAJIC PM-only)
            top_p_pct = round(top_p[1] * 100 / (prop_lots if prop_lots > 0 else n_tot), 1) if (prop_lots if prop_lots > 0 else n_tot) > 0 else 0
            # pct relatif au parc BDNB (vraie densite : si <80% du parc
            # alors les autres sont en PP -> pas mono)
            top_p_pct_bdnb = round(top_p[1] * 100 / bdnb, 1) if bdnb > 0 else 0
        else:
            top_p = None
            top_p_pct = 0
            top_p_pct_bdnb = 0

        # Top SIREN tous types
        if owner_lots:
            top_all = max(owner_lots.items(), key=lambda x: x[1])
        else:
            top_all = None
        # Classe du proprietaire DOMINANT (top owner) - sert au garde-fou
        # Tertiaire ci-dessous. On teste le TOP owner, pas "any owner present"
        # (un immeuble de bureaux prive avec 1 lot social ne doit pas etre
        # neutralise).
        top_all_class = meta[top_all[0]]["class"] if top_all else None

        # Signal DVF : mutations Apt+Maison /an a l'adresse EXACTE
        # (pas a la parcelle, isolation stricte par cle).
        mut_an_exact = mut_apt_an_exact(cle, dvf_idx)

        # Classification - ORDRE STRICT :
        #   1. Override (priorite ABSOLUE, decision manuelle validee
        #      DVF/terrain, prime sur TOUT y compris Tertiaire)
        #   2. Tertiaire (usage BDNB)
        #   3. social (HLM majoritaire) MAIS bascule mixte si DVF
        #      decollect (mut/an >= 2)
        #   4. mixte (HLM minoritaire 20-60%)
        #   5. mono (1 SIREN prive >= 80% PM ET BDNB)
        #   6. - (laisser)
        has_emphy_hlm = emphy_hlm_lots > 0
        if cle in overrides_by_cle:
            # PRIORITE ABSOLUE : override manuel valide (dvf_decollect).
            # Ne JAMAIS retaguer social, et conserver le tag override
            # quel que soit le signal MAJIC ou l'usage BDNB.
            ov_info = overrides_by_cle[cle]
            reco = ov_info.get("new_tag") or "mixte"
            mut_str = ov_info.get("mut_apt_per_year")
            reason = (f"PROTECTED by _social_overrides_dl.json "
                      f"(_qualif_source=dvf_decollect"
                      + (f", was mut/an={mut_str}" if mut_str is not None
                         else "")
                      + ")")
        elif usage == "Tertiaire" and not (
                social_pct >= SOCIAL_PCT_MIN
                or has_emphy_hlm
                or top_all_class == "HLM"):
            # Garde-fou : usage BDNB=Tertiaire (RDC commercial) ne doit pas
            # masquer une forte propriete sociale. On ne classe PAS bureaux si
            # soc>=min OU emphyteote HLM (freeholder prive, bailleur HLM) OU
            # proprietaire DOMINANT HLM -> on laisse retomber dans la cascade
            # owner (social/mixte/-). NB : owner PUBLIC seul n'est PAS un signal
            # social (une mairie/hopital en Tertiaire = vrais bureaux) -> exclu
            # du garde-fou pour ne pas degrader de vrais bureaux administratifs.
            reco = "bureaux"
            reason = "usage_principal_bdnb=Tertiaire"
        elif has_emphy_hlm or social_pct >= SOCIAL_PCT_MIN:
            if mut_an_exact >= MUT_PER_YEAR_MIN:
                # Signal DVF : decollectivisation active = pas social pur
                # (PP invisibles MAJIC LOCAUX 2 par RGPD)
                reco = "mixte"
                reason = (f"social_pct={social_pct}% MAIS mut/an="
                          f"{mut_an_exact:.2f} >= 2 "
                          f"(decollectivisation DVF, PP invisibles MAJIC)")
            else:
                reco = "social"
                reason = (f"Emphyteote HLM ({emphy_hlm_lots}/{emphy_lots})"
                          if has_emphy_hlm
                          else f"social_pct={social_pct}% (mut/an="
                               f"{mut_an_exact:.2f} < 2)")
        elif 20 <= social_pct < SOCIAL_PCT_MIN:
            reco = "mixte"
            reason = f"social_pct={social_pct}%"
        elif top_p and top_p_pct >= 80 and top_p_pct_bdnb >= 80:
            # vrai mono : domine PM ET couvre majorite du parc BDNB
            reco = "mono"
            reason = (f"top SIREN prive {meta[top_p[0]]['dn'][:22]} "
                      f"{top_p_pct}% PM / {top_p_pct_bdnb}% BDNB")
        else:
            reco = "-"
            reason = ""

        # Format top SIREN string
        def fmt_owner(k, n):
            if k is None:
                return "-"
            sir, dr = k
            m = meta[k]
            return f"{sir} {dr} {m['dn'][:22]}({n}/{m['class']})"

        rows.append({
            "cle": cle,
            "bdnb": bdnb,
            "vlog": vlog,
            "usage": usage,
            "is_rnc": is_rnc,
            "immat": (co_by_cle.get(cle) or {}).get("numero_immatriculation")
                       or a.get("numero_immatriculation"),
            "majic_lots_tot": n_tot,
            "social_pct": social_pct,
            "emphy_hlm_lots": emphy_hlm_lots,
            "emphy_lots": emphy_lots,
            "prop_hlm_lots": prop_hlm_lots,
            "prop_lots": prop_lots,
            "top_all": fmt_owner(top_all[0], top_all[1]) if top_all else "-",
            "top_prive": fmt_owner(top_p[0], top_p[1]) if top_p else "-",
            "top_prive_pct": top_p_pct,
            "top_prive_pct_bdnb": top_p_pct_bdnb,
            "mut_an_exact": mut_an_exact,
            "is_protected": cle in overrides_by_cle,
            "reco": reco,
            "reason": reason,
            "has_emphy_hlm": has_emphy_hlm,
            "hlm_owners": sorted(
                [{"denom": meta[k]["dn"], "lots": n}
                 for k, n in owner_lots.items() if meta[k]["class"] == "HLM"],
                key=lambda x: -x["lots"]),
        })

    rows.sort(key=lambda r: -r["bdnb"])

    # Export JSON additif (consomme par pipeline.py : pile verte + zones grises).
    if args.json:
        Path(args.json).write_text(json.dumps({
            "secteur": cfg.slug, "short": cfg.short,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "rows": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [json] {len(rows)} rows -> {Path(args.json).name}")

    # 7. Resumes
    from collections import Counter
    ct = Counter(r["reco"] for r in rows)
    print()
    print(f"  Classification : {dict(ct)}")
    print()
    # Filtrer pour affichage : ne montrer que ceux avec recommandation
    proposed = [r for r in rows if r["reco"] != "-"]
    skipped = [r for r in rows if r["reco"] == "-"]
    print(f"  Avec recommandation tag KV : {len(proposed)}")
    print(f"  Sans recommandation (skip) : {len(skipped)}")
    print()

    # 8. Tableau pre-patch
    print("=" * 168)
    print("TABLEAU PRE-PATCH - tri nb_log_bdnb DESC (recommandations uniquement)")
    print("=" * 168)
    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'usage':22s} "
          f"{'RNC':3s} {'lots':>5} {'soc%':>6} {'mut/an':>6} {'prot':4s} "
          f"{'reco':8s} {'top owner':54s} {'reason'}")
    print("  " + "-" * 166)
    for i, r in enumerate(proposed, 1):
        prot_flag = "*" if r.get("is_protected") else " "
        print(f"  {i:>3} {r['cle']:32s} {r['bdnb']:>6} {r['usage']:22s} "
              f"{'oui' if r['is_rnc'] else 'non':3s} {r['majic_lots_tot']:>5} "
              f"{r['social_pct']:>5.1f}% {r['mut_an_exact']:>5.2f}  {prot_flag:>3s}  "
              f"{r['reco']:8s} {r['top_all']:54s} {r['reason']}")

    # 9. Apply ? Non par defaut.
    if not args.apply:
        print()
        print("=" * 78)
        print(f"DRY RUN. Lance --apply apres validation pour POST KV atomique.")
        print(f"Recos : social={ct.get('social',0)}  mixte={ct.get('mixte',0)}  "
              f"mono={ct.get('mono',0)}  bureaux={ct.get('bureaux',0)}")
        print("=" * 78)
        return

    # --- APPLY ---
    if not JWT:
        sys.exit("  [abort] env var DPE_JWT absente (requise pour --apply).")
    print()
    print("=" * 78)
    print("MODE --apply : POST KV atomique")
    print("=" * 78)
    headers = {
        "Authorization": f"Bearer {JWT}",
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # GET current
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               headers={k: v for k, v in headers.items() if k != "Content-Type"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    assigns_cloud = body.get("assignments") or {}
    fusions_cloud = body.get("fusions") or {}
    noms_cloud = body.get("noms") or {}
    print(f"  [GET] assigns={len(assigns_cloud)} fusions={len(fusions_cloud)}")

    n_changes = 0
    for r in proposed:
        prev = assigns_cloud.get(r["cle"])
        prev_t = (prev or {}).get("type")
        if prev_t == r["reco"]:
            continue
        assigns_cloud[r["cle"]] = {"type": r["reco"]}
        n_changes += 1
    print(f"  [diff] {n_changes} changes")

    if n_changes == 0:
        print("  [skip] rien a appliquer")
        return

    data = json.dumps({"assignments": assigns_cloud,
                       "fusions": fusions_cloud,
                       "noms": noms_cloud}).encode("utf-8")
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            print(f"  [POST] status={resp.status} body={json.loads(resp.read())}")
    except urllib.error.HTTPError as e:
        sys.exit(f"  POST err: {e.code} {e.read().decode('utf-8','replace')}")

    # Re-GET verif
    r = urllib.request.Request(f"{API}/secteur-assignments/{AGENCE}",
                               headers={k: v for k, v in headers.items() if k != "Content-Type"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    a2 = body.get("assignments") or {}
    fails = 0
    for r in proposed:
        v = a2.get(r["cle"])
        if not v or v.get("type") != r["reco"]:
            print(f"  [FAIL] {r['cle']:34s} got {v} (expected {r['reco']})")
            fails += 1
    print(f"  [verif] {len(proposed)-fails}/{len(proposed)} OK ; {fails} FAIL")

    # Maj cache local
    kv["assignments"] = assigns_cloud
    KV_LOCAL.write_text(json.dumps(kv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [local] {KV_LOCAL.name} mis a jour ({len(assigns_cloud)} assignments)")


if __name__ == "__main__":
    main()
