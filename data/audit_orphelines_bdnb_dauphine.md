# Audit « orphelines BDNB » + ventes DVF — secteur Dauphiné-Lacassagne

> **Lecture seule.** Aucun fichier de données / cache modifié. Caches RNC live consultés en lecture ; les requêtes manquantes ont été émises en direct (tabular-api RNIC) sans réécrire le cache disque.

## ÉTAPE 1 — Orphelines BDNB strictes (bgid null/vide & ventes-logement > 0)

**Résultat : 0 adresse(s)** dans ce secteur.

Toutes les adresses du `secteur_*_light.json` portent un `batiment_groupe_id` non nul, et chacun de ces bgid existe dans `bdnb_*.json`. **Il n'existe donc aucune orpheline BDNB au sens strict.** Cause structurelle (`make_light.py` l.628-660) : la jointure BDNB applique un fallback à 3 paliers — (1) `numero_immat_principal` via la copro RNC de même clé, (2) `bdnb_par_voie` (numéro+voie), (3) **proximité GPS < 50 m** (`bdnb_proche`). En tissu urbain dense (Lyon 3e / Paris 7e-15e) le palier 3 trouve toujours un bâtiment dans les 50 m : `bb` n'est jamais `None`, l'adresse n'est jamais abandonnée. Le géocodage est lui aussi systématiquement résolu (0 adresse à coordonnées nulles).

→ La notion pertinente n'est donc pas « sans bgid » mais « **sans rattachement BDNB fiable** » : adresses dont le **seul** lien BDNB est le palier le plus faible (`_bdnb_match=='gps'`, proximité aveugle 50 m, sans identité immat ni numéro+voie) **et** ayant des ventes-logement. C'est cette population de fait qui est diagnostiquée ci-dessous (équivalent réel des « orphelines »).

## ÉTAPE 1bis — Population « orphelines de fait » (`_bdnb_match=='gps'` & ventes-logement > 0)

| Indicateur | Valeur |
|---|--:|
| Orphelines de fait (total) | **2** |
| → hors-RNC actives (à diagnostiquer) | **1** |
| → déjà rattachées par fusion BDNB (non orphelines) | 1 |
| Ventes-logement concernées (hors-RNC actives) | 4 |

## ÉTAPE 2 + 3 — Diagnostic ligne par ligne (hors-RNC actives)

### `71|RUE|PAUL BERT` — 71 RUE PAUL BERT

- **Ventes** : 4 logement / 4 total · **bgid GPS** `bdnb-bg-WPVN-TN1Z-KE2S` · `nb_log_bdnb`=None · usage BDNB « Secondaire »
- **a) Normalisation orthographique** : échec — clé normalisée `(71,PAUL BERT)` sans correspondance dans `cle_adresse` ni `nom_copropriete`/`adresse`. Raison : la voie normalisée est connue du registre mais aucune copro au n° 71.
- **b) Proximité GPS** : aucune copro RNC géolocalisée à proximité (≤ 80 m).
- **c) RNC live (tabular-api, cache, token `PAUL`, 92 lignes)** : aucune copro à ce (numéro, voie) dans le RNC national → pas d'immatriculation pour cette adresse.
- **d) Géocodage BAN** : adresse géocodée (`_coord_source=geocode`), coordonnées présentes (lat=45.75651, lon=4.861099) → ce n'est pas la cause. IRIS `693830501` dans secteur.
- **➡ Catégorie : Monopropriété** — usage BDNB « Secondaire » (non-copro) ; aucune copro RNC au n° (a/b/c ∅)

## ÉTAPE 4 — Bilan chiffré par catégorie

> **Note de classement.** Une copro trouvée *immatriculée* (match orthographique exact sur une `cle_adresse` du snapshot, ou hit RNC live) n'est par définition **pas** « copro non immatriculée » : ces cas ne relèvent d'**aucune** des 5 catégories résiduelles. Ce sont des **rattachables** (lacune de couverture du pipeline : la clé DVF abrège la voie — `CAPT`→`CAPITAINE`, `GAL`→`GENERAL` — donc l'appariement automatique la rate), comptés à part.

| Catégorie | n | ventes-log |
|---|--:|--:|
| Adresse DVF fantôme | 0 | 0 |
| Copro non immatriculée | 0 | 0 |
| Monopropriété | 1 | 4 |
| Hors périmètre | 0 | 0 |
| Inconnu | 0 | 0 |
| _(hors 5 cat.)_ **Rattachable (copro immatriculée — hors 5 cat.)** | **0** | **0** |
| **Total hors-RNC actives** | **1** | **4** |
| _(rappel)_ déjà rattachées par fusion | 1 | 2 |

### Liste complète — orphelines de fait hors-RNC actives

| cle | adr | v_log | v_tot | usage BDNB | nb_log_bdnb | a | b≤50m | c (RNC live) | catégorie | statut |
|---|---|--:|--:|---|--:|:-:|:-:|---|---|---|
| `71\|RUE\|PAUL BERT` | 71 RUE PAUL BERT | 4 | 4 | Secondaire | None | non | 0 | ∅ | Monopropriété | usage BDNB « Secondaire » (non-copro) ; aucune copro RNC au n° (a/b/c ∅) |

### Liste — orphelines de fait DÉJÀ rattachées (fusion BDNB même bgid ; non orphelines au sens métier)

| cle | adr | v_log | v_tot | usage BDNB | bgid | ancre de fusion |
|---|---|--:|--:|---|---|---|
| `51\|RUE\|PROFESSEUR PAUL SISLEY` | 51 RUE PROFESSEUR PAUL SISLEY | 2 | 2 | Résidentiel collectif | `bdnb-bg-QP8Z-VMM2-M7MW` | `77\|COURS\|ALBERT THOMAS` |

---
*Diagnostic lecture seule `scripts/diag_orphelines_bdnb.py` — n'écrit que ce rapport.*