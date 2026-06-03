# Diag ENRICH MAJIC montchat (Phase 5, infra MAJIC, ETAPE 2 - EXECUTION)

> Tache d'EXECUTION. PYTHONUTF8=1, prints ASCII-safe. **AUCUNE ecriture KV.
> AUCUN commit / git add / push.** Date : 2026-06-03.
> Sorties produites (side-files de SIGNAUX, light NON touche) :
> `data/_bgid_parcelle_montchat.json` (cache parcelle) +
> `data/_enrich_majic_montchat_full.json` (sweep). Le light
> `secteur_montchat_light.json` n'a PAS ete modifie.
>
> **Convention** : [PREUVE] = sortie lue ; [DEDUCTION] = inference.

---

## 0. Resume du run

| Item | Valeur |
|---|---|
| Cache parcelle build | **resumable maison** `scripts/_fetch_bgid_parcelle_montchat.py` |
| Pourquoi pas le fetch interne | le fetch interne `enrich_majic_full` a un `sleep(0.05)` (20 req/s) -> **BDNB HTTP 429 massif** des ~bgid 100, et il **cache `[]` sur 429** (donc re-run non-reparable) ; il n'ecrit le cache qu'**en fin de boucle** (crash = tout perdu) |
| Fetcher maison | throttle 0.25s + **backoff exponentiel sur 429** + **checkpoint disque /25** + resumable (ne refetch que absent/vide) |
| Appels BDNB | **1143** bgids distincts (1 appel/bgid), endpoint public `rel_batiment_groupe_parcelle` |
| Resultat fetch | **ok=1134, vide=9, err=0** (0 echec, 0 429 final), duree **588s (~10 min)** |
| Nb re-runs cache | **1 seul run** suffisant (0 erreur ; les 9 "vide" sont legitimes = bgid sans parcelle BDNB) |
| Sweep enrich | `enrich_majic_full.py --secteur montchat --skip-bdnb-completion` ; read parquet 116871 lots en 1.9s, sweep 1430 adr en 2.2s |
| Ecriture light | **AUCUNE** (enrich lit le light, ecrit seulement `cache_bg` + `enrich_majic`) [PREUVE code l.99 read / l.123+l.309 write] |
| Ecriture KV | **AUCUNE** |
| Commit | **AUCUN** |

> **Note sequencement** : le run interne `enrich_majic_full --secteur montchat`
> (sans `--skip`) a ete LANCE puis ARRETE avant tout write (429 massif, cache
> jamais ecrit -> 0 poison). Le cache a ete (re)construit proprement par le
> fetcher resumable, puis le sweep relance avec `--skip-bdnb-completion`.

---

## 1. VIGILANCE 69385 : VERDICT = RAS

**Aucune parcelle `69385000...` n'est sortie dans le cache.** [PREUVE]

Distribution des prefixes parcelle dans `_bgid_parcelle_montchat.json` :

| prefixe | nb parcelles |
|---|--:|
| `69383000` (Lyon 3e) | **1237** |
| `69388000` (Lyon 8e) | **11** |
| `69385000` (Lyon 5e) | **0** |

-> La jointure MAJIC est saine avec `code_commune=["383","388"]`. Les 11 copros
declarees arrondissement RNC 69385 ont bien leurs **parcelles physiques en
383/388** (artefact de declaration RNC, pas de geo). **Conforme a la prediction
du diag infra (vigilance c probable non-besoin).** NE PAS toucher
`secteurs.json` : aucun ajout `"385"`/`"69385000"`/`"69005"` necessaire.

---

## 2. COUVERTURE PARCELLE

| Item | Valeur |
|---|--:|
| bgids light distincts | **1143** |
| resolus (>=1 parcelle BDNB) | **1134 (99,2 %)** |
| dans cache mais vide `[]` | **9** (bgid sans parcelle BDNB - legitime) |
| absents du cache | **0** |

Cote sweep enrich (par ADRESSE, 1430 au total) :
- `ok` (>=1 lot MAJIC PM joint) : **968 (67,7 %)**
- `no_majic` (parcelle sans lot PM) : **451**
- `no_parcelle` (bgid sans parcelle) : **11**

> Couverture parcelle **excellente (99,2 %)** vs jointure-adresse B2 (239/530).
> Les 451 `no_majic` = parcelle resolue mais **0 lot PM** dessus (angle-mort PP
> RGPD, pas un trou de jointure).

---

## 3. CLASSIF FERMES (perimetre hors-RNC restant)

**Perimetre** = adresses hors-RNC actives du light : `!in_copro & !has_immat &
!is_fa` = **576 adresses** [PREUVE].

> **Ecart de perimetre vs B2 (530) a expliciter** : B2 partait de 530 "hors-RNC
> actifs" puis retirait 133 A_FUSER (meme bgid qu'une copro RNC) -> bornes B2
> calculees sur ~397-408. Ici le filtre `!in_copro & !has_immat & !is_fa` lu
> DIRECTEMENT sur le light POST-B1 (B2/B2a = tags KV, **PAS** ecrits dans le
> light) donne **576**. Les 133 A_FUSER de B2 sont des **tags KV non encore
> poses** : ils restent donc `!in_copro` dans le light et sont comptes ici. La
> classif ci-dessous porte sur les **576**, surensemble des ~408 de B2.

Comptage PROPRIETAIRES recompte **directement depuis le parquet**, en EXCLUANT
syndic/gerant/mandataire/gestionnaire/usufruitier/nu-proprietaire (le playbook
DL filtre ces non-proprietaires ; `enrich_majic_full` ne filtre PAS, d'ou ce
recompte) [PREUVE `_analyse_enrich_montchat.py`].

| Classe | n | Critere |
|---|--:|---|
| **MONO** | **234** | 1 proprio PM + ratio lots/log >= 0,9 |
| **MONO_weak** | **57** | 1 seul proprio PM mais ratio < 0,9 (parcelle sous-couverte) |
| **COPRO** | **74** | >= 2 proprios PM distincts |
| **ANGLE-MORT PP** | **211** | 0 proprio PM (no_majic / no_parcelle / 0 SIREN apres filtre syndic) |
| **TOTAL** | **576** | |

[ref] flag `is_mono` brut d'enrich (sans filtre syndic) sur ce perimetre : 243.

> **Caveat MONO ratio > 1** : beaucoup de MONO ont `ratio_pm_bdnb` > 1 (jusqu'a
> 9,5). Ratio = lots_MAJIC_parcelle / nb_log_bdnb_adresse. Un ratio >> 1 = la
> **parcelle regroupe plusieurs batis/adresses** (1 seul gros proprio PM sur la
> parcelle entiere) : c'est un signal mono **fort** au sens propriete (1 SIREN
> detient tout), mais le `nb_log_bdnb` de la seule adresse sous-estime. A
> confirmer en arbitrage (mono vrai vs ensemble mono-propriete multi-batis).

---

## 4. COMPARAISON AUX BORNES DU DRY-RUN B2

Bornes B2 (jointure ADRESSE, faible, 239/530 couverts) : MONO-PM ~85, COPRO ~23,
AMBIGU 76.

| Signal | Borne B2 (adresse) | Ferme (parcelle) | Delta | Cause de l'ecart |
|---|--:|--:|--:|---|
| MONO (via PM) | ~85 | **234** (+57 weak) | **+149** | jointure parcelle BDNB recupere les lots PM qu'une jointure par adresse normalisee ratait (1 bgid groupe N adresses postales, 1 seule porte les lots) |
| COPRO (>=2 PM) | ~23 | **74** | **+51** | idem : la parcelle reunit tous les lots PM -> revele les pluri-proprietes invisibles a l'adresse |
| ANGLE-MORT / AMBIGU | 76 (AMBIGU) | **211** (angle-mort total perimetre) | n/a | perimetres differents (B2 AMBIGU = sous-ensemble ; ici angle-mort sur 576) |

> **Les chiffres FERMES ont fortement bouge a la hausse** apres la vraie jointure
> parcelle : la jointure ADRESSE de B2 etait une **borne basse** (manquait ~291
> adresses sur 530). La jointure PARCELLE retrouve la propriete PM sur 968/1430
> adresses (67,7 %) au lieu de 239/530. MONO et COPRO grimpent en consequence,
> exactement comme anticipe par B2 ("la jointure parcelle resserrerait
> MONO/SOCIAL/COPRO").

---

## 5. LES 76 AMBIGUS B2 : residu reel 0-PM apres jointure parcelle

| Sortie | n |
|---|--:|
| **bascule MONO** (1 proprio PM trouve via parcelle) | **24** |
| **bascule COPRO** (>=2 proprios PM) | **13** |
| **RESTENT 0-PM reel** (no_PM_parcelle / no_parcelle) | **39** |
| **TOTAL** | **76** |

**-> 37/76 ambigus se resolvent par la jointure parcelle** (24 mono + 13 copro).
Il en RESTE **39 reellement 0-PM** (parcelle resolue mais aucun lot PM dessus =
angle-mort PP RGPD, OU bgid vide).

### sci_nom -> mono

- Ambigus B2 portant un `sci_nom` : **20**
- dont **bascules MONO via parcelle** (PM reel trouve) : **6**
- dont **restent 0-PM** malgre le `sci_nom` : **9**
- (les 5 autres sci_nom basculent COPRO : la SCI nommee ne detient pas seule)

> **Nuance importante** : un `sci_nom` dans le light **ne suffit pas** a basculer
> mono mecaniquement. Sur les 20, seuls 6 ont un PM proprietaire reel sur la
> parcelle ; 9 restent 0-PM (la SCI n'apparait PAS comme proprietaire PM dans le
> parquet MAJIC PM-only - soit SCI radiee, soit non captee, soit proprio = PP).
> -> Ces 9 sont a arbitrer manuellement (le `sci_nom` reste un **indice** mono,
> pas une preuve de propriete exclusive).

### LISTE RESIDU reellement 0-PM (39) - pour arbitrage manuel

`status=no_PM_parcelle` sauf mention ; nlog=nb_log_bdnb ; vlog=nb_ventes_logement.

| cle | nlog | bgid | vlog | sci_nom |
|---|--:|---|--:|---|
| 40\|ROUTE\|GENAS | 40 | bdnb-bg-65W8-1KMQ-2TAR | 0 | - |
| 177\|COURS\|DOCTEUR LONG | 38 | bdnb-bg-EBC7-FJMV-2MV4 | 0 | - |
| 179\|COURS\|DOCTEUR LONG | 38 | bdnb-bg-EBC7-FJMV-2MV4 | 0 | - |
| 150\|ROUTE\|GENAS | 29 | bdnb-bg-CGYC-HHU9-94E4 | 0 | - |
| 2\|BOULEVARD\|PINEL | 28 | bdnb-bg-Q3LE-MSPC-6UYP | 0 | - |
| 25B\|COURS\|DOCTEUR LONG | 26 | bdnb-bg-ECG1-MH9G-RHE8 | 0 | SCI LA CANOPEE |
| 8\|RUE\|DOCTEUR REBATEL | 25 | bdnb-bg-P2DG-Q47U-658U | 3 | MAXIMILIEN 55 |
| 162\|ROUTE\|GENAS | 23 | bdnb-bg-AW77-VX5A-G1FG | 1 | SCI IMMOVAPI |
| 160\|ROUTE\|GENAS | 20 | bdnb-bg-D6DX-2E24-ZH3P | 1 | SCI 3D |
| 27\|RUE\|BALME | 18 | bdnb-bg-2QXR-GNCQ-CULG | 2 | - |
| 2\|RUE\|RUCHE | 18 | bdnb-bg-1R2R-9QN4-QZAY | 0 | - |
| 22\|RUE\|BALME | 18 | bdnb-bg-2QXR-GNCQ-CULG | 0 | SCI BALME |
| 67\|AVENUE\|LACASSAGNE | 17 | bdnb-bg-4YXS-5BP6-9YFV | 1 | - |
| 28\|RUE\|ROUX SOIGNAT | 17 | bdnb-bg-2YLM-7699-HHKZ | 0 | - |
| 84\|ROUTE\|GENAS | 13 | bdnb-bg-LSBD-A8MX-J4SF | 2 | - |
| 14\|RUE\|CHARLES RICHARD | 13 | bdnb-bg-93UB-G9X3-JLM7 | 0 | - |
| 10\|RUE\|ST ISIDORE | 11 | bdnb-bg-8WHS-2GTL-S6VF | 0 | SCI DURGA |
| 10B\|RUE\|ST ISIDORE | 11 | bdnb-bg-8WHS-2GTL-S6VF | 0 | SCI DURGA |
| 11\|RUE\|PROFESSEUR FLORENCE | 11 | bdnb-bg-QRC7-431U-DGQS | 0 | - |
| 20B\|COURS\|RICHARD VITTON | 11 | bdnb-bg-2S53-ELZT-GXW1 | 0 | - |
| 16\|IMPASSE\|SABLON | 7 | bdnb-bg-VCYU-ZFNY-T97Y | 1 | - |
| 6\|IMPASSE\|LINDBERG | 7 | bdnb-bg-P3KY-XPS9-U8AR | 1 | - |
| 12\|RUE\|EGLISE | 3 | bdnb-bg-AFN9-NLTR-RQ9V | 1 | - |
| 5\|RUE\|JULIEN | 2 | bdnb-bg-NYSK-17DL-F91N | 2 | - |
| 13\|RUE\|CAPITAINE | 2 | bdnb-bg-WQ3R-4SRX-MN7V | 0 | - |
| 12\|RUE\|JULES MASSENET | 2 | bdnb-bg-AAZP-SMPC-D3SQ | 1 | - |
| 14\|RUE\|ALFRED DE MUSSET | 2 | bdnb-bg-X2CW-95JR-KA89 | 1 | - |
| 27\|RUE\|BONNAND | 2 | bdnb-bg-SCRM-1NCF-ZHH9 | 1 | - |
| 2\|IMPASSE\|LUTIN | 2 | bdnb-bg-PYYG-73T3-A6PY | 1 | - |
| 1\|AVENUE\|CHATEAU | 2 | bdnb-bg-CR6N-Z6W2-AVA9 | 0 | IJK AVENIR |
| 3\|RUE\|EGLISE | 2 | bdnb-bg-GPBS-3CRM-6164 | 0 | SCI JULIMIKE |
| 32\|RUE\|JULES MASSENET | 2 | bdnb-bg-NLV8-DHWS-31F9 | 0 | - |
| 38\|AVENUE\|ACACIAS | 0 | bdnb-bg-MCHK-YQFV-MLCM | 2 | - |
| 67B\|AVENUE\|LACASSAGNE | 0 | bdnb-bg-4YXS-5BP6-9YFV | 1 | - |
| 45B\|RUE\|JEANNE D ARC | 0 | bdnb-bg-6NJ4-7KH1-4JGC | 1 | - |
| 66B\|COURS\|RICHARD VITTON | 0 | bdnb-bg-ZET4-Y1JM-28JP | 1 | - |
| 23B\|RUE\|FEUILLAT | 0 | bdnb-bg-A8MV-CV23-LP7H | 1 | - |
| 9B\|RUE\|VILLEBOIS MAREUIL | 0 | bdnb-bg-NEJZ-W1WK-SB2Y | 1 | - |
| 13B\|RUE\|CAPITAINE | 0 | bdnb-bg-WQ3R-4SRX-MN7V | 1 | - |

**Observations** :
- **Cluster ROUTE GENAS** (40/150/160/162/84) reste 0-PM : la parcelle est
  resolue (donc pas un bord de commune comme craint en B2) mais **0 lot PM** =
  proprietaires PP (ou SCI non-PM-listees). Plusieurs portent une SCI (IMMOVAPI,
  3D) -> indice mono a verifier hors-bande.
- **Doublons bgid** (meme bati, 2 facades) : 27/22 BALME (CULG), 10/10B ST
  ISIDORE (S6VF, SCI DURGA), 67/67B LACASSAGNE (9YFV), 13/13B CAPITAINE
  (MN7V) -> a traiter en paire.
- Les 7 lignes `nlog=0` (38 ACACIAS, 67B LACASSAGNE, B-suffixes) = facades
  secondaires sans logement BDNB propre, faible enjeu.

### LISTE bascule MONO (24) - 1 proprio PM trouve

86/88 GENAS, 200 GENAS, 70 GENAS, 8 IMPASSE LINDBERG, 100 DOCTEUR LONG, 124
DAUPHINE (SCI 124 RUE DU DAUPHINE), 110 DOCTEUR LONG (G ET PH RESIDENCE
MONTCHAT), 170 GENAS, 26 HARMONIE, 132 DAUPHINE, 110 DAUPHINE, 16 RUCHE, 20
GENAS, 43 DOCTEUR LONG, 37 ACACIAS, 7 LOUIS, 55 DOCTEUR LONG (SCI DES 4A), 25
DOCTEUR BONHOMME, 37 CHATEAU, 4 SPORTS, 6 PALAIS D ETE (SCI), 17 CAPITAINE (SCI
DU CAPITAINE), 91B BALME (SCI AVAKIAN).

> 18/24 ont `ratio > 1` (parcelle multi-batis 1 proprio) ; 3 ont ratio < 0,9 (8
> LINDBERG 0,087 ; 7 LOUIS 0,429 ; 25 BONHOMME 0,25) = mono "faible", PM minoritaire
> sur la parcelle -> a confirmer.

### LISTE bascule COPRO (13) - >=2 proprios PM

10/12 HARMONIE (2 PM, 72 log), 134/138 GENAS (11 PM, SCI BLEU VERT / PUCCINI),
101 LACASSAGNE (13 PM, 58 log), 125/123 DAUPHINE (3 PM), 106 DOCTEUR LONG (2),
48 GENAS (2), 82 DOCTEUR LONG (2), 5 DOCTEUR LONG (8 PM, NADELI), 14 DOCTEUR
LONG (2, MONTCHATPSY), 2 GENAS (2).

> Le cluster HARMONIE (72 log) et 101 LACASSAGNE (58 log, 13 PM) = vraies copros
> non-immatriculees de PM, conforme a l'hypothese B2.

---

## 6. CONFIRMATIONS

- **AUCUNE ecriture KV.** [confirme]
- **AUCUN commit / git add / push.** [confirme]
- **Light `secteur_montchat_light.json` NON modifie** : enrich lit le light et
  n'ecrit que `_bgid_parcelle_montchat.json` + `_enrich_majic_montchat_full.json`
  (side-files de signaux). [PREUVE code enrich l.99/123/309]
- **Aucune modif de `secteurs.json`** (verdict 69385 = RAS, rien a ajouter). DL
  et MP non touches. `index.html` non touche.
- Scripts ajoutes (non commites) : `scripts/_fetch_bgid_parcelle_montchat.py`
  (fetcher resumable) + `scripts/_analyse_enrich_montchat.py` (analyse).

---

*Aucune ecriture KV, aucun commit. Side-files de signaux uniquement.*
