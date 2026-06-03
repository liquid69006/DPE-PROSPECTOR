# Diag Manche B2a — Application des 3 dispositions ROBUSTES MONTCHAT

> **Phase 5, Manche B2a.** Application des 3 ensembles ROBUSTES de la classif B2
> (indépendants de la jointure MAJIC) : **FUSER**, **BUREAUX**, **MONO via
> nb_log==1**. SOCIAL / MIXTE / COPRO_NON_IMMAT / MONO-1PM / les 76 AMBIGUS sont
> DIFFÉRÉS (après l'infra MAJIC Montchat). **AUCUN commit / git add / push.
> AUCUN POST KV.** DL/MP et `index.html` non touchés. PYTHONUTF8=1, ASCII-safe.
> Date : 2026-06-03. Source : `data/secteur_montchat_light.json` (POST-B1 : 1430
> adr, parc 15848, Σ ventes_logement 932 / total 1217).

---

## DEUX MÉCANISMES

| Ensemble | Mécanisme | Cible |
|---|---|---|
| **FUSER** | **fusion DANS LE LIGHT** (`_fusion_auto`+`_fusion_cible`) — doublons bgid | `secteur_montchat_light.json` |
| **BUREAUX + MONO** | **tags KV `as.type`** | `secteur_assignments:dauphine-lacassagne-montchat` |

---

## ÉTAPE 1 — FUSER : GARDE PARITÉ → **ARRÊT** (33 cross-rue écartés > seuil 15)

### Re-dérivation des 133 FUSER (orange hors-RNC partageant un bgid avec une copro RNC visible)

Le « 133 » du dry-run B2 se décompose ainsi (vérifié sur le light) :

| Sous-ensemble | n | Statut B2a |
|---|--:|---|
| **déjà fusées** (`_fusion_auto`+`_fusion_cible` déjà posés, Manche A) | **80** | **NO-OP** (70 fusées vers un sibling même-bgid ; 10 vers un bgid≠, fusions cross-bgid Manche A, hors B2a) |
| **non-encore-fusées, RETENUES** (garde parité OK) | **20** | applicables |
| **non-encore-fusées, ÉCARTÉES cross-rue** | **33** | différées B2b |
| **TOTAL** | **133** | |

### GARDE PARITÉ / anti-cross-rue (méthode DL/make_light)

Une source n'est fusée que si une copro RNC VISIBLE du **même bgid** est sur la
**même voie ET la même parité** (pair/impair du numéro). Rationale (PIPELINE.md,
passe bgid-orphelin REJETÉE : « 58→69 GRENELLE pair/impair côtés opposés ») : un
bgid partagé entre deux côtés opposés de la rue (ou deux voies) est un artefact
de faux-matching BDNB — `bgid+immat == même bâtiment physique` est FAUX dans ce cas.

### 20 RETENUS (même voie + même parité)

```
17|RUE|HARMONIE          -> 11|RUE|HARMONIE
45|AVENUE|ROCKEFELLER    -> 43|AVENUE|ROCKEFELLER
25|RUE|JULIEN            -> 23|RUE|JULIEN
11|RUE|JULIE             -> 13|RUE|JULIE
203|AVENUE|LACASSAGNE    -> 201|AVENUE|LACASSAGNE
26|COURS|DOCTEUR LONG    -> 28|COURS|DOCTEUR LONG
46|ROUTE|GENAS           -> 44|ROUTE|GENAS
73|COURS|DOCTEUR LONG    -> 71|COURS|DOCTEUR LONG
104B|BOULEVARD|PINEL     -> 44|BOULEVARD|PINEL
13B|RUE|GIRIE            -> 13|RUE|GIRIE
14|RUE|JULES VERNE       -> 6|RUE|JULES VERNE
15B|RUE|FEUILLAT         -> 15|RUE|FEUILLAT
20|RUE|JEANNE D ARC      -> 12|RUE|JEANNE D ARC
21T|RUE|DOCTEUR REBATEL  -> 19|RUE|DOCTEUR REBATEL
2B|RUE|ROUX SOIGNAT      -> 2|RUE|ROUX SOIGNAT
3|IMPASSE|GAZAGNON       -> 11|IMPASSE|GAZAGNON
44B|RUE|ST ISIDORE       -> 44|RUE|ST ISIDORE
7|RUE|STE MARIE          -> 5B|RUE|STE MARIE
70|COURS|DOCTEUR LONG    -> 72|COURS|DOCTEUR LONG
9B|RUE|TRARIEUX          -> 7|RUE|TRARIEUX
```

### 33 ÉCARTÉS CROSS-RUE (différés B2b)

| source | ancre candidate | raison |
|---|---|---|
| 20\|RUE\|BALME | 15\|RUE\|BALME | parité opposée (20 vs 15) |
| 11\|RUE\|GUY | 18\|RUE\|DOCTEUR BONHOMME | voie diff ; parité opposée |
| 7\|RUE\|DOC PAUL DIDAY | 5\|RUE\|DOCTEUR PAUL DIDAY | voie diff (abréviation DOC/DOCTEUR) |
| 154\|AVENUE\|LACASSAGNE | 135\|AVENUE\|LACASSAGNE | parité opposée (154 vs 135) |
| 14\|RUE\|DOCTEUR BONHOMME | 13\|RUE\|DOCTEUR BONHOMME | parité opposée (14 vs 13) |
| 5\|RUE\|LOUIS | 30\|COURS\|RICHARD VITTON | voie diff ; parité opposée |
| 96\|BOULEVARD\|PINEL | 49\|AVENUE\|ESQUIROL | voie diff ; parité opposée |
| 1\|RUE\|CONVENTION | 154\|COURS\|DOCTEUR LONG | voie diff ; parité opposée |
| 1\|RUE\|JEAN MARC BERNARD | 2\|RUE\|JEAN MARC BERNARD | parité opposée (1 vs 2) |
| 1\|RUE\|PROFESSEUR ROCHAIX | 2\|RUE\|PROFESSEUR ROCHAIX | parité opposée (1 vs 2) |
| 11\|RUE\|BARA | 14\|RUE\|BARA | parité opposée (11 vs 14) |
| 11\|RUE\|DOC PAUL DIDAY | 13\|RUE\|DOCTEUR PAUL DIDAY | voie diff (abréviation) |
| 115\|COURS\|ALBERT THOMAS | 114\|COURS\|ALBERT THOMAS | parité opposée (115 vs 114) |
| 14\|RUE\|HARMONIE | 11\|RUE\|HARMONIE | parité opposée (14 vs 11) |
| 14\|RUE\|FIOL | 11\|RUE\|FIOL | parité opposée (14 vs 11) |
| 15\|RUE\|JEANNE D ARC | 12\|RUE\|JEANNE D ARC | parité opposée (15 vs 12) |
| 2\|PLACE\|RECONNAISSANCE | 3\|PLACE\|RECONNAISSANCE | parité opposée (2 vs 3) |
| 2\|RUE\|DOCTEUR REBATEL | 1B\|RUE\|DOCTEUR REBATEL | parité opposée (2 vs 1) |
| 2B\|RUE\|GERMAIN DAVID | 3\|RUE\|GERMAIN DAVID | parité opposée (2 vs 3) |
| 3\|RUE\|BALTHAZAR | 2\|RUE\|BALTHAZAR | parité opposée (3 vs 2) |
| 31T\|RUE\|FEUILLAT | 22\|RUE\|JEANNE D ARC | voie diff ; parité opposée |
| 34\|COURS\|DOCTEUR LONG | 33\|COURS\|DOCTEUR LONG | parité opposée (34 vs 33) |
| 4\|RUE\|DOCTEUR BONHOMME | 5\|RUE\|DOCTEUR BONHOMME | parité opposée (4 vs 5) |
| 42\|COURS\|RICHARD VITTON | 11\|RUE\|CAMILLE | voie diff ; parité opposée |
| 43\|RUE\|GUILLOUD | 34\|RUE\|DOCTEUR REBATEL | voie diff ; parité opposée |
| 44\|RUE\|LOUIS | 45\|RUE\|LOUIS | parité opposée (44 vs 45) |
| 47\|RUE\|PROFESSEUR FLORENCE | 54\|RUE\|PROFESSEUR FLORENCE | parité opposée (47 vs 54) |
| 4T\|RUE\|FEUILLAT | 4\|\|4B R FEUILLAT | voie diff (clé ancre malformée) |
| 5\|RUE\|ST CHARLES | 6\|RUE\|ST CHARLES | parité opposée (5 vs 6) |
| 54\|RUE\|PROFESSEUR ROCHAIX | 53\|RUE\|PROFESSEUR ROCHAIX | parité opposée (54 vs 53) |
| 67\|COURS\|DOCTEUR LONG | 66\|COURS\|DOCTEUR LONG | parité opposée (67 vs 66) |
| 9\|RUE\|EGLISE | 2\|RUE\|STE MARIE | voie diff ; parité opposée |
| 9001\|PLACE\|CHATEAU | 6\|PLACE\|CHATEAU | parité opposée (9001 vs 6) |

### DÉCISION : ARRÊT de l'apply FUSER (conforme spec)

La spec B2a impose : **« Si la garde parité écarte beaucoup (>~15) → ARRÊTE et
documente. »** Ici **33 écartés > 15** → **`fix_fuser_b2a_montchat.py --apply`
n'a PAS été lancé** (le script refuse l'apply tant que cross-rue > 15, sauf
`--force`). **Le light Montchat n'a PAS été modifié** (0 diff git, aucun
`.preb2a.bak`). Les 20 retenus restent à valider par Yann avant fusion.

> **Note d'analyse** : le « 133 » du dry-run B2 surévaluait le FUSER applicable
> car il testait « même bgid » SANS la garde anti-cross-rue. Les 33 écartés sont
> majoritairement des **côtés pair/impair opposés de la même voie** (4 vs 5
> BONHOMME, 34 vs 33 DOCTEUR LONG, 5 vs 6 ST CHARLES, 1 vs 2 ROCHAIX…) — le motif
> exact que la passe bgid-orphelin auto avait été REJETÉE pour (PIPELINE.md §3.1).
> Le robuste réel = **20 retenus** (+ 80 déjà fusées = no-op).

---

## ÉTAPE 2 — BUREAUX (34) + MONO (69) : candidat KV PRÊT (non posté)

### Dérivation (sur les 397 oranges NON-FUSER, bgid ne partageant pas de copro RNC)

- **BUREAUX = 34** : `usage_principal_bdnb` non-résidentiel (Tertiaire). [PREUVE light]
- **MONO = 69** : résidentiel `nb_log_bdnb == 1` (règle Yann : 1 log → mono),
  **hors les 2** que la passe SOCIAL/MIXTE du dry-run interceptait
  (`143|RUE|DAUPHINE` et `147B|AVENUE|LACASSAGNE`, tous deux `vlog=2` → candidats
  rotation/social, MAJIC-dépendants → **DIFFÉRÉS**, pas tagués mono en B2a). Cela
  fixe MONO B2a à **69** exactement (= chiffre dry-run robuste).

### Candidat écrit

`data/_kv_assign_montchat.b2a.candidate.json` =
`{"assignments": {103 clés: {type}}, "fusions": {}, "noms": {}}`
→ **103 entrées** (34 bureaux + 69 mono), format `secteur_assignments`.

### Scripts du rituel ANTI-DRIFT (miroirs DL `_b2_*_dl.py`)

- `scripts/_b2a_backup_diff_montchat.py` — GET prod (gracieux : 404/{} → vide) →
  backup `_kv_assign_montchat.b2a.preaudit.bak` → safety diff (0 conflit
  d'écrasement, 0 retrait, 0 modif hors-B2a) → ré-écrit le candidat **mergé sur
  prod** (merge défensif si KV non-vide).
- `scripts/_b2a_post_montchat.py` — anti-drift `GET prod == backup` → UNIQUE POST
  du candidat → re-GET verify == candidat → miroir `data/_kv_assign_montchat.json`.

### Commande POST pour Yann (PowerShell, JWT requis)

```powershell
. scripts\load_jwt.ps1
python scripts\_b2a_backup_diff_montchat.py    # GET + backup + safety diff, AUCUN POST
# (relire la sortie : "DIFF CONFORME : +103 ajouts, 0 retrait")
python scripts\_b2a_post_montchat.py           # anti-drift -> UNIQUE POST -> verify -> miroir
```

> **JWT absent des shells de l'agent → AUCUN GET/POST effectué ici.** KV Montchat
> attendu NEUF/vide (les scripts gèrent un GET gracieux + merge défensif).

---

## ÉTAPE 3 — VÉRIFS

### Nombre réellement applicable

| Disposition | applicable B2a | note |
|---|--:|---|
| **FUSER** | **0 appliqué** (20 retenus en attente Yann) | apply STOPPÉ : 33 cross-rue > 15 |
| **BUREAUX** (KV) | **34** | candidat prêt |
| **MONO via nb_log==1** (KV) | **69** | candidat prêt |
| **TOTAL préparé** | **103 (KV)** + 20 (FUSER en attente) | |

### Effet orange

- **Tags KV BUREAUX/MONO ne vident PAS le compteur hors-RNC strict** (la ligne
  reste sans immat / hors `coproprietes[]`) — comme noté en B1, le compteur orange
  par la métrique hors-RNC stricte ne bouge qu'à la **fusion** ou via le filtrage
  par type dans le dashboard.
- **FUSER 0 appliqué** → 0 sortie d'orange par fusion en B2a.
- **Orange : 530 → 530** (métrique hors-RNC stricte inchangée tant que FUSER non
  appliqué). L'objectif « 530 → ~294 » du dry-run supposait les 133 FUSER + 103
  tags appliqués ET comptés ; ici **FUSER différé** → la baisse réelle se
  matérialisera quand les 20 FUSER retenus seront posés (orange → ~510) et au
  filtrage type. **Pas de chute en B2a** (aucune écriture light, KV non posté).

### Parc 15848 INCHANGÉ — vérifié

- FUSER **non appliqué** → light intact (0 diff git, aucun `.preb2a.bak`).
- Simulation des 103 tags KV via `_parc_replique_montchat.py(asg=103 tags)` :
  **parc = 15848** (identique au baseline). BUREAUX → 0 log mais étaient déjà
  tertiaire/0-résid ; MONO → 1 log mais étaient déjà `nb_log_bdnb==1` → **net 0**.

| | parc secL |
|---|--:|
| baseline (light POST-B1) | **15848** |
| + 103 tags KV simulés | **15848** |

### Σ ventes 932 INCHANGÉ

Light intact + tags KV ne touchent pas les ventes. Σ nb_ventes_logement = **932**,
Σ nb_ventes_total = **1217** (sur l'ensemble des adresses, inchangé).

### `test_render_secteur.js` — exit 0

| secteur | exit |
|---|--:|
| `dauphine-lacassagne` | **0** |
| `montchat` | **0** |
| `motte-picquet` | **0** |

Lancé depuis `scripts/`. Le test charge ses propres fixtures et valide
`secL == réplique parc` en interne (montchat : `22381 == 22381`, OK). Le light
n'étant pas modifié et les tags KV n'étant pas dans le light, le résultat est
identique au pré-B2a. (Le gotcha « exit 1 / Unexpected token » noté en B1 ne se
reproduit plus — resync index.html intervenue depuis.)

---

## FICHIERS PRODUITS (aucun commité, aucun git add, aucun POST)

- `data/_kv_assign_montchat.b2a.candidate.json` — candidat KV (103 tags)
- `scripts/fix_fuser_b2a_montchat.py` — FUSER (dry-run lancé ; **apply NON lancé**)
- `scripts/_b2a_backup_diff_montchat.py` — rituel GET+backup+diff
- `scripts/_b2a_post_montchat.py` — rituel anti-drift + POST
- `data/diag_mancheB2a_montchat.md` — ce rapport
- **NON produit** : `secteur_montchat_light.json.preb2a.bak` (FUSER non appliqué)

## BLOCAGES / À VALIDER

1. **FUSER STOPPÉ** (33 cross-rue > 15) : les **20 retenus** (liste ci-dessus)
   sont prêts mais en attente de validation Yann. Pour appliquer après validation :
   `python scripts\fix_fuser_b2a_montchat.py --apply --force` (parc-neutre attendu,
   backup `.preb2a.bak`). Les 33 écartés → B2b (jointure parcelle / vérif terrain).
2. **2 MONO différés** (`143 DAUPHINE`, `147B LACASSAGNE`, vlog=2) → relèvent du
   pass SOCIAL/MIXTE MAJIC (Manche ultérieure).
3. **POST KV non effectué** (JWT absent). Commande fournie ci-dessus.
