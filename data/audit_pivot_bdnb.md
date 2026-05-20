# Audit - pipeline RNC via pivot BDNB multi-adresses

> **Lecture seule.** Aucun fichier de donnees du light modifie. Cache `data/_pivot_bdnb_cache.json` peuple en ecriture (artefact derive, idempotent).

## Concept
Pour chaque adresse **hors-RNC active** (predicat exact renderSecteur : `!fused & cle != cle_adresse copro & !numero_immatriculation & nb_ventes_logement>0`), on interroge l'API BDNB `batiment_groupe_complet?select=l_libelle_adr,l_cle_interop_adr&batiment_groupe_id=in.(...)` sur le `batiment_groupe_id` BDNB. Toutes les adresses BAN attachees au meme bati-groupe deviennent **pivots** : pour chacune, on canonise (regles `_canon_parts` make_light + SUBS GAL/CAPT/AYRES bidirectionnelles) et on cherche un match dans `coproprietes[].cle_adresse` du snapshot secteur. Si match -> candidat rattachement.

## Bilan

| secteur | hr-actives | matches pivot | skip-list | appels BDNB |
|---|--:|--:|--:|--:|
| dauphine_lacassagne | 42 | **0** | 1 | 0 |
| motte_picquet | 24 | **0** | 0 | 0 |
| **total** | **66** | **0** | **1** | 0 |

## Matches par adresse

_Aucun match pivot trouve._


## Cas skippes (skip-list documentee)

Paires (orph, ancre) instruites individuellement et exclues du flux actionnable. Le pivot continue de les detecter (le bgid light n'a pas change) mais ne les remonte plus comme "matches".

| secteur | orph | -> ancre | immat | v_log | instruit le | commit | raison |
|---|---|---|---|--:|---|---|---|
| dauph | `18\|RUE\|ST ANTOINE` | `17\|RUE\|ST ANTOINE` | AE9439365 | 3 | 2026-05-20 | `cd74576` | FAUX POSITIF : bgid light PFFK (assigne par defaut par make_light num_voie BDNB) ne corres... |

## Top 10 par ventes-logement relocalisables

_(aucun)_


## Cas qui auraient ete rates sans pivot BDNB

Pipeline existant `make_light` : (1) jointure RNC->copro `copro_by_cle` exacte / ALIAS_RNC manuel ; (2) BDNB num+voie ; (3) GPS<50m (palier faible). Puis fusion-bgid stricte (parite homogene). **Aucun de ces paliers n'expose les autres adresses BAN du meme batiment** : si la copro RNC est ancree sur une voie/numero qui ne figure pas dans la cle DVF d'origine, le pipeline ne peut pas la trouver (c'est exactement la classe de cas A2/A3 et Acollas documentee dans `fix_mp_cibles_horsrnc.py`, instruite individuellement jusqu'a present).

Le pivot BDNB ouvre un NOUVEAU vecteur systematique : il revele **0 orpheline(s) DVF** rattachable(s) sans intervention manuelle au-dela de l'API. Sans ce pipeline, ces cas seraient laisses en categorie B faute de pouvoir etre detectes par cle/bgid stricte.


## Methodologie + limites
- API BDNB `api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet` (`select=l_libelle_adr,l_cle_interop_adr,libelle_adr_principale_ban,nb_adresse_valid_ban&batiment_groupe_id=in.(...)`), lots de 10, throttling 0.1s.
- Cache `data/_pivot_bdnb_cache.json` (artefact derive, peut etre supprime).
- Matching snapshot uniquement (pas de RNC live ici, rapide). Une 2e passe RNC live (`tabular-api 3ea8e2c3...`) sur les pivots sans match snapshot peut completer (cf. `audit_horsrnc_dvf.py` etape d).
- Limites : (1) la canonisation des pivots reproduit make_light + SUBS minimaliste ; (2) un pivot peut matcher une copro qui n'est PAS sur le meme bgid -> miroir Acollas-type, ventes relocalisees mais BDNB buckets dedupliques (a verifier parc cas par cas, cf. PIPELINE Sec 6, fix_acollas_range / fix_mp_voie_abrev) ; (3) les ancres deja visibles doivent etre instruites RE-POINT (pattern A3 / fix_repoint_p2a) plutot que ALIAS.


---
*`scripts/pipeline_bdnb_pivot.py` - dry-run uniquement. Aucune modification des fichiers du light. Cache + rapport seuls ecrits.*