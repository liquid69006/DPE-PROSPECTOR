# Manche A — Clés malformées MONTCHAT (pile rouge → 0)

> **Phase 5, Manche A.** Traitement des 10 clés malformées (pile rouge T3) du
> light `data/secteur_montchat_light.json`. Pattern calqué sur le fix DL
> clés-malformées (`scripts/fix_clemalformee.py` + `_dryrun_clemalformee.py`,
> commit ff0af4a) : REBIND `cle_adresse` copro → cle valide + propagation
> immat/lots/syndic ; INJECT clone-based (pattern Suffren) si l'ancre est
> absente ; DENY-list pour l'irrécupérable.
>
> Modifications : `data/secteur_montchat_light.json` (+ backup `.preclemalf.bak`),
> `scripts/fix_clemalformee_montchat.py` (créé), `data/_cles_invalides_montchat.json`.
> **Aucun commit, aucun `git add`.** DL/MP et `index.html` non touchés.

---

## ÉTAPE 1 — Lookups live (RNC / BAN)

### St Isidore — AD5117908 (« LE SECRET D'ISIDORE », 39 lots hab, 82 tot)
- **RNC live** (tabular-api `3ea8e2c3-…`, `numero_immatriculation__exact=AD5117908`) :
  - `nom_usage_copropriete = "LE SECRET D'ISIDORE"`
  - `adresse_reference = "r saint-isidore, 69003 Lyon"` · `numero_voie_adresse = "r saint-isidore,"`
    → **aucun numéro de voie renseigné côté RNC** (le n° n'est pas dans l'adresse).
  - `reference_cadastrale_1 = 69123383DH0010` · `reference_cadastrale_2 = 69123383DH0137`
  - `latitude = 45.75` (tronquée) · `longitude = 4.881329` · `nombre_lots_habitation = 39`.
- **Résolution du numéro par la parcelle** : BDNB `rel_batiment_groupe_parcelle?parcelle_id=eq.69383000DH0137`
  (conversion RNC→BDNB Lyon : `69123383…` → `69383000…`) →
  bgids `S5D6-FVVN-T57M`, `4PCJ-EJJT-D5X7`, `55TB-…`, `FSR8-…`. Dans le light,
  bgid `S5D6-FVVN-T57M` porte **`44|RUE|ST ISIDORE`** (et `44B`). `DH0010` →
  0 bgid BDNB.
- **BAN reverse** des coords RNC (`lon=4.881329&lat=45.75`) → top hit
  **`44ter Rue Saint Isidore 69003 Lyon`** (score 0,9957). Concordant.
- **Verdict : n° = 44 → REBIND `44|RUE|ST ISIDORE`.**
  Subtilité : `44|RUE|ST ISIDORE` existait mais était **auto-fusé** dans
  `42|RUE|ST ISIDORE` (qui porte une **autre** copro, AD4688198 « L'ÉCRIN »,
  62 lots, **bgid distinct B5YZ**). 42 et 44 sont **2 bâtiments distincts** sur
  la même parcelle DH0137 — make_light a fusé 44→42 à tort. On **UN-FUSE 44**
  (clear `_fusion_auto`/`_fusion_cible`) pour qu'il devienne sa propre ancre RNC
  visible. Pas de double-comptage bgid (B5YZ ≠ S5D6).

### Trarieux — clé adresse `|RUE|TRARIEUX` (bgid SY4L-91Y9-KL8N, 1 log BDNB)
- **BAN reverse** des coords (`lon=4.886516&lat=45.745205`) → la voie est bien
  **Rue Trarieux 69003 Lyon** ; housenumbers les plus proches **72 / 74**
  (scores 0,9984 / 0,9979, coords quasi sur l'axe).
- **BDNB `rel_batiment_groupe_adresse?batiment_groupe_id=eq.bdnb-bg-SY4L-91Y9-KL8N`**
  → `cle_interop_adr = 69383_7115_00074` = **74 Rue Trarieux** (clé interop BAN
  autorité directe). Concordant avec le reverse (74 = le bâti, 72/74 alignés).
- **Verdict : n° = 74 → RENAME** la ligne adresse `|RUE|TRARIEUX` → `74|RUE|TRARIEUX`.
  `74|RUE|TRARIEUX` était **absent** du light → pas de collision, simple
  ré-étiquetage de la ligne (1 log BDNB, mono). `70` et `72` Rue Trarieux
  existent déjà (autres bgids), donc pas de fusion.

> Les 2 lookups ont abouti (réseau OK). Aucun DENY par défaut requis.

---

## ÉTAPE 2 — Les 10 dispositions finales

Script : **`scripts/fix_clemalformee_montchat.py`** (dry-run par défaut /
`--apply`, backup `.preclemalf.bak`, idempotent, repli gracieux, trace
`metadata._correctif_clemalformee_montchat`). Modèle direct = fix DL
clés-malformées + INJECT clone-based de `fix_alasseur_inject.py`.

| # | Clé malformée | Type | immat | Disposition finale | Cible |
|---|---|---|---|---|---|
| 1 | `\|RUE\|DAUPHINE` | copro | AC6769996 (10) | **REBIND** | `75\|RUE\|DAUPHINE` (= rebind DL identique, cohérence inter-secteur) |
| 2 | `\|\|TERRASSES DE MAREUIL 15…` | copro | AC7341035 (22) | **REBIND** | `15B\|RUE\|VILLEBOIS MAREUIL` (15 fusé→15B, **même bgid XRJV**, ancre visible) |
| 3 | `\|\|ROCHAIX 63…` | copro | AC8010274 (14) | **REBIND** | `63\|RUE\|PROFESSEUR ROCHAIX` |
| 4 | `\|\|VILLA FOUCAULD 12 A 20…` | copro | AC8318594 (34) | **INJECT + REBIND** | `12\|RUE\|JEANNE D ARC` (créée, clone `15\|RUE\|JEANNE D ARC` bgid 2HL4 ilot 113 ; RNC 34 = BDNB 34 exact) |
| 5 | `\|\|REVERSY 71…` | copro | AD3160348 (14) | **REBIND** | `71\|AVENUE\|LACASSAGNE` |
| 6 | `\|RUE\|ST ISIDORE` | copro | AD5117908 (39) | **REBIND + UN-FUSE** | `44\|RUE\|ST ISIDORE` (lookup ci-dessus) |
| 7 | `\|\|RESIDENCE D ARSONVAL 53…` | copro | AD7135940 (31) | **REBIND** | `53\|RUE\|PROFESSEUR ROCHAIX` |
| 8 | `\|\|TERRASSES LACASSAGNE 201 203…` | copro | AD9466327 (6) | **INJECT + REBIND** | `201\|AVENUE\|LACASSAGNE` (créée, clone `203\|AVENUE\|LACASSAGNE` bgid D13S ilot 172) |
| 9 | `\|RUE\|TRARIEUX` | adresse | — | **RENAME** | `74\|RUE\|TRARIEUX` (lookup ci-dessus) |
| 10 | `\|RUE\|CELLARD` | adresse | — | **DENY** | `_cles_invalides_montchat.json` (0 donnée : pas d'immat/bgid/coords/log) |

**Bilan opérations** : 6 REBIND + 2 INJECT + 1 RENAME + 1 DENY = **10/10**.
`skip = 0`. Re-run = entièrement idempotent (10× NOOP, parc Δ0).

**Écart vs plan initial (documenté, non forcé)** :
- #2 cible **`15B`** (et non `15`) car `15` est fusé dans `15B` (même bgid) —
  l'ancre **visible** est `15B`. Parc identique (même bgid), copro rendue.
- #6 : `44` existait mais fusé dans `42` (copro tierce, bgid distinct) → REBIND
  vers `44` **+ un-fuse** plutôt que vers `42` (qui porte déjà AD4688198).

**Propagation REBIND** (copro→adresse, si l'adresse ne l'a pas) :
`numero_immatriculation`, `nb_lots_habitation`, `taux_rotation`
(←`taux_rotation_5ans`), `classement_rotation`, `syndic`, `_syndic_src`.
L'adresse devient RNC → **badge implicite « Copropriété »**.

**INJECT** (clone-based) : nouvelle adresse clonée d'une voisine de la même voie
pour `batiment_groupe_id`/`longitude`/`latitude`/`code_iris`/`_ilot`/usage, puis
`cle`/`numero_immatriculation`/`nb_lots_habitation` posés,
`_bdnb_match='immat_inject_clemalf'`, `_coord_source='clone_inject_clemalf'`.

**Îlotage** : les 2 INJECT héritent du `_ilot` du clone (12 JEANNE D ARC → 113,
201 LACASSAGNE → 172) ; le RENAME conserve l'îlot existant (74 TRARIEUX → 219).
**Aucune relance de `_apply_ilot_kml_montchat.py` nécessaire** (0 adresse sans îlot).

---

## ÉTAPE 2b — Effet pipeline

### Pile rouge → 0 (hors DENY justifié)
- Clés malformées **10 → 1**. La seule restante = `|RUE|CELLARD`, **mise en
  DENY-list** (irrécupérable : aucune donnée). C'est donc **0 clé malformée
  réductible restante** ; 1 DENY justifié.

### Delta parc (NON-NEUTRE — attendu)
Les 8 copros rebindées/injectées étaient invisibles (`cle_adresse` orpheline) et
deviennent visibles → le parc augmente. **Source d'autorité = `renderSecteur()`
réel d'`index.html`** (via `test_render_secteur.js`) :

| Parc `secL` (renderSecteur réel) | valeur |
|---|---|
| **AVANT** (état `.preclemalf.bak`) | **15 769** |
| **APRÈS** (light patché) | **15 809** |
| **DELTA** | **+40** |

**Décomposition** (le delta n'égale PAS Σ lots = 170, car 6/8 cibles étaient
déjà des hr-actives **visibles contribuant leur log BDNB** ; le rebind ne fait
qu'appliquer la priorité RNC sur le même bgid) :

| Cible | BDNB avant | RNC après | Δ bgid |
|---|--:|--:|--:|
| 75 DAUPHINE (bgid 6E83) | 10 | 10 | +0 |
| **15B VILLEBOIS MAREUIL** (WMNE) | 10 | 22 | **+12** |
| 63 ROCHAIX (33C5) | 13 | 14 | +1 |
| 71 LACASSAGNE (187X) | 14 | 14 | +0 |
| **44 ST ISIDORE** (FVVN, un-fusé) | 12 | 39 | **+27** |
| 53 ROCHAIX (Q9RU) | 31 | 31 | +0 |
| 12 JEANNE D ARC (INJECT, clone bgid 2HL4 = 15/20) | 34 (déjà compté) | 34 | +0 |
| 201 LACASSAGNE (INJECT, clone bgid D13S = 203) | 6 (déjà compté) | 6 | +0 |
| **TOTAL** | | | **+40** |

Cohérent : 12 + 1 + 27 = +40. Le +27 sur 44 ST ISIDORE vient de l'**un-fuse**
(le bgid S5D6 ne contribuait que 12 log BDNB via 44B ; il passe à 39 lots RNC,
priorité RNC, pas de double-comptage car 44B partage le bgid donc est dédupliqué).

### Comptes
| | AVANT | APRÈS |
|---|--:|--:|
| Adresses (light) | 1399 | 1401 (+2 INJECT) |
| Copros immat visibles (modèle Python) | 585 | 593 (+8) |
| Clés malformées | 10 | 1 (DENY) |

### `test_render_secteur.js` — exit 0 sur DL ET Montchat
- **DL** (`SECTEUR=dauphine_lacassagne`, défaut) : `RESULTAT : OK`, exit **0**.
  Tous les asserts DL passent (Montbrillant B3, 70 injectées, parc 22 381,
  marché libre, hr-actifs 36). **DL non régressé** (fichier non touché).
- **Montchat** (`SECTEUR=montchat`) : `RESULTAT : OK`, exit **0**. renderSecteur
  ne lève pas, 0 double-rendu d'immat, parc `secL = 15 809` = réplique exacte de
  la règle 2-passes, B3 ignoré (gate DAUPH), hr-actifs 142.

---

## ÉTAPE 3 — Recouvrement frontière DL ↔ Montchat (READ-ONLY, rien dédupliqué)

Constat de chevauchement géographique (Rue Dauphiné, Av Lacassagne à cheval
entre les 2 secteurs). Comparaison `secteur_dauphine_lacassagne_light.json` ×
`secteur_montchat_light.json` (post-fix). **Aucune modification, aucune dédup.**

### (a) Copros communes (même `numero_immatriculation`) : **31**
```
AA2213171 LE CEDRE LUMIERE     AA2791176 SDC CARINAE          AA3708823 SDC LE BOUTON D'OR
AA4814810 LES PINS             AA6355408 2 RUE BARA            AA6892400 LE REBATEL - MS15801
AA7362809 LE JARDIN BARA       AA8663353 LE DOLPHIN 3          AB0832204 LE REBATEL
AB1648146 RESIDENCE 22 DAVID   AB1842756 LE DAUPHINE           AB2398634 60 lacassagne
AB9003328 VILLA DAUPHINE       AB9788415 SDC 48 AV LACASSAGNE  AB9797408 ZEN - MS169207
AC5718366 32 RUE DR REBATEL    AC6769996 75 RUE DU DAUPHINE    AC8216780 60 BIS AV LACASSAGNE
AC9350984 LE PAVILLON DU DAUPHIN  AD0186064 34 RUE DR REBATEL  AD0379297 SDC 141 DAUPHINE
AD5047121 SDC 77 DAUPHINE      AD5054531 SDC 131 DAUPHINE      AD5115928 SDC LES TERRASSES DU DAUPHINE
AD5267315 SDC 71 DAUPHINE      AD5288691 SDC 51BIS LACASSAGNE  AD6166722 SDC 0051 58 LACASSAGNE
AE3717733 VILLA FLEURY         AE8227266 HORIZON MONPLAISIR    AH1784180 84 rue du Dauphiné
AH6902480 83 DAUPHINE
```
> **Note** : `AC6769996` (notre rebind #1, « 75 RUE DU DAUPHINE ») apparaît dans
> les deux secteurs — cohérent, c'est le même immat à cheval DL/Montchat, rebindé
> à l'identique (`75|RUE|DAUPHINE`) des deux côtés.

### (b) Adresses communes (même `cle`) : **57**
| Voie | n | clés |
|---|--:|---|
| DAUPHINE | 22 | 71/75/77/79/83/84/89/93/97/99/115/117/123/125/131/135/137/139/141/143 + 84B/97B |
| LACASSAGNE (AVENUE) | 13 | 48/54/56/58/60/64/66/68 + 51B/58T/60B/64B/66B |
| DOCTEUR REBATEL | 8 | 2/8/12/14/20/32/36/44 |
| BARA | 4 | 2/11/12/14 |
| CARRY | 4 | 5/7/12/14 |
| DAVID | 2 | 22/24 |
| CONVENTION | 1 | 1 |
| GUILLOUD | 1 | 43 |
| MONTBRILLANT | 1 | 25 |
| ST MAXIMIN | 1 | 62 |

### TOTAL recouvrement frontière : **31 copros + 57 adresses communes**
Constat conforme au chevauchement attendu (axes Dauphiné / Lacassagne / Rebatel /
Bara / Carry sur la limite Montchat ↔ Dauphiné-Lacassagne). **Aucune dédup
effectuée** (chaque secteur reste autonome ; le double-comptage éventuel est un
sujet inter-secteur hors périmètre de cette manche).

---

*Aucun commit, aucun `git add`, aucun push. DL/MP et `index.html` intacts.*
