# Audit « orphelines BDNB » + ventes DVF — secteur La Motte-Picquet

> **Lecture seule.** Aucun fichier de données / cache modifié. Caches RNC live consultés en lecture ; les requêtes manquantes ont été émises en direct (tabular-api RNIC) sans réécrire le cache disque.

## ÉTAPE 1 — Orphelines BDNB strictes (bgid null/vide & ventes-logement > 0)

**Résultat : 0 adresse(s)** dans ce secteur.

Toutes les adresses du `secteur_*_light.json` portent un `batiment_groupe_id` non nul, et chacun de ces bgid existe dans `bdnb_*.json`. **Il n'existe donc aucune orpheline BDNB au sens strict.** Cause structurelle (`make_light.py` l.628-660) : la jointure BDNB applique un fallback à 3 paliers — (1) `numero_immat_principal` via la copro RNC de même clé, (2) `bdnb_par_voie` (numéro+voie), (3) **proximité GPS < 50 m** (`bdnb_proche`). En tissu urbain dense (Lyon 3e / Paris 7e-15e) le palier 3 trouve toujours un bâtiment dans les 50 m : `bb` n'est jamais `None`, l'adresse n'est jamais abandonnée. Le géocodage est lui aussi systématiquement résolu (0 adresse à coordonnées nulles).

→ La notion pertinente n'est donc pas « sans bgid » mais « **sans rattachement BDNB fiable** » : adresses dont le **seul** lien BDNB est le palier le plus faible (`_bdnb_match=='gps'`, proximité aveugle 50 m, sans identité immat ni numéro+voie) **et** ayant des ventes-logement. C'est cette population de fait qui est diagnostiquée ci-dessous (équivalent réel des « orphelines »).

## ÉTAPE 1bis — Population « orphelines de fait » (`_bdnb_match=='gps'` & ventes-logement > 0)

| Indicateur | Valeur |
|---|--:|
| Orphelines de fait (total) | **13** |
| → hors-RNC actives (à diagnostiquer) | **1** |
| → déjà rattachées par fusion BDNB (non orphelines) | 12 |
| Ventes-logement concernées (hors-RNC actives) | 1 |

## ÉTAPE 2 + 3 — Diagnostic ligne par ligne (hors-RNC actives)

### `71|QUAI|JACQUES CHIRAC` — 71 QUAI JACQUES CHIRAC

- **Ventes** : 1 logement / 1 total · **bgid GPS** `bdnb-bg-6SBC-228Y-4AEN` · `nb_log_bdnb`=15 · usage BDNB « Résidentiel collectif »
- **a) Normalisation orthographique** : échec — clé normalisée `(71,JACQUES CHIRAC)` sans correspondance dans `cle_adresse` ni `nom_copropriete`/`adresse`. Raison : la voie normalisée est connue du registre mais aucune copro au n° 71.
- **b) Proximité GPS** : copro la plus proche à **77.4 m** — `3|RUE|BUENOS AYRES` immat `AB3659166` (BUENOS AYRES-3 J Y). 0 copro(s) ≤ 50 m.
  - Aucune copro RNC ≤ 50 m → pas de rattachement GPS possible.
- **c) RNC live (tabular-api, cache, token `JACQUES`, 17 lignes)** : aucune copro à ce (numéro, voie) dans le RNC national → pas d'immatriculation pour cette adresse. Voie renommée : re-sondée sous l'ancien nom « BRANLY » (2 lignes) → toujours aucune copro au n° 71.
- **d) Géocodage BAN** : adresse géocodée (`_coord_source=geocode`), coordonnées présentes (lat=48.857457, lon=2.291383) → ce n'est pas la cause. IRIS `751072807` dans secteur.
- **➡ Catégorie : Copro non immatriculée** — résidentiel collectif 15 lgts BDNB, absent RNC (a/b/c ∅) ; voie renommée — sondée sous « BRANLY » : toujours aucun n°

## ÉTAPE 4 — Bilan chiffré par catégorie

> **Note de classement.** Une copro trouvée *immatriculée* (match orthographique exact sur une `cle_adresse` du snapshot, ou hit RNC live) n'est par définition **pas** « copro non immatriculée » : ces cas ne relèvent d'**aucune** des 5 catégories résiduelles. Ce sont des **rattachables** (lacune de couverture du pipeline : la clé DVF abrège la voie — `CAPT`→`CAPITAINE`, `GAL`→`GENERAL` — donc l'appariement automatique la rate), comptés à part.

| Catégorie | n | ventes-log |
|---|--:|--:|
| Adresse DVF fantôme | 0 | 0 |
| Copro non immatriculée | 1 | 1 |
| Monopropriété | 0 | 0 |
| Hors périmètre | 0 | 0 |
| Inconnu | 0 | 0 |
| _(hors 5 cat.)_ **Rattachable (copro immatriculée — hors 5 cat.)** | **0** | **0** |
| **Total hors-RNC actives** | **1** | **1** |
| _(rappel)_ déjà rattachées par fusion | 12 | 41 |

### Liste complète — orphelines de fait hors-RNC actives

| cle | adr | v_log | v_tot | usage BDNB | nb_log_bdnb | a | b≤50m | c (RNC live) | catégorie | statut |
|---|---|--:|--:|---|--:|:-:|:-:|---|---|---|
| `71\|QUAI\|JACQUES CHIRAC` | 71 QUAI JACQUES CHIRAC | 1 | 1 | Résidentiel collectif | 15 | non | 0 | ∅ | Copro non immatriculée | résidentiel collectif 15 lgts BDNB, absent RNC (a/b/c ∅) ; voie renommée — sondée sous « BRANLY » : toujours aucun n° |

### Liste — orphelines de fait DÉJÀ rattachées (fusion BDNB même bgid ; non orphelines au sens métier)

| cle | adr | v_log | v_tot | usage BDNB | bgid | ancre de fusion |
|---|---|--:|--:|---|---|---|
| `34\|RUE\|MIOLLIS` | 34 RUE MIOLLIS | 8 | 9 | Résidentiel collectif | `bdnb-bg-KKXK-HUWE-NMFU` | `16\|BOULEVARD\|GARIBALDI` |
| `36\|RUE\|MIOLLIS` | 36 RUE MIOLLIS | 6 | 52 | Résidentiel collectif | `bdnb-bg-KKXK-HUWE-NMFU` | `16\|BOULEVARD\|GARIBALDI` |
| `3\|AVENUE\|CHAMPAUBERT` | 3 AVENUE DE CHAMPAUBERT | 6 | 6 | Résidentiel collectif | `bdnb-bg-UHLY-6XC7-PRSL` | `80\|AVENUE\|SUFFREN` |
| `5\|RUE\|GAL LAMBERT` | 5 RUE DU GAL LAMBERT | 5 | 5 | Résidentiel collectif | `bdnb-bg-JXQ1-42AR-2CFG` | `5\|RUE\|GENERAL LAMBERT` |
| `3\|RUE\|GAL DE CASTELNAU` | 3 RUE DU GAL DE CASTELNAU | 3 | 5 | Résidentiel collectif | `bdnb-bg-WHG8-Q9AN-QR6C` | `4\|RUE\|GENERAL DE CASTELNAU` |
| `6\|AVENUE\|GAL DETRIE` | 6 AVENUE DU GAL DETRIE | 3 | 5 | Résidentiel collectif | `bdnb-bg-51P3-7MJW-1MYH` | `38\|AVENUE\|CHARLES FLOQUET` |
| `9\|RUE\|GAL DE LARMINAT` | 9 RUE DU GAL DE LARMINAT | 3 | 3 | Résidentiel collectif | `bdnb-bg-YUBA-32JB-Q8QC` | `9\|RUE\|GENERAL DE LARMINAT` |
| `2\|RUE\|GAL DE LARMINAT` | 2 RUE DU GAL DE LARMINAT | 2 | 5 | Résidentiel collectif | `bdnb-bg-AS4L-LFNK-ANXJ` | `4\|RUE\|GENERAL DE LARMINAT` |
| `32\|RUE\|MIOLLIS` | 32 RUE MIOLLIS | 2 | 3 | Tertiaire | `bdnb-bg-LJRN-ABEM-2VT5` | `16\|BOULEVARD\|GARIBALDI` |
| `\|ALLEE\|LEON BOURGEOIS` |  | 1 | 1 | Résidentiel collectif | `bdnb-bg-M3B8-DJ7V-TCKJ` | `1\|RUE\|BUENOS AYRES` |
| `5\|RUE\|GAL DE LARMINAT` |  | 1 | 1 | Résidentiel collectif | `bdnb-bg-J3YX-LKL5-U98B` | `3\|RUE\|GAL DE LARMINAT` |
| `6\|RUE\|GAL DE LARMINAT` | 6 RUE DU GAL DE LARMINAT | 1 | 1 | Tertiaire | `bdnb-bg-PHBC-JCMV-7GBR` | `6\|RUE\|GENERAL DE LARMINAT` |

---
*Diagnostic lecture seule `scripts/diag_orphelines_bdnb.py` — n'écrit que ce rapport.*