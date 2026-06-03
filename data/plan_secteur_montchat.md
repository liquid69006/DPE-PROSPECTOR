# PLAN — Déploiement Secteur Prospector sur MONTCHAT (agence bufferné)

> **À l'attention de Claude Code.** Ce document est la spec du chantier. On
> l'exécute **phase par phase**, dans l'ordre. À chaque 🚦 GATE : **STOP**, on
> présente le résultat à Yann, on attend sa validation avant de continuer. On ne
> commit jamais sans feu vert, on ne push jamais sans feu vert explicite.
> Sauvegarder ce fichier en `data/plan_secteur_montchat.md` au démarrage.

## Objectif
Monter le **Secteur Prospector complet sur Montchat** dans la session bufferné,
avec un **toggle secteur DL ↔ secteur Montchat** dans le header. Qualité visée :
**identique à DL**. Particularité : Montchat est **îloté à la main** par le KML
fourni (134 îlots), qui **remplace la couche IRIS** comme unité d'organisation
de l'arbre (l'IRIS reste utilisé pour les stats Filosofi/INSEE).

## Discipline (rappel CLAUDE.md / PIPELINE.md — non négociable)
- **Explore read-only AVANT toute modif** (Phase 0). Pour chaque chantier non
  trivial : cartographier → plan → validation → seulement ensuite coder.
- **Additif sur la prod** : jamais de régénération destructive sur des données
  vivantes ; correctifs chirurgicaux. (PIPELINE §3)
- **Rituel anti-drift KV** pour toute écriture KV :
  `backup_diff → GET prod == backup → POST → re-GET verify → mirror → commit`.
- **Namespace Montchat SÉPARÉ de DL** (KV et fichiers).
- `PYTHONUTF8=1`, **prints ASCII-safe** (pas d'accents/emoji dans les sorties
  console — cp1252).
- **`test_render_secteur.js` exit 0 sur DL *et* Montchat** avant tout commit qui
  touche le front.
- **Subagent decomposition** pour les grosses phases.
- Commit → verify → push **sur approbation explicite uniquement**.

## Gates où Yann intervient (le « minimum d'intervention »)
1. 🚦 G0 — valider le rapport d'Explore (et l'ajustement des phases).
2. 🚦 G1 — valider les extraits sources Montchat (volumes, emprise).
3. 🚦 G2 — valider le 1er light Montchat (structure, comptes, îlots peuplés).
4. 🚦 G3 — valider le toggle (UI).
5. 🚦 G4..n — valider les arbitrages de qualification (domaine — itératif).
6. 🚦 GP — autoriser chaque push.
Entre les gates, Claude Code exécute seul.

---

## PHASE 0 — EXPLORE (read-only, cartographie de la chaîne Secteur)
**But** : tout savoir avant de coder, surtout l'origine des données sources.
Rapport → `data/diag_secteur_montchat.md`. NE RIEN MODIFIER. STOP à la fin.

- **E1 — Données sources (LE point gating).** Qui génère
  `secteur_dauphine_lacassagne.json` (copros RNC) et
  `dvf_dauphine_lacassagne.json` (ventes) ? Script de scoping national →
  périmètre (lequel ; entrées : RNC national, DVF data.gouv, commune INSEE,
  polygone) ou entrées externes sans script ? → **Montchat = re-run d'un script
  sur le périmètre, ou procurement manuel ?**
- **E2 — Pipeline par-zone.** Lire `make_light.py` (DL) **et**
  `make_light_motte_picquet.py` (MP) : codé en dur DL vs paramétré (chemins,
  commune INSEE, périmètre, IRIS) ? Ce que MP fait différemment (= patron
  d'ajout de zone). Inputs/outputs exacts de chacun.
- **E3 — Couche îlots.** Dans make_light DL : où se fait l'attribution IRIS
  (`code_iris`, WFS) et la construction de l'arbre IRIS>îlot>adresse ? Où
  brancher les 134 îlots KML (un `code_ilot` point-in-polygon) **en gardant**
  `code_iris` pour Filosofi/INSEE ?
- **E4 — Sorties par-zone.** Fichiers + clés KV produits par Secteur par zone
  (light JSON DL : nom/chemin ; KV `_arbitres_*`, `_cles_invalides_*`,
  `_kv_assign_*`, `_kv_repartition_*` : patron de nommage). Lister les clés KV
  Secteur DL **exactes**.
- **E5 — Front Secteur.** Comment Secteur charge une zone (`secteurResolve`
  agence→[fichier,id,nom,ville], `#secteur-titre`) ? Multi-AGENCE seulement, ou
  déjà multi-ZONE-dans-une-agence (`AGENCES_CONFIG.zones` utilisé par Secteur) ?
  Où/comment insérer un toggle DL/Montchat intra-agence bufferné ?
- **E6 — État MP.** MP Secteur : fait / en cours / amorcé ? Sert-il de template
  complet pour Montchat ?

**🚦 G0** — Yann valide le rapport. **On ajuste les phases 1-7 ci-dessous selon
E1/E2/E4/E5 avant de continuer.** STOP.

---

## PHASE 1 — DONNÉES SOURCES MONTCHAT
**Conditionnel au résultat de E1.**

- **Si un script de scoping existe** (national → périmètre) : le relancer sur le
  **périmètre Montchat** (le polygone de zone du json + commune(s) INSEE — ⚠️
  vérifier si Montchat déborde sur le 8e/69388 en plus du 3e/69383) pour
  produire `secteur_montchat.json` (copros RNC) et `dvf_montchat.json` (ventes).
- **Sinon (procurement)** : lister précisément à Yann ce qu'il doit fournir
  (DVF de la/les commune(s) filtré au périmètre, export RNC), avec la méthode.
  C'est le seul endroit où une action data de Yann peut être requise.
- BDNB : via l'API (national, fonctionne pour Montchat — pas d'extrait préalable).
- **Vérifs** : nb copros, nb mutations DVF, emprise GPS cohérente avec la bbox
  KML (lon 4.8698→4.8983, lat 45.7404→45.7549).

**🚦 G1** — Yann valide volumes + emprise. STOP.

---

## PHASE 2 — `make_light_montchat.py` + 1er LIGHT
**Créer** `make_light_montchat.py`, calqué sur `make_light.py` (DL) et le patron
MP (E2). Subagent decomposition recommandée.

- **Paramétrage Montchat** : chemins des sources Montchat, commune(s) INSEE,
  polygone de membership (du json), sorties Montchat.
- **Couche îlots KML (adaptation clé)** : charger `data/kml/Ilotage_Montchat.kml`
  → 134 polygones. Appliquer les 2 fixes : **plus petit îlot « 118 » → « 195 »**,
  **îlot « 162 » refermé**. Pour chaque adresse : `code_ilot` = point-in-polygon
  contre les 134 îlots ; orphelin (sur rue/bord, géocodage) → îlot le plus proche
  dans **~25 m**, sinon `ilot=null` + signalement. **Garder `code_iris`** (pour
  Filosofi/INSEE). L'arbre devient **îlot(KML)>adresse**.
- **Reste du pipeline identique à DL** : comptage DVF (dédup par mutation),
  copros slim (lots RNC prioritaires sur BDNB pour le dénominateur), passe B/T/Q,
  fusion par bgid/nomgrp avec garde `l_libelle_adr`, etc.
- Committer le KML dans `data/kml/Ilotage_Montchat.kml`.
- Lancer → produire le **light Montchat** (nom/chemin selon E4, ex.
  `data/<...>-montchat-secteur.json` ou équivalent).
- **Vérifs structurelles** : tous les îlots peuplés (distribution adresses/îlot),
  nb orphelins acceptable, copros/ventes/parc cohérents, JSON valide.

**🚦 G2** — Yann valide le 1er light (structure, comptes, îlots). STOP.

---

## PHASE 3 — NAMESPACE KV MONTCHAT (séparé de DL)
- Créer les clés KV Secteur Montchat, **suffixe distinct** (ex. `_montchat` ou
  `_mtc`) : `_arbitres_montchat.json`, `_cles_invalides_montchat.json`,
  `_kv_assign_montchat`, `_kv_repartition_montchat` (patron exact selon E4).
- Initialiser **vides** (pas de données DL à migrer ; Montchat part de zéro).
- Toute écriture KV → **rituel anti-drift**. Comme on initialise des clés
  neuves, le risque est faible, mais on applique le rituel (backup, GET, POST,
  re-GET).

**🚦 G3-KV** — Yann autorise l'init KV (léger). STOP.

---

## PHASE 4 — FRONT : TOGGLE SECTEUR DL ↔ MONTCHAT (bufferné)
- Ajouter dans Secteur Prospector un **toggle 2-états** (Dauphiné-Lacassagne |
  Montchat), visible en session bufferné, intra-agence (selon E5 :
  `AGENCES_CONFIG.zones` ou un sélecteur zone dédié).
- Le toggle pilote `secteurResolve`/le chargement de zone : charge le **light**
  de la zone active + le **namespace KV** de la zone active, met à jour
  `#secteur-titre` et les compteurs.
- **`test_render_secteur.js` exit 0 sur DL ET Montchat** (étendre le test à
  Montchat).
- Pas de régression sur DPE/SCI/Secteur-DL.

**🚦 G3** — Yann valide l'UI du toggle. STOP.

---

## PHASE 5 — QUALIFICATION MONTCHAT (playbook DL réutilisé) — *itératif*
On amène Montchat au niveau « propre comme DL », en rejouant la méthodologie
documentée (manches DL, CLAUDE.md/JOURNAL). C'est la phase qui demande l'œil
métier de Yann, mais le playbook existe → rapide. Procéder par **manches**, une
🚦 GATE par manche :

1. **Cartographie des piles** : compter orange / rouge / indéterminés sur
   Montchat (état initial).
2. **Verdict-scope gate** (`_arbitres_montchat.json`) pour `bgid_confirmed` /
   `live_indetermine`.
3. **Deny-list** (`_cles_invalides_montchat.json`) pour les clés malformées.
4. **Reclassification MAJIC/BDNB** des `cible_0vente_*` (logique `copro_non_immat`
   via BDNB + règle angle-mort MAJIC LOCAUX2 RGPD : `nb_log_bdnb>1` + pas
   d'immat RNC + 0 PM = `copro_non_immat`).
5. **Classification** : règles social_pct (≥60 social / 20-60 mixte / SIREN privé
   ≥80 mono) ; faux positifs syndics (FONCIA, SAGNIMORTE, REGIE *, LYMMOBILIER,
   PIRON GESTION) → vérifier `code_droit`.
6. **Matching adresses** en couches : clé canonique → fallback RNC coords null →
   re-géocodage BAN → fusion bgid avec filtre parité (pairs/impairs).
7. **Marché-libre** : repère strict unique (≥1 lot habitation, hors social/
   bureaux, jugé par tag d'ancre, fusion-aware) — comme DL.
8. **Objectif** : piles orange/rouge à **0**.

**🚦 G5.x** — Yann valide les arbitrages de chaque manche (domaine). STOP entre
manches.

---

## PHASE 6 — VÉRIF + DÉPLOIEMENT
- `test_render_secteur.js` exit 0 sur DL **et** Montchat.
- Smoke-check : toggle, chargement zones, KV par zone, pas d'erreur console,
  Dauphiné inchangé.
- Commit `feat(secteur): deploiement Montchat (ilotage KML + toggle + KV separe)`.
- **🚦 GP** — Yann autorise le push → Cloudflare Pages redéploie.

---

## PHASE 7 — DOCUMENTATION (CLAUDE.md + PIPELINE.md + JOURNAL.md)
- **CLAUDE.md** : ajouter Montchat aux zones Secteur déployées (bufferné = DL +
  Montchat) ; documenter le toggle ; la couche **îlots KML vs IRIS** ; le
  namespace KV Montchat ; le patron `make_light_montchat.py`.
- **PIPELINE.md** : nouvelle section « Pipeline Montchat » — scoping des sources,
  attribution `code_ilot` (KML) vs `code_iris` (stats), fixes KML (118→195, 162),
  sorties/KV par zone, règle orphelins ~25 m.
- **JOURNAL.md** : entrée datée du build (comptes, îlots, gotchas, commits).
- Commit `docs: Montchat (claude.md + pipeline + journal)`.
- **🚦 GP** — Yann autorise le push.

---

## Conventions transverses (rappel)
- ASCII-safe + `PYTHONUTF8=1` partout.
- Gotcha coords si `secteurs.json` touché : `[lon,lat]` côté Python / `[lat,lon]`
  côté `secteurs.json` ; KML en `lon,lat,alt`.
- Immats/lots hérités via bgid = display-only (le parc lit `coproByCle`).
- Badge implicite « Copropriété » = RNC immat **sans tag KV** → laisser
  `as.type` vide pour les copros immatriculées.
- Anti-drift KV idempotent (re-run POST sûr).
- Aucune dé-fusion d'impasses de l'Ordre (sur-comptage lots).

## Ce que Claude Code NE fait pas sans Yann
- Pas de push sans feu vert (chaque GP).
- Pas d'écriture KV sans rituel anti-drift + validation.
- Pas de procurement de données externes (Phase 1, branche procurement) — c'est
  Yann qui fournit si pas de script.
- Pas d'arbitrage métier en Phase 5 sans validation (G5.x).
