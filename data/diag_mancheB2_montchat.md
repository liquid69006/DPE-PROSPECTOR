# Diag Manche B2 — Classification de la pile orange hors-RNC MONTCHAT (DRY-RUN)

> **Phase 5, Manche B2.** Tache **READ-ONLY / DRY-RUN.** Aucune ecriture sauf ce
> rapport. **AUCUN commit / git add.** PYTHONUTF8=1, prints ASCII-safe.
> Date : 2026-06-03. Source : `data/secteur_montchat_light.json` (etat POST-B1 :
> 1430 adr, 633 copros, parc 15848, Sigma ventes_logement 932). MAJIC :
> `C:\Users\Station 5\majic_locaux2_2025.parquet` (22,5 M lignes). INSEE 69383+69388.
>
> **Objet** : proposer (sans appliquer) le **type** de chacun des **530 hors-RNC
> actifs** (pile orange). Le critere discriminant = **PROPRIETE** (1 proprietaire
> -> MONO ; plusieurs -> COPRO_NON_IMMAT), **PAS** le nombre de logements (regle
> Yann). Il n'existe PAS de type "maison".
>
> **Convention** : **[PREUVE]** = code / donnee lus ; **[DEDUCTION]** = inference.

---

## ETAPE 1 — Playbook DL de classification (lecture du code)

### Scripts lus

| Script | Role |
|---|---|
| `scripts/enrich_majic.py` | Phase 1 : sweep serial hr-actifs, 1 query MAJIC par parcelle |
| `scripts/enrich_majic_full.py` | Phase 2 : sweep BULK (1 read MAJIC filtre dep+commune, groupby parcelle), produit `_enrich_majic_<sct>_full.json` |
| `scripts/_scan_sansventes_majic_dl.py` | classifieur final (MONO_*/TERTIAIRE/FRAGMENTEE/PP_PURE) sur la sortie enrich |
| `scripts/_diag_social_combined_dvf_majic_dl.py` | regle social_pct + faux-positifs social via MAJIC x DVF |
| `scripts/secteur_config.py` | source unique de verite (`secteurs.json` : INSEE, needles, seuils) |

### Cle de jointure light x MAJIC = la **PARCELLE BDNB** (pas l'adresse, pas le numero_majic) [PREUVE]

Le pipeline DL ne joint **pas** par adresse normalisee. Il joint par **code
parcelle** :

1. Chaque adresse light porte `batiment_groupe_id` (bgid). [PREUVE light]
2. `enrich_majic_full.py` construit/complete un cache `bgid -> [parcelle_id]`
   (`data/_bgid_parcelle_<sct>.json`) via l'API BDNB live
   `rel_batiment_groupe_parcelle?batiment_groupe_id=eq.<bgid>` [PREUVE l.54-74].
3. La parcelle BDNB (ex `69383000EI0113`) est decoupee en `(section, numero_parcelle)`
   par `parc_to_majic()` [PREUVE l.46-51 : `sec=p[8:10]`, `plan=int(p[10:].lstrip('0'))`].
4. MAJIC est lu en BULK filtre `departement` + `code_commune` **en liste** (multi-commune
   gere : MP=115+107) [PREUVE l.139-142], puis `groupby(code_commune, section, numero_parcelle)`,
   et la cle BDNB est reconstruite via `pref_by_commune()` (`{'383':'69383000'}`) [PREUVE l.150-156].

> **Consequence Montchat** : la jointure canonique DL exige
> **`data/_bgid_parcelle_montchat.json`** qui **N'EXISTE PAS ENCORE** (seuls
> `_bgid_parcelle_dl.json` 901 et `_bgid_parcelle_mp.json` 1000 existent) [PREUVE].
> Le light Montchat ne porte **aucun champ parcelle** [PREUVE : 0 cle `parc*` dans
> les adresses]. Pour reproduire la jointure DL exacte il faut **construire ce
> cache via BDNB-live** (~672 bgids hors-RNC, l'API ouverte `api.bdnb.io` deja
> utilisee en B1). **Voir ETAPE 2 pour la methode de substitution utilisee dans ce
> dry-run** (jointure par adresse, plus faible) et son taux de couverture.

### Comptage des PROPRIETAIRES (le discriminant) [PREUVE]

Une fois les lots MAJIC d'une parcelle reunis :
- **Le proprietaire = `numero_siren`** (groupby SIREN). `enrich_majic_full` calcule
  pour chaque SIREN : `lots` (= nb de lignes LOCAUX2), `pct_lots`, `denomination`
  [PREUVE l.204-213].
- **MONO** (Phase 2 raffinee) = `1 seul SIREN` **ET** `pct_lots>=100` **ET**
  `ratio_pm_bdnb = lots_total/nb_log_bdnb >= 0.9` [PREUVE l.218-221]. Le ratio
  garde contre les faux mono (parcelle sous-couverte).
- `_scan_sansventes_majic_dl` ajoute la nuance : `top_pct>=80` -> MONO_*
  (sous-type par denomination) ; `>=5 SIREN & top<50%` -> FRAGMENTEE (= vraie
  copro non-immat de PM) ; `ratio<0.15` -> PP_PURE [PREUVE l.137-149].

### L'angle-mort PP (RGPD) — comment DL le gere [PREUVE + verifie sur le parquet]

- **MAJIC LOCAUX2 fourni ici est PM-only** : sur 116 871 lignes Lyon 3e+8e,
  **116 869 ont un `numero_siren`**, 2 seulement null [PREUVE]. Les **personnes
  physiques (PP) sont quasi-absentes** de la table -> **0 SIREN trouve != 0
  proprietaire** (ce sont des PP non listees, RGPD).
- DL en tient compte explicitement : `ratio_pm_bdnb < 0.15` -> **PP_PURE** =
  "vraie copro PP majoritaire, laisser tel quel, cible prospection"
  [PREUVE `_scan_sansventes` l.138-139, RECOS l.161]. Donc **0 PM ne bascule
  JAMAIS automatiquement en MONO** ; cote DL c'est traite comme copro de PP
  (cible). Dans CE dry-run B2 (cf. arbre Yann fourni) le **0 PM = AMBIGU a
  flaguer** pour arbitrage Yann (mono vs copro_non_immat), conforme a la spec.

### social_pct — sur quel champ [PREUVE]

- Il n'y a **pas** de champ `nb_lots_sociaux` dans la donnee. DL **estime** le %
  social a partir de MAJIC : `_diag_social_combined_dvf_majic_dl.py` somme les
  **lots PM detenus par des bailleurs HLM** (`is_hlm_denom` via needles) ramenes
  a la part habitation RNC : `social_pct_corrige = HLM_habit_estim *100 / RNC_habit`
  [PREUVE l.136-143].
- Le signal HLM est double : **denomination** (needles `HABITAT, HLM, SACVL, OPAC,
  ALLIADE, GRANDLYON, 3F, ICF, ADOMA, ERILIA, DYNACITE, METROPOLE HABITAT...`
  [PREUVE l.39-46]) **ET** `groupe_personne_libelle` (= `office HLM` /
  `economie mixte` cote parquet — 52 386 lignes "office HLM" sur la zone Lyon
  [PREUVE]).
- Seuils (`secteurs.json[dauphine-lacassagne].metier.seuils`) : `social_pct_min=60`
  (>=60 -> social), `mut_apt_per_year_min=2` (faux-positif social si rotation DVF
  forte) [PREUVE secteur_config]. **20-60 -> mixte** (regle reprise de l'arbre B2).

### Faux-positifs syndics / gestionnaires [PREUVE + champ confirme]

- Le parquet a la colonne **`code_droit_libelle`** [PREUVE]. Valeurs sur la zone :
  `Proprietaire` (95 608), `Gerant, mandataire, gestionnaire` (11 891),
  `Emphyteote` (2 640), `Usufruitier` (1 771), **`Syndic de copropriete`** (1 763),
  `Nu-proprietaire` (1 402), etc. [PREUVE].
- FONCIA, REGIE LESTRA, SAGNIMORTE, LYMMOBILIER, PIRON GESTION... apparaissent dans
  LOCAUX2 **comme `Syndic de copropriete` ou `Gerant/mandataire/gestionnaire`** :
  ce sont des GESTIONNAIRES, **PAS des proprietaires**. Les compter ferait
  conclure MONO a tort. -> **Filtre** : exclure du comptage de proprietaires toute
  ligne dont `code_droit_libelle` contient `SYNDIC | GERANT | MANDATAIRE |
  GESTIONNAIRE` (ce dry-run exclut en plus `USUFRUITIER | NU-PROPRIETAIRE`, qui ne
  sont pas la pleine propriete).

### Logique DL — tableau de synthese

| Etape | Critere | Champ(s) | Verdict |
|---|---|---|---|
| 0 | jointure | bgid -> parcelle BDNB -> MAJIC (section,plan) | reunit les lots |
| 1 | exclure non-proprietaires | `code_droit_libelle` ~ syndic/gerant/usufruit | hors comptage |
| 2 | usage non-resid | `usage_principal_bdnb` (light) | BUREAUX |
| 3 | social | HLM lots / total (needles + `office HLM`) `>=60` | SOCIAL ; 20-60 MIXTE |
| 4 | mono | 1 SIREN proprio (>=80-100%) + ratio>=0.9 | MONO |
| 4 | copro PM | >=2 SIREN proprio | COPRO_NON_IMMAT |
| 4 | 0 SIREN | angle-mort PP | DL=PP_PURE(cible) ; **B2=AMBIGU** |

### SECTEUR-parametrable pour Montchat (INSEE 69383+69388)

- **INSEE** : `code_commune in ['383','388']` (le polygone Montchat deborde sur le
  8e ; le parquet a bien 61 243 lignes 383 + 55 628 lignes 388) [PREUVE].
- **Needles HLM** : reutilisables telles quelles (memes bailleurs Grand Lyon /
  SACVL / Alliade que DL — avantage Lyon vs MP) [DEDUCTION conforme manche0].
- **Seuils** : `social_pct_min=60`, `mut_apt_per_year_min=2` (identiques DL).
- **Manquant** : `secteurs.json` n'a PAS encore d'entree `montchat` (DL porte les 2
  zones dans `geo.zones`) -> `enrich_majic_full.py --secteur montchat` ne tourne
  pas tel quel ; **il faut ajouter le slug `montchat`** (paths + geo + metier) OU
  lancer un script standalone. Et **construire `_bgid_parcelle_montchat.json`**.

---

## ETAPE 2 — DRY-RUN : classification des 530 hors-RNC actifs

### Methode employee dans ce dry-run (et son ecart au playbook DL)

La jointure DL canonique (parcelle) **n'est pas executable** ici sans BDNB-live
(cache parcelle Montchat absent). Pour livrer un dry-run **sans ecriture reseau ni
fichier**, ce rapport joint le light x MAJIC **par adresse normalisee**
`(numero_sans_suffixe_B/T, nom_voie_normalise)` sur les 2 communes (PM-only,
exclusion syndics/gerants/usufruit). C'est une **substitution plus faible** que la
parcelle :

- **Couverture obtenue : 239 / 530 oranges** ont >=1 ligne MAJIC PM jointe.
- Les **291 sans aucune ligne MAJIC** se repartissent en (a) **voies absentes du
  parquet PM** (ex `RUE HARMONIE`, `ROUTE GENAS` -> 0 ligne : PP-only ou bord de
  commune), (b) suffixes/normalisations residuels. **C'est l'angle-mort PP/jointure**,
  PAS une preuve de 0-proprietaire reel.

> **[DEDUCTION] La parcelle BDNB recupererait une partie de ces 291** (un meme bgid
> peut grouper plusieurs adresses postales dont une seule porte les lots MAJIC).
> **Recommandation** : avant l'application reelle, lancer `enrich_majic_full` en
> mode Montchat (apres ajout du slug + build cache parcelle) pour **resserrer la
> distribution** — les comptes ci-dessous sont une **borne de travail**, fiable
> sur les 239 joints, indicative sur le reste.

### Arbre de decision applique (ordre strict, conforme spec)

1. **bgid == bgid d'une copro RNC visible** (immat sur l'adresse OU `cle in
   coproprietes`, inclut les 29 injects B1) -> **A_FUSER**.
2. **usage non-residentiel** (`usage_principal_bdnb` != Residentiel*, != Dependance,
   != Secondaire) -> **BUREAUX**.
3. **social_pct >= 60 -> SOCIAL** ; **20-60 -> MIXTE** (HLM lots PM / total lots PM,
   needles + `office HLM`).
4. residentiel prive : **`nb_log_bdnb==1` -> MONO** (regle Yann, sans condition) ;
   **>1 log** -> **1 PM proprio -> MONO** ; **>=2 PM -> COPRO_NON_IMMAT** ;
   **0 PM -> AMBIGU** (angle-mort PP, a arbitrer).

---

## ETAPE 3 — RESULTATS

### DISTRIBUTION proposee (530 oranges)

| Type | n | Methode / compte |
|---|--:|---|
| **A_FUSER** | **133** | meme bgid qu'une copro RNC visible (107 bgids distincts) -> deviennent RNC immatriculees, sortent de l'orange |
| **MONO** | **154** | 69 via `nb_log_bdnb==1` (regle Yann) + 85 via 1 seul PM proprio MAJIC |
| **SOCIAL** | **91** | HLM lots PM / total >= 60% (bailleurs Grand Lyon / SACVL / office HLM) |
| **BUREAUX** | **34** | `usage_principal_bdnb == Tertiaire` (100%) |
| **COPRO_NON_IMMAT** | **23** | >=2 PM proprios distincts (12 a 2 PM, 11 a 3-7 PM) |
| **MIXTE** | **19** | social_pct 20-60% |
| **AMBIGU** | **76** | >1 log + 0 PM MAJIC (68 sans aucune ligne MAJIC + 8 avec lignes toutes syndic/exclues) |
| **TOTAL** | **530** | |

> **Fiabilite** : A_FUSER (preuve directe bgid), BUREAUX (preuve usage light) et
> MONO-via-nlog1 (regle Yann) sont **robustes**. MONO-via-1PM, SOCIAL, MIXTE,
> COPRO_NON_IMMAT dependent de la jointure adresse (borne sur les 239 joints).
> AMBIGU = a arbitrer + a re-tester en jointure parcelle.

### LISTE des 76 AMBIGUS (>1 log, 0 PM MAJIC) — pour arbitrage Yann

Indices : `nlog` = nb_log_bdnb ; `vlog` = nb_ventes_logement ; `niv` = nb_niveau
BDNB ; `surf` = surface_emprise_sol (m2) ; `sci` = `sci_nom` du light (signal
mono fort si present). `nb_log_rnc` BDNB = None pour TOUS (pas d'immat) -> non
listee. Tri par nlog desc.

| cle | nlog | vlog | niv | surf | sci_nom |
|---|--:|--:|--:|--:|---|
| 10\|RUE\|HARMONIE | 72 | 0 | 6 | 1069 | - |
| 12\|RUE\|HARMONIE | 72 | 0 | 6 | 1069 | - |
| 134\|ROUTE\|GENAS | 67 | 0 | 7 | 678 | SCI BLEU VERT |
| 138\|ROUTE\|GENAS | 67 | 0 | 7 | 678 | SCI PUCCINI |
| 101\|AVENUE\|LACASSAGNE | 58 | 5 | 9 | 473 | - |
| 40\|ROUTE\|GENAS | 40 | 0 | 7 | 564 | - |
| 177\|COURS\|DOCTEUR LONG | 38 | 0 | 6 | 655 | - |
| 179\|COURS\|DOCTEUR LONG | 38 | 0 | 6 | 655 | - |
| 86\|ROUTE\|GENAS | 31 | 0 | 7 | 428 | - |
| 88\|ROUTE\|GENAS | 31 | 0 | 7 | 428 | - |
| 150\|ROUTE\|GENAS | 29 | 0 | 7 | 691 | - |
| 2\|BOULEVARD\|PINEL | 28 | 0 | 7 | 476 | - |
| 200\|ROUTE\|GENAS | 26 | 0 | 7 | 338 | - |
| 25B\|COURS\|DOCTEUR LONG | 26 | 0 | 8 | 238 | SCI LA CANOPEE |
| 8\|RUE\|DOCTEUR REBATEL | 25 | 3 | 6 | 334 | MAXIMILIEN 55 |
| 70\|ROUTE\|GENAS | 24 | 0 | 7 | 139 | - |
| 162\|ROUTE\|GENAS | 23 | 1 | 6 | 266 | SCI IMMOVAPI |
| 8\|IMPASSE\|LINDBERG | 23 | 2 | 3 | 822 | - |
| 125\|RUE\|DAUPHINE | 22 | 3 | 6 | 412 | LES ROCHERS |
| 123\|RUE\|DAUPHINE | 22 | 1 | 6 | 412 | - |
| 100\|COURS\|DOCTEUR LONG | 21 | 0 | 5 | 510 | - |
| 160\|ROUTE\|GENAS | 20 | 1 | 6 | 229 | SCI 3D |
| 27\|RUE\|BALME | 18 | 2 | 5 | 426 | - |
| 124\|RUE\|DAUPHINE | 18 | 0 | 5 | 276 | SCI 124 RUE DU DAUPHINE |
| 2\|RUE\|RUCHE | 18 | 0 | 4 | 197 | - |
| 22\|RUE\|BALME | 18 | 0 | 5 | 426 | SCI BALME |
| 67\|AVENUE\|LACASSAGNE | 17 | 1 | 5 | 807 | - |
| 28\|RUE\|ROUX SOIGNAT | 17 | 0 | 6 | 184 | - |
| 106\|COURS\|DOCTEUR LONG | 16 | 0 | 6 | 298 | - |
| 110\|COURS\|DOCTEUR LONG | 16 | 0 | 5 | 287 | G ET PH RESIDENCE MONTCHAT |
| 170\|ROUTE\|GENAS | 16 | 0 | 6 | 241 | - |
| 26\|RUE\|HARMONIE | 15 | 0 | 3 | 641 | - |
| 48\|ROUTE\|GENAS | 14 | 3 | 8 | 119 | - |
| 132\|RUE\|DAUPHINE | 14 | 0 | 6 | 362 | - |
| 84\|ROUTE\|GENAS | 13 | 2 | 4 | 331 | - |
| 14\|RUE\|CHARLES RICHARD | 13 | 0 | 4 | 310 | - |
| 82\|COURS\|DOCTEUR LONG | 13 | 0 | 5 | 281 | - |
| 5\|COURS\|DOCTEUR LONG | 12 | 1 | 7 | 169 | NADELI |
| 110\|RUE\|DAUPHINE | 12 | 0 | 6 | 153 | - |
| 16\|RUE\|RUCHE | 12 | 0 | 4 | 286 | - |
| 20\|ROUTE\|GENAS | 12 | 0 | 5 | 191 | - |
| 14\|COURS\|DOCTEUR LONG | 11 | 2 | 7 | 358 | MONTCHATPSY |
| 10\|RUE\|ST ISIDORE | 11 | 0 | 2 | 639 | SCI DURGA |
| 10B\|RUE\|ST ISIDORE | 11 | 0 | 2 | 639 | SCI DURGA |
| 11\|RUE\|PROFESSEUR FLORENCE | 11 | 0 | 5 | 362 | - |
| 20B\|COURS\|RICHARD VITTON | 11 | 0 | 4 | 263 | - |
| 43\|COURS\|DOCTEUR LONG | 9 | 0 | 5 | 149 | - |
| 37\|AVENUE\|ACACIAS | 8 | 0 | 3 | 151 | - |
| 7\|RUE\|LOUIS | 7 | 2 | 3 | 216 | - |
| 16\|IMPASSE\|SABLON | 7 | 1 | 3 | 305 | - |
| 6\|IMPASSE\|LINDBERG | 7 | 1 | 3 | 176 | - |
| 2\|ROUTE\|GENAS | 7 | 0 | 4 | 227 | - |
| 55\|COURS\|DOCTEUR LONG | 5 | 0 | 3 | 128 | SCI DES 4A |
| 25\|RUE\|DOCTEUR BONHOMME | 4 | 2 | 3 | 330 | - |
| 37\|AVENUE\|CHATEAU | 4 | 0 | 2 | 129 | - |
| 12\|RUE\|EGLISE | 3 | 1 | 2 | 229 | - |
| 4\|RUE\|SPORTS | 3 | 0 | 1 | 80 | - |
| 6\|RUE\|PALAIS D ETE | 3 | 0 | 2 | 202 | SCI 6 RUE DU PALAIS D'ETE |
| 5\|RUE\|JULIEN | 2 | 2 | 2 | 133 | - |
| 13\|RUE\|CAPITAINE | 2 | 0 | 2 | 80 | - |
| 12\|RUE\|JULES MASSENET | 2 | 1 | 3 | 155 | - |
| 14\|RUE\|ALFRED DE MUSSET | 2 | 1 | 2 | 108 | - |
| 27\|RUE\|BONNAND | 2 | 1 | 2 | 194 | - |
| 2\|IMPASSE\|LUTIN | 2 | 1 | 2 | 101 | - |
| 1\|AVENUE\|CHATEAU | 2 | 0 | 1 | 190 | IJK AVENIR |
| 17\|RUE\|CAPITAINE | 2 | 0 | 2 | 266 | SCI DU CAPITAINE |
| 3\|RUE\|EGLISE | 2 | 0 | 3 | 87 | SCI JULIMIKE |
| 32\|RUE\|JULES MASSENET | 2 | 0 | 2 | 120 | - |
| 91B\|RUE\|BALME | 2 | 0 | 2 | 70 | SCI AVAKIAN |
| 38\|AVENUE\|ACACIAS | 0 | 2 | - | 107 | - |
| 67B\|AVENUE\|LACASSAGNE | 0 | 1 | 5 | 807 | - |
| 45B\|RUE\|JEANNE D ARC | 0 | 1 | 2 | 91 | - |
| 66B\|COURS\|RICHARD VITTON | 0 | 1 | 2 | 147 | - |
| 23B\|RUE\|FEUILLAT | 0 | 1 | 2 | 85 | - |
| 9B\|RUE\|VILLEBOIS MAREUIL | 0 | 1 | 2 | 101 | - |
| 13B\|RUE\|CAPITAINE | 0 | 1 | 2 | 80 | - |

**Observations d'arbitrage** :
- **Cluster ROUTE GENAS (15 AMBIGUS)** : voie **totalement absente du parquet PM
  383+388** -> soit PP pures, soit bord de polygone / commune voisine (Villeurbanne
  69266 ?). Plusieurs portent une SCI (`SCI BLEU VERT`, `SCI PUCCINI`, `SCI 3D`,
  `SCI IMMOVAPI`) = **signal mono fort**. **A verifier hors-bande** (commune INSEE
  reelle de ROUTE GENAS).
- **RUE HARMONIE (3)** : aussi absente du parquet PM. Gros batis (72 log, 1069 m2)
  -> probables copros PP (copro_non_immat) ou bailleur non capte.
- **20 AMBIGUS portent un `sci_nom`** non vide -> penchent **mono** (1 SCI
  proprietaire), mais `sci_nom` du light est indicatif, pas la preuve de propriete
  exclusive. A confirmer en jointure parcelle.

### HEURISTIQUE proposee (chiffree, NON appliquee)

Sur les 76 AMBIGUS, regle de pre-tri suggere a Yann :
- **`nlog<=4` ET `0 vente` -> probable MONO** : **9 cas** (petits batis sans
  rotation = mono-propriete probable).
- **`nlog>=8` ET `>=2 ventes` -> probable COPRO_NON_IMMAT** : **8 cas** (gros bati
  + rotation = lots vendus separement = pluri-propriete).
- **reste : 59 a arbitrer** (dont le cluster GENAS/HARMONIE a re-jointer en
  parcelle + verifier commune).
- **Lever supplementaire** : `sci_nom` present (20 cas) -> pencher MONO.

> Ces 17 pre-tris (9+8) ne sont PAS appliques — proposition uniquement.

### Effet orange estime : 530 -> ~76 (borne haute) / potentiellement moins

| Sortie de l'orange | n |
|---|--:|
| par **FUSION** (A_FUSER, deviennent RNC immat) | 133 |
| par **CLASSIFICATION** (MONO/SOCIAL/BUREAUX/COPRO_NON_IMMAT/MIXTE) | 321 |
| **restent AMBIGUS** (a arbitrer Yann) | 76 |
| **TOTAL** | 530 |

- **530 -> 76 AMBIGUS** si toutes les classifications sont retenues (les 321
  classees + 133 fusees sortent de l'orange).
- [DEDUCTION] La jointure **parcelle** (enrich_majic_full Montchat) reduirait
  encore les 76 AMBIGUS (une partie des 68 "0-ligne-MAJIC" recupererait des PM via
  le bgid). **Borne realiste apres parcelle : AMBIGUS < 76**, concentres sur PP
  pures + ROUTE GENAS hors-perimetre.

> **Nuance fusion** : comme note en B1, une adresse hors-RNC qui partage le bgid
> d'une copro RNC reste une **ligne distincte** ; "A_FUSER" = poser un tag /
> declencher une fusion UI, pas supprimer la ligne. L'effet "sort de l'orange" se
> materialise quand la fusion (ou le tag type) est applique en KV.

---

## NEUTRALITE — parc 15848 et Sigma ventes 932 INCHANGES

**Confirme.** Manche B2 = **pose de tags de TYPE** (`as.type` dans le KV
`secteur_assignments:dauphine-lacassagne-montchat`), PAS une modification du light :

- Aucune ecriture du light : `secteur_montchat_light.json` **non touche**. Donc
  `nb_log_bdnb`, `nb_lots_habitation`, `batiment_groupe_id`, `ventes_*` **inchanges**
  -> **parc 15848 INCHANGE**, **Sigma nb_ventes_logement = 932 INCHANGE**,
  **Sigma nb_ventes_total = 1217 INCHANGE**.
- `as.type` ne participe PAS au calcul du parc (`renderSecteur` dedup par bgid sur
  bgRncLots + bgBdnbResid, independant du type KV) ni au comptage des ventes.
  Un tag `mono`/`copro_non_immat`/`social`/`mixte`/`bureaux` ne fait que **colorer
  / categoriser** l'adresse dans le dashboard.
- **Seule exception possible (a part) : A_FUSER.** Une fusion REELLE (au-dela du
  simple tag) peut basculer la valeur d'un bgid estimation->RNC, comme en B1 (switch
  par bgid, parc-neutre net si lots RNC ~ BDNB). Ce dry-run **ne propose que le tag**,
  pas la fusion physique -> tant qu'on ne fait que tagger, le parc reste 15848.

**Application reelle (manche ulterieure)** : ecriture KV
`secteur_assignments:dauphine-lacassagne-montchat` via le worker, avec le **rituel
anti-drift non negociable** (`GET prod == backup local` AVANT tout POST, cf.
CLAUDE.md §6 et PIPELINE.md §8). **Aucune ecriture KV n'a ete faite ici.**

---

## Reserves / preuve vs deduction

- **[PREUVE]** : tout le playbook DL (5 scripts lus), colonnes MAJIC (`code_droit_libelle`,
  `numero_siren`, `groupe_personne_libelle`, `denomination`, `nature_voie`/`nom_voie`),
  PM-only du parquet (116 869/116 871 avec SIREN), distribution `code_droit_libelle`,
  champs du light Montchat, 133 A_FUSER (bgid in bg_rnc), 34 BUREAUX (usage Tertiaire),
  jointure adresse 239/530, absence de `_bgid_parcelle_montchat.json`, absence du slug
  `montchat` dans `secteurs.json`.
- **[DEDUCTION]** : la jointure parcelle resserrerait MONO/SOCIAL/COPRO et reduirait
  les AMBIGUS ; ROUTE GENAS = bord de commune / PP ; les distributions MONO-1PM /
  SOCIAL / MIXTE / COPRO_NON_IMMAT sont des **bornes de travail** (fiables sur les
  239 joints, indicatives sur le reste).
- **Necessite BDNB-live / MAJIC-live pour l'application reelle** :
  1. construire `data/_bgid_parcelle_montchat.json` (API BDNB `rel_batiment_groupe_parcelle`,
     ~672 bgids) ;
  2. ajouter le slug `montchat` a `secteurs.json` (geo `code_commune:["383","388"]`,
     metier needles DL, seuils 60/2, paths `_*_montchat`) ;
  3. lancer `enrich_majic_full.py --secteur montchat` pour la jointure PARCELLE
     canonique ;
  4. re-derouler l'arbre B2 sur cette sortie -> distribution finale resserree ;
  5. arbitrer les AMBIGUS residuels (mono vs copro_non_immat) avec Yann + verifier
     la commune reelle du cluster ROUTE GENAS.

---

*Aucune modification effectuee hors ce rapport. Aucun commit, aucun git add.
Fichiers temporaires supprimes.*
