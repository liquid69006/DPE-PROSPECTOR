# Diagnostic — 4 ensembles immobiliers MP signalés terrain

> **Lecture seule.** Aucun fichier de données / cache modifié. RNC live
> tabular-api `3ea8e2c3…` et BAN `api-adresse.data.gouv.fr` interrogés
> en lecture, BDNB rel via cache `_horsrnc_bdnb_live_motte_picquet.json`.

## Préambule géographique

Les 12 adresses signalées se concentrent autour de **deux îlots du
Front de Seine, 75007** :
- **Îlot Buenos Ayres / Léon Bourgeois** (~ lat 48.857) — angle rue
  Buenos Ayres × allée Léon Bourgeois × quai Jacques Chirac (ancien
  Quai Branly avant 2017).
- **Îlot Suffren / Général Détrie** (~ lat 48.853) — av Suffren
  × av Général Détrie × proche Champ de Mars.

La **renomination Quai Branly → Quai Jacques Chirac (2017)** affecte
G3/G4 : RNC, BAN et BDNB co-existent sous les deux noms. La numérotation
du quai change aussi : `67 Quai Jacques Chirac` (BAN lon 2.295301)
n'est PAS au même endroit que `69/71 Quai Jacques Chirac` (≈ 400 m de
distance — sur un long quai, blocs séparés).

---

## GROUPE 1 — `2A + 4 RUE BUENOS AIRES + 6/8 ALLEE LEON BOURGEOIS`

### ÉTAPE 1 — État du light

| adresse signalée | clé light | bgid | immat | syndic | nb_lots | nb_log_bdnb | v_log | `_fusion_auto` |
|---|---|---|---|---|--:|--:|--:|---|
| 2A RUE BUENOS AIRES | **absente** (BAN `2a` existe, score 0.76, lon 2.292019) | — | — | — | — | — | — | — |
| 4 RUE BUENOS AIRES | `4\|RUE\|BUENOS AIRES` | `bdnb-bg-BBRR-9P88-BTJ5` | ∅ | ∅ | — | 20 | 1 | non |
| 6 ALLEE LEON BOURGEOIS | `\|ALLEE\|LEON BOURGEOIS` (clé sans num) | `bdnb-bg-M3B8-DJ7V-TCKJ` | ∅ | ∅ | — | 16 | 1 | True → `1\|RUE\|BUENOS AYRES` |
| 8 ALLEE LEON BOURGEOIS | idem (même clé) | idem | idem | idem | — | 16 | 1 | True → `1\|RUE\|BUENOS AYRES` |

**bgids distincts** : BBRR (4 Buenos Aires) ≠ M3B8 (Allée Léon
Bourgeois). Aucune fusion-bgid possible. La clé `|ALLEE|LEON
BOURGEOIS` est UNIQUE pour toute l'allée (make_light ne distingue pas
les numéros 2/4/6/8 — anomalie côté DVF/BAN ; toute la "rangée" est
agrégée).

### ÉTAPE 2 — Vérification RNC

Snapshot MP : **3 copros mentionnant CHAMPFLEURY/BUENOS AYRES** dans
le voisinage :

| immat | cle_adresse | nom | lots | syndic |
|---|---|---|--:|---|
| **AD4111738** | `1\|RUE\|BUENOS AYRES` | "1 RUE DE BUENOS AYRES" | 13 | CGA (déjà mappée → allée L. Bourgeois) |
| **AF1857283** | `1B\|RUE\|BUENOS AYRES` | "1 bis BUENOS AYRES" | 22 | SOLANOCTE |
| **AB3659166** | `3\|RUE\|BUENOS AYRES` | "BUENOS AYRES-3 J Y" | 30 | CF GESTION (déjà rattachée DVF `3 BUENOS AIRES`) |

RNC live `BUENOS` 75007 → 3 copros (identiques au snapshot). RNC live
`BOURGEOIS` 75007 → **0 ligne** (l'Allée Léon Bourgeois n'est pas
voie d'immatriculation RNC).
BDNB rel cache : `BBRR-9P88-BTJ5` → `immats=[]` (BDNB ne lie pas le 4
BUENOS AIRES à une copro). `M3B8` → `AD4111738` (cohérent avec la
mappe existante).

**Aucune copro RNC immatriculée à `2A` ni `4 RUE BUENOS AIRES`**
selon les sources publiques.

### ÉTAPE 3 — Mécanisme proposé

- **6/8 ALLEE LEON BOURGEOIS** : **DÉJÀ RATTACHÉS** (ALIAS_RNC
  `|ALLEE|LEON BOURGEOIS → 1|RUE|BUENOS AYRES` AD4111738, lot
  fix_mp_cibles_horsrnc A1, parc-neutre). Rien à faire.
- **4 RUE BUENOS AIRES** : aucun match RNC. 2 hypothèses :
  1. **Hypothèse "extension AF1857283"** : si le terrain confirme que
     `1bis BUENOS AYRES` (AF1857283, 22 lots) couvre 2A/4 BUENOS
     AIRES, → `ALIAS_RNC += { "4|RUE|BUENOS AIRES": "1B|RUE|BUENOS
     AYRES" }`. Demande **confirmation Pappers/acte**.
  2. **Catégorie B** : copro non immatriculée (résidentiel collectif
     20 lgts BDNB, hors RNC).
- **2A RUE BUENOS AIRES** : absent du DVF → pas de vente → pas
  d'orpheline DVF à rattacher actuellement.

### ÉTAPE 4 — Dry-run hypothétique (non appliqué)

| cas | mécanisme | clé | → ancre | immat | impact parc |
|---|---|---|---|---|---|
| sûr | — (déjà rattaché) | `\|ALLEE\|LEON BOURGEOIS` | `1\|RUE\|BUENOS AYRES` | AD4111738 | (n/a) |
| **hypothèse confirmation user** | ALIAS_RNC miroir bgid (BBRR≠AF1857283) | `4\|RUE\|BUENOS AIRES` | `1B\|RUE\|BUENOS AYRES` | **AF1857283** | switch BDNB 20→RNC 22 (+2 sur bgid BBRR si AF1857283 sans autre adresse light) |

---

## GROUPE 2 — `7 AV GENERAL DETRIE + 55 AV SUFFREN`

### ÉTAPE 1 — État du light

| adresse signalée | clé light | bgid | immat | syndic | nb_lots | nb_log_bdnb | v_log | `_fusion_auto` |
|---|---|---|---|---|--:|--:|--:|---|
| 7 AV GENERAL DETRIE | **absente** (BAN score 0.97 housenumber, lon 2.298319) | — | — | — | — | — | — | — |
| 55 AVENUE SUFFREN | `55\|AVENUE\|SUFFREN` | `bdnb-bg-GQAG-T52L-7376` | ∅ | ∅ | — | 15 | 1 | non · fsrcs = `['5\|AVENUE\|GAL DETRIE']` |

### Découverte importante (latente)

Dans le light, **deux variantes coexistent** pour le 5 av du Général
Détrie :
- `5|AVENUE|GENERAL DETRIE` (clé du snapshot, bgid `Y2Q8-C4WX-26E9`) →
  **copro AD5265665 "5 AVENUE DU GENERAL DETRIE"** (11 lots) — *correctement
  rattachée*.
- `5|AVENUE|GAL DETRIE` (clé DVF abrégée, bgid `GQAG-T52L-7376`,
  **différent**) → fusé dans `55|AVENUE|SUFFREN`.

Les deux clés pointent vers le même bâti physique mais BDNB a deux
bgids distincts (GQAG et Y2Q8). La fusion auto bgid n'a donc pas pu
les regrouper, et `make_light` n'a pas d'`ALIAS_RNC GAL→GENERAL` pour
le 5.

### ÉTAPE 2 — Vérification RNC

RNC live `DETRIE` 75007 → **1 copro** : `AD5265665` au `5 AVENUE DU
GENERAL DETRIE` (11 lots). Snapshot a aussi `AC2917656` au `6 AVENUE
DU GENERAL DETRIE` (13 lots), pair en face. **Aucune copro au n° 7**
ni au n° 55 av Suffren. BDNB rel cache : `GQAG-T52L-7376` →
`immats=[]`.

### ÉTAPE 3 — Mécanisme proposé

- **55 AV SUFFREN** : hr-active 1 vlog. Hypothèse terrain user = même
  ensemble que 5/7 Général Détrie. Si confirmé que AD5265665 couvre
  l'angle Suffren/Détrie :
  - `ALIAS_RNC += { "55|AVENUE|SUFFREN": "5|AVENUE|GENERAL DETRIE" }`
  - Demande **confirmation Pappers/acte** (la copro a 11 lots
    seulement, contre 15 BDNB sur GQAG — gap +4 plausible si quelques
    lots commerciaux / annexes non RNC).
- **7 AV GENERAL DETRIE** : absent DVF → pas d'orpheline à rattacher
  actuellement (pas d'enjeu data immédiat).

### ÉTAPE 4 — Dry-run hypothétique (non appliqué)

| cas | mécanisme | clé | → ancre | immat | impact parc |
|---|---|---|---|---|---|
| **hypothèse confirmation user** | ALIAS_RNC miroir bgid (GQAG → Y2Q8) | `55\|AVENUE\|SUFFREN` | `5\|AVENUE\|GENERAL DETRIE` | **AD5265665** | switch BDNB 15→RNC 11 sur bgid GQAG = **−4** (bgid Y2Q8 reste à 11). **Chaîne** : 5 GAL DETRIE (fsrc de 55 SUFFREN, bgid GQAG) à re-pointer aussi vers 5 GENERAL DETRIE — sans quoi orphelin. |

---

## GROUPE 3 — `2 RUE BUENOS AIRES + 69A QUAI JACQUES CHIRAC + 1 AV SUFFREN`

### ÉTAPE 1 — État du light

| adresse signalée | clé light | bgid | immat | nb_log_bdnb | v_log | `_fusion_auto` |
|---|---|---|---|--:|--:|---|
| 2 RUE BUENOS AIRES | `2\|RUE\|BUENOS AIRES` | `bdnb-bg-FB3W-4B4K-PYEL` | ∅ | 15 | 1 | non |
| 69A QUAI JACQUES CHIRAC | **absente** (BAN score 0.97 housenumber, lon 2.291646) | — | — | — | — | — |
| 1 AVENUE SUFFREN | **absente** (BAN score 0.97, lon 2.291530) | — | — | — | — | — |

GPS : `1 av Suffren` BAN est à **52 m** de `2 RUE BUENOS AIRES` light,
et `69A QUAI JACQUES CHIRAC` BAN à ≈ 30 m également. Cohérent avec
un même bloc d'angle.

### ÉTAPE 2 — Vérification RNC

- Snapshot MP : pas de copro à `2 BUENOS AIRES`, `1 SUFFREN`, ni `69A
  QUAI JACQUES CHIRAC`. La copro `9 SUFFREN` (AC9106204, 51 lots) est
  à ≈ 100 m, hors bloc.
- RNC live `CHIRAC`/`BRANLY` 75007 : `AA8105728` (59 J Chirac, 18
  lots), `AB3789013` (67 J Chirac, 21 lots), `AA3438710` (65 Branly,
  20 lots). Aucune au n° 69/69A.
- BDNB rel cache `FB3W-4B4K-PYEL` : `immats=[]`.

### ÉTAPE 3 — Mécanisme proposé

**Aucune copro RNC immatriculée** ne couvre cet îlot (vérifié national).
- `2 RUE BUENOS AIRES` : **Catégorie B** (vraie copro non
  immatriculée, résidentiel collectif 15 lgts BDNB, 1 vente). À
  laisser tel quel, conforme à la convention `fix_mp_cibles_horsrnc`
  catégorie B. Cohérent avec le diag orphelines BDNB du 2026-05-19.
- `69A QUAI JACQUES CHIRAC` + `1 AVENUE SUFFREN` : absents DVF/light
  → pas d'enjeu data immédiat. Si DVF y enregistre des ventes plus
  tard, traiter alors.

### ÉTAPE 4 — Dry-run hypothétique

| cas | mécanisme | recommandation |
|---|---|---|
| `2\|RUE\|BUENOS AIRES` | (aucun) | Catégorie B confirmée — pas d'action |

---

## GROUPE 4 — `67B QUAI BRANLY + 69 QUAI JACQUES CHIRAC + 2/4 ALLEE LEON BOURGEOIS`

### ÉTAPE 1 — État du light

| adresse signalée | clé light | bgid | immat | nb_log_bdnb | v_log | `_fusion_auto` |
|---|---|---|---|--:|--:|---|
| 67B QUAI BRANLY | **absente** (BAN score 0.71 *street level* — `67B` housenumber n'existe pas en BAN) | — | — | — | — | — |
| 69 QUAI JACQUES CHIRAC | `69\|QUAI\|JACQUES CHIRAC` | `bdnb-bg-6SBC-228Y-4AEN` | ∅ | 15 | 0 | True → `71\|QUAI\|JACQUES CHIRAC` |
| 2 ALLEE LEON BOURGEOIS | `\|ALLEE\|LEON BOURGEOIS` | `bdnb-bg-M3B8-DJ7V-TCKJ` | ∅ | 16 | 1 | True → `1\|RUE\|BUENOS AYRES` |
| 4 ALLEE LEON BOURGEOIS | idem | idem | ∅ | 16 | 1 | True → `1\|RUE\|BUENOS AYRES` |

### ÉTAPE 2 — Vérification RNC

- Snapshot MP : `AB3789013` "67 Quai Jacques Chirac" (21 lots) existe
  — **mais GPS à 400 m** des bgids 6SBC/M3B8 (BAN 67 J Chirac =
  lon 2.295301 vs 69 J Chirac = lon 2.291525). **Bâtiment distinct,
  bloc différent du quai**. *Pas un candidat valide* malgré la
  proximité de numérotation.
- RNC live `BRANLY` 75007 : 1 copro `AA3438710` au **65** Branly (20
  lots). Aucune au 67B/69. La renomination Branly→Jacques Chirac
  rend la zone confuse, mais le RNC ne couvre ni 67B BRANLY ni 69
  J. CHIRAC (déjà documenté `diag_21_floquet.md` et
  `audit_orphelines_bdnb_motte.md`).
- BDNB rel cache `6SBC` : `immats=[]`.

### ÉTAPE 3 — Mécanisme proposé

- **2/4 ALLEE LEON BOURGEOIS** : **DÉJÀ RATTACHÉS** (via la même
  clé unique `|ALLEE|LEON BOURGEOIS → 1|RUE|BUENOS AYRES` AD4111738).
  Rien à faire.
- **69 QUAI JACQUES CHIRAC** : déjà fusé dans `71 QUAI JACQUES CHIRAC`
  (qui est lui-même hr-active sans copro — `71` documenté comme
  vraie copro non immatriculée dans `audit_orphelines_bdnb_motte.md`,
  même sous l'ancien nom *Branly*). **Catégorie B confirmée**.
- **67B QUAI BRANLY** : BAN ne reconnaît pas `67B` comme housenumber
  → l'adresse réelle est probablement `67 BIS QUAI JACQUES CHIRAC`
  (rebaptisé), à laquelle ne correspond aucune copro RNC à cette
  hauteur du quai (la `AB3789013 "67 Quai Jacques Chirac"` étant à
  400 m). **Catégorie B / hors-DVF immédiat**.

### ÉTAPE 4 — Dry-run hypothétique

| cas | mécanisme | recommandation |
|---|---|---|
| `\|ALLEE\|LEON BOURGEOIS` | — (déjà rattaché) | aucun, conforme |
| `69\|QUAI\|JACQUES CHIRAC` | — (déjà fusé) ; le **71** sous-jacent reste cat. B | aucun |
| `67B QUAI BRANLY` | — (absent light) | aucun |

---

## Synthèse — actions possibles

| groupe | adresses sûres déjà rattachées | candidats SOUS HYPOTHÈSE (à confirmer terrain) | catégorie B confirmée |
|---|---|---|---|
| **G1** | `\|ALLEE\|LEON BOURGEOIS` (6/8) → AD4111738 | **`4\|RUE\|BUENOS AIRES` → `1B\|RUE\|BUENOS AYRES` AF1857283** (si AF1857283 couvre 2A/4) | 2A absente DVF |
| **G2** | `5\|AVENUE\|GENERAL DETRIE` → AD5265665 | **`55\|AVENUE\|SUFFREN` → `5\|AVENUE\|GENERAL DETRIE` AD5265665** + re-point `5\|AVENUE\|GAL DETRIE` (chaîne) — parc −4 prévu | 7 Détrie absent DVF |
| **G3** | (aucune sûre, juste géocolocation) | aucune (RNC ∅ partout) | `2\|RUE\|BUENOS AIRES` |
| **G4** | `\|ALLEE\|LEON BOURGEOIS` (2/4) → AD4111738 ; `69\|QUAI\|J. CHIRAC` → `71` (cat. B sous-jacente) | aucune (`AB3789013 "67 J. Chirac"` à 400 m, bâti distinct) | 67B BRANLY, 71 J. CHIRAC |

### Confirmations terrain nécessaires (Pappers / acte / syndic local)

1. **G1 — AF1857283 "1 bis BUENOS AYRES" couvre-t-elle 2A/4 BUENOS
   AIRES ?** (22 lots ; permettrait `ALIAS_RNC 4|RUE|BUENOS AIRES →
   1B|RUE|BUENOS AYRES`).
2. **G2 — AD5265665 "5 AVENUE DU GENERAL DETRIE" couvre-t-elle
   l'ensemble {5, 7, 55 Suffren} ?** (11 lots, gap +4 vs nb_log_bdnb
   15 sur bgid GQAG — peut-être commerce/annexe hors syndic). Si oui :
   - `ALIAS_RNC += { "55|AVENUE|SUFFREN": "5|AVENUE|GENERAL DETRIE" }`
   - + correctif chirurgical re-pointant `5|AVENUE|GAL DETRIE` (fsrc
     actuel de 55 SUFFREN) vers le même anchor (chaîne, cf. méthode
     `fix_mp_voie_abrev`).

### Fichiers et données **inchangés**

Aucune modification de `secteur_motte_picquet_light.json`,
`make_light_motte_picquet.py`, `.bak` ni cache. Audit purement read-only.

---
*Sources : `data/secteur_motte_picquet_light.json`,
`data/bdnb_motte_picquet.json`, `data/_horsrnc_bdnb_live_motte_picquet.json`,
RNC tabular-api `3ea8e2c3…`, BAN `api-adresse.data.gouv.fr`. Cf.
`data/audit_orphelines_bdnb_motte.md`, `data/audit_lacunes_pipeline.md`,
`scripts/fix_mp_cibles_horsrnc.py` (méthode catégorie B / A1-A3).*
