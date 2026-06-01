# Diag READ-ONLY — Aligner le « strict » du dashboard sur le MARCHE LIBRE (secteur DL)

> Objectif : préparer (NE PAS appliquer) la modif qui ferait que le gros chiffre
> « strict » du dashboard secteur exclue **social + bureaux** (comme la
> répartition `sctGen`), tout en gardant mixte / mono / copro / copro_non_immat.
> Aucune modification de données ni de code n'a été faite. Seul ce rapport est écrit.
>
> Fichiers analysés (lecture seule) :
> - `index.html` (SPA, `renderSecteur` + module `sctGen`)
> - `data/secteur_dauphine_lacassagne_light.json` (data)
> - `data/_kv_assign_dl.json` (tags KV social/bureaux/mono/…)
> - `scripts/test_render_secteur.js` (harnais §7)

---

## ETAPE 1 — Le prédicat d'exclusion social/bureaux

### Code EXACT (module `sctGen`, `index.html` l.2699-2705)

```js
const tg = (secteurAssign[a.cle] || {}).type;
if (tg !== 'social' && tg !== 'bureaux') {
  o.nb_ventes += sumVpa(a);
} else {
  exclVentes  += sumVpa(a);
  exclAdresses++;
}
```

Commentaire-bloc juste au-dessus (l.2684-2688) :

```js
// [REFACTOR r7.7 2026-05-25] Exclusion ventes adresses social/bureaux :
// les adresses taguees secteurAssign.type in {social, bureaux} sont
// considerees hors-champ marche logement marchand (cf getEffectiveLog
// qui retourne deja 0 pour le parc). Coherence affichage/calcul.
```

### Quelle structure tague une adresse ?

`secteurAssign` — déclaré **module-level global** en `index.html` l.2244 :

```js
let secteurData = null, secteurLoaded = false, secteurAssign = {}, ...
```

Il est **chargé depuis le KV** (`secteurAssign = j.assignments || {}`, l.2453) à partir du
backend, miroir local de `data/_kv_assign_dl.json` (clé top-level `assignments`).
Indexé **par `a.cle`** : `secteurAssign[a.cle].type`. Le champ pertinent est
`.type`. Ce n'est PAS `coproByCle` (jointure RNC) ni une map front dédiée.

### L'ensemble exclu est-il EXACTEMENT {social, bureaux} ?

Oui. Le test `tg !== 'social' && tg !== 'bureaux'` (l.2700) inclut **tout le
reste** dans `o.nb_ventes` : `mixte`, `mono`, `copro_non_immat`, `cible_0vente_*`,
`null`/non-tagué, et les copros RNC (qui n'ont pas de tag KV → `tg === undefined`
→ incluses). Les types présents dans le KV DL (comptés) :
`social 213`, `bureaux 122`, `mixte 43`, `copro_non_immat 85`, `mono 106`,
`cible_0vente_active 54`, `cible_0vente_isolee 16`, `null 4`. Seuls `social` et
`bureaux` sont exclus.

Cohérence avec le parc : `getEffectiveLog` (l.4827-4834, dans `renderSecteur`)
retourne déjà `0` pour `social`/`bureaux` côté logements — la modif ventes
proposée serait donc l'exact pendant côté ventes.

### Accessibilité dans `renderSecteur`

OUI — `secteurAssign` est un **global de module**, déjà lu une dizaine de fois
DANS `renderSecteur` (ex. l.4828 `secteurAssign[a.cle]` dans `getEffectiveLog`,
l.4934-4935, l.4995, l.5061). **Aucun replumbing nécessaire** : le tag est dans
le scope, accessible par `a.cle`, exactement comme dans `sctGen`. La modif est
faisable en réutilisant le même prédicat `(secteurAssign[a.cle]||{}).type`.

---

## ETAPE 2 — Le « gros chiffre » strict du header

### Localisation (dans `renderSecteur`)

Accumulateurs déclarés l.4894 :
```js
let secAllV = 0, secL = 0;        // header = somme des Ilots = somme des adresses
```

Numérateur ventes par adresse — l.5076-5079 :
```js
const effV = {};
ANS.forEach(y => { effV[y] = ((vpaOf(a) || {})[y] || 0)
  + (mi ? (mi.ventes[y] || 0) : 0) + (am ? (am.ventes[y] || 0) : 0); });
const effTot = ANS.reduce((s, y) => s + effV[y], 0);
```
avec `vpaOf` (l.4808-4809) :
```js
const vpaOf = a => (secteurStrict && a && a.ventes_par_an_logement)
  ? a.ventes_par_an_logement : (a ? a.ventes_par_an : null);
```

Agrégation par îlot puis header — l.5099, l.5313, l.5342-5348 :
```js
iloAllV += effTot;                          // l.5099 (par adresse)
...
secAllV += iloAllV; secL += iloL;           // l.5313 (par îlot)
...
const secVAn = secAllV / 5;                 // l.5342
const secTaux = secL > 0 ? Math.round(secAllV / secL / 5 * 1000) / 10 : null; // l.5343
document.getElementById('secteur-resume').textContent =
  `${nbShown} adresses · ${nbRnc} RNC · ${nbBdnb} BDNB · `
  + `${secL.toLocaleString('fr-FR')} lgts · `
  + `${secVAn.toLocaleString('fr-FR', {minimumFractionDigits:1, maximumFractionDigits:1})} ventes/an · `
  + `taux secteur ${secTaux != null ? secTaux : '—'}%/an`;
```

### Filtre social/bureaux présent aujourd'hui ?

**NON.** `iloAllV += effTot` (l.5099) est inconditionnel : il somme `effTot` de
**toute** adresse rendue, sans regarder `secteurAssign[a.cle].type`. Les ventes
des adresses social/bureaux sont donc **incluses** dans `secAllV` (→ 599,6/an).
C'est le seul point à modifier (numérateur ventes du header).

### Ce qui NE doit PAS bouger (parc / dédup §6)

Le parc `secL` est **indépendant** du numérateur ventes :
- `iloL` est alimenté l.5129-5131 via `seenLgts` + `bgValue` (dédup par
  `batiment_groupe_id`), calculé l.4902-4957 (`bgRncLots`, `bgBdnbResid`,
  `bgValue`).
- Les adresses social/bureaux sont **déjà** sorties du parc : `getEffectiveLog`
  retourne 0 (l.4830), exclues de `bgBdnbResid` (l.4935), et ne réservent pas
  `bg:`+bgid dans `seenLgts` (test `(rnc || getEffectiveLog(a) > 0)` l.5112).

➜ Conclusion : on ne touche QUE l'accumulation du numérateur ventes
(`iloAllV`/`effTot`). `secL`, `bgValue`, `seenLgts`, `getEffectiveLog` restent
intacts. Le parc et la dédup bgid §6 ne sont pas affectés.

---

## ETAPE 3 — Surface « strict ventes » dans index.html

| # | Lieu | Ligne(s) | Champ / source | Filtre social/bureaux DÉJÀ présent ? |
|---|------|----------|----------------|--------------------------------------|
| 1 | **Header secteur** (`secteur-resume`) | 4894 / 5099 / 5313 / 5342 / 5344-5348 | `effTot` ← `vpaOf` (`ventes_par_an_logement`) + fusions `mi`/`am` | **NON** — à modifier |
| 2 | **Sous-total ÎLOT** (`iloStats`, ventes/an + taux îlot) | 5034 (`iloAllV`) / 5099 / 5315-5319 | `effTot` (même `vpaOf`) | **NON** — découle de l'accumulation l.5099 |
| 3 | **Ligne d'adresse** (colonnes années + total + taux + classe) | 5076-5091 / 5305-5308 | `effV[y]`, `effTot`, `taux`/`cls` | **NON** (affichage par-ligne ; voir Etape 4) |
| 4 | **Répartition îlot/secteur** (`sctGenComputeIlots`) | 2670-2705 | `sumVpa` ← `nb_ventes_logement` / `ventes_par_an_logement` | **OUI** — exclut `social`/`bureaux` (l.2700) |
| 5 | **Modale GÉN/EXPORT** (summary, quotas, table A0) | 3689-3696 / 3548+ (`sctGenStart`) | dérive de `sctGenComputeIlots` (`ilot.nb_ventes`, `sctGenScoreSecteur` l.2742-2752) | **OUI** (hérité de #4) |
| 6 | **Label « Mode » modale** (strictes/brutes) | 3512-3515 (`sct-gen-mode-info`) ; 3694-3696 (`summary`) | détection `a.ventes_par_an_logement` présent | n/a (label texte) |
| 7 | **Toggle « 📊 Ventes strictes »** (bouton dashboard) | 828-832 / 2254-2266 (`secteurStrict`) | pilote `vpaOf` (strict vs brut) | n/a (bascule globale strict/brut) |

**Interprétation :** la divergence se résume à #1+#2+#3 (renderSecteur dashboard,
**sans** filtre) vs #4+#5 (sctGen/export, **avec** filtre). Le commit b91a33b a
aligné le **label** « strict » de la modale (#6) sur le **calcul réel** de
`sctGenComputeIlots` (qui est déjà marché-libre), pas sur le toggle UI ; il n'a
pas touché le header dashboard. C'est exactement la divergence à résorber.

---

## ETAPE 4 — Les lignes social/bureaux affichent-elles leurs ventes ?

OUI. Une adresse taguée `social`/`bureaux` est rendue comme toute autre ligne :
- colonnes années + total : `effV[y]` et `effTot` (l.5305-5306) sont affichés tels
  quels, sans masquage ;
- la cellule **logements** (l.5280-5289) affiche `0 (X)` (parc effectif nul, `X`
  = `nb_log_bdnb` informatif) — donc le parc est déjà neutralisé visuellement…
- … mais la cellule **ventes** ne l'est pas : si l'adresse a des mutations
  logement, le total `effTot` (l.5306 `<b>${effTot}</b>`) et le taux (l.5307)
  s'affichent normalement.

État actuel constaté : **ventes visibles ligne par ligne, mais comptées dans le
header** (cohérent avec l'absence de filtre Etape 2/3-#1). En plan futur on
pourra décider de griser/masquer/laisser-hors-total ces lignes ; le présent diag
constate seulement l'état.

---

## ETAPE 5 — Vérif chiffre (light × KV)

Mapping du tag : `assignments` du KV (`data/_kv_assign_dl.json`, clé top-level
`assignments`, 643 entrées) est indexé **par `cle`**, jointe aux adresses du light
par `a.cle` — exactement comme `secteurAssign[a.cle]` en prod. Fusions (`fusions`)
appliquées comme dans renderSecteur (`fusedSrc` + redistribution `mergedInto` /
`autoMerged`).

### Résultats (réplique EXACTE de l'agrégat header renderSecteur, mode strict)

| Grandeur | 5 ans | /an |
|---|---|---|
| Strict TOTAL (header actuel, sans filtre) | 2998,0 | **599,6** |
| dont social+bureaux (effTot, après redistribution fusions) | 97,0 | 19,4 |
| Marché libre header (599,6 − 19,4) | 2901,0 | **580,2** |

### Réplique EXACTE de l'agrégat répartition `sctGenComputeIlots`

| Grandeur | 5 ans | /an |
|---|---|---|
| sctGen INCLUS (= répartition) | 2842,0 | **568,4** |
| sctGen exclu social/bureaux | 156,0 | 31,2 |
| **sctGen grand total** (568,4 + 31,2) | 2998,0 | **599,6** |

### Lecture de l'identité 599,6 − X = 568,4

L'identité **599,6 − 31,2 = 568,4** est VRAIE, mais **interne à `sctGen`** : son
grand total est 599,6 et son exclusion est 31,2/an. Le diag précédent avait raison.

**MAIS attention (finding important) :** si on aligne le header **avec son propre
prédicat strict** (`effTot` après fusions), on obtient **580,2/an**, PAS 568,4.
L'écart 580,2 vs 568,4 (= 11,8/an, soit 59 ventes/5 ans) vient du **traitement
des fusions** :
- `renderSecteur` **redistribue** les ventes d'une adresse fusionnée (source)
  vers sa cible (`mergedInto`/`autoMerged`, l.4841-4867 + l.5077-5078). Une
  source taguée social/bureaux voit ses ventes **déplacées** sur une cible
  (souvent non-social) → elles ne sont plus comptées comme social/bureaux.
- `sctGen` **ne gère PAS les fusions du tout** : il somme `sumVpa(a)` adresse par
  adresse (l.2701/2703) → une source social/bureaux reste comptée en exclusion.

Mesuré : 104 ventes/5 ans de ventes strictes social/bureaux reposent sur des
adresses fusionnées-source (comptées par sctGen, redistribuées ailleurs par le
header) ; après compensation par les cibles elles-mêmes social/bureaux, le delta
net entre les deux exclusions est 156 − 97 = 59 ventes (= 11,8/an).

**Conséquence pour le plan :** « aligner le strict du dashboard sur le marché
libre » donnera **580,2/an** (header avec filtre, qui RESPECTE les fusions), et
**NON 568,4**. Le 568,4 est le chiffre `sctGen` qui ignore les fusions. Décision
de produit à prendre par Yann :
- (a) header marché-libre **fusions-aware** → 580,2 (cohérent avec le reste de
  renderSecteur, recommandé) ; OU
- (b) alignement strict header == répartition sctGen (568,4) → impliquerait soit
  d'ignorer les fusions dans le header (régression), soit d'apprendre les fusions
  à sctGen. Plus lourd.

Vérif `nb_ventes_logement` : sur 794 adresses avec ventes logement, 0 adresse
« brut-seulement » et 0 écart `nb_ventes_logement != Σ ventes_par_an_logement`.
Donc le choix `nb_ventes_logement` (sctGen) vs `Σ ventes_par_an_logement` (header)
n'introduit AUCUN écart ici ; tout l'écart 580,2/568,4 est dû aux fusions.

---

## ETAPE 6 — Harnais `scripts/test_render_secteur.js` (§7)

### Plages renderSecteur extraites EN DUR (`slice` 1-based)

`scripts/test_render_secteur.js` l.31-37 :
```js
const SRC = [
  slice(2058, 2062),   // ROT_COLOR + TYPE_OPTS
  slice(2084, 2086),   // esc
  slice(2088, 2092),   // secteurNorm
  slice(2105, 2146),   // sctTauxAnnuel..sctBadge
  slice(2148, 2484),   // renderSecteur (parc / strict / hr-actif / sctQ)
].join("\n\n");
```

> ⚠️ **GOTCHA connu (cf. MEMORY mp-cibles-horsrnc + commentaire l.24-30) :** ces
> plages sont **codées en dur** et re-cassent à chaque édition d'index.html
> (resync 2026-05-19 documenté l.27-30). **Déjà périmées** vs l'index.html
> courant : `renderSecteur` est aujourd'hui en l.4787-5351 (pas 2148-2484) et le
> module helpers sont décalés. Toute insertion de lignes (même 1 ligne dans
> renderSecteur) décale ces ranges → SyntaxError d'extraction. **À recaler
> AVANT/APRÈS la modif** (pré-requis pour que le harnais tourne tout court).

### Baselines liées aux ventes strictes

- l.193-195 — baseline ventes/an strict vs brut :
  ```js
  check(`ventes/an strict <= brut (${ven(curResume)} -> ${ven(sR)})`, ven(sR) <= ven(curResume));
  check(`ventes/an strict < brut (effet depend. exclues)`, ven(sR) < ven(curResume));
  ```
- l.281-329 — baseline parc `secL` (réplique EXACTE règle dédup bg:bgid) :
  ```js
  check(`secL == réplique EXACTE de la règle parc (${secL} == ${expected})`, secL === expected);
  ```

> ⚠️ **Point clé harnais :** le sandbox initialise `secteurAssign: {}` **vide**
> (l.59). Donc le harnais N'EXERCE PAS le tag social/bureaux : avec un assign
> vide, le filtre marché-libre ne retire rien → `ventes/an strict` resterait
> identique au test. Conséquences :
> 1. La baseline ventes/an strict (l.193-195) **ne changera PAS** après la modif
>    (rien à rebaser côté chiffre, tant que `secteurAssign={}` dans le test).
> 2. La nouvelle exclusion social/bureaux **ne sera pas couverte** par le harnais
>    actuel. Pour la tester il faudrait ajouter un cas avec un `secteurAssign`
>    peuplé (≥1 social + ≥1 bureaux avec ventes) et une baseline « marché libre
>    < total » — **à prévoir au plan, pas fait ici.**
> 3. La baseline parc `secL` (l.281-329) **ne doit pas bouger** (la modif ne
>    touche pas le parc) → sert de garde-fou anti-régression §6.

### À resynchroniser/rebaser APRÈS la modif (à ne pas faire maintenant)

1. **Recaler les `slice(...)`** l.32-36 sur les nouvelles lignes d'index.html
   (déjà nécessaire indépendamment : ranges périmés).
2. Vérifier que la baseline parc `secL` (l.328) reste verte (invariant §6).
3. (Optionnel mais recommandé) **ajouter** un cas de test avec `secteurAssign`
   peuplé pour couvrir l'exclusion social/bureaux ventes (sinon non-testée).

---

## CONCLUSION — Plan d'implémentation minimal (additif & réversible)

**Fichiers touchés : `index.html` (1 endroit) + `scripts/test_render_secteur.js`
(rebase ranges + baseline). AUCUNE donnée, aucun KV, aucun script Python.**

### Ordre des opérations

1. **`index.html` — header ventes (UNIQUE point fonctionnel).**
   Dans `renderSecteur`, conditionner l'accumulation du numérateur ventes au
   prédicat marché-libre, en réutilisant EXACTEMENT le test de sctGen
   `(secteurAssign[a.cle]||{}).type not in {social,bureaux}`. Le point chirurgical
   est l.5099 (`iloAllV += effTot`) : ne sommer `effTot` dans l'agrégat
   header/îlot que si l'adresse n'est pas social/bureaux. `effTot`/`effV`
   restent calculés (l.5076-5079) pour l'affichage ligne (Etape 4 inchangée), on
   ne neutralise que la **contribution à l'agrégat**.
   - ⚠️ NE PAS toucher `secL`, `iloL`, `bgValue`, `seenLgts`, `getEffectiveLog`
     (parc/dédup §6 — déjà marché-libre, doit rester bit-identique).
   - ⚠️ NE PAS toucher `vpaOf` ni le toggle `secteurStrict` (le brut reste brut ;
     le filtre social/bureaux est orthogonal au toggle strict/brut — décider si
     l'exclusion s'applique aussi en mode brut : recommandé OUI, pour cohérence
     avec sctGen qui exclut dans les 2 modes).
   - Réversible : un seul `if` ajouté, retrait trivial.

2. **Décision produit AVANT de coder (cf. Etape 5) :** le header marché-libre
   donnera **580,2/an** (fusions-aware), pas 568,4. Confirmer avec Yann que c'est
   le chiffre attendu (recommandé), sinon arbitrer le traitement des fusions.

3. **(Optionnel) Cohérence d'affichage ligne (Etape 4) :** décider de griser /
   marquer « hors total » les lignes social/bureaux. Purement cosmétique, séparable
   du chiffre. À ne faire que si Yann le demande.

4. **`scripts/test_render_secteur.js` — rebase :**
   a. Recaler les `slice(...)` l.32-36 sur la structure courante d'index.html
      (pré-requis, ranges déjà périmés).
   b. Vérifier baseline parc `secL` (l.328) verte = preuve §6 intact.
   c. Ajouter (recommandé) un cas `secteurAssign` peuplé pour couvrir l'exclusion.
   - Note : la baseline ventes/an strict (l.193-195) ne bouge pas tant que le
     sandbox garde `secteurAssign={}`.

5. **Dry-run/validation Yann** (règle §4.6) puis commit type
   `feat(secteur):` ou `fix(dl):` — pas de `[skip ci]` requis (pas de workflow lié).

### Invariants à préserver (garde-fous)
- Parc `secL` et dédup bgid (§6) : **bit-identique** avant/après.
- Brut (`ventes_par_an`) : inchangé (sauf si on étend l'exclusion au brut, à
  décider — recommandé pour cohérence sctGen).
- Affichage ligne par adresse : ventes toujours calculées (Etape 4) ; seul
  l'agrégat header/îlot change.
