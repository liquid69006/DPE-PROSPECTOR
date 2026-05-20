# Audit — lacunes du pipeline make_light (rattachements hors-RNC manqués)

> Lecture seule. Cible = prédicat exact *Hors-RNC actifs* de `renderSecteur` (non fusionnée, clé ∉ `cle_adresse` copro, pas d'immat, `nb_ventes_logement>0`). Caches RNC live non sollicités ici : on raisonne sur le snapshot et la chaîne `_canon_parts` de `make_light*`.

## ÉTAPE 1 — Cause-racine, par famille de cas résolus manuellement

### a) Variantes orthographiques (AYRES↔AIRES, GAL↔GENERAL, CAPT↔CAPITAINE)
`make_light*.py` normalise les tokens de la clé d'adresse via `_canon_parts` qui applique uniquement : (1) `VOIE` (type-de-voie `R`→`RUE`, `AV`→`AVENUE`, `BD`→`BOULEVARD`…), (2) `BIS` (`BIS`→`B`, `TER`→`T`), (3) `SAINTS` (`SAINT`→`ST`), (4) `ARTICLES` (`DE`/`DU`/`DES`/`LA`… strippés **en tête** du nom). **Aucune substitution sur les tokens internes du nom de voie** : `GAL` ≠ `GENERAL`, `CAPT` ≠ `CAPITAINE`, `AYRES` ≠ `AIRES` restent des tokens distincts → la jointure exacte `copro_by_cle.get(cle)` échoue → l'adresse chute au palier BDNB par num+voie ou GPS aveugle 50 m. **C'est par design** : ajouter une table `SUBS` à `_canon_parts` change la normalisation pour TOUT le pipeline (BDNB join, BAN, copro_by_cle, fusion bgid…) — risque réel de collisions de clés et de régression silencieuse. Convention établie (PIPELINE §4) = **ALIAS_RNC case-par-cas**, chirurgical.

**Abréviations actuellement gérées** :
| dict | contenu |
|---|---|
| `VOIE` (DL & MP, identique) | R/RUE, AV/AVE/AVENUE, BD/BLD/BOUL/BOULEVARD, CRS/COURS, IMP/IMPASSE, PL/PLACE, ALL/ALLEE, CHE/CH/CHEMIN, QU/QUAI, RTE/ROUTE, SQ/SQUARE, MTE/MONTEE, PAS/PASSAGE, GR (GRANDE RUE), TSSE/TERRASSE, VLA/VILLA |
| `BIS` | B/BIS, T/TER, Q/QUATER, A/C/D |
| `SAINTS` | SAINT→ST, SAINTE→STE, SAINTES→STES, SAINTS→STS |
| `ARTICLES` (tête seulement) | DE, DES, DU, D, LA, LE, LES, L, AUX |

**Abréviations / variantes attestées projet mais NON gérées** (corrigées au coup par coup via `ALIAS_RNC`) :
| famille | exemples projet |
|---|---|
| militaires | `GAL`/`GEN`/`GENL` → GENERAL · `MAL` → MARECHAL · `CMDT`/`CDT` → COMMANDANT · `CAPT`/`CNE` → CAPITAINE · `LT`/`LIEUT` → LIEUTENANT · `COL` → COLONEL |
| civils/religieux | `DR` → DOCTEUR · `PR`/`PROF` → PROFESSEUR · `PRES` → PRESIDENT · `MGR` → MONSEIGNEUR · `PCE` → PRINCE · `MNE` → MADELEINE · `FG` → FAUBOURG |
| variantes ortho | `AYRES` ↔ `AIRES` (BUENOS) |

### b) Adresses d'angle (Champfleury/Suffren, Gréard/Suffren, Gal Detrie/Charles Floquet)
L'auto-fusion `make_light` par `batiment_groupe_id` (`make_light*.py` ~l.778-846) **regroupe** les adresses partageant le même bgid BDNB, **puis splite par parité du numéro de voirie** (pair vs impair) — *garde-fou* indispensable pour ne pas fusionner les deux côtés d'une voie (le bgid 1/3/5 ≠ bgid 2/4/6 dans 99 % des cas, mais quand BDNB groupe un corner sur un seul bgid on l'aurait à tort).

Conséquence : pour un coin de rue (`6 Champfleury` PAIR + `45 Suffren` IMPAIR mais même bgid `PEQ4`), chacune se retrouve seule dans son seau parité → **groupe < 2 membres → fusion sautée**. Ce n'est PAS un bug mais une décision de sécurité. Le tri du *principal* (l.812 : `cle ∈ copro_by_cle → syndic → +ventes → adresse → cle`) garantit en revanche que quand la fusion par bgid s'applique, c'est bien la copro RNC qui devient le principal (cf. `28 RUE/PLACE DUPLEIX`, `38 CHARLES FLOQUET`). Reste les angles parité-mixte : **traitement manuel ALIAS_RNC obligé** (c'est la convention A2/A3 de `fix_mp_cibles_horsrnc.py`).

Le cas `4 OCTAVE GREARD ↔ 15 SUFFREN` (AA1378777) est spécifique : **bgids BDNB différents** (ZWNL ≠ 9HGZ), donc ni groupe bgid ni fusion possible. Le nom de la copro RNC (`4 AVENUE OCTAVE GREARD`) ne porte pas le n° de son `adresse_reference` (15 Suffren) — seule la lecture humaine fait le lien. **Impossible à détecter automatiquement** sans indexer `nom_copropriete` (fragile, beaucoup de faux positifs).

### c) Adresses fantômes DVF (Buenos Aires sans copro propre)
DVF agrège la mutation cadastrale sous une clé `(No voie, B/T/Q, Type de voie, Voie)` reflétant le **libellé voie de la DGFiP** (fichier MAJIC), qui **diverge couramment** du libellé RNC : `BUENOS AIRES` (DVF) ↔ `BUENOS AYRES` (RNC) ; `CAPT SCOTT` (DVF) ↔ `CAPITAINE SCOTT` (RNC) ; `GAL DE CASTELNAU` (DVF) ↔ `GENERAL DE CASTELNAU` (RNC). Ce sont des **variantes de libellé**, pas des erreurs cadastrales : la DGFiP code la voie en interne (`Code voie`) et le libellé n'est que descriptif. Le pipeline pourrait croiser `Code voie` DGFiP ↔ codes Insee/BAN, mais ça demande un référentiel de codes-voie par commune (non maintenu dans le projet). La convention actuelle = **détecter ces fantômes après coup** via l'audit hors-RNC (`scripts/audit_horsrnc_dvf.py`, `scripts/diag_orphelines_bdnb.py`) puis `ALIAS_RNC`.

## ÉTAPE 2 — Lacunes restantes (scan exhaustif des 2 secteurs)

Cibles hors-RNC actives scannées : **DL 83**, **MP 34**. Copros snapshot : DL 553, MP 821.

### P1 — abréviation de voie résolvable via extension SUBS

**0 cas** (0 ventes-logement).

_Aucun cas restant._

### P2 — même `batiment_groupe_id` qu'une copro RNC, fusion auto manquée

**21 cas** (100 ventes-logement).

**Sous-classes** : P2a=5, P2b=4, P2c=8, P2d=3, P2e=1.

| secteur | sub | cle hors-RNC | v_log | copro candidate (même bgid) | immat | lots | raison probable |
|---|---|---|--:|---|---|--:|---|
| dauph | **P2a** | `53\|RUE\|ETIENNE RICHERAND` | 10 | `51\|RUE\|ETIENNE RICHERAND` | AC3598851 | 64 | **RE-POINT** : copro RNC ancrée enterrée SOUS ce fantôme (auto-bgid-fusion a choisi le phantome DVF + de ventes comme principal → copro invisible). Pattern A3 de `fix_mp_cibles_horsrnc`. Re-point individuel. |
| dauph | **P2a** | `56\|AVENUE\|LACASSAGNE` | 4 | `54\|AVENUE\|LACASSAGNE` | AA4814810 | 50 | **RE-POINT** : copro RNC ancrée enterrée SOUS ce fantôme (auto-bgid-fusion a choisi le phantome DVF + de ventes comme principal → copro invisible). Pattern A3 de `fix_mp_cibles_horsrnc`. Re-point individuel. |
| dauph | **P2a** | `316\|RUE\|PAUL BERT` | 3 | `318\|RUE\|PAUL BERT` | AC6168629 | 6 | **RE-POINT** : copro RNC ancrée enterrée SOUS ce fantôme (auto-bgid-fusion a choisi le phantome DVF + de ventes comme principal → copro invisible). Pattern A3 de `fix_mp_cibles_horsrnc`. Re-point individuel. |
| motte | **P2a** | `9\|RUE\|GUESCLIN` | 8 | `3\|PASSAGE\|GUESCLIN` | AB1748391 | 104 | **RE-POINT** : copro RNC ancrée enterrée SOUS ce fantôme (auto-bgid-fusion a choisi le phantome DVF + de ventes comme principal → copro invisible). Pattern A3 de `fix_mp_cibles_horsrnc`. Re-point individuel. |
| motte | **P2a** | `156\|BOULEVARD\|GRENELLE` | 6 | `154\|BOULEVARD\|GRENELLE` | AB1105360 | 35 | **RE-POINT** : copro RNC ancrée enterrée SOUS ce fantôme (auto-bgid-fusion a choisi le phantome DVF + de ventes comme principal → copro invisible). Pattern A3 de `fix_mp_cibles_horsrnc`. Re-point individuel. |
| dauph | **P2b** | `9\|RUE\|PROFESSEUR PAUL SISLEY` | 16 | `7B\|RUE\|PROFESSEUR PAUL SISLEY` | AA0012898 | 225 | **ORPHELIN bgid-fusion** : src ET anchor tous deux *principals* sur même bgid+parité+voie — l'auto-fusion n'a PAS regroupé. Cause typique : un des deux ajouté APRÈS make_light par `fix_horsrnc_attribution` / `fix_*` (chaîne §5) → ordre des passes. |
| dauph | **P2b** | `260\|RUE\|PAUL BERT` | 5 | `264B\|RUE\|PAUL BERT` | AE1699040 | 8 | **ORPHELIN bgid-fusion** : src ET anchor tous deux *principals* sur même bgid+parité+voie — l'auto-fusion n'a PAS regroupé. Cause typique : un des deux ajouté APRÈS make_light par `fix_horsrnc_attribution` / `fix_*` (chaîne §5) → ordre des passes. |
| dauph | **P2b** | `12\|RUE\|CARRY` | 4 | `6\|RUE\|CARRY` | AC1825504 | 12 | **ORPHELIN bgid-fusion** : src ET anchor tous deux *principals* sur même bgid+parité+voie — l'auto-fusion n'a PAS regroupé. Cause typique : un des deux ajouté APRÈS make_light par `fix_horsrnc_attribution` / `fix_*` (chaîne §5) → ordre des passes. |
| dauph | **P2b** | `14\|RUE\|ST SIDOINE` | 3 | `12\|RUE\|ST SIDOINE` | AB2206571 | 165 | **ORPHELIN bgid-fusion** : src ET anchor tous deux *principals* sur même bgid+parité+voie — l'auto-fusion n'a PAS regroupé. Cause typique : un des deux ajouté APRÈS make_light par `fix_horsrnc_attribution` / `fix_*` (chaîne §5) → ordre des passes. |
| dauph | **P2c** | `14\|RUE\|ST MAXIMIN` | 6 | `1\|RUE\|ROSSAN` | AB2460335 | 53 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2c** | `38\|RUE\|BARABAN` | 5 | `37\|RUE\|BARABAN` | AC9726381 | 29 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2c** | `48\|RUE\|ST MAXIMIN` | 3 | `51\|RUE\|ST MAXIMIN` | AB2784080 | 50 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2c** | `18\|RUE\|ETIENNE RICHERAND` | 3 | `19\|RUE\|ETIENNE RICHERAND` | AG2447720 | 8 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2c** | `10\|RUE\|DAUPHINE` | 3 | `1\|RUE\|ST MAXIMIN` | AF0858860 | 14 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2c** | `46\|RUE\|ST MAXIMIN` | 2 | `43\|RUE\|ST MAXIMIN` | AB1744747 | 22 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| motte | **P2c** | `27\|RUE\|FREMICOURT` | 2 | `28\|RUE\|FREMICOURT` | AB3441680 | 16 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| motte | **P2c** | `3\|PLACE\|CAMBRONNE` | 2 | `6\|PLACE\|CAMBRONNE` | AB5809108 | 19 | **CORNER parité-mixte** (garde-fou bgid-fusion : split pair/impair → 2 buckets, chacun < 2 membres → skip). Sécurité parc, à instruire en ALIAS_RNC manuel. |
| dauph | **P2d** | `12\|RUE\|LOUIS JASSERON` | 6 | `17\|RUE\|LOUIS JASSERON` | AA7487564 | 29 | ancre déjà fusionnée ailleurs (`13|RUE|LOUIS JASSERON`) |
| dauph | **P2d** | `6\|RUE\|ST EUSEBE` | 5 | `8\|RUE\|ST EUSEBE` | AG4913810 | 15 | ancre déjà fusionnée ailleurs (`2|RUE|ST EUSEBE`) |
| dauph | **P2d** | `18\|RUE\|ST ANTOINE` | 3 | `17\|RUE\|ST ANTOINE` | AE9439365 | 45 | ancre déjà fusionnée ailleurs (`19|RUE|ST ANTOINE`) |
| dauph | **P2e** | `24\|AVENUE\|LACASSAGNE` | 1 | `24\|\|ET 24 BIS AVENUE LACASSAGNE` | AG1556893 | 64 | voie/nat différent(e) : abréviation non couverte par SUBS (chevauche P1) ou véritable changement de nom de voie. |

### P3 — orthographe RNC vs DVF (token-set ≥ 0.6, hors P1)

**0 cas** (0 ventes-logement).

_Aucun cas restant._

### Statistique — abréviations détectées dans les clés hors-RNC actives (toutes confondues)

| token | n |
|---|--:|
| `PROFESSEUR` → `PR` | 4 |
| `AIRES` → `AYRES` | 2 |
| `DOCTEUR` → `DR` | 1 |

## ÉTAPE 3 — Recommandations

**Bilan résiduel** : P1 = 0 cas, P2 = 21 cas (P2a 5 (31 v_log), P2b 4 (28 v_log), P2c 8 (26 v_log), P2d 3 (14 v_log), P2e 1 (1 v_log)), P3 = 0 cas (les ensembles peuvent se chevaucher).

1. **Étendre la table SUBS de `make_light*` ?** **À ÉVITER en l'état.** La normalisation `_canon_parts` impacte **tous** les consommateurs : `copro_by_cle` (jointure immat), `bdnb_par_voie` (jointure BDNB num+voie), tri de la principale fusion-bgid, label `_fusion_auto_label`. Une SUBS large risque de fusionner deux copros RNC distinctes ayant la même forme abrégée (collision `cle_adresse`). Si on l'introduit, le faire **token-par-token avec une whitelist courte** (GAL/GEN→GENERAL, CAPT/CNE→CAPITAINE, MAL→MARECHAL, AYRES→AIRES uniquement) **et** ajouter un test de régression : vérifier qu'aucune `cle_adresse` copro RNC ne collisionne après normalisation, sur les 2 secteurs (sinon ABORT). À défaut, **`ALIAS_RNC` reste la voie sûre** (déjà outillée par `fix_alias_rnc_meme_bgid.py` / `fix_mp_voie_abrev.py`).
2. **Améliorer la détection des bgid partagés (P2) ?** 
   - **P2a — RE-POINT (5 cas, 31 v_log)** :
     **À CORRIGER en priorité** (même cause-racine que `38 Charles
     Floquet` / A3 `fix_mp_cibles_horsrnc`). La copro RNC ancrée est
     enterrée sous un fantôme DVF principal — la copro est *invisible*
     dans le rendu, le parc compte le bucket BDNB phantom (sous-comptage
     systématique vs lots RNC réels). Pattern : **re-point individuel**
     (fix dédié, dry-run, parc model). Source-of-truth = critère
     `copro_by_cle` du tri principal-fusion (déjà ajouté au runtime
     post-Dupleix : à regen sur ces 6 cas), mais en attendant la regen
     → correctif chirurgical.
   - **P2b — ORPHELIN bgid-fusion (4 cas, 28 v_log)** :
     src ET anchor tous deux *principals* sur même bgid+parité+voie —
     `auto-bgid-fusion` aurait dû les regrouper. Cause vraisemblable :
     **l'un des deux a été ajouté APRÈS la passe `make_light` par
     un correctif** (`fix_horsrnc_attribution` réintroduit des adresses
     hors-RNC manquantes, `fix_invisible_insecteur_bgids`…). L'auto-
     bgid-fusion ne s'exécute pas une seconde fois. **Solution générique** :
     ajouter une passe `propage_fusion_bgid_post_correctif` qui ré-applique
     l'algorithme l.778-846 de make_light sur le light patché (idempotente,
     respecte parité), OU correctif chirurgical pour chaque cas. À étudier.
   - **P2c — CORNER parité-mixte (8 cas, 26 v_log)** :
     **NE PAS toucher le garde-fou parité** (sécurité parc PIPELINE §9.3 —
     mesuré -514 DL / -423 MP en cas d'affaiblissement). Traiter chaque
     coin par ALIAS_RNC manuel après vérification GPS+bgid (miroir bgid
     dédup ou parc-neutre selon).
   - **P2d/e (4 cas)** : ancre déjà
     fusionnée ailleurs, ou voie/nat divergent — instruire individuellement.

3. **Cas résiduels (P3 hors P1/P2)** : **0 cas.** 
4. **Cas hors-pipeline (vraies monopropriétés / copros non immatriculées)** : structurellement rien à faire — documenter (catégorie B de `fix_mp_cibles_horsrnc.py`, tracer dans `data/diag_*.md`).


---
*Audit lecture seule — `scripts/audit_lacunes_pipeline.py`. N'écrit que ce rapport.*