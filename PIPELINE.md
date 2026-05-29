# PIPELINE — Notes méthodologiques DPE-Prospector

Documentation des décisions structurantes du pipeline de génération
des données light (snapshot RNC + BDNB + DVF) et des règles de
correction terrain.

## §1. Architecture pipeline (résumé)

Le pipeline `make_light_<secteur>.py` (hors-repo, scripts locaux
utilisateur) génère `data/secteur_<secteur>_light.json` à partir de :

1. **Snapshot RNC** (registre national des copropriétés, archive
   data.gouv) → ancres `coproprietes[]` + attribution `numero_immatriculation`
2. **BDNB pivot** (`batiment_groupe_complet`, `rel_batiment_groupe_*`)
   → `batiment_groupe_id`, `nb_log_bdnb`, `usage_principal_bdnb`,
   `annee_construction`, etc. par GPS/BAN
3. **DVF brut** (mutations 2021-2025) → consolidation `ventes_par_an`,
   `ventes_par_an_logement`, `nb_ventes_*` par adresse
4. **MAJIC** (propriétaires fiscaux) → `dans_majic`, `sci_*`
5. **ALIAS_RNC** (mappings manuels) → fusions DVF→copro RNC, copros
   multi-voies, INJECT label-only

Le rendu UI (`index.html`) applique au runtime :
- consolidation parc (modèle Sec 6 : RNC autoritaire prioritaire,
  fallback BDNB résidentiel)
- `getEffectiveLog(a)` : `1` si qualification `mono` posée via menu UI,
  sinon `nb_log_bdnb` (commit `ee3185f`)
- qualifications utilisateur (KV Cloudflare : route
  `/secteur-assignments/{secteur_id}` du `worker.js`)

## §2. Patterns de correction terrain (catalogue)

Les corrections sont **manuelles, surgicales, validées terrain**
uniquement. Pas d'auto-fusion massive.

| Pattern | Description | Exemples |
|---|---|---|
| **Cambronne** (RE-POINT) | adresse orphelin → ancre RNC existante via re-fusion | fix_cambronne_belleuse, fix_perignon_saxe, fix_champaubert_6_village_suisse |
| **Suffren** (INJECT + ATTRIBUTION) | copro RNC live absente snapshot, injectée dans `coproprietes[]` + attribuée ancre existante | fix_suffren_barthelemy_garibaldi, fix_lowendal_suffren |
| **Disambig #immat** | 2 copros cohabitent même bati → cle suffixée `X|...|... #IMMAT` | fix_perignon_saxe (#AB8151755), fix_garibaldi_28_ah (#AH1602424) |
| **ÉTIQUETAGE label-only** (Clouet) | bati sans copro RNC, ajout `_fusion_auto_label` seul | fix_clouet_garibaldi_label, fix_violet_grenelle_label |
| **INJECT_LABEL_ONLY** | adresse BAN absente snapshot, injectée minimaliste fused vers ancre | fix_armonial_8cepre |
| **HYBRIDE Sisley** (3-en-1) | INJECT ancre + RE-POINT orphs + correction bgid | fix_parc_sisley, fix_chasseloup_suffren |
| **Détachement** (cleanup) | retrait d'adresses faussement rattachées à un grand ensemble | fix_armonial_pair_detach |
| **INVERSION_ANCRE_RNC** | inversion ancre/fused quand make_light a choisi par DVF/GPS au lieu de la `cle_adresse` RNC déclarée dans `coproprietes[]` | fix_federation_86_village_suffren |

Chaque correction génère un commit avec script `scripts/fix_*.py`,
backup `.preX.bak`, métadonnée `_correctif_X` dans le JSON light, et
ALIAS_RNC à porter dans `make_light_<secteur>.py` (hors-repo).

## §3. Mode correction chirurgicale uniquement

**Règle absolue** : aucune correction massive automatique.

Les pipelines forward + reverse pivot BDNB sont **saturés** depuis
2026-05-20 (forward 0/66 hr-actives + reverse 0/1330 copros).
Toute nouvelle correction passe par signalement terrain + audit
manuel + dry-run + validation + commit dédié.

### §3.1 Évaluations rejetées (trace pour ne pas y revenir)

#### Passe `bgid-orphelin` automatique (REJETÉE 2026-05-21)

**Hypothèse évaluée** : auto-fuser les adresses hors-RNC non-fusées
dont le `batiment_groupe_id` est déjà occupé par une ancre RNC active
ET dont le `syndic` (cadastre/RNC) match exactement le syndic ancre.

**Scan** : `scripts/scan_bgid_orphelin_mp.py` → 42 cas détectés sur
Motte-Picquet (41 bgids RNC partagés, 11 cas avec syndic match exact).

**Audit approfondi** des 11 cas "haute confiance" :
`scripts/audit_bgid_orphelin_safe11.py` (parcelles, distances entre
numéros, présence dans `l_libelle_adr` BDNB pivot, années).

**Conclusion** : la passe **a été évaluée et rejetée** — le `bgid`
BDNB seul + `syndic match` n'est **pas suffisant** pour garantir que
deux adresses pair/impair appartiennent au même bâtiment physique.

Exemples de faux positifs identifiés :
- **58 → 69 BD GRENELLE** (distance 11, pair vs impair = **côtés
  opposés du boulevard** physiquement distincts, même si bgid BDNB
  commun par défaut de géocodage).
- **4 → 7 RUE PRESLES** (distance 3, le 4 PRESLES absent du pivot
  `l_libelle_adr` qui liste 5/7/9/11 — probable bati distinct en face).

**Décision** : correction manuelle terrain uniquement. Pas
d'intégration de la passe dans `make_light_motte_picquet.py`.

Le seul cas validé manuellement (terrain user 2026-05-21) :
- **6 AVENUE DE CHAMPAUBERT → 78 AVENUE SUFFREN** (Village Suisse
  AA0529289) — confirmé par BDNB pivot (l_libelle_adr inclut le 6
  parmi 13 façades du bati 2HH6 parcelle DH/0022). Commit dédié.

Les 10 autres cas du scan restent **à traiter au cas par cas sur
signalement terrain uniquement**, comme tous les correctifs précédents.

Outils de réévaluation disponibles si signalement futur (lecture
seule) :
- `scripts/scan_bgid_orphelin_mp.py` — scan complet périmètre
- `scripts/audit_bgid_orphelin_safe11.py` — audit détaillé par cas
- `scripts/extract_horsrnc_sansvente_mp.py` — extraction hors-RNC sans
  logements/ventes pour qualification manuelle
- `scripts/extract_ventes_bloc_mp.py` — détection ventes bloc DVF

### §3.2 Critère final d'auto-rattachement (référence)

Pour qu'une adresse soit automatiquement rattachée à une ancre RNC
côté `make_light`, **trois conditions cumulatives** doivent être
réunies :
1. **ALIAS_RNC explicite** porté manuellement dans `make_light` après
   validation terrain
2. **OU** vente DVF directe à cette adresse qui matche l'immat
3. **OU** présence de l'adresse dans `l_libelle_adr` du bgid BDNB
   pivot **ET** syndic match (ce dernier critère n'est PAS encore
   implémenté pour éviter les faux positifs type 58→69 GRENELLE)

Tout autre cas reste **hors-RNC orphelin** jusqu'à signalement terrain.

## §4. Conventions

- **Backups** : chaque fix surgical produit un `.preX.bak` du light
- **Métadonnées** : chaque correctif écrit `metadata._correctif_X`
  dans le JSON light, avec texte explicatif complet (sources,
  parcelles, syndic, effet parc)
- **Commits** : un commit par correctif, message structuré
  `[SECTEUR]: fix X (immat SYNDIC N lots, pattern Y)`
- **Push** : sur validation utilisateur seulement (workflow "commit
  sans push, attendre feu vert")
- **Mémoire** : chaque pattern majeur ou décision méthodologique est
  également documentée dans `memory/` (slug-kebab.md) avec lien index
  dans `MEMORY.md`

## §5. Principe directeur — les overrides sont des entrées sacrées

⚠️ **Les overrides (`data/_social_overrides_*.json`) sont des ENTRÉES
du pipeline, JAMAIS des sorties recalculées.**

Ils encodent des arbitrages terrain humains (validés par Yann) qui
priment sur tout calcul automatique. Aucun outil du pipeline ne doit
les régénérer, les écraser ou les « corriger » : il les LIT et les
applique par-dessus le résultat auto. Toute exécution qui modifierait
un override est un bug à corriger, pas un résultat à committer.

Corollaire : la reproductibilité (cf. §7, étape 5) se mesure sur
`résultat auto + overrides appliqués`, jamais sur le seul calcul brut.

## §6. Pièges génériques de qualification (chantier DL, mai 2026)

Cinq pièges identifiés pendant la qualification du secteur
Dauphiné-Lacassagne. Ils sont **secteur-agnostiques** : tout outil de
qualification (DL, MP, futurs secteurs) doit les neutraliser.

### Piège 1 — MAJIC LOCAUX 2 exclut les personnes physiques (RGPD)

`social_pct` est **surévalué** : MAJIC LOCAUX 2 n'expose pas les
propriétaires personnes physiques (RGPD), donc une copro
décollectivisée (lots revendus à des particuliers) paraît massivement
détenue par des personnes morales.

**Antidote** : croiser avec DVF. Si `mut/an ≥ 2` sur l'adresse exacte
→ **ne pas tagger social**, même si `social_pct ≥ 60 %` : une rotation
soutenue signe une copro privée en cours de décollectivisation.
(Seuils déjà encodés : `secteurs.json[<slug>].metier.seuils` =
`social_pct_min: 60`, `mut_apt_per_year_min: 2`.)

**Cas de référence** : **28 ÉTIENNE RICHERAND** (« Charial ») — MAJIC
dit **98,4 % social**, mais **6,2 mut/an** = décollectivisation → en
réalité **copro privée majoritaire**.

### Piège 2 — FA-source (façade fictive) à 0 vente propre

Une façade fictive (`_fusion_auto=True`) sans vente propre ne doit
**pas** se voir attribuer les mutations de sa parcelle : ce sont les
ventes d'autres bâtiments, comptées en double.

**Antidote** : guard à 2 conditions.
- `FA && own_ventes == 0` → **skip** (ne rien compter).
- `FA && own_ventes > 0` → **traiter normalement** (ex. 84B DAUPHINE).

**Cas de référence** : **11 façades fictives RUE DU DAUPHINÉ**
(suffixes B/A/C/D sur les n° 25 à 55, toutes fusionnées vers le
**59 RUE DU DAUPHINÉ**) + **2B DAUPHINÉ** (façade du **2 RUE DU
DAUPHINÉ**). Toutes à 0 vente propre, ventes réelles portées par les
ancres 59 et 2.

### Piège 3 — DVF rate les suffixes B/T/Q dans certains lots

DVF ne rattache pas toujours les suffixes (B/T/Q) au bon lot →
**ventes orphelines** invisibles à l'adresse.

**Antidote** : récupérer par **élargissement de clé** (recherche des
mutations suffixées), avec **garde-fou anti-doublon** obligatoire pour
ne pas re-compter une vente déjà rattachée.

### Piège 4 — bgid mal snappés (light vs BAN autoritaire)

Quand `make_light` snappe une adresse sur un `batiment_groupe_id`
différent de celui que désigne BAN, l'adresse est rattachée au
**mauvais bâtiment** → ses ventes deviennent invisibles.

**Antidote** : détection **automatisable** (comparaison bgid light vs
bgid BAN-autoritaire) → alimente la pile orange. **Correction =
arbitrage manuel** (pattern Cambronne/Sisley, jamais auto).

**Cas de référence** : **12 ESPÉRANCE**.

### Piège 5 — le nom d'un propriétaire ne dit pas sa nature juridique

Tagger « social » sur la base du **libellé** du propriétaire produit
des faux positifs.

**Antidote** : filtrer sur la **forme juridique** (HLM / OPH / ESH /
OPAC…), pas sur le libellé. Les needles `metier.hlm_needles` /
`public_non_hlm` doivent viser des formes/entités, pas des mots
vagues.

**Cas de référence** : **« ASSOCIATION DE L'HÔTEL SOCIAL »**
(227 FÉLIX FAURE) = **association privée prospectable**, PAS du social
malgré le mot « social » dans le nom.

## §7. Plan chantier — Pipeline secteur-agnostique

Objectif : un pipeline de qualification **paramétré par secteur**
(via `data/secteurs.json[<slug>]`), validé sur DL avant tout scan MP.

| Étape | Statut | Contenu |
|---|---|---|
| **1. Config par secteur** | ✅ **FAIT** (`d92abcf`) | `data/secteurs.json` (chemins, géo, needles, seuils par slug) |
| **2. Modulariser les outils** | ✅ **FAIT** (`411390b`) | Les 4 moteurs (`_scan`, `fix_kv`, `enrich_full`, `enrich`) + helper `secteur_config.py` lisent `secteurs.json[<slug>]` via `--secteur`. Logique inchangée. |
| **3. Coder les 2 détecteurs** | ✅ **FAIT** (`8e21d54`) | `_detect_bgid_suspects.py` (piège 4) + `_detect_noms_ambigus.py` (piège 5), read-only secteur-agnostiques, alimentent la pile **orange**. |
| **4. Tri 3 piles + rapport** | à faire | 🟢 **verte** = certifié auto · 🟠 **orange** = à arbitrer · 🔴 **rouge** = anomalies données. Produit un **rapport par secteur** + tag dashboard `a_arbitrer`. |
| **5. VALIDATION sur DL** | à faire | **Banc d'essai** : le pipeline doit **reproduire l'état KV DL actuel à l'identique** (résultats auto **+ overrides préservés**, cf. §5). ⛔ **NE PAS scanner MP tant que DL n'est pas reproductible.** |
| **6. Scan MP** | 🔒 bloqué (§5 + needles) | À n'exécuter **qu'après** étape 5 réussie **ET** constitution des **needles parisiennes** (cf. `secteurs.json[motte-picquet].metier._TODO`). |

**Sortie attendue de l'étape 6 (MP)** :
- MP **qualifié à 100 %** : **1014 untagged scannés** + **73 legacy
  ré-audités**.
- **3 piles** produites (verte / orange / rouge).
- **Pile orange arbitrée par Yann** (les arbitrages deviennent des
  overrides — entrées sacrées, cf. §5).
