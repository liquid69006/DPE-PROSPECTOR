# Vérification globale RNC → BDNB — bilan (lecture seule)

Source : snapshot local `data/bdnb_dauphine_lacassagne.json` (aucun appel API, reproductible via `scripts/verif_rnc_bdnb.py`). Lien RNC↔BDNB = `numero_immat_principal`. Un `batiment_groupe_id` est *manquant* s'il n'est référencé par **aucune** adresse du jeu secteur.

## Bilan chiffré

| Indicateur | Valeur |
|---|--:|
| Copros RNC (light) | 553 |
| Immat distincts dans le snapshot BDNB | 533 |
| Copros liées avec écart | 20 |
| **A. Vraie fusion manquante** | **20 copros · 24 bât · 52 lgts** |
| **B. Adresse copro absente du croisement** | **0 copros · 0 bât · 0 lgts** |
| bgid snapshot inutilisés par une adresse | 369 |
| bgid secteur absents du snapshot | 0 |

> **A** = cible directe d'une passe de fusion (copro déjà dans le jeu, bâtiment BDNB supplémentaire non rattaché). **B** = trou amont de croisement d'adresses (la copro n'a aucune adresse dans les 1166) — à corriger côté géocodage/jointure, pas par fusion.

## Catégorie A — vraies fusions manquantes (toutes, 20 copros)

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|
| 1 | AF4379210 | ESPRIT JARDIN A | `28|RUE|CITE` | 2 | 1 | 1 | 12 | `bdnb-bg-XKYK-HDG5-8HDC` 28 Rue de la Cité 69003 Lyon 3e Arrondissement (12 log) |
| 2 | AD1124098 | 281 RUE PAUL BERT | `281|RUE|PAUL BERT` | 4 | 1 | 3 | 11 | `bdnb-bg-68NM-VK87-N53K` 281 Rue Paul Bert 69003 Lyon 3e Arrondissement (5 log)<br>`bdnb-bg-K7VE-YX44-Y3F9` 281 Rue Paul Bert 69003 Lyon 3e Arrondissement (0 log)<br>`bdnb-bg-ZFWH-M36K-8AL7` 281 Rue Paul Bert 69003 Lyon 3e Arrondissement (6 log) |
| 3 | AE1699040 | LE CLOS ROUGET DE L'ISLE | `264B|RUE|PAUL BERT` | 3 | 2 | 1 | 8 | `bdnb-bg-NLTQ-X8HS-GWPG` 264B Rue Paul Bert 69003 Lyon 3e Arrondissement (8 log) |
| 4 | AB2996023 | 316 LAFAYETTE | `316|COURS|LAFAYETTE` | 2 | 1 | 1 | 6 | `bdnb-bg-LEVA-AZLY-VTU1` 316 Cours Lafayette 69003 Lyon 3e Arrondissement (6 log) |
| 5 | AH0715979 | 4 rue Etienne RICHERAND | `4|RUE|ETIENNE RICHERAND` | 2 | 1 | 1 | 4 | `bdnb-bg-YFUR-LHTB-FGXJ` 4 Rue Étienne Richerand 69003 Lyon 3e Arrondissement (4 log) |
| 6 | AD9391244 | LE PATIO SAINT-ANTOINE - MS167298 | `50|RUE|ST ANTOINE` | 3 | 1 | 2 | 3 | `bdnb-bg-9H8U-9VAU-EN8T` 50 Rue Saint-Antoine 69003 Lyon 3e Arrondissement (2 log)<br>`bdnb-bg-NBV8-YC65-QXEZ` 50 Rue Saint-Antoine 69003 Lyon 3e Arrondissement (1 log) |
| 7 | AF6359384 | 331 rue Paul Bert 69003 LYON | `331|RUE|PAUL BERT` | 2 | 1 | 1 | 2 | `bdnb-bg-JD5P-DNQX-XAPV` 331 Rue Paul Bert 69003 Lyon 3e Arrondissement (2 log) |
| 8 | AA3108057 | 198 AVENUE FELIX FAURE | `198|AVENUE|FELIX FAURE` | 2 | 1 | 1 | 1 | `bdnb-bg-HLNU-7LGU-8FN5` 198.0 AVENUE FELIX FAURE 69003 Lyon 3e Arrondissement (1 log) |
| 9 | AA3708823 | SDC LE BOUTON D'OR | `36|RUE|DOCTEUR REBATEL` | 2 | 1 | 1 | 1 | `bdnb-bg-MK4U-818W-4W3T` 36 Rue Docteur Rebatel 69003 Lyon 3e Arrondissement (1 log) |
| 10 | AC9146481 | 228/230 Rue Paul Bert | `228|RUE|PAUL BERT` | 2 | 1 | 1 | 1 | `bdnb-bg-8BNN-JZ42-KT65` 228 Rue Paul Bert 69003 Lyon 3e Arrondissement (1 log) |
| 11 | AD1162361 | 95 RUE BARABAN | `95|RUE|BARABAN` | 2 | 1 | 1 | 1 | `bdnb-bg-QDR7-6GJV-V4TC` 95 Rue Baraban 69003 Lyon 3e Arrondissement (1 log) |
| 12 | AE5562418 | SDC 51 RUE DU DAUPHINE | `51|RUE|DAUPHINE` | 2 | 1 | 1 | 1 | `bdnb-bg-NAE9-FMH5-CKL3` 51 Rue du Dauphiné 69003 Lyon 3e Arrondissement (1 log) |
| 13 | AE6121685 | BARA | `3|RUE|BARA #AE6121685` | 2 | 1 | 1 | 1 | `bdnb-bg-KL36-5KML-NGF2` 3 Rue Bara 69003 Lyon 3e Arrondissement (1 log) |
| 14 | AB7150030 | 39 RUE DU DAUPHINE* | `39|RUE|DAUPHINE` | 3 | 1 | 2 | 0 | `bdnb-bg-138Y-RTAZ-85Y5` 39 Rue du Dauphiné 69003 Lyon 3e Arrondissement (0 log)<br>`bdnb-bg-LXFE-MYWH-X5C2` 39 Rue du Dauphiné 69003 Lyon 3e Arrondissement (0 log) |
| 15 | AA7211261 | 242 AV FELIX FAURE | `242|AVENUE|FELIX FAURE` | 2 | 1 | 1 | 0 | `bdnb-bg-NXHS-FA28-L2TF` 242 Avenue Félix Faure 69003 Lyon 3e Arrondissement (0 log) |
| 16 | AA8431108 | 1/3 RUE SAINT EUSEBE | `1|RUE|ST EUSEBE` | 2 | 1 | 1 | 0 | `bdnb-bg-3FEU-Z8KB-CLPZ` 1 Rue Saint-Eusèbe 69003 Lyon 3e Arrondissement (0 log) |
| 17 | AB1910728 | 20 TER RUE GUILLOUD | `20T|RUE|GUILLOUD` | 2 | 1 | 1 | 0 | `bdnb-bg-CLN3-X8K2-SCET` 20T Rue Guilloud 69003 Lyon 3e Arrondissement (0 log) |
| 18 | AB2810141 | 17 DAVID | `17|RUE|DAVID` | 2 | 1 | 1 | 0 | `bdnb-bg-9KJT-5BBV-CLTB` 17 Rue David 69003 Lyon 3e Arrondissement (0 log) |
| 19 | AB7163991 | 175 AVENUE FELIX FAURE | `175|AVENUE|FELIX FAURE` | 2 | 1 | 1 | 0 | `bdnb-bg-CYHK-G282-9UZS` 175 Avenue Félix Faure 69003 Lyon 3e Arrondissement (0 log) |
| 20 | AC6529416 | RESIDENCE 351 RUE P.BERT | `351|RUE|PAUL BERT` | 2 | 1 | 1 | 0 | `bdnb-bg-G7QC-KCQS-R9J2` None (0 log) |

## Catégorie B — top 20 par logements manquants

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|

## Catégorie B — top 20 par nombre de bâtiments manquants

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|


## Diagnostic catégorie B — causes racines

| Sous-cause | Copros | Nature |
|---|--:|---|
| **B1b** numéro copro absent des 1166, voisin même rue <25 m | 0 | univers d'adresses incomplet (bâti pourtant présent en BDNB par immat) |
| **B1a** vrai trou isolé (aucune adresse 1166 < 25 m) | 0 | rue mal couverte / clé malformée |
| **B2** bis/ter ou type de voie replié sur le numéro de base | 0 | normalisation de clé trop agressive |
| **B3** une adresse partagée par 2 copros | 0 | modèle 1 clé → 1 bgid (collision) |

> **Cause dominante (B1a+B1b = 0 copros)** : les 1166 adresses ont été bâties à partir des lignes mutations/sources, pas exhaustivement depuis les adresses de référence RNC. Une copro sans mutation DVF récente à son numéro exact n'a aucune ligne adresse — alors que son bâtiment existe en BDNB via `numero_immat_principal`. **B2/B3 (0)** : la clé `NUM|TYPE|RUE` à un seul bgid perd le bis/ter et les adresses partagées.

### B1b — numéro absent, adresse 1166 voisine (<25 m)

| Immat | Copropriété | clé_adresse RNC | adresse 1166 la plus proche |
|---|---|---|---|

### B1a — vrai trou isolé

| Immat | Copropriété | clé_adresse RNC | adresse 1166 la plus proche |
|---|---|---|---|

### B2 — bis/ter / type de voie replié

| Immat | Copropriété | clé_adresse RNC | clé 1166 absorbante |
|---|---|---|---|

### B3 — adresse partagée par 2 copros

| Immat | Copropriété | clé_adresse RNC | — |
|---|---|---|---|

## Recommandation

Court-circuiter le croisement d'adresses pour l'attribution RNC↔BDNB : quand une copro a un lien propre `numero_immat_principal` en BDNB, rattacher directement ses `batiment_groupe_id` par immat (corrige B1a/B1b/B2, ~38/42). Pour B3, indexer les adresses par `(clé, immat)` au lieu de la clé seule afin de représenter deux copros à une même adresse postale.
