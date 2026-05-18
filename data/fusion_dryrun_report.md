# Dry-run fusion adresse->copro - Dauphine-Lacassagne

**Dry-run, rien d'applique.** Carte `secteurFusions` (forme localStorage `{srcCle: dstCleAdresse}`) pour les adresses hors-RNC actives **FUSION-MEME-BATI** : la copro existe deja au dashboard via une adresse du **meme batiment**, on relocalise les ventes DVF orphelines de l'adresse hors-RNC vers cette copro. Le parc est deja dedup `bg:bgid` (parc RNC pur) -> **aucune inflation**.

- Carte proposee : `data/secteurFusions_dryrun.json` (37 fusions)
- Application = charger cette carte dans `secteurFusions` (localStorage) **apres validation** ; non fait ici.

## Simulation (vraie `renderSecteur()`, sans -> avec fusions)

| Metrique | Avant | Apres | Delta attendu |
|---|--:|--:|---|
| Adresses affichees | 979 | 942 | -37 (sources retirees) |
| Copros RNC affichees | 527 | 527 | inchange (copro deja visible) |
| **Parc logements (secL)** | **17372** | **17372** | **0 (dedup bg:bgid)** |
| Ventes/an (brut) | 813.4 | 813.4 | 0 (relocalisation) |
| Ventes/an (strict) | 556 | 556 | 0 (relocalisation) |
| Taux secteur (brut) | 4.7% | 4.7% | 0 |
| Filtre Hors-RNC actifs | 121 | 84 | -37 |

### Invariants dry-run

- OK - parc secL INCHANGE (brut)
- OK - parc secL INCHANGE (strict)
- OK - ventes/an CONSERVEES (brut, relocalisation pure)
- OK - ventes/an CONSERVEES (strict)
- OK - taux secteur INCHANGE (brut)
- OK - nbShown -= 37 (sources fusionnees retirees)
- OK - hors-RNC actifs -= 37 (121 -> 84)
- OK - RNC affichees +0/=

> 37 fusions ; **127 ventes logement** reattribuees a leur copro (numerateur de rotation deplace vers la bonne copro ; total secteur conserve).

## Detail des fusions proposees

| # | Adresse hors-RNC (src) | -> Copro (dst cle_adresse) | immat | Syndic | lots | ventes_log | ventes_brut/an |
|--:|---|---|---|---|--:|--:|---|
| 1 | 36 RUE ST PHILIPPE `36\|RUE\|ST PHILIPPE` | 34/36 Rue Saint Philippe `34\|RUE\|ST PHILIPPE` | AC8791634 | COTRIMO GESTION | 28 | 9 | [1,3,2,2,1] |
| 2 | 194 AVENUE FELIX FAURE `194\|AVENUE\|FELIX FAURE` | 23 Métallurgie & 194 F. Fa `23\|RUE\|METALLURGIE` | AD9012642 | CABINET PETRUCCI CONVE | 36 | 8 | [0,1,1,4,2] |
| 3 | 168 AVENUE FELIX FAURE `168\|AVENUE\|FELIX FAURE` | SDC LE PRESIDENT `170\|AVENUE\|FELIX FAURE` | AA2730372 | ADMINISTION D'IMMEUBLE | 40 | 8 | [1,5,3,1,1] |
| 4 | 209 AVENUE FELIX FAURE `209\|AVENUE\|FELIX FAURE` | SDC VILLA SYRACUSE `7\|\|PTR ST EUSEBE` | AD3386570 | REGIE FRANCOIS GOFFIN | 34 | 8 | [2,2,2,2,0] |
| 5 | 15 RUE ST EUSEBE `15\|RUE\|ST EUSEBE` | SDC ESPACE EMERAUDE BAT B `12\|RUE\|ST EUSEBE` | AA2028389 | LYMMOBILIER | 33 | 7 | [2,1,2,1,1] |
| 6 | 9 RUE DE MONTBRILLANT `9\|RUE\|MONTBRILLANT` | LE PRIVILEGE MONTBRILLANT  `9B\|RUE\|MONTBRILLANT` | AB6211445 | FONCIA SAINT LOUIS | 59 | 6 | [1,1,1,1,2] |
| 7 | 89 RUE BELLECOMBE `89\|RUE\|BELLECOMBE` | LE BELLECOMBE SAINT ANTOIN `13\|RUE\|ST ANTOINE` | AB2463065 | FONCIA LYON | 72 | 6 | [5,2,1,0,2] |
| 8 | 12 RUE DE VILLON `12\|RUE\|VILLON` | RESIDENCE LE PARC VILLON `10\|RUE\|VILLON` | AA7891641 | REGIE CARRON | 34 | 5 | [1,1,1,2,1] |
| 9 | 2 RUE LOUIS JASSERON `2\|RUE\|LOUIS JASSERON` | LES BALCONS DE LA PART DIE `3\|RUE\|LOUIS JASSERON` | AF5264262 | CONFIANCE IMMOBILIER | 25 | 5 | [2,1,1,2,1] |
| 10 | 93 RUE BELLECOMBE `93\|RUE\|BELLECOMBE` | SDC LE BELLECOMBE `94\|RUE\|BELLECOMBE` | AB5869177 | REGIE GINON | 21 | 5 | [0,2,1,1,1] |
| 11 | 51 RUE ST ANTOINE `51\|RUE\|ST ANTOINE` | LE PATIO SAINT-ANTOINE - M `50\|RUE\|ST ANTOINE` | AD9391244 | LAMY | 25 | 5 | [2,2,1,0,0] |
| 12 | 7 RUE MAURICE FLANDIN `7\|RUE\|MAURICE FLANDIN` | LE PRIVILÈGE LAFAYETTE `6\|RUE\|MAURICE FLANDIN` | AB1493691 | non connu | 18 | 5 | [1,2,2,0,0] |
| 13 | 182 AVENUE FELIX FAURE `182\|AVENUE\|FELIX FAURE` | LE FELIX FAURE `9\|RUE\|METALLURGIE` | AC2489979 | REGIE DE VENDIN | 52 | 4 | [0,1,1,2,0] |
| 14 | 30 RUE ST ANTOINE `30\|RUE\|ST ANTOINE` | LA COUR SAINT ANTOINE `25\|RUE\|ST ANTOINE` | AC3226362 | SOC ADMIN & GESTION IM | 63 | 4 | [1,0,1,1,1] |
| 15 | 131 AVENUE FELIX FAURE `131\|AVENUE\|FELIX FAURE` | PRT DIEU SQUARE CARRE PRT  `139\|AVENUE\|FELIX FAURE` | AA8736043 | IMMO DE FRANCE RHONE A | 83 | 4 | [5,1,1,0,0] |
| 16 | 237 AVENUE FELIX FAURE `237\|AVENUE\|FELIX FAURE` | PAUL BERT - FELIX FAURE `336\|RUE\|PAUL BERT` | AC0225904 | REGIE VINCENT TARGE | 16 | 3 | [1,0,1,1,2] |
| 17 | 3 RUE ST EUSEBE `3\|RUE\|ST EUSEBE` | LE SAINT EUSEBE `2\|RUE\|ST EUSEBE` | AB0287870 | GESTION ET PATRIMOINE  | 14 | 3 | [1,0,0,1,1] |
| 18 | 21 RUE STE ANNE DE BARABAN `21\|RUE\|STE ANNE DE BARABAN` | SDC 21 RUE SAINTE ANNE DE  `21A\|RUE\|STE ANNE DE BARABAN` | AC8951105 | CORNEILLE SAINT MARC | 26 | 3 | [0,2,2,0,0] |
| 19 | 22 RUE ETIENNE RICHERAND `22\|RUE\|ETIENNE RICHERAND` | SDC 21 RUE ETIENNE RICHERA `21\|RUE\|ETIENNE RICHERAND` | AB0141341 | non connu | 14 | 3 | [1,0,2,0,0] |
| 20 | 5 RUE DE MONTBRILLANT `5\|RUE\|MONTBRILLANT` | 5 BIS RUE DE MONTBRILLANT `5B\|RUE\|MONTBRILLANT` | AA9253212 | CITYA VENDOME LUMIERE | 6 | 3 | [0,1,2,0,0] |
| 21 | 64 RUE DU DAUPHINE `64\|RUE\|DAUPHINE` | PARC SISLEY `62\|RUE\|DAUPHINE` | AA8932717 | CITYA VENDOME LUMIERE | 21 | 2 | [0,0,1,1,1] |
| 22 | 32 RUE PROFESSEUR PAUL SISLEY `32\|RUE\|PROFESSEUR PAUL SISLEY` | LES DAHLIAS - MS130778 `31\|RUE\|PROFESSEUR PAUL SISLEY` | AA7236011 | REGIE FRANCOIS GOFFIN | 32 | 2 | [0,0,1,1,0] |
| 23 | 63 RUE DE LA VILLETTE `63\|RUE\|VILLETTE` | LES TERRASSES DE LA GARE `11\|AVENUE\|GEORGES POMPIDOU` | AA0787333 | ESPACE IMMOBILIER LYON | 80 | 2 | [0,1,0,0,1] |
| 24 | 74 RUE ETIENNE RICHERAND `74\|RUE\|ETIENNE RICHERAND` | SDC LE CASTELLANNE `30\|RUE\|ANTOINE CHARIAL` | AF6417042 | ADMINISTRATION D'IMMEU | 55 | 2 | [1,0,0,0,1] |
| 25 | 84 RUE ANTOINE CHARIAL `84\|RUE\|ANTOINE CHARIAL` | LE CLOS DE LA ROSERAIE - M `86\|RUE\|ANTOINE CHARIAL` | AA7209463 | LAMY | 38 | 2 | [2,0,0,1,0] |
| 26 | 41 RUE GUILLOUD `41\|RUE\|GUILLOUD` | LE GUILLOUD `39\|RUE\|GUILLOUD` | AJ0217901 | REGIE DU LYONNAIS | 30 | 2 | [0,2,0,0,0] |
| 27 | 23 RUE STE ANNE DE BARABAN `23\|RUE\|STE ANNE DE BARABAN` | SAINTE ANNE `24\|RUE\|STE ANNE DE BARABAN` | AB8780330 | REGIE VINCENT TARGE | 47 | 1 | [2,3,3,0,3] |
| 28 | 17 RUE ST VICTORIEN `17\|RUE\|ST VICTORIEN` | LE SAINT VICTORIEN `16\|RUE\|ST VICTORIEN` | AA9260977 | MALSH PROPERTY | 69 | 1 | [0,0,0,0,1] |
| 29 | 2 RUE DE LA METALLURGIE `2\|RUE\|METALLURGIE` | 1 RUE DE LA METALLURGIE `1\|RUE\|METALLURGIE` | AB8301665 | non connu | 21 | 1 | [0,0,0,0,1] |
| 30 | 25 RUE ROGER BRECHAN `25\|RUE\|ROGER BRECHAN` | COTE PARC SISLEY-LYN `23\|RUE\|ROGER BRECHAN` | AB4648424 | REGIE DERVAULT BY GERA | 17 | 1 | [0,0,1,1,0] |
| 31 | 40 RUE ST MAXIMIN `40\|RUE\|ST MAXIMIN` | SDC LE CASSIOPEE `39\|RUE\|ST MAXIMIN` | AB5878327 | REGIE GINON | 33 | 1 | [2,1,2,1,0] |
| 32 | 41 COURS ALBERT THOMAS `41\|COURS\|ALBERT THOMAS` | LE SPHINX `41\|COURS\|ALBERT THOMAS 24 RUE DES TUILIERS` | AG6298160 | REGIE POZETTO | 34 | 1 | [1,0,0,1,0] |
| 33 | 5 RUE MEYNIS `5\|RUE\|MEYNIS` | 5 BIS RUE MEYNIS `5B\|RUE\|MEYNIS` | AB8324360 | non connu | 9 | 1 | [0,1,0,0,0] |
| 34 | 5 RUE ROSSAN `5\|RUE\|ROSSAN` | LE N1 RUE GUILLOUD `1\|RUE\|GUILLOUD` | AC1757376 | CONFLUENCE ROLIN BAINS | 70 | 1 | [0,0,0,1,0] |
| 35 | 20 RUE GUILLOUD `20\|RUE\|GUILLOUD` | 20 TER RUE GUILLOUD `20T\|RUE\|GUILLOUD` | AB1910728 | REGIE ROCHON - LESNE | 32 | 1 | [0,1,0,0,0] |
| 36 | 30 RUE PROFESSEUR PAUL SISLEY `30\|RUE\|PROFESSEUR PAUL SISLEY` | SDC SDC LE SISLEY `30\|\|30B R DU PROFESSEUR PAUL SISLEY` | AC7505134 | CENTRALE IMMOBILIERE D | 43 | 1 | [1,0,0,0,0] |
| 37 | 97 RUE BARABAN `97\|RUE\|BARABAN` | SDC 99 RUE BARABAN `99\|RUE\|BARABAN` | AD7354640 | REGIE POZETTO | 7 | 1 | [0,3,0,0,0] |

## REVUE-MANUELLE - classe A non fusionnee proprement (17)

_Copro RNC trouvee mais `cle_adresse` rendue via une auto-fusion (mergedInto jamais consomme -> ventes perdues) ou sur un autre bgid. Exclues de la carte ; rattachement manuel requis._

| Adresse hors-RNC | immat | Copro | ventes_log | Raison |
|---|---|---|--:|---|
| 9 RUE PROFESSEUR PAUL SISLEY `9\|RUE\|PROFESSEUR PAUL SISLEY` | AA0012898 | ATRIUM SISLEY | 16 | src est cible d'auto-fusion (ventes enfants perdues) |
| 53 RUE ETIENNE RICHERAND `53\|RUE\|ETIENNE RICHERAND` | AC3598851 | LE BEAUBOURG | 10 | src est cible d'auto-fusion (ventes enfants perdues) |
| 12 RUE LOUIS JASSERON `12\|RUE\|LOUIS JASSERON` | AA7487564 | L'ENEIDE 1 - MS15805 | 6 | src est cible d'auto-fusion (ventes enfants perdues) |
| 14 RUE ST MAXIMIN `14\|RUE\|ST MAXIMIN` | AB2460335 | TERRASSES ET VILLAS ST M | 6 | src est cible d'auto-fusion (ventes enfants perdues) |
| 38\|RUE\|BARABAN `38\|RUE\|BARABAN` | AC9726381 | L'OLEANDRE | 5 | src est cible d'auto-fusion (ventes enfants perdues) |
| 260\|RUE\|PAUL BERT `260\|RUE\|PAUL BERT` | AE1699040 | LE CLOS ROUGET DE L'ISLE | 5 | src est cible d'auto-fusion (ventes enfants perdues) |
| 6 RUE ST EUSEBE `6\|RUE\|ST EUSEBE` | AG4913810 | LE  SAINT EUSEBE | 5 | cle_adresse copro auto-fusionnee ou autre bgid |
| 12 RUE CARRY `12\|RUE\|CARRY` | AC1825504 | 6/8, rue Carry | 4 | src est cible d'auto-fusion (ventes enfants perdues) |
| 56 AVENUE LACASSAGNE `56\|AVENUE\|LACASSAGNE` | AA4814810 | LES PINS | 4 | src est cible d'auto-fusion (ventes enfants perdues) |
| 48 RUE ST MAXIMIN `48\|RUE\|ST MAXIMIN` | AB2784080 | RESIDENCE MANET | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 18 RUE ETIENNE RICHERAND `18\|RUE\|ETIENNE RICHERAND` | AG2447720 | SDC 19 RUE ETIENNE RICHE | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 316 RUE PAUL BERT `316\|RUE\|PAUL BERT` | AC6168629 | RESIDENCE 318 RUE PAUL B | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 10 RUE DU DAUPHINE `10\|RUE\|DAUPHINE` | AF0858860 | 1 R SAINT MAXIMIN | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 14 RUE ST SIDOINE `14\|RUE\|ST SIDOINE` | AB2206571 | LA VICTORIENNE | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 18 RUE ST ANTOINE `18\|RUE\|ST ANTOINE` | AE9439365 | LE SAINT ANTOINE | 3 | cle_adresse copro auto-fusionnee ou autre bgid |
| 46 RUE ST MAXIMIN `46\|RUE\|ST MAXIMIN` | AB1744747 | LES JARDINS D'HELIOS | 2 | src est cible d'auto-fusion (ventes enfants perdues) |
| 24 AVENUE LACASSAGNE `24\|AVENUE\|LACASSAGNE` | AG1556893 | BRICKS 2 | 1 | src est cible d'auto-fusion (ventes enfants perdues) |

## Notes

- bgid = batiment BDNB ; src != dst ; dst = adresse REELLEMENT rendue (cle_adresse non auto-fusionnee) & meme bgid -> `mergedInto[dst]` garanti consomme (conservation des ventes).
- 0 adresse(s) avec >1 copro candidate propre (choix = immat principal snapshot, sinon + de lots) : aucune.

**Aucune donnee modifiee. Aucune fusion appliquee. Validation requise avant chargement de la carte.**
