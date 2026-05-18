# Vérification globale RNC → BDNB — bilan (lecture seule)

Source : snapshot local `data/bdnb_dauphine_lacassagne.json` (aucun appel API, reproductible via `scripts/verif_rnc_bdnb.py`). Lien RNC↔BDNB = `numero_immat_principal`. Un `batiment_groupe_id` est *manquant* s'il n'est référencé par **aucune** adresse du jeu secteur.

## Bilan chiffré

| Indicateur | Valeur |
|---|--:|
| Copros RNC (light) | 821 |
| Immat distincts dans le snapshot BDNB | 796 |
| Copros liées avec écart | 55 |
| **A. Vraie fusion manquante** | **9 copros · 9 bât · 63 lgts** |
| **B. Adresse copro absente du croisement** | **46 copros · 47 bât · 743 lgts** |
| bgid snapshot inutilisés par une adresse | 187 |
| bgid secteur absents du snapshot | 0 |

> **A** = cible directe d'une passe de fusion (copro déjà dans le jeu, bâtiment BDNB supplémentaire non rattaché). **B** = trou amont de croisement d'adresses (la copro n'a aucune adresse dans les 1166) — à corriger côté géocodage/jointure, pas par fusion.

## Catégorie A — vraies fusions manquantes (toutes, 9 copros)

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|
| 1 | AB7673924 | 47 RUE FONDARY | `47|RUE|FONDARY` | 2 | 1 | 1 | 34 | `bdnb-bg-2B72-XLDV-RUD8` 47 Rue Fondary 75015 Paris 15e Arrondissement (34 log) |
| 2 | AB0927913 | 77 COMMERCE | `77|RUE|COMMERCE` | 2 | 1 | 1 | 12 | `bdnb-bg-1LM9-X81M-X9E8` 77 Rue du Commerce 75015 Paris 15e Arrondissement (12 log) |
| 3 | AB9227737 | SDC 64 LETELLIER | `64|RUE|LETELLIER` | 2 | 1 | 1 | 7 | `bdnb-bg-XWCZ-URFJ-63W8` 64 Rue Letellier 75015 Paris 15e Arrondissement (7 log) |
| 4 | AB4519302 | 20 rue de l'Avre | `20|RUE|AVRE` | 2 | 1 | 1 | 5 | `bdnb-bg-D91X-C7XL-KDVM` 20 Rue de l'Avre 75015 Paris 15e Arrondissement (5 log) |
| 5 | AA8927949 | SDC 9 BIS LAKANAL | `9B|RUE|LAKANAL` | 2 | 1 | 1 | 4 | `bdnb-bg-H8ED-S65E-27QN` 9B Rue Lakanal 75015 Paris 15e Arrondissement (4 log) |
| 6 | AC1927326 | SDC 64 rue de la Croix Nivert 75015 PA | `64|RUE|CROIX NIVERT` | 2 | 1 | 1 | 1 | `bdnb-bg-4ZDC-GPF9-LXJ1` 64 Rue de la Croix Nivert 75015 Paris 15e Arrondissement (1 log) |
| 7 | AA0600619 | SQUARE LOWENDAL | `5|RUE|ALEXANDRE CABANEL` | 3 | 2 | 1 | 0 | `bdnb-bg-CY1V-7M4M-TXBG` None (0 log) |
| 8 | AB7675747 | SDC 17 BOULEVARD GARIBALDI 75015 PARIS | `17|BOULEVARD|GARIBALDI` | 2 | 1 | 1 | 0 | `bdnb-bg-UEJ8-7NS9-6X7H` 17.0 BOULEVARD GARIBALDI 75015 Paris 15e Arrondissement (0 log) |
| 9 | AC0962894 | 13 RUE FALLEMPIN | `13|RUE|FALLEMPIN` | 2 | 1 | 1 | 0 | `bdnb-bg-U62N-DVT6-Q3EJ` None (0 log) |

## Catégorie B — top 20 par logements manquants

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|
| 1 | AA5741111 | 40 BIS SUFFREN | `40B|AVENUE|SUFFREN` | 1 | 0 | 1 | 149 | `bdnb-bg-C7QQ-X17T-HLMS` 40B Avenue de Suffren 75015 Paris 15e Arrondissement (149 log) |
| 2 | AC0264010 | SDC 42 Suffren | `42|AVENUE|SUFFREN` | 1 | 0 | 1 | 38 | `bdnb-bg-LBQE-B74L-BGHB` 42 Avenue de Suffren 75015 Paris 15e Arrondissement (38 log) |
| 3 | AB8151755 | 42, AV. SAXE/10 RUE PERIGNON | `42|AVENUE|SAXE` | 1 | 0 | 1 | 32 | `bdnb-bg-QPWJ-BC6L-9W1A` 42 Avenue de Saxe 75007 Paris 7e Arrondissement (32 log) |
| 4 | AH7248073 | SDC 57 SUFFREN | `57|AVENUE|SUFFREN` | 1 | 0 | 1 | 32 | `bdnb-bg-NULF-A944-MHQA` 57 Avenue de Suffren 75007 Paris 7e Arrondissement (32 log) |
| 5 | AA8895435 | SDC 3/5 RUE DU CAPITAINE SCOTT | `3|RUE|CAPITAINE SCOTT` | 2 | 0 | 2 | 29 | `bdnb-bg-QVW8-5P2S-ENU5` 3 Rue du Capitaine Scott 75015 Paris 15e Arrondissement (6 log)<br>`bdnb-bg-WGEL-XEFS-SHSJ` 3 Rue du Capitaine Scott 75015 Paris 15e Arrondissement (23 log) |
| 6 | AC8648685 | SDC 11 RUE DU GENERAL DE LARMINAT | `11|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 28 | `bdnb-bg-37WL-T87E-MY2F` 11 Rue du Général de Larminat 75015 Paris 15e Arrondissement (28 log) |
| 7 | AC9870650 | 9 rue pérignon | `9|RUE|PERIGNON` | 1 | 0 | 1 | 21 | `bdnb-bg-8LUJ-WDNA-8757` 9 Rue Pérignon 75015 Paris 15e Arrondissement (21 log) |
| 8 | AD7454481 | 18, Rue Saint Saëns | `18|RUE|ST SAENS` | 1 | 0 | 1 | 20 | `bdnb-bg-PAV6-AFL1-5HRT` 18 Rue Saint-Saëns 75015 Paris 15e Arrondissement (20 log) |
| 9 | AA4866968 | SDC 2 ter rue Alasseur | `2T|RUE|ALASSEUR` | 1 | 0 | 1 | 18 | `bdnb-bg-J81C-46M3-6UGZ` 2T Rue Alasseur 75015 Paris 15e Arrondissement (18 log) |
| 10 | AB3628898 | SDC 15  VIOLET | `15|RUE|VIOLET` | 1 | 0 | 1 | 18 | `bdnb-bg-A4BC-UMGJ-64NK` 15 Rue Violet 75015 Paris 15e Arrondissement (18 log) |
| 11 | AB6177950 | SUFFREN - 112 | `112T|AVENUE|SUFFREN` | 1 | 0 | 1 | 18 | `bdnb-bg-V6R3-YUFA-KFKR` 112T Avenue de Suffren 75015 Paris 15e Arrondissement (18 log) |
| 12 | AB7675259 | 32 RUE PERIGNON | `32|RUE|PERIGNON` | 1 | 0 | 1 | 18 | `bdnb-bg-KZHK-UD9J-N57W` 32 Rue Pérignon 75015 Paris 15e Arrondissement (18 log) |
| 13 | AB8458838 | 22 RUE SAINT SAENS | `22|RUE|ST SAENS` | 1 | 0 | 1 | 16 | `bdnb-bg-4HSS-GNSZ-ZSUU` 22 RUE SAINT SAENS 75015 Paris 15e Arrondissement (16 log) |
| 14 | AB8862260 | SDC 8 BIS RUE BARTHELEMY | `8B|RUE|BARTHELEMY` | 1 | 0 | 1 | 16 | `bdnb-bg-6UA3-2J64-2ARG` 8B Rue Barthélemy 75015 Paris 15e Arrondissement (16 log) |
| 15 | AC2917656 | SDC 6 AV DU GENERAL DETRIE | `6|AVENUE|GENERAL DETRIE` | 1 | 0 | 1 | 16 | `bdnb-bg-XDLQ-CMKN-FNWA` 6 Avenue du Général Detrie 75007 Paris 7e Arrondissement (16 log) |
| 16 | AC7998412 | Copropriété du 6 bd Garibaldi - Paris  | `6|BOULEVARD|GARIBALDI` | 1 | 0 | 1 | 16 | `bdnb-bg-BWYP-EQFG-KRBB` 6 Boulevard Garibaldi 75015 Paris (16 log) |
| 17 | AB6094874 | SDC 3 RUE SAINT SAENS | `3|RUE|ST SAENS` | 1 | 0 | 1 | 15 | `bdnb-bg-A2M9-EBZ3-CN1C` 3 RUE SAINT SAENS 75015 Paris 15e Arrondissement (15 log) |
| 18 | AD9170887 | SDC 7 TER RUE DU GENERAL DE LARMINAT 7 | `7T|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 15 | `bdnb-bg-EBUV-RS3R-VG2J` 7T Rue du Général de Larminat 75015 Paris 15e Arrondissement (15 log) |
| 19 | AA9446949 | 8 RUE DU GENERAL LARMINAT | `8|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 14 | `bdnb-bg-QS63-LZ8W-HJ1G` 8 Rue du Général de Larminat 75015 Paris 15e Arrondissement (14 log) |
| 20 | AC8117780 | 11 bis rue de Pondichery | `11B|RUE|PONDICHERY` | 1 | 0 | 1 | 14 | `bdnb-bg-396G-P894-CYQ1` 11B Rue de Pondichéry 75015 Paris 15e Arrondissement (14 log) |

## Catégorie B — top 20 par nombre de bâtiments manquants

| # | Immat | Copropriete | clé_adresse | BDNB | Prés. | Manq. | Lgts manq. | Bâtiments manquants |
|--:|---|---|---|--:|--:|--:|--:|---|
| 1 | AA8895435 | SDC 3/5 RUE DU CAPITAINE SCOTT | `3|RUE|CAPITAINE SCOTT` | 2 | 0 | 2 | 29 | `bdnb-bg-QVW8-5P2S-ENU5` 3 Rue du Capitaine Scott 75015 Paris 15e Arrondissement (6 log)<br>`bdnb-bg-WGEL-XEFS-SHSJ` 3 Rue du Capitaine Scott 75015 Paris 15e Arrondissement (23 log) |
| 2 | AA5741111 | 40 BIS SUFFREN | `40B|AVENUE|SUFFREN` | 1 | 0 | 1 | 149 | `bdnb-bg-C7QQ-X17T-HLMS` 40B Avenue de Suffren 75015 Paris 15e Arrondissement (149 log) |
| 3 | AC0264010 | SDC 42 Suffren | `42|AVENUE|SUFFREN` | 1 | 0 | 1 | 38 | `bdnb-bg-LBQE-B74L-BGHB` 42 Avenue de Suffren 75015 Paris 15e Arrondissement (38 log) |
| 4 | AB8151755 | 42, AV. SAXE/10 RUE PERIGNON | `42|AVENUE|SAXE` | 1 | 0 | 1 | 32 | `bdnb-bg-QPWJ-BC6L-9W1A` 42 Avenue de Saxe 75007 Paris 7e Arrondissement (32 log) |
| 5 | AH7248073 | SDC 57 SUFFREN | `57|AVENUE|SUFFREN` | 1 | 0 | 1 | 32 | `bdnb-bg-NULF-A944-MHQA` 57 Avenue de Suffren 75007 Paris 7e Arrondissement (32 log) |
| 6 | AC8648685 | SDC 11 RUE DU GENERAL DE LARMINAT | `11|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 28 | `bdnb-bg-37WL-T87E-MY2F` 11 Rue du Général de Larminat 75015 Paris 15e Arrondissement (28 log) |
| 7 | AC9870650 | 9 rue pérignon | `9|RUE|PERIGNON` | 1 | 0 | 1 | 21 | `bdnb-bg-8LUJ-WDNA-8757` 9 Rue Pérignon 75015 Paris 15e Arrondissement (21 log) |
| 8 | AD7454481 | 18, Rue Saint Saëns | `18|RUE|ST SAENS` | 1 | 0 | 1 | 20 | `bdnb-bg-PAV6-AFL1-5HRT` 18 Rue Saint-Saëns 75015 Paris 15e Arrondissement (20 log) |
| 9 | AA4866968 | SDC 2 ter rue Alasseur | `2T|RUE|ALASSEUR` | 1 | 0 | 1 | 18 | `bdnb-bg-J81C-46M3-6UGZ` 2T Rue Alasseur 75015 Paris 15e Arrondissement (18 log) |
| 10 | AB3628898 | SDC 15  VIOLET | `15|RUE|VIOLET` | 1 | 0 | 1 | 18 | `bdnb-bg-A4BC-UMGJ-64NK` 15 Rue Violet 75015 Paris 15e Arrondissement (18 log) |
| 11 | AB6177950 | SUFFREN - 112 | `112T|AVENUE|SUFFREN` | 1 | 0 | 1 | 18 | `bdnb-bg-V6R3-YUFA-KFKR` 112T Avenue de Suffren 75015 Paris 15e Arrondissement (18 log) |
| 12 | AB7675259 | 32 RUE PERIGNON | `32|RUE|PERIGNON` | 1 | 0 | 1 | 18 | `bdnb-bg-KZHK-UD9J-N57W` 32 Rue Pérignon 75015 Paris 15e Arrondissement (18 log) |
| 13 | AB8458838 | 22 RUE SAINT SAENS | `22|RUE|ST SAENS` | 1 | 0 | 1 | 16 | `bdnb-bg-4HSS-GNSZ-ZSUU` 22 RUE SAINT SAENS 75015 Paris 15e Arrondissement (16 log) |
| 14 | AB8862260 | SDC 8 BIS RUE BARTHELEMY | `8B|RUE|BARTHELEMY` | 1 | 0 | 1 | 16 | `bdnb-bg-6UA3-2J64-2ARG` 8B Rue Barthélemy 75015 Paris 15e Arrondissement (16 log) |
| 15 | AC2917656 | SDC 6 AV DU GENERAL DETRIE | `6|AVENUE|GENERAL DETRIE` | 1 | 0 | 1 | 16 | `bdnb-bg-XDLQ-CMKN-FNWA` 6 Avenue du Général Detrie 75007 Paris 7e Arrondissement (16 log) |
| 16 | AC7998412 | Copropriété du 6 bd Garibaldi - Paris  | `6|BOULEVARD|GARIBALDI` | 1 | 0 | 1 | 16 | `bdnb-bg-BWYP-EQFG-KRBB` 6 Boulevard Garibaldi 75015 Paris (16 log) |
| 17 | AB6094874 | SDC 3 RUE SAINT SAENS | `3|RUE|ST SAENS` | 1 | 0 | 1 | 15 | `bdnb-bg-A2M9-EBZ3-CN1C` 3 RUE SAINT SAENS 75015 Paris 15e Arrondissement (15 log) |
| 18 | AD9170887 | SDC 7 TER RUE DU GENERAL DE LARMINAT 7 | `7T|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 15 | `bdnb-bg-EBUV-RS3R-VG2J` 7T Rue du Général de Larminat 75015 Paris 15e Arrondissement (15 log) |
| 19 | AA9446949 | 8 RUE DU GENERAL LARMINAT | `8|RUE|GENERAL DE LARMINAT` | 1 | 0 | 1 | 14 | `bdnb-bg-QS63-LZ8W-HJ1G` 8 Rue du Général de Larminat 75015 Paris 15e Arrondissement (14 log) |
| 20 | AC8117780 | 11 bis rue de Pondichery | `11B|RUE|PONDICHERY` | 1 | 0 | 1 | 14 | `bdnb-bg-396G-P894-CYQ1` 11B Rue de Pondichéry 75015 Paris 15e Arrondissement (14 log) |


## Diagnostic catégorie B — causes racines

| Sous-cause | Copros | Nature |
|---|--:|---|
| **B1b** numéro copro absent des 1166, voisin même rue <25 m | 20 | univers d'adresses incomplet (bâti pourtant présent en BDNB par immat) |
| **B1a** vrai trou isolé (aucune adresse 1166 < 25 m) | 3 | rue mal couverte / clé malformée |
| **B2** bis/ter ou type de voie replié sur le numéro de base | 10 | normalisation de clé trop agressive |
| **B3** une adresse partagée par 2 copros | 13 | modèle 1 clé → 1 bgid (collision) |

> **Cause dominante (B1a+B1b = 23 copros)** : les 1166 adresses ont été bâties à partir des lignes mutations/sources, pas exhaustivement depuis les adresses de référence RNC. Une copro sans mutation DVF récente à son numéro exact n'a aucune ligne adresse — alors que son bâtiment existe en BDNB via `numero_immat_principal`. **B2/B3 (23)** : la clé `NUM|TYPE|RUE` à un seul bgid perd le bis/ter et les adresses partagées.

### B1b — numéro absent, adresse 1166 voisine (<25 m)

| Immat | Copropriété | clé_adresse RNC | adresse 1166 la plus proche |
|---|---|---|---|
| AA4713186 | 7 rue de castelnau | `7|RUE|GENERAL DE CASTELNAU` | 7|RUE|GAL DE CASTELNAU (~0 m) |
| AA8895435 | SDC 3/5 RUE DU CAPITAINE SCOTT | `3|RUE|CAPITAINE SCOTT` | 3|RUE|CAPT SCOTT (~0 m) |
| AA9267253 | IMMEUBLE 25 VIOLET | `25|RUE|VIOLET` | 27|RUE|VIOLET (~7 m) |
| AA9446949 | 8 RUE DU GENERAL LARMINAT | `8|RUE|GENERAL DE LARMINAT` | 8|RUE|GAL DE LARMINAT (~0 m) |
| AB4373353 | ALASSEUR | `3|RUE|ALASSEUR` | 5|RUE|ALASSEUR (~13 m) |
| AB8458838 | 22 RUE SAINT SAENS | `22|RUE|ST SAENS` | 27|BOULEVARD|GRENELLE (~23 m) |
| AC0366161 | 3 rue du Gal Castelnau | `3|RUE|GENERAL DE CASTELNAU` | 3|RUE|GAL DE CASTELNAU (~0 m) |
| AC1004126 | 65 RUE FONDARY | `65|RUE|FONDARY` | 61|RUE|FONDARY (~13 m) |
| AC2917656 | SDC 6 AV DU GENERAL DETRIE | `6|AVENUE|GENERAL DETRIE` | 6|AVENUE|GAL DETRIE (~0 m) |
| AC3796695 | 7 BIS RUE DU GENERAL LARMINAT | `7B|RUE|GENERAL DE LARMINAT` | 9001|RUE|GAL LUCOTTE (~13 m) |
| AC7998412 | Copropriété du 6 bd Garibaldi - Pari | `6|BOULEVARD|GARIBALDI` | 4|BOULEVARD|GARIBALDI (~18 m) |
| AC8648685 | SDC 11 RUE DU GENERAL DE LARMINAT | `11|RUE|GENERAL DE LARMINAT` | 11|RUE|GAL DE LARMINAT (~0 m) |
| AD1811801 | SDC 13 TIPHAINE | `13|RUE|TIPHAINE` | 15|RUE|TIPHAINE (~9 m) |
| AD5265665 | 5 AVENUE DU GENERAL DETRIE | `5|AVENUE|GENERAL DETRIE` | 5|AVENUE|GAL DETRIE (~0 m) |
| AD9170887 | SDC 7 TER RUE DU GENERAL DE LARMINAT | `7T|RUE|GENERAL DE LARMINAT` | 9|RUE|GAL DE LARMINAT (~12 m) |
| AD9546367 | SDC 5 GENERAL DE LARMINAT | `5|RUE|GENERAL DE LARMINAT` | 5|RUE|GAL DE LARMINAT (~0 m) |
| AE0180281 | SDC 21 TIPHAINE | `21|RUE|TIPHAINE` | 19|RUE|TIPHAINE (~10 m) |
| AF1857283 | 1 bis BUENOS AYRES | `1B|RUE|BUENOS AYRES` | 3|RUE|BUENOS AIRES (~19 m) |
| AG8297707 | SDC 3 VILLA DE GRENELLE | `21|RUE|FALLEMPIN` | 19|RUE|FALLEMPIN (~6 m) |
| AH7248073 | SDC 57 SUFFREN | `57|AVENUE|SUFFREN` | 55|AVENUE|SUFFREN (~19 m) |

### B1a — vrai trou isolé

| Immat | Copropriété | clé_adresse RNC | adresse 1166 la plus proche |
|---|---|---|---|
| AB6094874 | SDC 3 RUE SAINT SAENS | `3|RUE|ST SAENS` | 32|RUE|FEDERATION (~32 m) |
| AD7454481 | 18, Rue Saint Saëns | `18|RUE|ST SAENS` | 25|BOULEVARD|GRENELLE (~47 m) |
| AE2886398 | 9 E LAKANAL 75015 PARIS | `9||E R LAKANAL` | 5|RUE|LAKANAL (~34 m) |

### B2 — bis/ter / type de voie replié

| Immat | Copropriété | clé_adresse RNC | clé 1166 absorbante |
|---|---|---|---|
| AA4866968 | SDC 2 ter rue Alasseur | `2T|RUE|ALASSEUR` | 2|RUE|ALASSEUR |
| AA5741111 | 40 BIS SUFFREN | `40B|AVENUE|SUFFREN` | 40|AVENUE|SUFFREN |
| AB5639992 | SDC 9 D RUE LAKANAL | `9D|RUE|LAKANAL` | 9|RUE|LAKANAL |
| AB6177950 | SUFFREN - 112 | `112T|AVENUE|SUFFREN` | 112|AVENUE|SUFFREN |
| AB8862260 | SDC 8 BIS RUE BARTHELEMY | `8B|RUE|BARTHELEMY` | 8|RUE|BARTHELEMY |
| AC5420922 | SDC 2Bis Rue Alasseur | `2B|RUE|ALASSEUR` | 2|RUE|ALASSEUR |
| AC5614987 | 11 BIS RUE VALENTIN HAUY | `11B|RUE|VALENTIN HAUY` | 11|RUE|VALENTIN HAUY |
| AC8117780 | 11 bis rue de Pondichery | `11B|RUE|PONDICHERY` | 11|RUE|PONDICHERY |
| AD0736843 | 47 bis rue du Commerce, 75015 Paris | `47B|RUE|COMMERCE` | 47|RUE|COMMERCE |
| AG5171368 | SDC 76A RUE CROIX NIVERT 75017 PARIS | `76A|RUE|CROIX NIVERT` | 76|RUE|CROIX NIVERT |

### B3 — adresse partagée par 2 copros

| Immat | Copropriété | clé_adresse RNC | — |
|---|---|---|---|
| AB1483791 | SDC 9 LAKANAL | `9|RUE|LAKANAL` |  |
| AB2240224 | SDC 3 RUE ROSA BONHEUR | `3|RUE|ROSA BONHEUR` |  |
| AB3027117 | Fallempin 3 rue LCB | `3|RUE|FALLEMPIN` |  |
| AB3628898 | SDC 15  VIOLET | `15|RUE|VIOLET` |  |
| AB4394060 | SDC 11 RUE CHASSELOUP LAUBAT | `11|RUE|CHASSELOUP LAUBAT` |  |
| AB7675259 | 32 RUE PERIGNON | `32|RUE|PERIGNON` |  |
| AB8151755 | 42, AV. SAXE/10 RUE PERIGNON | `42|AVENUE|SAXE` |  |
| AB9281015 | 112, AVENUE DE SUFFREN 75015 PARIS | `112|AVENUE|SUFFREN` |  |
| AC0264010 | SDC 42 Suffren | `42|AVENUE|SUFFREN` |  |
| AC3186186 | 158 SUFFREN | `158|AVENUE|SUFFREN` |  |
| AC9870650 | 9 rue pérignon | `9|RUE|PERIGNON` |  |
| AD1287697 | 11 AVENUE DE SUFFREN | `11|AVENUE|SUFFREN` |  |
| AD2824910 | SDC 53 AVE DE LA MOTTE PICQUET - 750 | `53|AVENUE|MOTTE PICQUET` |  |

## Recommandation

Court-circuiter le croisement d'adresses pour l'attribution RNC↔BDNB : quand une copro a un lien propre `numero_immat_principal` en BDNB, rattacher directement ses `batiment_groupe_id` par immat (corrige B1a/B1b/B2, ~38/42). Pour B3, indexer les adresses par `(clé, immat)` au lieu de la clé seule afin de représenter deux copros à une même adresse postale.
