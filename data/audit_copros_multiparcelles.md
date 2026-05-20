# Audit copros multi-parcelles (RNC `reference_cadastrale_2/3`)

Source : snapshot RNC raw `data/secteur_*.json` (champ `reference_cadastrale_2`/`_3` non vide). Cette declaration **explicite** par RNC est la preuve la plus solide d'une copro RNC multi-bati sur plusieurs bgids BDNB distincts (cf. precedent fix Fondary/Croix Nivert `0b05a1e`).

**Note jointure cadastrale** : Paris (75) = jointure BDNB.l_parcelle_id <-> RNC.ref_cadastrale via normalisation `PARIS{arr}|{SECT}|{NUM}` ; Lyon Dauphine = jointure **indisponible** (l_parcelle_id absent dans `bdnb_dauphine_lacassagne.json`) -> fallback methode B (adresse compl <-> adresses[] light).


## [Motte-Picquet (Paris 15)]  (snapshot raw : 835 copros)

**Copros multi-parcelles** : 6 declarent au moins une `reference_cadastrale_2` (et/ou `_3`).

**Jointure cadastrale BDNB** : OUI (champ l_parcelle_id present).


**Cas actionnables** : 4 / 6 (copro visible + adresse(s) orpheline(s) hors-RNC sur une autre parcelle/bgid).


### Detail des 6 copros multi-parcelles

| # | immat | nom | nlots | parc | rc1 | rc2 | rc3 | visible? | actionnable ? | candidats |
|--:|---|---|--:|--:|---|---|---|---|---|---|
| 1 | `AA3422532` | 5-11 bd Garibaldi | 39 | 2 | `CZ0064` | `CZ0066` | `—` | `5|BOULEVARD|GARIBALDI` | (visible, aucun candidat) | — |
| 2 | `AB0562918` | 119 - 125 boulevard de grenelle | 130 | 2 | `DE0100` | `DE0099` | `—` | `119|BOULEVARD|GRENELLE` | **✅ OUI** | `121|BOULEVARD|GRENELLE` (bgid cadastral)<br>`123|BOULEVARD|GRENELLE` (bgid cadastral) |
| 3 | `AB7861529` | village suffren EFGH - MS192006 | 115 | 3 | `DI0016` | `DI0010` | `DI0003` | `7|RUE|PRESLES` | **✅ OUI** | `14|PASSAGE|GUESCLIN` (bgid cadastral)<br>`14|PASSAGE|GUESCLIN` (compl)<br>`2|PASSAGE|GUESCLIN` (bgid cadastral)<br>`2|PASSAGE|GUESCLIN` (compl)<br>`4|RUE|PRESLES` (bgid cadastral)<br>`88|RUE|FEDERATION` (bgid cadastral)<br>`8|PASSAGE|GUESCLIN` (bgid cadastral)<br>`8|PASSAGE|GUESCLIN` (compl) |
| 4 | `AB9273434` | SDC 40/42 RUE DE LA CROIX NIVERT | 17 | 2 | `DF0112` | `DF0111` | `—` | `40|RUE|CROIX NIVERT` | **✅ OUI** | `91|RUE|FONDARY` (bgid cadastral)<br>`91|RUE|FONDARY` (compl) |
| 5 | `AH1602424` | PARIS (75015) – 28 boulevard Garibal | 13 | 2 | `CX0054` | `CX0066` | `—` | ❌ INVISIBLE | — | `29|BOULEVARD|GARIBALDI` (bgid cadastral) |
| 6 | `AJ1220698` | 15 RUE GRAMME PARIS 75015 | 24 | 2 | `EG0073` | `EG0072` | `—` | `15|RUE|GRAMME` | **✅ OUI** | `11||CITE THURE` (bgid cadastral) |

### Cas actionnables (fiche complete)


#### 2. `AB0562918` — 119 - 125 boulevard de grenelle
- **Adresse de reference** : `119 bd de grenelle 75015 Paris`
- **Lots habitation** : 130 · **Syndic** : CABINET PIERRE BONNEFOI SA  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `119|BOULEVARD|GRENELLE`
- **Parcelles RNC** :
   - `75056115DE0100` -> key=`PARIS15|DE|0100` -> bgids: `bdnb-bg-T4ZX-2WDY-QMS7` -> adresses[]: `119|BOULEVARD|GRENELLE` (immat=AB0562918), `121|BOULEVARD|GRENELLE` (immat=None), `123|BOULEVARD|GRENELLE` (immat=None)
   - `75056115DE0099` -> key=`PARIS15|DE|0099` -> bgids: `bdnb-bg-T4ZX-2WDY-QMS7` -> adresses[]: `119|BOULEVARD|GRENELLE` (immat=AB0562918), `121|BOULEVARD|GRENELLE` (immat=None), `123|BOULEVARD|GRENELLE` (immat=None)
- **Adresses orphelines (jointure cadastrale)** :
   - `121|BOULEVARD|GRENELLE` — bgid `bdnb-bg-T4ZX-2WDY-QMS7` — nb_log_bdnb=111 — vlog=0 — _fa=True
   - `123|BOULEVARD|GRENELLE` — bgid `bdnb-bg-T4ZX-2WDY-QMS7` — nb_log_bdnb=111 — vlog=0 — _fa=True

#### 3. `AB7861529` — village suffren EFGH - MS192006
- **Adresse de reference** : `7 r de presles 75015 Paris`
- **Lots habitation** : 115 · **Syndic** : GERARD SAFAR SAS  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `7|RUE|PRESLES`
- **Parcelles RNC** :
   - `75056115DI0016` -> key=`PARIS15|DI|0016` -> bgids: `bdnb-bg-PS7Y-T8QH-F26C`, `bdnb-bg-QX4P-4SRC-PQKA`, `bdnb-bg-TW35-U22F-U92T` -> adresses[]: `8|PASSAGE|GUESCLIN` (immat=None), `2|PASSAGE|GUESCLIN` (immat=None), `14|PASSAGE|GUESCLIN` (immat=None)
   - `75056115DI0010` -> key=`PARIS15|DI|0010` -> bgids: `bdnb-bg-QNW4-6U22-1GTJ` -> adresses[]: `4|RUE|PRESLES` (immat=None), `7|RUE|PRESLES` (immat=AB7861529)
   - `75056115DI0003` -> key=`PARIS15|DI|0003` -> bgids: `bdnb-bg-69B5-LL5X-E2NB`, `bdnb-bg-8V28-KGX2-QBQS` -> adresses[]: `88|RUE|FEDERATION` (immat=None), `86|RUE|FEDERATION` (immat=AB6092555), `82|RUE|FEDERATION` (immat=AB6091565)
- **Adresses orphelines (jointure cadastrale)** :
   - `8|PASSAGE|GUESCLIN` — bgid `bdnb-bg-PS7Y-T8QH-F26C` — nb_log_bdnb=22 — vlog=0 — _fa=True
   - `2|PASSAGE|GUESCLIN` — bgid `bdnb-bg-QX4P-4SRC-PQKA` — nb_log_bdnb=17 — vlog=0 — _fa=True
   - `14|PASSAGE|GUESCLIN` — bgid `bdnb-bg-TW35-U22F-U92T` — nb_log_bdnb=42 — vlog=0 — _fa=None
   - `4|RUE|PRESLES` — bgid `bdnb-bg-QNW4-6U22-1GTJ` — nb_log_bdnb=35 — vlog=0 — _fa=None
   - `88|RUE|FEDERATION` — bgid `bdnb-bg-69B5-LL5X-E2NB` — nb_log_bdnb=181 — vlog=0 — _fa=None
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'2 pas du guesclin 75015 Paris'` -> `2|PASSAGE|GUESCLIN` — bgid `bdnb-bg-QX4P-4SRC-PQKA` — nb_log_bdnb=17 — vlog=0 — _fa=True
   - compl `'8 pas du guesclin 75015 Paris'` -> `8|PASSAGE|GUESCLIN` — bgid `bdnb-bg-PS7Y-T8QH-F26C` — nb_log_bdnb=22 — vlog=0 — _fa=True
   - compl `'14 pas du guesclin 75015 Paris'` -> `14|PASSAGE|GUESCLIN` — bgid `bdnb-bg-TW35-U22F-U92T` — nb_log_bdnb=42 — vlog=0 — _fa=None

#### 4. `AB9273434` — SDC 40/42 RUE DE LA CROIX NIVERT
- **Adresse de reference** : `40 r de la croix nivert 75015 Paris`
- **Lots habitation** : 17 · **Syndic** : — · **Mandat** : Pas de mandat en cours
- **Visible (ancre principale dans light)** : `40|RUE|CROIX NIVERT`
- **Parcelles RNC** :
   - `75056115DF0112` -> key=`PARIS15|DF|0112` -> bgids: `bdnb-bg-DN3P-4R65-2XG2` -> adresses[]: _(aucune adresse light)_
   - `75056115DF0111` -> key=`PARIS15|DF|0111` -> bgids: `bdnb-bg-STYB-453N-Y18X` -> adresses[]: `40|RUE|CROIX NIVERT` (immat=AB9273434), `91|RUE|FONDARY` (immat=None)
- **Adresses orphelines (jointure cadastrale)** :
   - `91|RUE|FONDARY` — bgid `bdnb-bg-STYB-453N-Y18X` — nb_log_bdnb=8 — vlog=1 — _fa=True
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'91 r fondary 75015 Paris'` -> `91|RUE|FONDARY` — bgid `bdnb-bg-STYB-453N-Y18X` — nb_log_bdnb=8 — vlog=1 — _fa=True

#### 6. `AJ1220698` — 15 RUE GRAMME PARIS 75015
- **Adresse de reference** : `15 Rue Gramme 75015 Paris`
- **Lots habitation** : 24 · **Syndic** : R. J. TRODE ET COMPAGNIE  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `15|RUE|GRAMME`
- **Parcelles RNC** :
   - `75056115EG0073` -> key=`PARIS15|EG|0073` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `75056115EG0072` -> key=`PARIS15|EG|0072` -> bgids: `bdnb-bg-5M1L-C8YG-8NE1` -> adresses[]: `15|RUE|GRAMME` (immat=AJ1220698), `11||CITE THURE` (immat=None)
- **Adresses orphelines (jointure cadastrale)** :
   - `11||CITE THURE` — bgid `bdnb-bg-5M1L-C8YG-8NE1` — nb_log_bdnb=26 — vlog=3 — _fa=True

## [Dauphine-Lacassagne (Lyon 3e)]  (snapshot raw : 564 copros)

**Copros multi-parcelles** : 34 declarent au moins une `reference_cadastrale_2` (et/ou `_3`).

**Jointure cadastrale BDNB** : NON (champ l_parcelle_id absent dans bdnb_dauphine_lacassagne.json).


**Cas actionnables** : 16 / 34 (copro visible + adresse(s) orpheline(s) hors-RNC sur une autre parcelle/bgid).


### Detail des 34 copros multi-parcelles

| # | immat | nom | nlots | parc | rc1 | rc2 | rc3 | visible? | actionnable ? | candidats |
|--:|---|---|--:|--:|---|---|---|---|---|---|
| 1 | `AA0157016` | LES DAHLIAS | 62 | 2 | `BE0031` | `BE0008` | `—` | `11|RUE|DAHLIAS` | **✅ OUI** | `13|RUE|DAHLIAS` (compl)<br>`15|RUE|DAHLIAS` (compl) |
| 2 | `AA0208264` | LE MARQUITA | 45 | 2 | `AZ0194` | `AZ0154` | `—` | `10|RUE|JEAN RENOIR` | (visible, aucun candidat) | — |
| 3 | `AA0787333` | LES TERRASSES DE LA GARE | 80 | 2 | `EK0008` | `EK0007` | `—` | `11|AVENUE|GEORGES POMPIDOU` | **✅ OUI** | `13|AVENUE|GEORGES POMPIDOU` (compl)<br>`15|AVENUE|GEORGES POMPIDOU` (compl)<br>`63|RUE|VILLETTE` (compl) |
| 4 | `AA2213171` | REBATEL | 43 | 2 | `BK0017` | `BK0018` | `—` | `14|RUE|BARA` | (visible, aucun candidat) | — |
| 5 | `AA3186756` | MARC SANGNIER | 52 | 2 | `CO0130` | `DW0044` | `—` | `2|RUE|FREDERIC MISTRAL` | (visible, aucun candidat) | — |
| 6 | `AA4417416` | LE LACASSAGNE | 91 | 3 | `DR0140` | `DR0139` | `DR0138` | `10|AVENUE|LACASSAGNE` | **✅ OUI** | `12|AVENUE|LACASSAGNE` (compl) |
| 7 | `AA6259139` | ESPACE EMERAUDE BAT.J | 21 | 3 | `DV0005` | `DV0082` | `DV0083` | `48|RUE|STE ANNE DE BARABAN` | (visible, aucun candidat) | — |
| 8 | `AA9260977` | CLAUDIUS PIONCHON | 69 | 3 | `DZ0082` | `DZ0083` | `DZ0084` | `16|RUE|ST VICTORIEN` | **✅ OUI** | `16|RUE|CLAUDIUS PIONCHON` (compl) |
| 9 | `AB2926236` | LE SAINT GERMAIN | 56 | 2 | `DP0019` | `DP0083` | `—` | `23|RUE|TURBIL` | **✅ OUI** | `260|RUE|PAUL BERT` (compl) |
| 10 | `AB4364022` | 3eme AVENUE - MS34651 | 31 | 3 | `DN0099` | `DN0097` | `DN0101` | `296|RUE|PAUL BERT` | **✅ OUI** | `298|RUE|PAUL BERT` (compl) |
| 11 | `AB4738928` | SAINT MAXIMIN | 76 | 3 | `BD0030` | `BD0103` | `BD0109` | `23|RUE|ST MAXIMIN` | **✅ OUI** | `5|RUE|MARCEL PEHU` (compl) |
| 12 | `AB4859047` | LE PARC SISLEY | 39 | 3 | `AZ0130` | `AZ0132` | `AZ0041` | `74|RUE|DAUPHINE` | **✅ OUI** | `6|RUE|PROFESSEUR PAUL SISLEY` (compl)<br>`76|RUE|DAUPHINE` (compl) |
| 13 | `AB5681887` | 200 AVENUE FELIX FAURE | 14 | 2 | `DO0078` | `DO0077` | `—` | `200|AVENUE|FELIX FAURE` | (visible, aucun candidat) | — |
| 14 | `AB5772397` | BARABAN | 19 | 2 | `DZ0035` | `DZ0091` | `—` | `73|RUE|BARABAN` | (visible, aucun candidat) | — |
| 15 | `AB7363229` | FONTAINE DE CYBELE | 122 | 3 | `AZ0183` | `AZ0182` | `AZ0145` | `50|RUE|DAUPHINE` | **✅ OUI** | `52|RUE|DAUPHINE` (compl)<br>`54|RUE|DAUPHINE` (compl) |
| 16 | `AB7739527` | LES PORTES DE L'ESPLANADE | 85 | 2 | `AZ0233` | `AZ0205` | `—` | `42|AVENUE|LACASSAGNE` | **✅ OUI** | `44|AVENUE|LACASSAGNE` (compl) |
| 17 | `AB7762370` | LES ALLEES SISLEY | 41 | 3 | `AZ0185` | `AZ0184` | `AZ0151` | `42|RUE|DAUPHINE` | (visible, aucun candidat) | — |
| 18 | `AB8349037` | LES JARDINS D'ELYANDE | 43 | 2 | `AZ0053` | `AZ0051` | `—` | `9|RUE|ROGER BRECHAN` | **✅ OUI** | `11|RUE|ROGER BRECHAN` (compl) |
| 19 | `AB9633892` | SAINT MAXIMIN | 58 | 2 | `BE0053` | `BE0057` | `—` | `27|RUE|ST MAXIMIN` | (visible, aucun candidat) | — |
| 20 | `AC9350984` | LE PAVILLON DU DAUPHIN | 57 | 2 | `do0028` | `do0027` | `—` | `89|RUE|DAUPHINE` | **✅ OUI** | `14|RUE|CARRY` (compl)<br>`93|RUE|DAUPHINE` (compl) |
| 21 | `AD4794368` | 251 RUE PAUL BERT | 9 | 2 | `DS0045` | `DS0047` | `—` | `251|RUE|PAUL BERT` | (visible, aucun candidat) | — |
| 22 | `AD5268305` | LACASSAGNE | 98 | 3 | `BI0060` | `DR0221` | `DR0220` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | **✅ OUI** | `20|AVENUE|LACASSAGNE` (compl)<br>`22|AVENUE|LACASSAGNE` (compl) |
| 23 | `AD8245730` | Le Padoue | 34 | 3 | `DY0088` | `DY0082` | `DY0100` | `55|RUE|ST ANTOINE` | (visible, aucun candidat) | — |
| 24 | `AF2458867` | ANGLE LUMIERE | 31 | 3 | `BC0040` | `BC0039` | `BC0041` | `13|RUE|ROSSAN` | **✅ OUI** | `15|RUE|ROSSAN` (compl) |
| 25 | `AF5123849` | LE LUMEN | 11 | 2 | `DN0066` | `DN0103` | `—` | `5||PTR ST EUSEBE` | (visible, aucun candidat) | — |
| 26 | `AF5210398` | WAKE UP | 43 | 3 | `DR0068` | `DR0069` | `DR0070` | `166|RUE|BARABAN` | **✅ OUI** | `168|RUE|BARABAN` (compl) |
| 27 | `AF6359384` | 331 rue Paul Bert 69003 LYON | 2 | 3 | `DV0115` | `DV0114` | `DV0113` | `331|RUE|PAUL BERT` | (visible, aucun candidat) | — |
| 28 | `AG0726372` | BARABAN | 25 | 3 | `DS0118` | `DS0115` | `DS0057` | `117|RUE|BARABAN` | (visible, aucun candidat) | — |
| 29 | `AG6298160` | LE SPHINX | 34 | 2 | `BC0037` | `BC0084` | `—` | `41|COURS|ALBERT THOMAS 24 RUE DES TUILIERS` | (visible, aucun candidat) | — |
| 30 | `AH0426635` | LE 43 | 23 | 3 | `DO0056` | `DO0057` | `DO0091` | `43|AVENUE|LACASSAGNE` | (visible, aucun candidat) | — |
| 31 | `AH7871353` | RESIDENCE CLAUDIUS PIONCHON | 60 | 3 | `DZ0116` | `DZ0020` | `DZ0019` | `24|RUE|CLAUDIUS PIONCHON` | **✅ OUI** | `26|RUE|CLAUDIUS PIONCHON` (compl)<br>`28|RUE|CLAUDIUS PIONCHON` (compl) |
| 32 | `AI3897188` | SAINT-EUSEBE | 25 | 3 | `DW0066` | `CO0153` | `CO0154` | `25|RUE|ST EUSEBE` | (visible, aucun candidat) | — |
| 33 | `AI6621486` | COPROPRIETE 254 RUE PAUL BERT | 7 | 2 | `DP0066` | `DP0007` | `—` | `254|RUE|PAUL BERT` | (visible, aucun candidat) | — |
| 34 | `AJ3763760` | 1 RUE DE LA VILLETTE LYON | 12 | 2 | `EI0117` | `EI0039` | `—` | `1|RUE|VILLETTE` | (visible, aucun candidat) | — |

### Cas actionnables (fiche complete)


#### 1. `AA0157016` — LES DAHLIAS
- **Adresse de reference** : `11 r des dahlias 69003 Lyon`
- **Lots habitation** : 62 · **Syndic** : GRANDLYON HABITAT - OFFICE PUBLIC DE L'HABITAT  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `11|RUE|DAHLIAS`
- **Parcelles RNC** :
   - `69123383BE0031` -> key=`LYON383|BE|0031` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383BE0008` -> key=`LYON383|BE|0008` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'15 r des dahlias 69003 Lyon'` -> `15|RUE|DAHLIAS` — bgid `bdnb-bg-PM1U-PYK6-UUL8` — nb_log_bdnb=25 — vlog=0 — _fa=True
   - compl `'13 r des dahlias 69003 Lyon'` -> `13|RUE|DAHLIAS` — bgid `bdnb-bg-342F-4SYF-US1H` — nb_log_bdnb=18 — vlog=11 — _fa=True

#### 3. `AA0787333` — LES TERRASSES DE LA GARE
- **Adresse de reference** : `11 av georges pompidou 69003 Lyon`
- **Lots habitation** : 80 · **Syndic** : ESPACE IMMOBILIER LYONNAIS  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `11|AVENUE|GEORGES POMPIDOU`
- **Parcelles RNC** :
   - `69123383EK0008` -> key=`LYON383|EK|0008` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383EK0007` -> key=`LYON383|EK|0007` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'15 av georges pompidou 69003 Lyon'` -> `15|AVENUE|GEORGES POMPIDOU` — bgid `bdnb-bg-HQEA-L5JU-AGCT` — nb_log_bdnb=20 — vlog=3 — _fa=True
   - compl `'13 av georges pompidou 69003 Lyon'` -> `13|AVENUE|GEORGES POMPIDOU` — bgid `bdnb-bg-HQEA-L5JU-AGCT` — nb_log_bdnb=20 — vlog=3 — _fa=True
   - compl `'63 r de la villette 69003 Lyon'` -> `63|RUE|VILLETTE` — bgid `bdnb-bg-BENR-J4R2-X2NB` — nb_log_bdnb=66 — vlog=2 — _fa=True

#### 6. `AA4417416` — LE LACASSAGNE
- **Adresse de reference** : `10 av lacassagne 69003 Lyon`
- **Lots habitation** : 91 · **Syndic** : N G PARTNERS  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `10|AVENUE|LACASSAGNE`
- **Parcelles RNC** :
   - `69123383DR0140` -> key=`LYON383|DR|0140` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0139` -> key=`LYON383|DR|0139` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0138` -> key=`LYON383|DR|0138` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'12 av lacassagne 69003 Lyon'` -> `12|AVENUE|LACASSAGNE` — bgid `bdnb-bg-HV4Y-ENCA-KLHP` — nb_log_bdnb=24 — vlog=11 — _fa=True

#### 8. `AA9260977` — CLAUDIUS PIONCHON
- **Adresse de reference** : `16 r saint-victorien 69003 Lyon`
- **Lots habitation** : 69 · **Syndic** : MALSH PROPERTY  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `16|RUE|ST VICTORIEN`
- **Parcelles RNC** :
   - `69123383DZ0082` -> key=`LYON383|DZ|0082` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DZ0083` -> key=`LYON383|DZ|0083` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DZ0084` -> key=`LYON383|DZ|0084` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'16 r claudius pionchon 69003 Lyon'` -> `16|RUE|CLAUDIUS PIONCHON` — bgid `bdnb-bg-5N1W-CV3S-R6RD` — nb_log_bdnb=23 — vlog=1 — _fa=None

#### 9. `AB2926236` — LE SAINT GERMAIN
- **Adresse de reference** : `23 r turbil 69003 Lyon`
- **Lots habitation** : 56 · **Syndic** : REGIE CENTRALE IMMOBILIERE  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `23|RUE|TURBIL`
- **Parcelles RNC** :
   - `69123383DP0019` -> key=`LYON383|DP|0019` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DP0083` -> key=`LYON383|DP|0083` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'260 r paul bert 69003 Lyon'` -> `260|RUE|PAUL BERT` — bgid `bdnb-bg-D9LP-CBCP-F74E` — nb_log_bdnb=1 — vlog=5 — _fa=True

#### 10. `AB4364022` — 3eme AVENUE - MS34651
- **Adresse de reference** : `296 r paul bert 69003 LYON`
- **Lots habitation** : 31 · **Syndic** : REGIE JANIN ET CIE  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `296|RUE|PAUL BERT`
- **Parcelles RNC** :
   - `69383000DN0099` -> key=`LYON383|DN|0099` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69383000DN0097` -> key=`LYON383|DN|0097` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69383000DN0101` -> key=`LYON383|DN|0101` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'298 r paul bert 69003 LYON'` -> `298|RUE|PAUL BERT` — bgid `bdnb-bg-MNMB-7F9F-2TDS` — nb_log_bdnb=31 — vlog=0 — _fa=None

#### 11. `AB4738928` — SAINT MAXIMIN
- **Adresse de reference** : `23 Rue Saint Maximin 69003 Lyon`
- **Lots habitation** : 76 · **Syndic** : FONCIA SAINT LOUIS  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `23|RUE|ST MAXIMIN`
- **Parcelles RNC** :
   - `69123383BD0030` -> key=`LYON383|BD|0030` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383BD0103` -> key=`LYON383|BD|0103` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383BD0109` -> key=`LYON383|BD|0109` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'5 Rue Marcel Pehu 69003 Lyon'` -> `5|RUE|MARCEL PEHU` — bgid `bdnb-bg-GMWN-9ZYS-LQGQ` — nb_log_bdnb=32 — vlog=4 — _fa=None

#### 12. `AB4859047` — LE PARC SISLEY
- **Adresse de reference** : `74 r du dauphine 69003 Lyon`
- **Lots habitation** : 39 · **Syndic** : REGIE FRANCOIS GOFFIN  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `74|RUE|DAUPHINE`
- **Parcelles RNC** :
   - `69123383AZ0130` -> key=`LYON383|AZ|0130` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0132` -> key=`LYON383|AZ|0132` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0041` -> key=`LYON383|AZ|0041` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'76 r du dauphine 69003 Lyon'` -> `76|RUE|DAUPHINE` — bgid `bdnb-bg-ULHW-P9KF-JSGH` — nb_log_bdnb=39 — vlog=2 — _fa=None
   - compl `'6 r du professeur paul sisley 69003 Lyon'` -> `6|RUE|PROFESSEUR PAUL SISLEY` — bgid `bdnb-bg-AM81-DZPJ-QXMN` — nb_log_bdnb=6 — vlog=2 — _fa=None

#### 15. `AB7363229` — FONTAINE DE CYBELE
- **Adresse de reference** : `50 r du dauphine 69003 Lyon`
- **Lots habitation** : 122 · **Syndic** : REGIE FRANCOIS GOFFIN  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `50|RUE|DAUPHINE`
- **Parcelles RNC** :
   - `69123383AZ0183` -> key=`LYON383|AZ|0183` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0182` -> key=`LYON383|AZ|0182` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0145` -> key=`LYON383|AZ|0145` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'54 r du dauphine 69003 Lyon'` -> `54|RUE|DAUPHINE` — bgid `bdnb-bg-G2ZQ-H667-PH4K` — nb_log_bdnb=30 — vlog=6 — _fa=True
   - compl `'52 r du dauphine 69003 Lyon'` -> `52|RUE|DAUPHINE` — bgid `bdnb-bg-TD3K-MD6A-6F6R` — nb_log_bdnb=8 — vlog=6 — _fa=True

#### 16. `AB7739527` — LES PORTES DE L'ESPLANADE
- **Adresse de reference** : `42 av lacassagne 69003 Lyon`
- **Lots habitation** : 85 · **Syndic** : REGIE DE VENDIN  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `42|AVENUE|LACASSAGNE`
- **Parcelles RNC** :
   - `69123383AZ0233` -> key=`LYON383|AZ|0233` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0205` -> key=`LYON383|AZ|0205` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'44 av lacassagne 69003 Lyon'` -> `44|AVENUE|LACASSAGNE` — bgid `bdnb-bg-DUWL-V4G5-KYKL` — nb_log_bdnb=29 — vlog=8 — _fa=True

#### 18. `AB8349037` — LES JARDINS D'ELYANDE
- **Adresse de reference** : `9 r roger brechan 69003 Lyon`
- **Lots habitation** : 43 · **Syndic** : — · **Mandat** : Pas de mandat en cours
- **Visible (ancre principale dans light)** : `9|RUE|ROGER BRECHAN`
- **Parcelles RNC** :
   - `69123383AZ0053` -> key=`LYON383|AZ|0053` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383AZ0051` -> key=`LYON383|AZ|0051` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'11 r roger brechan 69003 Lyon'` -> `11|RUE|ROGER BRECHAN` — bgid `bdnb-bg-8ZRV-FM7X-XP77` — nb_log_bdnb=41 — vlog=6 — _fa=True

#### 20. `AC9350984` — LE PAVILLON DU DAUPHIN
- **Adresse de reference** : `89 r du dauphine 69003 Lyon`
- **Lots habitation** : 57 · **Syndic** : SOC ADMIN & GESTION IMMEUB ROLIN BAINSON  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `89|RUE|DAUPHINE`
- **Parcelles RNC** :
   - `69123383do0028` -> key=`LYON383|DO|0028` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383do0027` -> key=`LYON383|DO|0027` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'14 r carry 69003 Lyon'` -> `14|RUE|CARRY` — bgid `bdnb-bg-FW4B-YECQ-FPCT` — nb_log_bdnb=9 — vlog=1 — _fa=True
   - compl `'93 r du dauphine 69003 Lyon'` -> `93|RUE|DAUPHINE` — bgid `bdnb-bg-SAR3-A4XV-LE8B` — nb_log_bdnb=57 — vlog=4 — _fa=True

#### 22. `AD5268305` — LACASSAGNE
- **Adresse de reference** : `20-20 BIS AVENUE LACASSAGNE 22 AVENUE LACASSAGNE 69003 LYON`
- **Lots habitation** : 98 · **Syndic** : FONCIA LYON  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE`
- **Parcelles RNC** :
   - `69123383BI0060` -> key=`LYON383|BI|0060` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0221` -> key=`LYON383|DR|0221` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0220` -> key=`LYON383|DR|0220` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'20 AVENUE LACASSAGNE 69003 LYON'` -> `20|AVENUE|LACASSAGNE` — bgid `bdnb-bg-NHQQ-8MZ7-KS1W` — nb_log_bdnb=97 — vlog=0 — _fa=None
   - compl `'22 AVENUE LACASSAGNE 69003 LYON'` -> `22|AVENUE|LACASSAGNE` — bgid `bdnb-bg-9DFR-GCRL-WUGG` — nb_log_bdnb=38 — vlog=2 — _fa=True

#### 24. `AF2458867` — ANGLE LUMIERE
- **Adresse de reference** : `13 r rossan 69003 Lyon`
- **Lots habitation** : 31 · **Syndic** : AF GESTION LYON 2  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `13|RUE|ROSSAN`
- **Parcelles RNC** :
   - `69123383BC0040` -> key=`LYON383|BC|0040` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383BC0039` -> key=`LYON383|BC|0039` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383BC0041` -> key=`LYON383|BC|0041` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'15 r rossan 69003 Lyon'` -> `15|RUE|ROSSAN` — bgid `bdnb-bg-7E2X-558L-F9RE` — nb_log_bdnb=19 — vlog=3 — _fa=True

#### 26. `AF5210398` — WAKE UP
- **Adresse de reference** : `166 r baraban 69003 Lyon`
- **Lots habitation** : 43 · **Syndic** : FONCIA LYON  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `166|RUE|BARABAN`
- **Parcelles RNC** :
   - `69123383DR0068` -> key=`LYON383|DR|0068` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0069` -> key=`LYON383|DR|0069` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DR0070` -> key=`LYON383|DR|0070` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'168 r baraban 69003 Lyon'` -> `168|RUE|BARABAN` — bgid `bdnb-bg-Q7LS-WV66-NMGE` — nb_log_bdnb=43 — vlog=0 — _fa=True

#### 31. `AH7871353` — RESIDENCE CLAUDIUS PIONCHON
- **Adresse de reference** : `24 r claudius pionchon 69003 Lyon`
- **Lots habitation** : 60 · **Syndic** : GRANDLYON HABITAT - OFFICE PUBLIC DE L'HABITAT  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `24|RUE|CLAUDIUS PIONCHON`
- **Parcelles RNC** :
   - `69123383DZ0116` -> key=`LYON383|DZ|0116` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DZ0020` -> key=`LYON383|DZ|0020` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383DZ0019` -> key=`LYON383|DZ|0019` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'28 r claudius pionchon 69003 Lyon'` -> `28|RUE|CLAUDIUS PIONCHON` — bgid `bdnb-bg-JTAL-3RN1-KX5T` — nb_log_bdnb=61 — vlog=3 — _fa=True
   - compl `'26 r claudius pionchon 69003 Lyon'` -> `26|RUE|CLAUDIUS PIONCHON` — bgid `bdnb-bg-JTAL-3RN1-KX5T` — nb_log_bdnb=61 — vlog=4 — _fa=True

---
## Bilan global

- Copros multi-parcelles RNC scannees : **40** sur les 2 secteurs.
- Cas **actionnables** (copro visible + au moins un orphelin hors-RNC sur une autre parcelle/bgid) : **20**.

**Lecture des colonnes orphelin** : `vlog` = ventes logement actuelles sur l'adresse orpheline (pertinence DVF) ; `_fa=True` indique que l'adresse est deja fusionnee ailleurs - re-pointer la chaine entiere (voir `_fusion_cible`).

### Synthese des cas actionnables (orphelins dedupliques)

| sect | immat | ancre | orphelin | vlog | nb_log_bdnb | _fa | _fc | nom copro | nlots |
|---|---|---|---|--:|--:|---|---|---|--:|
| motte_ | `AB0562918` | `119|BOULEVARD|GRENELLE` | `121|BOULEVARD|GRENELLE` | 0 | 111 | ✅ | `119|BOULEVARD|GRENELLE` | 119 - 125 boulevard de grenell | 130 |
| motte_ | `AB0562918` | `119|BOULEVARD|GRENELLE` | `123|BOULEVARD|GRENELLE` | 0 | 111 | ✅ | `119|BOULEVARD|GRENELLE` | 119 - 125 boulevard de grenell | 130 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `14|PASSAGE|GUESCLIN` | 0 | 42 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `2|PASSAGE|GUESCLIN` | 0 | 17 | ✅ | `14|PASSAGE|GUESCLIN` | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `4|RUE|PRESLES` | 0 | 35 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `88|RUE|FEDERATION` | 0 | 181 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `8|PASSAGE|GUESCLIN` | 0 | 22 | ✅ | `14|PASSAGE|GUESCLIN` | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB9273434` | `40|RUE|CROIX NIVERT` | `91|RUE|FONDARY` | 1 | 8 | ✅ | `40|RUE|CROIX NIVERT` | SDC 40/42 RUE DE LA CROIX NIVE | 17 |
| motte_ | `AJ1220698` | `15|RUE|GRAMME` | `11||CITE THURE` | 3 | 26 | ✅ | `15|RUE|GRAMME` | 15 RUE GRAMME PARIS 75015 | 24 |
| dauphi | `AA0157016` | `11|RUE|DAHLIAS` | `13|RUE|DAHLIAS` | 11 | 18 | ✅ | `11|RUE|DAHLIAS` | LES DAHLIAS | 62 |
| dauphi | `AA0157016` | `11|RUE|DAHLIAS` | `15|RUE|DAHLIAS` | 0 | 25 | ✅ | `11|RUE|DAHLIAS` | LES DAHLIAS | 62 |
| dauphi | `AA0787333` | `11|AVENUE|GEORGES POMPIDOU` | `13|AVENUE|GEORGES POMPIDOU` | 3 | 20 | ✅ | `11|AVENUE|GEORGES POMPIDOU` | LES TERRASSES DE LA GARE | 80 |
| dauphi | `AA0787333` | `11|AVENUE|GEORGES POMPIDOU` | `15|AVENUE|GEORGES POMPIDOU` | 3 | 20 | ✅ | `11|AVENUE|GEORGES POMPIDOU` | LES TERRASSES DE LA GARE | 80 |
| dauphi | `AA0787333` | `11|AVENUE|GEORGES POMPIDOU` | `63|RUE|VILLETTE` | 2 | 66 | ✅ | `11|AVENUE|GEORGES POMPIDOU` | LES TERRASSES DE LA GARE | 80 |
| dauphi | `AA4417416` | `10|AVENUE|LACASSAGNE` | `12|AVENUE|LACASSAGNE` | 11 | 24 | ✅ | `10|AVENUE|LACASSAGNE` | LE LACASSAGNE | 91 |
| dauphi | `AA9260977` | `16|RUE|ST VICTORIEN` | `16|RUE|CLAUDIUS PIONCHON` | 1 | 23 | — | — | CLAUDIUS PIONCHON | 69 |
| dauphi | `AB2926236` | `23|RUE|TURBIL` | `260|RUE|PAUL BERT` | 5 | 1 | ✅ | `264B|RUE|PAUL BERT` | LE SAINT GERMAIN | 56 |
| dauphi | `AB4364022` | `296|RUE|PAUL BERT` | `298|RUE|PAUL BERT` | 0 | 31 | — | — | 3eme AVENUE - MS34651 | 31 |
| dauphi | `AB4738928` | `23|RUE|ST MAXIMIN` | `5|RUE|MARCEL PEHU` | 4 | 32 | — | — | SAINT MAXIMIN | 76 |
| dauphi | `AB4859047` | `74|RUE|DAUPHINE` | `6|RUE|PROFESSEUR PAUL SISLEY` | 2 | 6 | — | — | LE PARC SISLEY | 39 |
| dauphi | `AB4859047` | `74|RUE|DAUPHINE` | `76|RUE|DAUPHINE` | 2 | 39 | — | — | LE PARC SISLEY | 39 |
| dauphi | `AB7363229` | `50|RUE|DAUPHINE` | `52|RUE|DAUPHINE` | 6 | 8 | ✅ | `50|RUE|DAUPHINE` | FONTAINE DE CYBELE | 122 |
| dauphi | `AB7363229` | `50|RUE|DAUPHINE` | `54|RUE|DAUPHINE` | 6 | 30 | ✅ | `50|RUE|DAUPHINE` | FONTAINE DE CYBELE | 122 |
| dauphi | `AB7739527` | `42|AVENUE|LACASSAGNE` | `44|AVENUE|LACASSAGNE` | 8 | 29 | ✅ | `42|AVENUE|LACASSAGNE` | LES PORTES DE L'ESPLANADE | 85 |
| dauphi | `AB8349037` | `9|RUE|ROGER BRECHAN` | `11|RUE|ROGER BRECHAN` | 6 | 41 | ✅ | `9|RUE|ROGER BRECHAN` | LES JARDINS D'ELYANDE | 43 |
| dauphi | `AC9350984` | `89|RUE|DAUPHINE` | `14|RUE|CARRY` | 1 | 9 | ✅ | `6|RUE|CARRY` | LE PAVILLON DU DAUPHIN | 57 |
| dauphi | `AC9350984` | `89|RUE|DAUPHINE` | `93|RUE|DAUPHINE` | 4 | 57 | ✅ | `89|RUE|DAUPHINE` | LE PAVILLON DU DAUPHIN | 57 |
| dauphi | `AD5268305` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | `20|AVENUE|LACASSAGNE` | 0 | 97 | — | — | LACASSAGNE | 98 |
| dauphi | `AD5268305` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | `22|AVENUE|LACASSAGNE` | 2 | 38 | ✅ | `20|AVENUE|LACASSAGNE` | LACASSAGNE | 98 |
| dauphi | `AF2458867` | `13|RUE|ROSSAN` | `15|RUE|ROSSAN` | 3 | 19 | ✅ | `13|RUE|ROSSAN` | ANGLE LUMIERE | 31 |
| dauphi | `AF5210398` | `166|RUE|BARABAN` | `168|RUE|BARABAN` | 0 | 43 | ✅ | `166|RUE|BARABAN` | WAKE UP | 43 |
| dauphi | `AH7871353` | `24|RUE|CLAUDIUS PIONCHON` | `26|RUE|CLAUDIUS PIONCHON` | 4 | 61 | ✅ | `24|RUE|CLAUDIUS PIONCHON` | RESIDENCE CLAUDIUS PIONCHON | 60 |
| dauphi | `AH7871353` | `24|RUE|CLAUDIUS PIONCHON` | `28|RUE|CLAUDIUS PIONCHON` | 3 | 61 | ✅ | `24|RUE|CLAUDIUS PIONCHON` | RESIDENCE CLAUDIUS PIONCHON | 60 |

### Priorisation suggeree

- **19 orphelin(s) avec vlog ≥ 2** (priorite haute, ventes DVF a relocaliser) :
   - `AJ1220698` (24 lots, R. J. TRODE ET COMPAGN) <- `11||CITE THURE` vlog=3
   - `AA0157016` (62 lots, GRANDLYON HABITAT - OF) <- `13|RUE|DAHLIAS` vlog=11
   - `AA0787333` (80 lots, ESPACE IMMOBILIER LYON) <- `13|AVENUE|GEORGES POMPIDOU` vlog=3
   - `AA0787333` (80 lots, ESPACE IMMOBILIER LYON) <- `15|AVENUE|GEORGES POMPIDOU` vlog=3
   - `AA0787333` (80 lots, ESPACE IMMOBILIER LYON) <- `63|RUE|VILLETTE` vlog=2
   - `AA4417416` (91 lots, N G PARTNERS ) <- `12|AVENUE|LACASSAGNE` vlog=11
   - `AB2926236` (56 lots, REGIE CENTRALE IMMOBIL) <- `260|RUE|PAUL BERT` vlog=5
   - `AB4738928` (76 lots, FONCIA SAINT LOUIS ) <- `5|RUE|MARCEL PEHU` vlog=4
   - `AB4859047` (39 lots, REGIE FRANCOIS GOFFIN ) <- `6|RUE|PROFESSEUR PAUL SISLEY` vlog=2
   - `AB4859047` (39 lots, REGIE FRANCOIS GOFFIN ) <- `76|RUE|DAUPHINE` vlog=2
   - `AB7363229` (122 lots, REGIE FRANCOIS GOFFIN ) <- `52|RUE|DAUPHINE` vlog=6
   - `AB7363229` (122 lots, REGIE FRANCOIS GOFFIN ) <- `54|RUE|DAUPHINE` vlog=6
   - `AB7739527` (85 lots, REGIE DE VENDIN ) <- `44|AVENUE|LACASSAGNE` vlog=8
   - `AB8349037` (43 lots, —) <- `11|RUE|ROGER BRECHAN` vlog=6
   - `AC9350984` (57 lots, SOC ADMIN & GESTION IM) <- `93|RUE|DAUPHINE` vlog=4
   - `AD5268305` (98 lots, FONCIA LYON ) <- `22|AVENUE|LACASSAGNE` vlog=2
   - `AF2458867` (31 lots, AF GESTION LYON 2 ) <- `15|RUE|ROSSAN` vlog=3
   - `AH7871353` (60 lots, GRANDLYON HABITAT - OF) <- `26|RUE|CLAUDIUS PIONCHON` vlog=4
   - `AH7871353` (60 lots, GRANDLYON HABITAT - OF) <- `28|RUE|CLAUDIUS PIONCHON` vlog=3

- **Re-points sans ventes (`vlog=0`)** : interet principalement dedup multi-bgid (parc plus propre), pas de relocalisation DVF. Pattern Cambronne/Fondary.

- **Orphelins `_fa=True` (deja fusionnes ailleurs)** : le re-point vers la copro multi-parcelles correcte doit absorber la chaine de fusion existante. Pattern fix_pivot_bdnb_lot (chain_in -> meme ancre).

### Copros multi-parcelles INVISIBLES

**1 copro(s)** multi-parcelles dont l'immatriculation n'est present dans aucune adresse du light. Necessite injection prealable (pattern `fix_horsrnc_attribution` cat. A/B2 ou pattern Suffren si absente du snapshot RNC).

| sect | immat | nom | nlots | adr_ref | rc1 | rc2 | rc3 |
|---|---|---|--:|---|---|---|---|
| motte_ | `AH1602424` | PARIS (75015) – 28 boulevard Garib | 13 | 28 bd garibaldi 75015 Paris | `CX0054` | `CX0066` | `—` |

### Limites de l'audit

1. **Snapshot RNC fige** : le scan utilise `secteur_*.json` (snapshot ingere a une date donnee). Des copros peuvent avoir renseigne `reference_cadastrale_2/3` plus recemment dans RNC live - un re-scan periodique via RNC live pourrait reveler des cas supplementaires.
2. **Jointure cadastrale Lyon indisponible** : `bdnb_dauphine_lacassagne.json` n'a pas de `l_parcelle_id` -> seule la methode B (compl <-> adresses) est utilisee pour DL, plus fragile (depend du parsing d'adresse).
3. **Faux positifs methode B** : un match `compl -> cle adresse` peut correspondre a une autre copro homonyme (cf. 260 PAUL BERT vlog=5 mais nb_log_bdnb=1 = local commercial, ou 14 CARRY deja fusionne dans 6 CARRY). Verifier le bgid avant tout re-point.
4. **`_fa=True` indique deja fusionne** : un re-point doit absorber toute la chaine `_fusion_cible -> orphelin` (pattern `fix_pivot_bdnb_lot.absorbe_chaine`).


---
*Audit en lecture seule. Source : `secteur_*.json` snapshot RNC + `bdnb_*.json` BDNB enrichi + `secteur_*_light.json` (adresses + copros). Genere par `scripts/audit_copros_multiparcelles.py` (PYTHONUTF8=1).*