# Audit hors-RNC + ventes DVF — secteur motte_picquet

Lecture seule. Cible = prédicat *Hors-RNC actifs* de renderSecteur (non fusionnée, clé ≠ cle_adresse copro, sans immat, `nb_ventes_logement>0`).

> **Lecture critique.** Une cible n'est **sûrement** rattachable que si l'identité est *forte* : immat via BDNB `rel_batiment_groupe_rnc`, **ou** variante orthographique exacte de `cle_adresse`, **ou** même `batiment_groupe_id` que la copro (même bâtiment → parc-neutre, classe des 7 déjà appliquées). Les autres (proximité GPS seule, match sur nom/adresse libre, RNC live) sont des **pistes à confirmer manuellement** : les appliquer en masse **détruit du parc** (ce sont des bâtiments DISTINCTS proches d'une copro, dont on retirerait le stock BDNB réel sans que la copro le gagne).

## Bilan

| Indicateur | Valeur |
|---|--:|
| Cibles hors-RNC + ventes | **53** |
| → **A-fort** (rattachable sûr, parc-sûr) | **23** |
| → A-faible (piste, confirmation manuelle) | 25 |
| → B (monopropriété / non immatriculée) | **5** |
| Ventes-log à relocaliser — A-fort | **94** |
| Ventes-log — A-faible (non sûr) | 48 |
| **Parc A-fort seul** : 29004 → 28926 | **-78** (23 modélisés) |
| Parc A-fort+faible (illustre la destruction) : 29004 → 28581 | -423 |

### Répartition A par voie de résolution (force)

| Étape | n | force |
|---|--:|---|
| c_gps | 25 | weak |
| a_bdnb | 21 | strong |
| b_norm | 2 | strong |

### Répartition A par mécanisme

| Mécanisme | n |
|---|--:|
| ALIAS_RNC miroir bgid | 27 |
| ALIAS_RNC meme bgid (parc-neutre) | 19 |
| RE-POINT (ancre fusionnee dans la cible) | 2 |

## Top 10 A-FORT par ventes-logement à relocaliser

| Adresse (cle) | v_log | v_tot | via | immat | copro | syndic | lots | mécanisme |
|---|--:|--:|---|---|---|---|--:|---|
| `23|RUE|LAOS` | 16 | 23 | a_bdnb | AA9613753 | SDC DU 21 23 25 RUE DU LAO | GRIFFATON & CO | 112 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|RUE|GUESCLIN` | 8 | 13 | a_bdnb | AB1748391 | Résidence Du Guesclin | URBANIA VAL D OUEST | 104 | RE-POINT (ancre fusionnee dans la cible) |
| `3|RUE|CAPT SCOTT` | 8 | 11 | a_bdnb | AF6894638 | SDC 1 Capitaine Scott | CABINET IFNOR | 27 | ALIAS_RNC meme bgid (parc-neutre) |
| `18|RUE|JUGE` | 7 | 46 | a_bdnb | AC4170221 | SDC 19 RUE JUGE | FONCIA PARIS RIVE GA | 10 | ALIAS_RNC meme bgid (parc-neutre) |
| `156|BOULEVARD|GRENELLE` | 6 | 6 | a_bdnb | AB1105360 | PARIS MOTTE PICQUET GRENEL | non connu | 35 | RE-POINT (ancre fusionnee dans la cible) |
| `3|AVENUE|CHAMPAUBERT` | 6 | 6 | a_bdnb | AB6311765 | SDC 80 SUFFREN - 2 CHAMPAU | CABINET MDA IMMO | 29 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|SQUARE|DESAIX` | 6 | 6 | a_bdnb | AC2394427 | SDC 10 SQUARE DESAIX | non connu | 14 | ALIAS_RNC meme bgid (parc-neutre) |
| `39|RUE|FONDARY` | 4 | 5 | a_bdnb | AB4199527 | SDC 39-41 RUE FONDARY 7501 | CABINET CITEAU | 49 | ALIAS_RNC meme bgid (parc-neutre) |
| `47|BOULEVARD|GARIBALDI` | 4 | 5 | a_bdnb | AA6084305 | GARIBALDI - PARIS 15 | S.T.B. GESTION - IMM | 27 | ALIAS_RNC meme bgid (parc-neutre) |
| `4|RUE|GAL DE CASTELNAU` | 4 | 4 | a_bdnb | AB1024181 | SDC 5 RUE DE LA CAVALERIE | GERASCO | 24 | ALIAS_RNC meme bgid (parc-neutre) |

## A-FORT — rattachables sûrs (toutes)

| cle | v_log | via | immat | anchor | copro | lots | mécanisme |
|---|--:|---|---|---|---|--:|---|
| `23|RUE|LAOS` | 16 | a_bdnb | AA9613753 | `21|RUE|LAOS` | SDC DU 21 23 25 RUE DU L | 112 | ALIAS_RNC meme bgid (parc-neutre) |
| `3|RUE|CAPT SCOTT` | 8 | a_bdnb | AF6894638 | `1|RUE|CAPITAINE SCOTT` | SDC 1 Capitaine Scott | 27 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|RUE|GUESCLIN` | 8 | a_bdnb | AB1748391 | `3|PASSAGE|GUESCLIN` | Résidence Du Guesclin | 104 | RE-POINT (ancre fusionnee dans la cible) |
| `18|RUE|JUGE` | 7 | a_bdnb | AC4170221 | `19|RUE|JUGE` | SDC 19 RUE JUGE | 10 | ALIAS_RNC meme bgid (parc-neutre) |
| `156|BOULEVARD|GRENELLE` | 6 | a_bdnb | AB1105360 | `154|BOULEVARD|GRENELLE` | PARIS MOTTE PICQUET GREN | 35 | RE-POINT (ancre fusionnee dans la cible) |
| `3|AVENUE|CHAMPAUBERT` | 6 | a_bdnb | AB6311765 | `80|AVENUE|SUFFREN` | SDC 80 SUFFREN - 2 CHAMP | 29 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|SQUARE|DESAIX` | 6 | a_bdnb | AC2394427 | `10|SQUARE|DESAIX` | SDC 10 SQUARE DESAIX | 14 | ALIAS_RNC meme bgid (parc-neutre) |
| `39|RUE|FONDARY` | 4 | a_bdnb | AB4199527 | `41|RUE|FONDARY` | SDC 39-41 RUE FONDARY 75 | 49 | ALIAS_RNC meme bgid (parc-neutre) |
| `47|BOULEVARD|GARIBALDI` | 4 | a_bdnb | AA6084305 | `49|BOULEVARD|GARIBALDI` | GARIBALDI - PARIS 15 | 27 | ALIAS_RNC meme bgid (parc-neutre) |
| `4|RUE|GAL DE CASTELNAU` | 4 | a_bdnb | AB1024181 | `5|RUE|CAVALERIE` | SDC 5 RUE DE LA CAVALERI | 24 | ALIAS_RNC meme bgid (parc-neutre) |
| `11|RUE|GAL DE LARMINAT` | 3 | b_norm(cle_adresse) | AC8648685 | `11|RUE|GENERAL DE LARMINAT` | SDC 11 RUE DU GENERAL DE | 26 | ALIAS_RNC miroir bgid |
| `1|RUE|JOSE MARIA DE HEREDIA` | 3 | a_bdnb | AH2463305 | `67|AVENUE|SEGUR` | SEGUR AVENUE 67 | 15 | ALIAS_RNC meme bgid (parc-neutre) |
| `3|RUE|GAL DE CASTELNAU` | 3 | a_bdnb | AI7024987 | `4|RUE|GENERAL DE CASTELNAU` | DU GENERAL DE CASTELNAU  | 28 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|RUE|GAL DE LARMINAT` | 3 | a_bdnb | AA3229176 | `9|RUE|GENERAL DE LARMINAT` | SDC 9 rue Général Larmin | 16 | ALIAS_RNC meme bgid (parc-neutre) |
| `10|RUE|DUPLEIX` | 2 | a_bdnb | AA5614235 | `11|RUE|DUPLEIX` | SDC 9-11 DUPLEIX | 73 | ALIAS_RNC meme bgid (parc-neutre) |
| `27|RUE|FREMICOURT` | 2 | a_bdnb | AB3441680 | `28|RUE|FREMICOURT` | 28 rue Fremicourt | 16 | ALIAS_RNC meme bgid (parc-neutre) |
| `2|RUE|GAL DE LARMINAT` | 2 | a_bdnb | AD0541896 | `4|RUE|GENERAL DE LARMINAT` | 4 LARMINAT - MS38509 | 15 | ALIAS_RNC meme bgid (parc-neutre) |
| `3|PLACE|CAMBRONNE` | 2 | a_bdnb | AB5809108 | `6|PLACE|CAMBRONNE` | SDC 6 CAMBRONNE | 19 | ALIAS_RNC meme bgid (parc-neutre) |
| `155|AVENUE|SUFFREN` | 1 | a_bdnb | AI4207031 | `12|RUE|BELLART` | SDC SUFFREN 155 | 9 | ALIAS_RNC meme bgid (parc-neutre) |
| `1||CITE THURE` | 1 | a_bdnb | AI8720518 | `132|RUE|THEATRE` | SDC 132 rue du Théâtre e | 6 | ALIAS_RNC meme bgid (parc-neutre) |
| `6|RUE|GAL DE LARMINAT` | 1 | a_bdnb | AA7531452 | `6|RUE|GENERAL DE LARMINAT` | DU GENERAL DE LARMINAT 6 | 9 | ALIAS_RNC meme bgid (parc-neutre) |
| `7|RUE|GAL DE CASTELNAU` | 1 | a_bdnb | AC0121202 | `5|RUE|GENERAL DE CASTELNAU` | 5 rue du General de Cast | 20 | ALIAS_RNC meme bgid (parc-neutre) |
| `8|RUE|GAL DE LARMINAT` | 1 | b_norm(cle_adresse) | AA9446949 | `8|RUE|GENERAL DE LARMINAT` | 8 RUE DU GENERAL LARMINA | 41 | ALIAS_RNC miroir bgid |

## A-FAIBLE — pistes (confirmation manuelle, NON applicables en masse)

| cle | v_log | via | immat | anchor | copro | lots |
|---|--:|---|---|---|---|--:|
| `26|BOULEVARD|GARIBALDI` | 6 | c_gps(13m) | AD5922125 | `28|BOULEVARD|GARIBALDI` | SDC 26/28 BD GARIBALDI | 3 |
| `10|RUE|PERIGNON` | 5 | c_gps(20m) | AA9850447 | `7|RUE|PERIGNON` | SDC du 7 rue Pérignon 75 | 41 |
| `13|RUE|CARRIER BELLEUSE` | 4 | c_gps(14m) | AD4548764 | `10|RUE|CARRIER BELLEUSE` | SDC CARRIER-BELLEUSE | 17 |
| `22|RUE|FEDERATION` | 4 | c_gps(13m) | AA0398420 | `20|RUE|FEDERATION` | LE SAINT SAENS | 500 |
| `11||CITE THURE` | 3 | c_gps(9m) | AE0226167 | `6||CITE THURE` | SDC 6 CITE THURE | 17 |
| `55|RUE|COMMERCE` | 3 | c_gps(20m) | AI0729426 | `51|RUE|COMMERCE` | SDC 51 rue du Commerce P | 8 |
| `8|RUE|CROIX NIVERT` | 3 | c_gps(11m) | AD3295243 | `6|RUE|CROIX NIVERT` | SDC 6 RUE DE LA CROIX NI | 8 |
| `14|RUE|TIPHAINE` | 2 | c_gps(12m) | AC6572218 | `11B|RUE|TIPHAINE` | Syndicat des Copropriéta | 14 |
| `7|RUE|HUMBLOT` | 2 | c_gps(13m) | AC8844789 | `5|RUE|HUMBLOT` | SDC 5 Humblot | 13 |
| `11|RUE|FALLEMPIN` | 1 | c_gps(9m) | AC0962894 | `13|RUE|FALLEMPIN` | 13 RUE FALLEMPIN | 36 |
| `128|AVENUE|SUFFREN` | 1 | c_gps(29m) | AC0762161 | `120|AVENUE|SUFFREN` | 120 AVENUE DE SUFFREN | 46 |
| `147|AVENUE|SUFFREN` | 1 | c_gps(19m) | AB8773814 | `145|AVENUE|SUFFREN` | 145 AVENUE DE SUFFREN | 56 |
| `15|RUE|LETELLIER` | 1 | c_gps(11m) | AA5189691 | `13|RUE|LETELLIER` | 13 rue letellier | 33 |
| `16|RUE|VIOLET` | 1 | c_gps(13m) | AB2931673 | `18|RUE|VIOLET` | SDC 18 VIOLET | 34 |
| `19|RUE|FALLEMPIN` | 1 | c_gps(6m) | AG8297707 | `21|RUE|FALLEMPIN` | SDC 3 VILLA DE GRENELLE | 19 |
| `21|AVENUE|CHARLES FLOQUET` | 1 | c_gps(22m) | AB3748845 | `19|AVENUE|CHARLES FLOQUET` | 19 Avenue Charles Floque | 25 |
| `2|RUE|BUENOS AIRES` | 1 | c_gps(14m) | AD4111738 | `1|RUE|BUENOS AYRES` | 1 RUE DE BUENOS AYRES | 13 |
| `4|RUE|BUENOS AIRES` | 1 | c_gps(14m) | AB3659166 | `3|RUE|BUENOS AYRES` | BUENOS AYRES-3 J Y | 30 |
| `51|RUE|FEDERATION` | 1 | c_gps(14m) | AA3469731 | `60|RUE|FEDERATION` | SDC 60 FEDERATION | 5 |
| `55|AVENUE|SUFFREN` | 1 | c_gps(19m) | AH7248073 | `57|AVENUE|SUFFREN` | SDC 57 SUFFREN | 81 |
| `55|RUE|FEDERATION` | 1 | c_gps(16m) | AD9092834 | `64|RUE|FEDERATION` | SDC 64-66-68-70 Fédérati | 43 |
| `6|RUE|ALASSEUR` | 1 | c_gps(14m) | AA3169430 | `4|RUE|ALASSEUR` | SDC 4 rue Alasseur | 27 |
| `6|RUE|BARTHELEMY` | 1 | c_gps(11m) | AB8058877 | `8|RUE|BARTHELEMY` | 8 RUE BARTHELEMY | 18 |
| `91|RUE|FONDARY` | 1 | c_gps(19m) | AA4793600 | `80|RUE|FONDARY` | SDC 80 rue Fondary | 9 |
| `9|RUE|LOURMEL` | 1 | c_gps(14m) | AA2385763 | `11|RUE|LOURMEL` | SDC LOURMEL & JUGE - 750 | 163 |

## Cibles B (structurellement hors-RNC)

| cle | v_log | v_tot | nb_log_bdnb | usage | dernier essai |
|---|--:|--:|--:|---|---|
| `163|AVENUE|SUFFREN` | 2 | 2 | 14 | Résidentiel collectif | d_rnc_live |
| `16|AVENUE|LOWENDAL` | 2 | 3 | 27 | Résidentiel collectif | d_rnc_live |
| `2|RUE|CEPRE` | 1 | 1 | 11 | Résidentiel collectif | d_rnc_live |
| `71|QUAI|JACQUES CHIRAC` | 1 | 1 | 15 | Résidentiel collectif | d_rnc_live |
| `83|BOULEVARD|GRENELLE` | 1 | 1 | 31 | Résidentiel collectif | d_rnc_live |