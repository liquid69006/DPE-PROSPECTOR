# Audit - pipeline pivot BDNB INVERSE

> Lecture seule. Cache `data/_pivot_bdnb_cache.json` partage avec la passe forward (artefact derive).

## Concept
Passe INVERSE du pivot : pour chaque copro RNC visible dans le snapshot (cle_adresse presente dans le light, non fusee, avec immat), on interroge l'API BDNB `batiment_groupe_complet.l_libelle_adr` sur le bgid de son adresse principale. Chaque pivot retourne est compare aux adresses hors-RNC actives (predicat exact renderSecteur). Si match -> orph rattachable a cette copro. Couvre les cas que la passe forward rate (P2c parite mixte, ancres ajoutees post-make_light).

## Bilan

| secteur | hr-actives | copros scannees | matches | skip-list | appels BDNB |
|---|--:|--:|--:|--:|--:|
| dauphine_lacassagne | 69 | 530 | **24** | 0 | 52 |
| motte_picquet | 30 | 798 | **2** | 0 | 79 |
| **total** | 99 | 1328 | **26** | 0 | 131 |

**Classification** : miroir (Acollas-type)=25, parc-neutre (meme bgid)=1.

**Apport** : 0 match(es) via SUBS ; 0 cas avec collision (autre copro sur meme bgid -> ambiguite a verifier).

## Matches par adresse

| secteur | orph hors-RNC | v_log | bg orph | <- copro ancre (visible) | immat | lots | syndic | type | autres copros bgid |
|---|---|--:|---|---|---|--:|---|---|--:|
| dauph | `30\|RUE\|ETIENNE RICHERAND` | 12 | `...Z8-N3AL-EF91` | `28\|RUE\|ETIENNE RICHERAND` | AA0358655 | 211 | GRANDLYON HABITAT  | miroir (Acollas-type) | 0 |
| dauph | `8\|RUE\|CLAUDIUS PIONCHON` | 9 | `...XN-JTJZ-HPB4` | `12\|RUE\|ST SIDOINE` | AB2206571 | 165 | FONCIA LYON | miroir (Acollas-type) | 0 |
| dauph | `29\|RUE\|STE ANNE DE BARABAN` | 6 | `...EL-Q4MX-AZC3` | `27\|RUE\|STE ANNE DE BARABAN` | AA1700848 | 99 | REGIE DERVAULT BY  | miroir (Acollas-type) | 0 |
| dauph | `11\|RUE\|RIBOUD` | 5 | `...47-TD9J-M4FB` | `11\|RUE\|MAURICE FLANDIN` | AA1456987 | 70 | ESPACE IMMOBILIER  | miroir (Acollas-type) | 0 |
| dauph | `16\|RUE\|ETIENNE RICHERAND` | 4 | `...5W-CLD7-6WBT` | `22\|RUE\|ST ANTOINE` | AA1601434 | 115 | GRANDLYON HABITAT  | miroir (Acollas-type) | 0 |
| dauph | `31\|RUE\|STE ANNE DE BARABAN` | 4 | `...7S-ZSUP-29YF` | `27\|RUE\|STE ANNE DE BARABAN` | AA1700848 | 99 | REGIE DERVAULT BY  | miroir (Acollas-type) | 0 |
| dauph | `47\|RUE\|PROFESSEUR PAUL SISLEY` | 4 | `...19-EARQ-9D7B` | `16\|RUE\|GUILLOUD` | AA7407463 | 50 | REGIE GINDRE | miroir (Acollas-type) | 0 |
| dauph | `22\|RUE\|LOUIS JASSERON` | 4 | `...LJ-N3JJ-SW4G` | `18\|RUE\|LOUIS JASSERON` | AB1570571 | 110 | LAMY | miroir (Acollas-type) | 0 |
| dauph | `4\|RUE\|JEAN RENOIR` | 4 | `...3M-F4BX-8Z7T` | `38\|RUE\|JEANNE HACHETTE` | AB6374961 | 72 | LYMMOBILIER | miroir (Acollas-type) | 0 |
| dauph | `4\|RUE\|MARCEL PEHU` | 4 | `...WN-9ZYS-LQGQ` | `28\|RUE\|ST PHILIPPE` | AC2574101 | 34 | REGIE FRANCOIS GOF | miroir (Acollas-type) | 0 |
| dauph | `51\|AVENUE\|GEORGES POMPIDOU` | 3 | `...B2-4HSV-Y9VP` | `18\|RUE\|LOUIS JASSERON` | AB1570571 | 110 | LAMY | miroir (Acollas-type) | 0 |
| dauph | `5\|RUE\|JEAN PIERRE LEVY` | 3 | `...UB-Z7P7-2XQ1` | `1\|RUE\|JEAN PIERRE LEVY` | AB3947009 | 89 | VSA IMMOBILIER | miroir (Acollas-type) | 0 |
| dauph | `6\|RUE\|METALLURGIE` | 3 | `...TK-SKSS-P2M2` | `9\|RUE\|DAVID` | AB3954260 | 84 | REGIE MOLIERE | miroir (Acollas-type) | 0 |
| dauph | `10\|RUE\|TERNOIS` | 2 | `...MC-KXL7-E97N` | `23\|RUE\|RIBOUD` | AA1991660 | 37 | REGIE FRANCOIS GOF | miroir (Acollas-type) | 0 |
| dauph | `325\|RUE\|PAUL BERT` | 2 | `...GZ-FUN1-1XWM` | `2\|RUE\|ST EUSEBE` | AB0287870 | 14 | GESTION ET PATRIMO | miroir (Acollas-type) | 0 |
| dauph | `124\|RUE\|ANTOINE CHARIAL` | 2 | `...8P-5ZM6-3A3B` | `11\|RUE\|ST EUSEBE` | AB1809680 | 42 | REGIE DES GONES | miroir (Acollas-type) | 0 |
| dauph | `11\|RUE\|DAVID` | 2 | `...PW-6YPJ-XASZ` | `9\|RUE\|DAVID` | AB3954260 | 84 | REGIE MOLIERE | miroir (Acollas-type) | 0 |
| dauph | `10\|RUE\|METALLURGIE` | 2 | `...4Y-G9R6-B2ZS` | `9\|RUE\|DAVID` | AB3954260 | 84 | REGIE MOLIERE | miroir (Acollas-type) | 0 |
| dauph | `10\|RUE\|TEINTURIERS` | 2 | `...ZA-TNRT-44JS` | `104\|RUE\|BARABAN` | AC1218890 | 53 | GERIMMO | miroir (Acollas-type) | 0 |
| dauph | `4\|RUE\|MAURICE FLANDIN` | 2 | `...RS-K6JM-Z1H3` | `234\|COURS\|LAFAYETTE` | AC8608747 | 30 | FONCIA LYON | miroir (Acollas-type) | 0 |
| dauph | `277\|RUE\|PAUL BERT` | 1 | `...NH-CNYH-DY2X` | `76\|RUE\|ANTOINE CHARIAL` | AA1694256 | 111 | REGIE CENTRALE IMM | miroir (Acollas-type) | 0 |
| dauph | `279\|RUE\|PAUL BERT` | 1 | `...Q7-1AD8-Z67B` | `76\|RUE\|ANTOINE CHARIAL` | AA1694256 | 111 | REGIE CENTRALE IMM | miroir (Acollas-type) | 0 |
| dauph | `69\|RUE\|BARABAN` | 1 | `...9P-RL7A-RWW7` | `61\|RUE\|BARABAN` | AB2515468 | 149 | non connu | miroir (Acollas-type) | 0 |
| dauph | `24\|AVENUE\|LACASSAGNE` | 1 | `...XU-6YKR-D8DU` | `24\|\|ET 24 BIS AVENUE LACASSAGNE` | AG1556893 | 64 | FONCIA LYON | parc-neutre | 0 |
| motte | `22\|RUE\|FEDERATION` | 4 | `...CU-YC17-6HN1` | `20\|RUE\|FEDERATION` | AA0398420 | 500 | CABINET SAINT LAMB | miroir (Acollas-type) | 0 |
| motte | `11\|\|CITE THURE` | 3 | `...SV-XK55-A3WG` | `15\|RUE\|GRAMME` | AJ1220698 | 24 | R. J. TRODE ET COM | miroir (Acollas-type) | 0 |

## Top 10 par ventes-logement relocalisables

| secteur | orph hors-RNC | v_log | v_tot | <- copro candidate | immat | lots | nom copro |
|---|---|--:|--:|---|---|--:|---|
| dauph | `30\|RUE\|ETIENNE RICHERAND` | 12 | 12 | `28\|RUE\|ETIENNE RICHERAND` | AA0358655 | 211 | Antoine Charial |
| dauph | `8\|RUE\|CLAUDIUS PIONCHON` | 9 | 9 | `12\|RUE\|ST SIDOINE` | AB2206571 | 165 | LA VICTORIENNE |
| dauph | `29\|RUE\|STE ANNE DE BARABAN` | 6 | 7 | `27\|RUE\|STE ANNE DE BARABAN` | AA1700848 | 99 | LES JARDINS DE BABYLONE |
| dauph | `11\|RUE\|RIBOUD` | 5 | 5 | `11\|RUE\|MAURICE FLANDIN` | AA1456987 | 70 | LE FLANDIN SAINT ANTOINE |
| dauph | `16\|RUE\|ETIENNE RICHERAND` | 4 | 4 | `22\|RUE\|ST ANTOINE` | AA1601434 | 115 | LES JARDINS DE CHARIAL |
| dauph | `31\|RUE\|STE ANNE DE BARABAN` | 4 | 9 | `27\|RUE\|STE ANNE DE BARABAN` | AA1700848 | 99 | LES JARDINS DE BABYLONE |
| dauph | `47\|RUE\|PROFESSEUR PAUL SISLEY` | 4 | 4 | `16\|RUE\|GUILLOUD` | AA7407463 | 50 | LE SISLEY - MS32872 |
| dauph | `22\|RUE\|LOUIS JASSERON` | 4 | 4 | `18\|RUE\|LOUIS JASSERON` | AB1570571 | 110 | BARABAN 2 - MS133639 |
| dauph | `4\|RUE\|JEAN RENOIR` | 4 | 16 | `38\|RUE\|JEANNE HACHETTE` | AB6374961 | 72 | CENTRAL PARC |
| dauph | `4\|RUE\|MARCEL PEHU` | 4 | 4 | `28\|RUE\|ST PHILIPPE` | AC2574101 | 34 | LES DOMES SAINT PHILIPPE I |

## Comparaison forward vs reverse
- **Forward** (pipeline_bdnb_pivot.py) : direction orph -> bgid orph -> BDNB pivots -> copros. Rate les cas ou le bgid de l'orph est different de celui de la copro (corner parite-mixte, ordering passes).
- **Reverse** (ce pipeline) : direction copro RNC -> bgid copro -> BDNB pivots -> hr-actives. Couvre exactement le complementaire : trouve les orphelines que la copro 'reclamait' via BDNB mais que make_light n'a pas regroupees.
- **Union ideale** = forward U reverse. La paire (orph, anchor) peut apparaitre dans les 2 (meme cas) ou un seul (asymetrie). Pour appliquer en lot, traiter l'union dedupliquee.


## Methodologie + limites
- Cache BDNB partage entre forward et reverse (idempotent, 1 appel par bgid maxi sur les 2 passes).
- SUBS bidirectionnels herites (GAL/CAPT/AYRES).
- Skip-list partagee (SKIP_PAIRS de pipeline_bdnb_pivot).
- Filtre collision : flag `autres copros bgid` > 0 signale qu'un AUTRE syndicat existe sur le meme bgid (rare ; ARMONIAL I + sous-syndicats par exemple) -> verifier avant rattachement.
- Limites : les bgids avec une seule adresse-pivot ne produiront aucun match (rien a remonter). Les cas a vraie ambiguite (orph pourrait appartenir a 2 copros voisines avec bgid different mais meme adresse BAN) produisent collision flag.


---
*`scripts/pipeline_bdnb_pivot_reverse.py` - dry-run uniquement. Aucune modification du light. Cache + rapport seuls ecrits.*