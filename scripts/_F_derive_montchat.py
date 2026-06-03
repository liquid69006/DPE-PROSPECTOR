#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche F Montchat - DERIVATION READ-ONLY du candidat KV social/mixte (aucun POST).

Classe les 132 batiments a proprietaire bailleur HLM/public (pile F, differes par
la manche D via la garde social-precedence) en social / mixte / <20 selon la
convention DL.

CONVENTION DL (citee VERBATIM des sources) :
  social_pct (formule DL canon, _diag_social_combined_dvf_majic_dl.py l.135-146) :
    prop_habit          = rnc_habit / rnc_total
    hlm_habit_estim     = round(hlm_pm * prop_habit, 1)
    social_pct_corrige  = round(hlm_habit_estim * 100 / rnc_habit, 1)
    -> NUMERATEUR  = lots HLM/public PM (needles) ramenes en habitation
    -> DENOMINATEUR = rnc_habit = copro.nb_lots_habitation (RNC)
  Seuils (secteurs.json.metier.seuils) : social_pct_min=60, mut_apt_per_year_min=2
  Verdict (l.159-164) :
    FAUX_POSITIF : social_pct < 60  OU  mut/an >= 2
    SOCIAL       : social_pct >= 60 ET mut/an < 1
  Garde mut (PIPELINE.md root S6 Piege 1) : rotation >= 2 mut/an -> PAS social
                                            meme si social_pct >= 60.

>>> PROBLEME DE COUVERTURE (a documenter, pas a contourner) :
  Les 132 sont HORS-RNC (in_copro=False, has_immat=False) -> AUCUNE entree copro
  RNC -> rnc_habit=0 ET rnc_total=0 -> la formule DL social_pct_corrige renvoie
  None (N/A) pour LES 132. La convention DL ne definit PAS de denominateur de
  remplacement pour les hors-RNC. Ce script calcule donc DEUX proxys transparents
  (jamais arbitres comme "le" social_pct DL) :
    px_majic = hlm_pm * 100 / majic_lots   (= social_pct AVANT, _diag_social_pct
               _corrige_dl.py l.116, NON corrige habit ; numerateur/denom = lots PM)
    px_bdnb  = hlm_pm * 100 / nb_log_bdnb  (proxy parc, denom = logements BDNB)
  + part proprietaire bailleur en nb d'OWNERS (n_bailleur / n_owners_pm).
  AUCUN tag n'est pose sur la base d'un proxy non-canonique : ce script PRODUIT
  les chiffres pour arbitrage Yann, le candidat KV taggue selon la regle de
  RABATTEMENT explicitee ci-dessous (voir CHOICE), a valider.

Produit (AUCUNE ecriture KV, AUCUN commit) :
  data/_kv_assign_montchat.F.candidate.json
  data/diag_mancheF_montchat.md
ASCII-safe, PYTHONUTF8=1.
"""
import os
import sys
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from secteur_config import load_secteur  # noqa: E402

MAJIC = r"C:\Users\Station 5\majic_locaux2_2025.parquet"
PILE_F = ROOT / "data" / "_pile_social_F_montchat.json"
MIRROR = ROOT / "data" / "_kv_assign_montchat.json"
D_CAND = ROOT / "data" / "_kv_assign_montchat.D.candidate.json"
CANDIDATE = ROOT / "data" / "_kv_assign_montchat.F.candidate.json"
REPORT = ROOT / "data" / "diag_mancheF_montchat.md"

NON_PROPRIO = re.compile(r"SYNDIC|GERANT|MANDATAIRE|GESTIONNAIRE|USUFRUIT|NU.?PROPRI", re.I)


def main():
    cfg = load_secteur("montchat")
    light = json.loads(cfg.light.read_text(encoding="utf-8"))
    ad_by_cle = {a.get("cle") or "": a for a in light["adresses"]}
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in light["coproprietes"]}
    enr = json.loads(cfg.enrich_majic.read_text(encoding="utf-8"))
    enr_by_cle = {r["cle"]: r for r in enr.get("results", [])}

    pile = json.loads(PILE_F.read_text(encoding="utf-8"))
    F_cles = [c["cle"] for c in pile["cles"]]

    NEEDLES = tuple(n.upper() for n in (tuple(cfg.hlm_needles) + tuple(cfg.public_non_hlm)))

    def is_bailleur(den):
        d = str(den or "").upper()
        return any(n in d for n in NEEDLES)

    # ---- recompte proprietaires PM par parcelle (filtre syndic) - identique D ----
    import pyarrow.parquet as pq
    tbl = pq.read_table(MAJIC, filters=[("departement", "=", cfg.dep),
                                        ("code_commune", "in", cfg.code_commune)])
    df = tbl.to_pandas()
    pref = cfg.pref_by_commune()
    # owners_by_parc[key] = { siren: lots } (filtre syndic) ; bailleur_lots/owners ----
    owner_lots = defaultdict(lambda: defaultdict(int))     # parc -> siren -> lots
    owner_den = {}                                         # siren -> denomination
    for cc, sec, plan, sir, droit, den in zip(
            df["code_commune"], df["section"], df["numero_parcelle"],
            df["numero_siren"], df["code_droit_libelle"], df["denomination"]):
        try:
            key = f"{pref[str(cc)]}{sec}{str(int(plan)).zfill(4)}"
        except Exception:
            continue
        if sir is None:
            continue
        if droit and NON_PROPRIO.search(str(droit)):
            continue
        owner_lots[key][sir] += 1   # 1 ligne parquet = 1 local detenu
        if sir not in owner_den:
            owner_den[sir] = den

    # ---- DVF : mutations Apt+Maison distinctes par parcelle (garde mut/an) ----
    dvf = json.loads(Path(cfg.dvf_path).read_text(encoding="utf-8"))
    dvf_by_parc = defaultdict(list)
    for m in dvf:
        sec = m.get("Section") or ""
        plan = m.get("No plan") or ""
        if not sec or not plan:
            continue
        plan_norm = plan.lstrip("0") or "0"
        if str(m.get("Code type local") or "").strip() in ("1", "2"):
            dvf_by_parc[(sec, plan_norm)].append(m)

    def parc_to_dvf_key(parc):
        return (parc[8:10], parc[10:].lstrip("0") or "0")

    def mut_distinctes(parcs):
        seen = set()
        for parc in parcs:
            for m in dvf_by_parc.get(parc_to_dvf_key(parc), []):
                seen.add((m.get("Date mutation"), m.get("No disposition"),
                          m.get("Valeur fonciere")))
        return len(seen)

    # ---- classer les 132 ----
    rows = []
    for cle in F_cles:
        e = enr_by_cle.get(cle, {})
        a = ad_by_cle.get(cle, {})
        parcs = e.get("parcelles_bdnb") or []
        p0 = parcs[0] if parcs else None
        lots_map = owner_lots.get(p0, {}) if p0 else {}
        majic_lots = sum(lots_map.values())
        n_owners = len(lots_map)
        bailleur_sirens = [s for s in lots_map if is_bailleur(owner_den.get(s))]
        hlm_pm = sum(lots_map[s] for s in bailleur_sirens)
        n_bailleur = len(bailleur_sirens)
        nb_log = a.get("nb_log_bdnb")
        vlog = a.get("nb_ventes_logement") or 0

        # convention DL social_pct_corrige : hors-RNC -> rnc_habit=0 -> N/A
        cp = co_by_cle.get(cle, {})
        rnc_habit = cp.get("nb_lots_habitation") or 0
        social_pct_dl = None  # hors-RNC : indefini par construction

        # proxys transparents (NON canoniques)
        px_majic = round(hlm_pm * 100 / majic_lots, 1) if majic_lots else None
        px_bdnb = round(hlm_pm * 100 / nb_log, 1) if nb_log else None
        owner_share = round(n_bailleur * 100 / n_owners, 1) if n_owners else None

        # garde mut (DVF)
        mut5 = mut_distinctes(parcs)
        mut_an = round(mut5 / 5, 2)

        # top bailleur denom
        top_bail = None
        if bailleur_sirens:
            top = max(bailleur_sirens, key=lambda s: lots_map[s])
            top_bail = owner_den.get(top)

        rows.append({
            "cle": cle, "nb_log": nb_log, "vlog": vlog,
            "majic_lots": majic_lots, "n_owners": n_owners,
            "n_bailleur": n_bailleur, "hlm_pm": hlm_pm,
            "owner_share": owner_share, "px_majic": px_majic, "px_bdnb": px_bdnb,
            "social_pct_dl": social_pct_dl, "rnc_habit": rnc_habit,
            "mut5": mut5, "mut_an": mut_an, "top_bail": top_bail,
            "parc": p0, "status": e.get("status"),
        })

    # ===================================================================
    # REGLE DE TAGGING (CHOICE explicite -- a valider par Yann)
    # ===================================================================
    # La convention DL n'a PAS de social_pct hors-RNC. Pour NE PAS taguer a
    # l'aveugle, la regle de rabattement appliquee ici est :
    #
    #   social  <=> owner_share == 100 (TOUS les proprietaires PM sont bailleurs)
    #               ET mut_an < 2 (garde rotation, PIPELINE S6 Piege 1)
    #   mixte   <=> 0 < owner_share < 100  (bailleur + prive copropriete)
    #               ET mut_an < 2
    #   <20 / garde-mut : owner_share < 20 OU mut_an >= 2 -> NON tagge en
    #               manche F (renvoye en arbitrage : surtout prive / rotation).
    #
    # Rationale : hors-RNC, px_majic/px_bdnb sont biaises (MAJIC PM-only voit
    # surtout les bailleurs ; px_bdnb gonfle si parcelle multi-batis). La part
    # d'OWNERS bailleurs est le signal le moins biaise dont on dispose. Le seuil
    # social_pct_min=60 reste cite mais n'est pas applicable faute de denom RNC.
    # Cette regle est CONSERVATRICE (un seul prive sur la parcelle -> mixte, pas
    # social) et alignee sur l'esprit DL (social_pct sur lots HABITATION).
    SOC, MIX, LOW = [], [], []
    new_tags = {}
    for r in rows:
        osh = r["owner_share"]
        mut_block = r["mut_an"] >= 2.0
        if osh is None:
            LOW.append((r, "no_owner_pm"))         # 0 PM -> arbitrage
        elif mut_block:
            LOW.append((r, "mut>=2"))              # garde rotation
        elif osh < 20:
            LOW.append((r, "owner_share<20"))      # surtout prive
        elif osh >= 100:
            new_tags[r["cle"]] = "social"
            SOC.append(r)
        else:
            new_tags[r["cle"]] = "mixte"
            MIX.append(r)

    # ---- candidat = D candidate (381) + tags F ; PAS de modif des 381 ----
    d_cand = json.loads(D_CAND.read_text(encoding="utf-8"))
    base_assign = dict(d_cand.get("assignments", {}) or {})
    n_base = len(base_assign)
    cand_assign = dict(base_assign)
    inter_with_D = []
    for cle, t in new_tags.items():
        if cle in base_assign:
            inter_with_D.append((cle, base_assign[cle].get("type"), t))
        cand_assign[cle] = {"type": t}
    candidate = {
        "assignments": cand_assign,
        "fusions": d_cand.get("fusions", {}) or {},
        "noms": d_cand.get("noms", {}) or {},
    }
    CANDIDATE.write_text(json.dumps(candidate, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    # ---- effet LIVE (social -> getEffectiveLog=0) ----
    sum_log_social = sum((r["nb_log"] or 0) for r in SOC)
    sum_vlog_social = sum((r["vlog"] or 0) for r in SOC)
    sum_log_mixte = sum((r["nb_log"] or 0) for r in MIX)
    sum_vlog_mixte = sum((r["vlog"] or 0) for r in MIX)

    # ===================== IMPRESSION =====================
    print("=" * 70)
    print("MANCHE F MONTCHAT - DERIVATION (DRY-RUN, aucun POST)")
    print("=" * 70)
    print("  pile F (a classer)          :", len(F_cles))
    print("  needles bailleur (HLM+pub)  :", len(NEEDLES))
    print("\n-- CONVENTION DL social_pct --")
    print("  formule canon : HLM_habit_estim*100/rnc_habit (rnc_habit=copro.nb_lots_habitation)")
    print("  HORS-RNC -> rnc_habit=0 -> social_pct_dl = N/A pour les 132 (couverture absente)")
    print("  proxys produits : px_majic=hlm_pm/majic_lots ; px_bdnb=hlm_pm/nb_log_bdnb ; owner_share")
    n_dl_na = sum(1 for r in rows if r["social_pct_dl"] is None)
    print("  social_pct_dl=N/A :", n_dl_na, "/", len(rows))
    print("\n-- DISTRIBUTION (regle rabattement owner_share, voir entete CHOICE) --")
    print("  social (owner_share=100, mut<2):", len(SOC))
    print("  mixte  (0<owner_share<100, mut<2):", len(MIX))
    print("  LOW/garde (<20 | mut>=2 | 0PM)  :", len(LOW))
    print("    dont owner_share<20 :", sum(1 for _, why in LOW if why == "owner_share<20"))
    print("    dont mut>=2         :", sum(1 for _, why in LOW if why == "mut>=2"))
    print("    dont 0 PM           :", sum(1 for _, why in LOW if why == "no_owner_pm"))
    print("\n-- INTERSECTION F vs D (doit etre VIDE) --")
    print("  intersection :", len(inter_with_D))
    for c in inter_with_D:
        print("    [!!]", c)
    print("\n-- DIFF KV --")
    print("  base (D candidate)  :", n_base)
    print("  candidat F (complet):", len(cand_assign))
    print("  ajouts F            :", len(cand_assign) - n_base,
          "(", len(SOC), "social +", len(MIX), "mixte )")
    print("\n-- EFFET LIVE (a documenter, NON applique) --")
    print("  social: parc live retire =", sum_log_social,
          "logements ; marche-libre live retire =", sum_vlog_social, "ventes")
    print("  mixte : nb_log =", sum_log_mixte, "; ventes =", sum_vlog_mixte,
          "(effet selon regle mixte UI, a verifier index.html)")

    print("\n-- LISTE LOW / arbitrage (%d) --" % len(LOW))
    for r, why in sorted(LOW, key=lambda x: -(x[0]["nb_log"] or 0)):
        print("   %-32s osh=%-6s pxM=%-6s pxB=%-6s nlog=%-5s vlog=%-3s mut/an=%-5s why=%s top=%s"
              % (r["cle"], r["owner_share"], r["px_majic"], r["px_bdnb"],
                 r["nb_log"], r["vlog"], r["mut_an"], why, str(r["top_bail"])[:30]))

    write_report(rows, SOC, MIX, LOW, new_tags, base_assign, cand_assign,
                 inter_with_D, n_dl_na, sum_log_social, sum_vlog_social,
                 sum_log_mixte, sum_vlog_mixte, len(NEEDLES))
    print("\n  candidat ecrit ->", CANDIDATE.name, "(", len(cand_assign), "entrees, PAS POSTe)")
    print("  rapport ecrit  ->", REPORT.name)
    print("=" * 70)
    print("  STOP. Aucun POST, aucun commit.")


def write_report(rows, SOC, MIX, LOW, new_tags, base_assign, cand_assign,
                 inter_with_D, n_dl_na, slog_s, svlog_s, slog_m, svlog_m, n_needles):
    n_base = len(base_assign)
    n_add = len(cand_assign) - n_base
    L = []
    A = L.append
    A("# Diag MANCHE F Montchat (Phase 5, classif social/mixte des 132 bailleurs)\n")
    A("> DRY-RUN READ-ONLY. PYTHONUTF8=1, ASCII-safe. **AUCUNE ecriture KV, AUCUN "
      "POST, AUCUN commit / git add.** Date : 2026-06-03.\n")
    A("> Namespace KV : `secteur_assignments:dauphine-lacassagne-montchat`. "
      "Light, DL/MP, index.html NON touches.\n")
    A("\n---\n")

    A("\n## VOLET 1 - Convention F de DL (citee verbatim)\n")
    A("\n### Formule `social_pct` (source : `scripts/_diag_social_combined_dvf_majic_dl.py` l.135-146)\n")
    A("\n```python\n"
      "if rnc_habit > 0 and rnc_total > 0:\n"
      "    prop_habit = rnc_habit / rnc_total\n"
      "    hlm_habit_estim = round(hlm_pm * prop_habit, 1)\n"
      "    social_pct_corrige = round(hlm_habit_estim * 100 / rnc_habit, 1)\n"
      "elif rnc_habit > 0:\n"
      "    social_pct_corrige = round(hlm_pm * 100 / rnc_habit, 1)\n"
      "else:\n"
      "    social_pct_corrige = None\n"
      "```\n")
    A("\n- **Numerateur** = `hlm_habit_estim` = lots PM detenus par un proprietaire "
      "**bailleur** (denomination matchant un needle `metier.hlm_needles` + "
      "`metier.public_non_hlm`, MAJUSCULE, substring), ramenes en habitation via "
      "`prop_habit`. La detection bailleur (`is_hlm_denom`) couvre les memes "
      "needles que le filtre manche D.\n")
    A("- **Denominateur** = `rnc_habit` = `copropriete.nb_lots_habitation` (RNC). "
      "**PAS** `nb_log_bdnb**, PAS le total MAJIC.\n")
    A("- **Source des comptes PM** : `_enrich_majic_*_full.json` (`sirens[].lots`), "
      "soit le parquet `majic_locaux2_2025.parquet` joint **par parcelle BDNB** "
      "(LOCAUX2 PM-only). Le filtre syndic/gerant/usufruit/nu-proprietaire est "
      "applique au recompte (regex `SYNDIC|GERANT|MANDATAIRE|GESTIONNAIRE|"
      "USUFRUIT|NU.?PROPRI`).\n")
    A("\n### Seuils (source : `data/secteurs.json` -> `montchat.metier.seuils`, "
      "identiques a DL)\n")
    A("\n- `social_pct_min` = **60** ; `mut_apt_per_year_min` = **2**.\n")
    A("- **Verdict** (`_diag_social_combined_dvf_majic_dl.py` l.159-164) :\n"
      "  - `FAUX_POSITIF` : `social_pct < 60` **OU** `mut/an >= 2`\n"
      "  - `SOCIAL`       : `social_pct >= 60` **ET** `mut/an < 1`\n"
      "  - `INCERTAIN`    : sinon\n")
    A("- **Reclassement** (l.166-177) : `FAUX_POSITIF` + immat RNC -> `mixte` ; "
      "`FAUX_POSITIF` sans immat -> `copro_non_immat` ; `SOCIAL` -> garder social.\n")
    A("\n> **Le seuil 20-60 -> mixte du brief n'apparait PAS tel quel dans le code DL.** "
      "Le code DL ne connait que `>=60 social` / `<60 faux-positif`. La bascule "
      "`mixte` n'y est PAS pilotee par une tranche `20-60` de social_pct, mais par "
      "la **presence d'un immat RNC** sur un faux-positif. **La tranche `20-60 -> "
      "mixte` et le cas `<20` du brief ne sont donc PAS une convention DL ecrite** "
      "(deduction du brief, non preuve code).\n")
    A("\n### Piege social `mut_apt_per_year_min` (source : `PIPELINE.md` root S6 "
      "Piege 1, l.153-168)\n")
    A("\n> *\"`social_pct` est surevalue : MAJIC LOCAUX 2 n'expose pas les "
      "proprietaires personnes physiques (RGPD) [...]. Antidote : croiser avec DVF. "
      "Si `mut/an >= 2` sur l'adresse exacte -> ne pas tagger social, meme si "
      "`social_pct >= 60 %`.\"* Cas de reference : 28 ETIENNE RICHERAND (98,4 % "
      "social MAJIC mais 6,2 mut/an -> copro privee).\n")
    A("- **OUI, le garde mut est applique** ci-dessous : tout batiment a `mut/an >= 2` "
      "est SORTI du tag social (range en LOW/arbitrage), conformement a DL.\n")

    A("\n### >>> COUVERTURE : le cas hors-RNC N'EST PAS couvert par la convention DL\n")
    A("\nLes 132 batiments F sont **hors-RNC** (`in_copro=False`, `has_immat=False`) : "
      "par construction ils n'ont **aucune entree copro RNC**, donc "
      "`nb_lots_habitation = 0` -> la formule DL `social_pct_corrige` renvoie "
      "**None (N/A) pour LES 132** (`social_pct_dl=N/A : %d/%d`). **La convention DL "
      "ne definit aucun denominateur de remplacement pour les hors-RNC.** Le pipeline "
      "social DL (`_diag_social_*_dl.py`) ne s'applique qu'aux cles DEJA taggees "
      "social qui SONT des copros RNC (avec `nb_lots_habitation`).\n" % (n_dl_na, len(rows)))
    A("\n**Consequence (conforme a la consigne du brief : ne pas taguer a l'aveugle "
      "si la convention ne couvre pas)** : ce diag NE PEUT PAS calculer le "
      "`social_pct` DL canon sur ces 132. Il produit a la place deux proxys "
      "**transparents et non-canoniques**, et applique une regle de rabattement "
      "conservatrice (VOLET 2) qu'il faut **valider par Yann** :\n")
    A("\n- `px_majic` = `hlm_pm * 100 / majic_lots` (= `social_pct AVANT` non corrige, "
      "`_diag_social_pct_corrige_dl.py` l.116 ; biaise a la HAUSSE car LOCAUX2 = PM-only).\n")
    A("- `px_bdnb`  = `hlm_pm * 100 / nb_log_bdnb` (proxy parc ; biaise si parcelle multi-batis).\n")
    A("- `owner_share` = `n_owners_bailleurs * 100 / n_owners_PM` (signal le moins biaise).\n")

    A("\n## VOLET 2 - Regle de rabattement appliquee (CHOICE, a valider)\n")
    A("\nFaute de `social_pct` DL canon, le tag repose sur **`owner_share`** (part "
      "d'OWNERS PM bailleurs) + garde mut DVF :\n")
    A("\n| Condition | Tag |\n|---|---|\n")
    A("| `owner_share == 100` ET `mut/an < 2` | **social** |\n")
    A("| `0 < owner_share < 100` ET `mut/an < 2` | **mixte** |\n")
    A("| `owner_share < 20` **OU** `mut/an >= 2` **OU** 0 PM | **NON tagge** (arbitrage) |\n")
    A("\n> Regle CONSERVATRICE : un seul coproprietaire prive sur la parcelle -> "
      "`mixte`, pas social. Le seuil `social_pct_min=60` est cite mais inapplicable "
      "(pas de denom RNC). **A valider** : si Yann prefere un seuil sur `px_bdnb` ou "
      "`px_majic`, la distribution changera.\n")

    A("\n## VOLET 3 - Distribution\n")
    A("\n| Classe | n |\n|---|--:|\n")
    A("| social (owner_share=100, mut<2) | %d |\n" % len(SOC))
    A("| mixte (0<owner_share<100, mut<2) | %d |\n" % len(MIX))
    A("| NON tagge (LOW : <20 / mut>=2 / 0PM) | %d |\n" % len(LOW))
    A("| **TOTAL** | **%d** |\n" % len(rows))
    n_low20 = sum(1 for _, why in LOW if why == "owner_share<20")
    n_lowmut = sum(1 for _, why in LOW if why == "mut>=2")
    n_low0 = sum(1 for _, why in LOW if why == "no_owner_pm")
    A("\nDecomposition LOW : `owner_share<20` = **%d** ; `mut/an>=2` (garde rotation) "
      "= **%d** ; `0 PM` (parcelle sans lot PM apres filtre syndic) = **%d**.\n"
      % (n_low20, n_lowmut, n_low0))

    A("\n### Liste des <20%% / NON tagges (cas sensible : pousses en F mais surtout prives)\n")
    A("\n| cle | owner_share | px_majic | px_bdnb | nb_log | vlog | mut/an | raison | top bailleur |\n"
      "|---|--:|--:|--:|--:|--:|--:|---|---|\n")
    for r, why in sorted(LOW, key=lambda x: -(x[0]["nb_log"] or 0)):
        A("| %s | %s | %s | %s | %s | %s | %s | %s | %s |\n"
          % (r["cle"], r["owner_share"], r["px_majic"], r["px_bdnb"], r["nb_log"],
             r["vlog"], r["mut_an"], why, str(r["top_bail"] or "-")[:34]))

    A("\n### Liste mixte (%d)\n" % len(MIX))
    A("\n| cle | owner_share | n_owners | hlm_pm | nb_log | vlog | mut/an | top bailleur |\n"
      "|---|--:|--:|--:|--:|--:|--:|---|\n")
    for r in sorted(MIX, key=lambda x: -(x["nb_log"] or 0)):
        A("| %s | %s | %s | %s | %s | %s | %s | %s |\n"
          % (r["cle"], r["owner_share"], r["n_owners"], r["hlm_pm"], r["nb_log"],
             r["vlog"], r["mut_an"], str(r["top_bail"] or "-")[:34]))

    A("\n### Liste social (top 30 par nb_log)\n")
    A("\n| cle | n_owners | majic_lots | nb_log | vlog | mut/an | top bailleur |\n"
      "|---|--:|--:|--:|--:|--:|---|\n")
    for r in sorted(SOC, key=lambda x: -(x["nb_log"] or 0))[:30]:
        A("| %s | %s | %s | %s | %s | %s | %s |\n"
          % (r["cle"], r["n_owners"], r["majic_lots"], r["nb_log"], r["vlog"],
             r["mut_an"], str(r["top_bail"] or "-")[:34]))
    if len(SOC) > 30:
        A("\n... +%d autres social.\n" % (len(SOC) - 30))

    A("\n## Candidat KV + diff\n")
    A("\n- Base = `_kv_assign_montchat.D.candidate.json` (**%d** = 103 B2a + 278 D), "
      "PRESERVEE a l'identique.\n" % n_base)
    A("- Candidat F = `data/_kv_assign_montchat.F.candidate.json` (**%d** entrees).\n"
      % len(cand_assign))
    A("\n| | assignments |\n|---|--:|\n")
    A("| base D (381) | %d |\n" % n_base)
    A("| candidat F (POST complet) | %d |\n" % len(cand_assign))
    A("\n**Diff = +%d ajouts (%d social + %d mixte), 0 modif, 0 retrait.** "
      "KV %d -> %d.\n" % (n_add, len(SOC), len(MIX), n_base, len(cand_assign)))
    A("\n**Intersection des cles F (taggees) avec les tags D (mono/copro) = %d** %s "
      "(les 132 F etaient EXCLUS de D par la garde social-precedence ; les tags F "
      "n'ecrasent donc aucun mono/copro D). B2a 103 + D 278 preserves a l'identique.\n"
      % (len(inter_with_D), "VIDE OK" if not inter_with_D else "ANOMALIE !!"))
    if inter_with_D:
        for cle, dt, ft in inter_with_D:
            A("- [ANOMALIE] `%s` D=%s F=%s\n" % (cle, dt, ft))

    A("\n## Neutralite parc LIGHT\n")
    A("\nLes tags `as.type` sont **KV-only** : le light n'est PAS touche. Le parc "
      "`secL` calcule par `renderSecteur` sur le light brut reste **15 848** "
      "(tags hors light) ; Sigma ventes **932**. test_render exit 0 (DL + montchat "
      "+ MP) - voir section run.\n")

    A("\n## Effet LIVE attendu (a documenter, NON applique)\n")
    A("\nUn tag **social** -> `getEffectiveLog = 0` cote index.html (LIVE) -> le parc "
      "LIVE **et** le marche-libre LIVE baissent (ventes des social exclues du "
      "marche-libre).\n")
    A("\n| Effet LIVE | logements retires | ventes retirees |\n|---|--:|--:|\n")
    A("| social (%d) | **%d** | **%d** |\n" % (len(SOC), slog_s, svlog_s))
    A("| mixte (%d) - pour info | %d | %d |\n" % (len(MIX), slog_m, svlog_m))
    A("\n> Le parc LIVE diminue de **%d logements** (Sigma nb_log_bdnb des social) et "
      "le marche-libre LIVE de **%d ventes** (Sigma nb_ventes_logement des social). "
      "L'effet mixte depend de la regle UI mixte (a verifier index.html, hors-scope "
      "ici).\n" % (slog_s, svlog_s))

    A("\n## Scripts anti-drift + commande POST (NE PAS POSTER)\n")
    A("\n- `scripts/_F_backup_diff_montchat.py` (calque `_D_backup_diff`, "
      "ALLOWED_NEW_TYPES = {social, mixte}).\n")
    A("- `scripts/_F_post_montchat.py` (calque `_D_post`, GET==backup -> POST -> "
      "re-GET verify -> miroir).\n")
    A("\n```powershell\n. scripts\\load_jwt.ps1\n"
      "python scripts\\_F_backup_diff_montchat.py\n"
      "python scripts\\_F_post_montchat.py\n```\n")
    A("\n*Aucun POST, aucun commit dans cette manche (DRY-RUN).*\n")

    REPORT.write_text("".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
