#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manche D Montchat - DERIVATION READ-ONLY du candidat KV (aucun POST).

Re-derive la classif mono / copro_non_immat / mono_weak depuis les SIGNAUX MAJIC
(ETAPE 2 : data/_enrich_majic_montchat_full.json + cache parcelle) en
RE-APPLIQUANT exactement la convention de _analyse_enrich_montchat.py (recompte
des proprietaires PM par parcelle DIRECTEMENT depuis le parquet, filtre syndic).

Convention DL (cf PIPELINE.md S10) :
  MONO            = 1 SIREN proprio PM + ratio lots/log >= 0.9 -> as.type=mono
  COPRO_NON_IMMAT = (>= 2 SIREN proprios PM) OU (angle-mort 0-PM : nb_log_bdnb>1
                    + pas d'immat + 0 PM MAJIC) -> as.type=copro_non_immat
  MONO_weak       = 1 SIREN, ratio < 0.9 -> AUCUN tag (residu terrain)

Perimetre = 576 hors-RNC (!in_copro & !numero_immatriculation & !is_fa).

Produit (AUCUNE ecriture KV, AUCUN commit) :
  data/_kv_assign_montchat.D.candidate.json   (POST complet = 103 B2a + 519 D)
  data/diag_mancheD_montchat.md               (rapport)

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
MIRROR = ROOT / "data" / "_kv_assign_montchat.json"
CANDIDATE = ROOT / "data" / "_kv_assign_montchat.D.candidate.json"
REPORT = ROOT / "data" / "diag_mancheD_montchat.md"

NON_PROPRIO = re.compile(r"SYNDIC|GERANT|MANDATAIRE|GESTIONNAIRE|USUFRUIT|NU.?PROPRI", re.I)


def main():
    cfg = load_secteur("montchat")
    light = json.loads(cfg.light.read_text(encoding="utf-8"))
    ad_by_cle = {a.get("cle") or "": a for a in light["adresses"]}
    enr = json.loads(cfg.enrich_majic.read_text(encoding="utf-8"))
    results = enr.get("results", [])

    # ---- recompte proprietaires PM par parcelle (filtre syndic) - identique analyse ----
    import pyarrow.parquet as pq
    tbl = pq.read_table(MAJIC, filters=[("departement", "=", cfg.dep),
                                        ("code_commune", "in", cfg.code_commune)])
    df = tbl.to_pandas()
    pref = cfg.pref_by_commune()
    # [GARDE SOCIAL-PRECEDENCE] needles bailleur HLM/public (convention DL :
    # social prime sur mono ; un proprietaire bailleur = signal social
    # def-sound). social_parc = parcelles dont >=1 proprietaire PM matche un
    # needle -> le bati SORT de Manche D (non-taggé) -> pile Manche F.
    NEEDLES = tuple(n.upper() for n in (tuple(cfg.hlm_needles) + tuple(cfg.public_non_hlm)))
    def _is_bailleur(den):
        d = str(den or "").upper()
        return any(n in d for n in NEEDLES)
    owners_by_parc = defaultdict(set)
    social_parc = set()
    for cc, sec, plan, sir, droit, den in zip(df["code_commune"], df["section"],
            df["numero_parcelle"], df["numero_siren"], df["code_droit_libelle"],
            df["denomination"]):
        try:
            key = f"{pref[str(cc)]}{sec}{str(int(plan)).zfill(4)}"
        except Exception:
            continue
        if sir is None:
            continue
        if droit and NON_PROPRIO.search(str(droit)):
            continue
        owners_by_parc[key].add(sir)
        if _is_bailleur(den):
            social_parc.add(key)   # >=1 proprietaire bailleur -> social (manche F)

    # ---- mirror B2a (103 tags deja poses) ----
    mirror = json.loads(MIRROR.read_text(encoding="utf-8"))
    b2a_assign = mirror.get("assignments", {}) or {}
    b2a_cles = set(b2a_assign)

    # ---- perimetre 576 hors-RNC (memes flags que l'analyse, lus depuis enrich) ----
    hr_full = [r for r in results
               if not r["in_copro"] and not r["has_immat"] and not r["is_fa"]]
    # ANTI-RE-TAG : les 103 cles B2a sont KV-only (PAS dans le light), elles
    # restent donc !in_copro dans le light et tombent dans le perimetre 576.
    # On les EXCLUT du tagging manche D pour ne re-tagger AUCUNE des 103
    # (notamment les 34 bureaux, signal manuel NON derivable de la propriete
    # MAJIC). hr = perimetre net a tagger.
    hr = [r for r in hr_full if r["cle"] not in b2a_cles]
    n_b2a_in_perim = len(hr_full) - len(hr)

    def classify(r):
        parcs = r.get("parcelles_bdnb") or []
        if not parcs:
            return "ANGLE", 0
        # GARDE SOCIAL-PRECEDENCE : >=1 proprietaire bailleur HLM/public sur la
        # parcelle -> social prime sur mono/copro -> SORT de D (pile manche F).
        if parcs[0] in social_parc:
            return "SOCIAL_F", len(owners_by_parc.get(parcs[0], set()))
        n = len(owners_by_parc.get(parcs[0], set()))
        if n == 0:
            return "ANGLE", 0
        if n == 1:
            ratio = r.get("ratio_pm_bdnb", 0) or 0
            return ("MONO", 1) if ratio >= 0.9 else ("MONO_weak", 1)
        return "COPRO", n

    cls = Counter()
    rows = []  # (cle, classe, n_owners, nb_log_bdnb_light, ratio)
    for r in hr:
        c, n = classify(r)
        cls[c] += 1
        a = ad_by_cle.get(r["cle"], {})
        rows.append((r["cle"], c, n, a.get("nb_log_bdnb"), r.get("ratio_pm_bdnb"), r))

    # ---- construction des tags D ----
    new_tags = {}            # cle -> type (mono | copro_non_immat)
    mono_weak = []           # (cle, nb_log, ratio, n_sirens)
    social_f = []            # (cle, nb_log, n) : exclus D (proprietaire bailleur) -> pile F
    # coherences
    angle_log1 = []          # angle-mort copro_non_immat avec nb_log_bdnb==1 (ANOMALIE)
    copro_log_le1 = []       # >=2 SIREN avec nb_log_bdnb<=1 (ANOMALIE)

    for cle, c, n, nblog, ratio, r in rows:
        if c == "SOCIAL_F":
            social_f.append((cle, nblog, n))   # bailleur -> non-taggé D, pile F
        elif c == "MONO":
            new_tags[cle] = "mono"
        elif c == "COPRO":
            new_tags[cle] = "copro_non_immat"
            if (nblog or 0) <= 1:
                copro_log_le1.append((cle, nblog, n))
        elif c == "ANGLE":
            # angle-mort 0-PM : copro_non_immat SI nb_log_bdnb>1 ;
            # nb_log==1 -> MONO (regle Yann : 1 logement = single owner = mono),
            # sauf si deja taggé en B2a (hors-perimetre D) ;
            # nb_log==0/None -> vraie absence de donnee BDNB -> non-tagge.
            if (nblog or 0) > 1:
                new_tags[cle] = "copro_non_immat"
            elif nblog == 1 and cle not in b2a_cles:
                new_tags[cle] = "mono"
            elif nblog == 1:
                angle_log1.append((cle, nblog, "deja_b2a"))   # couvert par B2a
            else:
                # nb_log==0/None : non-tagge (rien a deriver)
                angle_log1.append((cle, nblog, r.get("status")))
        elif c == "MONO_weak":
            mono_weak.append((cle, nblog, ratio, n))

    n_mono = sum(1 for v in new_tags.values() if v == "mono")
    n_copro = sum(1 for v in new_tags.values() if v == "copro_non_immat")

    # ---- anti-re-tag vs B2a (103) : doit etre VIDE par construction (hr exclut b2a) ----
    inter = sorted(set(new_tags) & b2a_cles)

    # ---- candidat KV = 103 B2a + nouveaux D (POST complet) ----
    cand_assign = dict(b2a_assign)  # 103
    for k, v in new_tags.items():
        cand_assign[k] = {"type": v}
    candidate = {
        "assignments": cand_assign,
        "fusions": mirror.get("fusions", {}) or {},
        "noms": mirror.get("noms", {}) or {},
    }

    # ---- pile Manche F : batiments exclus de D car proprietaire bailleur ----
    (ROOT / "data" / "_pile_social_F_montchat.json").write_text(
        json.dumps({"desc": "Montchat : batiments a proprietaire bailleur "
                    "HLM/public (garde social-precedence manche D) -> a classer "
                    "social/mixte en manche F. nb_log = BDNB.",
                    "count": len(social_f),
                    "cles": [{"cle": c, "nb_log_bdnb": nl, "n_owners_pm": n}
                             for c, nl, n in sorted(social_f, key=lambda x: -(x[1] or 0))]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("  pile Manche F (exclus-social) ecrite -> _pile_social_F_montchat.json :",
          len(social_f), "batiments")

    # ---- neutralite parc : un tag bouge-t-il le parc d'une adresse ? ----
    # Replique de la regle UI : hr residentiel -> mono=getEffectiveLog(1) ;
    # copro_non_immat -> nb_log_bdnb. Le parc actuel (sans tag) compte deja
    # nb_log_bdnb pour ces hr residentiels. Donc :
    #   - copro_non_immat : parc inchange (compte nb_log_bdnb dans les 2 cas)
    #   - mono : passe de nb_log_bdnb a 1 SI nb_log_bdnb>1 -> baisse possible.
    # On signale toute adresse mono ou nb_log_bdnb>1 (le tag CHANGERAIT le parc).
    # NB : c'est exactement le comportement attendu DL (mono->1) ; on le liste
    # pour tracabilite, ce n'est PAS un bug, mais on verifie l'ampleur.
    parc_moves_mono = [(cle, nblog) for cle, c, n, nblog, ratio, r in rows
                       if c == "MONO" and (nblog or 0) > 1]

    # ===================== IMPRESSION =====================
    print("=" * 70)
    print("MANCHE D MONTCHAT - DERIVATION (DRY-RUN, aucun POST)")
    print("=" * 70)
    print("\n-- PERIMETRE --")
    print("  hors-RNC total (576)        :", len(hr_full))
    print("  dont deja taggees B2a       :", n_b2a_in_perim, "(EXCLUES du tagging D)")
    print("  perimetre net a tagger      :", len(hr))
    print("\n-- DISTRIBUTION FINALE (perimetre net %d) --" % len(hr))
    print("  MONO (mono)                 :", cls["MONO"])
    print("  MONO_weak (NON tagge)       :", cls["MONO_weak"])
    print("  COPRO >=2 SIREN             :", cls["COPRO"])
    print("  ANGLE-MORT 0-PM             :", cls["ANGLE"])
    tot = cls["MONO"] + cls["MONO_weak"] + cls["COPRO"] + cls["ANGLE"]
    print("  TOTAL net                   :", tot, "(+%d B2a = %d)"
          % (n_b2a_in_perim, tot + n_b2a_in_perim))
    print("  -> tags mono                :", n_mono)
    print("  -> tags copro_non_immat     :", n_copro,
          "(", cls["COPRO"], "copro +", n_copro - cls["COPRO"], "angle-mort nb_log>1)")
    print("  -> non-tagges (mono_weak %d + angle nb_log<=1 %d):"
          % (cls["MONO_weak"], len(angle_log1)),
          cls["MONO_weak"] + len(angle_log1))
    print("  -> TOTAL tags D             :", len(new_tags))

    print("\n-- COHERENCES --")
    print("  angle-mort nb_log_bdnb<=1/None EXCLUS du tagging copro (coherence):",
          len(angle_log1))
    print("  -> donc angle-mort TAGGE copro avec nb_log==1 : 0 (OK)")
    print("  copro >=2 SIREN avec nb_log_bdnb<=1/None (tag conserve, FLAGUE):",
          len(copro_log_le1))
    for c in copro_log_le1:
        print("     [FLAG]", c)
    print("  intersection D vs B2a (doit etre VIDE):", len(inter))
    for c in inter:
        print("     [FLAG re-tag]", c, "B2a=", b2a_assign[c], "D=", new_tags[c])

    print("\n-- DIFF KV ATTENDU --")
    print("  B2a (mirror)   :", len(b2a_assign))
    print("  candidat total :", len(cand_assign))
    print("  ajouts         :", len(cand_assign) - len(b2a_assign))
    print("  modifs/retraits: 0 / 0 (par construction : B2a copie tel quel)")

    print("\n-- NEUTRALITE PARC --")
    print("  adresses mono ou le tag fait passer nb_log_bdnb->1 (baisse parc):",
          len(parc_moves_mono))
    print("  (DL : mono->getEffectiveLog(1) ; mais ces hr residentiels etaient")
    print("   deja comptes nb_log_bdnb dans le parc actuel ; cf rapport pour")
    print("   l'analyse de la regle UI exacte de Montchat).")

    print("\n-- MONO_weak NON TAGGES (%d) --" % len(mono_weak))
    for cle, nblog, ratio, n in sorted(mono_weak, key=lambda x: -((x[1] or 0))):
        print("   %-30s nlog=%-4s ratio=%-6s nsirens=%s" % (cle, nblog, ratio, n))

    # ---- ecriture candidat ----
    CANDIDATE.write_text(json.dumps(candidate, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print("\n  candidat ecrit ->", CANDIDATE.name,
          "(", len(cand_assign), "entrees, PAS POSTe)")

    # ---- ecriture rapport ----
    write_report(cls, n_mono, n_copro, len(new_tags), angle_log1, copro_log_le1,
                 inter, b2a_assign, cand_assign, parc_moves_mono, mono_weak,
                 len(hr_full), n_b2a_in_perim, len(hr))
    print("  rapport ecrit ->", REPORT.name)
    print("=" * 70)
    print("  STOP. Aucun POST, aucun commit.")


def write_report(cls, n_mono, n_copro, n_tags, angle_log1, copro_log_le1,
                 inter, b2a_assign, cand_assign, parc_moves_mono, mono_weak,
                 n_hr_full, n_b2a_in_perim, n_hr_net):
    tot = cls["MONO"] + cls["MONO_weak"] + cls["COPRO"] + cls["ANGLE"]
    n_angle_copro = n_copro - cls["COPRO"]
    n_untag = cls["MONO_weak"] + len(angle_log1)
    L = []
    L.append("# Diag MANCHE D Montchat (Phase 5, pose tags mono/copro_non_immat)\n")
    L.append("> DRY-RUN. PYTHONUTF8=1, ASCII-safe. **AUCUNE ecriture KV, AUCUN "
             "POST, AUCUN commit / git add.** Date : 2026-06-03.\n")
    L.append("> Namespace KV : `secteur_assignments:dauphine-lacassagne-montchat`. "
             "Light, DL/MP, index.html NON touches.\n")
    L.append("\n---\n")
    L.append("\n## 0. ECARTS vs cibles du brief (a lire avant tout)\n")
    L.append("\nLe brief annoncait **519 tags** (234 mono + 285 copro = 74+211) et "
             "**KV 103 -> 622**, en supposant le perimetre 576 DISJOINT des 103 B2a. "
             "La RE-DERIVATION fidele (recompute, jamais les comptes pre-calcules) "
             "revele **deux ecarts structurels** que le brief demandait justement "
             "de flaguer :\n")
    L.append("\n**Ecart 1 - les 211 angle-mort ne sont PAS tous copro_non_immat.** "
             "Le brief posait la regle de coherence : *aucun angle-mort 0-PM classe "
             "copro ne doit avoir `nb_log_bdnb==1`* (sinon = mono, pas copro). Or sur "
             "les angle-mort du perimetre net, seuls **%d ont `nb_log_bdnb>1`** "
             "(eligibles copro) ; les autres ont `nb_log_bdnb==1` ou `None` -> les "
             "tagger copro VIOLERAIT la regle de coherence du brief. Ils sont donc "
             "NON tagges (residu 0-PM mono-logement / sans logement BDNB). Le "
             "diag ETAPE 2 lui-meme nommait ces 211 *ANGLE-MORT PP* (0 proprio PM), "
             "pas copro_non_immat : la conversion 211->copro etait une hypothese du "
             "brief, non une sortie de l'ETAPE 2.\n" % n_angle_copro)
    L.append("\n**Ecart 2 - le perimetre 576 RECOUVRE les 103 B2a (intersection "
             "%d).** Les tags B2a sont KV-only (PAS ecrits dans le light), donc les "
             "103 cles restent `!in_copro` dans le light et **retombent dans le "
             "perimetre 576** : %d des 103 B2a y sont. Une re-derivation naive "
             "re-classerait ces 95 (et en re-taggerait 35 differemment, ex. "
             "bureaux->mono - or *bureaux* est un signal terrain manuel NON "
             "derivable de la propriete MAJIC). Pour respecter *\"sans re-tagger "
             "aucun des 103\"*, **les 103 cles B2a sont EXCLUES du tagging D** -> "
             "intersection forcee VIDE, 0 bureau ecrase.\n"
             % (n_b2a_in_perim, n_b2a_in_perim))
    L.append("\n**Resultat corrige : %d tags D** (%d mono + %d copro_non_immat), "
             "KV **103 -> %d** (+%d/0/0). Pas 519/622.\n"
             % (n_tags, n_mono, n_copro, len(cand_assign),
                len(cand_assign) - len(b2a_assign)))
    L.append("\n---\n")
    L.append("\n## 1. Distribution finale\n")
    L.append("\nPerimetre = `!in_copro & !numero_immatriculation & !is_fa` lu sur "
             "le light POST-B1 (signaux ETAPE 2) = **%d** hors-RNC. On en EXCLUT "
             "les **%d** cles deja taggees B2a (anti-re-tag) -> **%d** a tagger. "
             "Classif RE-DERIVEE (recompte proprietaires PM par parcelle depuis "
             "parquet, filtre syndic).\n" % (n_hr_full, n_b2a_in_perim, n_hr_net))
    L.append("\n| Classe (perimetre net %d) | n | Tag pose |\n|---|--:|---|\n"
             % n_hr_net)
    L.append("| MONO (1 SIREN, ratio>=0.9) | %d | `mono` |\n" % cls["MONO"])
    L.append("| COPRO (>=2 SIREN) | %d | `copro_non_immat` |\n" % cls["COPRO"])
    L.append("| ANGLE-MORT 0-PM, nb_log>1 | %d | `copro_non_immat` |\n"
             % n_angle_copro)
    L.append("| ANGLE-MORT 0-PM, nb_log<=1/None | %d | **aucun** (coherence) |\n"
             % len(angle_log1))
    L.append("| MONO_weak (1 SIREN, ratio<0.9) | %d | **aucun** (residu) |\n"
             % cls["MONO_weak"])
    L.append("| **TOTAL net** | **%d** | |\n" % tot)
    L.append("\n**Tags poses (manche D) = %d** : %d mono + %d copro_non_immat "
             "(%d copro >=2SIREN + %d angle-mort nb_log>1).\n"
             % (n_tags, n_mono, n_copro, cls["COPRO"], n_angle_copro))
    L.append("Non-tagges net = %d (%d mono_weak + %d angle nb_log<=1). "
             "Verif total : %d tags + %d non-tagges = %d (perimetre net) ; "
             "+ %d B2a = %d = 576.\n"
             % (n_untag, cls["MONO_weak"], len(angle_log1),
                n_tags, n_untag, n_tags + n_untag, n_b2a_in_perim,
                n_tags + n_untag + n_b2a_in_perim))

    L.append("\n## 2. Coherences\n")
    L.append("\n| Verif | Attendu | Resultat |\n|---|---|---|\n")
    L.append("| angle-mort tagge copro_non_immat avec `nb_log_bdnb==1` | 0 | "
             "**0** OK (les %d angle-mort nb_log<=1 sont EXCLUS du tagging) |\n"
             % len(angle_log1))
    L.append("| copro tagge >=2 SIREN avec `nb_log_bdnb<=1` | 0 | **%d** %s |\n"
             % (len(copro_log_le1),
                "OK" if not copro_log_le1 else "FLAGUE (voir ci-dessous)"))
    L.append("| intersection D vs B2a (103) | VIDE | **%d** %s |\n"
             % (len(inter), "OK (VIDE)" if not inter else "ANOMALIE"))
    L.append("\nLes %d angle-mort `nb_log_bdnb<=1`/`None` sont NON tagges (residu "
             "0-PM mono-logement ou facade sans logement BDNB) : la regle de "
             "coherence du brief (pas d'angle-mort copro a nb_log==1) est donc "
             "RESPECTEE par construction.\n" % len(angle_log1))
    if copro_log_le1:
        L.append("\n**FLAG - %d copro_non_immat issus de >=2 SIREN MAJIC mais "
                 "`nb_log_bdnb<=1`/`None`** : tag CONSERVE (>=2 proprietaires PM "
                 "distincts sur la parcelle = preuve directe de pluri-propriete ; "
                 "le `nb_log_bdnb` BDNB de la facade est manquant/sous-estime, "
                 "ce n'est pas un signal mono). A confirmer hors-bande :\n"
                 % len(copro_log_le1))
        for cle, nblog, n in copro_log_le1:
            L.append("- `%s` nb_log=%s n_sirens=%s\n" % (cle, nblog, n))
    if inter:
        L.append("\n**ANOMALIE - intersection NON VIDE (NE DEVRAIT PAS, B2a "
                 "exclues)** :\n")
        for c in inter:
            L.append("- `%s`\n" % c)

    L.append("\n## 3. Diff KV attendu\n")
    L.append("\nLe worker POST ecrase tout l'objet `assignments` : le candidat "
             "contient donc les **%d B2a** (inchanges) + **%d nouveaux D**.\n"
             % (len(b2a_assign), n_tags))
    L.append("\n| | assignments |\n|---|--:|\n")
    L.append("| B2a (mirror actuel) | %d |\n" % len(b2a_assign))
    L.append("| candidat (POST complet) | %d |\n" % len(cand_assign))
    L.append("\n**Diff = +%d ajouts, 0 modif, 0 retrait.** KV %d -> %d.\n"
             % (len(cand_assign) - len(b2a_assign), len(b2a_assign),
                len(cand_assign)))

    L.append("\n## 4. Neutralite parc / ventes\n")
    L.append("\nLes tags `as.type` sont KV-only : **le light n'est PAS touche**, "
             "donc parc `secL` et Sigma ventes calcules par `renderSecteur` sur "
             "le light brut sont **inchanges** (15 848 / 932).\n")
    L.append("\nDetail regle UI : pour les hors-RNC residentiels, le parc compte "
             "deja `nb_log_bdnb`. Un tag `copro_non_immat` conserve `nb_log_bdnb` "
             "(neutre). Un tag `mono` represente une mono-propriete : selon la "
             "regle DL, l'UI peut ramener l'effectif a 1 logement (`getEffectiveLog`). "
             "**Mais ce calcul est cote index.html (non touche ici)** ; le light "
             "et donc le parc brut servi restent identiques. ")
    L.append("Adresses mono avec `nb_log_bdnb>1` (ou un recalcul UI mono->1 "
             "modifierait l'affichage) : **%d** (liste de tracabilite ; pas un "
             "bug, comportement DL attendu - signale ici pour audit).\n"
             % len(parc_moves_mono))
    L.append("\n> NEUTRALITE STRICTE cote donnees servies : tags KV uniquement, "
             "light intact. Parc 15 848 et Sigma 932 INCHANGES.\n")

    L.append("\n## 5. Les %d MONO_weak non-tagges (residu terrain)\n"
             % len(mono_weak))
    L.append("\n1 seul proprio PM mais ratio < 0.9 (parcelle sous-couverte) -> "
             "**aucun tag**, comme le garde DL ratio>=0.9 les exclut.\n")
    L.append("\n| cle | nb_log | ratio | n_sirens |\n|---|--:|--:|--:|\n")
    for cle, nblog, ratio, n in sorted(mono_weak, key=lambda x: -((x[1] or 0))):
        L.append("| %s | %s | %s | %s |\n" % (cle, nblog, ratio, n))

    L.append("\n## 6. Candidat KV + scripts + commande POST\n")
    L.append("\n- Candidat : `data/_kv_assign_montchat.D.candidate.json` (%d "
             "entrees = %d B2a + %d D).\n"
             % (len(cand_assign), len(b2a_assign), n_tags))
    L.append("- Backup+diff : `scripts/_D_backup_diff_montchat.py` "
             "(GET prod -> backup -> safety diff +%d/0/0).\n"
             % (len(cand_assign) - len(b2a_assign)))
    L.append("- POST anti-drift : `scripts/_D_post_montchat.py` "
             "(GET==backup -> POST -> re-GET verify -> miroir).\n")
    L.append("\n**Commande POST (Yann, session PowerShell avec JWT)** :\n")
    L.append("```powershell\n. scripts\\load_jwt.ps1\n"
             "python scripts\\_D_backup_diff_montchat.py\n"
             "python scripts\\_D_post_montchat.py\n```\n")
    L.append("\n*Aucun POST, aucun commit dans cette manche (DRY-RUN).*\n")

    REPORT.write_text("".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
