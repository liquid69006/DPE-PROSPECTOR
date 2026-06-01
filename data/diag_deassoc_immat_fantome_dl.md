# Diagnostic — Dé-association du set complet « immat fantôme via bgid » (secteur Dauphiné-Lacassagne)

> **READ-ONLY.** Date : 2026-06-01. AUCUN fichier de données/code modifié, AUCUN commit, AUCUN fix. Seul ce rapport est écrit.
> Source light : `data/secteur_dauphine_lacassagne_light.json` (light **courant**, post-commit 71f2ca3 = fusion S1 appliquée).
> Source KV : `data/_kv_assign_dl.json` (clé `assignments`).
> Diags amont lus : `data/diag_s1_immat_provenance_dl.md`, `data/diag_fusion_auto_residuel_dl.md`.
> **Preuve LIVE disponible (réseau OK)** : toutes les vérifs `l_libelle_adr` / parcelle / BAN ci-dessous sont **LIVE** (BDNB `api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet`, `rel_batiment_groupe_parcelle`, `rel_batiment_groupe_adresse` ; BAN `api-adresse.data.gouv.fr` ; RNC tabular-api `3ea8e2c3-…`). Quand une déduction est purement locale, c'est signalé.

---

## Synthèse exécutive

| Question | Réponse |
|---|---|
| **E1 — taille du set** | **23 adresses** portent un immat hérité via bgid (`numero_immatriculation` non null, `_bdnb_match≠immat`, cle absente de `coproprietes[]`). Conforme à l'attendu (~23). |
| **E2 — répartition verdict** | **13 LÉGITIMES** (bgid déclare le n° en `l_libelle_adr`) + **10 FANTÔMES** (bgid ne déclare PAS le n°). Sur les 10 fantômes : **3 RE-POINT** (impasse de l'Ordre) + **7 RETRAIT** (pas de vrai bgid distinct). |
| **E3 — doublons d'îlot** | **1 vrai doublon cross-îlot résolu** : 121 CHARIAL (vrai îlot 34 / phantom îlot 39). 11B ST MAXIMIN = quasi-doublon îlots adjacents 66/67. Les autres fantômes partagent l'îlot de leur faux bâti (pas de cross-îlot). |
| **E4 — impact chiffré** | **Δ ventes = 0, Δ secVAn = 0 (597,8 inchangé), Δ parc = 0** (variante recommandée). Les 10 fantômes ont **TOUS `nb_ventes_logement = 0`**. L'immat/lots fantôme est **display-only** (le parc lit les lots dans `coproprietes[]`, pas sur la ligne adresse). |
| **E5 — cause racine** | Le writer concret est **`scripts/_apply_propag_immat_21suff_dl.py`** (marker `fix_propag_immat_21suff_dl_2026-05-23`), pas make_light directement. L'origine du signal reste le bgid (`numero_immat_principal` snapshot BDNB). Garde manquante = filtre `l_libelle_adr` (n° déclaré par le bgid) — à poser **dans le triage 85-suffixes** (en amont) et/ou dans make_light. |

---

## E1 — ÉNUMÉRATION DU SET COMPLET (23 adresses)

Critère exact : `numero_immatriculation` non null **ET** `_bdnb_match ≠ "immat"` **ET** `cle` absente de `coproprietes[]`. Total = **23** (dont 19 `num_voie`, 3 `bdnb_orphelin`, 1 `immat_horsrnc_fix`).

> **Note d'état** : depuis le snapshot `.prefusions1.bak` du diag S1, le light courant a fusionné la plupart de ces lignes. **21/23 sont aujourd'hui des secondaires de fusion** (`_fusion_auto`+`_fusion_cible`, non rendues comme nœud propre) ; **seules 2 restent rendues** : `11B|ST MAXIMIN` et `121A|ANTOINE CHARIAL` (les 2 fantômes S1, laissés hors fusion par le garde `DECLARED_S1`). Le set de dé-association reste néanmoins l'ensemble des **lignes portant l'immat fantôme** : retirer l'immat hérité indu, qu'elles soient rendues ou déjà fusionnées (une ligne fusionnée porte toujours son `numero_immatriculation` fantôme, visible si l'UI la déplie / sur les recalculs futurs).

| # | cle | bgid (court) | immat (hérité) | lots hér. | `_bdnb_match` | KV type | vlog (`nb_ventes_logement`) | îlot light | îlot KV | rendue ? | cible fusion |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `10B\|RUE\|FREDERIC MISTRAL` | YKPV-1S76 | AA1991173 | 37 | num_voie | None | 0 | 32 | None | fusée | `10\|FREDERIC MISTRAL` |
| 2 | `11B\|RUE\|PROFESSEUR PAUL SISLEY` | P7TQ-TZ2P | AA0012898 | 225 | num_voie | None | 0 | 74 | None | fusée | `7B\|PROF PAUL SISLEY` |
| 3 | `11B\|RUE\|ST MAXIMIN` | VFY6-RGM1 | AB4738928 | 76 | num_voie | cible_0vente_active | 0 | 67 | None | **rendue** | — |
| 4 | `11\|IMPASSE\|ORDRE` | W8DF-4GCQ | AB8922999 | 49 | bdnb_orphelin | None | 0 | 47 | None | fusée | `118\|BARABAN` |
| 5 | `121A\|RUE\|ANTOINE CHARIAL` | G1YT-XLZF | AA9271602 | 25 | num_voie | social | 0 | 39 | None | **rendue** | — |
| 6 | `121B\|RUE\|ANTOINE CHARIAL` | G1YT-XLZF | AA9271602 | 25 | num_voie | social | 0 | 39 | None | fusée | `121A\|CHARIAL` |
| 7 | `121C\|RUE\|ANTOINE CHARIAL` | G1YT-XLZF | AA9271602 | 25 | num_voie | social | 0 | 39 | None | fusée | `121A\|CHARIAL` |
| 8 | `121D\|RUE\|ANTOINE CHARIAL` | G1YT-XLZF | AA9271602 | 25 | num_voie | social | 0 | 39 | None | fusée | `121A\|CHARIAL` |
| 9 | `130B\|RUE\|BARABAN` | 4XAJ-TVQA | AE1293612 | 60 | num_voie | None | 0 | 35 | None | fusée | `61\|CHARIAL` |
| 10 | `191B\|AVENUE\|FELIX FAURE` | 7CBW-4P8G | AI6510671 | 34 | num_voie | social | 1* | 52 | None | fusée | `191\|FELIX FAURE` |
| 11 | `19B\|RUE\|ST ANTOINE` | FUDZ-T2KQ | AA3187663 | 41 | num_voie | None | 7 | 13 | None | fusée | `19\|ST ANTOINE` |
| 12 | `28B\|RUE\|CLAUDIUS PIONCHON` | 3RN1-KX5T | AH7871353 | 60 | num_voie | mixte | 2 | 23 | None | fusée | `24\|PIONCHON` |
| 13 | `2B\|RUE\|DAUPHINE` | NHFZ-3KHY | AG8595613 | 39 | num_voie | None | 0 | 68 | None | fusée | `2\|DAUPHINE` |
| 14 | `30\|\|30B R DU PROFESSEUR PAUL SISLEY` | QHYH-Y2WN | AC7505134 | 43 | immat_horsrnc_fix | None | 0 | 67 | None | fusée | `30\|PROF PAUL SISLEY` |
| 15 | `4B\|RUE\|DAVID` | E9BD-25LA | AB8779696 | 33 | num_voie | None | 0 | 58 | None | fusée | `8\|DAVID` |
| 16 | `6B\|RUE\|STE ANNE DE BARABAN` | QRF3-15LG | AE4069597 | 27 | num_voie | None | 4 | 35 | None | fusée | `4\|STE ANNE` |
| 17 | `7\|IMPASSE\|ORDRE` | W8DF-4GCQ | AB8922999 | 49 | bdnb_orphelin | None | 0 | 47 | None | fusée | `118\|BARABAN` |
| 18 | `84B\|RUE\|DAUPHINE` | LU23-N3G3 | AH1784180 | 60 | num_voie | mixte | 9 | 74 | None | fusée | `84\|DAUPHINE` |
| 19 | `8B\|RUE\|DAVID` | E9BD-25LA | AB8779696 | 33 | num_voie | None | 9 | 58 | None | fusée | `8\|DAVID` |
| 20 | `9B\|RUE\|PROFESSEUR PAUL SISLEY` | P7TQ-TZ2P | AA0012898 | 225 | num_voie | None | 10 | 74 | None | fusée | `7B\|PROF PAUL SISLEY` |
| 21 | `9Q\|RUE\|MONTBRILLANT` | M2VT-GSQE | AB6211445 | 59 | num_voie | None | 4 | 76 | None | fusée | `9\|MONTBRILLANT #AB6220503` |
| 22 | `9T\|RUE\|MONTBRILLANT` | M2VT-GSQE | AB6211445 | 59 | num_voie | None | 1 | 76 | None | fusée | `9\|MONTBRILLANT #AB6220503` |
| 23 | `9\|IMPASSE\|ORDRE` | W8DF-4GCQ | AB8922999 | 49 | bdnb_orphelin | None | 0 | 47 | None | fusée | `118\|BARABAN` |

\* `191B FELIX FAURE` : `nb_ventes_logement` brut = 1 mais `ventes_par_an_logement` est vide → contribution **strict** = 0 (cf. E4). Tous les autres ont 0.

> îlot KV = None partout (le `assignments[cle].ilot` n'est jamais renseigné sur ce set ; l'îlot effectif vient du `_ilot` light).

---

## E2 — TYPE DE CORRECTION PAR CAS (test discriminant `l_libelle_adr` LIVE)

Méthode (réplique exacte du diag S1) : on récupère LIVE la liste `l_libelle_adr` du bgid actuel ; on normalise chaque façade (n° + suffixe B/T/Q/A/C/D) ; **le bgid déclare-t-il le numéro (de base ou suffixé) de la cle ?**

### Tableau des numéros réellement déclarés par chaque bgid (preuve LIVE)

| bgid (court) | `l_libelle_adr` LIVE (numéros déclarés) |
|---|---|
| YKPV-1S76 | 10, **10B** |
| P7TQ-TZ2P | 7B, **9, 9B, 11, 11B**, 57 |
| VFY6-RGM1 | 23, 25 |
| W8DF-4GCQ | 118 (BARABAN) |
| G1YT-XLZF | 90, 92 |
| 4XAJ-TVQA | 106 (BARABAN) |
| 7CBW-4P8G | 191, 9 (meynis) |
| FUDZ-T2KQ | 19, **19B** |
| 3RN1-KX5T | 24, 26, **28** |
| NHFZ-3KHY | 2, **2B** |
| QHYH-Y2WN | 30, **30B**, 32 |
| E9BD-25LA | 8, **8B** |
| QRF3-15LG | 4, 6, **6B** |
| LU23-N3G3 | 84, **84B** |
| M2VT-GSQE | **9B, 9Q, 9T** (MONTBRILLANT) |

### Verdict par cas (13 LÉGITIME / 10 FANTÔME)

| cle | tok | n° déclaré par bgid ? | VERDICT | vrai bgid (si RE-POINT) | preuve |
|---|---|---|---|---|---|
| `10B\|FREDERIC MISTRAL` | 10B | OUI (10B) | **LÉGITIME** | — | bgid déclare `10 B Rue Frédéric Mistral` |
| `11B\|PROF PAUL SISLEY` | 11B | OUI (11B) | **LÉGITIME** | — | bgid déclare `11 B Rue Prof. Paul Sisley` |
| `9B\|PROF PAUL SISLEY` | 9B | OUI (9B) | **LÉGITIME** | — | bgid déclare `9 B …` |
| `19B\|ST ANTOINE` | 19B | OUI (19B) | **LÉGITIME** (S1 #3) | — | bgid déclare `19 B Rue St Antoine` |
| `28B\|PIONCHON` | 28B | OUI (base 28) | **LÉGITIME** (S1 #5) | — | bgid déclare 24/26/28 |
| `2B\|DAUPHINE` | 2B | OUI (2B) | **LÉGITIME** | — | bgid déclare `2 B Rue du Dauphiné` |
| `30\|…30B SISLEY` | 30 | OUI (30/30B) | **LÉGITIME** | — | bgid déclare 30/30B/32 |
| `4B\|DAVID` *(voir FANTÔME)* | — | — | — | — | — |
| `6B\|STE ANNE` | 6B | OUI (6B) | **LÉGITIME** (S1 #2) | — | bgid déclare 4/6/6B |
| `84B\|DAUPHINE` | 84B | OUI (84B) | **LÉGITIME** | — | bgid déclare `84 B …` |
| `8B\|DAVID` | 8B | OUI (8B) | **LÉGITIME** | — | bgid déclare 8/8B |
| `9Q\|MONTBRILLANT` | 9Q | OUI (9Q) | **LÉGITIME** | — | bgid déclare 9B/9Q/9T |
| `9T\|MONTBRILLANT` | 9T | OUI (9T) | **LÉGITIME** | — | bgid déclare 9B/9Q/9T |
| `11B\|ST MAXIMIN` | 11B | **NON** (23/25) | **FANTÔME → RETRAIT** | aucun bgid distinct identifiable | bgid déclare 23/25 ; le vrai `11` ST MAXIMIN est ailleurs (bgid 29R7, îlot 66) mais aucun bgid ne déclare `11`/`11B` ST MAXIMIN |
| `121A\|CHARIAL` | 121A | **NON** (90/92) | **FANTÔME → RE-POINT** | **AX8P-5ZM6-3A3B** (îlot 34) | bgid G1YT déclare 90/92 ; vrai 121 déjà dans le light sur bgid AX8P |
| `121B\|CHARIAL` | 121B | **NON** (90/92) | **FANTÔME → RE-POINT** | AX8P-5ZM6-3A3B | idem (chaîne 121B/C/D fusées sous 121A) |
| `121C\|CHARIAL` | 121C | **NON** (90/92) | **FANTÔME → RE-POINT** | AX8P-5ZM6-3A3B | idem |
| `121D\|CHARIAL` | 121D | **NON** (90/92) | **FANTÔME → RE-POINT** | AX8P-5ZM6-3A3B | idem |
| `130B\|BARABAN` | 130B | **NON** (106) | **FANTÔME → RETRAIT** | aucun (130 inexistant BAN) | bgid 4XAJ déclare 106 BARABAN ; BAN n'a **aucun housenumber 130 Rue Baraban** (LIVE) → pas de vrai bgid distinct |
| `4B\|DAVID` | 4B | **NON** (8/8B) | **FANTÔME → RETRAIT** | aucun (4 inexistant BAN) | bgid E9BD déclare 8/8B ; BAN n'a **aucun housenumber 4 Rue David** (seul « 4 Rue Germain David », autre voie) → pas de vrai bgid distinct |
| `7\|IMPASSE\|ORDRE` | 7 | **NON** (118 BARABAN) | **FANTÔME → RE-POINT** | **QHUC-YTP8-DSV7** | bgid AGDC déclare 118 Baraban ; BAN `69383_5148_00007` → bgid QHUC déclare `7 Impasse de l'Ordre` |
| `9\|IMPASSE\|ORDRE` | 9 | **NON** (118 BARABAN) | **FANTÔME → RE-POINT** | **7CXY-SW9L-5XEB** | BAN `69383_5148_00009` → bgid 7CXY déclare `9 Impasse de l'Ordre` |
| `11\|IMPASSE\|ORDRE` | 11 | **NON** (118 BARABAN) | **FANTÔME → RE-POINT** | **PK29-38CK-NCFJ** | BAN `69383_5148_00011` → bgid PK29 déclare `11 Impasse de l'Ordre` |

### Comptage E2

| Catégorie | Compte | cles |
|---|---|---|
| **LÉGITIME** (bgid déclare le n°, hors dé-association) | **13** | 10B Mistral, 11B/9B Sisley, 19B St Antoine, 28B Pionchon, 2B Dauphine, 30/30B Sisley, 6B Ste Anne, 84B Dauphine, 8B David, 9Q/9T Montbrillant |
| **FANTÔME → RE-POINT** (vrai bgid distinct identifiable) | **7** | 121A/B/C/D Charial (→AX8P), 7/9/11 Impasse Ordre (→QHUC/7CXY/PK29) |
| **FANTÔME → RETRAIT** (pas de vrai bgid distinct) | **3** | 11B ST MAXIMIN, 130B BARABAN, 4B DAVID |
| **TOTAL FANTÔME** | **10** | |

> **Note importante sur les 3 RE-POINT « Impasse de l'Ordre »** : les 3 bgids cibles (QHUC/7CXY/PK29) **et** le bgid actuel AGDC (118 Baraban) sont **tous sur la MÊME parcelle `69383000DS0119`** (preuve LIVE `rel_batiment_groupe_parcelle`), qui est celle de la copro **AB8922999 « SDC LE CLOS SAINTE ANNE »**. L'impasse de l'Ordre est donc l'**accès arrière du même îlot bâti** (même SDC). Le `_bdnb_match=bdnb_orphelin` + fusion vers 118 BARABAN n'est donc **pas faux au sens « mauvais bâtiment »** : c'est la même copro physique, juste éclatée en bgids mono-adresse par BDNB. Strictement, AGDC ne **déclare pas** 7/9/11 Impasse (d'où le classement FANTÔME par le test `l_libelle_adr`), mais la dé-association ici est **cosmétique** (corriger le bgid pour pointer le vrai sous-bâtiment) et **doit conserver la fusion vers 118 BARABAN** pour ne pas sur-compter le parc (cf. E4). C'est le cas le moins urgent du set.
>
> **11B ST MAXIMIN** (RETRAIT) : le vrai `11` ST MAXIMIN existe déjà (bgid 29R7, îlot 66), mais aucun bgid ne déclare `11`/`11B` ST MAXIMIN. Le `11B` actuel est un faux-matching `num_voie` sur le bgid VFY6 (= 23/25 ST MAXIMIN, copro CARRE DES LYS). → RETRAIT de l'immat AB4738928 (garder le bgid VFY6 ou détacher ; pas de vrai bgid distinct prouvé).

---

## E3 — DOUBLONS D'ÎLOT

Test : un numéro de voie apparaît-il dans **>1 îlot** à cause du fantôme ?

| numéro de voie | entité RÉELLE (bgid / îlot) | fantôme (bgid / îlot) | cross-îlot ? | résolu par |
|---|---|---|---|---|
| **121 CHARIAL** | vrai `121` → bgid **AX8P** / **îlot 34** | `121A-D` → bgid G1YT / **îlot 39** | **OUI (34 ≠ 39)** | **RE-POINT** : 121A-D rejoignent AX8P/îlot 34 (vrai bâti) → le doublon disparaît. **1 doublon résolu.** |
| **11 ST MAXIMIN** | vrai `11` → bgid 29R7 / **îlot 66** | `11B` → bgid VFY6 / **îlot 67** | quasi (66 vs 67, îlots adjacents) | RETRAIT immat ; 11B reste sur VFY6 (pas de vrai bgid). Le n° « 11 » resterait visible en 66 (vrai) ; « 11B » en 67. Pas un cross-îlot franc — bordure de blocs. |
| 130 / 130B BARABAN | `130` et `130B` partagent bgid 4XAJ / îlot 35 | (même) | NON | pas de cross-îlot (même îlot) |
| 4 / 4B DAVID | `4` et `4B` partagent bgid E9BD / îlot 58 | (même) | NON | pas de cross-îlot |
| 7/9/11 Impasse Ordre | toutes sur bgid AGDC / îlot 47 | (même) | NON | pas de cross-îlot (RE-POINT change le bgid mais reste dans l'îlot 47) |

**Quantification** : **1 vrai doublon d'îlot résolu** (121 CHARIAL : îlot 34 vs 39). Le RE-POINT de 121A-D vers AX8P (îlot 34) fait disparaître la 2e occurrence du « 121 » en îlot 39 (le bâti 90-92), exactement comme prévu au diag S1. 11B ST MAXIMIN est une bordure (66/67), pas un doublon franc.

---

## E4 — IMPACT (PAS parc-neutre a priori, mais Δ = 0 mesuré)

Calcul reproduit avec le **mirror exact du dashboard** (`scripts/_simul_exact_dashboard.py`, secteurStrict=ON, filtres OFF) pour les ventes, et l'**algo `renderSecteur` exact** d'`index.html` (l.4924-4987 : `bgRncLots`/`bgBdnbResid`/`bgValue`, dédup `bg:bgid`) pour le parc.

### Fait central : tous les fantômes sont à `nb_ventes_logement = 0`

| fantôme | `ventes_par_an_logement` (strict) | `nb_ventes_logement` |
|---|---|---|
| 11B ST MAXIMIN | `{2021:0}` | 0 |
| 121A / 121B / 121C / 121D CHARIAL | `{}` | 0 |
| 130B BARABAN | `{}` | 0 |
| 4B DAVID | `{2021:0,2022:0,2023:0,2025:0}` | 0 |
| 7 / 9 / 11 Impasse Ordre | `{}` | 0 |

→ **AUCUN fantôme ne porte de vente en mode strict.** La liste des fantômes à `vlog > 0` est **VIDE**.

### Pourquoi l'immat/lots fantôme n'affecte PAS le parc

`renderSecteur` calcule le parc (`secL`) via `bgValue[bgid]` = **Σ lots RNC des copros** rattachées au bâti (`bgRncLots`), où les lots viennent de **`coproByCle[a.cle].nb_lots_habitation`** — **PAS** du champ `numero_immatriculation`/`nb_lots_habitation` porté sur la **ligne adresse**. Les fantômes ne sont **pas** dans `coproprietes[]` (par définition du set) → `cp = coproByCle[cle] = None` → ils ne contribuent jamais à `bgRncLots`. Leur immat/lots est donc **purement display-only** (badge UI). De plus :
- Les fantômes **fusés** (`fusedSrc`) sont ignorés des 3 passes parc.
- Les 2 fantômes **rendus** (11B social-adjacent / 121A `social`) : leurs bgids (VFY6, G1YT) sont **déjà dominés par la copro RNC réelle** (23 ST MAXIMIN 76 lots ; 90 CHARIAL 25 lots) via `bgRncLots` → le `bgBdnbResid` n'est pas consulté, et 121A est de toute façon exclu (KV `social`).

### Mesure de la dé-association (variante recommandée : RETRAIT immat/lots + RE-POINT bgid impasse, fusion conservée)

| Grandeur | Baseline | Après dé-assoc | Δ |
|---|---|---|---|
| Σ `nb_ventes_logement` (effTot strict, secAllV) | 2989 | 2989 | **+0** |
| **secVAn strict (= secAllV/5)** | **597,8** | **597,8** | **+0,0** |
| parc `secL` (dédup `bg:bgid`) | 18 385 | 18 385 | **+0** |
| répartition par îlot (ventes) | — | — | **aucun déplacement** (tous fantômes 0 vente) |

> **Sur le « 578,4 »** : le header strict marché-libre **courant** vaut **597,8 ventes/an** (le 578,4 cité dans la tâche est une valeur d'un header antérieur). Quelle que soit la base de référence, **Δ = 0** : aucun fantôme ne porte de vente strict.

### Variante alternative (si on UNFUSE aussi les fantômes au lieu de garder la fusion)

| Grandeur | Baseline | UNFUSE+RETRAIT (10) | Δ |
|---|---|---|---|
| secVAn strict | 597,8 | 597,8 | **+0,0** |
| parc `secL` | 18 385 | 18 406 | **+21** |

Le **+21** vient **uniquement** des 3 bgids impasse re-pointés (QHUC/7CXY/PK29) **s'ils sont dé-fusionnés** : devenus des adresses résidentielles autonomes sans copro, ils alimenteraient `bgBdnbResid` à hauteur de `nb_log_bdnb` 9+6+6 = 21. **Or ces 21 lgts sont des sous-fragments BDNB du MÊME SDC LE CLOS SAINTE ANNE (28 lgts au total sur AGDC)** — les compter en plus serait un **SUR-COMPTAGE**. → **Recommandation : conserver la fusion des impasses vers 118 BARABAN** (RE-POINT bgid seul, fusion intacte) → Δ parc = 0 (variante recommandée ci-dessus).

**Conclusion E4** : la dé-association complète est **strictement neutre** (Δ ventes = 0, Δ secVAn = 0, Δ parc = 0) si on conserve les fusions. Le seul effet réel est **structurel/hygiène** : retrait d'un immat/lots fantôme display-only + résolution du doublon d'îlot 121 (E3). Contrairement à ce que la tâche anticipait, **ce n'est pas un changement de parc** — parce que les fantômes étaient déjà soit fusés, soit dominés par la vraie copro, et tous à 0 vente.

---

## E5 — MAKE_LIGHT (cause racine) + GARDE À POSER

### Localisation du writer concret de l'immat fantôme

Contrairement à la formulation initiale (« make_light dénormalise l'immat sur tout le bloc bgid »), le **writer concret** dans le light courant n'est PAS la boucle principale de make_light, mais un **fix post-make_light in-repo** :

- **`scripts/_apply_propag_immat_21suff_dl.py`** (marker `fix_propag_immat_21suff_dl_2026-05-23`). Preuve : **19 des 23** adresses du set portent ce marker `_correctif_propagation_indice` (les 3 Impasse Ordre = path `bdnb_orphelin` ; `30B Sisley` = `immat_horsrnc_fix`).
- Ce script lit `data/_triage_85_suffixes_dl.json` → liste `rattachables_rnc` (21 cles) ; pour chaque cle il copie depuis la copro mère (indexée par immat) : `numero_immatriculation`, `nb_lots_habitation`, `taux_rotation`, `syndic`, etc. (l.79-94).
- **L'immat mère est choisie via `rnc_hits`** (ex. `121A → {immat:AA9271602, nom:"90-92 CHARIAL", hab:25, in_sct:"DEJA-SCT"}`). Ce `rnc_hits` a été dérivé **par le bgid** : `numero_immat_principal` du snapshot BDNB du bgid faux-matché. C'est **là** que vit la « dénorm via bgid » : le bgid G1YT porte `numero_immat_principal = AA9271602` dans le snapshot (vérifié LIVE+snapshot), et le triage a rattaché 121A à cette immat **sans vérifier que le bgid déclare réellement 121 en `l_libelle_adr`**.

### Origine amont dans make_light (le signal bgid)

Dans `C:\Users\Station 5\make_light.py` (1188 lignes) :
- **l.446-464** : construction de `bdnb_by_immat` à partir de `b.numero_immat_principal` (chaque bgid BDNB porte son immat principal).
- **l.477-499 `bdnb_par_voie`** : rattache une adresse à un bâti BDNB par **rue + n° le plus proche dans 80 m** (`RAYON=80.0`). C'est ce matching laxiste (sans validation `l_libelle_adr`/parcelle) qui colle 121A au bgid G1YT (90-92) → `_bdnb_match="num_voie"` (l.696-700).
- **l.722-746** : la ligne adresse reçoit `batiment_groupe_id = bb.batiment_groupe_id` ; l'`numero_immatriculation`/`nb_lots_habitation` (l.732-734) viennent de `cm = copro_by_cle.get(ak)` — **None pour un fantôme** (la copro 90-92 ne déclare pas 121). Donc make_light lui-même laisse l'immat à **None** sur le fantôme ; c'est le **triage 85-suffixes** qui l'a ensuite rempli via le bgid.

```python
# make_light.py l.732-734 (assignation immat/lots sur la ligne adresse)
"numero_immatriculation": (cm.get("numero_immatriculation") if cm else None),
"nb_lots_habitation":     (cm.get("nb_lots_habitation")     if cm else None),
# cm = copro_by_cle.get(ak) or copro_by_cle.get(ALIAS_RNC.get(ak, ""))  (l.690)
```

### Le garde existant (aval) — commit 71f2ca3

make_light a **déjà** une passe « Consolidation S1 » (l.996-1086) avec la table `DECLARED_S1` (l.1015-1022) et la fonction `_declared_s1` (l.1024-1028) : elle **ne fusionne** un suffixe même-bgid+même-immat **QUE si son numéro de base est dans la table des n° déclarés LIVE** (`l_libelle_adr`). Les 2 fantômes connus (G1YT 121A-D, VFY6 11B) sont **explicitement exclus** de `DECLARED_S1` (commentaire l.1019-1021). **Mais ce garde n'agit qu'au moment de la FUSION**, pas au moment de la **propagation d'immat** — il empêche de fuser un fantôme sous l'ancre, il **n'empêche pas** le triage 85-suffixes de lui coller l'immat.

### Garde recommandé (à poser EN AMONT, au moment de la dénormalisation immat)

Le garde anti-fantôme doit être posé **au moment où l'immat est propagée**, pas seulement à la fusion :

1. **Priorité (correction du vrai bug) — dans `scripts/_apply_propag_immat_21suff_dl.py` / le triage `_triage_85_suffixes_dl.json`** : avant de propager l'immat d'un `rnc_hit` sur une cle suffixée, **vérifier que le bgid de la cle déclare réellement son numéro de base en `l_libelle_adr`** (preuve LIVE, ou table curée style `DECLARED_S1`). Si non déclaré → **ne pas propager** (la cle reste hors-RNC, candidate à RE-POINT/RETRAIT). C'est le filtre qui aurait empêché les 10 fantômes.

2. **Dans make_light, en amont (au moment du `num_voie` match l.696-700)** : durcir `bdnb_par_voie` pour qu'un match `num_voie` ne soit retenu que si le **numéro demandé** figure dans les façades **réellement déclarées par le bâti candidat** — c.-à-d. comparer `pn` (numéro cherché) non seulement à `nums` issus de `libelle_adr_principale_ban` (1 seul principal, insuffisant) mais à l'ensemble `l_libelle_adr`. **Limite documentée** (commentaire l.1009-1011) : le snapshot BDNB local (`bdnb_*.json`) **ne contient PAS `l_libelle_adr`** (seulement `libelle_adr_principale_ban` = 1 façade principale). Tant que le snapshot n'embarque pas `l_libelle_adr`, le garde robuste passe par une **table curée DECLARED** (comme `DECLARED_S1` / `ALIAS_RNC` / `FUSION_RNC_EXTRA_NUMS`), alimentée par preuve LIVE.

**Critère du garde, en une phrase** : ne propager `numero_immatriculation`/`nb_lots_habitation` d'une copro sur une adresse suffixée/voisine **QUE si le bgid de cette adresse DÉCLARE le numéro (de base) de l'adresse dans `l_libelle_adr`** (ou si la copro RNC couvre ce numéro via ref_cad/adresse_complémentaire). Sinon : abstention (hors-RNC).

---

## CONCLUSION

### (a) Plan de dé-association cas par cas

**13 LÉGITIMES — à laisser** (bgid déclare le n°, hors dé-association) :
`10B Mistral`, `11B Sisley`, `9B Sisley`, `19B St Antoine`, `28B Pionchon`, `2B Dauphine`, `30/30B Sisley`, `6B Ste Anne`, `84B Dauphine`, `8B David`, `9Q Montbrillant`, `9T Montbrillant`. (Dont 3 = vraies co-immat S1 déjà fusées 6B/19B/28B, confirmées légitimes — voir note ci-dessous.)

**7 RE-POINT bgid** (vrai bgid distinct prouvé) :
- `121A/B/C/D CHARIAL` → bgid **AX8P-5ZM6-3A3B** (vrai 121, îlot 34). Résout le doublon d'îlot. L'immat fantôme AA9271602 tombe naturellement (AX8P n'a pas cette immat).
- `7 Impasse Ordre` → **QHUC-YTP8-DSV7** ; `9` → **7CXY-SW9L-5XEB** ; `11` → **PK29-38CK-NCFJ**. **Conserver la fusion vers 118 BARABAN** (même parcelle DS0119 / même SDC LE CLOS SAINTE ANNE) — cas cosmétique, le moins urgent.

**3 RETRAIT immat/lots** (pas de vrai bgid distinct) :
- `11B ST MAXIMIN` : retirer immat AB4738928 (bgid VFY6 = 23/25, ne déclare pas 11B ; vrai 11 ailleurs sur 29R7).
- `130B BARABAN` : retirer immat AE1293612 (BAN n'a aucun housenumber 130 Baraban).
- `4B DAVID` : retirer immat AB8779696 (BAN n'a aucun housenumber 4 David).

> **Précision sur les « 6B/19B/28B déjà fusionnés au commit 71f2ca3 »** : la tâche demandait de les exclure du set s'ils apparaissaient comme « vrais suffixes déjà traités S1 ». Vérification LIVE : **6B Ste Anne, 19B St Antoine, 28B Pionchon sont effectivement LÉGITIMES** (bgid déclare 4/6/6B, 19/19B, 24/26/28). Ils figurent dans le set E1 (ils portent toujours leur immat, par construction du critère) mais sont **marqués LÉGITIME → hors dé-association** (déjà traités S1). ✓

### (b) Impact chiffré attendu

| | Δ |
|---|---|
| parc `secL` | **0** (variante recommandée, fusions conservées) ; +21 sur-comptage à ÉVITER si on dé-fuse les impasses |
| Σ `nb_ventes_logement` | **0** (tous fantômes à 0 vente) |
| secVAn strict (« 578,4 » → courant 597,8) | **+0,0** |
| répartition par îlot | **aucun déplacement de vente** |
| **Fantômes à `vlog > 0`** | **AUCUN** (liste vide) |

### (c) Fix make_light

Garde à poser **en amont** (propagation immat / triage 85-suffixes), pas seulement en aval (fusion) : ne propager immat/lots **QUE si le bgid déclare le numéro** (`l_libelle_adr` LIVE, ou table curée `DECLARED` style `DECLARED_S1`). Limite connue : le snapshot BDNB local n'embarque pas `l_libelle_adr` → table curée nécessaire tant que le snapshot reste sur `libelle_adr_principale_ban` seul. Writer concret à corriger en priorité : `scripts/_apply_propag_immat_21suff_dl.py` + entrée triage `_triage_85_suffixes_dl.json::rattachables_rnc`.

### (d) Doublons d'îlot résolus

**1** (121 CHARIAL : îlot 34 vrai vs îlot 39 phantom — résolu par RE-POINT vers AX8P). 11B ST MAXIMIN = bordure 66/67 (non franc).

### Preuve LIVE vs déduit localement

- **LIVE** : tous les `l_libelle_adr` par bgid, parcelles (`rel_batiment_groupe_parcelle`), BAN housenumbers (4 David / 130 Baraban inexistants, 7/9/11 Impasse Ordre existants), bgids cibles Impasse via `rel_batiment_groupe_adresse`, RNC `numero_immat_principal`/ref_cad.
- **LOCAL** : énumération du set (light + KV), états de fusion (`_fusion_auto`/`_fusion_cible`), simulation parc/ventes (algo `renderSecteur` + mirror dashboard reproduits), marker `_correctif_propagation_indice` (preuve du writer concret).
- **Aucune donnée inventée.**

> **Rappel : ceci est un diagnostic. AUCUN fix appliqué, AUCUNE écriture hors ce rapport, AUCUN commit.**
