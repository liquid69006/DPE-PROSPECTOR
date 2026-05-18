# Hors-RNC actifs -> lien RNC BDNB - Motte-Picquet

**Lecture seule.** Cibles = filtre dashboard *Hors-RNC actifs* (`!coproByCle[cle]` ET `!numero_immatriculation` ET `nb_ventes_logement>0`). Source immat : cache live `_horsrnc_bdnb_live_motte_picquet.json` (API `rel_batiment_groupe_rnc`) U `numero_immat_principal` du snapshot. **0 appel reseau** (100% cache), **aucune donnee modifiee**.

## Bilan

| Classe | Definition | Adresses |
|---|---|--:|
| **A** | copro RNC du secteur identifiee via BDNB | **37** |
| - FUSION-MEME-BATI | la copro est deja rendue via une adresse du **meme `bgid`** -> fusion adresse->copro propre (ventes relocalisees, parc deja dedup `bg:bgid`, 0 double-comptage) | **35** |
| - FUSION-AUTRE-BATI | copro visible mais via un `bgid` different (immat multi-batiments ?) -> revue manuelle | 3 |
| - NOUVEAU | copro du registre invisible partout -> ajout net (rare) | 0 |
| **B** | immat BDNB trouvee mais HORS registre secteur | **2** |
| **C** | aucune immat BDNB (vraie monopropriete / copro non immatriculee) | **40** |
| Total | cibles | 79 |

> Ventes logement orphelines relocalisables (FUSION-MEME-BATI) : **139** mutations strictes actuellement non attribuees a leur copro.

## A - Copros RNC rattachables (detail)

| Adresse | bgid | immat | Copro RNC | Syndic | lots_hab | ventes_log | Statut |
|---|---|---|---|---|---|---|---|
| 11 AVENUE DU MAINE | `bdnb-bg-FLSN-USYE-JCQ7` | AE5269964 | SDC 110 AVENUE DE SUFFREN | non connu | 13 | 7 | FUSION-AUTRE-BATI |
| 14 AVENUE DU MAINE | `bdnb-bg-FLSN-USYE-JCQ7` | AE5269964 | SDC 110 AVENUE DE SUFFREN | non connu | 13 | 7 | FUSION-AUTRE-BATI |
| 10|RUE|DUPLEIX | `bdnb-bg-N528-HLH4-HBMR` | AC1038041 | SDC 13 Dupleix | non connu | 24 | 2 | FUSION-AUTRE-BATI |
| 23 RUE DU LAOS | `bdnb-bg-R7R5-V6KY-HAXT` | AA9613753 | SDC DU 21 23 25 RUE DU LAOS | GRIFFATON & CO | 112 | 16 | **FUSION-MEME-BATI** |
| 9 RUE DU GUESCLIN | `bdnb-bg-74VK-UPM2-JYYD` | AB1748391 | R?sidence Du Guesclin | URBANIA VAL D OUEST | 104 | 8 | **FUSION-MEME-BATI** |
| 3 RUE DU CAPT SCOTT | `bdnb-bg-MRB7-NV5V-XQPL` | AF6894638 | SDC 1 Capitaine Scott | CABINET IFNOR | 27 | 8 | **FUSION-MEME-BATI** |
| 18 RUE JUGE | `bdnb-bg-W2GE-DA7G-F63N` | AC4170221 | SDC 19 RUE JUGE | FONCIA PARIS RIVE GAUCHE | 10 | 7 | **FUSION-MEME-BATI** |
| 61 AVENUE DE SEGUR | `bdnb-bg-B8SY-XQ8W-RU7P` | AC6299499 | SDC du 61/63 Avenue de S?gur | ELIMMO GESTION | 56 | 7 | **FUSION-MEME-BATI** |
| 43 RUE FONDARY | `bdnb-bg-1Y1L-E4T1-5F39` | AF9892365 | FONDARY 43/45 | CABINET GELIS | 43 | 7 | **FUSION-MEME-BATI** |
| 36 RUE MIOLLIS | `bdnb-bg-KKXK-HUWE-NMFU` | AD9666140 | 29 CAMBRONNE 75015 | CDIM | 16 | 6 | **FUSION-MEME-BATI** |
| 156 BOULEVARD DE GRENELLE | `bdnb-bg-F3HZ-H1TK-FPME` | AB1105360 | PARIS MOTTE PICQUET GRENELLE - | non connu | 35 | 6 | **FUSION-MEME-BATI** |
| 3 AVENUE DE CHAMPAUBERT | `bdnb-bg-UHLY-6XC7-PRSL` | AB6311765 | SDC 80 SUFFREN - 2 CHAMPAUBERT | CABINET MDA IMMO | 29 | 6 | **FUSION-MEME-BATI** |
| 9 SQUARE DESAIX | `bdnb-bg-NTCL-E216-D426` | AC2394427 | SDC 10 SQUARE DESAIX | non connu | 14 | 6 | **FUSION-MEME-BATI** |
| 5 RUE DU GAL LAMBERT | `bdnb-bg-JXQ1-42AR-2CFG` | AB7917073 | 5 RUE DU GENERAL LAMBERT | BR COPROPRIETE | 39 | 5 | **FUSION-MEME-BATI** |
| 6 RUE CHAMPFLEURY | `bdnb-bg-PEQ4-R33A-KUU4` | AB0758383 | 6 RUE CHAMPFLEURY | TIFFENCOGE | 29 | 4 | **FUSION-MEME-BATI** |
| 39 RUE FONDARY | `bdnb-bg-KA4C-YCKL-KZBN` | AB4199527 | SDC 39-41 RUE FONDARY 75015 PA | CABINET CITEAU | 49 | 4 | **FUSION-MEME-BATI** |
| 47 BOULEVARD GARIBALDI | `bdnb-bg-R8BU-M8UW-9XG4` | AA6084305 | GARIBALDI - PARIS 15 | S.T.B. GESTION - IMMO GE | 27 | 4 | **FUSION-MEME-BATI** |
| 4 RUE DU GAL DE CASTELNAU | `bdnb-bg-AT1J-MWX1-DFMU` | AB1024181 | SDC 5 RUE DE LA CAVALERIE | GERASCO | 24 | 4 | **FUSION-MEME-BATI** |
| 7 RUE CARRIER BELLEUSE | `bdnb-bg-CC8V-7YJ2-D3V6` | AC2604221 | SDC CARRIER BELLEUSE (6 RUE) | FONCIA PARIS RIVE DROITE | 14 | 4 | **FUSION-MEME-BATI** |
| 3 RUE DU GAL DE CASTELNAU | `bdnb-bg-WHG8-Q9AN-QR6C` | AI7024987 | DU GENERAL DE CASTELNAU 4 RUE | JEAN CHARPENTIER-SOPAGI  | 28 | 3 | **FUSION-MEME-BATI** |
| 6 AVENUE DU GAL DETRIE | `bdnb-bg-51P3-7MJW-1MYH` | AC6620728 | 38 Charles Floquet | FONCIERE ET IMMOBILIERE  | 36 | 3 | **FUSION-MEME-BATI** |
| 9 RUE DU GAL DE LARMINAT | `bdnb-bg-YUBA-32JB-Q8QC` | AA3229176 | SDC 9 rue G?n?ral Larminat | AVENTIN | 16 | 3 | **FUSION-MEME-BATI** |
| 1 RUE JOSE MARIA DE HEREDIA | `bdnb-bg-XEU6-SX79-W1RA` | AH2463305 | SEGUR AVENUE 67 | ADRIEN SIMONNET SAS | 15 | 3 | **FUSION-MEME-BATI** |
| 63 RUE DU COMMERCE | `bdnb-bg-DX5N-JSFQ-35TD` | AA1834670 | SDC 63/65 RUE DU COMMERCE 7501 | CITYA IMMOBILIER TEISSIE | 33 | 3 | **FUSION-MEME-BATI** |
| 38 RUE DE LA FEDERATION | `bdnb-bg-2D39-EQYE-6K8A` | AD0544940 | 37/39 FEDERATION - MS40248 | UNION COMMERCIALE IMMOBI | 19 | 3 | **FUSION-MEME-BATI** |
| 1 RUE DE BUENOS AIRES | `bdnb-bg-M3B8-DJ7V-TCKJ` | AD4111738 | 1 RUE DE BUENOS AYRES | CGA | 13 | 2 | **FUSION-MEME-BATI** |
| 2 RUE DU GAL DE LARMINAT | `bdnb-bg-AS4L-LFNK-ANXJ` | AD0541896 | 4 LARMINAT - MS38509 | ATRIUM GESTION PARIS 15 | 15 | 2 | **FUSION-MEME-BATI** |
| 16 RUE FREMICOURT | `bdnb-bg-YT8F-8UVW-X9PQ` | AF2096014 | SDC 16 - 18 rue Fr?micourt | DM GESTION | 37 | 2 | **FUSION-MEME-BATI** |
| 27 RUE FREMICOURT | `bdnb-bg-28QF-MUJA-UL8K` | AB3441680 | 28 rue Fremicourt | ATRIUM GESTION PARIS 15 | 16 | 2 | **FUSION-MEME-BATI** |
| 3 PLACE CAMBRONNE | `bdnb-bg-5EJY-P43A-W2JX` | AB5809108 | SDC 6 CAMBRONNE | DAUCHEZ PROPERTY MANAGEM | 19 | 2 | **FUSION-MEME-BATI** |
| 135 RUE DU THEATRE | `bdnb-bg-VD62-C1QJ-T3ZT` | AD5373162 | 134 rue du th??tre | GESTION ET TRANSACTIONS  | 15 | 1 | **FUSION-MEME-BATI** |
| |ALLEE|LEON BOURGEOIS | `bdnb-bg-M3B8-DJ7V-TCKJ` | AD4111738 | 1 RUE DE BUENOS AYRES | CGA | 13 | 1 | **FUSION-MEME-BATI** |
| 1 CITE THURE | `bdnb-bg-YHQV-17YZ-RARN` | AI8720518 | SDC 132 rue du Th??tre et 1 ci | Identit? non partag?e en | 6 | 1 | **FUSION-MEME-BATI** |
| 155 AVENUE DE SUFFREN | `bdnb-bg-ZWXU-9VJU-VD7B` | AI4207031 | SDC SUFFREN 155 | JMD CONSEIL | 9 | 1 | **FUSION-MEME-BATI** |
| 3 RUE DE BUENOS AIRES | `bdnb-bg-DJ6H-9KDB-HAGV` | AB3659166 | BUENOS AYRES-3 J Y | CF GESTION IMMOBILIERE | 30 | 1 | **FUSION-MEME-BATI** |
| 6 RUE DU GAL DE LARMINAT | `bdnb-bg-PHBC-JCMV-7GBR` | AA7531452 | DU GENERAL DE LARMINAT 6 RUE | JEAN CHARPENTIER-SOPAGI  | 9 | 1 | **FUSION-MEME-BATI** |
| 7 RUE DU GAL DE CASTELNAU | `bdnb-bg-Y4MM-76QV-HLQU` | AC0121202 | 5 rue du General de Castelnau | CABINET PIERRE BONNEFOI  | 20 | 1 | **FUSION-MEME-BATI** |

## B - Immat hors secteur (info, non rattachable ici)

| Adresse | bgid | immat BDNB | ventes_log | nom BDNB |
|---|---|---|---|---|
| 16 AVENUE DE LOWENDAL | `bdnb-bg-R41C-48RR-9DHU` | AB8146169 | 2 | 16-18, AVENUE LOWENDAL |
| 163 AVENUE DE SUFFREN | `bdnb-bg-QTC9-KFAU-5TPU` | AD2301695 | 2 | 163 AVENUE DE SUFFREN |

## C - Aucune immat BDNB (40 adresses)

_Vraie monopropriete, copro non immatriculee au RNC, ou bati BDNB sans relation `rel_batiment_groupe_rnc`. Non rattachable via BDNB._

| Adresse | bgid | ventes_log | nb_log_bdnb |
|---|---|---|---|
| 30 RUE MIOLLIS | `bdnb-bg-XDM8-1XCX-84Y1` | 14 | 20 |
| 163 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | 9 | - |
| 17 RUE CEPRE | `bdnb-bg-LJD4-899K-FZF5` | 8 | 45 |
| 106 RUE DE SEVRES | `bdnb-bg-QNR9-N4KK-K8A1` | 7 | - |
| 4 AVENUE EMILE ACOLLAS | `bdnb-bg-1QLP-NQE7-LM1Q` | 6 | 16 |
| 26 BOULEVARD GARIBALDI | `bdnb-bg-PNXA-8DRE-F4GM` | 6 | 15 |
| 5 RUE DE L EGLISE | `bdnb-bg-XHH7-SYZY-QSFQ` | 6 | - |
| 10 RUE PERIGNON | `bdnb-bg-6RE2-LG3N-FXCZ` | 5 | 27 |
| 13 RUE CARRIER BELLEUSE | `bdnb-bg-4CUT-Z57B-XDTM` | 4 | 33 |
| 22 RUE DE LA FEDERATION | `bdnb-bg-A4CU-YC17-6HN1` | 4 | 1 |
| 28 RUE DUPLEIX | `bdnb-bg-ZW4Z-VEGN-9VF8` | 4 | 1 |
| 6 AVENUE EMILE ACOLLAS | `bdnb-bg-79UA-TW3K-DQLE` | 4 | 18 |
| 11 CITE THURE | `bdnb-bg-HNSV-XK55-A3WG` | 3 | 5 |
| 11 RUE DU GAL DE LARMINAT | `bdnb-bg-2C94-UQ57-XTEP` | 3 | 15 |
| 55 RUE DU COMMERCE | `bdnb-bg-ZC1A-K8AP-RZ1P` | 3 | 6 |
| 8 RUE DE LA CROIX NIVERT | `bdnb-bg-JHPF-31PS-7UD1` | 3 | 18 |
| 7|RUE|HUMBLOT | `bdnb-bg-UAGM-46Q3-SUTU` | 2 | 12 |
| 14 RUE TIPHAINE | `bdnb-bg-L59B-AGAK-AP75` | 2 | 8 |
| 9 RUE DE L EGLISE | `bdnb-bg-SJRT-PTDZ-KASE` | 2 | - |
| 8 RUE DU GAL DE LARMINAT | `bdnb-bg-8J73-8U9C-J8RF` | 1 | 16 |
| 128 AVENUE DE SUFFREN | `bdnb-bg-WAEU-1XSX-V5GP` | 1 | 18 |
| 11|RUE|FALLEMPIN | `bdnb-bg-DFH3-VK2Z-9CEE` | 1 | 1 |
| 55|AVENUE|SUFFREN | `bdnb-bg-GQAG-T52L-7376` | 1 | 15 |
| 9|RUE|LOURMEL | `bdnb-bg-ULGL-GMJY-1YAS` | 1 | 13 |
| 21|AVENUE|CHARLES FLOQUET | `bdnb-bg-GZ79-JFXC-74CF` | 1 | 1 |
| 91|RUE|FONDARY | `bdnb-bg-DN3P-4R65-2XG2` | 1 | 4 |
| 147 AVENUE DE SUFFREN | `bdnb-bg-9TTE-EQAG-Z8LH` | 1 | 10 |
| 15 RUE LETELLIER | `bdnb-bg-B5MQ-AZTT-5PV6` | 1 | 26 |
| 16 RUE VIOLET | `bdnb-bg-9PX4-LE3D-RT3Q` | 1 | 7 |
| 19 RUE FALLEMPIN | `bdnb-bg-8SVW-VJ5N-H9XW` | 1 | 1 |
| 2 RUE CEPRE | `bdnb-bg-Z2Z2-65KJ-U324` | 1 | 11 |
| 2 RUE DE BUENOS AIRES | `bdnb-bg-FB3W-4B4K-PYEL` | 1 | 15 |
| 4 AVENUE OCTAVE GREARD | `bdnb-bg-ZWNL-RMHH-RY7N` | 1 | 11 |
| 4 RUE DE BUENOS AIRES | `bdnb-bg-BBRR-9P88-BTJ5` | 1 | 20 |
| 51 RUE DE LA FEDERATION | `bdnb-bg-TGBY-G4B7-X44K` | 1 | 40 |
| 55 RUE DE LA FEDERATION | `bdnb-bg-KK61-2FJK-3SDH` | 1 | 17 |
| 6 RUE ALASSEUR | `bdnb-bg-9DSY-ZPJ1-Y95N` | 1 | 16 |
| 6 RUE BARTHELEMY | `bdnb-bg-MALT-7HZW-3SXQ` | 1 | 17 |
| 71 QUAI JACQUES CHIRAC | `bdnb-bg-6SBC-228Y-4AEN` | 1 | 15 |
| 83 BOULEVARD DE GRENELLE | `bdnb-bg-5KST-PABL-LAUP` | 1 | 31 |

## Etape 4 - Evaluation dry-run (proprete du rattachement)

Le parc RNC est deja dedup par `bg:bgid` (cf. correctif parc RNC pur) : aucune des copros A n'est *perdue* cote logements. L'enjeu reel = **relocaliser les ventes DVF orphelines** de ces adresses hors-RNC vers leur copro, SANS double-compter (mecanisme = `secteurFusions` adresse->copro, qui deplace les ventes ; il NE faut PAS injecter une copro dupliquee).

- **35 FUSION-MEME-BATI = rattachement PROPRE** : la copro est rendue via une adresse du **meme batiment** ; fusionner l'adresse hors-RNC vers cette copro relocalise ses **139 ventes logement** sans toucher au parc (dedup `bg:bgid`) -> **0 collision, 0 double-comptage**. Candidats surs.
- 3 FUSION-AUTRE-BATI : copro visible sur un `bgid` different (immat possiblement multi-batiments, ou mapping BDNB a verifier) -> revue manuelle avant fusion.
- 0 NOUVEAU : copro du registre invisible partout -> rattachement = ajout net (parc + ventes) ; rare.

**Dry-run uniquement. Aucune donnee modifiee. Aucune fusion appliquee : validation requise.**
