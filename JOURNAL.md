# JOURNAL — DPE-PROSPECTOR

> Journal de session daté. Entrées les plus récentes en haut.
> Méthodologie durable → `PIPELINE.md` ; briefing → `CLAUDE.md`.

---

## 2026-06-03 — Déploiement Secteur Montchat (Phase 5 → doc Phase 7)

Déploiement complet de Secteur Prospector sur **Montchat**, zone intra-DL
(`dauphine-lacassagne-montchat`, toggle header). Qualification manche par
manche (A, G, B1, B2a, D, F, H), clôture marché-libre. Doc canonique mise à
jour (CLAUDE.md §3/§5/§7/§10, PIPELINE.md §6 + §12).

### Commits

| Hash | Titre |
|---|---|
| `cdb214e` | infra MAJIC Montchat (secteurs.json + cache parcelle + enrich) |
| `1dbc416` | manche D (mono / copro_non_immat) |
| `e792551` | manche F (social / mixte) |
| `06cb2ae` | docs(secteur): Montchat Phase 5 (diags + sources) |
| `eeb326f` | fix auth worker — match préfixe `secId` zone-suffixé |

### Insights clés

- **`owner_share` = fallback social hors-RNC** (Montchat-only) ; candidat au
  générique si DL/MP le rencontrent. cf. `PIPELINE.md` §12.
- **Social prime sur mono** : bailleurs sociaux passaient le filtre mono →
  garde social-précédence.
- **Vérifier le KV live, pas le mirror** : manche D revertée sans que le
  mirror le reflète ; rituel anti-drift a reconstruit 103 → 381 → 505.
- **Auth worker** : `secId` zone-suffixé non autorisé par égalité exacte →
  match préfixe (`startsWith(a + "-")`), déployé via `wrangler deploy`.
- **Bug 429 `enrich_majic_full`** : fetcher interne jeté en 429, cache `[]` ;
  contourné par `_fetch_bgid_parcelle_montchat.py` (resumable, throttle
  0,25 s + backoff + checkpoint). **Dette** : à corriger pour re-builds DL/MP.
- **Chiffres finaux** : 505 tags, parc 13 815, marché-libre 181,6/an, taux
  1,3 %/an.

### Chantiers ouverts

- **Résidus terrain** : 8 (F) + 46 mono-faible + 25 angle (D) + 34 cross-rue (B2b).
- **Dette 429 `enrich_majic_full`** (re-builds DL/MP).
- **DL** : drift KV (584,6 vs 578,4/an, `cible_0vente_*` non migrés) + migration
  `cible_0vente` → `as.cible` à trancher.
- **Sauvegarde des extracteurs hors-dépôt** (single-point-of-failure, toutes agences).

---

## 2026-06-01 — Strict = marché libre + hygiène fusion/immat (DL)

Session post-jalon 4. Le chantier `_fusion_auto` (~625 façades) annoncé en
priorité s'est révélé un faux départ (Baraban déjà fusionné ; ~625 = chiffre
historique périmé). Le vrai sujet a émergé : la divergence header strict
(597,8/an) vs répartition conseillers (568,4/an), tracée jusqu'au sens même de
« strict ». Trois lots livrés : marché-libre, fusion S1, dé-association
d'immats fantômes.

### Repère unifié (cf. `data/PIPELINE.md` §6)

| Vue | Valeur | Définition |
|---|---|---|
| Brut | **895,2/an** | toutes mutations (parking/commerce/social/bureaux inclus) — *inchangé* |
| Strict / défaut | **578,4/an** | ventes ≥1 lot habitation **et** hors social/bureaux, jugé par tag d'**ancre**, fusion-aware — *repère unique partout* |

Strict brut (Σ nb_ventes_logement/5) = 599,6/an ; l'écart jusqu'à 578,4 = les
ventes en social/bureaux (par ancre) + 1,8/an de garde copro (FLANDIN).
Σ ventes logement = 2998. Parc secL DL = 22 381 (inchangé sur tous les lots).

### Commits (ordre chronologique)

| Hash | Titre |
|---|---|
| `ff46cea` | chore(test): resync test_render_secteur sur refactor renderSecteur 2026-05-24 (plages slice, stubs globals, 3 assertions rebasées) |
| `56253c9` | feat(secteur): strict = marché libre (578,4) — exclusion social/bureaux par ancre, fusion-aware, garde copro, cellules parenthésées |
| `71f2ca3` | fix(dl): fusion S1 (3 façades même-bgid + immat déclaré BDNB), garde `l_libelle_adr` |
| `4cf25a2` | fix(dl): dé-association immats fantômes 121A-D + 11B + garde anti-propagation |

(+ répartition 10 secteurs re-générée sur la base 578,4, KV re-persisté ;
backup `_kv_repartition_dl_backup`.)

### Insights clés

- **Strict = marché libre.** Header dashboard et répartition divergeaient pour
  deux raisons cumulées : (a) le header n'excluait pas social/bureaux
  (≈31/an), (b) `renderSecteur` est fusion-aware alors que `sctGen` ignorait
  les fusions (≈12/an). Aligné : strict = marché libre, exclusion jugée **par
  le tag de l'ancre** de fusion, fusion-aware partout → **578,4 unique**. Brut
  reste « tout ».
- **Garde copro FLANDIN.** Les fusions manuelles vers une ancre **non-copro**
  ne redistribuent pas leurs ventes (garde copro de `renderSecteur`) → 578,4 et
  non 580,2 (1,8/an, cas 5/7→3 FLANDIN, différé à un re-point copro ciblé).
- **« ~625 façades » = fantôme historique.** Les `fix_fusion_*`/INJECT/RE-FUSE
  empilés avaient déjà consolidé l'essentiel ; résiduel réel = 61 bgid éclatés
  / 126 unités, dont S1 (même immat) = 5 groupes.
- **Discriminant `l_libelle_adr`.** « Même immat » ne prouve « même copro » que
  si le bgid **déclare le numéro**. Sinon = immat propagé par faux-matching
  bgid. Verdict S1 : 3 vraies co-immat (6B→4 STE ANNE, 19B→19 ST ANTOINE,
  28B→24 PIONCHON) / 2 fantômes (121 CHARIAL, 11B ST MAXIMIN).
- **Immats fantômes = display-only.** Un immat/lots hérité via bgid sur une
  ligne adresse est display-only (le parc lit les lots via `coproByCle`, pas la
  ligne) → impact parc/ventes **NUL**. 23 adresses concernées (21 déjà masquées
  par fusion). Cause racine : `make_light bdnb_par_voie` rayon 80 m
  (faux-match bgid) + `_apply_propag_immat_21suff_dl.py` qui dénormalise
  l'immat sur tout le bloc.
- **Doublon d'îlot 121 CHARIAL.** Symptôme visible du bgid faux-matché : vrai
  121 (bgid AX8P, îlot 34) vs phantom 121A-D (bgid G1YT = bâti 90-92, îlot 39).
  Résolu par re-point AX8P. ⚠️ Piège évité : dé-fuser les impasses de l'Ordre
  aurait ajouté +21 lgts (sous-fragments du même SDC 28 lots).

### Gardes posées (anti-récidive)

- `l_libelle_adr` à la **fusion** (`fix_fusion_s1_immat.py` + port make_light
  table `DECLARED_S1`).
- `bgid_declares()` / `BGID_DECLARED` à la **propagation**
  (`_apply_propag_immat_21suff_dl.py`).
- Cause source `make_light bdnb_par_voie` 80 m documentée pour traitement
  ultérieur.

### Chantiers ouverts (jalon 5)

1. Vérif définition `ventes_par_an_logement` (make_light vs métier).
2. Migration `cible_0vente_*` → `as.cible`.
3. Déploiement **MP** (pattern manche complet).
4. Re-point copro FLANDIN (5/7→3, micro-chantier, +1,8/an).
5. Cause source des fantômes : faux-matching `make_light bdnb_par_voie` 80 m.

---

## 2026-05-31 — Boucle jalon 4 DL (scellée)

Boucle de qualification du secteur **Dauphiné-Lacassagne** : toutes les
piles d'arbitrage ramenées à 0, pipeline DL reproductible. Jalon 4 scellé
par le commit `b91a33b`.

### État final DL (cf. `PIPELINE.md` §7.1)

| Métrique | Valeur |
|---|---|
| `a_arbitrer` / `a_completer` / `rouge` | **0 / 0 / 0** |
| Pile 🟢 verte | **1385 adresses** |
| `cible_0vente` résiduel | **70** (121 → 70, 51 reclassées vers le vrai type bâti) |
| KV DL | **643 assignments · 6 fusions · 0 noms** |

### Commits (17, ordre chronologique)

| Hash | Titre |
|---|---|
| `93388b0` | fix(kv-dl): batch 3 — 5 corrections social→bureaux (immeubles Commune de Lyon administratifs) |
| `feb8807` | feat(kv-dl): batch 4 — 48 ajouts AUTO_ONLY (bailleurs HLM/publics : +38 social / +10 mixte) |
| `7c0e84e` | fix(kv-dl): batch 5 — 8 re-tags ORANGE résiduels (Jasseron→mono, Commune→bureaux, 132 Baraban→mixte) |
| `f73dc56` | feat(pipeline): nom_ambigu — ne plus ré-arbitrer les clés décidées (M1 tag KV + M2 liste `nom_ambigu_resolus`), secteur-agnostique |
| `0e8ce97` | feat(kv-dl): manche A — 41 Turbil → mixte (zone grise tranchée) |
| `5e11c04` | feat(kv-dl): B2 — 4 Richerand social ; ensemble Tuiliers (11 St Maximin + 9 Tuiliers copro_non_immat + fusion) |
| `2185421` | feat(pipeline): manche II — clear `bgid_live_required` (override `_bgid_resolus` + garde-fous M1 & RNC-skip), cache bgid B0/B0-bis |
| `1c774ff` | data(kv): manche D — re-tag 7 bgid_confirmed (54 Villette + 121 Charial social ; 7 Lacassagne + 31 Dauphine copro_non_immat ; 10 Petites Soeurs + 17 Dauphine mono ; 1 Carry bureaux) |
| `f0bc341` | feat(pipeline): Phase 2 manche D — gate `_arbitres` (verdict-scope) sort les bgid_confirmed de `a_arbitrer` (35→0) |
| `ea6e75b` | feat(ui): PR1 — refonte filter row Secteur (4 dropdowns Catégorie/RNC/Ventes/Logement + 2 presets + barre d'état + auto-déplier) ; retrait 7 toggles-lentilles |
| `cd9e33b` | feat(ui): polish rendu Secteur — menu requalif universel, pré-sélection îlot via `ilotEffectif`, badge implicite Copropriété pour RNC sans tag KV |
| `fe05fee` | feat(pipeline): manche C — gate `_arbitres` indéterminé (`a_completer` 12→0) |
| `56c2640` | feat(pipeline): manche E — deny-list `_cles_invalides` + gate T3 (rouge 1→0) ; mécanisme secteur-agnostique, repli no-op |
| `4c9703d` | data(kv): sync miroir — tag manuel 50 AVENUE LACASSAGNE copro_non_immat (pose via dashboard, hors manche F) |
| `7594814` | data(kv): manche F — re-tag 10 cibles_0vente vers leur vrai type (4 social, 1 mono, 5 copro_non_immat) |
| `e231c74` | data(kv): manche G — re-tag 41 cible_0vente via levier BDNB (3 social + 38 copro_non_immat) ; +fix UI Note 1/Note 2 |
| `b91a33b` | fix(ui): polish final — normalize display adresse + align label strict modale gen/export sur le calcul réel |

### Insights clés (détail → `PIPELINE.md` §10)

- **MAJIC LOCAUX 2 = personnes morales seulement (RGPD)** → copros de
  personnes physiques (ancien lyonnais) sortent à 0 owner PM = faux
  `NEEDS_TERRAIN`.
- **Levier BDNB** : `nb_log_bdnb>1` + pas d'immat RNC + 0 PM MAJIC =
  `copro_non_immat` *par définition* (pas heuristique). Levier des manches F/G.
- **`cible_0vente` = signal commercial**, pas un type bâti → à migrer vers
  `as.cible` séparé (jalon 5).
- **Anti-drift KV a payé** : épisode **50 AVENUE LACASSAGNE** — tag manuel
  dashboard → miroir désync → manche F bloquée à juste titre → sync miroir
  (`4c9703d`) puis reprise.

### Side-files arrivés à maturité cette session

`_arbitres_dl` (verdict-scope), `_cles_invalides_dl` (deny-list T3),
`_bgid_resolus_dl` (re-bind bgid), `_nom_ambigu_resolus_dl` (re-bind nom),
`_social_overrides_dl` (entrées sacrées). Pattern de câblage unique
secteurs.json → secteur_config.py → loader → gate (cf. `PIPELINE.md` §9).

### Chantiers transférés au jalon 5 (cf. `PIPELINE.md` §11)

1. **MP** : déploiement du pattern manche (3 clés malformées LEON
   BOURGEOIS / FONDARY / GRENELLE → deny-list ; cible_0vente PP via levier
   BDNB ; arbitres si besoin).
2. **Révision `_fusion_auto` make_light** (hors-repo) : ~625 façades
   multi-entrées même bgid non auto-fusionnées.
3. **Vérif définition `ventes_par_an_logement`** make_light vs Yann.
4. **Migration `cible_0vente_*` → `as.cible`** (schéma KV).
