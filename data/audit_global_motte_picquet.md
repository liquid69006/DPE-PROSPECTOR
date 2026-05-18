# Audit global — Secteur La Motte-Picquet

**Croisement DVF × RNC × BDNB** — lecture seule, aucune donnée modifiée.

- Fichier audité : `data/secteur_motte_picquet_light.json`
- Généré (source) : 2026-05-18T19:27:49 — commune : Paris 7e + 15e (INSEE 75107 + 75115)
- Périmètre : 30 IRIS / 821 copropriétés / 1305 adresses
- Sources brutes : DVF `dvf_motte_picquet.json` (8322 lignes), RNC T3 2025, BDNB live

> Seuils d'alerte : 🟢 OK · 🟡 à surveiller · 🔴 anomalie

---

## AUDIT 1 — Cohérence DVF

### 1.1 Ventes brutes vs strictes (logement) par année

| Année | Brut (`ventes_par_an`) | Strict logement (`ventes_par_an_logement`) | Δ strict/brut | DVF brut métadonnée |
|---|--:|--:|--:|--:|
| 2021 | 761 | 581 | -23.7% | 1569 |
| 2022 | 827 | 640 | -22.6% | 2072 |
| 2023 | 727 | 524 | -27.9% | 1479 |
| 2024 | 685 | 510 | -25.5% | 1406 |
| 2025 | 781 | 585 | -25.1% | 1796 |
| **Total** | **3781** | **2840** | **-24.9%** | **8322** |

- Cohérence interne : Σ `ventes_par_an` = **3781** vs `nb_ventes_total` = **3781** → 🟢 identiques
- Cohérence interne : Σ `ventes_par_an_logement` = **2840** vs `nb_ventes_logement` = **2840** → 🟢 identiques
- Réduction strict vs brut : **-24.9%** (note métadonnée `_correctif_taux_logement` annonce 2840 vs 3781 = -24.9%).

**Cross-check DVF brut (fichier source `dvf_motte_picquet.json`)**

- Lignes DVF brutes : **8322** (= `nb_mutations_dvf` métadonnée 8322 → 🟢 OK)
- dont nature 'Vente' : 8191 · type local Appartement/Maison : 3573
- mutations distinctes (réf+disposition+parcelle) : ~3786
- Par année (brut fichier) : 2021=1569 · 2022=2072 · 2023=1479 · 2024=1406 · 2025=1796

> ⚠️ Le fichier DVF brut (8322 lignes) couvre Paris 7e/15e **avant** filtrage polygone/rattachement copro. Seules **3781** ventes sont rattachées à une adresse du secteur (écart 4541 = mutations hors-polygone, dépendances/commerces non rattachés, non géocodées). Comportement attendu, pas une perte de donnée.

### 1.2 Adresses avec / sans ventes

- Adresses avec ≥1 vente brute : **801** (61.4%)
- Adresses sans aucune vente brute : **504** (38.6%)
- Adresses avec ≥1 vente stricte (logement) : **746** (57.2%)
- Adresses brut>0 mais strict=0 (que dépendances/commerces) : **55**

### 1.3 Taux de rotation aberrants (> 50 %/an)

🟡 **5 adresse(s)** > 50 %/an — **artefact de dénominateur, pas une hyper-rotation réelle** :

| Adresse | IRIS | lots RNC | log BDNB | dénom. utilisé | ventes brut | taux brut | ventes log | taux strict |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| 18 RUE JUGE | 751155910 | — | 9 | BDNB=9 | 46 | 102.2 | 7 | 15.6 |
| 36 RUE MIOLLIS | 751155811 | — | 13 | BDNB=13 | 52 | 80.0 | 6 | 9.2 |
| 22 RUE DE LA FEDERATION | 751155918 | — | 1 | BDNB=1 | 4 | 80.0 | 4 | 80.0 |
| 28 RUE DUPLEIX | 751155915 | — | 1 | BDNB=1 | 4 | 80.0 | 4 | 80.0 |
| 18 RUE CEPRE | 751155811 | 47 | 1 | RNC | 3 | 1.3 | 3 | 60.0 |

> **Diagnostic** : 4/5 de ces adresses ont `nb_lots_habitation` null (hors-RNC, sans immatriculation) ou un `nb_log_bdnb` qui sous-compte grossièrement le bâti (ex. *18 RUE CÉPRÉ* : 47 lots RNC mais BDNB=1 logement → taux strict 60 %). Le taux %/an est alors calculé sur un dénominateur effondré (1 à 13) : le **numérateur (ventes) reste correct** et n'affecte ni les totaux ni la cohérence verticale, mais le **taux par adresse de ces ~5 cas est non fiable**. À traiter en filtrant `nb_lots_habitation>0` pour tout classement de rotation.

- Distribution taux brut (n=1125) : min 0.0 · médiane 1.7 · p90 5.8 · max 102.2 %/an

### 1.4 Concentration des ventes

- Top 5 adresses = **7.7%** du total · Top 10 = **11.4%** · Top 25 = **18.8%** · Top 50 = **27.9%**
- Indice Herfindahl (HHI) sur adresses : **32** (🟢 < 1500, marché fragmenté)
- Adresse la plus active : *78 AVENUE DE SUFFREN* — 76 ventes (2.0% du secteur), 320 lots

**Top 10 adresses par volume de ventes :**

| Adresse | IRIS | lots hab | ventes brut | taux %/an |
|---|---|--:|--:|--:|
| 78 AVENUE DE SUFFREN | 751155914 | 320 | 76 | 4.8 |
| 146 BOULEVARD DE GRENELLE | 751155912 | 316 | 62 | 3.9 |
| 15 RUE LAKANAL | 751155901 | 392 | 54 | 2.8 |
| 36 RUE MIOLLIS | 751155811 | None | 52 | 80.0 |
| 18 RUE JUGE | 751155910 | None | 46 | 102.2 |
| 80 RUE DE LA CROIX NIVERT | 751155901 | 41 | 35 | 17.1 |
| 96 AVENUE DE SUFFREN | 751155913 | 217 | 31 | 2.9 |
| 16 BOULEVARD GARIBALDI | 751155811 | 592 | 27 | 0.9 |
| 54 AVENUE DE LA MOTTE PICQUET | 751155914 | 79 | 25 | 6.3 |
| 23 RUE DU LAOS | 751155913 | None | 23 | 7.2 |

**Répartition des ventes par IRIS (top/bottom) :** voir AUDIT 5. Min IRIS = 34 ventes · max = 374 ventes · médiane = 226. 🟢 réparties (aucun IRIS ne domine anormalement).

---

## AUDIT 2 — Couverture RNC

### 2.1 Copros liées / non liées

- Copropriétés RNC dans le light : **821** (métadonnée `nb_coproprietes_rnc` = 835 → écart 14 : copros RNC hors-polygone ou fusionnées auto)
- Copros **liées** à ≥1 adresse du secteur (via `numero_immatriculation`) : **731** (89.0%)
- Copros **non liées** (présentes mais aucune adresse rattachée) : **90** (11.0%)
- Adresses **sans** `numero_immatriculation` (hors-RNC / non rattachées) : **564** sur 1305 (43.2%)
- Adresses avec immat **orphelin** (immat absent de la liste copros) : **2** 🟡 — immat injectés via passe hors-RNC/immat_fix (voir métadonnée correctifs)

### 2.2 Syndic nommé / non connu

- Syndic **nommé** : **679** (82.7%)
- Syndic **non connu** (`NON CONNU` / identité non partagée open data) : **142** (17.3%)
- Source du syndic (`_syndic_src`) : rnc=704 · rnic_live=117

### 2.3 Type de syndic (professionnel / bénévole / non connu)

⚠️ **Limite de donnée** : le light RNC ne porte **pas** de champ `type_syndic` (le fichier ANAH T3 distingue pro/bénévole/coopératif mais l'attribut n'a pas été propagé). Classification dérivée du libellé uniquement :

- *Non connu* : **142** (17.3%)
- *Bénévole* (libellé contient « BÉNÉVOLE ») : **0** → 🟡 aucun détecté : soit absence réelle, soit attribut non propagé (probable)
- *Professionnel présumé* (syndic nommé non bénévole) : **679** (82.7%)

**Top 10 syndics nommés :**

| Syndic | Nb copros |
|---|--:|
| CABINET REGY | 33 |
| CABINET PIERRE BONNEFOI SA | 29 |
| JEAN CHARPENTIER-SOPAGI SA | 20 |
| FONCIA PARIS RIVE GAUCHE | 19 |
| FONCIA PARIS RIVE DROITE | 19 |
| GERASCO | 18 |
| GRIFFATON ET MONTREUIL | 17 |
| ATRIUM GESTION PARIS 15 | 15 |
| UNION COMMERCIALE IMMOBILIERE | 15 |
| CABINET LOISELET PERE FILS ET DAIGREMONT | 12 |

### 2.4 `nb_lots_habitation` aberrant (0 lot ou > 500 lots)

- Copros avec **0 lot habitation** (ou null) : **0** 🟢
- Copros avec **> 500 lots habitation** : **2** 🟡

| Immat | Nom copro | lots hab | lots total | IRIS |
|---|---|--:|--:|---|
| AC6717193 | AFUL CABANEL | 905 | 1048 | 751155812 |
| AA0646265 | ARMONIAL I | 592 | 1726 | 751155811 |

- Distribution lots habitation : min 1 · médiane 23 · moyenne 33 · max 905 · Σ = 27050 (métadonnée `nb_lots_habitation_rnc` = 27350)

---

## AUDIT 3 — Cohérence BDNB

### 3.1 Couverture `batiment_groupe_id`

- Adresses **avec** `batiment_groupe_id` : **1305** (100.0%)
- Adresses **sans** BDNB : **0** (0.0%) 🟢
- Méthode de match (`_bdnb_match`) : immat=716 · num_voie=403 · gps=82 · immat_horsrnc_fix=58 · immat_fix=46

### 3.2 Incohérences `nb_log_bdnb` vs `nb_lots_habitation` (RNC), écart > 50 %

- Adresses comparables (RNC>0 et BDNB>0) : **737**
- Écart > 50 % : **102** (13.8% des comparables) 🟡
- Écart relatif médian |BDNB-RNC|/RNC : **15.4%**
- BDNB > RNC : 106 adr · BDNB = RNC : 107 adr · BDNB < RNC : 524 adr (RNC compte des lots juridiques, BDNB des logements physiques → BDNB souvent < RNC)

**Top 15 écarts les plus forts :**

| Adresse | IRIS | RNC lots hab | BDNB log | écart |
|---|---|--:|--:|--:|
| 10 RUE EDGAR FAURE | 751155916 | 17 | 117 | 588% |
| 16 RUE DE LA FEDERATION | 751155918 | 35 | 177 | 406% |
| 28 BOULEVARD GARIBALDI | 751155811 | 3 | 13 | 333% |
| None | 751155917 | 5 | 16 | 220% |
| 154 BOULEVARD DE GRENELLE | 751155912 | 35 | 89 | 154% |
| 11 RUE GEORGE BERNARD SHAW | 751155916 | 49 | 112 | 129% |
| 164 BOULEVARD DE GRENELLE | 751155912 | 1 | 2 | 100% |
| 18 RUE CEPRE | 751155811 | 47 | 1 | 98% |
| 16 RUE CEPRE | 751155811 | 47 | 1 | 98% |
| 17 RUE DE LA CROIX NIVERT | 751155810 | 38 | 1 | 97% |
| 11 RUE ALEXANDRE CABANEL | 751155812 | 905 | 27 | 97% |
| 3 BOULEVARD DE GRENELLE | 751155918 | 27 | 1 | 96% |
| 64 RUE DE LA FEDERATION | 751155917 | 43 | 84 | 95% |
| 24 AVENUE DE SUFFREN | 751155918 | 222 | 13 | 94% |
| 10 AVENUE EMILE ACOLLAS | 751072807 | 160 | 10 | 94% |

### 3.3 Répartition des classes DPE

| Classe | Nb adresses | % |
|---|--:|--:|
| C | 65 | 5.0% |
| D | 286 | 21.9% |
| E | 443 | 33.9% |
| F | 221 | 16.9% |
| G | 108 | 8.3% |
| (non renseigné / autre) | 182 | 13.9% |

- Passoires énergétiques (F+G) : **329** adresses (25.2%)
- DPE renseigné : **1123**/1305 (86.1%) 🟢

---

## AUDIT 4 — Cohérence géographique

### 4.1 Adresses par IRIS

- IRIS du secteur : **30** · IRIS portant ≥1 adresse : **17**
- Toutes les adresses ont un `code_iris` ∈ 30 IRIS du secteur : 🟢 OUI (1305/1305)
- IRIS du secteur **sans aucune adresse** : **13/30** — 🟢 attendu (voir diagnostic)

| code_iris | nom | type | part_iris % | part_secteur % | nature |
|---|---|:--:|--:|--:|---|
| 751155999 | Seine et Berges | D | 9.3 | 1.5 | Seine/quais (non résid.) |
| 751072812 | Champ de Mars | D | 3.0 | 0.8 | parc/équipement (non résid.) |
| 751072704 | École Militaire 4 | H | 4.4 | 0.4 | rognure de polygone (<0,1 %) |
| 751155808 | Necker 8 | H | 1.2 | 0.1 | rognure de polygone (<0,1 %) |
| 751072899 | Seine et Berges 3 | D | 0.6 | 0.1 | Seine/quais (non résid.) |
| 751072702 | École Militaire 2 | H | 0.1 | 0.0 | rognure de polygone (<0,1 %) |
| 751155814 | Necker 14 | H | 0.0 | 0.0 | rognure de polygone (<0,1 %) |
| 751155903 | Grenelle 3 | H | 0.1 | 0.0 | rognure de polygone (<0,1 %) |
| 751155920 | Grenelle 20 | A | 0.0 | 0.0 | IRIS activité (peu de copro) |
| 751155809 | Necker 9 | H | 0.0 | 0.0 | rognure de polygone (<0,1 %) |
| 751072707 | École Militaire 7 | A | 0.0 | 0.0 | IRIS activité (peu de copro) |
| 751155909 | Grenelle 9 | H | 0.3 | 0.0 | rognure de polygone (<0,1 %) |
| 751155905 | Grenelle 5 | H | 0.3 | 0.0 | rognure de polygone (<0,1 %) |

> **Diagnostic** : les 13 IRIS vides sont des **rognures de polygone** (part_secteur ≤ 1,5 %, souvent 0,0 %) issues de l'intersection WFS contours_iris × polygone secteur, ou des IRIS **non résidentiels** (Seine et berges, Champ de Mars, IRIS « activité » type A). Zéro copropriété y est **attendu** — ce n'est pas un défaut de rattachement. ⚠️ Conséquence cosmétique : le bandeau « **30 IRIS** » surévalue l'emprise réelle ; seuls **17 IRIS** portent des adresses (footprint résidentiel réel).

| Métrique | Valeur |
|---|--:|
| Adresses/IRIS — min | 9 |
| Adresses/IRIS — médiane | 79 |
| Adresses/IRIS — moyenne | 76.8 |
| Adresses/IRIS — max | 131 |

### 4.2 IRIS avec trop peu (< 5) ou trop d'adresses (> 200)

- IRIS < 5 adresses : **0** 🟢

- IRIS > 200 adresses : **0** 🟢

**Répartition complète adresses + copros par IRIS :**

| code_iris | nom IRIS | adresses | copros | part_secteur_pct |
|---|---|--:|--:|--:|
| 751155912 | Grenelle 12 | 131 | 80 | 7.3 |
| 751072807 | Gros Caillou 7 | 109 | 65 | 9.7 |
| 751155913 | Grenelle 13 | 105 | 55 | 7.4 |
| 751155812 | Necker 12 | 105 | 57 | 7.3 |
| 751155911 | Grenelle 11 | 101 | 77 | 5.4 |
| 751155918 | Grenelle 18 | 86 | 50 | 15.0 |
| 751155813 | Necker 13 | 86 | 68 | 5.2 |
| 751155915 | Grenelle 15 | 84 | 56 | 5.7 |
| 751155811 | Necker 11 | 79 | 42 | 4.5 |
| 751155917 | Grenelle 17 | 76 | 39 | 6.7 |
| 751155910 | Grenelle 10 | 72 | 49 | 3.1 |
| 751155914 | Grenelle 14 | 64 | 36 | 4.8 |
| 751155902 | Grenelle 2 | 64 | 49 | 3.9 |
| 751072703 | École Militaire 3 | 62 | 49 | 3.9 |
| 751155916 | Grenelle 16 | 37 | 12 | 4.3 |
| 751155901 | Grenelle 1 | 35 | 31 | 2.3 |
| 751155810 | Necker 10 | 9 | 6 | 0.6 |
| 751155808 | Necker 8 | 0 | 0 | 0.1 |
| 751072702 | École Militaire 2 | 0 | 0 | 0.0 |
| 751072704 | École Militaire 4 | 0 | 0 | 0.4 |
| 751155814 | Necker 14 | 0 | 0 | 0.0 |
| 751072899 | Seine et Berges 3 | 0 | 0 | 0.1 |
| 751155903 | Grenelle 3 | 0 | 0 | 0.0 |
| 751072812 | Champ de Mars | 0 | 0 | 0.8 |
| 751155999 | Seine et Berges | 0 | 0 | 1.5 |
| 751155920 | Grenelle 20 | 0 | 0 | 0.0 |
| 751155809 | Necker 9 | 0 | 0 | 0.0 |
| 751072707 | École Militaire 7 | 0 | 0 | 0.0 |
| 751155909 | Grenelle 9 | 0 | 0 | 0.0 |
| 751155905 | Grenelle 5 | 0 | 0 | 0.0 |

---

## AUDIT 5 — Taux de rotation global

### 5.1 Taux brut & strict par IRIS

Taux annuel = (Σ ventes 5 ans / 5) / Σ lots habitation × 100. *(lots = somme `nb_lots_habitation` des adresses RNC de l'IRIS ; les adresses hors-RNC sans lots ne contribuent pas au dénominateur → taux légèrement majoré sur ces IRIS).*

| code_iris | nom | adr | Σ ventes brut | Σ ventes strict | Σ lots | taux brut %/an | taux strict %/an | flag |
|---|---|--:|--:|--:|--:|--:|--:|---|
| 751072812 | Champ de Mars | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155901 | Grenelle 1 | 35 | 163 | 120 | 957 | 3.4 | 2.5 | 🟢 |
| 751155910 | Grenelle 10 | 72 | 206 | 147 | 1167 | 3.5 | 2.5 | 🟢 |
| 751155911 | Grenelle 11 | 101 | 245 | 183 | 2145 | 2.3 | 1.7 | 🟢 |
| 751155912 | Grenelle 12 | 131 | 374 | 293 | 2196 | 3.4 | 2.7 | 🟢 |
| 751155913 | Grenelle 13 | 105 | 332 | 221 | 1469 | 4.5 | 3.0 | 🟢 |
| 751155914 | Grenelle 14 | 64 | 212 | 153 | 1213 | 3.5 | 2.5 | 🟢 |
| 751155915 | Grenelle 15 | 84 | 222 | 197 | 1368 | 3.2 | 2.9 | 🟢 |
| 751155916 | Grenelle 16 | 37 | 80 | 51 | 433 | 3.7 | 2.4 | 🟢 |
| 751155917 | Grenelle 17 | 76 | 229 | 162 | 1695 | 2.7 | 1.9 | 🟢 |
| 751155918 | Grenelle 18 | 86 | 290 | 229 | 2605 | 2.2 | 1.8 | 🟢 |
| 751155902 | Grenelle 2 | 64 | 251 | 177 | 1420 | 3.5 | 2.5 | 🟢 |
| 751155920 | Grenelle 20 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155903 | Grenelle 3 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155905 | Grenelle 5 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155909 | Grenelle 9 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751072807 | Gros Caillou 7 | 109 | 210 | 161 | 1476 | 2.8 | 2.2 | 🟢 |
| 751155810 | Necker 10 | 9 | 34 | 29 | 204 | 3.3 | 2.8 | 🟢 |
| 751155811 | Necker 11 | 79 | 296 | 221 | 1557 | 3.8 | 2.8 | 🟢 |
| 751155812 | Necker 12 | 105 | 226 | 184 | 2474 | 1.8 | 1.5 | 🟢 |
| 751155813 | Necker 13 | 86 | 232 | 183 | 1461 | 3.2 | 2.5 | 🟢 |
| 751155814 | Necker 14 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155808 | Necker 8 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155809 | Necker 9 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751155999 | Seine et Berges | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751072899 | Seine et Berges 3 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751072702 | École Militaire 2 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751072703 | École Militaire 3 | 62 | 179 | 129 | 1132 | 3.2 | 2.3 | 🟢 |
| 751072704 | École Militaire 4 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| 751072707 | École Militaire 7 | 0 | 0 | 0 | 0 | — | — | ⚠️ pas de lots RNC |
| **TOTAL** | **secteur** | **1305** | **3781** | **2840** | **24972** | **3.03** | **2.27** | |

### 5.2 IRIS au taux aberrant

🟢 **Aucun IRIS** avec taux brut > 50 %/an.

### 5.3 Cohérence verticale (Σ IRIS == header)

| Indicateur | Σ par IRIS | Header global | Statut |
|---|--:|--:|---|
| Adresses | 1305 | 1305 | 🟢 OK |
| Ventes brutes | 3781 | 3781 | 🟢 OK |
| Ventes strictes | 2840 | 2840 | 🟢 OK |

- Σ ventes brutes par IRIS = **3781** = `nb_ventes_total` cumulé = **3781** → 🟢 cohérence verticale parfaite
- Note : la métadonnée `nb_mutations_dvf` (8322) compte les **lignes DVF brutes** (Paris 7e/15e entier) et n'est PAS censée égaler la somme rattachée au secteur (3781). Le « header » pertinent pour la cohérence verticale est le cumul des adresses, pas le compteur DVF brut.

---

## Synthèse & verdict

| Audit | Résultat | Verdict |
|---|---|:--:|
| 1 — DVF | Σ ventes brut=3781 (≡ Σ annuelle), strict=2840 (-24.9%), 5 adr >50%/an, HHI=32 | 🟡 |
| 2 — RNC | 731/821 copros liées, 142 syndic non connu (17%), 0 copro 0-lot, 2 copro >500 lots | 🟢 |
| 3 — BDNB | 1305/1305 avec bât. groupe (100%), 102 écarts >50% vs RNC, DPE renseigné 86% | 🟢 |
| 4 — Géo | 0 adresse hors-30-IRIS (1305/1305 ✓), 13 IRIS vides = rognures/non-résid. (footprint réel 17 IRIS), 0 IRIS <5 adr, 0 IRIS >200 adr | 🟢 |
| 5 — Rotation | taux brut secteur 3.03%/an, strict 2.27%/an, 0 IRIS aberrant, Σ IRIS≡header | 🟢 |

**Conclusion** — La cohérence verticale (Σ IRIS = header, Σ annuelle = total) est **parfaite** : aucune perte ni double-comptage. Les principaux points d'attention sont *structurels et documentés*, non des bugs : (a) le compteur DVF brut couvre Paris 7e/15e entier et ne doit pas être confondu avec le rattaché-secteur ; (b) l'absence de champ `type_syndic` (pro/bénévole non distinguable) ; (c) les écarts RNC↔BDNB reflètent lots juridiques vs logements physiques ; (d) ~5 adresses hors-RNC affichent un taux %/an artificiel (dénominateur effondré quand `nb_lots_habitation` est null ou `nb_log_bdnb` sous-compte) — à filtrer sur `nb_lots_habitation>0` pour tout classement ; (e) le bandeau « 30 IRIS » surévalue l'emprise (footprint résidentiel réel = 17 IRIS, 13 rognures non résidentielles).

---
*Rapport généré le 2026-05-18 — audit lecture seule, données non modifiées.*