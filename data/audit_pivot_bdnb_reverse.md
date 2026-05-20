# Audit - pipeline pivot BDNB INVERSE

> Lecture seule. Cache `data/_pivot_bdnb_cache.json` partage avec la passe forward (artefact derive).

## Concept
Passe INVERSE du pivot : pour chaque copro RNC visible dans le snapshot (cle_adresse presente dans le light, non fusee, avec immat), on interroge l'API BDNB `batiment_groupe_complet.l_libelle_adr` sur le bgid de son adresse principale. Chaque pivot retourne est compare aux adresses hors-RNC actives (predicat exact renderSecteur). Si match -> orph rattachable a cette copro. Couvre les cas que la passe forward rate (P2c parite mixte, ancres ajoutees post-make_light).

## Bilan

| secteur | hr-actives | copros scannees | matches | skip-list | appels BDNB |
|---|--:|--:|--:|--:|--:|
| dauphine_lacassagne | 45 | 530 | **0** | 0 | 0 |
| motte_picquet | 27 | 798 | **0** | 0 | 0 |
| **total** | 72 | 1328 | **0** | 0 | 0 |

## Matches par adresse

_Aucun nouveau match trouve par la passe inverse._


## Top 10 par ventes-logement relocalisables

_(aucun)_


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