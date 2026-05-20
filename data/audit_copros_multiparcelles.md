# Audit copros multi-parcelles (RNC `reference_cadastrale_2/3`)

Source : snapshot RNC raw `data/secteur_*.json` (champ `reference_cadastrale_2`/`_3` non vide). Cette declaration **explicite** par RNC est la preuve la plus solide d'une copro RNC multi-bati sur plusieurs bgids BDNB distincts (cf. precedent fix Fondary/Croix Nivert `0b05a1e`).

**Note jointure cadastrale** : Paris (75) = jointure BDNB.l_parcelle_id <-> RNC.ref_cadastrale via normalisation `PARIS{arr}|{SECT}|{NUM}` ; Lyon Dauphine = jointure **indisponible** (l_parcelle_id absent dans `bdnb_dauphine_lacassagne.json`) -> fallback methode B (adresse compl <-> adresses[] light).


## [Motte-Picquet (Paris 15)]  (snapshot raw : 835 copros)

**Copros multi-parcelles** : 6 declarent au moins une `reference_cadastrale_2` (et/ou `_3`).

**Jointure cadastrale BDNB** : OUI (champ l_parcelle_id present).


**Cas actionnables (RESTANTS)** : 1 / 6 (copro visible + orphelin(s) **non encore fusionne(s)** vers cette ancre).

**Cas DEJA-FUSE-OK** : 3 (orphelins deja `_fa=True / _fc=ancre`, aucun fix requis - confirme par `scripts/fix_multiparcelles_dl_lot.py` dry-run du 2026-05-20).


### Detail des 6 copros multi-parcelles

| # | immat | nom | nlots | parc | rc1 | rc2 | rc3 | visible? | statut | candidats |
|--:|---|---|--:|--:|---|---|---|---|---|---|
| 1 | `AA3422532` | 5-11 bd Garibaldi | 39 | 2 | `CZ0064` | `CZ0066` | `—` | `5|BOULEVARD|GARIBALDI` | (aucun candidat) | — |
| 2 | `AB0562918` | 119 - 125 boulevard de grenelle | 130 | 2 | `DE0100` | `DE0099` | `—` | `119|BOULEVARD|GRENELLE` | ✓ deja-fuse-ok | `121|BOULEVARD|GRENELLE` ✓deja-fuse<br>`123|BOULEVARD|GRENELLE` ✓deja-fuse |
| 3 | `AB7861529` | village suffren EFGH - MS192006 | 115 | 3 | `DI0016` | `DI0010` | `DI0003` | `7|RUE|PRESLES` | **✅ RESTANT** | `14|PASSAGE|GUESCLIN` (bgid cadastral)<br>`14|PASSAGE|GUESCLIN` (compl)<br>`2|PASSAGE|GUESCLIN` (bgid cadastral)<br>`2|PASSAGE|GUESCLIN` (compl)<br>`4|RUE|PRESLES` (bgid cadastral)<br>`88|RUE|FEDERATION` (bgid cadastral)<br>`8|PASSAGE|GUESCLIN` (bgid cadastral)<br>`8|PASSAGE|GUESCLIN` (compl) |
| 4 | `AB9273434` | SDC 40/42 RUE DE LA CROIX NIVERT | 17 | 2 | `DF0112` | `DF0111` | `—` | `40|RUE|CROIX NIVERT` | ✓ deja-fuse-ok | `91|RUE|FONDARY` ✓deja-fuse |
| 5 | `AH1602424` | PARIS (75015) – 28 boulevard Garibal | 13 | 2 | `CX0054` | `CX0066` | `—` | ❌ INVISIBLE | — | `29|BOULEVARD|GARIBALDI` (bgid cadastral) |
| 6 | `AJ1220698` | 15 RUE GRAMME PARIS 75015 | 24 | 2 | `EG0073` | `EG0072` | `—` | `15|RUE|GRAMME` | ✓ deja-fuse-ok | `11||CITE THURE` ✓deja-fuse |

### Cas actionnables (fiche complete)


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

## [Dauphine-Lacassagne (Lyon 3e)]  (snapshot raw : 564 copros)

**Copros multi-parcelles** : 34 declarent au moins une `reference_cadastrale_2` (et/ou `_3`).

**Jointure cadastrale BDNB** : NON (champ l_parcelle_id absent dans bdnb_dauphine_lacassagne.json).


**Cas actionnables (RESTANTS)** : 7 / 34 (copro visible + orphelin(s) **non encore fusionne(s)** vers cette ancre).

**Cas DEJA-FUSE-OK** : 9 (orphelins deja `_fa=True / _fc=ancre`, aucun fix requis - confirme par `scripts/fix_multiparcelles_dl_lot.py` dry-run du 2026-05-20).


### Detail des 34 copros multi-parcelles

| # | immat | nom | nlots | parc | rc1 | rc2 | rc3 | visible? | statut | candidats |
|--:|---|---|--:|--:|---|---|---|---|---|---|
| 1 | `AA0157016` | LES DAHLIAS | 62 | 2 | `BE0031` | `BE0008` | `—` | `11|RUE|DAHLIAS` | ✓ deja-fuse-ok | `13|RUE|DAHLIAS` ✓deja-fuse<br>`15|RUE|DAHLIAS` ✓deja-fuse |
| 2 | `AA0208264` | LE MARQUITA | 45 | 2 | `AZ0194` | `AZ0154` | `—` | `10|RUE|JEAN RENOIR` | (aucun candidat) | — |
| 3 | `AA0787333` | LES TERRASSES DE LA GARE | 80 | 2 | `EK0008` | `EK0007` | `—` | `11|AVENUE|GEORGES POMPIDOU` | ✓ deja-fuse-ok | `13|AVENUE|GEORGES POMPIDOU` ✓deja-fuse<br>`15|AVENUE|GEORGES POMPIDOU` ✓deja-fuse<br>`63|RUE|VILLETTE` ✓deja-fuse |
| 4 | `AA2213171` | REBATEL | 43 | 2 | `BK0017` | `BK0018` | `—` | `14|RUE|BARA` | (aucun candidat) | — |
| 5 | `AA3186756` | MARC SANGNIER | 52 | 2 | `CO0130` | `DW0044` | `—` | `2|RUE|FREDERIC MISTRAL` | (aucun candidat) | — |
| 6 | `AA4417416` | LE LACASSAGNE | 91 | 3 | `DR0140` | `DR0139` | `DR0138` | `10|AVENUE|LACASSAGNE` | ✓ deja-fuse-ok | `12|AVENUE|LACASSAGNE` ✓deja-fuse |
| 7 | `AA6259139` | ESPACE EMERAUDE BAT.J | 21 | 3 | `DV0005` | `DV0082` | `DV0083` | `48|RUE|STE ANNE DE BARABAN` | (aucun candidat) | — |
| 8 | `AA9260977` | CLAUDIUS PIONCHON | 69 | 3 | `DZ0082` | `DZ0083` | `DZ0084` | `16|RUE|ST VICTORIEN` | **✅ RESTANT** | `16|RUE|CLAUDIUS PIONCHON` (compl) |
| 9 | `AB2926236` | LE SAINT GERMAIN | 56 | 2 | `DP0019` | `DP0083` | `—` | `23|RUE|TURBIL` | **✅ RESTANT** | `260|RUE|PAUL BERT` (compl) |
| 10 | `AB4364022` | 3eme AVENUE - MS34651 | 31 | 3 | `DN0099` | `DN0097` | `DN0101` | `296|RUE|PAUL BERT` | **✅ RESTANT** | `298|RUE|PAUL BERT` (compl) |
| 11 | `AB4738928` | SAINT MAXIMIN | 76 | 3 | `BD0030` | `BD0103` | `BD0109` | `23|RUE|ST MAXIMIN` | **✅ RESTANT** | `5|RUE|MARCEL PEHU` (compl) |
| 12 | `AB4859047` | LE PARC SISLEY | 39 | 3 | `AZ0130` | `AZ0132` | `AZ0041` | `74|RUE|DAUPHINE` | **✅ RESTANT** | `6|RUE|PROFESSEUR PAUL SISLEY` (compl)<br>`76|RUE|DAUPHINE` (compl) |
| 13 | `AB5681887` | 200 AVENUE FELIX FAURE | 14 | 2 | `DO0078` | `DO0077` | `—` | `200|AVENUE|FELIX FAURE` | (aucun candidat) | — |
| 14 | `AB5772397` | BARABAN | 19 | 2 | `DZ0035` | `DZ0091` | `—` | `73|RUE|BARABAN` | (aucun candidat) | — |
| 15 | `AB7363229` | FONTAINE DE CYBELE | 122 | 3 | `AZ0183` | `AZ0182` | `AZ0145` | `50|RUE|DAUPHINE` | ✓ deja-fuse-ok | `52|RUE|DAUPHINE` ✓deja-fuse<br>`54|RUE|DAUPHINE` ✓deja-fuse |
| 16 | `AB7739527` | LES PORTES DE L'ESPLANADE | 85 | 2 | `AZ0233` | `AZ0205` | `—` | `42|AVENUE|LACASSAGNE` | ✓ deja-fuse-ok | `44|AVENUE|LACASSAGNE` ✓deja-fuse |
| 17 | `AB7762370` | LES ALLEES SISLEY | 41 | 3 | `AZ0185` | `AZ0184` | `AZ0151` | `42|RUE|DAUPHINE` | (aucun candidat) | — |
| 18 | `AB8349037` | LES JARDINS D'ELYANDE | 43 | 2 | `AZ0053` | `AZ0051` | `—` | `9|RUE|ROGER BRECHAN` | ✓ deja-fuse-ok | `11|RUE|ROGER BRECHAN` ✓deja-fuse |
| 19 | `AB9633892` | SAINT MAXIMIN | 58 | 2 | `BE0053` | `BE0057` | `—` | `27|RUE|ST MAXIMIN` | (aucun candidat) | — |
| 20 | `AC9350984` | LE PAVILLON DU DAUPHIN | 57 | 2 | `do0028` | `do0027` | `—` | `89|RUE|DAUPHINE` | **✅ RESTANT** | `14|RUE|CARRY` (compl)<br>`93|RUE|DAUPHINE` ✓deja-fuse |
| 21 | `AD4794368` | 251 RUE PAUL BERT | 9 | 2 | `DS0045` | `DS0047` | `—` | `251|RUE|PAUL BERT` | (aucun candidat) | — |
| 22 | `AD5268305` | LACASSAGNE | 98 | 3 | `BI0060` | `DR0221` | `DR0220` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | **✅ RESTANT** | `20|AVENUE|LACASSAGNE` (compl)<br>`22|AVENUE|LACASSAGNE` (compl) |
| 23 | `AD8245730` | Le Padoue | 34 | 3 | `DY0088` | `DY0082` | `DY0100` | `55|RUE|ST ANTOINE` | (aucun candidat) | — |
| 24 | `AF2458867` | ANGLE LUMIERE | 31 | 3 | `BC0040` | `BC0039` | `BC0041` | `13|RUE|ROSSAN` | ✓ deja-fuse-ok | `15|RUE|ROSSAN` ✓deja-fuse |
| 25 | `AF5123849` | LE LUMEN | 11 | 2 | `DN0066` | `DN0103` | `—` | `5||PTR ST EUSEBE` | (aucun candidat) | — |
| 26 | `AF5210398` | WAKE UP | 43 | 3 | `DR0068` | `DR0069` | `DR0070` | `166|RUE|BARABAN` | ✓ deja-fuse-ok | `168|RUE|BARABAN` ✓deja-fuse |
| 27 | `AF6359384` | 331 rue Paul Bert 69003 LYON | 2 | 3 | `DV0115` | `DV0114` | `DV0113` | `331|RUE|PAUL BERT` | (aucun candidat) | — |
| 28 | `AG0726372` | BARABAN | 25 | 3 | `DS0118` | `DS0115` | `DS0057` | `117|RUE|BARABAN` | (aucun candidat) | — |
| 29 | `AG6298160` | LE SPHINX | 34 | 2 | `BC0037` | `BC0084` | `—` | `41|COURS|ALBERT THOMAS 24 RUE DES TUILIERS` | (aucun candidat) | — |
| 30 | `AH0426635` | LE 43 | 23 | 3 | `DO0056` | `DO0057` | `DO0091` | `43|AVENUE|LACASSAGNE` | (aucun candidat) | — |
| 31 | `AH7871353` | RESIDENCE CLAUDIUS PIONCHON | 60 | 3 | `DZ0116` | `DZ0020` | `DZ0019` | `24|RUE|CLAUDIUS PIONCHON` | ✓ deja-fuse-ok | `26|RUE|CLAUDIUS PIONCHON` ✓deja-fuse<br>`28|RUE|CLAUDIUS PIONCHON` ✓deja-fuse |
| 32 | `AI3897188` | SAINT-EUSEBE | 25 | 3 | `DW0066` | `CO0153` | `CO0154` | `25|RUE|ST EUSEBE` | (aucun candidat) | — |
| 33 | `AI6621486` | COPROPRIETE 254 RUE PAUL BERT | 7 | 2 | `DP0066` | `DP0007` | `—` | `254|RUE|PAUL BERT` | (aucun candidat) | — |
| 34 | `AJ3763760` | 1 RUE DE LA VILLETTE LYON | 12 | 2 | `EI0117` | `EI0039` | `—` | `1|RUE|VILLETTE` | (aucun candidat) | — |

### Cas actionnables (fiche complete)


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

#### 20. `AC9350984` — LE PAVILLON DU DAUPHIN
- **Adresse de reference** : `89 r du dauphine 69003 Lyon`
- **Lots habitation** : 57 · **Syndic** : SOC ADMIN & GESTION IMMEUB ROLIN BAINSON  · **Mandat** : Mandat en cours
- **Visible (ancre principale dans light)** : `89|RUE|DAUPHINE`
- **Parcelles RNC** :
   - `69123383do0028` -> key=`LYON383|DO|0028` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
   - `69123383do0027` -> key=`LYON383|DO|0027` -> bgids: _(non trouve dans BDNB)_ -> adresses[]: _(aucune adresse light)_
- **Adresses orphelines (jointure compl RNC)** :
   - compl `'14 r carry 69003 Lyon'` -> `14|RUE|CARRY` — bgid `bdnb-bg-FW4B-YECQ-FPCT` — nb_log_bdnb=9 — vlog=1 — _fa=True

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

---
## Bilan global

- Copros multi-parcelles RNC scannees : **40** sur les 2 secteurs.
- Cas **actionnables** (copro visible + au moins un orphelin hors-RNC sur une autre parcelle/bgid) : **8**.

**Lecture des colonnes orphelin** : `vlog` = ventes logement actuelles sur l'adresse orpheline (pertinence DVF) ; `_fa=True` indique que l'adresse est deja fusionnee ailleurs - re-pointer la chaine entiere (voir `_fusion_cible`).

### Synthese des cas actionnables (orphelins dedupliques)

| sect | immat | ancre | orphelin | vlog | nb_log_bdnb | _fa | _fc | nom copro | nlots |
|---|---|---|---|--:|--:|---|---|---|--:|
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `14|PASSAGE|GUESCLIN` | 0 | 42 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `2|PASSAGE|GUESCLIN` | 0 | 17 | ✅ | `14|PASSAGE|GUESCLIN` | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `4|RUE|PRESLES` | 0 | 35 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `88|RUE|FEDERATION` | 0 | 181 | — | — | village suffren EFGH - MS19200 | 115 |
| motte_ | `AB7861529` | `7|RUE|PRESLES` | `8|PASSAGE|GUESCLIN` | 0 | 22 | ✅ | `14|PASSAGE|GUESCLIN` | village suffren EFGH - MS19200 | 115 |
| dauphi | `AA9260977` | `16|RUE|ST VICTORIEN` | `16|RUE|CLAUDIUS PIONCHON` | 1 | 23 | — | — | CLAUDIUS PIONCHON | 69 |
| dauphi | `AB2926236` | `23|RUE|TURBIL` | `260|RUE|PAUL BERT` | 5 | 1 | ✅ | `264B|RUE|PAUL BERT` | LE SAINT GERMAIN | 56 |
| dauphi | `AB4364022` | `296|RUE|PAUL BERT` | `298|RUE|PAUL BERT` | 0 | 31 | — | — | 3eme AVENUE - MS34651 | 31 |
| dauphi | `AB4738928` | `23|RUE|ST MAXIMIN` | `5|RUE|MARCEL PEHU` | 4 | 32 | — | — | SAINT MAXIMIN | 76 |
| dauphi | `AB4859047` | `74|RUE|DAUPHINE` | `6|RUE|PROFESSEUR PAUL SISLEY` | 2 | 6 | — | — | LE PARC SISLEY | 39 |
| dauphi | `AB4859047` | `74|RUE|DAUPHINE` | `76|RUE|DAUPHINE` | 2 | 39 | — | — | LE PARC SISLEY | 39 |
| dauphi | `AC9350984` | `89|RUE|DAUPHINE` | `14|RUE|CARRY` | 1 | 9 | ✅ | `6|RUE|CARRY` | LE PAVILLON DU DAUPHIN | 57 |
| dauphi | `AD5268305` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | `20|AVENUE|LACASSAGNE` | 0 | 97 | — | — | LACASSAGNE | 98 |
| dauphi | `AD5268305` | `20B|AVENUE|LACASSAGNE 22 AVENUE LACASSAGNE` | `22|AVENUE|LACASSAGNE` | 2 | 38 | ✅ | `20|AVENUE|LACASSAGNE` | LACASSAGNE | 98 |

### Priorisation suggeree

- **5 orphelin(s) avec vlog ≥ 2** (priorite haute, ventes DVF a relocaliser) :
   - `AB2926236` (56 lots, REGIE CENTRALE IMMOBIL) <- `260|RUE|PAUL BERT` vlog=5
   - `AB4738928` (76 lots, FONCIA SAINT LOUIS ) <- `5|RUE|MARCEL PEHU` vlog=4
   - `AB4859047` (39 lots, REGIE FRANCOIS GOFFIN ) <- `6|RUE|PROFESSEUR PAUL SISLEY` vlog=2
   - `AB4859047` (39 lots, REGIE FRANCOIS GOFFIN ) <- `76|RUE|DAUPHINE` vlog=2
   - `AD5268305` (98 lots, FONCIA LYON ) <- `22|AVENUE|LACASSAGNE` vlog=2

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