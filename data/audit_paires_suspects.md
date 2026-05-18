# Audit paires suspectes — pattern « 10 RUE / 10 PASSAGE MEYNIS »

**Lecture seule.** Pattern : 2 adresses *même numéro + même nom de voie*, **type de voie différent**, où l'une porte des logements (copro RNC ou `nb_log_bdnb`) sans aucune vente DVF, et l'autre des ventes DVF (`nb_ventes_logement>0`) sans logement. Aucune donnée modifiée.


## Dauphine-Lacassagne

Groupes (num+nom) multi-types analysés : **3** · clones STRICTS : **0** · cas RELAXÉS à examiner : **0**


### Dauphine-Lacassagne — clones STRICTS (= bug Meynis) : 0

_Aucune paire stricte (A: logements>0 & 0 vente / B: ventes>0 & 0 logement). Le seul clone exact (10 RUE/PASSAGE MEYNIS) est déjà corrigé._


### Dauphine-Lacassagne — cas RELAXÉS à examiner manuellement : 0

_B = ventes strictes mais ~aucun logement propre (pas de copro, `nb_log_bdnb`≤1 ou usage non résidentiel, non fusionné) ; A = copro RNC réelle même num+nom, autre type. Phantom DVF probable mais A porte aussi ses propres ventes → rattachement non automatique, revue requise._

_Aucun._


## Motte-Picquet

Groupes (num+nom) multi-types analysés : **10** · clones STRICTS : **0** · cas RELAXÉS à examiner : **1**


### Motte-Picquet — clones STRICTS (= bug Meynis) : 0

_Aucune paire stricte (A: logements>0 & 0 vente / B: ventes>0 & 0 logement). Le seul clone exact (10 RUE/PASSAGE MEYNIS) est déjà corrigé._


### Motte-Picquet — cas RELAXÉS à examiner manuellement : 1

_B = ventes strictes mais ~aucun logement propre (pas de copro, `nb_log_bdnb`≤1 ou usage non résidentiel, non fusionné) ; A = copro RNC réelle même num+nom, autre type. Phantom DVF probable mais A porte aussi ses propres ventes → rattachement non automatique, revue requise._

| # | A copro (cle) | A: lots / syndic / copro | B ventes (cle) | B: vl / vt / usage / log_bdnb | dist | même bgid |
|--:|---|---|---|---|--:|:--:|
| 1 | `28|PLACE|DUPLEIX` | 36 / non connu / 28 PLACE ET RUE DUPLEIX (AA9462284) | `28|RUE|DUPLEIX` | 4 / 4 / Tertiaire / 1 | 8 m | non |

## Méthode

- Clé de groupe = (numéro, nom de voie normalisé sans accents) extraits de `cle` (`num|type|nom`), **type ignoré**.
- Groupe retenu si ≥2 adresses ET ≥2 types de voie distincts.
- **A** = logements>0 (`nb_lots_habitation` copro/adresse ou `nb_log_bdnb`) ET `nb_ventes_total==0`.
- **B** = `nb_ventes_logement>0` ET aucun logement.
- Paire = un A et un B du même groupe, **types différents**.
- `statut` : *déjà fusionné* (`_fusion_auto`), *même bgid* (fusion auto possible), sinon *À CORRIGER* (ALIAS_RNC / COPRO_FORCE dans make_light.py, cf. fix Meynis).

---
*Lecture seule — aucune donnée modifiée.*