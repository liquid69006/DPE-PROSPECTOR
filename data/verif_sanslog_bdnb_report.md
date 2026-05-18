# Adresses sans logements → rapprochement BDNB (live, lecture seule)

« Sans logements » = filtre dashboard exact (`!(nb_log_bdnb>0) && !(copro.nb_lots_habitation>0)`). Le snapshot local ne porte que le `nb_log` RNC (=0 ici) → API ouverte `batiment_groupe_ffo_bat` (nb_log fichiers fonciers, usage) + `batiment_groupe_dpe_representatif_logement` (DPE logement).

## Bilan

| Catégorie | Adresses |
|---|--:|
| **A** BDNB confirme des logements (donnée à corriger) | **0** |
| **B** voisin/​même bâti avec logements (doublon potentiel) | 2 |
| **C** BDNB confirme 0 logement (tertiaire/commerce/parking) | 124 |
| **D** inconnu (à qualifier manuellement) | 6 |

Total : 132 adresses sans logements, 84 bâtiments distincts. 0 sans bgid.

## A — BDNB confirme des logements (à mettre à jour)

_aucune_

## B — même `batiment_groupe_id` qu'une adresse AVEC logements (doublon structurel : entrée secondaire du même bâtiment)

| Adresse | bgid | adresse AVEC lgts (même bgid) | dist géo | usage |
|---|---|---|---|---|
| 3 COURS ALBERT THOMAS | `bdnb-bg-GB65-26FA-H5KS` | 5 COURS ALBERT THOMAS | 19 m | Tertiaire & Autres |
| 7 AVENUE LACASSAGNE | `bdnb-bg-XXU3-L2LW-69P8` | 6 AVENUE LACASSAGNE | 19 m | Tertiaire & Autres |

## C — BDNB confirme 0 logement (tertiaire/commerce/parking : normal) — échantillon 40

_124 adresses → bâtiments non résidentiels qualifiés par BDNB. Plusieurs n° de rue d'un même immeuble de bureaux/commerce = normal._

| Adresse | bgid | ffo nb_log | usage | type | niveaux | DPE |
|---|---|---|---|---|---|---|
| 10 RUE GANDOLIERE | `bdnb-bg-CXP2-X59F-KFA2` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE MEYNIS | `bdnb-bg-GFKS-DC3T-CRB1` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE ROGER BRECHAN | `bdnb-bg-7LYT-S1HN-R4SH` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE ST MARC | `bdnb-bg-FFBR-PB1L-5YFY` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE ST VICTORIEN | `bdnb-bg-1DBJ-3PC2-EVUG` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 10 RUE DES TEINTURIERS | `bdnb-bg-WQZA-TNRT-44JS` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 112 AVENUE FELIX FAURE | `bdnb-bg-95AH-FSBN-6WJ1` | 0 | Tertiaire & Autres | — | niv 14 | DPE non |
| 11 PASSAGE ROGER BRECHAN | `bdnb-bg-P8PR-P99U-EBPQ` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 11 RUE CLAUDIUS PIONCHON | `bdnb-bg-B7XN-JTJZ-HPB4` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 11 RUE GUILLOUD | `bdnb-bg-K1BT-FS4J-HZAJ` | 0 | Tertiaire & Autres | — | niv 8 | DPE non |
| 11 RUE ST MAXIMIN | `bdnb-bg-29R7-3GSE-U5WB` | 0 | Tertiaire & Autres | — | niv 5 | DPE non |
| 120 RUE ANTOINE CHARIAL | `bdnb-bg-AX8P-5ZM6-3A3B` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 121 RUE ANTOINE CHARIAL | `bdnb-bg-AX8P-5ZM6-3A3B` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 123 RUE ANTOINE CHARIAL | `bdnb-bg-AX8P-5ZM6-3A3B` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 124 RUE ANTOINE CHARIAL | `bdnb-bg-AX8P-5ZM6-3A3B` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 127 AVENUE FELIX FAURE | `bdnb-bg-D1FS-8QT9-MCVX` | 0 | Secondaire | — | niv 1 | DPE non |
| 12 RUE D AUBIGNY | `bdnb-bg-4AP3-MLCF-HZGV` | 0 | Tertiaire & Autres | — | niv 6 | DPE non |
| 148 RUE PAUL BERT | `bdnb-bg-WPVN-TN1Z-KE2S` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 14 RUE GENERAL MOUTON DUVERNET | `bdnb-bg-95AH-FSBN-6WJ1` | 0 | Tertiaire & Autres | — | niv 14 | DPE non |
| 14 RUE MAURICE FLANDIN | `bdnb-bg-KY6U-AHNX-6BKG` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 158 RUE PAUL BERT | `bdnb-bg-WPVN-TN1Z-KE2S` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 15 AVENUE LACASSAGNE | `bdnb-bg-FRYM-XEVY-K4QF` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 15 RUE MAURICE FLANDIN | `bdnb-bg-KY6U-AHNX-6BKG` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 160 RUE BARABAN | `bdnb-bg-TXNA-UR75-J51Y` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 16 AVENUE GEORGES POMPIDOU | `bdnb-bg-V4JK-AHTA-BJP3` | 0 | Tertiaire & Autres | — | niv 8 | DPE non |
| 16 RUE GENERAL MOUTON DUVERNET | `bdnb-bg-95AH-FSBN-6WJ1` | 0 | Tertiaire & Autres | — | niv 14 | DPE non |
| 16 RUE DE MONTBRILLANT | `bdnb-bg-S11S-Q6QJ-KLRK` | 0 | Tertiaire & Autres | — | niv 2 | DPE non |
| 17 RUE MAURICE FLANDIN | `bdnb-bg-KY6U-AHNX-6BKG` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 1 COURS ALBERT THOMAS | `bdnb-bg-BXLP-QJHG-4M7Z` | 0 | Tertiaire & Autres | — | niv 7 | DPE non |
| 1 RUE CARRY | `bdnb-bg-SQC2-49E9-C6J1` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 1 RUE GENERAL MOUTON DUVERNET | `bdnb-bg-CSCV-CK1X-T4EZ` | 0 | Tertiaire & Autres | — | niv 2 | DPE non |
| 276|RUE|PAUL BERT | `bdnb-bg-TLY3-3GD6-NUNJ` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 42 AVENUE GEORGES POMPIDOU | `bdnb-bg-CEJM-HEJT-UUUC` | 0 | Tertiaire & Autres | — | niv 8 | DPE non |
| 4 RUE CLAUDIUS PIONCHON | `bdnb-bg-B7XN-JTJZ-HPB4` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 55 RUE BARABAN | `bdnb-bg-BQNM-T5XQ-77LY` | 0 | Tertiaire & Autres | — | niv 6 | DPE non |
| 69 COURS ALBERT THOMAS | `bdnb-bg-7XDR-GYAZ-FWFR` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 69 RUE BARABAN | `bdnb-bg-5W9P-RL7A-RWW7` | 0 | Dépendance | — | niv 1 | DPE non |
| 71 RUE PAUL BERT | `bdnb-bg-WPVN-TN1Z-KE2S` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 89 RUE DE LA VILLETTE | `bdnb-bg-36F5-BHL7-ME1G` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |
| 8 RUE CLAUDIUS PIONCHON | `bdnb-bg-B7XN-JTJZ-HPB4` | 0 | Tertiaire & Autres | — | niv 1 | DPE non |

## D — inconnu (qualification manuelle)

| Adresse | bgid | ffo nb_log | usage | type | niveaux | DPE |
|---|---|---|---|---|---|---|
| 13 RUE CLAUDIUS PIONCHON | `bdnb-bg-W3VL-6KCU-S5RQ` | — | — | — | niv — | DPE non |
| 2 RUE D AUBIGNY | `bdnb-bg-8WK9-A5TB-955B` | — | — | — | niv — | DPE non |
| 4 RUE D AUBIGNY | `bdnb-bg-8WK9-A5TB-955B` | — | — | — | niv — | DPE non |
| 4 RUE DE LA VILLETTE | `bdnb-bg-9Q8J-7KPH-2P9U` | — | — | — | niv — | DPE non |
| 5 RUE DE LA VILLETTE | `bdnb-bg-9Q8J-7KPH-2P9U` | — | — | — | niv — | DPE non |
| 6 RUE DE LA VILLETTE | `bdnb-bg-9Q8J-7KPH-2P9U` | — | — | — | niv — | DPE non |
