# Diag Manche 0 — Cartographie de qualification MONTCHAT (READ-ONLY)

> **Tâche READ-ONLY.** Aucune modification de données ni de code, aucun commit,
> aucun `git add`. Seul fichier écrit = ce rapport.
> Source : `data/secteur_montchat_light.json` (1399 adresses, 633 copros,
> métadonnées : 646 copros RNC, 12 804 lots hab RNC, 16 IRIS, 2552 mutations DVF
> / 1051 distinctes). **KV Montchat = VIDE** → aucune adresse taguée. On
> cartographie donc des **CANDIDATS dérivés des données** (pas des tags posés).
> Référence méthodo : playbook DL (`PIPELINE.md` §7–§11, `data/diag_*dl*.md`).
>
> ⚠️ **Passes hors-RNC SKIPPÉES en Phase 2** (`fix_horsrnc_attribution` /
> `fix_invisible_insecteur_bgids` différées). Le périmètre hors-RNC est donc
> brut, non-réconcilié — c'est l'essentiel du travail des manches.

---

## Définitions retenues (alignées DL)

- **Copro immat (badge implicite « Copropriété »)** : `cle ∈ coproprietes[]`
  (par `cle_adresse`) **OU** `numero_immatriculation` non null
  (cf. `diag_migration_cible_dl.md` E3, `plan §204`).
- **Hors-RNC** : `cle ∉ coproprietes[]` **ET** pas d'`numero_immatriculation`.
- **copro_non_immat (levier BDNB, règle angle-mort MAJIC LOCAUX2)** : hors-RNC +
  `nb_log_bdnb > 1` + usage résidentiel + **0 PM MAJIC** =
  `copro_non_immat` *par définition* (PIPELINE §10). Le critère **0 PM MAJIC
  n'est PAS dérivable du light seul** → nécessite le parquet
  `C:\Users\Station 5\majic_locaux2_2025.parquet` (présent, 208 Mo) en manche
  dédiée. Ici on ne livre que le sous-critère light (`nb_log_bdnb>1` + résid +
  pas d'immat).
- **cible_0vente** : SIGNAL COMMERCIAL (PAS un type bâti) — copro **immatriculée**
  avec `nb_ventes_logement == 0` (`diag_migration_cible_dl.md`, PIPELINE §10).
- **Marché libre / strict** : exclut `social` + `bureaux`
  (`diag_strict_marche_libre_dl.md` E1). Non taguable ici (KV vide).
- **Clé malformée (pile rouge T3)** : `parse_cle(cle) is None` — numéro non
  extractible avant le 1er `|` (`scripts/pipeline.py` l.47-52, `build_pile_rouge`
  l.228-235). Deny-list = `_cles_invalides_<agence>.json` (manche E).
- **Orphelin d'îlot** : `_ilot ∈ {null, 'X'}` (sur rue / bord / non géocodable).

> **Preuve vs déduction** : tous les comptes ci-dessous sont des **lectures
> directes** du light (preuve). Les **types** social / mono / mixte / bureaux,
> et le tri copro_non_immat vs faux-matching, sont des **déductions** qui
> demandent MAJIC / BDNB live / œil métier en manche (non tranchés ici).

---

## ÉTAPE 1 — INVENTAIRE

### 1. Piles d'arbitrage

#### 1a. Pile ORANGE — hors-RNC « actives » (verdict requis)
**Critère exact** : `!copro` (hors-RNC) **ET** (`nb_ventes_logement > 0`
**OU** `nb_log_bdnb > 1`). Ce sont les adresses qui demanderaient un
verdict-scope (`bgid_confirmed` / `live_indetermine`) : copro non-immat réelle
**OU** faux-matching `_bdnb_match=num_voie` à re-pointer/re-fuser.

| Sous-pile | Compte |
|---|---|
| **ORANGE total** (hors-RNC actives) | **536** |
| dont `nb_ventes_logement > 0` | 200 |
| dont `nb_log_bdnb > 1` & usage **résidentiel** | 416 |
| dont `nb_log_bdnb > 1` & usage **non-résidentiel** (Tertiaire/dép.) | 28 |

Échantillon de clés : `95|AVENUE|LACASSAGNE`, `3|RUE|ST ISIDORE`,
`10|RUE|DOCTEUR BONHOMME`, `4|RUE|EST`, `101|AVENUE|LACASSAGNE`,
`11|RUE|DOMREMY`, `21|RUE|PROFESSEUR FLORENCE`, `34|RUE|AMIRAL COURBET`,
`64|AVENUE|LACASSAGNE`, `99|AVENUE|LACASSAGNE`, `110|COURS|ALBERT THOMAS`,
`158|COURS|ALBERT THOMAS`.

> **Lecture** : c'est la pile lourde. Sur le `_bdnb_match` global, **758
> adresses** sont matchées en `num_voie` (matching faible, candidat
> faux-matching à arbitrer) vs 595 en `immat`/`immat_fix` (matching fort).
> **Aucun** marqueur `correctif_*` ni `*_horsrnc_*` (à comparer aux ~100
> markers de DL post-manches) → confirme que **Montchat n'a reçu aucune passe
> de réconciliation hors-RNC**.

#### 1b. Pile ROUGE — clés malformées / invalides (`parse_cle is None`)
**Compte total : 10** (vs **1** sur DL après nettoyage). Deux familles :

| Forme | Source dans le light | n |
|---|---|---|
| `\|TYPE\|VOIE` (numéro vide avant le 1er `\|`) | 2 dans `adresses[]`, 2 dans `coproprietes[]` | 4 |
| `\|\|NOM_COPRO …` (nom de copro mis en clé, 2 `\|` vides) | `coproprietes[]` seulement | 6 |

Liste exacte (+ source) :
```
|RUE|CELLARD                                          adresses
|RUE|TRARIEUX                                         adresses
|RUE|DAUPHINE                                         copros
|RUE|ST ISIDORE                                       copros
||RESIDENCE D ARSONVAL 53 RUE DU PROFESSEUR ROCHAIX   copros
||REVERSY 71 AVENUE LACASSAGNE                        copros
||ROCHAIX 63 RUE DU PROFESSEUR ROCHAIX                copros
||TERRASSES DE MAREUIL 15 RUE VILLEBOIS MAREUIL       copros
||TERRASSES LACASSAGNE 201 203 AVENUE LACASSAGNE      copros
||VILLA FOUCAULD 12 A 20 RUE JEANNE D ARC             copros
```
- **2 dans `adresses[]`** (`|RUE|CELLARD`, `|RUE|TRARIEUX`) → surfacent comme
  lignes adresse au dashboard.
- **8 dans `coproprietes[]` seulement** → surfacent via `coproByCle` (immat sans
  ligne adresse résoluble). Les 6 `||NOM …` portent l'adresse réelle **dans le
  nom** (ex. « 53 RUE DU PROFESSEUR ROCHAIX ») → re-bind possible (pattern REBIND
  cle malformée DL, cf. MEMORY fix-dl-clemalformee-rebind) OU deny-list si SDC
  pré-scission irrécupérable.
- **Bug make_light Montchat** : extraction du numéro échoue (4 cas `|TYPE|VOIE`
  = num absent ; 6 cas = le pipeline a mis le **nom de copro** en `cle_adresse`
  au lieu de `NUM|TYPE|VOIE`). Même classe de bug que DL `|TYPE|VOIE`.
- **T1** (FA=True + ventes>0 sans `_fusion_cible`) : **0** (tous les
  `_fusion_auto`=214 ont un `_fusion_cible`=214 → fusion propre).

#### 1c. INDÉTERMINÉS (aucun levier de classification)
`!copro` **ET** `nb_log_bdnb == 0` **ET** `!dans_majic` :
- **Compte strict (nlog==0, !majic, !copro) : 19.**
- Compte large (nlog ≤ 1, !majic, !copro) : 87.
- Échantillon : `|RUE|CELLARD`, `27|RUE|GERMAIN DAVID`, `38|AVENUE|ACACIAS`,
  `5|RUE|GELAS`, `2|RUE|ANDRE`, `31B|RUE|FEUILLAT`, `13T|RUE|VIALA`,
  `67B|AVENUE|LACASSAGNE`, `45B|RUE|LOUIS`, `27B|RUE|GERMAIN DAVID`.
- Beaucoup de **suffixes B/T** (façades, FA-source probables — pattern DL
  `37B DAUPHINE`). Plusieurs recoupent la pile rouge (`|RUE|CELLARD`).

### 2. Classification (candidats, KV vide)

| Catégorie | n | % | Méthode de détection (light seul) |
|---|---|---|---|
| **copro immatriculée** | **622** | 44,5 % | `cle ∈ coproprietes[]` OU `numero_immatriculation` (badge implicite) |
| **copro_non_immat candidate** | **416** | 29,7 % | hors-RNC + `nb_log_bdnb>1` + usage résidentiel (✗ 0-PM-MAJIC = manche) |
| BDNB multi-log **non-résid** | 28 | 2,0 % | hors-RNC + `nb_log_bdnb>1` + usage Tertiaire/Dép. (probable bureaux/faux-match) |
| **non_qualifié** (reste) | **333** | 23,8 % | hors-RNC + `nb_log_bdnb ≤ 1` (mono/maison/indéterminé) |

Détail copro immat (622) : `in copros[] & immat`=584 · copro-only (dans
`coproprietes[]`, champ immat adresse vide)=2 · **immat-only** (immat sur
l'adresse mais **absente de `coproprietes[]`**)=36.

> **social / mono / mixte / bureaux — NON dérivables du light seul** :
> - Pas de champ `nb_lots_sociaux` ni `nb_log_marchand` dans le schéma Montchat
>   (ni DL) → **mixte/social non calculables** ici. Règle social_pct
>   (≥60 social / 20-60 mixte) = **manche MAJIC + syndic** (faux positifs
>   syndics FONCIA/REGIE/… à filtrer via `code_droit`, cf. plan §164-165).
> - `sci_proprietaire` = **True pour les 1399** (flag SCI Prospector global,
>   PAS un signal par-adresse) → **inutilisable** comme levier mono.
> - **mono** : déductible seulement via ratio MAJIC/BDNB ≥ 90 % + 1 SIREN privé
>   ≥ 80 % (cf. MEMORY fix-44-turbil) → **manche MAJIC** (parquet présent).
> - **bureaux** : proxy light = `usage_principal_bdnb == 'Tertiaire'` = **119
>   adresses** (à confirmer par tag métier ; n'est pas un type KV automatique).
> - `dans_majic` = True pour **1107 / 1399** (76 %) → la passe MAJIC couvrira la
>   grande majorité.

### 3. cible_0vente (signal commercial)
Copros immatriculées (622) avec `nb_ventes_logement == 0` :

| | n |
|---|---|
| **cible_0vente candidate (copro immat, 0 vente logement)** | **313** |
| dont `nb_ventes_total > 0` (activité non-logement : commerces/parkings) | 23 |
| dont `nb_ventes_total == 0` (aucune mutation du tout) | 290 |
| copros immat **avec** ventes logement (hors-cible) | 309 |

> Pas de split `active` / `isolée` dérivable du light seul (le split DL vient
> d'un scoring DVF / proximité, posé en manche). Le seul proxy disponible est
> « activité non-logement » (23) vs « zéro mutation » (290). **313** est un
> volume **4,5×** celui de DL (70 résiduel après manches F/G), cohérent avec un
> secteur **non encore qualifié** : la reclassification cible→type bâti sera la
> manche « œil métier » la plus volumineuse.

### 4. Orphelins d'îlot
`_ilot ∈ {null, 'X'}` : **41** (conforme aux ~41 annoncés).

| | n |
|---|---|
| `_ilot == 'X'` | 39 |
| `_ilot == null` | 2 |
| **avec coords** (lat+lon → re-géocodables / point-in-polygon ~25 m) | **39** |
| **sans coords** | **2** |

Concentration par voie : `ALBERT THOMAS` 9 · `DAUPHINE` 7 · `BARA` 4 ·
`CARRY` 4 · `LACASSAGNE` 4 · `CHATEAU` 3 · `DAVID` 2 · `FEUILLAT` 1 (+ divers).
→ Forte concentration sur les **axes de bord de zone** (Albert Thomas / Lacassagne
/ Dauphiné), typique des adresses snappées sur rue. 39/41 re-rattachables au plus
proche îlot (~25 m, règle plan §104) ; 2 sans coords = signalement manuel.

### 5. Hors-RNC (candidates `fix_horsrnc` / `fix_invisible`, passes différées)
`!copro` : **777** adresses au total.

| Nature (usage_principal_bdnb) | n |
|---|---|
| **résidentiel** (collectif/individuel) | 654 |
| Tertiaire | 100 |
| autre usage (Dépendance/Secondaire) | 5 |
| **sans usage BDNB** (`''`) | 18 |

> Ces 777 sont la **matière brute des passes Phase 2 différées**. Les 654
> résidentielles se scindent en : copro_non_immat réelles (à matérialiser) vs
> faux-matching `num_voie` à re-pointer/re-fuser (patterns Cambronne/Fondary/
> Éclatement DL). Les 18 sans usage rejoignent les indéterminés (1c).

### 6. BDNB résidentiel sans immat (candidates copro_non_immat — angle-mort)
`nb_log_bdnb > 1` **ET** pas d'immat :

| | n |
|---|---|
| `nb_log_bdnb>1` & hors-RNC (tous usages) | 444 |
| dont **usage résidentiel** (= copro_non_immat candidate) | **416** |

> **0-PM-MAJIC non dérivable du light** : la qualification définitive
> `copro_non_immat` exige le croisement `majic_locaux2_2025.parquet` (présent)
> pour confirmer « 0 propriétaire personne-morale » (copro de personnes
> physiques, RGPD-invisibles MAJIC). Le compte **416** est le sous-critère light
> (`nb_log_bdnb>1` + résid + 0 immat) ; il **borne par le haut** la pile
> copro_non_immat (certaines basculeront en social/mono/faux-match après MAJIC).

---

## ÉTAPE 2 — CONCLUSION

### Tableau de bord des piles (état initial Montchat, KV vide)

| Pile | Compte | Nature | Levier de résolution |
|---|---:|---|---|
| 🟠 **Orange** (hors-RNC actives) | **536** | verdict-scope `bgid_confirmed`/`live_indetermine` ; 758 `num_voie` faibles à trancher | détecteurs bgid/nom + arbitres + matching BDNB/parcelle |
| 🔴 **Rouge** (clés malformées) | **10** | 4× `\|TYPE\|VOIE` + 6× `\|\|NOM` (bug extraction make_light) | REBIND (nom→adresse) ou deny-list `_cles_invalides_montchat` |
| ⚪ **Indéterminés** (strict) | **19** | aucun levier (suffixes B/T, FA-source) | terrain / défaut non_qualifie |
| 🏢 **Copro immat** | **622** | badge implicite « Copropriété » | aucun tag (laisser vide, plan §204) |
| 📋 **copro_non_immat candidates** | **416** | BDNB résid sans immat | levier BDNB + **0-PM-MAJIC** (parquet) |
| 🎯 **cible_0vente candidates** | **313** | copro immat 0-vente-logement | signal commercial → `as.cible` (manche) |
| 🧭 **Orphelins d'îlot** | **41** | 39 'X' + 2 null ; 39 avec coords | point-in-polygon ~25 m / signalement |
| 🌐 **Hors-RNC total** | **777** | 654 résid · 100 tertiaire · 18 sans-usage | passes `fix_horsrnc`/`fix_invisible` (Phase 2 différée) |

### Proposition d'ordre des manches (ratio effort/résultat — calque DL)

> Principe DL : **trancher d'abord les piles d'arbitrage (rapides)**, puis les
> reclassifications de masse (œil métier), puis le matching/orphelins, puis le
> marché libre. Chaque manche = 1 GATE Yann (plan §170).

1. **Manche A — Deny-list / REBIND clés malformées (RAPIDE, 10 items).**
   `_cles_invalides_montchat.json`. Pour les 6 `||NOM …` : tenter REBIND
   (nom porte l'adresse, ex. ROCHAIX/REVERSY/TERRASSES) ; sinon deny-list.
   Pour les 4 `|TYPE|VOIE` : deny-list ou re-extraction num. → **effort faible**,
   ferme la pile rouge.

2. **Manche B — Passes hors-RNC différées (`fix_horsrnc` / `fix_invisible`).**
   Pré-requis structurel **avant** les arbitrages orange : matérialiser les
   copros non-immat réelles et purger les faux-matching `num_voie`. **777
   hors-RNC** en entrée → réduit mécaniquement la pile orange. Effort moyen
   (script + vérif parc), peu d'œil métier.

3. **Manche C — Verdict-scope orange (`_arbitres_montchat.json`).**
   Lancer `_detect_bgid_suspects` + `_detect_noms_ambigus` sur Montchat (jamais
   exécutés → pré-requis `pipeline.py`), puis arbitrer `bgid_confirmed` /
   `live_indetermine`. Volume = sous-ensemble des **536** orange survivant à la
   manche B (les 758 `num_voie` faibles concentrent l'effort). **Œil métier**,
   itératif, manche la plus longue avec la manche E.

4. **Manche D — Reclassification copro_non_immat via MAJIC (≤ 416 items).**
   Croisement parquet `majic_locaux2_2025.parquet` : `nb_log_bdnb>1` + 0 immat
   + **0 PM MAJIC** → `copro_non_immat`. Faux positifs syndics
   (FONCIA/REGIE/SAGNIMORTE/LYMMOBILIER/PIRON) à filtrer. **Œil métier modéré**
   (le script tranche 80-95 %, cf. `enrich_majic.py` DL).

5. **Manche E — cible_0vente → vrai type + `as.cible` (≤ 313 items).**
   Reclasser les 313 copros 0-vente vers leur vrai type bâti (la plupart
   `copro` RNC → laisser implicite) et poser le signal commercial sur
   `as.cible` (active/isolée). **Manche la plus volumineuse en œil métier**
   (4,5× DL). Peut être fusionnée avec D (même croisement MAJIC).

6. **Manche F — Classification social / mono / mixte / bureaux.**
   Règles `social_pct` (≥60 / 20-60) + ratio MAJIC/BDNB mono + Tertiaire→bureaux
   (119 candidats). Pas dérivable du light → **MAJIC + syndic + code_droit**.
   Œil métier, volume modéré.

7. **Manche G — Orphelins d'îlot (RAPIDE, 41 items).**
   Point-in-polygon ~25 m sur les 39 avec coords ; signalement des 2 sans
   coords. Quasi-mécanique.

8. **Manche H — Marché libre (repère strict).** Finalisation comme DL :
   exclusion social/bureaux, repère unique par ancre fusion-aware. Dépend des
   manches D-F. **Objectif final : piles orange/rouge à 0** (plan §168).

> **Manches rapides** : A (deny-list 10), G (orphelins 41). **Manches « œil
> métier »** : C (arbitrage orange), D (copro_non_immat ≤416), E (cible_0vente
> ≤313), F (classification). B est un pré-requis structurel (script, peu d'œil).

### Comparaison de volume Montchat vs DL (référence « propre »)

DL était **propre comme référence** après ses manches (jalon 4 scellé : orange 0,
rouge 0, vert 1385, cible_0vente résiduel 70). Lecture des **lights bruts** :

| Métrique | **Montchat (brut, KV vide)** | **DL (post-manches)** |
|---|---:|---:|
| Adresses | 1399 | 1385 |
| Copros immat (adresses) | 622 | 566 |
| Hors-RNC | **777** | 819* |
| Clés malformées (rouge) | **10** | **1** |
| Orphelins d'îlot | 41 | 39 |
| `_bdnb_match = num_voie` (faux-match candidats) | **758** | 604 |
| Marqueurs `correctif_*` / `*_horsrnc_*` | **0** | ~100+ (≈150 fixes manuels) |
| cible_0vente candidates | **313** | 70 (résiduel) |

\* *Le hors-RNC DL « résiduel » reste élevé en valeur brute mais a été
**entièrement arbitré** (chaque hors-RNC est soit copro_non_immat taguée, soit
fusée/re-pointée via les ~150 `correctif_*`). Montchat a 0 correctif → tout son
hors-RNC est **non traité**.*

**Effort total estimé** : Montchat part **à l'état brut** (équivalent DL
**avant** ses ~150 fixes terrain + manches D-G). Les volumes par pile sont du
**même ordre de grandeur** que DL en valeur absolue (secteur de taille
comparable), mais **100 % à qualifier** vs DL **0 % restant**. Les deux manches
de masse (C arbitrage orange ~500 + D/E reclassif ~300-400) concentrent
l'essentiel de l'effort « œil métier » ; A/G sont des manches courtes. Le
playbook DL (`enrich_majic.py`, `pipeline.py`, scan parcelle, side-files
secteur-agnostiques à repli gracieux) est **directement réutilisable** — c'est
ce qui rend l'effort tenable malgré le volume.

---

*Aucune modification effectuée hors ce rapport. Aucun commit, aucun git add.*
