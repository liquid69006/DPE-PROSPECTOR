# Vérification RNC → BDNB — API live vs snapshot (lecture seule)

API ouverte `api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc` (sans clé),
table de relation `numero_immat` ↔ `batiment_groupe_id`. 553 copros du
secteur vérifiées contre `data/bdnb_dauphine_lacassagne.json`.

## ⚠️ Correction d'interprétation

Le comparatif brut `rel` vs snapshot trouve **20 copros / 23 `batiment_groupe_id`
« only_live »**. Une première lecture (« le snapshot a omis 23 bâtiments,
~1276 lgts ») est **fausse et surévaluée** : la relation RNC↔bâtiment est
*many-to-many*, alors que le snapshot projette **un seul**
`numero_immat_principal` par bâtiment. Quand un même bâtiment physique
porte deux immatriculations RNC (ex. « LE PAVILLON DE FLORE » et
« …FLORE II », ou un SDC + son syndicat secondaire), le snapshot le
range sous l'une, et la liste secteur contient parfois l'autre. Le
bâtiment **est déjà présent et déjà compté** sous l'immat jumelle.

Re-caractérisation locale (snapshot + sidecar) des 23 bgid :

| Catégorie | Bgid | Réalité |
|---|--:|---|
| Déjà dans le snapshot **et déjà visibles** au dashboard | **17** | bâtiment partagé par 2 immats RNC — logements **déjà comptés** sous la copro jumelle. Forcer le lien **double-compterait** (le dedup `bgValue` somme les lots RNC par bâtiment). |
| Dans le snapshot mais invisibles | 2 | `202 AVENUE FELIX FAURE` (17 lgts), `254 RUE PAUL BERT` bgid `5S72` (7 lgts) — petits. |
| **Absents du snapshot — HORS SECTEUR** | 4 | `PARC MISTRAL` → 62 Av. Marc Sangnier **69100 Villeurbanne** + 1 enregistrement vide ; `1 place des maison neuves` → 1 Place des Tapis **69004 Lyon 4e** (×2). À **ne pas** injecter dans un jeu Lyon 3e. |

**Conclusion : le snapshot n'est pas matériellement incomplet.** Bilan
directionnel inchangé et confirmé : **0 bâtiment du snapshot absent du
live** (le snapshot n'est jamais faux). Aucun re-fetch / injection à
faire. Résidu réel mineur : 2 petits bâtiments invisibles (~24 lgts) +
un motif « immatriculation satellite » (copros « X II » jumelles d'un
bâtiment déjà compté) — annotation produit éventuelle, pas un bug de
complétude.

## Bilan brut (niveau relation, à lire avec la correction ci-dessus)

| Indicateur | Valeur |
|---|--:|
| Copros vérifiées | 553 |
| Copros `rel` live ≠ snapshot (par `numero_immat_principal`) | 20 |
| Bâtiments du snapshot absents du live | **0** |
| dont réellement absents du snapshot ET dans le secteur | **0** |
| dont absents du snapshot mais hors secteur / vides | 4 |
| dont déjà dans le snapshot (autre immat du même bâti) | 19 |

Détail nominatif des 23 bgid : voir la sortie de
`python scripts/verif_rnc_bdnb_live.py` (sidecar
`data/_rnc_bdnb_live_missing.json`) recroisée au snapshot.
