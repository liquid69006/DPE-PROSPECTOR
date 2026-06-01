# Plan — « strict = MARCHE LIBRE » fusion-aware partout (secteur Dauphiné-Lacassagne)

> PLAN READ-ONLY. Date : 2026-05-31. AUCUNE donnée/code modifié. Seul ce fichier est écrit.
> Décision actée par Yann : le « strict » = **MARCHE LIBRE** = exclure `{social, bureaux}`
> **jugé par le tag de l'ANCRE de fusion** (jamais l'adresse brute fusionnée), **fusion-aware
> PARTOUT**. Cible **580,2/an** côté dashboard ET côté répartition. Le brut reste inchangé.
>
> Sources lues : `index.html` (renderSecteur l.4787-5351 ; sctGen l.2659-2730),
> `data/secteur_dauphine_lacassagne_light.json`, `data/_kv_assign_dl.json`
> (assignments 643, fusions 6, noms), `scripts/test_render_secteur.js`, `data/PIPELINE.md`.

---

## 0. Rappel des mécaniques (vérifié dans le code)

- **Fusions = 2 sources**, toutes deux pliées vers leur **ancre** :
  - **manuelle** : `secteurFusions` (KV `fusions`, 6 entrées DL), `src → dst`, build l.4841-4848.
  - **auto BDNB** : champ light `_fusion_auto` + cible `a._fusion_cible || a._fusion_auto_target`
    (l.4859), build l.4858-4867.
  - **Nom du champ ancre vérifié** : `_fusion_cible` (dominant) **OU** `_fusion_auto_target`
    (3 récents) ; côté KV manuel, l'ancre est la **valeur** de `secteurFusions[src]`.
- **fusedSrc** (l.4844, 4861) marque les **sources** ; elles sont **écartées du rendu** dès
  `if (fusedSrc[a.cle]) return;` (l.4966). **Donc seules les ancres + adresses non-fusionnées
  sont rendues ET sommées.**
- L'ancre porte un `effTot` = ses propres ventes + ventes **redistribuées** des sources
  (`mi`=mergedInto manuel l.5074, `am`=autoMerged BDNB l.5075 ; calcul effV/effTot l.5076-5079).
- **Conséquence-clé** : côté `renderSecteur`, le header est **déjà fusion-aware** (les ventes
  d'une source vivent sur l'ancre). Exclure « par le tag de l'ANCRE » revient simplement à
  exclure l'**adresse rendue** (= l'ancre) si `secteurAssign[ancre.cle].type ∈ {social,bureaux}`.
  Aucune indirection `_fusion_cible` n'est nécessaire dans renderSecteur : l'ancre EST l'adresse.

### Chiffres reproduits (light × KV, mode strict)

| Grandeur | 5 ans | /an |
|---|---:|---:|
| Header strict TOTAL (sans filtre, actuel) | 2998,0 | **599,6** |
| dont ancres social/bureaux (effTot, fusion-aware) | 97,0 | 19,4 |
| **Header MARCHE LIBRE (599,6 − 19,4)** | 2901,0 | **580,2** |
| sctGen ACTUEL (exclusion par adresse, fusions ignorées) | 2842,0 | **568,4** |

---

## A — Dashboard (`renderSecteur`) : header + sous-total îlot + ligne

### Confirmation 580,2
`effTot` est **déjà fusion-aware** (l.5076-5079, redistribution `mi`/`am`). En conditionnant
l'accumulation à « ancre non social/bureaux », le header passe de **599,6 → 580,2/an**
(vérifié par calcul : 2998 − 97 = 2901 ; /5 = 580,2). ✔

### Récupérer l'ancre et son tag
Inutile de remonter `_fusion_cible` : dans renderSecteur la boucle ne voit que les **ancres**
(sources écartées l.4966). Le tag de l'ancre = `(secteurAssign[a.cle] || {}).type` — exactement
le même prédicat que sctGen. Définir une fois, juste avant la boucle d'accumulation :

```diff
   parIlot[ik].forEach(a => {
       ...
       const effTot = ANS.reduce((s, y) => s + effV[y], 0);
+      // [MARCHE LIBRE] exclusion par le tag de l'ANCRE de fusion. Dans
+      // renderSecteur la boucle ne voit que les ancres (sources fusionnees
+      // ecartees l.4966) -> a.cle EST la cle d'ancre. effTot est deja
+      // fusion-aware (ventes des sources redistribuees l.5076-5079).
+      const _mlExcl = (() => { const tg = (secteurAssign[a.cle] || {}).type;
+        return tg === 'social' || tg === 'bureaux'; })();
```

**Edit 1 — accumulation îlot (l.5099)** :
```diff
-        iloAllV += effTot;
+        iloAllV += _mlExcl ? 0 : effTot;   // marche libre : exclut ancres social/bureaux
```

**Sous-total îlot (l.5315-5317)** : alimenté par `iloAllV` → **se met à jour automatiquement**,
aucun edit. `iloTaux = sctTauxAnnuel(iloAllV, iloL)` (l.5315) suit.

**Header secteur (l.5313, 5342-5348)** : `secAllV += iloAllV` (l.5313) → **automatique**, aucun
edit. `secVAn = secAllV/5` (l.5342) devient 580,2.

**Ligne d'adresse (l.5305-5306)** : `effV[y]` et `effTot` restent affichés tels quels
(voir E pour la mise entre parenthèses). La ligne **n'est pas** touchée par Edit 1.

> ⚠️ NE PAS toucher : `secL`, `iloL`, `bgValue`, `seenLgts`, `getEffectiveLog`, `vpaOf`,
> `seenLgts` (parc / dédup §6 — déjà marché-libre, doit rester **bit-identique**).
> Édit unique et trivialement réversible (un ternaire).

> **Brut** : le ternaire s'applique aussi quand `secteurStrict=false` (Edit 1 est dans le
> chemin commun). Recommandé et **cohérent avec sctGen** qui exclut social/bureaux dans les 2
> modes. Le brut « tout inclus » de la consigne désigne les autres types (mixte/mono/copro…)
> qui restent comptés ; social/bureaux sont hors-marché par définition produit.

---

## B — Répartition (`sctGen`, l.2659-2730)

### État actuel
Exclusion **par le tag de l'ADRESSE** (l.2699-2700) **et fusions IGNORÉES** : `sumVpa(a)` est
sommé adresse par adresse, **sans** plier les sources sur leur ancre → 568,4/an.

### Changement minimal pour atteindre 580,2
sctGen doit devenir **fusion-aware** ET juger **par l'ancre**. Deux briques à ajouter dans
`sctGenComputeIlots` :

1. **Construire la table source→ancre** (réplique de renderSecteur l.4841-4867), au début de
   la fonction :
```diff
   const sumVpa = a => { ... };
+  // [MARCHE LIBRE] fusion-aware : plier les ventes des sources sur l'ancre,
+  // comme renderSecteur (l.4841-4867). 2 conventions : secteurFusions (KV
+  // manuel) + _fusion_auto/_fusion_cible|_fusion_auto_target (BDNB).
+  const adrByCle = {}; secteurData.adresses.forEach(a => adrByCle[a.cle] = a);
+  const fusedSrc = {}; const foldTo = {};   // srcCle -> ancreCle
+  Object.keys(secteurFusions || {}).forEach(src => {
+    const dst = secteurFusions[src];
+    if (!adrByCle[src] || !dst || src === dst) return;
+    fusedSrc[src] = true; foldTo[src] = dst;
+  });
+  secteurData.adresses.forEach(a => {
+    const cible = a._fusion_cible || a._fusion_auto_target;
+    if (a._fusion_auto && cible && !fusedSrc[a.cle]) { fusedSrc[a.cle] = true; foldTo[a.cle] = cible; }
+  });
+  // ventes pliees par ancre (en plus de leurs propres ventes)
+  const foldedVpa = {};
+  for (const src of Object.keys(foldTo)) {
+    foldedVpa[foldTo[src]] = (foldedVpa[foldTo[src]] || 0) + sumVpa(adrByCle[src]);
+  }
```

2. **Boucle d'agrégation** : ignorer les sources, juger par l'ancre, ajouter les ventes pliées :
```diff
   for (const a of secteurData.adresses) {
+    if (fusedSrc[a.cle]) continue;            // source fusionnee : ventes pliees sur l'ancre
     const iid = ilotEffectif(a);
     if (iid == null) continue;
     if (a._ilot === 'X') continue;
     const key = String(iid);
     if (!byIlot[key]) byIlot[key] = { ilotId: key, nb_ventes: 0, _slat:0, _slng:0, _nll:0, adresses: [] };
     const o = byIlot[key];
     const tg = (secteurAssign[a.cle] || {}).type;   // tg = tag de l'ANCRE (source ecartee)
+    const vTot = sumVpa(a) + (foldedVpa[a.cle] || 0);
     if (tg !== 'social' && tg !== 'bureaux') {
-      o.nb_ventes += sumVpa(a);
+      o.nb_ventes += vTot;
     } else {
-      exclVentes  += sumVpa(a);
+      exclVentes  += vTot;
       exclAdresses++;
     }
```
Résultat sctGen : **568,4 → 580,2/an** (identité parfaite avec le header). ✔

### POINT CRUCIAL — des sources tombent-elles dans un ÎLOT ≠ celui de leur ancre ?

**OUI.** Calcul sur light × KV (`ilotEffectif` source vs ancre) :

| Mesure | Valeur |
|---|---:|
| Sources fusionnées totales | 462 |
| Source **même** îlot que l'ancre | 419 |
| **Source îlot ≠ ancre** | **43** |
| Sources sans îlot / ancres sans îlot | 11 / 13 |
| **Ventes strictes (5 ans) sur sources en îlot ≠ ancre** | **90** |
| **/an** | **18,0** |

Top sources « relocalisées » d'un îlot à l'autre par le pliage (vpa 5 ans) :

| src (îlot src) → ancre (îlot ancre) | vpa 5 ans |
|---|---:|
| 25 RUE ST ANTOINE (9) → 272 COURS LAFAYETTE (3) | 14 |
| 141 AV FELIX FAURE (55) → 139 AV FELIX FAURE (54) | 12 |
| 6 RUE CADETS FRANCE LIBRE (57) → 2 RUE CADETS (56) | 9 |
| 136 RUE ANTOINE CHARIAL (33) → 128 ANTOINE CHARIAL (37) | 6 |
| 53 RUE ST MAXIMIN (80) → 51 ST MAXIMIN (78) | 5 |
| 12 RUE MOISSONNIER (48) → 11 AV LACASSAGNE (54) | 5 |
| 2 RUE LOUIS JASSERON (22) → 14 RUE ST VICTORIEN (11) | 5 |

**Conséquence (≠ 0 → PAS neutre intra-îlot)** : le passage fusion-aware **déplace** 18,0/an de
ventes vers l'îlot de l'ancre. Ce n'est pas seulement le critère d'exclusion qui change ; la
**géographie des ventes par îlot bouge**. C'est la source principale de l'impact ré-équilibrage
(partie D). Le calcul D ci-dessous intègre exactement ce pliage.

---

## C — Modale génération / export (l.3502-3696)

La modale **dérive intégralement de `sctGenComputeIlots()`** : `meanT`, `quotas`,
`sctGenScoreSecteur` (l.2742), table A0 — tout est calculé à partir de `sctGenState.ilots`
(= sortie de sctGenComputeIlots) et `sctGenState.repartition`. Le label « Mode » (l.3512-3515,
l.3694-3696) est un texte (« ventes strictes »/« brutes »), inchangé.

➜ **Aucun edit dédié dans la modale.** Une fois B appliqué, `ilot.nb_ventes` vaut la valeur
fusion-aware-par-ancre → `meanT`, quotas et table A0 atteignent **580,2/an** automatiquement.
Seul prérequis : que B soit fait AVANT (la modale hérite de #4 comme noté dans le diag étape 3).

---

## D — Impact ré-équilibrage (le point le plus important)

### D.1 Delta par îlot : ACTUEL (568,4, par adresse, fusions ignorées) → CIBLE (580,2, par ancre, fusion-aware)

Net global : **+11,8/an** (somme gains +26,4 − pertes −14,6). Îlots avec |Δ| > 0,05/an :

**Îlots qui GAGNENT** (îlot : actuel/an → cible/an, +Δ/an) :

| Îlot | Actuel/an | Cible/an | +Δ/an |
|---:|---:|---:|---:|
| 11 | 2,40 | 9,80 | **+7,40** |
| 54 | 6,60 | 10,20 | +3,60 |
| 3 | 8,60 | 11,80 | +3,20 |
| 37 | 5,00 | 7,00 | +2,00 |
| 56 | 12,20 | 14,00 | +1,80 |
| 9 | 11,00 | 12,40 | +1,40 |
| 10 | 2,40 | 3,80 | +1,40 |
| 50 | 15,40 | 16,60 | +1,20 |
| 16 | 2,40 | 3,60 | +1,20 |
| 60 | 5,20 | 6,00 | +0,80 |
| 75 | 2,20 | 3,00 | +0,80 |
| 38 | 4,80 | 5,40 | +0,60 |
| 29 | 4,00 | 4,40 | +0,40 |
| 61 | 11,60 | 12,00 | +0,40 |
| 52 | 10,20 | 10,40 | +0,20 |

**Îlots qui PERDENT** :

| Îlot | Actuel/an | Cible/an | Δ/an |
|---:|---:|---:|---:|
| 55 | 2,80 | 0,40 | −2,40 |
| 68 | 4,20 | 2,00 | −2,20 |
| 57 | 14,00 | 12,20 | −1,80 |
| 22 | 21,60 | 20,20 | −1,40 |
| 2 | 6,20 | 4,80 | −1,40 |
| 49 | 7,40 | 6,20 | −1,20 |
| 59 | 17,80 | 16,60 | −1,20 |
| 48 | 9,60 | 8,60 | −1,00 |
| 53 | 13,00 | 12,00 | −1,00 |
| 46 | 4,00 | 3,60 | −0,40 |
| 44 | 2,40 | 2,20 | −0,20 |
| 35 | 8,20 | 8,00 | −0,20 |
| 43 | 6,60 | 6,40 | −0,20 |

Deux effets se superposent : (i) **+19,4/an** réinjectés (les ventes des **ancres NON
social/bureaux** qui portent des sources autrefois exclues, et les ancres autrefois sommées
par adresse) ; (ii) la **relocalisation inter-îlots** de 18,0/an (cf. B). Le plus gros mouvement
est **îlot 11 +7,40/an** (pliage de sources des îlots 22 et autres vers l'ancre 14 ST VICTORIEN).

### D.2 Verdict par secteur — tolérance ±5 %

- Cible : moyenne/secteur = **580,2 / 10 = 58,02/an** ; bande **±5 % = ±2,90/an → [55,12 ; 60,92]**.
- Actuel : moyenne/secteur = 568,4 / 10 = 56,84/an (la répartition KV courante a été générée
  pour tenir ±5 % autour de **56,84**, pas autour de 58,02).

**Tableau secteur** : la carte **îlot → conseiller → secteur** des 10 secteurs n'est **PAS**
disponible en local (persistée uniquement en **KV** via `/secteur-repartition/{secId}` ;
`data/_kv_assign_dl.json` ne contient QUE `assignments`/`fusions`/`noms`, aucun
`conseillerId`/`repartition` — vérifié, 0 fichier local). Le tableau « secteur | total actuel/an
| total cible/an | Δ | %écart vs moyenne » ne peut donc être chiffré en read-only sans token KV.
À produire au moment de l'implémentation par un `GET /secteur-repartition/dauphine-lacassagne`
puis agrégation des îlots ci-dessus par `conseillerId`. **Structure du tableau à remplir** :

| Secteur (conseiller) | Total actuel/an | Total cible/an | Δ/an | % écart vs 58,02 |
|---|---:|---:|---:|---:|
| … (10 lignes) | … | … | … | … |

**Verdict ré-génération : OUI (re-génération nécessaire).** Raisons :
1. Un **seul îlot** se déplace de **+7,40/an** (îlot 11) et un autre de **−2,40** (îlot 55) —
   chacun **dépasse à lui seul la demi-bande de tolérance** (±2,90/an). Un secteur qui contient
   l'îlot 11 (ou un cumul des gros gains/pertes) sera très probablement poussé **hors de la
   bande [55,12 ; 60,92]**.
2. La répartition KV courante a été optimisée par `sctGenDistribByZone` (quotas par zone,
   contrainte overload ±5 %) sur les **anciennes** `nb_ventes` par îlot. Le nouvel agrégat
   change `ilot.nb_ventes` ET le score `sctGenScoreSecteur` (l.2742-2752) → l'équilibre
   ±5 % calculé sur l'ancienne base n'est plus garanti.
3. La moyenne-cible elle-même se déplace (56,84 → 58,02/an), donc la bande de référence change.

Recommandation : après A+B, **re-générer la répartition** (bouton Générer → l'algo recalcule
quotas/distribution sur la base 580,2), puis re-persister en KV. Le delta +11,8/an net + 18,0/an
relocalisés est trop structurant pour un simple re-tag.

---

## E — Lignes social/bureaux : parenthéser la cellule VENTES (ligne visible)

**Faisable**, modèle « `0 (X)` » déjà en place pour la cellule logements (l.5280-5289). La
ligne reste rendue (pas de masquage), seules les cellules ventes/total passent en « hors-total ».

**Edit (l.5305-5306)** — afficher les ventes grisées/parenthésées si ancre social/bureaux :
```diff
-          + ANS.map(y => sctCell(String(effV[y] || 0), SCTW.an, 'center')).join('')
-          + sctCell(`<b>${effTot}</b>`, SCTW.tot, 'center')
+          + ANS.map(y => sctCell(_mlExcl
+              ? `<span style="color:var(--text2);opacity:.6;">(${effV[y] || 0})</span>`
+              : String(effV[y] || 0), SCTW.an, 'center')).join('')
+          + sctCell(_mlExcl
+              ? `<span style="color:var(--text2);opacity:.6;" title="hors marche libre">(${effTot})</span>`
+              : `<b>${effTot}</b>`, SCTW.tot, 'center')
```
(réutilise `_mlExcl` défini en A). Le **taux** (l.5307) peut rester ou être forcé à `—` ;
le plus cohérent avec la cellule logements `0 (X)` est de laisser le taux tel quel (déjà calculé
sur `denomAff` qui vaut souvent `null` pour social/bureaux → affiche `—`). **Purement cosmétique,
séparable du chiffre** : à faire seulement si Yann le confirme.

---

## F — Harnais `scripts/test_render_secteur.js` (§7)

### Nouvelles plages SRC (l.31-37) — l'ancien `slice(2148,2484)` est PÉRIMÉ
renderSecteur est aujourd'hui en **4787-5351**. Bornes vérifiées par Read :

```diff
 const SRC = [
-  slice(2058, 2062),   // ROT_COLOR + TYPE_OPTS
-  slice(2084, 2086),   // esc
-  slice(2088, 2092),   // secteurNorm
-  slice(2105, 2146),   // sctTauxAnnuel..sctBadge
-  slice(2148, 2484),   // renderSecteur (...)
+  slice(2512, 2525),   // ROT_COLOR + TYPE_OPTS + TYPE_LABELS + TYPE_BADGE_COLORS
+  slice(4685, 4688),   // esc
+  slice(4689, 4693),   // secteurNorm
+  slice(4737, 4786),   // sctTauxAnnuel..sctClassAnnuel + SCTW + DPE_COLOR + sctDpe..normalizeAdresseDisplay
+  slice(4787, 5351),   // renderSecteur (parc / strict / hr-actif / sctQ / marche libre)
 ].join("\n\n");
```
> Note : `usageResid` et `USAGE_RESID` sont **internes** à renderSecteur (l.4816-4817) → couverts
> par la dernière slice. `TYPE_LABELS` (utilisé l.5281) est dans le 1er bloc (2512-2525).
> **Re-vérifier ces bornes après CHAQUE édition d'index.html** (gotcha connu MEMORY/§7).

### Fixture `secteurAssign` peuplé (sandbox l.59 le met vide → n'exerce PAS l'exclusion)
Ajouter une variante de `runRender` (ou un param) avec un `secteurAssign` **non vide** ciblant
des `cle` réellement présentes dans le light DL (toutes vérifiées présentes) :
```js
const ASSIGN_DL = {
  "11|RUE|DAUPHINE":      { type: "social"  },   // social (présent KV)
  "2|RUE|AUBIGNY":        { type: "bureaux" },   // bureaux (présent KV)
  "139|AVENUE|FELIX FAURE": { type: "mixte" },   // ANCRE de fusion (141 FF s'y plie) -> NON exclue
};
```
…et un appel `runRender(CUR, true, "", false, ASSIGN_DL)` (signature à étendre pour injecter
`secteurAssign` dans le sandbox au lieu de `{}` l.59). Cela **exerce** : 1 social exclu,
1 bureaux exclu, et 1 ancre fusionnée taguée (mixte) qui **conserve** les ventes pliées.

### Baselines à rebaser vers 580,2
- **l.193-195** (`ventes/an strict <= brut` / `< brut`) : avec le fixture vide actuel, **ne
  change PAS** (assign vide → aucune exclusion). **Rester vert.** En revanche, **avec le nouveau
  fixture peuplé**, ajouter une baseline dédiée :
  ```js
  // marché libre < strict total (exclusion ancres social/bureaux active)
  check(`ventes/an marche libre < strict total (${venML} < ${venStrict})`, venML < venStrict);
  ```
  et, si on chiffre en dur, **viser 580,2/an** sur le light DL courant (vs 599,6 sans fixture).
- **l.281-329** (parc `secL`) : **NE DOIT PAS bouger** (la modif ne touche pas le parc) →
  garde-fou anti-régression §6, doit rester vert bit-identique.

**Note de commit (pourquoi la baseline change)** : « la baseline ventes/an passe de 599,6 (tout
inclus) à 580,2 (marché libre = hors ancres social/bureaux, fusion-aware) — changement
intentionnel, pas une régression ; le parc `secL` reste invariant. »

---

## G — Doc : `data/PIPELINE.md` §6

Insérer, dans la puce **Ventes** de §6 (juste après la ligne « conservation prouvée », l.317),
le texte exact :

```
- **« Strict » = MARCHE LIBRE** : l'agrégat strict (header secteur, sous-total
  îlot, répartition sctGen, modale gén/export) **exclut** les adresses taguées
  `social` / `bureaux`, **jugé par le tag de l'ANCRE de fusion** (jamais
  l'adresse brute fusionnée), et **fusion-aware partout** (les ventes des
  sources sont pliées sur l'ancre avant exclusion). Cible DL = **580,2/an**
  (vs 599,6 tout-inclus). Le **brut** garde tous les types non-{social,bureaux}.
  Identité : header marché-libre == sctGen marché-libre == 580,2 (les deux
  fusion-aware). Parc `secL` (dédup `bg:bgid`) inchangé — orthogonal aux ventes.
```

---

## ORDRE D'IMPLÉMENTATION GLOBAL (additif & réversible)

1. **`index.html` / sctGen (B)** — `sctGenComputeIlots` (l.2659-2705) : ajouter `foldTo/foldedVpa`
   (fusion-aware) + `continue` sur `fusedSrc` + somme `vTot`. → sctGen 568,4 → **580,2**.
   *(Faire B avant C : la modale en dérive.)*
2. **`index.html` / renderSecteur (A)** — définir `_mlExcl` (par tag d'ancre = `a.cle`) +
   `iloAllV += _mlExcl ? 0 : effTot` (l.5099). → header 599,6 → **580,2**. NE PAS toucher parc.
3. **(C)** — vérifier (sans edit) que la modale gén/export affiche 580,2 (héritée de B).
4. **(E, optionnel/cosmétique, sur confirmation Yann)** — parenthéser cellules ventes
   social/bureaux (l.5305-5306) via `_mlExcl`. Ligne reste visible.
5. **`scripts/test_render_secteur.js` (F)** — recaler les `slice(...)` (l.31-37) sur 2512-2525 /
   4685-4688 / 4689-4693 / 4737-4786 / 4787-5351 ; ajouter fixture `ASSIGN_DL` + baseline marché
   libre < total ; vérifier baseline parc `secL` verte. Documenter le rebase dans le commit.
6. **`data/PIPELINE.md` §6 (G)** — insérer la puce « Strict = MARCHE LIBRE » après l.317.
7. **Ré-équilibrage (D)** — **re-générer** la répartition (bouton Générer → recalcul quotas sur
   base 580,2) puis re-persister KV. Verdict : **re-génération OUI** (mouvements par îlot
   jusqu'à +7,40/an > demi-bande ±2,90). Le tableau par secteur se chiffre au moment de l'impl.
   via `GET /secteur-repartition/dauphine-lacassagne` (carte îlot→conseiller KV-only, absente en
   local).
8. **Dry-run + validation Yann** (§4.6) → commit `feat(secteur):` (pas de `[skip ci]`).

### Invariants / garde-fous
- Parc `secL` + dédup `bg:bgid` (§6) : **bit-identique** avant/après (A/B ne touchent que le
  numérateur ventes ; E n'est que cosmétique).
- `getEffectiveLog`, `vpaOf`, `seenLgts`, `bgValue` : **non modifiés**.
- Identité finale visée : **header == sctGen == modale == 580,2/an**, fusion-aware partout,
  exclusion par tag d'ancre.
- Réversibilité : A = 1 ternaire ; B = 1 bloc fusion + 1 `continue` + `vTot` ; E = 2 cellules ;
  retrait trivial.
