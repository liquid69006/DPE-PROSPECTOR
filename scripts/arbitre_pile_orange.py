#!/usr/bin/env python3
"""Arbitrage conversationnel de la pile orange - pilote par Claude Code.

Modele : Claude joue le pont. Pas d'input() bloquant (incompatible tool Bash).
  --next                         imprime le PROCHAIN cas non decide (template FR)
  --decide --cle X --choix C     enregistre une decision (C in 1|2|3|pass|creuser)
                                 [--raison "..."] optionnel
  --status                       progression X/total

"creuser" N'EST PAS final : le cas reste dans la file (Claude fait le check
demande puis --next le re-propose). Un cas est "decide" (skippe) seulement si
choix in {1,2,3,pass}. Reprise native apres interruption.

N'ecrit JAMAIS en KV : seulement data/_arbitrages_pile_orange_<short>.json
(les decisions deviendront des overrides / tags au jalon 4).

Usage : python scripts/arbitre_pile_orange.py --secteur <slug> --next
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from secteur_config import load_secteur, slugs

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FINAL = {"1", "2", "3", "pass"}
SIGNAL_FR = {
    "parite_opposee": "bâtiment partagé entre un numéro pair et un impair de "
                      "la même rue (improbable physiquement)",
    "faux_match_majic": "l'adresse n'apparaît pas parmi les propriétaires "
                        "recensés sur la parcelle de ce bâtiment",
    "bgid_absent_cache": "bâtiment introuvable dans le cache des parcelles",
}
SEP = "═" * 67


def _paths(cfg):
    return (cfg.light.parent / f"_pile_orange_{cfg.short}.json",
            cfg.light.parent / f"_arbitrages_pile_orange_{cfg.short}.json")


def load_a_arbitrer(cfg):
    p, _ = _paths(cfg)
    if not p.exists():
        sys.exit(f"  [abort] {p.name} absent - lance d'abord pipeline.py.")
    return json.loads(p.read_text(encoding="utf-8")).get("a_arbitrer", [])


def load_events(cfg):
    _, p = _paths(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def decided_cles(events):
    return {e["cle"] for e in events if e.get("decision") in FINAL}


# ---------- rendu des cas ----------
def _bloc(idx, total, cfg, case, contrainte, consequences, vu, options):
    L = [SEP, f"Cas {idx}/{total} — Pile orange {cfg.slug}", SEP, "",
         f"📍 {case['adresse']}", f"🔗 {case['maps']}", "",
         "❓ Contrainte rencontrée", contrainte, "",
         "Conséquences possibles :"]
    L += [f"- {c}" for c in consequences]
    L += ["", "📊 Ce que les outils ont vu"]
    L += [f"- {v}" for v in vu]
    L += ["", "📝 Tes options"]
    L += [f"[{n}] {txt}" for n, txt in options]
    L += ["[4] CREUSER : montre-moi autre chose avant que je décide", "",
          f"(cle = {case['cle']})", "Ta décision (1/2/3/4) ?", ">"]
    return "\n".join(L)


def render_case(idx, total, cfg, case):
    t = case["type"]
    d = case.get("data", {})
    kv = case.get("current_kv_tag")
    if t == "bgid_confirmed":
        vois = ", ".join(v.replace("|", " ") for v in
                         (d.get("bgid_group_voisins") or [])) or "un voisin"
        sigs = [SIGNAL_FR.get(s, s) for s in (d.get("signaux") or [])]
        bl = (d.get("bgid_light") or "").replace("bdnb-bg-", "")
        bb = (d.get("bgid_ban") or "").replace("bdnb-bg-", "")
        contrainte = (
            "Le pipeline ne sait pas si cette adresse est rattachée au bon "
            "immeuble. La source géographique du projet (make_light) l'a "
            f"placée dans le même bâtiment que {vois} (parité opposée), alors "
            "que la source officielle d'adressage (BAN) la place dans un "
            "bâtiment différent.")
        consequences = [
            "Si on corrige : logements et ventes comptés sur le bon immeuble, "
            "carte du secteur juste.",
            "Si on conserve : l'adresse reste sur un bâtiment probablement faux "
            "(logements mal attribués / double comptage)."]
        vu = [f"Signal : {' ; '.join(sigs)}",
              f"Voisin parité opposée : {vois}",
              f"BAN (autorité) → {bb} ; le light dit {bl}",
              f"Confiance : {d.get('score')}"
              + (" (cross-RNC confirmé)" if d.get("cross_rnc") else " (pas de copro RNC pour recouper)")]
        options = [
            ("1", "CORRIGER : rattacher au bâtiment indiqué par BAN"),
            ("2", "CONSERVER : garder le rattachement actuel — cas exceptionnel "
                  "(rare) où BAN se trompe, comme le 84B DAUPHINÉ déjà vu"),
            ("3", "VÉRIFIER TERRAIN : marquer pour contrôle avant de trancher")]
        return _bloc(idx, total, cfg, case, contrainte, consequences, vu, options)

    if t == "nom_ambigu":
        contrainte = (
            f"Un propriétaire de cette copropriété s'appelle « {d.get('denomination')} ». "
            "Le nom évoque du logement social, mais juridiquement c'est une "
            "personne morale de droit privé — PAS un bailleur social (HLM / "
            "office public). Le pipeline ne sait pas s'il faut sortir cette "
            "adresse de la prospection (social) ou la garder (copro privée).")
        consequences = [
            "Si non prospectable : l'adresse sort des cibles (traitée comme social).",
            "Si prospectable : l'adresse reste une cible (le propriétaire social-sonnant "
            "n'est que minoritaire)."]
        nb = d.get("nb_log_bdnb")
        vu = [f"Signal : libellé « {d.get('mot_declencheur')} » mais forme = "
              f"« {d.get('forme_juridique')} » (pas un bailleur HLM/OPH)",
              f"Lots détenus par ce propriétaire : {d.get('lots')} sur "
              f"{d.get('total_lots_pm')} lots de personnes morales "
              f"({d.get('pct_proprio')}%)"
              + (f" — immeuble ~{nb} logements" if nb else ""),
              f"Tag KV actuel : {kv or '(aucun)'}"]
        options = [
            ("1", f"PROSPECTABLE : copro classique, l'asso est un propriétaire "
                  f"parmi d'autres → CONFIRME le tag KV actuel ({kv or 'aucun'})"),
            ("2", "NON PROSPECTABLE : traiter comme du social / géré "
                  "→ REMPLACE le tag par a_arbitrer:social"),
            ("3", "VÉRIFIER : marquer pour contrôle")]
        return _bloc(idx, total, cfg, case, contrainte, consequences, vu, options)

    if t == "zone_grise_mixte":
        sp, mut = d.get("social_pct"), d.get("mut_an_exact")
        contrainte = (
            f"Cette adresse a un pourcentage social significatif ({sp}%) mais "
            f"sous le seuil habituel de {cfg.social_pct_min}%. Comme la rotation "
            f"des ventes est faible ({mut:.1f}/an), elle ne ressemble pas à une "
            "copro en décollectivisation. Le pipeline hésite entre la classer "
            "mixte (présence sociale notable) ou en copro privée standard.")
        consequences = [
            "Si mixte : présence sociale notée, l'adresse reste suivie comme telle.",
            "Si copro privée : classée standard, prospectable (le % social est subi)."]
        hlm = d.get("hlm_owners") or []
        if hlm:
            bail = "Bailleurs sociaux détectés : " + ", ".join(
                f"{h['denom']} ({h['lots']} lots)" for h in hlm)
        else:
            bail = ("Aucun bailleur HLM/OPH identifié — le % social vient de "
                    "plusieurs propriétaires diffus")
        vu = [f"social_pct = {sp}% (seuil social = {cfg.social_pct_min}%)",
              f"rotation ventes = {mut:.1f}/an (seuil = {cfg.mut_apt_per_year_min}/an)",
              bail]
        options = [("1", "MIXTE : présence sociale notable, classer mixte"),
                   ("2", "COPRO PRIVÉE : classer en standard prospectable (le % social est subi)"),
                   ("3", "VÉRIFIER : contrôle terrain")]
        return _bloc(idx, total, cfg, case, contrainte, consequences, vu, options)

    if t == "zone_grise_mono":
        tpp = d.get("top_prive_pct")
        contrainte = (
            f"Un seul propriétaire privé détient ~{tpp}% des lots — proche du "
            "seuil de mono-propriété (80%) sans l'atteindre. Le pipeline ne "
            "sait pas s'il faut la classer en mono-propriété.")
        consequences = [
            "Si mono : 1 seul logement compté (mono-propriétaire).",
            "Si copro classique : tous les lots comptés comme logements."]
        vu = [f"top propriétaire privé : {d.get('top_prive')}",
              f"part = {tpp}% des lots PM / {d.get('top_prive_pct_bdnb')}% du parc BDNB"]
        options = [("1", "MONO : mono-propriété (1 logement)"),
                   ("2", "COPRO CLASSIQUE : compter tous les lots"),
                   ("3", "VÉRIFIER : contrôle terrain")]
        return _bloc(idx, total, cfg, case, contrainte, consequences, vu, options)

    return f"[type inconnu: {t}] cle={case['cle']}"


# ---------- commandes ----------
def cmd_next(cfg):
    cases = load_a_arbitrer(cfg)
    done = decided_cles(load_events(cfg))
    total = len(cases)
    for i, case in enumerate(cases, 1):
        if case["cle"] not in done:
            print(render_case(i, total, cfg, case))
            return
    print(f"✅ Tous les {total} cas de la pile orange ont été arbitrés.")


def cmd_decide(cfg, cle, choix, raison):
    if choix not in FINAL | {"creuser"}:
        sys.exit(f"  [abort] choix invalide: {choix} (1|2|3|pass|creuser)")
    _, p = _paths(cfg)
    events = load_events(cfg)
    events.append({"cle": cle, "decision": choix,
                   "horodatage": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "raison_yann": raison or None})
    p.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    etat = "enregistre (FINAL)" if choix in FINAL else "note (creuser - cas garde dans la file)"
    print(f"  {etat} : {cle} -> {choix}" + (f"  [{raison}]" if raison else ""))


def cmd_preview(cfg, cle):
    """Apercu d'un cas par cle (lecture seule, ne touche PAS aux events)."""
    cases = load_a_arbitrer(cfg)
    for i, case in enumerate(cases, 1):
        if case["cle"] == cle:
            print(render_case(i, len(cases), cfg, case))
            print("\n[PREVIEW lecture seule — aucun event enregistré]")
            return
    sys.exit(f"  [preview] cle absente de a_arbitrer : {cle}")


def cmd_status(cfg):
    cases = load_a_arbitrer(cfg)
    events = load_events(cfg)
    done = decided_cles(events)
    from collections import Counter
    ct = Counter(e["decision"] for e in events if e.get("decision") in FINAL)
    n_creuser = sum(1 for e in events if e.get("decision") == "creuser")
    print(f"  Pile orange {cfg.slug} : {len(done)}/{len(cases)} arbitrés "
          f"({dict(ct)})  · {n_creuser} évènements 'creuser'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secteur", default="dauphine-lacassagne",
                        help="slug secteur (defaut: dauphine-lacassagne)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--next", action="store_true", help="prochain cas non decide")
    g.add_argument("--decide", action="store_true", help="enregistre une decision")
    g.add_argument("--status", action="store_true", help="progression")
    g.add_argument("--preview-cle", default=None, metavar="CLE",
                   help="apercu d'un cas par cle (lecture seule, ne touche pas aux events)")
    parser.add_argument("--cle", help="cle a decider (avec --decide)")
    parser.add_argument("--choix", help="1|2|3|pass|creuser (avec --decide)")
    parser.add_argument("--raison", default=None, help="precision Yann (optionnel)")
    args = parser.parse_args()
    cfg = load_secteur(args.secteur)

    if args.next:
        cmd_next(cfg)
    elif args.preview_cle:
        cmd_preview(cfg, args.preview_cle)
    elif args.status:
        cmd_status(cfg)
    elif args.decide:
        if not args.cle or not args.choix:
            sys.exit("  [abort] --decide requiert --cle et --choix")
        cmd_decide(cfg, args.cle, args.choix, args.raison)


if __name__ == "__main__":
    main()
