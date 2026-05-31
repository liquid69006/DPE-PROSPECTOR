# JOURNAL — DPE-PROSPECTOR

> Journal de session daté. Entrées les plus récentes en haut.
> Méthodologie durable → `PIPELINE.md` ; briefing → `CLAUDE.md`.

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
