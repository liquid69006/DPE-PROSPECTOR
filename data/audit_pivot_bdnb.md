# Audit - pipeline RNC via pivot BDNB multi-adresses

> **Lecture seule.** Aucun fichier de donnees du light modifie. Cache `data/_pivot_bdnb_cache.json` peuple en ecriture (artefact derive, idempotent).

## Concept
Pour chaque adresse **hors-RNC active** (predicat exact renderSecteur : `!fused & cle != cle_adresse copro & !numero_immatriculation & nb_ventes_logement>0`), on interroge l'API BDNB `batiment_groupe_complet?select=l_libelle_adr,l_cle_interop_adr&batiment_groupe_id=in.(...)` sur le `batiment_groupe_id` BDNB. Toutes les adresses BAN attachees au meme bati-groupe deviennent **pivots** : pour chacune, on canonise (regles `_canon_parts` make_light + SUBS GAL/CAPT/AYRES bidirectionnelles) et on cherche un match dans `coproprietes[].cle_adresse` du snapshot secteur. Si match -> candidat rattachement.

## Bilan

| secteur | hr-actives | matches pivot | appels BDNB |
|---|--:|--:|--:|
| dauphine_lacassagne | 80 | **12** | 8 |
| motte_picquet | 33 | **2** | 4 |
| **total** | **113** | **14** | 12 |

**Classification** : parc-neutre (meme bgid)=14.

**Apport** : 0 match(es) trouve(s) GRACE A SUBS (auraient ete rates sans). 12 ancre(s) deja visible(s) en pipe (collision potentielle a verifier).

## Matches par adresse

| secteur | cle hors-RNC | v_log | bgid | adresse pivot BDNB | -> copro ancre | immat | lots | syndic | type | collision |
|---|---|--:|---|---|---|---|--:|---|---|---|
| dauph | `9\|RUE\|PROFESSEUR PAUL SISLEY` | 16 | `...CY-P7TQ-TZ2P` | 7 B Rue Professeur Paul Sisley, 69003, Lyon 3e | `7B\|RUE\|PROFESSEUR PAUL SISLEY` | AA0012898 | 225 | GAGNEUX SERVICES I | parc-neutre | DEJA VISIBLE |
| dauph | `12\|RUE\|LOUIS JASSERON` | 6 | `...UC-A62Z-LN35` | 13 Rue Louis Jasseron, 69003, Lyon 3e Arrondis | `13\|RUE\|LOUIS JASSERON` | AC6278774 | 17 | LAMY | parc-neutre | DEJA VISIBLE |
| dauph | `12\|RUE\|LOUIS JASSERON` | 6 | `...UC-A62Z-LN35` | 17 Rue Louis Jasseron, 69003, Lyon 3e Arrondis | `17\|RUE\|LOUIS JASSERON` | AA7487564 | 29 | LAMY | parc-neutre | - |
| dauph | `14\|RUE\|ST MAXIMIN` | 6 | `...3V-PN4E-7QWG` | 1 Rue Rossan, 69003, Lyon 3e Arrondissement | `1\|RUE\|ROSSAN` | AB2460335 | 53 | REGIE PEDRINI | parc-neutre | DEJA VISIBLE |
| dauph | `38\|RUE\|BARABAN` | 5 | `...CU-S4U4-AGR1` | 37 Rue Baraban, 69003, Lyon 3e Arrondissement | `37\|RUE\|BARABAN` | AC9726381 | 29 | non connu | parc-neutre | DEJA VISIBLE |
| dauph | `260\|RUE\|PAUL BERT` | 5 | `...LP-CBCP-F74E` | 264 B Rue Paul Bert, 69003, Lyon 3e Arrondisse | `264B\|RUE\|PAUL BERT` | AE1699040 | 8 | REGIE DU LYONNAIS | parc-neutre | DEJA VISIBLE |
| dauph | `12\|RUE\|CARRY` | 4 | `...4B-YECQ-FPCT` | 6 Rue Carry, 69003, Lyon 3e Arrondissement | `6\|RUE\|CARRY` | AC1825504 | 12 | C2L | parc-neutre | DEJA VISIBLE |
| dauph | `48\|RUE\|ST MAXIMIN` | 3 | `...6G-4P2Q-RRZK` | 51 Rue Saint Maximin, 69003, Lyon 3e Arrondiss | `51\|RUE\|ST MAXIMIN` | AB2784080 | 50 | REGIE PEDRINI | parc-neutre | DEJA VISIBLE |
| dauph | `18\|RUE\|ETIENNE RICHERAND` | 3 | `...NV-GU7Z-XPMJ` | 19 Rue Etienne Richerand, 69003, Lyon 3e Arron | `19\|RUE\|ETIENNE RICHERAND` | AG2447720 | 8 | non connu | parc-neutre | DEJA VISIBLE |
| dauph | `10\|RUE\|DAUPHINE` | 3 | `...NL-L1N7-K12Y` | 1 Rue Saint Maximin, 69003, Lyon 3e Arrondisse | `1\|RUE\|ST MAXIMIN` | AF0858860 | 14 | GESTION ET PATRIMO | parc-neutre | DEJA VISIBLE |
| dauph | `14\|RUE\|ST SIDOINE` | 3 | `...CZ-EFDZ-724F` | 12 Rue Saint-Sidoine, 69003, Lyon 3e Arrondiss | `12\|RUE\|ST SIDOINE` | AB2206571 | 165 | FONCIA LYON | parc-neutre | DEJA VISIBLE |
| dauph | `18\|RUE\|ST ANTOINE` | 3 | `...FK-6Z9V-TUP1` | 17 Rue Saint-Antoine, 69003, Lyon 3e Arrondiss | `17\|RUE\|ST ANTOINE` | AE9439365 | 45 | CONFLUENCE ROLIN B | parc-neutre | - |
| dauph | `46\|RUE\|ST MAXIMIN` | 2 | `...DK-M71Z-3JJQ` | 43 Rue Saint-Maximin, 69003, Lyon 3e Arrondiss | `43\|RUE\|ST MAXIMIN` | AB1744747 | 22 | non connu | parc-neutre | DEJA VISIBLE |
| motte | `156\|BOULEVARD\|GRENELLE` | 6 | `...HZ-H1TK-FPME` | 154 Boulevard De Grenelle, 75015, Paris 15e Ar | `154\|BOULEVARD\|GRENELLE` | AB1105360 | 35 | non connu | parc-neutre | - |
| motte | `3\|PLACE\|CAMBRONNE` | 2 | `...JY-P43A-W2JX` | 6 Place Cambronne, 75015, Paris 15e Arrondisse | `6\|PLACE\|CAMBRONNE` | AB5809108 | 19 | DAUCHEZ PROPERTY M | parc-neutre | DEJA VISIBLE |

## Top 10 par ventes-logement relocalisables

| secteur | cle hors-RNC | v_log | v_tot | -> copro candidate | immat | lots |
|---|---|--:|--:|---|---|--:|
| dauph | `9\|RUE\|PROFESSEUR PAUL SISLEY` | 16 | 16 | 7 B Rue Professeur Paul Sisley -> `7B\|RUE\|PROFESSEUR PAUL SISLEY` | AA0012898 | 225 |
| dauph | `12\|RUE\|LOUIS JASSERON` | 6 | 6 | 13 Rue Louis Jasseron, 69003,  -> `13\|RUE\|LOUIS JASSERON` | AC6278774 | 17 |
| dauph | `14\|RUE\|ST MAXIMIN` | 6 | 6 | 1 Rue Rossan, 69003, Lyon 3e A -> `1\|RUE\|ROSSAN` | AB2460335 | 53 |
| motte | `156\|BOULEVARD\|GRENELLE` | 6 | 6 | 154 Boulevard De Grenelle, 750 -> `154\|BOULEVARD\|GRENELLE` | AB1105360 | 35 |
| dauph | `38\|RUE\|BARABAN` | 5 | 5 | 37 Rue Baraban, 69003, Lyon 3e -> `37\|RUE\|BARABAN` | AC9726381 | 29 |
| dauph | `260\|RUE\|PAUL BERT` | 5 | 5 | 264 B Rue Paul Bert, 69003, Ly -> `264B\|RUE\|PAUL BERT` | AE1699040 | 8 |
| dauph | `12\|RUE\|CARRY` | 4 | 4 | 6 Rue Carry, 69003, Lyon 3e Ar -> `6\|RUE\|CARRY` | AC1825504 | 12 |
| dauph | `48\|RUE\|ST MAXIMIN` | 3 | 7 | 51 Rue Saint Maximin, 69003, L -> `51\|RUE\|ST MAXIMIN` | AB2784080 | 50 |
| dauph | `18\|RUE\|ETIENNE RICHERAND` | 3 | 5 | 19 Rue Etienne Richerand, 6900 -> `19\|RUE\|ETIENNE RICHERAND` | AG2447720 | 8 |
| dauph | `10\|RUE\|DAUPHINE` | 3 | 4 | 1 Rue Saint Maximin, 69003, Ly -> `1\|RUE\|ST MAXIMIN` | AF0858860 | 14 |

## Cas qui auraient ete rates sans pivot BDNB

Pipeline existant `make_light` : (1) jointure RNC->copro `copro_by_cle` exacte / ALIAS_RNC manuel ; (2) BDNB num+voie ; (3) GPS<50m (palier faible). Puis fusion-bgid stricte (parite homogene). **Aucun de ces paliers n'expose les autres adresses BAN du meme batiment** : si la copro RNC est ancree sur une voie/numero qui ne figure pas dans la cle DVF d'origine, le pipeline ne peut pas la trouver (c'est exactement la classe de cas A2/A3 et Acollas documentee dans `fix_mp_cibles_horsrnc.py`, instruite individuellement jusqu'a present).

Le pivot BDNB ouvre un NOUVEAU vecteur systematique : il revele **14 orpheline(s) DVF** rattachable(s) sans intervention manuelle au-dela de l'API. Sans ce pipeline, ces cas seraient laisses en categorie B faute de pouvoir etre detectes par cle/bgid stricte.


**Attention** : 12 ancre(s) sont **deja visibles** dans le rendu actuel (ont une cle_adresse non fusee). Verifier avant tout fix : une fusion supplementaire pourrait creer un double-rendu ou un changement de principal indesirable (cf. PIPELINE Sec 6).


## Methodologie + limites
- API BDNB `api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet` (`select=l_libelle_adr,l_cle_interop_adr,libelle_adr_principale_ban,nb_adresse_valid_ban&batiment_groupe_id=in.(...)`), lots de 10, throttling 0.1s.
- Cache `data/_pivot_bdnb_cache.json` (artefact derive, peut etre supprime).
- Matching snapshot uniquement (pas de RNC live ici, rapide). Une 2e passe RNC live (`tabular-api 3ea8e2c3...`) sur les pivots sans match snapshot peut completer (cf. `audit_horsrnc_dvf.py` etape d).
- Limites : (1) la canonisation des pivots reproduit make_light + SUBS minimaliste ; (2) un pivot peut matcher une copro qui n'est PAS sur le meme bgid -> miroir Acollas-type, ventes relocalisees mais BDNB buckets dedupliques (a verifier parc cas par cas, cf. PIPELINE Sec 6, fix_acollas_range / fix_mp_voie_abrev) ; (3) les ancres deja visibles doivent etre instruites RE-POINT (pattern A3 / fix_repoint_p2a) plutot que ALIAS.


---
*`scripts/pipeline_bdnb_pivot.py` - dry-run uniquement. Aucune modification des fichiers du light. Cache + rapport seuls ecrits.*