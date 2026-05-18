# Dry-run fusion adresse->copro - Motte-Picquet

**Dry-run, rien d'applique.** Carte `secteurFusions` (forme localStorage `{srcCle: dstCleAdresse}`) pour les adresses hors-RNC actives **FUSION-MEME-BATI** : la copro existe deja au dashboard via une adresse du **meme batiment**, on relocalise les ventes DVF orphelines de l'adresse hors-RNC vers cette copro. Le parc est deja dedup `bg:bgid` (parc RNC pur) -> **aucune inflation**.

- Carte proposee : `data/secteurFusions_dryrun_motte_picquet.json` (26 fusions)
- Application = charger cette carte dans `secteurFusions` (localStorage) **apres validation** ; non fait ici.

## Simulation (vraie `renderSecteur()`, sans -> avec fusions)

| Metrique | Avant | Apres | Delta attendu |
|---|--:|--:|---|
| Adresses affichees | 1134 | 1108 | -26 (sources retirees) |
| Copros RNC affichees | 795 | 795 | inchange (copro deja visible) |
| **Parc logements (secL)** | **25909** | **25909** | **0 (dedup bg:bgid)** |
| Ventes/an (brut) | 756.2 | 756.2 | 0 (relocalisation) |
| Ventes/an (strict) | 568 | 568 | 0 (relocalisation) |
| Taux secteur (brut) | 2.9% | 2.9% | 0 |
| Filtre Hors-RNC actifs | 79 | 53 | -26 |

### Invariants dry-run

- OK - parc secL INCHANGE (brut)
- OK - parc secL INCHANGE (strict)
- OK - ventes/an CONSERVEES (brut, relocalisation pure)
- OK - ventes/an CONSERVEES (strict)
- OK - taux secteur INCHANGE (brut)
- OK - nbShown -= 26 (sources fusionnees retirees)
- OK - hors-RNC actifs -= 26 (79 -> 53)
- OK - RNC affichees +0/=

> 26 fusions ; **99 ventes logement** reattribuees a leur copro (numerateur de rotation deplace vers la bonne copro ; total secteur conserve).

## Detail des fusions proposees

| # | Adresse hors-RNC (src) | -> Copro (dst cle_adresse) | immat | Syndic | lots | ventes_log | ventes_brut/an |
|--:|---|---|---|---|--:|--:|---|
| 1 | 23 RUE DU LAOS `23\|RUE\|LAOS` | SDC DU 21 23 25 RUE DU LAO `21\|RUE\|LAOS` | AA9613753 | GRIFFATON & CO | 112 | 16 | [6,3,4,6,4] |
| 2 | 18 RUE JUGE `18\|RUE\|JUGE` | SDC 19 RUE JUGE `19\|RUE\|JUGE` | AC4170221 | FONCIA PARIS RIVE GAUC | 10 | 7 | [5,15,5,9,12] |
| 3 | 61 AVENUE DE SEGUR `61\|AVENUE\|SEGUR` | SDC du 61/63 Avenue de Ség `63\|AVENUE\|SEGUR` | AC6299499 | ELIMMO GESTION | 56 | 7 | [3,5,5,2,5] |
| 4 | 43 RUE FONDARY `43\|RUE\|FONDARY` | FONDARY 43/45 `45\|RUE\|FONDARY` | AF9892365 | CABINET GELIS | 43 | 7 | [0,1,2,2,2] |
| 5 | 3 AVENUE DE CHAMPAUBERT `3\|AVENUE\|CHAMPAUBERT` | SDC 80 SUFFREN - 2 CHAMPAU `80\|AVENUE\|SUFFREN` | AB6311765 | CABINET MDA IMMO | 29 | 6 | [2,1,0,1,2] |
| 6 | 9 SQUARE DESAIX `9\|SQUARE\|DESAIX` | SDC 10 SQUARE DESAIX `10\|SQUARE\|DESAIX` | AC2394427 | non connu | 14 | 6 | [2,0,2,0,2] |
| 7 | 5 RUE DU GAL LAMBERT `5\|RUE\|GAL LAMBERT` | 5 RUE DU GENERAL LAMBERT `5\|RUE\|GENERAL LAMBERT` | AB7917073 | BR COPROPRIETE | 39 | 5 | [1,1,0,3,0] |
| 8 | 6 RUE CHAMPFLEURY `6\|RUE\|CHAMPFLEURY` | 6 RUE CHAMPFLEURY `45\|AVENUE\|SUFFREN` | AB0758383 | TIFFENCOGE | 29 | 4 | [3,1,2,0,2] |
| 9 | 39 RUE FONDARY `39\|RUE\|FONDARY` | SDC 39-41 RUE FONDARY 7501 `41\|RUE\|FONDARY` | AB4199527 | CABINET CITEAU | 49 | 4 | [2,2,1,0,0] |
| 10 | 47 BOULEVARD GARIBALDI `47\|BOULEVARD\|GARIBALDI` | GARIBALDI - PARIS 15 `49\|BOULEVARD\|GARIBALDI` | AA6084305 | S.T.B. GESTION - IMMO  | 27 | 4 | [1,3,1,0,0] |
| 11 | 7 RUE CARRIER BELLEUSE `7\|RUE\|CARRIER BELLEUSE` | SDC CARRIER BELLEUSE (6 RU `6\|RUE\|CARRIER BELLEUSE` | AC2604221 | FONCIA PARIS RIVE DROI | 14 | 4 | [1,2,0,0,1] |
| 12 | 3 RUE DU GAL DE CASTELNAU `3\|RUE\|GAL DE CASTELNAU` | DU GENERAL DE CASTELNAU 4  `4\|RUE\|GENERAL DE CASTELNAU` | AI7024987 | JEAN CHARPENTIER-SOPAG | 28 | 3 | [0,2,1,1,1] |
| 13 | 9 RUE DU GAL DE LARMINAT `9\|RUE\|GAL DE LARMINAT` | 9 BIS RUE DU GAL DE LARMIN `9B\|RUE\|GENERAL DE LARMINAT` | AC0949958 | non connu | 20 | 3 | [2,0,0,1,0] |
| 14 | 1 RUE JOSE MARIA DE HEREDIA `1\|RUE\|JOSE MARIA DE HEREDIA` | SEGUR AVENUE 67 `67\|AVENUE\|SEGUR` | AH2463305 | ADRIEN SIMONNET SAS | 15 | 3 | [0,1,0,2,1] |
| 15 | 63 RUE DU COMMERCE `63\|RUE\|COMMERCE` | SDC 63/65 RUE DU COMMERCE  `65\|RUE\|COMMERCE` | AA1834670 | CITYA IMMOBILIER TEISS | 33 | 3 | [1,0,0,0,3] |
| 16 | 38 RUE DE LA FEDERATION `38\|RUE\|FEDERATION` | 37/39 FEDERATION - MS40248 `37\|RUE\|FEDERATION` | AD0544940 | UNION COMMERCIALE IMMO | 19 | 3 | [0,0,1,0,2] |
| 17 | 1 RUE DE BUENOS AIRES `1\|RUE\|BUENOS AIRES` | 1 RUE DE BUENOS AYRES `1\|RUE\|BUENOS AYRES` | AD4111738 | CGA | 13 | 2 | [1,1,0,0,0] |
| 18 | 2 RUE DU GAL DE LARMINAT `2\|RUE\|GAL DE LARMINAT` | SDC 2 GENERAL LARMINAT `56\|AVENUE\|MOTTE PICQUET` | AF2293108 | non connu | 20 | 2 | [2,1,1,0,1] |
| 19 | 10\|RUE\|DUPLEIX `10\|RUE\|DUPLEIX` | SDC 9-11 DUPLEIX `11\|RUE\|DUPLEIX` | AA5614235 | CENTENNIAL GESTION | 73 | 2 | [1,0,0,1,0] |
| 20 | 16 RUE FREMICOURT `16\|RUE\|FREMICOURT` | SDC 16 - 18 rue Frémicourt `18\|RUE\|FREMICOURT` | AF2096014 | DM GESTION | 37 | 2 | [0,0,0,1,1] |
| 21 | 135 RUE DU THEATRE `135\|RUE\|THEATRE` | 134 rue du théâtre `134\|RUE\|THEATRE` | AD5373162 | GESTION ET TRANSACTION | 15 | 1 | [0,1,1,0,2] |
| 22 | \|ALLEE\|LEON BOURGEOIS `\|ALLEE\|LEON BOURGEOIS` | 1 RUE DE BUENOS AYRES `1\|RUE\|BUENOS AYRES` | AD4111738 | CGA | 13 | 1 | [0,0,1,0,0] |
| 23 | 1 CITE THURE `1\|\|CITE THURE` | SDC 132 rue du Théâtre et  `132\|RUE\|THEATRE` | AI8720518 | Identité non partagée  | 6 | 1 | [0,0,0,1,0] |
| 24 | 155 AVENUE DE SUFFREN `155\|AVENUE\|SUFFREN` | SDC SUFFREN 155 `12\|RUE\|BELLART` | AI4207031 | JMD CONSEIL | 9 | 1 | [0,0,0,1,0] |
| 25 | 3 RUE DE BUENOS AIRES `3\|RUE\|BUENOS AIRES` | BUENOS AYRES-3 J Y `3\|RUE\|BUENOS AYRES` | AB3659166 | CF GESTION IMMOBILIERE | 30 | 1 | [0,0,0,1,0] |
| 26 | 6 RUE DU GAL DE LARMINAT `6\|RUE\|GAL DE LARMINAT` | DU GENERAL DE LARMINAT 6 R `6\|RUE\|GENERAL DE LARMINAT` | AA7531452 | JEAN CHARPENTIER-SOPAG | 9 | 1 | [0,0,0,0,1] |

## REVUE-MANUELLE - classe A non fusionnee proprement (11)

_Copro RNC trouvee mais `cle_adresse` rendue via une auto-fusion (mergedInto jamais consomme -> ventes perdues) ou sur un autre bgid. Exclues de la carte ; rattachement manuel requis._

| Adresse hors-RNC | immat | Copro | ventes_log | Raison |
|---|---|---|--:|---|
| 9 RUE DU GUESCLIN `9\|RUE\|GUESCLIN` | AB1748391 | Résidence Du Guesclin | 8 | src est cible d'auto-fusion (ventes enfants perdues) |
| 3 RUE DU CAPT SCOTT `3\|RUE\|CAPT SCOTT` | AF6894638 | SDC 1 Capitaine Scott | 8 | src est cible d'auto-fusion (ventes enfants perdues) |
| 11 AVENUE DU MAINE `11\|AVENUE\|MAINE` | AE5269964 | SDC 110 AVENUE DE SUFFRE | 7 | src est cible d'auto-fusion (ventes enfants perdues) |
| 14 AVENUE DU MAINE `14\|AVENUE\|MAINE` | AE5269964 | SDC 110 AVENUE DE SUFFRE | 7 | src est cible d'auto-fusion (ventes enfants perdues) |
| 36 RUE MIOLLIS `36\|RUE\|MIOLLIS` | AD9666140 | 29 CAMBRONNE 75015 | 6 | src est cible d'auto-fusion (ventes enfants perdues) |
| 156 BOULEVARD DE GRENELLE `156\|BOULEVARD\|GRENELLE` | AB1105360 | PARIS MOTTE PICQUET GREN | 6 | src est cible d'auto-fusion (ventes enfants perdues) |
| 4 RUE DU GAL DE CASTELNAU `4\|RUE\|GAL DE CASTELNAU` | AB1024181 | SDC 5 RUE DE LA CAVALERI | 4 | src est cible d'auto-fusion (ventes enfants perdues) |
| 6 AVENUE DU GAL DETRIE `6\|AVENUE\|GAL DETRIE` | AC6620728 | 38 Charles Floquet | 3 | src est cible d'auto-fusion (ventes enfants perdues) |
| 27 RUE FREMICOURT `27\|RUE\|FREMICOURT` | AB3441680 | 28 rue Fremicourt | 2 | src est cible d'auto-fusion (ventes enfants perdues) |
| 3 PLACE CAMBRONNE `3\|PLACE\|CAMBRONNE` | AB5809108 | SDC 6 CAMBRONNE | 2 | src est cible d'auto-fusion (ventes enfants perdues) |
| 7 RUE DU GAL DE CASTELNAU `7\|RUE\|GAL DE CASTELNAU` | AC0121202 | 5 rue du General de Cast | 1 | src est cible d'auto-fusion (ventes enfants perdues) |

## Notes

- bgid = batiment BDNB ; src != dst ; dst = adresse REELLEMENT rendue (cle_adresse non auto-fusionnee) & meme bgid -> `mergedInto[dst]` garanti consomme (conservation des ventes).
- 2 adresse(s) avec >1 copro candidate propre (choix = immat principal snapshot, sinon + de lots) :
  - `9\|RUE\|GAL DE LARMINAT` -> AC0949958 (alt: AA3229176)
  - `2\|RUE\|GAL DE LARMINAT` -> AF2293108 (alt: AD0541896, AG9833203)

**Aucune donnee modifiee. Aucune fusion appliquee. Validation requise avant chargement de la carte.**
