# Diag MANCHE H Montchat (Phase 5, cloture marche-libre)

> READ-ONLY. PYTHONUTF8=1, ASCII-safe. **AUCUNE ecriture KV, AUCUN POST, AUCUN commit / git add.** Date : 2026-06-03.
> Namespace KV : `secteur_assignments:dauphine-lacassagne-montchat`. Light/DL/MP/index.html NON touches.
> Objet : calculer le **marche-libre Montchat** une fois les 505 tags KV (manches A->F) appliques, comme on l'a fait pour DL.
> Methode : replique fidele 2-passes de `renderSecteur()` (index.html) en memoire, light NON ecrit. Mirror KV = `data/_kv_assign_montchat.json` (505 assignments, **0 fusions manuelles**).
> Preuve directe = code lu dans index.html (n. de ligne cites). Le reste = calcul replique.

---

## VOLET 1 - Regle `getEffectiveLog` + marche-libre (code cite verbatim, index.html)

### 1.1 `getEffectiveLog(a)` - contribution PARC par type de tag (index.html l.5434-5441)

```js
const getEffectiveLog = a => {
  const as = secteurAssign[a.cle] || {};
  if (as.type === 'mono') return 1;
  if (as.type === 'social' || as.type === 'bureaux') return 0;
  // mixte : retourne nb_log_bdnb (parc total, comme copro_non_immat)
  return a.nb_log_bdnb;
};
```

| tag d'ANCRE | contribution PARC (hors-RNC) | preuve |
|---|---|---|
| `social` | **0** | l.5437 `return 0` |
| `bureaux` | **0** | l.5437 `return 0` (+ exclu en amont, voir 1.3) |
| `mono` | **1** | l.5436 `return 1` |
| `mixte` | **nb_log_bdnb** | l.5438-5440 (commentaire explicite : "parc total, comme copro_non_immat") -- PAS le marchand |
| `copro_non_immat` | **nb_log_bdnb** | fallthrough l.5440 `return a.nb_log_bdnb` |
| non-tagge | **nb_log_bdnb** | fallthrough l.5440 |
| **copro RNC** | **lots RNC** (`nb_lots_habitation`) | hors `getEffectiveLog` : path `rnc` l.5735-5742 (`bgRncLots` PRIORITAIRE, l.5525-5528) |

> Reponse a la question du brief : `mixte` -> **nb_log_bdnb** (parc total), PAS le marchand. C'est le meme retour que `copro_non_immat` / non-tagge. La distinction marchand/total ne joue qu'a l'AFFICHAGE de la cellule logement, pas dans le parc.

### 1.2 Marche-libre - exclusion des ventes social/bureaux (index.html l.5688-5719)

```js
const effTot = ANS.reduce((s, y) => s + effV[y], 0);
// [MARCHE LIBRE 2026-05-31] exclusion par le tag de l'ANCRE de fusion ...
// GATE secteurStrict : le "marche libre" ne s'applique qu'au mode STRICT (toggle ON).
const _mlExcl = secteurStrict && (as.type === 'social' || as.type === 'bureaux');
...
iloAllV += _mlExcl ? 0 : effTot;        // l.5719
```

- **Test d'exclusion EXACT** : `as.type === 'social' || as.type === 'bureaux'` (l.5697), **juge par le tag de l'ANCRE** (`as = secteurAssign[a.cle]`, l.5669) -- la boucle ne voit que les ancres, les sources fusionnees sont ecartees plus haut (`if (fusedSrc[a.cle]) return;` l.5574).
- **fusion-aware** : `effTot` agrege deja les ventes pliees des sources (`mi`=mergedInto manuel + `am`=autoMerged BDNB, l.5684-5687) AVANT exclusion.
- **GATE `secteurStrict`** : `_mlExcl` n'est vrai qu'en mode strict (toggle ON, defaut). En BRUT (`secteurStrict=false`) `_mlExcl` est toujours `false` -> tout-inclus. (Note : difference avec sctGen, qui exclut social/bureaux dans les 2 modes -- l.2836.)
- Agregat header : `secAllV += iloAllV` (l.5944) ; `secVAn = secAllV / 5` ; taux `sctTauxAnnuel(v,l)` = `Math.round(v/l/5*1000)/10` (l.5344).

Replique cote `sctGenComputeIlots` (l.2824-2839) : meme test `tg !== 'social' && tg !== 'bureaux'`, fusion-aware (`vTot = sumVpa(a) + foldedVpa[a.cle]`, l.2835), source ecartee `if (fusedSrc[a.cle]) continue;` (l.2825).

### 1.3 Confirmation : seuls social/bureaux exclus du marche-libre

OUI. `mono` / `copro_non_immat` / `mixte` / non-tagge / copro RNC tombent tous dans la branche `else` (l.5719 `iloAllV += effTot`) -> **INCLUS** dans le marche-libre. Seuls `social` et `bureaux` sont mis a 0. (Note : `bureaux` est aussi exclu du **parc RNC** des l.5516 `if (...type === 'bureaux') return;` et du path `bg:` l.5731 -- double garde.)

---

## VOLET 2 - 505 tags appliques au light Montchat (en memoire) + calcul

> Replique fidele de `renderSecteur()` (parc dedup `bg:bgid` + marche-libre fusion-aware). Light NON ecrit.
> **Validation de la replique** : sur `secteurAssign={}` (BRUT), elle reproduit EXACTEMENT le baseline annonce : **parc 15 848, ventes/an 186,4** (== test_render_secteur.js). C'est la preuve que la replique est isomorphe a l'UI.
> Detail technique : `renderSecteur` INCLUT les adresses `_ilot=='X'` (bucket "Ilot hors secteur") et "non assigne" dans le header secAllV/secL (l.5615-5620) -- contrairement a `sctGen` qui les SKIP (l.2828). La replique respecte ce comportement (sinon parc=15 196, ecart 652 = le bucket X).

### 2.1 Parc effectif final

| | parc `secL` | ventes/an (marche-libre) | taux %/an |
|---|--:|--:|--:|
| **BRUT** (tags hors light, test_render) | **15 848** | **186,4** | 1,2 |
| **LIVE** (505 tags appliques) | **13 815** | **181,6** | **1,3** |
| **Delta** | **-2 033** | **-4,8** | +0,1 |

### 2.2 Ventilation de la baisse parc (-2 033), dedup-aware (`bg:bgid`)

Decomposition incrementale (brut -> +social -> +bureaux -> +mono -> +copro_non_immat -> +mixte) :

| Type applique | parc apres | delta du pas | regle |
|---|--:|--:|---|
| social (105) -> 0 | 14 152 | **-1 696** | `getEffectiveLog=0` ; raw Sigma nb_log_bdnb = 1 833, mais -137 sont des bgid deja partages (dedup) |
| bureaux (34) -> 0 | 14 152 | **0** | les bgid bureaux ne portaient deja AUCUN parc residentiel (usage non-resid ou parc porte par un co-occupant resid du meme bgid) |
| mono (261) -> 1 | 13 815 | **-337** | 61 mono `nb_log_bdnb>1` ramenes a 1 (raw -440 dont -103 dedup) |
| copro_non_immat (86) | 13 815 | **0** | conserve `nb_log_bdnb` (neutre) |
| mixte (19) | 13 815 | **0** | conserve `nb_log_bdnb` (neutre) |
| **TOTAL** | **13 815** | **-2 033** | |

> La baisse est portee a **83 % par le social** (-1 696) et **17 % par le mono** (-337). bureaux/copro_non_immat/mixte = strictement parc-neutres.

### 2.3 Marche-libre ventes/an final + baisse social/bureaux

| | ventes 5 ans | /an |
|---|--:|--:|
| BRUT (tout inclus) | 932,0 | 186,4 |
| dont exclu **social** (5 ventes 5y) | 5,0 | 1,0 |
| dont exclu **bureaux** (19 ventes 5y) | 19,0 | 3,8 |
| **Marche-libre LIVE** (908 / 5) | **908,0** | **181,6** |

- Baisse marche-libre = **-24 ventes/5y = -4,8/an**. **Confirme l'ordre ~-5 annonce en manche F** (manche F annoncait "social -> 5 ventes retirees" ; ici le total social+bureaux = 4,8/an, dont 1,0 social + 3,8 bureaux).
- Le gros de l'exclusion ventes vient des **bureaux** (3,8/an), pas du social (1,0/an) : logique, les social Montchat sont du parc bailleur a tres faible rotation (mut/an ~0 sur l'ecrasante majorite, cf manche F).

### 2.4 Taux secteur final

`secTaux = Math.round(secAllV / secL / 5 * 1000)/10` = `Math.round(908 / 13815 / 5 * 1000)/10` = **1,3 %/an**. (Brut : 932/15848/5 = 1,2 %/an.) Le taux MONTE legerement car le parc baisse (-12,8 %) plus vite que les ventes (-2,6 %).

### 2.5 Application par ANCRE + 0 double-comptage

- Tag applique par `secteurAssign[a.cle]` ou `a.cle` = l'ancre (les sources fusionnees ecartees l.5574). Montchat = **0 fusion manuelle** (KV `fusions` vide) ; restent **232 fusions auto-BDNB** (`_fusion_auto`+`_fusion_cible`), gerees identiquement a l'UI (`am`/`autoMerged`).
- **0 double-comptage prouve** : parc dedup par `bg:bgid` (`seenLgts`, l.5749) ; meme bati compte 1x. La replique sur BRUT reproduit exactement 15 848 = test_render -> dedup correcte.

---

## VOLET 3 - Comparaison DL + coherence

> DL calcule avec la MEME replique (light `secteur_dauphine_lacassagne_light.json`, KV `_kv_assign_dl.json` = 645 assignments, 6 fusions manuelles, mode strict).
> Validation : la replique reproduit **DL BRUT = 599,6/an** EXACTEMENT (== "header strict total" du diag DL `data/diag_strict_marche_libre_dl.md` etape 5). Isomorphisme confirme sur les 2 secteurs.

| Secteur | parc BRUT | parc LIVE | ventes/an BRUT | **marche-libre LIVE /an** | taux LIVE %/an | excl soc/bur /an |
|---|--:|--:|--:|--:|--:|--:|
| **DL** | 22 381 | 18 085 | 599,6 | **584,6** | 3,2 | 13,2 |
| **Montchat** | 15 848 | 13 815 | 186,4 | **181,6** | 1,3 | 4,8 |

> Note DL : la consigne citait 578,4/an comme reference DL. La replique sur le KV DL **courant** (645 assignments, dont des `cible_0vente_*` qui ne sont PAS exclus du marche-libre, et la croissance des tags depuis le 31/05) donne **584,6/an** -- le chiffre flotte avec l'etat KV (le 578,4/580,2 etait un snapshot 2026-05-31). L'ecart est attendu et coherent (drift KV), pas une anomalie de calcul. Les invariants (parc dedup, 599,6 brut) sont reproduits a l'identique.

### Coherence (verifie)

1. **Social bien exclu** : les 105 social Montchat -> parc 0 (-1 696 lgts dedup) ET ventes hors marche-libre (-1,0/an). Idem DL. OK.
2. **0 double-comptage** : BRUT replique == test_render (15 848 Montchat, 599,6 DL) -> dedup `bg:bgid` exacte sur les 2 secteurs. OK.
3. **Ordres de grandeur plausibles** : Montchat (quartier voisin, plus petit) ~ 70 % du parc DL et ~ 31 % des ventes/an DL. Taux Montchat 1,3 %/an << DL 3,2 %/an. Coherent : Montchat porte beaucoup de **parc social/bailleur a tres faible rotation** (105 social + 19 mixte = 124 ancres bailleurs, mut/an ~0 d'apres manche F) -> denominateur parc effectif eleve relativement aux ventes. Pas d'anomalie.
4. **Pas d'ecart suspect** : le parc baisse bien (-2 033, non nul) et le marche-libre n'est PAS identique au brut (-4,8/an). Les social ont tres peu de ventes (5/5y) -> coherent avec un parc bailleur. KV bien applique par ancre (BRUT vide reproduit le baseline). OK.

---

## Tableau de bord CLOTURE Montchat (etat LIVE = 505 tags appliques)

> LIVE = tags KV appliques (calcul UI). Le **light brut** servi reste 15 848 / 932 (tags KV-only, hors light) -- c'est ce que voit `test_render`. La difference brut/LIVE est entierement portee par `secteurAssign` au render.

| Type rendu | n ancres | parc effectif | ventes/an (dans marche-libre) | ventes/an (exclues) |
|---|--:|--:|--:|--:|
| non-tagge (incl. copro RNC) | 701 | 12 137 | 155,0 | 0 |
| copro_non_immat | 86 | 1 007 | 10,0 | 0 |
| mixte | 19 | 393 | 0,8 | 0 |
| mono | 259 | 278 | 15,8 | 0 |
| social | 105 | 0 | 0 | 1,0 |
| bureaux | 28* | 0 | 0 | 3,8 |
| **TOTAL marche-libre** | | **13 815** | **181,6** | **(4,8 hors-total)** |

(*) 28 ancres bureaux rendues : sur 34 tags bureaux, 6 sont des sources auto-fusionnees (ecartees du rendu, plies sur leur ancre) ; idem social 105->100 rendues, mono 261->259, mixte 19->19. Les comptes "n ancres" sont post-fusion-auto BDNB (232 sources ecartees au total).

---

## Synthese

- **Parc effectif final Montchat = 13 815 lgts** (vs 15 848 brut, **-2 033** : social -1 696 + mono -337 ; bureaux/copro_non_immat/mixte neutres).
- **Marche-libre final = 181,6 ventes/an** (vs 186,4 brut, **-4,8/an** = social 1,0 + bureaux 3,8 ; confirme ~-5 manche F).
- **Taux secteur LIVE = 1,3 %/an** (vs 1,2 brut).
- **vs DL** : DL LIVE = 18 085 lgts / 584,6/an / 3,2 %/an. Montchat ~70 % du parc DL, ~31 % des ventes/an, taux 2,5x plus bas (parc bailleur faible rotation).
- **Coherence OK** : social exclu (parc 0 + ventes hors marche-libre), 0 double-comptage (BRUT replique == test_render 15 848 & DL 599,6), KV applique par ancre, ordres de grandeur plausibles. Aucune anomalie.

*Aucune ecriture KV, aucun commit dans cette manche (READ-ONLY). Seul fichier ecrit : ce rapport.*
