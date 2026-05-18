# Vérification RNC → BDNB — API live vs snapshot (lecture seule)

API ouverte `api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc` (sans clé), table de relation `numero_immat` ↔ `batiment_groupe_id`. Compare l'ensemble live à `data/bdnb_dauphine_lacassagne.json`.

## Bilan

| Indicateur | Valeur |
|---|--:|
| Copros vérifiées | 821 |
| Copros snapshot ≠ live | 33 |
| **Copros où le snapshot a omis des bâtiments** | **33** |
| Bâtiments live absents du snapshot | 37 (~4107.16 lgts) |
| Bâtiments snapshot absents du live | 0 |

## Top 20 — omissions du snapshot par logements

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AA0600619 | SQUARE LOWENDAL | 3 | 4 | 1 | 971.09 | bdnb-bg-SA52-4L6X-F488 |
| 2 | AA2459444 | SDC JEAN REY SUFFREN HABITATION | 0 | 1 | 1 | 478.0 | bdnb-bg-S2NN-CHNN-RWYU |
| 3 | AB3687951 | 80, rue de la Croix Nivert | 0 | 1 | 1 | 433.0 | bdnb-bg-YF1Q-78V5-M4B3 |
| 4 | AB0578443 | 20-22 R DESAIX | 0 | 1 | 1 | 270.0 | bdnb-bg-H7TH-3T93-SPXK |
| 5 | AC0788810 | 11 RUE PERIGNON | 0 | 1 | 1 | 220.0 | bdnb-bg-3KS7-LLZU-3EFH |
| 6 | AA8780744 | SDC 75 FONDARY | 0 | 1 | 1 | 169.0 | bdnb-bg-9XHF-1BR4-HJ4D |
| 7 | AB3687126 | 74 rue de la Fédération | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 8 | AC2379667 | 18/20 RUE PRESLES | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 9 | AD9092834 | SDC 64-66-68-70 Fédération | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 10 | AB0569376 | 23/29 rue de la croix nivert | 0 | 1 | 1 | 122.0 | bdnb-bg-2ADT-JHS6-GM5G |
| 11 | AA1834670 | SDC 63/65 RUE DU COMMERCE 75015 PA | 0 | 1 | 1 | 98.0 | bdnb-bg-DX5N-JSFQ-35TD |
| 12 | AC1038041 | SDC 13 Dupleix | 0 | 1 | 1 | 97.0 | bdnb-bg-N528-HLH4-HBMR |
| 13 | AB1483791 | SDC 9 LAKANAL | 1 | 6 | 5 | 81.33 | bdnb-bg-24H3-T9FT-8VK1 bdnb-bg-H8ED-S65E-27QN bdnb-bg-NBXL-2S6D-HATZ bdnb-bg-WV96-FDRW-5921 bdnb-bg-ZQWC-S26D-YY1K |
| 14 | AF4297610 | SDC 30 SUFFREN | 1 | 2 | 1 | 78.62 | bdnb-bg-R5UU-CT4G-J44H |
| 15 | AB4757803 | SDC 17/19, RUE DE LA CROIX-NIVERT | 0 | 1 | 1 | 76.0 | bdnb-bg-W9QE-UNHQ-D4WE |
| 16 | AI7024987 | DU GENERAL DE CASTELNAU 4 RUE | 0 | 1 | 1 | 56.0 | bdnb-bg-WHG8-Q9AN-QR6C |
| 17 | AB6181168 | DUPLEIX PARKING 5/11 G. B. SHAW | 0 | 1 | 1 | 50.0 | bdnb-bg-Z5ML-C2UJ-W26D |
| 18 | AB3028107 | PRESLES RUE DE 13 LMC | 0 | 1 | 1 | 48.0 | bdnb-bg-8N6F-YHDA-R8SF |
| 19 | AD0541896 | 4 LARMINAT - MS38509 | 0 | 1 | 1 | 48.0 | bdnb-bg-AS4L-LFNK-ANXJ |
| 20 | AG9833203 | SDC 2 RUE DU GENERAL LARMINAT | 0 | 1 | 1 | 48.0 | bdnb-bg-AS4L-LFNK-ANXJ |

## Top 20 — omissions du snapshot par nombre de bâtiments

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AB1483791 | SDC 9 LAKANAL | 1 | 6 | 5 | 81.33 | bdnb-bg-24H3-T9FT-8VK1 bdnb-bg-H8ED-S65E-27QN bdnb-bg-NBXL-2S6D-HATZ bdnb-bg-WV96-FDRW-5921 bdnb-bg-ZQWC-S26D-YY1K |
| 2 | AA0600619 | SQUARE LOWENDAL | 3 | 4 | 1 | 971.09 | bdnb-bg-SA52-4L6X-F488 |
| 3 | AA2459444 | SDC JEAN REY SUFFREN HABITATION | 0 | 1 | 1 | 478.0 | bdnb-bg-S2NN-CHNN-RWYU |
| 4 | AB3687951 | 80, rue de la Croix Nivert | 0 | 1 | 1 | 433.0 | bdnb-bg-YF1Q-78V5-M4B3 |
| 5 | AB0578443 | 20-22 R DESAIX | 0 | 1 | 1 | 270.0 | bdnb-bg-H7TH-3T93-SPXK |
| 6 | AC0788810 | 11 RUE PERIGNON | 0 | 1 | 1 | 220.0 | bdnb-bg-3KS7-LLZU-3EFH |
| 7 | AA8780744 | SDC 75 FONDARY | 0 | 1 | 1 | 169.0 | bdnb-bg-9XHF-1BR4-HJ4D |
| 8 | AB3687126 | 74 rue de la Fédération | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 9 | AC2379667 | 18/20 RUE PRESLES | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 10 | AD9092834 | SDC 64-66-68-70 Fédération | 0 | 1 | 1 | 163.0 | bdnb-bg-9CRE-MMSG-PL1M |
| 11 | AB0569376 | 23/29 rue de la croix nivert | 0 | 1 | 1 | 122.0 | bdnb-bg-2ADT-JHS6-GM5G |
| 12 | AA1834670 | SDC 63/65 RUE DU COMMERCE 75015 PA | 0 | 1 | 1 | 98.0 | bdnb-bg-DX5N-JSFQ-35TD |
| 13 | AC1038041 | SDC 13 Dupleix | 0 | 1 | 1 | 97.0 | bdnb-bg-N528-HLH4-HBMR |
| 14 | AF4297610 | SDC 30 SUFFREN | 1 | 2 | 1 | 78.62 | bdnb-bg-R5UU-CT4G-J44H |
| 15 | AB4757803 | SDC 17/19, RUE DE LA CROIX-NIVERT | 0 | 1 | 1 | 76.0 | bdnb-bg-W9QE-UNHQ-D4WE |
| 16 | AI7024987 | DU GENERAL DE CASTELNAU 4 RUE | 0 | 1 | 1 | 56.0 | bdnb-bg-WHG8-Q9AN-QR6C |
| 17 | AB6181168 | DUPLEIX PARKING 5/11 G. B. SHAW | 0 | 1 | 1 | 50.0 | bdnb-bg-Z5ML-C2UJ-W26D |
| 18 | AB3028107 | PRESLES RUE DE 13 LMC | 0 | 1 | 1 | 48.0 | bdnb-bg-8N6F-YHDA-R8SF |
| 19 | AD0541896 | 4 LARMINAT - MS38509 | 0 | 1 | 1 | 48.0 | bdnb-bg-AS4L-LFNK-ANXJ |
| 20 | AG9833203 | SDC 2 RUE DU GENERAL LARMINAT | 0 | 1 | 1 | 48.0 | bdnb-bg-AS4L-LFNK-ANXJ |
