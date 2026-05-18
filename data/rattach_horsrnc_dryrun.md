# ÉTAPE 4 — rattachabilité des copros invisibles (dry-run, lecture seule)

Réplique la dedup parc exacte de `renderSecteur()` (clé `bg:<bgid>`, valeur = Σ lots RNC des copros du bâtiment sinon `nb_log_bdnb`). Aucune écriture.

## Bilan

| Verdict | Copros×bgid | Sens |
|---|--:|---|
| **PROPRE** | 31 | bâti porté uniquement par des adresses hors-RNC : rattacher remplace `nb_log_bdnb` par les lots RNC (même clé `bg:`, **pas de double-comptage**) |
| **DÉJÀ-COMPTÉ** | 0 | un sibling RNC déjà visible occupe le même bâtiment : le bâti est déjà compté, rattacher **sommerait** les lots (inflation) — satellite/jumelle |
| **COLLISION-CLE** | 0 | `cle_adresse` déjà prise |

Lots RNC rattachables proprement : **1177** (30 copros).

## PROPRE — rattachables sans collision ni double-comptage

| Copro (immat) | nom | cle_adresse | lots | bgid | adresses hors-RNC du bâti | sibling VISIBLE (→ déjà compté) | parc bg av.→ap. |
|---|---|---|--:|---|---|---|---|
| AA0012898 | ATRIUM SISLEY | `7B|RUE|PROFESSEUR PAUL SISLEY` | 225 | `bdnb-bg-68CY-P7TQ-TZ2P` | 11 RUE PROFESSEUR PAUL SISLEY<br>9 RUE PROFESSEUR PAUL SISLEY<br>7 RUE PROFESSEUR PAUL SISLEY | — | 229→225 |
| AD5268305 | BRICKS 1 | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | 98 | `bdnb-bg-NHQQ-8MZ7-KS1W` | 20 AVENUE LACASSAGNE | — | 97→98 |
| AG1556893 | BRICKS 2 | `24||ET 24 BIS AVENUE LACASSAGNE` | 64 | `bdnb-bg-WLXU-6YKR-D8DU` | 24 AVENUE LACASSAGNE<br>23 AVENUE LACASSAGNE<br>26 AVENUE LACASSAGNE | — | 64→64 |
| AA2505634 | SAINT MARC I | `42A||50 RUE ST MAXIMIN` | 63 | `bdnb-bg-MYUH-YTYU-45YJ` | 41 RUE ST MAXIMIN | — | 64→63 |
| AB6211445 | LE PRIVILEGE MONTBRILLAN | `9B|RUE|MONTBRILLANT` | 59 | `bdnb-bg-9MYW-M2VT-GSQE` | 9 RUE DE MONTBRILLANT | — | 58→59 |
| AC5748488 | SDC LE MILLENIUM | `12T|RUE|GUILLOUD` | 59 | `bdnb-bg-MXAK-H6X5-46X1` | 12 RUE GUILLOUD | — | 59→59 |
| AB2460335 | TERRASSES ET VILLAS ST M | `1|RUE|ROSSAN` | 53 | `bdnb-bg-6J3V-PN4E-7QWG` | 12|RUE|ST MAXIMIN<br>14 RUE ST MAXIMIN | — | 31→53 |
| AB5872536 | SDC LA FERRANDIERE | `8T|RUE|NAZARETH` | 49 | `bdnb-bg-4NPE-6GZX-QJ7R` | 8 RUE DE NAZARETH | — | 50→49 |
| AC7505134 | SDC SDC LE SISLEY | `30||30B R DU PROFESSEUR PAUL SISLEY` | 43 | `bdnb-bg-PTBZ-QHYH-Y2WN` | 30 RUE PROFESSEUR PAUL SISLEY | — | 45→43 |
| AA2730372 | SDC LE PRESIDENT | `170|AVENUE|FELIX FAURE` | 40 | `bdnb-bg-EC36-CQJW-PMK3` | 168 AVENUE FELIX FAURE | — | 39→40 |
| AA7891641 | RESIDENCE LE PARC VILLON | `10|RUE|VILLON` | 34 | `bdnb-bg-AHXA-TMQQ-QT6N` | 12 RUE DE VILLON | — | 35→34 |
| AD3386570 | SDC VILLA SYRACUSE | `7||PTR ST EUSEBE` | 34 | `bdnb-bg-UWK7-TY35-KUDK` | 209 AVENUE FELIX FAURE | — | 33→34 |
| AG6298160 | LE SPHINX | `41|COURS|ALBERT THOMAS 24 RUE DES TUILIERS` | 34 | `bdnb-bg-FCLN-D7V1-1RVN` | 41 COURS ALBERT THOMAS | — | 33→34 |
| AB1910728 | 20 TER RUE GUILLOUD | `20T|RUE|GUILLOUD` | 32 | `bdnb-bg-212B-J3A4-DL3G` | 20 RUE GUILLOUD | — | 26→32 |
| AB4364022 | 3eme AVENUE - MS34651 | `296|RUE|PAUL BERT` | 31 | `bdnb-bg-MNMB-7F9F-2TDS` | 298 RUE PAUL BERT | — | 31→31 |
| AH8741316 | PAUL BERT MANUFACTURE | `220|RUE|PAUL BERT` | 31 | `bdnb-bg-9V7F-64PQ-UJ5S` | 8 RUE MOISSONNIER | — | 32→31 |
| AB0217901 | 2 BIS RUE RIBOUD - MS328 | `2B|RUE|RIBOUD` | 30 | `bdnb-bg-YAR9-LWKG-N28H` | 2 RUE RIBOUD | — | 31→30 |
| AC8791634 | 34/36 Rue Saint Philippe | `34|RUE|ST PHILIPPE` | 28 | `bdnb-bg-RA9K-1B11-8L1V` | 36 RUE ST PHILIPPE | — | 28→28 |
| AC8951105 | SDC 21 RUE SAINTE ANNE D | `21A|RUE|STE ANNE DE BARABAN` | 26 | `bdnb-bg-XFV3-8SMG-PGQD` | 21 RUE STE ANNE DE BARABAN | — | 26→26 |
| AA8932717 | PARC SISLEY | `62|RUE|DAUPHINE` | 21 | `bdnb-bg-TMHU-J6YL-UVAU` | 64 RUE DU DAUPHINE | — | 18→21 |
| AB4648424 | COTE PARC SISLEY-LYN | `23|RUE|ROGER BRECHAN` | 17 | `bdnb-bg-3S5M-GLK2-GFBZ` | 25 RUE ROGER BRECHAN | — | 17→17 |
| AC0225904 | PAUL BERT - FELIX FAURE | `336|RUE|PAUL BERT` | 16 | `bdnb-bg-VQUJ-JMTX-BB2C` | 237 AVENUE FELIX FAURE | — | 17→16 |
| AD5288691 | SDC 51BIS AVENUE LACASSA | `51B|AVENUE|LACASSAGNE` | 16 | `bdnb-bg-E3ZW-PDHN-JM11` | 51 AVENUE LACASSAGNE | — | 15→16 |
| AF0858860 | 1 R SAINT MAXIMIN | `1|RUE|ST MAXIMIN` | 14 | `bdnb-bg-RTNL-L1N7-K12Y` | 10 RUE DU DAUPHINE<br>8 RUE DU DAUPHINE | — | 14→14 |
| AA2695633 | 3 BIS RUE BARA | `3B|RUE|BARA` | 12 | `bdnb-bg-1LHG-5G1W-QJ9J` | 3 RUE BARA | — | 11→12 |
| AD5705983 | ESPERANCE 3 | `3|RUE|ESPERANCE` | 10 | `bdnb-bg-XK3Z-EJHT-UR4E` | 4 RUE DE L ESPERANCE | — | 10→10 |
| AB8324360 | 5 BIS RUE MEYNIS | `5B|RUE|MEYNIS` | 9 | `bdnb-bg-BRNB-KK97-9XY7` | 5 RUE MEYNIS | — | 9→9 |
| AE1699040 | LE CLOS ROUGET DE L'ISLE | `264B|RUE|PAUL BERT` | 8 | `bdnb-bg-D9LP-CBCP-F74E` | 260|RUE|PAUL BERT<br>262|RUE|PAUL BERT | — | 1→8 |
| AE1699040 | LE CLOS ROUGET DE L'ISLE | `264B|RUE|PAUL BERT` | 8 | `bdnb-bg-U7C2-SHCF-D72B` | 264 RUE PAUL BERT | — | 25→8 |
| AD7354640 | SDC 99 RUE BARABAN | `99|RUE|BARABAN` | 7 | `bdnb-bg-X6UQ-9RMD-36Y5` | 97 RUE BARABAN | — | 5→7 |
| AA9253212 | 5 BIS RUE DE MONTBRILLAN | `5B|RUE|MONTBRILLANT` | 6 | `bdnb-bg-EDS8-9W4U-U4UB` | 5 RUE DE MONTBRILLANT | — | 6→6 |

## DÉJÀ-COMPTÉ — bâti déjà compté via un sibling visible (NE PAS rattacher : double-comptage)

_aucune_

## COLLISION-CLE

_aucune_
