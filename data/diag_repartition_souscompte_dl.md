# Diagnostic — sous-compte de la répartition sctGen (secteur Dauphiné-Lacassagne)

> READ-ONLY. Date : 2026-05-31. Aucune donnée/code modifié.
> Source données : `data/secteur_dauphine_lacassagne_light.json`
> Source état KV courant : `data/_kv_assign_dl.json` (clé `assignments`)
> Source logique répartition : `index.html` (module `sctGen`)

---

## ETAPE 1 — Référence (somme sur TOUTES les adresses)

Calcul direct sur `data/secteur_dauphine_lacassagne_light.json`, champs absents/None traités comme 0 (aucun champ manquant constaté) :

| Mesure | Total 5 ans | / 5 (moyenne/an) | Attendu |
|---|---|---|---|
| **brut** = Σ `nb_ventes_total` | 4508 | **901.6** | ~893.2 |
| **strict** = Σ `nb_ventes_logement` | 2998 | **599.6** | ~597.8 |

**Les deux ne tombent pas exactement** sur les valeurs attendues (901.6 vs 893.2 ; 599.6 vs 597.8). Écart strict = +1.8/an. Le fichier light a vraisemblablement évolué (correctifs terrain) depuis la dernière mesure de référence. **Valeurs exactes calculées ici : brut/5 = 901.6 ; strict/5 = 599.6.**

Comptes :
- **n_adresses = 1385**
- `_fusion_auto == True` (fusionnées) : **459**
- ancres (non fusionnées) : **926**
- `nb_ventes_total` manquant/None : 0 ; `nb_ventes_logement` manquant/None : 0

---

## ETAPE 2 — Source de la répartition

Module `sctGen` dans `index.html`. La fonction d'agrégation par îlot est `sctGenComputeIlots()` (ligne **2659**).

**Fichier de données alimentant la répartition** : `secteurData` (= le light DL chargé en mémoire, `data/secteur_dauphine_lacassagne_light.json`), lu via `secteurData.adresses` (l. 2660, 2690). Pas d'autre fichier.

**Champ utilisé pour `ilot.nb_ventes` = STRICT (`nb_ventes_logement`), pas brut.**
Le mode est forcé en strict dès que les données logement existent, indépendamment du toggle UI (l. **2670**) :
```js
2670  const useStrict = secteurData.adresses.some(a => a.ventes_par_an_logement);
...
2672  const sumVpa = a => {
2673    if (useStrict && a.ventes_par_an_logement) {
2674      if (typeof a.nb_ventes_logement === 'number') return a.nb_ventes_logement;   // <- STRICT
2675      let s = 0; for (const y of ANS) s += (a.ventes_par_an_logement[y] || 0); return s;
2676    }
2677    if (typeof a.nb_ventes_total === 'number') return a.nb_ventes_total;            // fallback brut
...
```
DL a `ventes_par_an_logement` → `useStrict = true` → `sumVpa` renvoie `nb_ventes_logement` (valeurs 5 ans).

**Division par 5 ?** — PAS dans l'agrégation. L'algo travaille en cumul 5 ans en interne. La division /5 n'intervient qu'à **l'affichage** :
```js
2734  const SCT_GEN_ANS = 5;
2736  function sctGenPerYear(v) { return ((v || 0) / SCT_GEN_ANS).toFixed(1); }
```

**Filtre d'appartenance à un îlot** — `ilotEffectif(a)` (défini l. **4873**) :
```js
4873  const ilotEffectif = a => {
4874    const as = secteurAssign[a.cle] || {};
4875    if (as.ilot != null) return as.ilot;          // 1) override KV manuel
4876    if (a._ilot && a._ilot !== 'X') {              // 2) sinon _ilot du light (hors 'X')
4877      const n = parseInt(a._ilot);
4878      if (!Number.isNaN(n)) return n;
4879    }
4880    return null;                                    // 3) sinon AUCUN ilot
4881  };
```
Dans `sctGenComputeIlots`, une adresse est ignorée si `iid == null` (l. 2692) ou `_ilot === 'X'` (l. 2693).

**Exclusion social/bureaux** (point clé du sous-compte), l. **2699-2705** :
```js
2699    const tg = (secteurAssign[a.cle] || {}).type;
2700    if (tg !== 'social' && tg !== 'bureaux') {
2701      o.nb_ventes += sumVpa(a);                    // compté dans l'ilot
2702    } else {
2703      exclVentes  += sumVpa(a);                    // EXCLU (compteur diag uniquement)
2704      exclAdresses++;
2705    }
```
Les adresses taguées `social` ou `bureaux` dans le KV `secteurAssign` sont **comptées dans `exclVentes` et JAMAIS ajoutées à `ilot.nb_ventes`** (refactor r7.7 2026-05-25).

**Étage de distribution** `sctGenDistribByZone()` (l. 2787) : chaque îlot de chaque zone est affecté à un `bestSid` (l. **2923** `newRep[ilot.ilotId] = { conseillerId: bestSid }`), avec un fallback (l. 2900) garantissant qu'aucun îlot ne reste sans conseiller. **Donc aucun îlot n'est perdu à la distribution** — la somme sur les 10 secteurs = somme de tous les îlots.

---

## ETAPE 3 — Somme réelle de la répartition

Reproduction fidèle de `sctGenComputeIlots` (champ strict `nb_ventes_logement`, `ilotEffectif` = KV `as.ilot` sinon `_ilot≠'X'`, exclusion social/bureaux) avec l'état KV courant `data/_kv_assign_dl.json` :

| Poste | 5 ans | / an |
|---|---|---|
| **Total réellement sommé dans les îlots** (= Σ sur 10 secteurs) | 2842 | **568.4** |
| Exclu social/bureaux (`exclVentes`) | 156 | **31.2** |
| Adresses sans îlot (`iid == null`) | 0 | 0.0 |
| Adresses `_ilot == 'X'` | (1 row, 0 vente) | 0.0 |
| **Grand total (référence Étape 1)** | 2998 | **599.6** |

Réconciliation : 568.4 + 31.2 + 0 + 0 = **599.6** ✓ (84 îlots construits).

**VERDICT : COUVERTURE INCOMPLÈTE.** La répartition somme **568.4 ventes/an**, soit le « ~568 » attendu. Ce n'est **pas** un bug d'affichage (la division /5 est correcte et appliquée seulement à l'affichage ; l'algo agrège bien le strict `nb_ventes_logement`). Le manque vient de l'**exclusion volontaire des adresses taguées `social`/`bureaux`** (l. 2700-2705), retirées du marché logement marchand.

---

## ETAPE 4 — Résiduel (couverture incomplète)

- Adresses tombant dans **AUCUN** îlot (`ilotEffectif == null`) : **0** → 0 vente/an.
- Îlots affectés à **aucun** conseiller : **0** (la distribution place tous les îlots, fallback l. 2900).
- **Le résiduel provient donc à 100 % de l'exclusion `social`/`bureaux`**, pas d'une lacune d'affectation.

Somme du résiduel `nb_ventes_logement/5` (adresses social+bureaux ayant un îlot) :

| Type | Nb adresses | Ventes strictes / an |
|---|---|---|
| social | 209 | 26.0 |
| bureaux | 97 | 5.2 |
| **TOTAL** | **306** | **31.2** |

> Attendu ~29.8/an (= 597.8 − 568). Mesuré : **31.2/an** (= 599.6 − 568.4). L'écart vient de la dérive du light depuis la référence (strict réel 599.6 vs 597.8, cf. Étape 1) — la mécanique est la même. Sur les 306 adresses exclues, seules **48** portent des ventes logement > 0.

### Top 20 contributeurs manquants (ventes strictes/an décroissantes)

| Ventes/an | Type | Adresse |
|---:|---|---|
| 1.80 | social | 8 RUE CLAUDIUS PIONCHON |
| 1.40 | social | 4 RUE CLAUDIUS PIONCHON |
| 1.40 | bureaux | 5 COURS ALBERT THOMAS |
| 1.40 | bureaux | 79 RUE DU DAUPHINE |
| 1.40 | social | 20 RUE ST SIDOINE |
| 1.20 | social | 136 RUE ANTOINE CHARIAL |
| 1.20 | social | 4 RUE FRANCOIS GILLET |
| 1.20 | social | 252A RUE PAUL BERT |
| 1.00 | social | 7B RUE DE MONTBRILLANT |
| 0.80 | social | 132 RUE ANTOINE CHARIAL |
| 0.80 | social | 82 RUE ANTOINE CHARIAL |
| 0.80 | social | 16 RUE ETIENNE RICHERAND |
| 0.80 | social | 30 RUE ST ANTOINE |
| 0.80 | bureaux | 185T AVENUE FELIX FAURE |
| 0.80 | social | 66B AVENUE LACASSAGNE |
| 0.80 | social | 7T RUE DE MONTBRILLANT |
| 0.60 | social | 15 AVENUE GEORGES POMPIDOU |
| 0.60 | social | 18 RUE ETIENNE RICHERAND |
| 0.60 | social | 13 AVENUE GEORGES POMPIDOU |
| 0.60 | social | 6 RUE TURBIL |

---

## CONCLUSION

Les ~31.2 ventes/an « manquantes » (599.6 strict total − 568.4 réparti) ne sont pas perdues ni mal divisées : elles correspondent **exactement aux 306 adresses taguées `social`/`bureaux` dans le KV, volontairement exclues de la répartition par îlot (index.html l. 2700-2705)** — hors champ du marché logement marchand. C'est une **couverture incomplète assumée, pas un bug d'affichage**.

---

### Annexe — méthode / reproductibilité
- Référence : somme directe des champs `nb_ventes_total` / `nb_ventes_logement` sur les 1385 adresses du light.
- Répartition : réimplémentation de `ilotEffectif` + `sumVpa` + exclusion social/bureaux, alimentée par l'état KV `data/_kv_assign_dl.json` (clé `assignments`). 84 îlots, distribution `sctGenDistribByZone` vérifiée comme non-déperditive (tout îlot reçoit un conseiller).
- Réconciliation parfaite : 568.4 (réparti) + 31.2 (exclu) + 0 (sans îlot) = 599.6 (référence).
