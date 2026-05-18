# Adresses sans logements → rapprochement BDNB (live, lecture seule)

« Sans logements » = filtre dashboard exact (`!(nb_log_bdnb>0) && !(copro.nb_lots_habitation>0)`). Le snapshot local ne porte que le `nb_log` RNC (=0 ici) → API ouverte `batiment_groupe_ffo_bat` (nb_log fichiers fonciers, usage) + `batiment_groupe_dpe_representatif_logement` (DPE logement).

## Bilan

| Catégorie | Adresses |
|---|--:|
| **A** BDNB confirme des logements (donnée à corriger) | **0** |
| **B** voisin/​même bâti avec logements (doublon potentiel) | 4 |
| **C** BDNB confirme 0 logement (tertiaire/commerce/parking) | 57 |
| **D** inconnu (à qualifier manuellement) | 26 |

Total : 87 adresses sans logements, 60 bâtiments distincts. 10 sans bgid.

## A — BDNB confirme des logements (à mettre à jour)

_aucune_

## B — même `batiment_groupe_id` qu'une adresse AVEC logements (doublon structurel : entrée secondaire du même bâtiment)

| Adresse | bgid | adresse AVEC lgts (même bgid) | dist géo | usage |
|---|---|---|---|---|
| 11 RUE DE PRESLES | `bdnb-bg-4EHZ-51W9-YLYM` | 13 RUE DE PRESLES | 12 m | — |
| 3 AVENUE OCTAVE GREARD | `bdnb-bg-9HGZ-1AN9-9EDJ` | 15 AVENUE SUFFREN | 28 m | Tertiaire & Autres |
| 48 BOULEVARD GARIBALDI | `bdnb-bg-N3CE-YTEB-QRL6` | 46 BOULEVARD GARIBALDI | 10 m | Tertiaire & Autres |
| 70 AVENUE DE SUFFREN | `bdnb-bg-MC39-X7JB-H7H4` | 70B AVENUE SUFFREN | 0 m | Tertiaire & Autres |

## C — BDNB confirme 0 logement (tertiaire/commerce/parking : normal) — échantillon 40

_57 adresses → bâtiments non résidentiels qualifiés par BDNB. Plusieurs n° de rue d'un même immeuble de bureaux/commerce = normal._

| Adresse | bgid | ffo nb_log | usage | type | niveaux | DPE |
|---|---|---|---|---|---|---|
| 101 QUAI JACQUES CHIRAC | `bdnb-bg-9WBD-WZ5J-JGZG` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 102 BOULEVARD DE GRENELLE | `bdnb-bg-KMN1-AD27-BVJJ` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE DU COMMERCE | `bdnb-bg-8WWV-U8KH-X4VZ` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 11 AVENUE CHARLES FLOQUET | `bdnb-bg-RFG6-62K4-6X9Z` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 11 RUE DE L AVRE | `bdnb-bg-DUL7-MCJJ-Z9JU` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 11 RUE JUGE | `bdnb-bg-23BP-5MYG-NN2P` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 12 RUE TIPHAINE | `bdnb-bg-BKC7-4MP3-R26Q` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 132 BOULEVARD DE GRENELLE | `bdnb-bg-YP2W-RH3W-6V55` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 134 BOULEVARD DE GRENELLE | `bdnb-bg-64RL-SWJ7-1C4N` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 136 BOULEVARD DE GRENELLE | `bdnb-bg-64RL-SWJ7-1C4N` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 13 RUE JUGE | `bdnb-bg-5P8F-ABVD-F28T` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 140 BOULEVARD DE GRENELLE | `bdnb-bg-J48X-KQFK-9B5P` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 141 AVENUE DE SUFFREN | `bdnb-bg-V62Z-HLEN-EJVC` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 142 BOULEVARD DE GRENELLE | `bdnb-bg-5KQ4-PGDJ-X5D7` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 149 AVENUE DE SUFFREN | `bdnb-bg-GN29-NJCP-26BM` | 0 | Tertiaire & Autres | — | niv 2 | DPE non |
| 15 AVENUE CHARLES FLOQUET | `bdnb-bg-7WDC-QMY7-RRF6` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 15 RUE DUPLEIX | `bdnb-bg-X4K2-RJV1-R4A1` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 166 BOULEVARD DE GRENELLE | `bdnb-bg-U52X-T1NJ-6PY4` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 16 RUE JEAN REY | `bdnb-bg-ZHL6-JQ17-WPU6` | 0 | Tertiaire & Autres | — | niv 2 | DPE non |
| 1 AVENUE CHARLES FLOQUET | `bdnb-bg-MYV6-D78S-F5E1` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 1 RUE DE LOURMEL | `bdnb-bg-51LM-E65Q-8RZY` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 20 RUE JEAN REY | `bdnb-bg-S174-SFQV-PN5X` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 21 ALLEE MARGUERITE YOURCENAR | `bdnb-bg-27XU-NCLR-B72G` | — | Tertiaire | — | niv — | DPE non |
| 25 RUE DU COMMERCE | `bdnb-bg-UKZA-7G73-8VN6` | 0 | Tertiaire & Autres | — | niv 2 | DPE non |
| 29 RUE DE LA FEDERATION | `bdnb-bg-LZJA-XGNN-A4XL` | 0 | Tertiaire & Autres | — | niv 14 | DPE non |
| 2 RUE ALEXANDRE CABANEL | `bdnb-bg-BU7B-B9AM-VEPF` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 2 RUE CHASSELOUP LAUBAT | `bdnb-bg-1GJW-7MDQ-9RGA` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 3 IMPASSE GRISEL | `bdnb-bg-WL1J-3FSP-P5WX` | 0 | Tertiaire & Autres | — | niv 4 | DPE non |
| 3 RUE BARTHELEMY | `bdnb-bg-NRAP-BDVS-KRFN` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 3|RUE|CHASSELOUP LAUBAT | `bdnb-bg-1GJW-7MDQ-9RGA` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 3 RUE DE PONDICHERY | `bdnb-bg-GL8M-ZP7M-JP4T` | 0 | Tertiaire & Autres | — | niv 4 | DPE non |
| 3 SQUARE DESAIX | `bdnb-bg-58BB-RR3Q-XPUQ` | 0 | Tertiaire & Autres | — | niv 6 | DPE non |
| 59 AVENUE DE SEGUR | `bdnb-bg-FAWU-G662-QM38` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 59 RUE DU COMMERCE | `bdnb-bg-CT5D-HHME-FNQU` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 5 RUE DE L AVRE | `bdnb-bg-T3SU-2TJY-TYEC` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 6 RUE ALEXANDRE CABANEL | `bdnb-bg-BU7B-B9AM-VEPF` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 7 RUE DU GAL DE LARMINAT | `bdnb-bg-JW8K-UNYY-BAE9` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 8|AVENUE|CHARLES FLOQUET | `bdnb-bg-LQVN-CLSM-29MT` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 94 BOULEVARD DE GRENELLE | `bdnb-bg-BZ7D-Z6FZ-BLL6` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 9 RUE DE L EGLISE | `bdnb-bg-SJRT-PTDZ-KASE` | 0 | Tertiaire & Autres | — | niv 11 | DPE non |

## D — inconnu (qualification manuelle)

| Adresse | bgid | ffo nb_log | usage | type | niveaux | DPE |
|---|---|---|---|---|---|---|
| 102 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 104 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 106 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 10 RUE DU GAL DE CASTELNAU | `bdnb-bg-BH6F-JYLG-TQGF` | — | — | — | niv — | DPE non |
| 110 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 112 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 114 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 149 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 161 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 163 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 1|IMPASSE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 24 RUE DE PRESLES | `bdnb-bg-15NR-3HJJ-GNFF` | — | — | — | niv — | DPE non |
| 35 RUE DE L EGLISE | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 3|IMPASSE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 45|RUE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 5|IMPASSE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 5 RUE DE L EGLISE | `bdnb-bg-XHH7-SYZY-QSFQ` | — | — | — | niv — | DPE non |
| 67|QUAI|JACQUES CHIRAC | `None` | — | — | — | niv — | DPE non |
| 6|RUE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 75|RUE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 7|RUE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 85|RUE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 8|IMPASSE|EGLISE | `None` | — | — | — | niv — | DPE non |
| 8 RUE DE L EGLISE | `bdnb-bg-QNR9-N4KK-K8A1` | — | — | — | niv — | DPE non |
| 8 RUE DU GAL DE CASTELNAU | `bdnb-bg-BH6F-JYLG-TQGF` | — | — | — | niv — | DPE non |
| 9002 METRO DUPLEIX | `bdnb-bg-KA9V-XPBP-FSXH` | — | — | — | niv — | DPE non |
