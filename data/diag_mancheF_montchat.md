# Diag MANCHE F Montchat (Phase 5, classif social/mixte des 132 bailleurs)
> DRY-RUN READ-ONLY. PYTHONUTF8=1, ASCII-safe. **AUCUNE ecriture KV, AUCUN POST, AUCUN commit / git add.** Date : 2026-06-03.
> Namespace KV : `secteur_assignments:dauphine-lacassagne-montchat`. Light, DL/MP, index.html NON touches.

---

## VOLET 1 - Convention F de DL (citee verbatim)

### Formule `social_pct` (source : `scripts/_diag_social_combined_dvf_majic_dl.py` l.135-146)

```python
if rnc_habit > 0 and rnc_total > 0:
    prop_habit = rnc_habit / rnc_total
    hlm_habit_estim = round(hlm_pm * prop_habit, 1)
    social_pct_corrige = round(hlm_habit_estim * 100 / rnc_habit, 1)
elif rnc_habit > 0:
    social_pct_corrige = round(hlm_pm * 100 / rnc_habit, 1)
else:
    social_pct_corrige = None
```

- **Numerateur** = `hlm_habit_estim` = lots PM detenus par un proprietaire **bailleur** (denomination matchant un needle `metier.hlm_needles` + `metier.public_non_hlm`, MAJUSCULE, substring), ramenes en habitation via `prop_habit`. La detection bailleur (`is_hlm_denom`) couvre les memes needles que le filtre manche D.
- **Denominateur** = `rnc_habit` = `copropriete.nb_lots_habitation` (RNC). **PAS** `nb_log_bdnb**, PAS le total MAJIC.
- **Source des comptes PM** : `_enrich_majic_*_full.json` (`sirens[].lots`), soit le parquet `majic_locaux2_2025.parquet` joint **par parcelle BDNB** (LOCAUX2 PM-only). Le filtre syndic/gerant/usufruit/nu-proprietaire est applique au recompte (regex `SYNDIC|GERANT|MANDATAIRE|GESTIONNAIRE|USUFRUIT|NU.?PROPRI`).

### Seuils (source : `data/secteurs.json` -> `montchat.metier.seuils`, identiques a DL)

- `social_pct_min` = **60** ; `mut_apt_per_year_min` = **2**.
- **Verdict** (`_diag_social_combined_dvf_majic_dl.py` l.159-164) :
  - `FAUX_POSITIF` : `social_pct < 60` **OU** `mut/an >= 2`
  - `SOCIAL`       : `social_pct >= 60` **ET** `mut/an < 1`
  - `INCERTAIN`    : sinon
- **Reclassement** (l.166-177) : `FAUX_POSITIF` + immat RNC -> `mixte` ; `FAUX_POSITIF` sans immat -> `copro_non_immat` ; `SOCIAL` -> garder social.

> **Le seuil 20-60 -> mixte du brief n'apparait PAS tel quel dans le code DL.** Le code DL ne connait que `>=60 social` / `<60 faux-positif`. La bascule `mixte` n'y est PAS pilotee par une tranche `20-60` de social_pct, mais par la **presence d'un immat RNC** sur un faux-positif. **La tranche `20-60 -> mixte` et le cas `<20` du brief ne sont donc PAS une convention DL ecrite** (deduction du brief, non preuve code).

### Piege social `mut_apt_per_year_min` (source : `PIPELINE.md` root S6 Piege 1, l.153-168)

> *"`social_pct` est surevalue : MAJIC LOCAUX 2 n'expose pas les proprietaires personnes physiques (RGPD) [...]. Antidote : croiser avec DVF. Si `mut/an >= 2` sur l'adresse exacte -> ne pas tagger social, meme si `social_pct >= 60 %`."* Cas de reference : 28 ETIENNE RICHERAND (98,4 % social MAJIC mais 6,2 mut/an -> copro privee).
- **OUI, le garde mut est applique** ci-dessous : tout batiment a `mut/an >= 2` est SORTI du tag social (range en LOW/arbitrage), conformement a DL.

### >>> COUVERTURE : le cas hors-RNC N'EST PAS couvert par la convention DL

Les 132 batiments F sont **hors-RNC** (`in_copro=False`, `has_immat=False`) : par construction ils n'ont **aucune entree copro RNC**, donc `nb_lots_habitation = 0` -> la formule DL `social_pct_corrige` renvoie **None (N/A) pour LES 132** (`social_pct_dl=N/A : 132/132`). **La convention DL ne definit aucun denominateur de remplacement pour les hors-RNC.** Le pipeline social DL (`_diag_social_*_dl.py`) ne s'applique qu'aux cles DEJA taggees social qui SONT des copros RNC (avec `nb_lots_habitation`).

**Consequence (conforme a la consigne du brief : ne pas taguer a l'aveugle si la convention ne couvre pas)** : ce diag NE PEUT PAS calculer le `social_pct` DL canon sur ces 132. Il produit a la place deux proxys **transparents et non-canoniques**, et applique une regle de rabattement conservatrice (VOLET 2) qu'il faut **valider par Yann** :

- `px_majic` = `hlm_pm * 100 / majic_lots` (= `social_pct AVANT` non corrige, `_diag_social_pct_corrige_dl.py` l.116 ; biaise a la HAUSSE car LOCAUX2 = PM-only).
- `px_bdnb`  = `hlm_pm * 100 / nb_log_bdnb` (proxy parc ; biaise si parcelle multi-batis).
- `owner_share` = `n_owners_bailleurs * 100 / n_owners_PM` (signal le moins biaise).

## VOLET 2 - Regle de rabattement appliquee (CHOICE, a valider)

Faute de `social_pct` DL canon, le tag repose sur **`owner_share`** (part d'OWNERS PM bailleurs) + garde mut DVF :

| Condition | Tag |
|---|---|
| `owner_share == 100` ET `mut/an < 2` | **social** |
| `0 < owner_share < 100` ET `mut/an < 2` | **mixte** |
| `owner_share < 20` **OU** `mut/an >= 2` **OU** 0 PM | **NON tagge** (arbitrage) |

> Regle CONSERVATRICE : un seul coproprietaire prive sur la parcelle -> `mixte`, pas social. Le seuil `social_pct_min=60` est cite mais inapplicable (pas de denom RNC). **A valider** : si Yann prefere un seuil sur `px_bdnb` ou `px_majic`, la distribution changera.

## VOLET 3 - Distribution

| Classe | n |
|---|--:|
| social (owner_share=100, mut<2) | 105 |
| mixte (0<owner_share<100, mut<2) | 19 |
| NON tagge (LOW : <20 / mut>=2 / 0PM) | 8 |
| **TOTAL** | **132** |

Decomposition LOW : `owner_share<20` = **5** ; `mut/an>=2` (garde rotation) = **3** ; `0 PM` (parcelle sans lot PM apres filtre syndic) = **0**.

### Liste des <20%% / NON tagges (cas sensible : pousses en F mais surtout prives)

| cle | owner_share | px_majic | px_bdnb | nb_log | vlog | mut/an | raison | top bailleur |
|---|--:|--:|--:|--:|--:|--:|---|---|
| 101|AVENUE|LACASSAGNE | 7.7 | 2.6 | 1.7 | 58 | 5 | 3.6 | mut>=2 | COMMUNE DE LYON |
| 103|AVENUE|LACASSAGNE | 7.7 | 2.6 | 1.8 | 55 | 3 | 3.6 | mut>=2 | COMMUNE DE LYON |
| 29B|RUE|VIALA | 16.7 | 16.7 | 5.6 | 36 | 1 | 0.2 | owner_share<20 | FONCIERE D'HABITAT ET HUMANISME |
| 11|RUE|TRARIEUX | 9.1 | 16.2 | 33.3 | 18 | 3 | 0.8 | owner_share<20 | METROPOLE DE LYON |
| 17|RUE|TRARIEUX | 9.1 | 16.2 | 40.0 | 15 | 0 | 0.8 | owner_share<20 | METROPOLE DE LYON |
| 48|ROUTE|GENAS | 50.0 | 98.6 | 1007.1 | 14 | 3 | 2.0 | mut>=2 | ERILIA |
| 5|COURS|DOCTEUR LONG | 12.5 | 22.2 | 33.3 | 12 | 1 | 0.2 | owner_share<20 | FONDATION DU PRADO |
| 83|AVENUE|LACASSAGNE | 16.7 | 52.1 | None | None | 0 | 0.6 | owner_share<20 | ALLIADE HABITAT |

### Liste mixte (19)

| cle | owner_share | n_owners | hlm_pm | nb_log | vlog | mut/an | top bailleur |
|---|--:|--:|--:|--:|--:|--:|---|
| 35|RUE|COIGNET | 50.0 | 2 | 330 | 108 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 4|RUE|MONTAIGNE | 50.0 | 2 | 162 | 82 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 10|RUE|HARMONIE | 50.0 | 2 | 158 | 72 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 115|COURS|ALBERT THOMAS | 25.0 | 4 | 2 | 35 | 0 | 0.2 | IN'LI AURA |
| 6|IMPASSE|MOREL | 33.3 | 3 | 14 | 24 | 0 | 0.0 | IMMOBILIERE RHONE ALPES SA D'HLM |
| 7|PASSAGE|FEUILLAT | 50.0 | 2 | 154 | 17 | 0 | 0.0 | IN'LI AURA |
| 11|RUE|DOC PAUL DIDAY | 50.0 | 2 | 154 | 15 | 0 | 0.0 | IN'LI AURA |
| 17|RUE|DOC PAUL DIDAY | 50.0 | 2 | 154 | 14 | 0 | 0.0 | IN'LI AURA |
| 42|COURS|RICHARD VITTON | 50.0 | 2 | 46 | 14 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 44T|RUE|ST ISIDORE | 25.0 | 4 | 12 | 13 | 1 | 0.2 | OPH DE LA METROPOLE DE LYON |
| 44T|RUE|PROFESSEUR FLORENCE | 25.0 | 4 | 4 | 9 | 2 | 0.6 | HOSPICES CIVILS DE LYON |
| 15|RUE|DOC PAUL DIDAY | 50.0 | 2 | 154 | 8 | 0 | 0.0 | IN'LI AURA |
| 11B|RUE|CHARLES RICHARD | 50.0 | 2 | 2 | 1 | 0 | 0.0 | 3F RESIDENCES |
| 20|AVENUE|ESQUIROL | 50.0 | 2 | 1 | 1 | 0 | 0.0 | ETAT PAR DIRECTION DE L IMMOBILIER |
| 50|AVENUE|ESQUIROL | 50.0 | 2 | 1 | 1 | 0 | 0.0 | ETAT PAR DIRECTION DE L IMMOBILIER |
| 60|AVENUE|ROCKEFELLER | 50.0 | 2 | 8 | None | 0 | 0.0 | SEM PATRIMONIALE DU GRAND LYON |
| 80|COURS|EUGENIE | 50.0 | 2 | 2 | None | 0 | 0.4 | CONSULTING CHTITI HABITAT |
| 49|RUE|FEUILLAT | 50.0 | 2 | 2 | None | 0 | 0.0 | COMMUNAUTE URBAINE DE LYON |
| 5|PASSAGE|FEUILLAT | 50.0 | 2 | 154 | None | 0 | 0.0 | IN'LI AURA |

### Liste social (top 30 par nb_log)

| cle | n_owners | majic_lots | nb_log | vlog | mut/an | top bailleur |
|---|--:|--:|--:|--:|--:|---|
| 92|RUE|FERDINAND BUISSON | 1 | 491 | 246 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 10|RUE|FELIX ROLLET | 1 | 150 | 150 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 33|RUE|FEUILLAT | 1 | 278 | 134 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 52|BOULEVARD|PINEL | 1 | 89 | 87 | 0 | 0.0 | HOSPICES CIVILS DE LYON |
| 18|RUE|FIOL | 1 | 146 | 73 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 17B|RUE|CHARLES RICHARD | 1 | 145 | 71 | 0 | 0.0 | BATIGERE RHONE ALPES  SOCIETE ANON |
| 46|RUE|ST ISIDORE | 1 | 85 | 56 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 1B|RUE|DOCTEUR BONHOMME | 1 | 143 | 48 | 0 | 0.0 | BATIGERE RHONE ALPES  SOCIETE ANON |
| 2|RUE|DOCTEUR BONHOMME | 1 | 143 | 48 | 0 | 0.0 | BATIGERE RHONE ALPES  SOCIETE ANON |
| 126|COURS|ALBERT THOMAS | 1 | 142 | 37 | 0 | 0.0 | IN'LI AURA |
| 12|RUE|CARRY | 1 | 70 | 34 | 1 | 0.2 | IN'LI AURA |
| 5|RUE|CARRY | 1 | 70 | 34 | 0 | 0.2 | IN'LI AURA |
| 86|ROUTE|GENAS | 1 | 62 | 31 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 1|PASSAGE|FEUILLAT | 1 | 62 | 30 | 0 | 0.0 | ALLIADE HABITAT |
| 68|AVENUE|LACASSAGNE | 1 | 59 | 30 | 0 | 0.0 | BATIGERE RHONE ALPES  SOCIETE ANON |
| 42T|RUE|FEUILLAT | 1 | 60 | 29 | 0 | 0.0 | ALLIADE HABITAT |
| 200|ROUTE|GENAS | 1 | 63 | 26 | 0 | 0.0 | SA HLM LOGEMENT ALPES RHONE |
| 2B|RUE|VILLEBOIS MAREUIL | 1 | 26 | 25 | 0 | 0.0 | ADOMA |
| 33|RUE|JEAN MARC BERNARD | 1 | 50 | 24 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 70|ROUTE|GENAS | 1 | 75 | 24 | 0 | 0.0 | IN'LI AURA |
| 20|RUE|BARA | 2 | 94 | 22 | 0 | 0.0 | BATIGERE RHONE ALPES  SOCIETE ANON |
| 100|COURS|DOCTEUR LONG | 1 | 61 | 21 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 37|RUE|JULIEN | 1 | 40 | 20 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 17|RUE|FEUILLAT | 1 | 57 | 19 | 0 | 0.0 | SEM DE CONSTRUCTION DU DPT DE L AI |
| 42|RUE|FEUILLAT | 1 | 105 | 18 | 0 | 0.0 | ALLIADE HABITAT |
| 106|COURS|DOCTEUR LONG | 2 | 58 | 16 | 0 | 0.0 | GRANDLYON HABITAT - OFFICE PUBLIC  |
| 170|ROUTE|GENAS | 1 | 33 | 16 | 0 | 0.0 | OPH DE LA METROPOLE DE LYON |
| 1B|RUE|OMER LOUIS | 1 | 31 | 16 | 0 | 0.0 | ALLIADE HABITAT |
| 7|IMPASSE|VICTOR HUGO | 1 | 69 | 16 | 0 | 0.0 | CDC HABITAT SOCIAL SOCIETE ANONYME |
| 24|RUE|FERDINAND BUISSON | 1 | 19 | 15 | 0 | 0.0 | ALLIADE HABITAT |

... +75 autres social.

## Candidat KV + diff

- Base = `_kv_assign_montchat.D.candidate.json` (**381** = 103 B2a + 278 D), PRESERVEE a l'identique.
- Candidat F = `data/_kv_assign_montchat.F.candidate.json` (**505** entrees).

| | assignments |
|---|--:|
| base D (381) | 381 |
| candidat F (POST complet) | 505 |

**Diff = +124 ajouts (105 social + 19 mixte), 0 modif, 0 retrait.** KV 381 -> 505.

**Intersection des cles F (taggees) avec les tags D (mono/copro) = 0** VIDE OK (les 132 F etaient EXCLUS de D par la garde social-precedence ; les tags F n'ecrasent donc aucun mono/copro D). B2a 103 + D 278 preserves a l'identique.

## Neutralite parc LIGHT

Les tags `as.type` sont **KV-only** : le light n'est PAS touche. Le parc `secL` calcule par `renderSecteur` sur le light brut reste **15 848** (tags hors light) ; Sigma ventes **932**. test_render exit 0 (DL + montchat + MP) - voir section run.

## Effet LIVE attendu (a documenter, NON applique)

Un tag **social** -> `getEffectiveLog = 0` cote index.html (LIVE) -> le parc LIVE **et** le marche-libre LIVE baissent (ventes des social exclues du marche-libre).

| Effet LIVE | logements retires | ventes retirees |
|---|--:|--:|
| social (105) | **1833** | **5** |
| mixte (19) - pour info | 414 | 3 |

> Le parc LIVE diminue de **1833 logements** (Sigma nb_log_bdnb des social) et le marche-libre LIVE de **5 ventes** (Sigma nb_ventes_logement des social). L'effet mixte depend de la regle UI mixte (a verifier index.html, hors-scope ici).

## Scripts anti-drift + commande POST (NE PAS POSTER)

- `scripts/_F_backup_diff_montchat.py` (calque `_D_backup_diff`, ALLOWED_NEW_TYPES = {social, mixte}).
- `scripts/_F_post_montchat.py` (calque `_D_post`, GET==backup -> POST -> re-GET verify -> miroir).

```powershell
. scripts\load_jwt.ps1
python scripts\_F_backup_diff_montchat.py
python scripts\_F_post_montchat.py
```

*Aucun POST, aucun commit dans cette manche (DRY-RUN).*
