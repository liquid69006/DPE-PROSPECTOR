# Diagnostic BDNB — adresses hors-RNC (2 secteurs)

**Lecture seule, aucune donnée modifiée.** Objectif : peut-on appliquer
la règle d'affichage logements *Copro RNC → lots RNC · Maison/monopro
résidentielle → `nb_log_bdnb` · Tertiaire/social/inconnu → 0* ?

## Étape 1 — Champs BDNB dans les light JSON

Champs BDNB-dérivés présents sur les adresses (hors-RNC : 698 Dauphiné,
460 Motte) :

| Champ light | Valeurs | Sépare résid./tertiaire ? |
|---|---|---|
| `nb_log_bdnb` | 1–555, `null` (132 D / 76 M) | non (volume seulement) |
| `type_batiment` | appartement / immeuble / maison / `null` | **non** (typologie résidentielle uniquement) |
| `type_chauffage` | gaz / electricite / reseau / fioul / `null` | non |
| `classe_dpe`, `annee_construction`, `batiment_groupe_id`, `_bdnb_match` | — | non |

➡️ **Le light JSON ne contient AUCUN champ `usage_principal`,
`type_proprietaire` ni indicateur de logement social.** `type_batiment`
ne distingue pas le tertiaire/commercial.

### Mais : le snapshot `bdnb_<secteur>.json` contient déjà l'usage

Le fichier `data/bdnb_<secteur>.json` (non propagé au light) porte
**`usage_principal_bdnb_open`**, **couverture 100 %** des bgid hors-RNC
(698/698 D, 460/460 M). Valeurs distinctes (hors-RNC) :

| usage_principal_bdnb_open | Dauphiné | Motte |
|---|--:|--:|
| Résidentiel collectif | 478 | 321 |
| Tertiaire | 159 | 108 |
| Résidentiel individuel | 40 | 15 |
| Secondaire | 14 | 0 |
| Dépendance | 1 | 0 |
| `null` | 6 | 16 |

Le snapshot n'a **pas** de `type_proprietaire` ni de flag social.

## Étape 2 — API BDNB (10 exemples : 5 Dauphiné + 5 Motte)

API ouverte `https://api.bdnb.io/v1/bdnb/donnees` (sans clé).

- **`batiment_groupe_complet`** (134 champs) : `usage_principal_bdnb_open`,
  `usage_niveau_1_txt`, `nb_log`, `nb_log_rnc`, `nb_lot_tertiaire_rnc`,
  `nb_lot_garpark_rnc`, `l_denomination_proprietaire`, `l_siren`,
  `type_batiment_dpe`… **mais AUCUN `type_proprietaire` ni
  `code_proprietaire_type`** (ces champs demandés n'existent pas dans
  l'open data BDNB).
- **`rel_batiment_groupe_proprietaire_siren_open`** (table propriétaires) :
  `siren`, `bat_prop_denomination_proprietaire`, `dans_majic_pm`,
  **`is_bailleur`** (booléen), `nb_locaux_open`.
- `batiment_groupe_ffo_bat` : `usage_niveau_1_txt`, `nb_log` (redondant).
- `batiment_groupe_rnc` : 0 ligne (normal, ce sont des hors-RNC).

Observations sur les 10 exemples :

- `usage_principal_bdnb_open` confirmé fiable et = au snapshot.
- Propriétaires hors-RNC = quasi tous **SCI / personnes privées**,
  `is_bailleur=False` (ex. *69 Baraban*, *4 Dupleix*, *23 Laos*…).
- **1 cas social détecté** : *5 RUE JEAN PIERRE LEVY* → propriétaire
  unique `ALLIADE HABITAT` (siren 960506152, `is_bailleur=True`,
  `nb_locaux=162`) — ESH réelle. Détecté seulement par motif de
  dénomination (« HABITAT »/« ALLIADE »), pas par un champ typé.
- `is_bailleur=True` ≠ « bailleur social » : il signale un bailleur
  *quelconque* (gros loueur privé inclus) → faux positifs probables.

## Étape 3 — Faisabilité de la règle d'affichage

| Cas | Faisable ? | Critère |
|---|:--:|---|
| **Résidentiel privé → `nb_log_bdnb`** | ✅ **OUI** | `usage_principal_bdnb_open` ∈ {`Résidentiel collectif`, `Résidentiel individuel`}. Hors ligne (snapshot, 100 %). Sur les hors-RNC *actifs* : 227/227 D et 108/108 M ont `nb_log_bdnb>0` → affichables. |
| **Tertiaire/commercial → 0** | ✅ **OUI** | `usage_principal_bdnb_open` ∈ {`Tertiaire`, `Secondaire`, `Dépendance`}. Hors ligne. *Limite* : usage = usage **principal** ; un immeuble résidentiel avec commerces en pied = « Résidentiel collectif » (commerces non isolés sans `nb_lot_tertiaire_rnc`, absent hors-RNC). |
| **Logement social → 0** | ⚠️ **NON (pas proprement)** | Aucun champ typé dans BDNB open. Seuls proxys : (a) `is_bailleur` = générique, non social ; (b) motif de dénomination propriétaire vs référentiel bailleurs sociaux. Nécessite l'API + une liste curée + heuristique → faux positifs/négatifs. |
| Inconnu (`usage=null`) → 0 | ✅ trivial | 6 D / 16 M adresses. |

### Recommandations

1. **Réalisable maintenant, sans API** : propager
   `usage_principal_bdnb_open` du snapshot `bdnb_<sec>.json` vers le
   light (jointure par `batiment_groupe_id`, 100 % de couverture).
   Règle : `Résidentiel*` → `nb_log_bdnb` ; `Tertiaire|Secondaire|`
   `Dépendance|null` → 0. Couvre 2 des 3 cas proprement.
2. **Logement social** : non distinguable de façon fiable via BDNB
   open. Options :
   - **a.** Ignorer (volume très faible sur ces secteurs de
     prospection copro ; le seul cas détecté est *Alliade Habitat*) →
     traiter tout résidentiel via `nb_log_bdnb` ; risque = quelques
     bâtiments sociaux comptés comme résidentiel privé.
   - **b.** Heuristique propriétaire (API `rel_..._proprietaire` +
     `is_bailleur=True` + dénomination ∈ référentiel bailleurs sociaux
     SIREN : OPAC/OPH/ESH, Alliade, Grand Lyon Habitat, Paris Habitat,
     RIVP, Elogie, CDC Habitat, 3F, Batigère…). Coût : 1 appel API/bgid
     + liste à maintenir. Précision moyenne.
   - **c.** Robuste : croiser le SIREN propriétaire avec le **RPLS**
     (Répertoire du Parc Locatif Social, data.gouv) ou la liste
     officielle des organismes HLM — référentiel externe, hors BDNB.
3. Bonus monopropriété : `rel_..._proprietaire` à 1 propriétaire
   possédant ~tous les `nb_locaux` + usage résidentiel ⇒ monopropriété ;
   plusieurs propriétaires + résidentiel + hors-RNC ⇒ copro non
   immatriculée. Utile pour qualifier, nécessite l'API.

**Conclusion** : la règle est applicable pour résidentiel↔tertiaire dès
maintenant (champ déjà disponible localement) ; la branche *logement
social → 0* n'a pas de champ BDNB dédié et exige un référentiel externe
(RPLS) ou une heuristique propriétaire acceptée comme approximative.

---
*Diagnostic lecture seule — aucune donnée ni champ modifié.*
