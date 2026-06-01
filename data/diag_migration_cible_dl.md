# Diag — Migration `cible_0vente_*` → `as.cible` (secteur Dauphiné-Lacassagne)

> Tâche **READ-ONLY**. Aucune modif data/code, aucun commit. Seul fichier
> écrit = ce rapport. Cadrage de la migration du signal commercial
> `cible_0vente` (rangé à tort dans `as.type`) vers un champ séparé
> `as.cible`, pour libérer `as.type` au seul **type bâti**.
> (Réf. CLAUDE.md §8 + PIPELINE.md root §10 / roadmap §11.4.)

Sources lues : `data/_kv_assign_dl.json` (clé `assignments`),
`data/secteur_dauphine_lacassagne_light.json` (`adresses[]` +
`coproprietes[]`), `index.html` (renderSecteur / sctGen),
`PIPELINE.md` (root + data/), `JOURNAL.md`.

---

## E1 — Inventaire KV

`data/_kv_assign_dl.json.assignments` : **643 entrées** au total.
Répartition par `type` :

| `type` | n |
|---|---|
| `social` | 213 |
| `bureaux` | 122 |
| `mono` | 106 |
| `copro_non_immat` | 85 |
| **`cible_0vente_active`** | **54** |
| `mixte` | 43 |
| **`cible_0vente_isolee`** | **16** |
| `null` (objet sans `type`) | 4 |

**Total `cible_0vente_*` = 70** (54 `active` + 16 `isolee`). Conforme
au compte attendu (~70 ; 121 → 70 après les 51 reclassées en manches
F/G, cf. PIPELINE §7.1 / JOURNAL). Seules ces 2 valeurs `cible_0vente_*`
existent (pas de 3e variante).

### Structure d'un objet assignment `cible_0vente_*`

Clés observées sur l'ensemble des 70 entrées (preuve, dump KV) :

| clé | présence (sur 70) | rôle |
|---|---|---|
| `type` | 70/70 | = la valeur `cible_0vente_active` / `cible_0vente_isolee` |
| `_qualif_source` | 3/70 | métadonnée de traçabilité (ex. `ultime_scan_certif`) |
| `_qualif_date` | 3/70 | horodatage qualif |
| `_qualif_note` | 2/70 | note libre terrain |

- **`ilot` : 0/70** — aucune cible ne porte d'îlot manuel dans son
  assignment (l'îlot vient du light `a._ilot`).
- **`cible` : 0/70** — le champ cible n'existe **pas encore**.

Exemples (dump exact) :
```
"37B|RUE|DAUPHINE"   => {"type":"cible_0vente_active"}
"141|RUE|DAUPHINE"   => {"type":"cible_0vente_active","_qualif_source":"ultime_scan_certif",
                          "_qualif_date":"2026-05-28T06:28:38Z",
                          "_qualif_note":"retrait tag 'mixte' fantome sans qualif_source pre-existant"}
"227|AVENUE|FELIX FAURE" => {"type":"cible_0vente_active","_qualif_source":"ultime_scan_certif",
                          "_qualif_date":"...","_qualif_note":"ASSO DE L'HOTEL SOCIAL = asso privee (NI mono NI social)"}
```

(À titre de comparaison, les entrées « normales » sont aussi
type-only : `{"type":"social"}`, `{"type":"bureaux"}`, etc. Seules 5
entrées du KV entier portent un `ilot`, et 25 portent des champs de
diagnostic `_social_pct_corrige` / `_mut_apt_per_year` / `_previous_tag`.)

### Conclusion E1

Pour les 70 cibles, **`type` = le signal commercial, et RIEN d'autre**.
Aucun champ ne stocke le vrai type bâti dans l'objet assignment. Le vrai
type bâti **n'est PAS récupérable depuis le KV** : il est totalement
masqué par le signal. **MAIS** il reste reconstructible depuis le LIGHT
(immat RNC / BDNB) — voir E3 (c'est là que la migration récupère le vrai
type).

---

## E2 — Points de lecture front (`index.html`)

Fait notable : **la chaîne `cible_0vente` n'apparaît NULLE PART dans
`index.html`** (grep = 0 hit). Le front ne connaît pas cette valeur. Donc
aujourd'hui, partout où il teste `as.type`, une cible_0vente :
- **ne matche aucun `TYPE_LABELS`** (l.2519) → la 1re branche du badge
  (l.5195) est **sautée** ;
- **n'est ni `social` ni `bureaux`** → elle n'est **jamais exclue** du
  marché libre (`_mlExcl` l.5119, `tg` l.2730) ;
- **n'est pas un type valide de `TYPE_OPTS`** → si on ouvre le menu
  requalif, la valeur courante n'est pas pré-sélectionnée.

Comme **68/70 cibles portent un `numero_immatriculation`** (cf. E3),
elles tombent dans la branche `else if (rnc || a.numero_immatriculation)`
(l.5209) et s'affichent avec le **badge implicite « Copropriété »**. Le
tag `cible_0vente` est donc **totalement invisible à l'écran
aujourd'hui** (pour 68/70 ; les 2 hors-RNC tombent dans le `else`
dropdown « — type — »).

### Tableau des points

| Ligne | Rôle | Lecture **actuelle** | Lecture **après migration** |
|---|---|---|---|
| 2514-2517 `TYPE_OPTS` | options du menu requalif | n'inclut pas `cible_0vente` (jamais sélectionnable) | inchangé (le menu reste **type bâti pur**) ; le signal cible se pose ailleurs |
| 2519-2521 `TYPE_LABELS` | libellé court du badge | `cible_0vente_*` absent → label undefined → branche sautée | inchangé (type bâti) ; **ajouter** un marqueur cible séparé (badge 🎯) lu sur `as.cible` |
| 2523-2525 `TYPE_BADGE_COLORS` | couleur badge (seul `mixte` custom) | — | option : couleur dédiée pour le marqueur cible |
| 2557-2566 `secteurSetAssign(key, field, val)` | écriture KV générique (`type`/`ilot`) | sait écrire n'importe quel `field` | sait déjà écrire `field='cible'` (générique). **Ne JAMAIS** y reposer `type=cible_0vente_*` |
| **2728-2735** `sctGenComputeIlots` (`tg`) | exclusion ventes social/bureaux de la répartition | `tg !== 'social' && tg !== 'bureaux'` → **cible INCLUSE** | inchangé : `as.type` redevient le vrai type (copro / copro_non_immat) → reste non-social/bureaux → **INCLUSE** (calcul identique) |
| 4830-4831 `coproByCle` | index copro par `cle_adresse` | — | inchangé |
| 4903-4905 / 4916 `ilotEffectif` | îlot effectif (KV `as.ilot` puis `a._ilot`) | ne lit pas `type` | inchangé |
| **5024-5036** filtre **Catégorie** (`secteurCategoriesSelected`) | passe/bloque l'adresse selon la catégorie cochée | `t = as.type` ; cible → matche `copro_rnc` (via `isRnc`, l.5026) pour 68/70 ; preset `a_qualifier` = `!t && !isRnc` → **cible exclue** du « à qualifier » | `as.type` redevient le vrai type → matche `copro_rnc`/`copro_non_immat` correctement. **Ajouter** un filtre « 🎯 Cible 0-vente » lisant `as.cible` |
| **5119** `_mlExcl` (strict / marché libre, renderSecteur) | exclure social/bureaux du strict | `as.type === 'social' || as.type === 'bureaux'` → **cible NON exclue (incluse)** | inchangé : type restitué (copro/copro_non_immat) reste non-social/bureaux → **toujours incluse** (calcul identique). 0 vente strict de toute façon (E3) |
| 5195-5208 badge type (`TYPE_LABELS[as.type]`) | badge coloré + crayon ✏️ | cible → label undefined → **branche sautée** | `as.type` redevient vrai type → badge correct (Copro non immat. / etc.) |
| 5209-5224 badge implicite « Copropriété » | RNC/immat sans tag → badge sobre | 68/70 cibles affichent **« Copropriété »** ici (signal cible invisible) | idem (vrai type = copro RNC). **Superposer** un petit badge 🎯 si `as.cible` posé |
| 5225-5233 dropdown « — type — » | si ni tag ni RNC | 2/70 cibles hors-RNC tombent ici | après migration : 1 → `copro_non_immat` (badge), 1 → reste « — type — » (indéterminé) |
| 5302-5336 cellule **logements** | RNC→lots ; mono→1 ; social/bureaux→0 ; sinon nb_log_bdnb | cible non-mono/social/bureaux → affiche lots RNC (68) ou nb_log_bdnb (1) ou — (1) | inchangé (type restitué reste hors mono/social/bureaux) |
| 5323 `TYPE_LABELS[as.type]` (cellule log) | libellé social/bureaux | non atteint par cible | inchangé |
| 5540-5552 `secteurEditType` | ouvre le dropdown requalif `TYPE_OPTS` | `cur = as.type` (cible → non pré-sélectionnée car hors `TYPE_OPTS`) | `cur = as.type` = vrai type → pré-sélectionné correctement |

### Confirmations demandées (E2)

- **`_mlExcl` (l.5119) ne teste QUE `social`/`bureaux`** — confirmé par
  lecture. `cible_0vente_*` **n'y entre PAS** → une cible est aujourd'hui
  **INCLUSE dans le marché libre**. Après migration, son `as.type`
  devient son vrai type (copro / copro_non_immat), qui **reste
  non-social/bureaux** → l'inclusion ne change pas → **calcul strict
  identique**.
- **`sctGen` (l.2730) idem** : `tg !== 'social' && tg !== 'bureaux'` ne
  mentionne pas `cible_0vente` → cible **incluse** dans la répartition ;
  après migration, vrai type non-social/bureaux → **incluse à
  l'identique**.
- **Toute écriture KV** (`secteurSetAssign`) qui poserait
  `type=cible_0vente_*` : **aucune** dans le front actuel (le front ne
  connaît pas la valeur — les tags ont été posés par scripts pipeline /
  manches, pas par le dashboard). À NE PAS introduire : le signal cible
  doit s'écrire sur `field='cible'`.

---

## E3 — Que met-on dans `as.type` après ?

Cross-check **light × KV** (programme local, supprimé après usage) sur
les 70 cibles. `coproByCle` reconstruit comme le front
(`coproprietes[]` keyé par `cle_adresse`, 554 entrées) ; `isRnc =
coproByCle[cle] || a.numero_immatriculation`.

### Vrai type bâti détectable

| Vrai type restitué | n | levier (preuve) |
|---|---|---|
| **copro RNC** (`copro`) | **68** | `cle` ∈ `coproByCle` **ET** `numero_immatriculation` présent sur l'adresse light. Aujourd'hui déjà affichées « Copropriété » (badge implicite l.5209) |
| **copro_non_immat** | **1** | `11B|RUE|ST MAXIMIN` : pas d'immat, `nb_log_bdnb=41`, `usage_principal_bdnb=Résidentiel collectif` → levier BDNB (`nb_log>1` + pas d'immat) = copro_non_immat par définition (PIPELINE §10) |
| **indéterminé** (`non_qualifie`/null) | **1** | `37B|RUE|DAUPHINE` : pas d'immat, `nb_log_bdnb=None`, pas d'usage BDNB, 0 vente, bgid `7ZB9…` — façade B (suffixe), probable FA-source. Aucun levier → reste indéterminé |

**Estimation chiffrée : 69/70 ont un vrai type déterminable**
(68 copro RNC + 1 copro_non_immat). **1/70 reste indéterminé**
(`37B DAUPHINE` → `non_qualifie` ou null). social / mono / mixte /
bureaux détectables = **0** parmi les cibles.

> Note : 68/70 = copro RNC est cohérent. Un `cible_0vente` est par
> définition une adresse SANS mutation récente (0 vente) ; ces grandes
> copros immatriculées « dormantes » sont exactement la cible
> commerciale (gros parc, aucune rotation = vivier de mandats).

### Confirmation « 0 vente »

- **`nb_ventes_logement = 0` pour les 70/70** — confirmé (aucune
  exception). C'est la définition même du signal 0-vente.
- **9/70 ont `nb_ventes_total > 0`** (ventes **non-logement** :
  commerces / parkings / dépendances) :
  `7 FRANCOIS GILLET` (11), `19 MONTBRILLANT` (2), `280 LAFAYETTE` (2),
  `11B ST MAXIMIN` (2), `16 DAUPHINE` (1), `17 DAVID` (1), `24 TURBIL`
  (1), `243 PAUL BERT` (1), `30 DAUPHINE` (1). **Ce ne sont PAS des
  incohérences** : le signal est « 0 vente **logement** » ; ces ventes
  sont hors-habitation.

**Impact strict = NUL** : en mode strict, `vpaOf(a)` retourne
`ventes_par_an_logement` (l.4838), qui est **tout-zéro pour les 70**
(`effTot=0`). Donc, quel que soit le type restitué (même s'il était
social/bureaux qui exclurait), la contribution au marché libre strict
est **0 → 0**. Les 9 ventes `total>0` ne pèsent que sur le **brut**, où
**aucune exclusion n'existe** (`_mlExcl` toujours false en brut) — donc
indépendant du type aussi.

### Conclusion E3

**69/70 type-déterminable** (68 copro + 1 copro_non_immat) ; **1
indéterminé** (`37B DAUPHINE`). **0-vente logement confirmé sur les 70**
→ impact strict / répartition îlot **nul** quel que soit le type
restitué.

---

## E4 — Plan (esquisse, non exécuté)

### (a) Migration KV

Pour chaque entrée `cible_0vente_*` :
1. Déplacer le signal de `as.type` → **`as.cible`**.
2. Remplir `as.type` avec le vrai type bâti (E3) :
   - 68 → `copro` *(ou laisser **null** : ces adresses sont déjà
     reconnues copro RNC via `coproByCle`/immat et affichent le badge
     implicite « Copropriété ». Poser `type='copro'` est redondant — à
     trancher : null = on s'appuie sur l'implicite ; `copro` = explicite.
     Recommandation : **laisser null**, l'implicite suffit et évite
     d'ajouter une valeur `copro` à `TYPE_OPTS`)*.
   - 1 (`11B ST MAXIMIN`) → `copro_non_immat`.
   - 1 (`37B DAUPHINE`) → **null / `non_qualifie`** (indéterminé).

**Format `as.cible`** (à valider Yann) — deux options :
- **A. enum string** : `as.cible = 'active' | 'isolee'` (conserve la
  distinction active/isolée des 54/16). **Recommandé** (préserve
  l'information, symétrique au schéma actuel).
- B. booléen : `as.cible = true` (perd active vs isolée).
→ **Option A** recommandée.

**Mécanique (rituel anti-drift OBLIGATOIRE, CLAUDE.md §6 + PIPELINE
§8.1)** : pattern « manche » 2 scripts.
- `_<manche>_backup_diff_dl.py` : **GET prod** `/secteur-assignments/
  dauphine-lacassagne`, **compare au miroir** `data/_kv_assign_dl.json`
  (ABORT si `prod ≠ backup`), produit le candidat (déplacement
  `type→cible` + pose du vrai `type`).
- `_<manche>_post_dl.py` : **1 seul POST**, re-GET de vérif, MAJ miroir.
- JWT via `load_jwt.ps1` (session PowerShell directe, pas le `!`).
- Préserver les `_qualif_*` existants (3/70) sur l'objet migré.

### (b) Adaptation front (`index.html`)

| Fichier/fonction | Nature du changement |
|---|---|
| `TYPE_OPTS` / `TYPE_LABELS` (2514-2521) | inchangés si on laisse `type=null` pour les copro RNC. Sinon ajouter `['copro','Copropriété']` |
| badge l.5195-5224 | **superposer** un petit marqueur 🎯 « cible 0-vente » lu sur `as.cible` (à côté du badge type ou implicite « Copropriété »). Optionnel : tooltip `active`/`isolee` |
| `TYPE_BADGE_COLORS` (2523) | option : style dédié au marqueur cible |
| filtre Catégorie l.5024-5036 | **ajouter** une catégorie/checkbox « 🎯 Cible 0-vente » testant `as.cible` (filtre orthogonal au type). Le preset `a_qualifier` redevient correct mécaniquement (les ex-cibles ont un vrai type ou null) |
| `secteurEditType` (5540) / menu requalif | inchangé : opère sur `as.type` (type bâti). Le signal cible n'est plus touché par ce menu |
| `_mlExcl` (5119) / `sctGen` `tg` (2730) | **inchangés** : tests social/bureaux seulement ; vrai type restitué reste non-social/bureaux |
| `secteurSetAssign` (2557) | déjà générique (`field`) ; aucun changement structurel (sait écrire `field='cible'`). Éventuel point d'écriture UI pour (dé)taguer une cible |

### (c) Neutralité (chiffres)

- **Marché libre strict = 578,4/an : INCHANGÉ.** Les 70 cibles ont
  `ventes_par_an_logement` tout-zéro → `effTot=0` en strict → 0
  contribution avant comme après, quel que soit `as.type`.
- **Parc `secL` / `iloL` : INCHANGÉ.** Le parc (dédup `bg:bgid`,
  l.5152-5173) lit `as.type` **uniquement** via `getEffectiveLog` (mono
  → 1) et le guard social/bureaux. Aucune cible ne devient
  mono/social/bureaux : 68 restent copro RNC (lots RNC, déjà comptés
  via `coproByCle`), 1 reste copro_non_immat (nb_log_bdnb=41 inchangé),
  1 reste sans contribution (37B : ni bgValue ni nb_log). → **parc
  strictement neutre**.
- **Répartition `sctGen` : INCHANGÉE.** `byIlot[*].nb_ventes` somme
  `sumVpa(a)` (logement en strict, tout-zéro) ; l'exclusion `tg`
  social/bureaux ne capte aucune cible avant ni après.

### Ordre des opérations

1. **(read-only)** Geler la liste des 70 cibles + leur vrai type (E3)
   dans un side-file scratch (`_manche_*_candidate.json`, gitignoré).
2. **Migration KV** : rituel 2-scripts (anti-drift GET==backup → 1 POST
   → re-GET → MAJ miroir). Pose `as.cible` + vrai `as.type`. Commit data.
3. **Front** : ajouter marqueur 🎯 + filtre « Cible 0-vente » (lecture
   `as.cible`), laisser `_mlExcl`/`sctGen`/menu requalif intacts. Resync
   des plages de `test_render_secteur.js` si renderSecteur édité
   (gotcha connu). Commit UI.
4. **Preuve de neutralité** : `node scripts/test_render_secteur.js`
   (exit 0, `secL` inchangé) + vérifier header strict = 578,4/an.

**Nb d'entrées concernées : 70.** Fichiers/fonctions touchés :
`data/_kv_assign_dl.json` (KV) ; `index.html` (badge ~5195-5224,
filtre Catégorie ~5024-5036, éventuel `TYPE_OPTS`/`TYPE_LABELS`) ;
scripts manche `_manche_*_dl.py`.

---

## Conclusion

**(a) Périmètre exact** : **70** entrées `cible_0vente_*` (54 `active` +
16 `isolee`). Type bâti **déterminable pour 69** (68 copro RNC + 1
copro_non_immat) ; **1 indéterminé** (`37B|RUE|DAUPHINE`).

**(b) Plan ordonné** : (1) figer liste + vrai type (read-only) → (2)
migration KV rituel anti-drift 2-scripts (`type→cible` + pose vrai
`type`) → (3) front : marqueur 🎯 + filtre « cible 0-vente » sur
`as.cible`, `_mlExcl`/`sctGen`/requalif **inchangés** → (4) preuve
neutralité (`test_render` exit 0, strict 578,4/an, parc inchangé).

**(c) Question clé — a-t-on un vrai type à restituer ?** **OUI pour
69/70.**
- **68** = copro RNC (**preuve** : `cle ∈ coproByCle` ET
  `numero_immatriculation` présent dans le light ; déjà affichées
  implicitement « Copropriété »). → `as.type` = `copro` **ou null**
  (l'implicite RNC suffit).
- **1** = `copro_non_immat` (**preuve** : `11B ST MAXIMIN`, levier BDNB
  `nb_log_bdnb=41` + Résidentiel collectif + pas d'immat).
- **1 indéterminé** (**preuve** : `37B DAUPHINE`, aucun levier — pas
  d'immat, `nb_log_bdnb=None`, pas d'usage BDNB) → `as.type` =
  `non_qualifie`/null.

→ La migration laisse **au plus 1 entrée type-indéterminée**. Le signal
commercial part proprement vers `as.cible`, et `as.type` redevient le
type bâti pur sans perte (sauf le 1 cas structurellement indéterminé).

**Distinction preuve vs déduction** :
- **Preuve (KV/code/light lus)** : compte 70 (54/16) ; structure
  type-only (cible/ilot absents) ; `index.html` ne connaît pas
  `cible_0vente` (0 grep) ; `_mlExcl`/`sctGen` testent uniquement
  social/bureaux ; 70/70 `nb_ventes_logement=0` ; 68/70 immat+coproByCle ;
  `vpaOf` strict = `ventes_par_an_logement`.
- **Déduction** : `37B DAUPHINE` = FA-source/façade B (inféré du suffixe
  `B` + bgid + 0 donnée) — à confirmer terrain ; choix `type=copro` vs
  `null` pour les 68 = décision de design (recommandé null).
- **À trancher Yann** : format `as.cible` (enum `active`/`isolee`
  recommandé vs booléen) ; pose explicite `type=copro` ou null pour les
  68 RNC.

*Aucune modification effectuée hors ce rapport. Aucun commit.*
