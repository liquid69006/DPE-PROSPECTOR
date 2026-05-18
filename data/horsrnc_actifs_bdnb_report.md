# Hors-RNC actifs -> lien RNC BDNB - Dauphine-Lacassagne

**Lecture seule.** Cibles = filtre dashboard *Hors-RNC actifs* (`!coproByCle[cle]` ET `!numero_immatriculation` ET `nb_ventes_logement>0`). Source immat : cache live `_horsrnc_bdnb_live.json` (API `rel_batiment_groupe_rnc`) U `numero_immat_principal` du snapshot. **0 appel reseau** (100% cache), **aucune donnee modifiee**.

## Bilan

| Classe | Definition | Adresses |
|---|---|--:|
| **A** | copro RNC du secteur identifiee via BDNB | **54** |
| - FUSION-MEME-BATI | la copro est deja rendue via une adresse du **meme `bgid`** -> fusion adresse->copro propre (ventes relocalisees, parc deja dedup `bg:bgid`, 0 double-comptage) | **54** |
| - FUSION-AUTRE-BATI | copro visible mais via un `bgid` different (immat multi-batiments ?) -> revue manuelle | 0 |
| - NOUVEAU | copro du registre invisible partout -> ajout net (rare) | 0 |
| **B** | immat BDNB trouvee mais HORS registre secteur | **2** |
| **C** | aucune immat BDNB (vraie monopropriete / copro non immatriculee) | **65** |
| Total | cibles | 121 |

> Ventes logement orphelines relocalisables (FUSION-MEME-BATI) : **209** mutations strictes actuellement non attribuees a leur copro.

## A - Copros RNC rattachables (detail)

| Adresse | bgid | immat | Copro RNC | Syndic | lots_hab | ventes_log | Statut |
|---|---|---|---|---|---|---|---|
| 9 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-68CY-P7TQ-TZ2P` | AA0012898 | ATRIUM SISLEY | GAGNEUX SERVICES IMMOBIL | 225 | 16 | **FUSION-MEME-BATI** |
| 53 RUE ETIENNE RICHERAND | `bdnb-bg-FWNQ-PFMY-A36E` | AC3598851 | LE BEAUBOURG | non connu | 64 | 10 | **FUSION-MEME-BATI** |
| 36 RUE ST PHILIPPE | `bdnb-bg-RA9K-1B11-8L1V` | AC8791634 | 34/36 Rue Saint Philippe | COTRIMO GESTION | 28 | 9 | **FUSION-MEME-BATI** |
| 194 AVENUE FELIX FAURE | `bdnb-bg-LD4C-VJY6-N5SJ` | AD9012642 | 23 M?tallurgie & 194 F. Faure | CABINET PETRUCCI CONVERT | 36 | 8 | **FUSION-MEME-BATI** |
| 168 AVENUE FELIX FAURE | `bdnb-bg-EC36-CQJW-PMK3` | AA2730372 | SDC LE PRESIDENT | ADMINISTION D'IMMEUBLES  | 40 | 8 | **FUSION-MEME-BATI** |
| 209 AVENUE FELIX FAURE | `bdnb-bg-UWK7-TY35-KUDK` | AD3386570 | SDC VILLA SYRACUSE | REGIE FRANCOIS GOFFIN | 34 | 8 | **FUSION-MEME-BATI** |
| 15 RUE ST EUSEBE | `bdnb-bg-H9T9-DYCH-XSSS` | AA2028389 | SDC ESPACE EMERAUDE BAT B | LYMMOBILIER | 33 | 7 | **FUSION-MEME-BATI** |
| 9 RUE DE MONTBRILLANT | `bdnb-bg-9MYW-M2VT-GSQE` | AB6211445 | LE PRIVILEGE MONTBRILLANT A | FONCIA SAINT LOUIS | 59 | 6 | **FUSION-MEME-BATI** |
| 12 RUE LOUIS JASSERON | `bdnb-bg-4DUC-A62Z-LN35` | AA7487564 | L'ENEIDE 1 - MS15805 | LAMY | 29 | 6 | **FUSION-MEME-BATI** |
| 89 RUE BELLECOMBE | `bdnb-bg-YFY8-XRG7-16PK` | AB2463065 | LE BELLECOMBE SAINT ANTOINE | FONCIA LYON | 72 | 6 | **FUSION-MEME-BATI** |
| 14 RUE ST MAXIMIN | `bdnb-bg-6J3V-PN4E-7QWG` | AB2460335 | TERRASSES ET VILLAS ST MAXIMIN | REGIE PEDRINI | 53 | 6 | **FUSION-MEME-BATI** |
| 12 RUE DE VILLON | `bdnb-bg-AHXA-TMQQ-QT6N` | AA7891641 | RESIDENCE LE PARC VILLON | REGIE CARRON | 34 | 5 | **FUSION-MEME-BATI** |
| 2 RUE LOUIS JASSERON | `bdnb-bg-PP7G-YWLB-1ZEC` | AF5264262 | LES BALCONS DE LA PART DIEU | CONFIANCE IMMOBILIER | 25 | 5 | **FUSION-MEME-BATI** |
| 38|RUE|BARABAN | `bdnb-bg-77CU-S4U4-AGR1` | AC9726381 | L'OLEANDRE | non connu | 29 | 5 | **FUSION-MEME-BATI** |
| 260|RUE|PAUL BERT | `bdnb-bg-D9LP-CBCP-F74E` | AE1699040 | LE CLOS ROUGET DE L'ISLE | REGIE DU LYONNAIS | 8 | 5 | **FUSION-MEME-BATI** |
| 6 RUE ST EUSEBE | `bdnb-bg-FBLV-MDEK-PE5T` | AG4913810 | LE  SAINT EUSEBE | CHOMETTE | 15 | 5 | **FUSION-MEME-BATI** |
| 93 RUE BELLECOMBE | `bdnb-bg-KVDR-XPSM-PDB5` | AB5869177 | SDC LE BELLECOMBE | REGIE GINON | 21 | 5 | **FUSION-MEME-BATI** |
| 51 RUE ST ANTOINE | `bdnb-bg-HQWX-SRVS-WAVH` | AD9391244 | LE PATIO SAINT-ANTOINE - MS167 | LAMY | 25 | 5 | **FUSION-MEME-BATI** |
| 7 RUE MAURICE FLANDIN | `bdnb-bg-6RYY-NUCS-XLRZ` | AB1493691 | LE PRIVIL?GE LAFAYETTE | non connu | 18 | 5 | **FUSION-MEME-BATI** |
| 182 AVENUE FELIX FAURE | `bdnb-bg-YTPF-DAGN-K1LQ` | AC2489979 | LE FELIX FAURE | REGIE DE VENDIN | 52 | 4 | **FUSION-MEME-BATI** |
| 30 RUE ST ANTOINE | `bdnb-bg-6UE1-UT3G-U7D2` | AC3226362 | LA COUR SAINT ANTOINE | SOC ADMIN & GESTION IMME | 63 | 4 | **FUSION-MEME-BATI** |
| 12 RUE CARRY | `bdnb-bg-FW4B-YECQ-FPCT` | AC1825504 | 6/8, rue Carry | C2L | 12 | 4 | **FUSION-MEME-BATI** |
| 131 AVENUE FELIX FAURE | `bdnb-bg-DZ9A-B3PC-VXA9` | AA8736043 | PRT DIEU SQUARE CARRE PRT DIEU | IMMO DE FRANCE RHONE ALP | 83 | 4 | **FUSION-MEME-BATI** |
| 56 AVENUE LACASSAGNE | `bdnb-bg-JMUE-VX7J-RR9W` | AA4814810 | LES PINS | FONCIA LYON | 50 | 4 | **FUSION-MEME-BATI** |
| 48 RUE ST MAXIMIN | `bdnb-bg-4F6G-4P2Q-RRZK` | AB2784080 | RESIDENCE MANET | REGIE PEDRINI | 50 | 3 | **FUSION-MEME-BATI** |
| 18 RUE ETIENNE RICHERAND | `bdnb-bg-NWNV-GU7Z-XPMJ` | AG2447720 | SDC 19 RUE ETIENNE RICHERAND | non connu | 8 | 3 | **FUSION-MEME-BATI** |
| 237 AVENUE FELIX FAURE | `bdnb-bg-VQUJ-JMTX-BB2C` | AC0225904 | PAUL BERT - FELIX FAURE | REGIE VINCENT TARGE | 16 | 3 | **FUSION-MEME-BATI** |
| 3 RUE ST EUSEBE | `bdnb-bg-81HL-8BC6-UPG6` | AB0287870 | LE SAINT EUSEBE | GESTION ET PATRIMOINE LE | 14 | 3 | **FUSION-MEME-BATI** |
| 316 RUE PAUL BERT | `bdnb-bg-JFRZ-XJTQ-L9ZQ` | AC6168629 | RESIDENCE 318 RUE PAUL BERT | CABINET GINET SA | 6 | 3 | **FUSION-MEME-BATI** |
| 10 RUE DU DAUPHINE | `bdnb-bg-RTNL-L1N7-K12Y` | AF0858860 | 1 R SAINT MAXIMIN | GESTION ET PATRIMOINE LE | 14 | 3 | **FUSION-MEME-BATI** |
| 14 RUE ST SIDOINE | `bdnb-bg-4BCZ-EFDZ-724F` | AB2206571 | LA VICTORIENNE | FONCIA LYON | 165 | 3 | **FUSION-MEME-BATI** |
| 18 RUE ST ANTOINE | `bdnb-bg-PFFK-6Z9V-TUP1` | AE9439365 | LE SAINT ANTOINE | CONFLUENCE ROLIN BAINSON | 45 | 3 | **FUSION-MEME-BATI** |
| 21 RUE STE ANNE DE BARABAN | `bdnb-bg-XFV3-8SMG-PGQD` | AC8951105 | SDC 21 RUE SAINTE ANNE DE BARA | CORNEILLE SAINT MARC | 26 | 3 | **FUSION-MEME-BATI** |
| 22 RUE ETIENNE RICHERAND | `bdnb-bg-SBHG-VQWK-FCA9` | AB0141341 | SDC 21 RUE ETIENNE RICHERAND | non connu | 14 | 3 | **FUSION-MEME-BATI** |
| 5 RUE DE MONTBRILLANT | `bdnb-bg-EDS8-9W4U-U4UB` | AA9253212 | 5 BIS RUE DE MONTBRILLANT | CITYA VENDOME LUMIERE | 6 | 3 | **FUSION-MEME-BATI** |
| 64 RUE DU DAUPHINE | `bdnb-bg-TMHU-J6YL-UVAU` | AA8932717 | PARC SISLEY | CITYA VENDOME LUMIERE | 21 | 2 | **FUSION-MEME-BATI** |
| 32 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-7A21-PPNH-TLQM` | AA7236011 | LES DAHLIAS - MS130778 | REGIE FRANCOIS GOFFIN | 32 | 2 | **FUSION-MEME-BATI** |
| 46 RUE ST MAXIMIN | `bdnb-bg-PWDK-M71Z-3JJQ` | AB1744747 | LES JARDINS D'HELIOS | non connu | 22 | 2 | **FUSION-MEME-BATI** |
| 63 RUE DE LA VILLETTE | `bdnb-bg-BENR-J4R2-X2NB` | AA0787333 | LES TERRASSES DE LA GARE | ESPACE IMMOBILIER LYONNA | 80 | 2 | **FUSION-MEME-BATI** |
| 74 RUE ETIENNE RICHERAND | `bdnb-bg-RG9V-8L1Q-97UN` | AF6417042 | SDC LE CASTELLANNE | ADMINISTRATION D'IMMEUBL | 55 | 2 | **FUSION-MEME-BATI** |
| 84 RUE ANTOINE CHARIAL | `bdnb-bg-5BKM-AXLT-FC77` | AA7209463 | LE CLOS DE LA ROSERAIE - MS329 | LAMY | 38 | 2 | **FUSION-MEME-BATI** |
| 41 RUE GUILLOUD | `bdnb-bg-YTPJ-Q2XB-2DEF` | AJ0217901 | LE GUILLOUD | REGIE DU LYONNAIS | 30 | 2 | **FUSION-MEME-BATI** |
| 23 RUE STE ANNE DE BARABAN | `bdnb-bg-DPD7-7ZP1-GHVU` | AB8780330 | SAINTE ANNE | REGIE VINCENT TARGE | 47 | 1 | **FUSION-MEME-BATI** |
| 24 AVENUE LACASSAGNE | `bdnb-bg-WLXU-6YKR-D8DU` | AG1556893 | BRICKS 2 | FONCIA LYON | 64 | 1 | **FUSION-MEME-BATI** |
| 17 RUE ST VICTORIEN | `bdnb-bg-H6H4-644T-6NRG` | AA9260977 | LE SAINT VICTORIEN | MALSH PROPERTY | 69 | 1 | **FUSION-MEME-BATI** |
| 2 RUE DE LA METALLURGIE | `bdnb-bg-51HE-8CSW-Q4A6` | AB8301665 | 1 RUE DE LA METALLURGIE | non connu | 21 | 1 | **FUSION-MEME-BATI** |
| 25 RUE ROGER BRECHAN | `bdnb-bg-3S5M-GLK2-GFBZ` | AB4648424 | COTE PARC SISLEY-LYN | REGIE DERVAULT BY GERALD | 17 | 1 | **FUSION-MEME-BATI** |
| 40 RUE ST MAXIMIN | `bdnb-bg-6BRM-AZZY-6Q8H` | AB5878327 | SDC LE CASSIOPEE | REGIE GINON | 33 | 1 | **FUSION-MEME-BATI** |
| 41 COURS ALBERT THOMAS | `bdnb-bg-FCLN-D7V1-1RVN` | AG6298160 | LE SPHINX | REGIE POZETTO | 34 | 1 | **FUSION-MEME-BATI** |
| 5 RUE MEYNIS | `bdnb-bg-BRNB-KK97-9XY7` | AB8324360 | 5 BIS RUE MEYNIS | non connu | 9 | 1 | **FUSION-MEME-BATI** |
| 5 RUE ROSSAN | `bdnb-bg-CU5B-W5ZK-THBQ` | AC1757376 | LE N1 RUE GUILLOUD | CONFLUENCE ROLIN BAINSON | 70 | 1 | **FUSION-MEME-BATI** |
| 20 RUE GUILLOUD | `bdnb-bg-212B-J3A4-DL3G` | AB1910728 | 20 TER RUE GUILLOUD | REGIE ROCHON - LESNE | 32 | 1 | **FUSION-MEME-BATI** |
| 30 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-PTBZ-QHYH-Y2WN` | AC7505134 | SDC SDC LE SISLEY | CENTRALE IMMOBILIERE DE  | 43 | 1 | **FUSION-MEME-BATI** |
| 97 RUE BARABAN | `bdnb-bg-X6UQ-9RMD-36Y5` | AD7354640 | SDC 99 RUE BARABAN | REGIE POZETTO | 7 | 1 | **FUSION-MEME-BATI** |

## B - Immat hors secteur (info, non rattachable ici)

| Adresse | bgid | immat BDNB | ventes_log | nom BDNB |
|---|---|---|---|---|
| 3 RUE MAURICE FLANDIN | `bdnb-bg-W2RS-K6JM-Z1H3` | AB2505550 | 7 | 3-5-7 RUE MAURICE FLANDIN |
| 4 RUE MAURICE FLANDIN | `bdnb-bg-W2RS-K6JM-Z1H3` | AB2505550 | 2 | 3-5-7 RUE MAURICE FLANDIN |

## C - Aucune immat BDNB (65 adresses)

_Vraie monopropriete, copro non immatriculee au RNC, ou bati BDNB sans relation `rel_batiment_groupe_rnc`. Non rattachable via BDNB._

| Adresse | bgid | ventes_log | nb_log_bdnb |
|---|---|---|---|
| 106 RUE BARABAN | `bdnb-bg-8NJL-4XAJ-TVQA` | 13 | 61 |
| 30 RUE ETIENNE RICHERAND | `bdnb-bg-DAZ8-N3AL-EF91` | 12 | 13 |
| 59 RUE BARABAN | `bdnb-bg-W624-4P36-PURP` | 11 | - |
| 22 AVENUE GEORGES POMPIDOU | `bdnb-bg-Q4M4-7RMM-H4XQ` | 10 | 37 |
| 8 RUE CLAUDIUS PIONCHON | `bdnb-bg-B7XN-JTJZ-HPB4` | 9 | - |
| 44 RUE TURBIL | `bdnb-bg-UN53-G1LZ-2P34` | 8 | 27 |
| 10 RUE MEYNIS | `bdnb-bg-GFKS-DC3T-CRB1` | 7 | - |
| 28 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-CFFP-14RF-1SN5` | 6 | 18 |
| 29 RUE STE ANNE DE BARABAN | `bdnb-bg-YBEL-Q4MX-AZC3` | 6 | 1 |
| 143 RUE DU DAUPHINE | `bdnb-bg-LPW9-YCD1-7GFB` | 6 | 12 |
| 8 RUE DU DOCTEUR REBATEL | `bdnb-bg-P2DG-Q47U-658U` | 5 | 25 |
| 12 RUE MOISSONNIER | `bdnb-bg-JD9X-LS8L-R7A9` | 5 | 29 |
| 15 RUE ETIENNE RICHERAND | `bdnb-bg-YQDT-7VMV-E5S5` | 5 | 45 |
| 7 RUE DE LA METALLURGIE | `bdnb-bg-WSTK-SKSS-P2M2` | 5 | 21 |
| 11 RUE RIBOUD | `bdnb-bg-ZS47-TD9J-M4FB` | 5 | 13 |
| 9 RUE ST EUSEBE | `bdnb-bg-1R8S-PG6T-JXF4` | 5 | 18 |
| 4 RUE JEAN RENOIR | `bdnb-bg-WM3M-F4BX-8Z7T` | 4 | 35 |
| 16 RUE ETIENNE RICHERAND | `bdnb-bg-G15W-CLD7-6WBT` | 4 | 61 |
| 31 RUE STE ANNE DE BARABAN | `bdnb-bg-CS7S-ZSUP-29YF` | 4 | 1 |
| 5 RUE MARCEL PEHU | `bdnb-bg-GMWN-9ZYS-LQGQ` | 4 | 32 |
| 22 RUE LOUIS JASSERON | `bdnb-bg-VPLJ-N3JJ-SW4G` | 4 | 37 |
| 4 RUE MARCEL PEHU | `bdnb-bg-GMWN-9ZYS-LQGQ` | 4 | 32 |
| 47 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-B819-EARQ-9D7B` | 4 | 2 |
| 71 RUE PAUL BERT | `bdnb-bg-WPVN-TN1Z-KE2S` | 4 | - |
| 5 RUE JEAN PIERRE LEVY | `bdnb-bg-YAUB-Z7P7-2XQ1` | 3 | 36 |
| 125 RUE DU DAUPHINE | `bdnb-bg-NP5T-JZFB-UVR7` | 3 | 22 |
| 310 COURS LAFAYETTE | `bdnb-bg-PNCB-MYC1-JB4Q` | 3 | 15 |
| 52|AVENUE|GEORGES POMPIDOU | `bdnb-bg-71B2-4HSV-Y9VP` | 3 | 18 |
| 272 RUE PAUL BERT | `bdnb-bg-35NH-CNYH-DY2X` | 3 | 27 |
| 6 RUE DE LA METALLURGIE | `bdnb-bg-WSTK-SKSS-P2M2` | 3 | 21 |
| 51 AVENUE GEORGES POMPIDOU | `bdnb-bg-71B2-4HSV-Y9VP` | 3 | 18 |
| 75 RUE DU DAUPHINE | `bdnb-bg-XEEK-6E83-3BX4` | 3 | 10 |
| 9 RUE GABILLOT | `bdnb-bg-QGFJ-1RLT-6ZEN` | 3 | 27 |
| 10 RUE DES TEINTURIERS | `bdnb-bg-WQZA-TNRT-44JS` | 2 | - |
| 139 RUE DU DAUPHINE | `bdnb-bg-6PR8-HQ5A-SU4G` | 2 | 20 |
| 48|AVENUE|GEORGES POMPIDOU | `bdnb-bg-ZNN2-SAMJ-S68B` | 2 | 18 |
| 234 RUE PAUL BERT | `bdnb-bg-LQU8-MYBM-2AMK` | 2 | 7 |
| 10 RUE DE LA METALLURGIE | `bdnb-bg-324Y-G9R6-B2ZS` | 2 | 2 |
| 10 RUE TERNOIS | `bdnb-bg-5RMC-KXL7-E97N` | 2 | 80 |
| 124 RUE ANTOINE CHARIAL | `bdnb-bg-AX8P-5ZM6-3A3B` | 2 | - |
| 21 RUE CLAUDIUS PIONCHON | `bdnb-bg-JAVT-QG97-XWEW` | 2 | 35 |
| 11 RUE DAVID | `bdnb-bg-7VPW-6YPJ-XASZ` | 2 | 3 |
| 21 RUE ST ANTOINE | `bdnb-bg-ALA1-7UY8-ULUG` | 2 | 16 |
| 325 RUE PAUL BERT | `bdnb-bg-YTGZ-FUN1-1XWM` | 2 | 16 |
| 6 RUE PROFESSEUR PAUL SISLEY | `bdnb-bg-AM81-DZPJ-QXMN` | 2 | 6 |
| 76 RUE DU DAUPHINE | `bdnb-bg-ULHW-P9KF-JSGH` | 2 | 39 |
| 69 RUE BARABAN | `bdnb-bg-5W9P-RL7A-RWW7` | 1 | - |
| 21|RUE|GUILLOUD | `bdnb-bg-BALG-5MRC-2XQ6` | 1 | 1 |
| 33|AVENUE|LACASSAGNE | `bdnb-bg-MCU5-7CPV-JE1Z` | 1 | 1 |
| 13|RUE|METALLURGIE | `bdnb-bg-324Y-G9R6-B2ZS` | 1 | 2 |
| 6|RUE|PREVOYANTS DE L AVENIR | `bdnb-bg-B8FV-76BN-BDJJ` | 1 | 1 |
| 225|AVENUE|FELIX FAURE | `bdnb-bg-Y1BN-MPP6-46DX` | 1 | 1 |
| 157|RUE|ANTOINE CHARIAL | `bdnb-bg-3QGJ-3J39-NB4K` | 1 | 1 |
| 14|RUE|PREVOYANTS DE L AVENIR | `bdnb-bg-ENLN-1W4S-BPXX` | 1 | 1 |
| 8|RUE|ST PHILIPPE | `bdnb-bg-6J53-GM13-2GRL` | 1 | 1 |
| 277 RUE PAUL BERT | `bdnb-bg-35NH-CNYH-DY2X` | 1 | 27 |
| 3 RUE ROSSAN | `bdnb-bg-CD87-UNB7-7N3J` | 1 | 20 |
| 45 AVENUE GEORGES POMPIDOU | `bdnb-bg-KM3Q-XAC3-34D1` | 1 | 61 |
| 122 RUE BARABAN | `bdnb-bg-PQR4-97S4-XPXU` | 1 | 10 |
| 15 RUE DAVID | `bdnb-bg-H7YV-VH5E-JFY8` | 1 | 9 |
| 254 COURS LAFAYETTE | `bdnb-bg-2Q6B-A22Y-PRGD` | 1 | 1 |
| 279 RUE PAUL BERT | `bdnb-bg-U3Q7-1AD8-Z67B` | 1 | 6 |
| 4 RUE TERNOIS | `bdnb-bg-5RMC-KXL7-E97N` | 1 | 80 |
| 5 RUE ST MAXIMIN | `bdnb-bg-2UGA-DSEH-TAL4` | 1 | - |
| 65 RUE ETIENNE RICHERAND | `bdnb-bg-J5M8-8PYA-ALEX` | 1 | 6 |

## Etape 4 - Evaluation dry-run (proprete du rattachement)

Le parc RNC est deja dedup par `bg:bgid` (cf. correctif parc RNC pur) : aucune des copros A n'est *perdue* cote logements. L'enjeu reel = **relocaliser les ventes DVF orphelines** de ces adresses hors-RNC vers leur copro, SANS double-compter (mecanisme = `secteurFusions` adresse->copro, qui deplace les ventes ; il NE faut PAS injecter une copro dupliquee).

- **54 FUSION-MEME-BATI = rattachement PROPRE** : la copro est rendue via une adresse du **meme batiment** ; fusionner l'adresse hors-RNC vers cette copro relocalise ses **209 ventes logement** sans toucher au parc (dedup `bg:bgid`) -> **0 collision, 0 double-comptage**. Candidats surs.
- 0 FUSION-AUTRE-BATI : copro visible sur un `bgid` different (immat possiblement multi-batiments, ou mapping BDNB a verifier) -> revue manuelle avant fusion.
- 0 NOUVEAU : copro du registre invisible partout -> rattachement = ajout net (parc + ventes) ; rare.

**Dry-run uniquement. Aucune donnee modifiee. Aucune fusion appliquee : validation requise.**
