"""
Audit LECTURE SEULE des lacunes du pipeline make_light : pourquoi
certains rattachements hors-RNC n'ont PAS ete faits automatiquement,
et quelles autres adresses des 2 secteurs sont dans le meme cas.

Sortie : data/audit_lacunes_pipeline.md. Aucune ecriture des donnees.

Cibles = predicat exact "Hors-RNC actifs" de renderSecteur :
  cle non fusionnee (_fusion_auto/cible) ET cle ∉ cle_adresse copro
  ET pas de numero_immatriculation ET nb_ventes_logement > 0.

Patterns scrutes (cause-racine fournie ETAPE 1) :

P1 — Abreviation de voie non couverte par _canon_parts. La table
SUBS bidirectionnelle (GAL/GEN/GENL<->GENERAL, CAPT/CNE<->CAPITAINE,
MAL<->MARECHAL, CDT/CMDT<->COMMANDANT, DR<->DOCTEUR, PR/PROF<->
PROFESSEUR, FG<->FAUBOURG, AYRES<->AIRES, ...) est appliquee aux
tokens de la voie pour chercher une cle_adresse copro qui matche.
Cause : make_light normalise type (R->RUE), bis (BIS->B), saints
(SAINT->ST), articles tete (DE/DES/DU stripped) — mais PAS les
abreviations internes de tokens de voie. Convention etablie : alias
case-par-cas (ALIAS_RNC), pas extension SUBS (rayon d'impact pipeline
trop large, risque de collision de cles).

P2 — Meme batiment_groupe_id BDNB qu'une copro RNC, mais auto-fusion
non declenchee. Cause typique : split par parite (pair/impair) du
bgid-fusion safeguard (corner d'angle = 2 cotes), OU la copro est sur
une autre voie (auto-fusion respecte la voie via principal-sort).

P3 — Orthographe RNC vs DVF (variante non SUBS). Token-set similarity
sur (num,nat,voie) hors-RNC actif vs cle_adresse copro : meme num,
meme type, voie avec >=2 tokens communs et particules pres.

Format de sortie : ETAPE 1 (cause-racine, par famille de cas resolus
manuellement), ETAPE 2 (lacunes restantes, par pattern, par secteur),
ETAPE 3 (recommandations : SUBS extension cible / parite guard /
alias residuels). Lecture seule, aucune modification.
"""

import os
import re
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT_DL = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
LIGHT_MP = ROOT / "data" / "secteur_motte_picquet_light.json"
REPORT = ROOT / "data" / "audit_lacunes_pipeline.md"

# Table SUBS bidirectionnelle : forme abregee / variante -> forme
# canonique (developpee). Construite a partir des cas resolus
# (CAPT/GAL/AYRES/...) + abreviations frequentes des voies parisiennes/
# lyonnaises. Bidirectionnelle = on essaie les 2 sens pour matcher
# (DVF abrege vs RNC developpe ET inversement).
SUBS_PAIRS = [
    # militaires / titres (les + frequents dans le projet)
    ("GAL", "GENERAL"), ("GEN", "GENERAL"), ("GENL", "GENERAL"),
    ("MAL", "MARECHAL"), ("CDT", "COMMANDANT"), ("CMDT", "COMMANDANT"),
    ("CAPT", "CAPITAINE"), ("CNE", "CAPITAINE"), ("LT", "LIEUTENANT"),
    ("LIEUT", "LIEUTENANT"), ("COL", "COLONEL"),
    ("SGT", "SERGENT"), ("CHEV", "CHEVALIER"),
    # civils / religieux
    ("DR", "DOCTEUR"), ("PR", "PROFESSEUR"), ("PROF", "PROFESSEUR"),
    ("PRES", "PRESIDENT"), ("MGR", "MONSEIGNEUR"), ("ABBE", "ABBE"),
    ("PCE", "PRINCE"), ("PCESSE", "PRINCESSE"),
    ("MNE", "MADELEINE"), ("FG", "FAUBOURG"), ("GRDE", "GRANDE"),
    # variantes orthographiques attestees
    ("AYRES", "AIRES"),
]
# Construction du dict : forme1 -> forme2 ET forme2 -> forme1
SUBS = {}
for a, b in SUBS_PAIRS:
    SUBS.setdefault(a, b)
    SUBS.setdefault(b, a)
PARTICLES = {"DE", "DU", "DES", "LA", "LE", "L", "D", "AUX", "A", "ET"}
ACCENTS = str.maketrans("ÉÈÊÀÂÔÎÏÇÛÙ", "EEEAAOIICUU")


def _txt(s):
    s = str(s or "").translate(ACCENTS).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def voie_tokens(s):
    """Tokens d'un nom de voie, particules de tete strippees."""
    toks = _txt(s).split()
    while toks and toks[0] in PARTICLES:
        toks = toks[1:]
    return toks


def voie_canon(tokens):
    """Normalise un nom de voie via SUBS (token-a-token, particules
    sautees ; choix deterministe forme la PLUS LONGUE pour eviter les
    boucles symetriques)."""
    out = []
    for t in tokens:
        if t in PARTICLES:
            continue
        if t in SUBS:
            out.append(t if len(t) > len(SUBS[t]) else SUBS[t])
        else:
            out.append(t)
    return tuple(out)


def parse_cle(cle):
    """cle 'NUM[BIS]|TYPE|VOIE' -> (num, nat, voie_tokens, voie_canon)."""
    p = (cle or "").split("|")
    num = (p[0] or "").upper().strip() if p else ""
    nat = (p[1] or "").upper().strip() if len(p) > 1 else ""
    voie = p[2] if len(p) > 2 else ""
    toks = voie_tokens(voie)
    return num, nat, tuple(toks), voie_canon(toks)


def jaccard(a, b):
    sa, sb = set(a) - PARTICLES, set(b) - PARTICLES
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def collect(light):
    ad, co = light["adresses"], light["coproprietes"]
    by_cle = {a["cle"]: a for a in ad}
    copro_by_cle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    targets = [a for a in ad
               if a["cle"] not in fused
               and a["cle"] not in copro_by_cle
               and not a.get("numero_immatriculation")
               and (a.get("nb_ventes_logement") or 0) > 0]
    # bgid -> copro (via cle_adresse address)
    bg_to_copros = collections.defaultdict(list)
    for c in co:
        ca = c.get("cle_adresse")
        if not ca:
            continue
        ao = by_cle.get(ca)
        if ao and ao.get("batiment_groupe_id"):
            bg_to_copros[ao["batiment_groupe_id"]].append(c)
    # copro index by canonical-voie
    cop_idx_canon = collections.defaultdict(list)   # (num,nat,voie_canon) -> [copros]
    cop_idx_toks = collections.defaultdict(list)    # (num,nat,frozenset(toks-particules)) -> [copros]
    for c in co:
        ca = c.get("cle_adresse")
        if not ca:
            continue
        n, nat, toks, canon = parse_cle(ca)
        cop_idx_canon[(n, nat, canon)].append(c)
        cop_idx_toks[(n, nat, frozenset(set(toks) - PARTICLES))].append(c)
    return ad, co, by_cle, copro_by_cle, fused, targets, bg_to_copros, \
        cop_idx_canon, cop_idx_toks


def analyse(light, secteur):
    (ad, co, by_cle, copro_by_cle, fused, targets, bg_to_copros,
     cop_idx_canon, cop_idx_toks) = collect(light)
    rows = []
    for a in targets:
        cle = a["cle"]
        bg = a.get("batiment_groupe_id")
        n, nat, toks, canon = parse_cle(cle)
        rec = {
            "secteur": secteur, "cle": cle, "adresse": a.get("adresse"),
            "bg": bg, "vlog": a.get("nb_ventes_logement") or 0,
            "vtot": a.get("nb_ventes_total") or 0,
            "nblog": a.get("nb_log_bdnb"),
            "usage": a.get("usage_principal_bdnb"),
            "match": a.get("_bdnb_match"),
            "P1": None, "P2": None, "P3": None}
        # ---- P1 : SUBS canonicalisation matche une copro ?
        if canon != tuple(toks):
            m = cop_idx_canon.get((n, nat, canon)) \
                or cop_idx_canon.get((n, nat, voie_canon(canon)))
            if m and m[0].get("cle_adresse") != cle:
                c = m[0]
                # quelle paire SUBS expliquee ?
                pairs = sorted({
                    tuple(sorted([t, SUBS[t]])) for t in toks if t in SUBS})
                rec["P1"] = {"copro": c.get("cle_adresse"),
                             "immat": c.get("numero_immatriculation"),
                             "nom": c.get("nom_copropriete"),
                             "lots": c.get("nb_lots_habitation"),
                             "syndic": c.get("syndic"),
                             "pairs": pairs}
        # ---- P2 : meme bgid qu'une copro
        if bg:
            cands = [c for c in bg_to_copros.get(bg, [])
                     if c.get("cle_adresse") != cle]
            if cands:
                c = cands[0]
                anc_cle = c.get("cle_adresse")
                anc_obj = by_cle.get(anc_cle)
                cn, cnat, ctoks, ccanon = parse_cle(anc_cle)
                same_par = ((int(re.match(r"\d+", n).group()) % 2
                             == int(re.match(r"\d+", cn).group()) % 2)
                            if re.match(r"\d+", n or "")
                            and re.match(r"\d+", cn or "") else None)
                same_voie = ((nat, canon) == (cnat, ccanon))
                # sous-classification fine (cf. ETAPE 1.b/ETAPE 3) :
                anc_fused_to_src = (anc_obj and anc_obj.get("_fusion_auto")
                                    and anc_obj.get("_fusion_cible") == cle)
                anc_fused_other = (anc_obj and anc_obj.get("_fusion_auto")
                                   and not anc_fused_to_src)
                if anc_fused_to_src:
                    sub = "P2a"
                    why = ("**RE-POINT** : copro RNC ancrée enterrée "
                           "SOUS ce fantôme (auto-bgid-fusion a choisi "
                           "le phantome DVF + de ventes comme principal "
                           "→ copro invisible). Pattern A3 de "
                           "`fix_mp_cibles_horsrnc`. Re-point individuel.")
                elif anc_fused_other:
                    sub = "P2d"
                    why = ("ancre déjà fusionnée ailleurs "
                           f"(`{anc_obj.get('_fusion_cible')}`)")
                elif same_par and same_voie:
                    sub = "P2b"
                    why = ("**ORPHELIN bgid-fusion** : src ET anchor "
                           "tous deux *principals* sur même bgid+parité"
                           "+voie — l'auto-fusion n'a PAS regroupé. "
                           "Cause typique : un des deux ajouté APRÈS "
                           "make_light par `fix_horsrnc_attribution` "
                           "/ `fix_*` (chaîne §5) → ordre des passes.")
                elif not same_par:
                    sub = "P2c"
                    why = ("**CORNER parité-mixte** (garde-fou bgid-"
                           "fusion : split pair/impair → 2 buckets, "
                           "chacun < 2 membres → skip). Sécurité parc, "
                           "à instruire en ALIAS_RNC manuel.")
                elif not same_voie:
                    sub = "P2e"
                    why = ("voie/nat différent(e) : abréviation non "
                           "couverte par SUBS (chevauche P1) ou "
                           "véritable changement de nom de voie.")
                else:
                    sub = "P2?"
                    why = "autre"
                rec["P2"] = {"copro": anc_cle,
                             "immat": c.get("numero_immatriculation"),
                             "nom": c.get("nom_copropriete"),
                             "lots": c.get("nb_lots_habitation"),
                             "syndic": c.get("syndic"),
                             "bgid": bg, "same_par": same_par,
                             "same_voie": same_voie,
                             "anc_fused": bool(anc_obj
                             and anc_obj.get("_fusion_auto")),
                             "sub": sub, "why": why,
                             "n_cands": len(cands)}
        # ---- P3 : token-set similarity (>=0.6 jaccard sur tokens sans
        #          particules + meme num + meme nat) - hors P1
        if not rec["P1"]:
            tset = frozenset(set(toks) - PARTICLES)
            # essai 1 : indexe direct
            best, bsim = None, 0.6
            for c in co:
                ca = c.get("cle_adresse")
                if not ca:
                    continue
                cn, cnat, ctoks, _ = parse_cle(ca)
                if cn != n or cnat != nat:
                    continue
                if ca == cle:
                    continue
                sim = jaccard(toks, ctoks)
                if sim > bsim:
                    bsim, best = sim, c
            if best:
                rec["P3"] = {"copro": best.get("cle_adresse"),
                             "immat": best.get("numero_immatriculation"),
                             "nom": best.get("nom_copropriete"),
                             "lots": best.get("nb_lots_habitation"),
                             "sim": round(bsim, 2)}
        rows.append(rec)
    return rows, len(targets), len(co)


def main():
    light_dl = json.loads(LIGHT_DL.read_text(encoding="utf-8"))
    light_mp = json.loads(LIGHT_MP.read_text(encoding="utf-8"))
    rows_dl, nt_dl, nc_dl = analyse(light_dl, "dauphine_lacassagne")
    rows_mp, nt_mp, nc_mp = analyse(light_mp, "motte_picquet")
    rows = rows_dl + rows_mp

    def esc(s):
        return str(s).replace("|", "\\|") if s is not None else ""

    L = []
    L.append("# Audit — lacunes du pipeline make_light (rattachements "
             "hors-RNC manqués)\n")
    L.append("> Lecture seule. Cible = prédicat exact *Hors-RNC actifs* "
             "de `renderSecteur` (non fusionnée, clé ∉ `cle_adresse` "
             "copro, pas d'immat, `nb_ventes_logement>0`). Caches RNC "
             "live non sollicités ici : on raisonne sur le snapshot et "
             "la chaîne `_canon_parts` de `make_light*`.\n")

    L.append("## ÉTAPE 1 — Cause-racine, par famille de cas résolus "
             "manuellement\n")
    L.append(
        "### a) Variantes orthographiques (AYRES↔AIRES, GAL↔GENERAL, "
        "CAPT↔CAPITAINE)\n"
        "`make_light*.py` normalise les tokens de la clé d'adresse via "
        "`_canon_parts` qui applique uniquement : (1) `VOIE` "
        "(type-de-voie `R`→`RUE`, `AV`→`AVENUE`, `BD`→`BOULEVARD`…), "
        "(2) `BIS` (`BIS`→`B`, `TER`→`T`), (3) `SAINTS` (`SAINT`→`ST`), "
        "(4) `ARTICLES` (`DE`/`DU`/`DES`/`LA`… strippés **en tête** du "
        "nom). **Aucune substitution sur les tokens internes du nom de "
        "voie** : `GAL` ≠ `GENERAL`, `CAPT` ≠ `CAPITAINE`, `AYRES` ≠ "
        "`AIRES` restent des tokens distincts → la jointure exacte "
        "`copro_by_cle.get(cle)` échoue → l'adresse chute au palier "
        "BDNB par num+voie ou GPS aveugle 50 m. **C'est par design** : "
        "ajouter une table `SUBS` à `_canon_parts` change la "
        "normalisation pour TOUT le pipeline (BDNB join, BAN, copro_by_cle, "
        "fusion bgid…) — risque réel de collisions de clés et de "
        "régression silencieuse. Convention établie (PIPELINE §4) = "
        "**ALIAS_RNC case-par-cas**, chirurgical.\n\n"
        "**Abréviations actuellement gérées** :\n"
        "| dict | contenu |\n|---|---|\n"
        "| `VOIE` (DL & MP, identique) | "
        "R/RUE, AV/AVE/AVENUE, BD/BLD/BOUL/BOULEVARD, CRS/COURS, "
        "IMP/IMPASSE, PL/PLACE, ALL/ALLEE, CHE/CH/CHEMIN, QU/QUAI, "
        "RTE/ROUTE, SQ/SQUARE, MTE/MONTEE, PAS/PASSAGE, GR (GRANDE "
        "RUE), TSSE/TERRASSE, VLA/VILLA |\n"
        "| `BIS` | B/BIS, T/TER, Q/QUATER, A/C/D |\n"
        "| `SAINTS` | SAINT→ST, SAINTE→STE, SAINTES→STES, SAINTS→STS |\n"
        "| `ARTICLES` (tête seulement) | DE, DES, DU, D, LA, LE, LES, "
        "L, AUX |\n\n"
        "**Abréviations / variantes attestées projet mais NON gérées** "
        "(corrigées au coup par coup via `ALIAS_RNC`) :\n"
        "| famille | exemples projet |\n|---|---|\n"
        "| militaires | `GAL`/`GEN`/`GENL` → GENERAL · `MAL` → MARECHAL "
        "· `CMDT`/`CDT` → COMMANDANT · `CAPT`/`CNE` → CAPITAINE · "
        "`LT`/`LIEUT` → LIEUTENANT · `COL` → COLONEL |\n"
        "| civils/religieux | `DR` → DOCTEUR · `PR`/`PROF` → "
        "PROFESSEUR · `PRES` → PRESIDENT · `MGR` → MONSEIGNEUR · "
        "`PCE` → PRINCE · `MNE` → MADELEINE · `FG` → FAUBOURG |\n"
        "| variantes ortho | `AYRES` ↔ `AIRES` (BUENOS) |\n")

    L.append(
        "### b) Adresses d'angle (Champfleury/Suffren, Gréard/Suffren, "
        "Gal Detrie/Charles Floquet)\n"
        "L'auto-fusion `make_light` par `batiment_groupe_id` "
        "(`make_light*.py` ~l.778-846) **regroupe** les adresses "
        "partageant le même bgid BDNB, **puis splite par parité du "
        "numéro de voirie** (pair vs impair) — *garde-fou* "
        "indispensable pour ne pas fusionner les deux côtés d'une voie "
        "(le bgid 1/3/5 ≠ bgid 2/4/6 dans 99 % des cas, mais quand "
        "BDNB groupe un corner sur un seul bgid on l'aurait à tort).\n\n"
        "Conséquence : pour un coin de rue (`6 Champfleury` PAIR + "
        "`45 Suffren` IMPAIR mais même bgid `PEQ4`), chacune se "
        "retrouve seule dans son seau parité → **groupe < 2 membres "
        "→ fusion sautée**. Ce n'est PAS un bug mais une décision de "
        "sécurité. Le tri du *principal* (l.812 : `cle ∈ copro_by_cle "
        "→ syndic → +ventes → adresse → cle`) garantit en revanche "
        "que quand la fusion par bgid s'applique, c'est bien la "
        "copro RNC qui devient le principal (cf. `28 RUE/PLACE "
        "DUPLEIX`, `38 CHARLES FLOQUET`). Reste les angles "
        "parité-mixte : **traitement manuel ALIAS_RNC obligé** "
        "(c'est la convention A2/A3 de `fix_mp_cibles_horsrnc.py`).\n\n"
        "Le cas `4 OCTAVE GREARD ↔ 15 SUFFREN` (AA1378777) est "
        "spécifique : **bgids BDNB différents** (ZWNL ≠ 9HGZ), donc "
        "ni groupe bgid ni fusion possible. Le nom de la copro RNC "
        "(`4 AVENUE OCTAVE GREARD`) ne porte pas le n° de son "
        "`adresse_reference` (15 Suffren) — seule la lecture humaine "
        "fait le lien. **Impossible à détecter automatiquement** sans "
        "indexer `nom_copropriete` (fragile, beaucoup de faux positifs).\n")

    L.append(
        "### c) Adresses fantômes DVF (Buenos Aires sans copro propre)\n"
        "DVF agrège la mutation cadastrale sous une clé `(No voie, "
        "B/T/Q, Type de voie, Voie)` reflétant le **libellé voie de la "
        "DGFiP** (fichier MAJIC), qui **diverge couramment** du libellé "
        "RNC : `BUENOS AIRES` (DVF) ↔ `BUENOS AYRES` (RNC) ; `CAPT "
        "SCOTT` (DVF) ↔ `CAPITAINE SCOTT` (RNC) ; `GAL DE CASTELNAU` "
        "(DVF) ↔ `GENERAL DE CASTELNAU` (RNC). Ce sont des **variantes "
        "de libellé**, pas des erreurs cadastrales : la DGFiP code la "
        "voie en interne (`Code voie`) et le libellé n'est que "
        "descriptif. Le pipeline pourrait croiser `Code voie` DGFiP "
        "↔ codes Insee/BAN, mais ça demande un référentiel de codes-voie "
        "par commune (non maintenu dans le projet). La convention "
        "actuelle = **détecter ces fantômes après coup** via l'audit "
        "hors-RNC (`scripts/audit_horsrnc_dvf.py`, "
        "`scripts/diag_orphelines_bdnb.py`) puis `ALIAS_RNC`.\n")

    L.append("## ÉTAPE 2 — Lacunes restantes (scan exhaustif des 2 "
             "secteurs)\n")
    L.append(f"Cibles hors-RNC actives scannées : "
             f"**DL {nt_dl}**, **MP {nt_mp}**. "
             f"Copros snapshot : DL {nc_dl}, MP {nc_mp}.\n")

    for label, P, idx in [
            ("P1 — abréviation de voie résolvable via extension SUBS",
             "P1", lambda r: r["P1"]),
            ("P2 — même `batiment_groupe_id` qu'une copro RNC, fusion "
             "auto manquée", "P2", lambda r: r["P2"]),
            ("P3 — orthographe RNC vs DVF (token-set ≥ 0.6, hors P1)",
             "P3", lambda r: r["P3"])]:
        sub = [r for r in rows if idx(r)]
        L.append(f"### {label}\n")
        L.append(f"**{len(sub)} cas** ({sum(r['vlog'] for r in sub)} "
                 f"ventes-logement).\n")
        if not sub:
            L.append("_Aucun cas restant._\n")
            continue
        if P == "P1":
            L.append("| secteur | cle hors-RNC | v_log | usage | "
                     "copro candidate | immat | lots | substitutions |")
            L.append("|---|---|--:|---|---|---|--:|---|")
            for r in sorted(sub, key=lambda x: (x["secteur"], -x["vlog"])):
                p = r["P1"]
                pairs = ", ".join(f"{a}↔{b}" for a, b in p["pairs"])
                L.append(
                    f"| {r['secteur'][:5]} | `{esc(r['cle'])}` | "
                    f"{r['vlog']} | {esc(r['usage'])} | "
                    f"`{esc(p['copro'])}` | {p['immat']} | {p['lots']} "
                    f"| {pairs} |")
        elif P == "P2":
            # Compte par sous-classe
            by_sub = collections.Counter(r["P2"]["sub"] for r in sub)
            L.append("**Sous-classes** : "
                     + ", ".join(f"{k}={v}" for k, v
                                 in sorted(by_sub.items())) + ".\n")
            L.append("| secteur | sub | cle hors-RNC | v_log | "
                     "copro candidate (même bgid) | immat | lots | "
                     "raison probable |")
            L.append("|---|---|---|--:|---|---|--:|---|")
            for r in sorted(sub, key=lambda x: (x["P2"]["sub"],
                                                x["secteur"],
                                                -x["vlog"])):
                p = r["P2"]
                L.append(
                    f"| {r['secteur'][:5]} | **{p['sub']}** | "
                    f"`{esc(r['cle'])}` | {r['vlog']} | "
                    f"`{esc(p['copro'])}` | {p['immat']} | {p['lots']} "
                    f"| {p['why']} |")
        else:
            L.append("| secteur | cle hors-RNC | v_log | "
                     "copro candidate (sim) | immat | lots |")
            L.append("|---|---|--:|---|---|--:|")
            for r in sorted(sub, key=lambda x: (x["secteur"], -x["vlog"])):
                p = r["P3"]
                L.append(
                    f"| {r['secteur'][:5]} | `{esc(r['cle'])}` | "
                    f"{r['vlog']} | `{esc(p['copro'])}` (sim "
                    f"{p['sim']}) | {p['immat']} | {p['lots']} |")
        L.append("")

    # Statistiques d'abreviations rencontrees dans les hr-actives
    abv = collections.Counter()
    for r in rows:
        n, nat, toks, canon = parse_cle(r["cle"])
        for t in toks:
            if t in SUBS:
                abv[t] += 1
    L.append("### Statistique — abréviations détectées dans les "
             "clés hors-RNC actives (toutes confondues)\n")
    if abv:
        L.append("| token | n |\n|---|--:|")
        for t, n in abv.most_common():
            L.append(f"| `{t}` → `{SUBS[t]}` | {n} |")
    else:
        L.append("_Aucune abréviation reconnue dans les clés "
                 "restantes._\n")
    L.append("")

    L.append("## ÉTAPE 3 — Recommandations\n")
    n_p1 = sum(1 for r in rows if r["P1"])
    n_p2 = sum(1 for r in rows if r["P2"])
    n_p3 = sum(1 for r in rows if r["P3"])
    p2_sub = collections.Counter(r["P2"]["sub"] for r in rows if r["P2"])
    p2_vlog = collections.Counter()
    for r in rows:
        if r["P2"]:
            p2_vlog[r["P2"]["sub"]] += r["vlog"]
    L.append(
        f"**Bilan résiduel** : P1 = {n_p1} cas, P2 = {n_p2} cas "
        + "(" + ", ".join(f"{k} {v} ({p2_vlog[k]} v_log)"
                          for k, v in sorted(p2_sub.items())) + ")"
        + f", P3 = {n_p3} cas (les ensembles peuvent se chevaucher).\n")
    L.append(
        "1. **Étendre la table SUBS de `make_light*` ?** "
        + ("**À ÉVITER en l'état.** " if n_p1 == 0 else
           f"**À étudier ciblé** ({n_p1} cas à gain immédiat). ")
        + "La normalisation `_canon_parts` impacte **tous** les "
        "consommateurs : `copro_by_cle` (jointure immat), "
        "`bdnb_par_voie` (jointure BDNB num+voie), tri de la principale "
        "fusion-bgid, label `_fusion_auto_label`. Une SUBS large risque "
        "de fusionner deux copros RNC distinctes ayant la même forme "
        "abrégée (collision `cle_adresse`). Si on l'introduit, "
        "le faire **token-par-token avec une whitelist courte** "
        "(GAL/GEN→GENERAL, CAPT/CNE→CAPITAINE, MAL→MARECHAL, "
        "AYRES→AIRES uniquement) **et** ajouter un test de "
        "régression : vérifier qu'aucune `cle_adresse` copro RNC ne "
        "collisionne après normalisation, sur les 2 secteurs (sinon "
        "ABORT). À défaut, **`ALIAS_RNC` reste la voie sûre** (déjà "
        "outillée par `fix_alias_rnc_meme_bgid.py` / "
        "`fix_mp_voie_abrev.py`).\n"
        "2. **Améliorer la détection des bgid partagés (P2) ?** "
        + ("**Inutile** (0 cas)." if n_p2 == 0 else f"""
   - **P2a — RE-POINT ({p2_sub.get('P2a', 0)} cas, {p2_vlog.get('P2a', 0)} v_log)** :
     **À CORRIGER en priorité** (même cause-racine que `38 Charles
     Floquet` / A3 `fix_mp_cibles_horsrnc`). La copro RNC ancrée est
     enterrée sous un fantôme DVF principal — la copro est *invisible*
     dans le rendu, le parc compte le bucket BDNB phantom (sous-comptage
     systématique vs lots RNC réels). Pattern : **re-point individuel**
     (fix dédié, dry-run, parc model). Source-of-truth = critère
     `copro_by_cle` du tri principal-fusion (déjà ajouté au runtime
     post-Dupleix : à regen sur ces 6 cas), mais en attendant la regen
     → correctif chirurgical.
   - **P2b — ORPHELIN bgid-fusion ({p2_sub.get('P2b', 0)} cas, {p2_vlog.get('P2b', 0)} v_log)** :
     src ET anchor tous deux *principals* sur même bgid+parité+voie —
     `auto-bgid-fusion` aurait dû les regrouper. Cause vraisemblable :
     **l'un des deux a été ajouté APRÈS la passe `make_light` par
     un correctif** (`fix_horsrnc_attribution` réintroduit des adresses
     hors-RNC manquantes, `fix_invisible_insecteur_bgids`…). L'auto-
     bgid-fusion ne s'exécute pas une seconde fois. **Solution générique** :
     ajouter une passe `propage_fusion_bgid_post_correctif` qui ré-applique
     l'algorithme l.778-846 de make_light sur le light patché (idempotente,
     respecte parité), OU correctif chirurgical pour chaque cas. À étudier.
   - **P2c — CORNER parité-mixte ({p2_sub.get('P2c', 0)} cas, {p2_vlog.get('P2c', 0)} v_log)** :
     **NE PAS toucher le garde-fou parité** (sécurité parc PIPELINE §9.3 —
     mesuré -514 DL / -423 MP en cas d'affaiblissement). Traiter chaque
     coin par ALIAS_RNC manuel après vérification GPS+bgid (miroir bgid
     dédup ou parc-neutre selon).
   - **P2d/e ({p2_sub.get('P2d', 0) + p2_sub.get('P2e', 0)} cas)** : ancre déjà
     fusionnée ailleurs, ou voie/nat divergent — instruire individuellement.
""") + "\n"
        "3. **Cas résiduels (P3 hors P1/P2)** : "
        + ("**0 cas.** " if n_p3 == 0 else
           f"{n_p3} cas — instruire individuellement (similarité "
           "token-set, peut être un faux positif sur homonyme de "
           "voie). Cf. méthodo "
           "[`audit-horsrnc-dvf`](../memory/audit-horsrnc-dvf.md) "
           "strong/weak. ") + "\n"
        "4. **Cas hors-pipeline (vraies monopropriétés / copros non "
        "immatriculées)** : structurellement rien à faire — "
        "documenter (catégorie B de `fix_mp_cibles_horsrnc.py`, "
        "tracer dans `data/diag_*.md`).\n")

    L.append("\n---\n*Audit lecture seule — "
             "`scripts/audit_lacunes_pipeline.py`. N'écrit que ce "
             "rapport.*")

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"DL: {nt_dl} hr-actives  MP: {nt_mp} hr-actives")
    print(f"P1={n_p1}  P2={n_p2}  P3={n_p3}")
    print(f"rapport: {REPORT.name}")


if __name__ == "__main__":
    main()
