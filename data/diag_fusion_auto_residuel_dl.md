# Diag — Fusion auto résiduelle (façades multi-entrées même bgid non fusionnées) — secteur Dauphiné-Lacassagne (DL)

> **READ-ONLY.** Aucun fichier de données/code modifié, aucun commit, aucun fix. Seul ce rapport est écrit.
> Source : `data/secteur_dauphine_lacassagne_light.json` (light courant) + KV `data/_kv_assign_dl.json`.
> Date : 2026-05-31.

---

## Méthodologie & conventions

- **Parité** : numéro extrait de `cle` (partie avant le 1er `|`), regex `^(\d+)` → partie entière. Suffixes `B`/`T`/`bis`/`A` ignorés (`13B`→13→impair, `121A`→121→impair). Pas de numéro entier exploitable → parité `n/d`.
- **Secondaire de fusion** (NON rendu) : `_fusion_auto` truthy **ET** présence d'une cible (`_fusion_cible` **ou** `_fusion_auto_target`).
- **Unité rendue** : adresse qui n'est PAS un secondaire de fusion (donc : ancre `_fusion_auto_sources`, ou adresse normale sans fusion).
- **Groupe** : ensemble des unités rendues partageant le même `batiment_groupe_id` (bgid). Adresses sans bgid exclues (7 adresses).
- **Syndic exploitable** : non null, non vide, hors {`non connu`, `non renseigné`, `inconnu`} (insensible à la casse/espaces).
- **Type KV** : `assignments[cle].type` dans `data/_kv_assign_dl.json`.

### Note sur les fusions chaînées
4 adresses sont à la fois ancres (`_fusion_auto_sources`) **et** secondaires (`_fusion_auto`+cible) — fusions chaînées :
`25 ST ANTOINE`, `15 ETIENNE RICHERAND`, `27 AUBIGNY`, `4 VILLETTE`.
Par la règle déterministe de la tâche (secondaire = `_fusion_auto`+cible), elles sont classées **secondaires** (non rendues). Cela n'affecte aucun groupe retenu en E1.

---

## E1 — RECENSEMENT

| Mesure | Valeur |
|---|---|
| Adresses totales | 1385 |
| Secondaires de fusion (exclus) | 459 |
| Unités rendues (toutes) | 926 |
| Unités rendues **avec bgid** | **919** |
| Adresses sans bgid (exclues) | 7 |
| bgid distincts (parmi unités rendues) | 854 |
| **bgid produisant >1 unité rendue** | **61** |
| **Unités totales sur ces 61 bgid** | **126** |

Distribution de la taille des groupes (unités rendues par bgid) :

| Unités/bgid | Nb de bgid |
|---|---|
| 1 | 793 |
| 2 | 57 |
| 3 | 4 |

### Écart vs l'attendu (~625)
Le contexte attend **~625 unités**. La mesure « unités rendues avec bgid » est **919**, soit un écart de ~+294. La cible ~625 ne correspond précisément à **aucune** des définitions testées :

| Définition | Compte |
|---|---|
| Unités rendues (incl. sans bgid) | 926 |
| Unités rendues hors `_ilot='X'` | 898 |
| Unités rendues avec bgid hors `_ilot='X'` | 891 |
| bgid distincts (unités, hors X) | 829 |
| bgid distincts (unités, tous) | 854 |

Hypothèses d'explication de l'écart (non tranché, ne change rien à l'analyse qui suit) :
- Le ~625 est probablement un **chiffre historique** (ancien snapshot du light, antérieur aux nombreux fix `_fusion_*`, RE-FUSE, INJECT documentés dans MEMORY.md) — le light courant a vu de nombreuses injections/refusions depuis.
- Ou il vise un sous-périmètre (ex. unités **avec immat** = 639, ou unités hors `_ilot='X'` filtrées encore davantage).
- L'exclusion `_ilot='X'` (39 adresses, dont 28 unités rendues) et les 7 sans-bgid ne suffisent pas à combler l'écart.

**Le périmètre de travail retenu pour E2→E5 est robuste et indépendant de ce chiffre : 61 bgid éclatés / 126 unités rendues.**

---

## E2 — COLLECTE PAR UNITÉ

Pour chacune des 126 unités des 61 bgid retenus, collecté : `cle`, parité, `numero_immatriculation`, `syndic` (exploitable ou non), `nb_lots_habitation`, `nb_log_bdnb`, `nb_ventes_logement`, `secteurAssign[cle].type`, `_bdnb_match`. Données agrégées en E3/E4 et échantillonnées en E5.

---

## E3 — STRATIFICATION

**Ordre de test déterministe appliqué à chaque groupe :**
1. ≥2 immats distincts non null → **S4**
2. sinon, tous les immats non null **et** identiques (1 seul immat couvre toutes les unités) → **S1**
3. sinon, syndic exploitable identique sur toutes les unités → **S2**
4. sinon → **S3**

| Strate | Définition | Groupes | Unités |
|---|---|---|---|
| **S1** | Toutes unités même immat non null → 1 copro, fusion SÛRE parc-neutre | **5** | **10** |
| **S2** | Pas S1, syndic exploitable identique sur toutes → probablement 1 copro | **9** | **19** |
| **S3** | Ni S1 ni S2 → ambigu, preuve terrain nécessaire | **46** | **95** |
| **S4** | ≥2 immats distincts non null → 2+ copros, NE PAS fuser | **1** | **2** |
| **TOTAL** | | **61** | **126** |

Le total **boucle avec E1** (61 groupes / 126 unités). ✓

### Détail S3
S3 regroupe deux sous-cas (le pas 4 est un fourre-tout) :
- **S3-mixte** (correspond à la définition stricte « parité MIXTE + immats null/absents ») : **34 groupes**. Cas d'angle classiques (pair × impair sur un même bgid).
- **S3-résiduel** (même parité, immats null sur les sans-immat, **pas** de syndic commun exploitable) : **12 groupes**. Souvent : 1 unité immatriculée + 1 unité B/T sans immat ni syndic, ou 2 unités B-suffixées toutes deux sans immat/syndic.

---

## E4 — NEUTRALITÉ PARC

**Choix de l'ancre** d'un groupe (déterministe) : unité avec le plus de `nb_lots_habitation`, puis le plus de `nb_log_bdnb`, puis la plus petite `cle` (ordre lexicographique).

### Démonstration de neutralité parc (S1)
Le parc affiché (`secL` dans `renderSecteur`) compte chaque bâtiment **une seule fois via la clé `bg:<bgid>`** (PIPELINE.md §6). Les lots attribués à un bgid = somme lots RNC de la copro (ou `nb_log_bdnb` fallback), **indépendamment du nombre de lignes** portant ce bgid. Vérification par groupe S1 : à l'intérieur de chaque groupe, `nb_lots_habitation` et `nb_log_bdnb` sont **identiques sur toutes les unités** (même copro, même bâti) :

| bgid (suffixe) | lots (toutes unités) | bdnb (toutes unités) | ancre retenue | ventes relocalisées |
|---|---|---|---|---|
| VFY6-RGM1 | 76 | 41 | `11B\|RUE\|ST MAXIMIN` | 5 |
| QRF3-15LG | 27 | 29 | `4\|RUE\|STE ANNE DE BARABAN` | 4 |
| FUDZ-T2KQ | 41 | 40 | `19B\|RUE\|ST ANTOINE` | 6 |
| G1YT-XLZF | 25 | 25 | `121A\|RUE\|ANTOINE CHARIAL` | 1 |
| 3RN1-KX5T | 60 | 61 | `24\|RUE\|CLAUDIUS PIONCHON` | 2 |
| **TOTAL S1** | | | | **18** |

Regrouper les lignes ne touche donc **ni `secL` (parc) ni le total ventes** ; le seul effet visible est le **regroupement de lignes UI** : les **18 ventes_logement** des unités non-ancre seraient relocalisées sous l'ancre (somme inchangée à l'échelle secteur).

### Hypothèse S2
Même raisonnement (1 copro probable). Détail par groupe :

| bgid (suffixe) | ventes relocalisées | commentaire |
|---|---|---|
| 96UR-3947 | 0 | 28 ETIENNE RICHERAND porte déjà les 19 ventes (= ancre) |
| 82K8-7HRF | 0 | 22 DAUPHINE = ancre (2 ventes) |
| TX3N-8L23 | 0 | 24 ST PHILIPPE = ancre (1 vente) |
| 7CKJ-3Q9D | 0 | toutes vlog=0 |
| N4HU-YD2U | 0 | toutes vlog=0 |
| 7F9F-2TDS | 0 | toutes vlog=0 |
| Y7QM-A3JB | 0 | 36 DAUPHINE = ancre (1 vente) |
| PDHN-JM11 | 0 | toutes vlog=0 |
| 64PQ-UJ5S | 0 | toutes vlog=0 |
| **TOTAL S2** | **0** | |

**S2 relocalise 0 vente** : dans chaque groupe S2, l'unité immatriculée (ou la plus grosse) — qui devient l'ancre — porte déjà l'intégralité des ventes ; les unités sans immat (B-suffixes, façades secondaires) ont toutes `nb_ventes_logement = 0`. Parc strictement neutre (lots/bdnb identiques, bgid-keyé).

**Total ventes relocalisées S1+S2 = 18** (toutes en S1). Aucun changement de parc ni de total ventes secteur dans les deux strates.

---

## E5 — ÉCHANTILLONS (5/strate, ou tous si <5)

### S1 (les 5 groupes — exhaustif)
| bgid | cles | immat | syndic | parités | lots | bdnb | vlog | type KV |
|---|---|---|---|---|---|---|---|---|
| VFY6-RGM1 | 23 / 11B ST MAXIMIN | AB4738928 | FONCIA SAINT LOUIS | impair/impair | 76 | 41 | 5/0 | None / cible_0vente_active |
| QRF3-15LG | 4 / 6B STE ANNE DE BARABAN | AE4069597 | EURL GROS PROXIMITE | pair/pair | 27 | 29 | 5/4 | None / None |
| FUDZ-T2KQ | 19 / 19B ST ANTOINE | AA3187663 | PICHET IMMOBILIER | impair/impair | 41 | 40 | 6/7 | None / None |
| G1YT-XLZF | 90 / 121A ANTOINE CHARIAL | AA9271602 | REGIE LESTRA | pair/impair | 25 | 25 | 1/0 | None / social |
| 3RN1-KX5T | 24 / 28B CLAUDIUS PIONCHON | AH7871353 | GRANDLYON HABITAT | pair/pair | 60 | 61 | 6/2 | mixte / mixte |

> Note : G1YT-XLZF est S1 (même immat AA9271602) **bien que de parité mixte** (90 pair / 121A impair) — l'immat commun prime, fusion sûre.

### S2 (5 premiers sur 9)
| bgid | cles | immats | syndic commun | lots | bdnb | vlog | type KV |
|---|---|---|---|---|---|---|---|
| 96UR-3947 | 28 ETIENNE RICHERAND / 11 TERNOIS | AA0358655 / None | GRANDLYON HABITAT | 211/None | 211 | 19/0 | mixte / copro_non_immat |
| 82K8-7HRF | 22 / 21 DAUPHINE | AI7701238 / None | REGIE DE L'OPERA | 22/None | 22 | 2/0 | None / mono |
| TX3N-8L23 | 24 / 23 ST PHILIPPE | AA5976667 / None | FONCIERE HAUSSMANN | 6/None | 7 | 1/0 | None / bureaux |
| 7CKJ-3Q9D | 70/72 MAURICE FLANDIN, 75 VILLETTE | None/None/AF4080479 | ELYGESTION | 2 | 2 | 0/0/0 | bureaux ×3 |
| N4HU-YD2U | 29 ETIENNE RICHERAND / 43 AUBIGNY | AG9619537 / None | OPH METROPOLE LYON | 65/None | 64 | 0/0 | social / social |

### S3 (5 premiers sur 46)
| bgid | cles | immats | syndic | parités | lots | bdnb | vlog | type KV |
|---|---|---|---|---|---|---|---|---|
| 27SZ-1D73 | 46 / 47 GEORGES POMPIDOU | AB9345703 / None | FONCIA SAINT LOUIS / — | pair/impair | 74/None | 19 | 7/0 | None / mono |
| NEHV-8KAS | 8 / 8B FRANCOIS GILLET | AA5973367 / None | REGIE DES GONES / — | pair/pair | 52/None | 52 | 3/11 | mixte / copro_non_immat |
| M1N7-38NB | 2 / 3 FRANCOIS GILLET | None / AA1827336 | — / REGIE DES GONES | pair/impair | None/30 | 32 | 0/7 | mono / mono |
| 5ABF-Q89H | 36 / 37 TURBIL | AB8983389 / None | LYMMOBILIER / — | pair/impair | 17/None | 17 | 6/0 | None / copro_non_immat |
| L2LW-69P8 | 6 / 7 LACASSAGNE | AF5613245 / None | REGIE PEDRINI / — | pair/impair | 142/None | None | 0/0 | bureaux / copro_non_immat |

#### S3-résiduel (même parité, 5 premiers sur 12)
| bgid | cles | immats | syndic | bdnb | vlog | type KV |
|---|---|---|---|---|---|---|
| NEHV-8KAS | 8 / 8B FRANCOIS GILLET | AA5973367 / None | REGIE DES GONES / — | 52 | 3/11 | mixte / copro_non_immat |
| 75JZ-QX89 | 11 / 11B DAUPHINE | None / None | — / — | 103 | 0/0 | social / social |
| M1EY-SXFT | 15 / 15B CLAUDIUS PIONCHON | None / None | — / — | 44 | 0/0 | social / social |
| EBHY-Y74D | 155 / 185T FELIX FAURE | None / None | — / — | 67 | 0/4 | social / bureaux |
| 1MR8-BM8W | 17 / 17B CLAUDIUS PIONCHON | None / None | — / — | 1 | 0/0 | mono / mono |

### S4 (le seul groupe — exhaustif)
| bgid | cles | immats | syndic | parités | lots | bdnb | vlog | type KV |
|---|---|---|---|---|---|---|---|---|
| EQDH-V7QL | 11 / 12 ESPERANCE | AA9690066 / AA8146995 | LYMMOBILIER / REGIE CENTRALE | impair/pair | 25/34 | 25 | 5/0 | None / cible_0vente_active |

> S4 : 2 immats distincts (AA9690066 ≠ AA8146995) + 2 syndics distincts + parités opposées → **2 copros physiquement distinctes** sur un même bgid BDNB. NE PAS fuser.

---

## CONCLUSION

### Volumes
- **Fusionnables EN SÛRETÉ (S1) : 5 groupes / 10 unités** → 5 fusions, parc strictement neutre, **18 ventes relocalisées** sous ancre.
- **Fusionnables probables (S2) : 9 groupes / 19 unités** → +9 fusions, parc neutre, **0 vente relocalisée** (les ancres portent déjà toutes les ventes).
- **S1+S2 combiné : 14 groupes / 29 unités, 18 ventes relocalisées, 0 changement de parc/total ventes.**
- **Ambigus (S3) : 46 groupes / 95 unités** — 34 d'angle (parité mixte) + 12 résiduels — **preuve terrain nécessaire** (parcelle DVF, ref_cad RNC live, pivot BDNB `l_libelle_adr`). Ne pas fuser à l'aveugle : des cas comme 6/7 LACASSAGNE (bureaux × copro_non_immat) ou 155/185T FELIX FAURE (social × bureaux) sont vraisemblablement des **bâtis distincts** malgré bgid commun.
- **À exclure (S4) : 1 groupe / 2 unités** — 2 copros distinctes (11/12 ESPERANCE) — **ne jamais fuser**.

### Avis sur un `fix_fusion_*` additif + portage make_light
**Oui, recommandé pour S1 ; oui sous réserve pour S2 ; non pour S3/S4.**

1. **S1 (5 groupes)** : critère **immat identique non null** = preuve directe « 1 seule copro RNC ». Un `fix_fusion_*` additif sur le light courant (fusionner les 10 unités en 5 ancres, relocaliser les 18 ventes, label étendu) est **sûr, parc-neutre, déterministe**. Le portage dans make_light est trivial et sûr : **assouplir la garde anti-parité-mixte uniquement quand `numero_immatriculation` est identique non null** (cf. G1YT-XLZF, parité mixte mais immat commun = vrai positif que la garde actuelle rate). C'est la meilleure voie.

2. **S2 (9 groupes)** : critère **syndic commun exploitable** = probable mais pas certain (un même syndic peut gérer 2 copros voisines). Volume faible et **0 vente relocalisée** → faible ROI et faible risque, mais à **valider au cas par cas** (les 9 sont listés en E4). Un assouplissement make_light sur syndic seul est plus risqué que sur immat ; à n'envisager qu'avec garde supplémentaire (même `nb_log_bdnb`, déjà vrai ici).

3. **S3/S4 (47 groupes)** : **NE PAS automatiser**. La parité mixte sans immat commun = exactement la garde d'angle que make_light pose volontairement (faux positifs documentés MEMORY.md : 58→69 GRENELLE pair/impair côtés opposés). Ces cas relèvent de la **correction manuelle terrain** (patterns Cambronne/Fondary/INVERSION_ANCRE), pas d'un critère automatique.

### Synthèse chiffrée
| | Groupes | Unités | Ventes reloc. | Δ parc | Action |
|---|---|---|---|---|---|
| S1 | 5 | 10 | 18 | 0 | **fix + portage make_light (garde immat)** |
| S2 | 9 | 19 | 0 | 0 | fix au cas par cas (optionnel) |
| S3 | 46 | 95 | — | — | manuel terrain (pas d'auto) |
| S4 | 1 | 2 | — | — | exclure |

> **Rappel : ceci est un diagnostic. AUCUN fix appliqué, AUCUNE écriture hors ce rapport, AUCUN commit.**
