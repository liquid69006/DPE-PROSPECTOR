# Diagnostic — provenance immat des 5 groupes "S1" + cas 121 ANTOINE CHARIAL (secteur Dauphiné-Lacassagne)

> READ-ONLY. Date : 2026-06-01. AUCUNE donnée/code modifié. Seul ce fichier est écrit.
> Source PRÉ-fusion : `data/secteur_dauphine_lacassagne_light.json.prefusions1.bak`
> Source POST-fusion : `data/secteur_dauphine_lacassagne_light.json` (fix `fix_fusion_s1_immat.py` appliqué, NON commité)
> Source KV : `data/_kv_assign_dl.json` (clé `assignments`)
> **Preuve LIVE disponible** : réseau OK → BDNB `l_libelle_adr` (resource `batiment_groupe_complet`) + `rel_batiment_groupe_parcelle` + RNC live tabular-api `3ea8e2c3-0038-464a-b17e-cd5c91f65ce2`. Toutes les preuves BDNB/RNC ci-dessous sont **LIVE** (pas locales).
> Preuve LOCALE : copros du light **n'ont AUCUN** `reference_cadastrale_*` ni `adresse_complementaire_*` peuplé (0/554) → la couverture par numéro a dû être établie en LIVE.

---

## Synthèse exécutive

| Question | Réponse |
|---|---|
| **E0 — 121 est-il un intrus dans le bgid G1YT ?** | **OUI.** BDNB `l_libelle_adr` du bgid `3WFJ-G1YT-XLZF` = **uniquement `90` et `92` Rue Antoine Charial**. 121A/B/C/D y sont par faux matching `num_voie` make_light. |
| **E1 — combien de VRAIES co-immat / FANTÔMES parmi les 5 ?** | **3 VRAIES** (Ste Anne, St Antoine, Pionchon) + **2 FANTÔMES** (121A-D sous 90 CHARIAL ; 11B sous 23 ST MAXIMIN). |
| **E2 — sur-propagation immat par alias-bgid (DL)** | **23 adresses** ont un immat hérité via bgid (`_bdnb_match≠immat` & absentes de `coproprietes[]`), dont **19 en `num_voie` strict**. |
| **E3 — cause du doublon d'îlot** | DEUX entités "121 CHARIAL" distinctes : le **vrai 121** (bgid AX8P, parcelle DT0120, **îlot 34**) et les **phantom 121A-D** (bgid G1YT, parcelle DT0089, **îlot 39**, immat AA9271602). |
| **Reco G1YT** | **EXCLURE G1YT du fix_fusion_s1** → traiter en **dé-association** (retirer l'immat fantôme AA9271602 de 121A-D + corriger leur bgid faux-matching), PAS en fusion sous 90. |

---

## E0 — Provenance du bgid de 121 (bdnb-bg-3WFJ-G1YT-XLZF)

### Membres RÉELS du bgid côté BDNB (preuve LIVE `l_libelle_adr`)
```
bdnb-bg-3WFJ-G1YT-XLZF -> [ "90 Rue Antoine Charial", "92 Rue Antoine Charial" ]
```
**Seuls 90 et 92** sont rattachés à ce bgid côté BDNB. 121 (sous toutes ses formes) **n'y est pas**.

### Membres du bgid G1YT dans le light PRÉ-fusion (`.prefusions1.bak`)
| cle | `numero_immatriculation` | `_bdnb_match` | dans `coproprietes[]` | vlog | lots |
|---|---|---|---|---|---|
| `90\|RUE\|ANTOINE CHARIAL` | AA9271602 | **immat** | **OUI** | 1 | 25 |
| `92\|RUE\|ANTOINE CHARIAL` | None (fusionné→90) | num_voie | non | 3 | None |
| `121A\|RUE\|ANTOINE CHARIAL` | AA9271602 | **num_voie** | non | 0 | 25 |
| `121B\|RUE\|ANTOINE CHARIAL` | AA9271602 | num_voie | non | 0 | 25 |
| `121C\|RUE\|ANTOINE CHARIAL` | AA9271602 | num_voie | non | 0 | 25 |
| `121D\|RUE\|ANTOINE CHARIAL` | AA9271602 | num_voie | non | 0 | 25 |

### Verdict E0
- **90 et 92** = la VRAIE copro AA9271602 « 90-92 RUE ANTOINE CHARIAL » (REGIE LESTRA). `90` est `_bdnb_match=immat` ET présent dans `coproprietes[]` (cle_adresse `90|RUE|ANTOINE CHARIAL`, 25 lots habit, 97 lots tot). `92` y est par `num_voie` mais BDNB le confirme dans le bgid → légitime façade.
- **121A/B/C/D = INTRUS confirmé.** `_bdnb_match=num_voie`, absents de `coproprietes[]`, ABSENTS du `l_libelle_adr` BDNB du bgid. Les lots=25 et l'immat AA9271602 sont **dénormalisés** (hérités du bgid par make_light, voir §E2), PAS propres à 121.
- **make_light a mis 121A-D dans G1YT par num_voie**, puis l'immat de l'ancre copro 90 a été dénormalisé sur tous les membres du bloc bgid → 121 hérite d'un **immat FANTÔME**.

> Note parcelle (preuve LIVE) : le bgid G1YT est sur parcelle BDNB `69383000DT0089` = RNC `69123383DT0089` = `reference_cadastrale_1` de AA9271602. La parcelle "matche" donc au niveau bgid — mais c'est précisément parce que make_light a rattaché 121A-D au mauvais bgid. La preuve d'exclusion est le `l_libelle_adr` (90/92 seuls), pas la parcelle.

---

## E1 — Provenance de l'immat des 5 groupes S1

Méthode : pour chaque source `num_voie`, on teste si son **numéro** est réellement couvert par l'immat de l'ancre. Preuve LIVE = BDNB `l_libelle_adr` du bgid commun (le numéro de la source y figure-t-il ?) + RNC `reference_cadastrale` de l'immat (la parcelle du bgid de la source est-elle une ref_cad de la copro ?).

### Détail par groupe

| # | bgid | immat (copro) | ancre | source `num_voie` | numéro dans `l_libelle_adr` BDNB du bgid ? | VERDICT source |
|---|---|---|---|---|---|---|
| 1 | RBD4-VFY6-RGM1 | AB4738928 « SDC LE CARRE DES LYS » | `23\|ST MAXIMIN` | `11B\|ST MAXIMIN` | **NON** — bgid déclare `23`, `25` seulement | **FANTÔME** |
| 2 | SR2C-QRF3-15LG | AE4069597 « LE NIVOLET » | `4\|STE ANNE` | `6B\|STE ANNE` | **OUI** — bgid déclare `4`, `6`, `6 B` | **VRAIE co-immat** |
| 3 | 7TYE-FUDZ-T2KQ | AA3187663 « LE SAINT ANTOINE » | `19\|ST ANTOINE` | `19B\|ST ANTOINE` | **OUI** — bgid déclare `19`, `19 B` | **VRAIE co-immat** |
| 4 | 3WFJ-G1YT-XLZF | AA9271602 « 90-92 CHARIAL » | `90\|CHARIAL` | `121A/B/C/D\|CHARIAL` | **NON** — bgid déclare `90`, `92` seulement | **FANTÔME** (×4 unités) |
| 5 | JTAL-3RN1-KX5T | AH7871353 « RES. CLAUDIUS PIONCHON » | `24\|PIONCHON` | `28B\|PIONCHON` | **OUI** — bgid déclare `24`, `26`, `28` | **VRAIE co-immat** |

### Preuve parcelle complémentaire (LIVE — convertie BDNB→RNC : `69383000` → `69123383`)

| immat | ref_cad RNC (live) | parcelles du bgid (live, RNC) | intersection |
|---|---|---|---|
| AB4738928 | BD0030, BD0103, BD0109 | BD0109, BD0112, BD0114, BD0116 | BD0109 ✓ (mais voir ci-dessous) |
| AE4069597 | DT0003 | DT0003 | DT0003 ✓ |
| AA3187663 | EI0095 | EI0095 | EI0095 ✓ |
| AA9271602 | DT0089 | DT0089 | DT0089 ✓ (mais voir ci-dessous) |
| AH7871353 | DZ0019, DZ0020, DZ0116 | DZ0019, DZ0020, DZ0116 | 3/3 ✓ |

⚠️ **La parcelle matche pour les 5** (y compris les 2 fantômes) car make_light a rattaché les intrus au mauvais bgid, et **ce bgid** est bien sur la parcelle de la copro. La parcelle au niveau bgid est donc **non-discriminante**. Le test discriminant est **`l_libelle_adr`** (quelles façades BAN le bgid déclare réellement) : il **exclut 11B et 121A-D**, **inclut 6B / 19B / 28B**.

### Cas 1 (11B ST MAXIMIN) — vérification renforcée
La copro AB4738928 (CARRE DES LYS, ensemble multi-parcelles 247 lots tot) est répartie sur 2 bgids (reverse parcelle live) :
- `bdnb-bg-...VFY6-RGM1` → `l_libelle_adr` = **23, 25 St-Maximin**
- `bdnb-bg-9ZYS-LQGQ` → `l_libelle_adr` = **5 Rue Marcel Pehu** (cf. memory `fix-multiparcelles-dl-lot2`)

**Aucun des 2 bgids ne déclare `11` ni `11B` St-Maximin.** Par ailleurs le vrai `11|RUE|ST MAXIMIN` du light est dans un bgid totalement différent (`29R7-3GSE-U5WB`, îlot 66). → **11B est bien un FANTÔME** rattaché à RBD4 par `num_voie`, immat dénormalisé.

### Cas 4 (121A-D) — détail demandé
- Les 4 unités 121A/B/C/D portent l'immat AA9271602 par dénormalisation bgid (lots=25 hérités, vlog=0).
- BDNB exclut 121 du bgid G1YT (§E0). Le vrai 121 est ailleurs (§E3).
- KV : 121A/B/C/D sont taguées **`social`** (≠ tag de l'ancre 90 qui est `None`). Les fusionner sous 90 fait basculer ces 4 unités sociales sous une ancre non-sociale → distorsion potentielle du calcul "marché libre" (jugé par tag d'ancre).

### Bilan E1
- **3 groupes = VRAIES co-immatriculations** → fusion S1 **légitime** : groupes **2 (6B Ste Anne), 3 (19B St Antoine), 5 (28B Pionchon)**.
- **2 groupes = immat FANTÔME** → fusion S1 **incorrecte** : groupe **1 (11B St Maximin)** et groupe **4 (121A-D Charial)**. Ces sources ne devraient PAS être fusionnées sous l'ancre copro : elles devraient être **dé-associées** (immat fantôme retiré, bgid faux-matching corrigé).

---

## E2 — Quel mécanisme a propagé l'immat ; ampleur sur DL

### Mécanisme
Ce n'est **PAS** un correctif in-repo de propagation. Vérifié :
- `metadata._correctif_propag_immat` (le fix « 530 DL + 104 MP ») ne traite QUE `_bdnb_match ∈ {immat_fix, immat_horsrnc_fix}` — il **exclut explicitement** `num_voie`. Il n'est donc PAS la cause des cas `num_voie`.
- La cause est **make_light lui-même** : il crée les suffixes (11B, 121A-D, 6B…) dans le **bloc bgid** et **dénormalise l'immat de l'ancre copro sur tous les membres du bgid**. C'est ce que documente le docstring de `fix_fusion_s1_immat.py` (l.11-16 : « l'ancre copro (cle_adresse) est consumed par la fusion RNC AVANT le bloc bgid… le suffixe même-immat (ex 11B, copro=False, immat dénormalisé) reste alors SEUL »).
- Pour les VRAIS co-immat (6B/19B/28B) cette dénormalisation est correcte. Pour les FAUX num_voie (11B, 121A-D) elle propage un **immat fantôme**.

### Quantification (sur `.prefusions1.bak`, 1385 adresses DL)
Adresses avec `numero_immatriculation` non null **+** `_bdnb_match ≠ immat` **+** **absentes** de `coproprietes[]` (= immat hérité via bgid, potentiellement fantôme) :

| Critère | Compte |
|---|---|
| **TOTAL immat hérité via bgid** | **23** |
| dont `_bdnb_match=num_voie` (strict) | **19** |
| dont `_bdnb_match=bdnb_orphelin` | 3 |
| dont `_bdnb_match=immat_horsrnc_fix` | 1 |

### Les 19 cas `num_voie` strict (échantillon complet)
```
10B|RUE|FREDERIC MISTRAL        immat=AA1991173  bgid=...YKPV-1S76  ilot=32
11B|RUE|PROFESSEUR PAUL SISLEY  immat=AA0012898  bgid=...P7TQ-TZ2P  ilot=74
11B|RUE|ST MAXIMIN              immat=AB4738928  bgid=...VFY6-RGM1  ilot=67   <- FANTÔME (groupe S1 #1)
121A|RUE|ANTOINE CHARIAL        immat=AA9271602  bgid=...G1YT-XLZF  ilot=39   <- FANTÔME (groupe S1 #4)
121B|RUE|ANTOINE CHARIAL        immat=AA9271602  bgid=...G1YT-XLZF  ilot=39   <- FANTÔME
121C|RUE|ANTOINE CHARIAL        immat=AA9271602  bgid=...G1YT-XLZF  ilot=39   <- FANTÔME
121D|RUE|ANTOINE CHARIAL        immat=AA9271602  bgid=...G1YT-XLZF  ilot=39   <- FANTÔME
130B|RUE|BARABAN                immat=AE1293612  bgid=...4XAJ-TVQA  ilot=35
191B|AVENUE|FELIX FAURE         immat=AI6510671  bgid=...7CBW-4P8G  ilot=52
19B|RUE|ST ANTOINE              immat=AA3187663  bgid=...FUDZ-T2KQ  ilot=13   <- VRAIE (groupe S1 #3, confirmée BDNB)
28B|RUE|CLAUDIUS PIONCHON       immat=AH7871353  bgid=...3RN1-KX5T  ilot=23   <- VRAIE (groupe S1 #5, confirmée BDNB)
2B|RUE|DAUPHINE                 immat=AG8595613  bgid=...NHFZ-3KHY  ilot=68
4B|RUE|DAVID                    immat=AB8779696  bgid=...E9BD-25LA  ilot=58
6B|RUE|STE ANNE DE BARABAN      immat=AE4069597  bgid=...QRF3-15LG  ilot=35   <- VRAIE (groupe S1 #2, confirmée BDNB)
84B|RUE|DAUPHINE                immat=AH1784180  bgid=...LU23-N3G3  ilot=74
8B|RUE|DAVID                    immat=AB8779696  bgid=...E9BD-25LA  ilot=58
9B|RUE|PROFESSEUR PAUL SISLEY   immat=AA0012898  bgid=...P7TQ-TZ2P  ilot=74
9Q|RUE|MONTBRILLANT             immat=AB6211445  bgid=...M2VT-GSQE  ilot=76
9T|RUE|MONTBRILLANT             immat=AB6211445  bgid=...M2VT-GSQE  ilot=76
```
> Lecture : la dénormalisation d'immat par bgid touche **23 adresses** DL. La plupart sont des suffixes-façades (B/T/Q) **plausiblement légitimes** (même bâtiment physique) — seul un audit `l_libelle_adr` par cas tranche. Les **5 cas S1** ci-dessus ont été tranchés en LIVE : 3 légitimes, 2 fantômes (11B, 121A-D). Les 14 autres `num_voie` (hors S1) ne sont PAS des doublons S1 (bgid à 1 seule unité rendue ou suffixe unique) et **sortent du périmètre** du fix_fusion_s1 ; ils restent à auditer un jour (B/T/Q vs vrais éclatements).

---

## E3 — Doublon 2 îlots (34 et 39)

### Trace îlots (light `_ilot` ; KV `ilot` = None pour tous → l'îlot effectif vient du light)

| cle | bgid | parcelle (RNC) | `_ilot` light | dans `coproprietes[]` | immat | KV type |
|---|---|---|---|---|---|---|
| `90\|...CHARIAL` (ancre) | G1YT | DT0089 | **39** | OUI | AA9271602 | None |
| `92\|...CHARIAL` | G1YT | DT0089 | 39 | non | (fusionné→90) | None |
| `121A\|...CHARIAL` | G1YT | DT0089 | **39** | non | AA9271602 (fantôme) | **social** |
| `121B\|...CHARIAL` | G1YT | DT0089 | 39 | non | AA9271602 (fantôme) | social |
| `121C\|...CHARIAL` | G1YT | DT0089 | 39 | non | AA9271602 (fantôme) | social |
| `121D\|...CHARIAL` | G1YT | DT0089 | 39 | non | AA9271602 (fantôme) | social |
| **`121\|...CHARIAL`** (vrai) | **AX8P-5ZM6-3A3B** | **DT0120** | **34** | non | None | (non taguée) |
| `123\|...CHARIAL` (→ fused 121) | AX8P | DT0120 | 34 | non | None | None |

### Cause exacte du doublon
Il existe **DEUX entités distinctes portant le numéro 121 Rue Antoine Charial** dans le light :
1. **Le VRAI 121** : cle `121|RUE|ANTOINE CHARIAL` (sans suffixe), **bgid AX8P-5ZM6-3A3B**, **parcelle DT0120**, **îlot 34**, sans immat (`_bdnb_match=num_voie`), avec `123` fusionné dessous. BDNB de ce bgid déclare `120 Rue Antoine Charial` (côté pair voisin) — c'est le vrai bâti du 120-121-123.
2. **Les FAUX 121A-D** : bgid **G1YT-XLZF**, **parcelle DT0089** (= le bâti 90-92), **îlot 39**, immat fantôme AA9271602, tagués social.

→ Le numéro "121 Charial" apparaît donc dans **l'îlot 34** (le vrai, via `121`) **ET l'îlot 39** (les faux, via `121A-D` rattachés au bâti 90-92). C'est un **doublon de provenance bgid**, pas une relocalisation de fusion.

### Lien avec le finding « 43 sources fusionnées en îlot ≠ ancre »
- **121A-D NE font PAS partie** des sources relocalisées : leur `_ilot=39` est **identique** à celui de l'ancre 90 (îlot 39). La fusion S1 #4 est donc parc-neutre ET îlot-neutre (et ventes-neutre : 121A-D ont vlog=0).
- (Recompté sur le light POST-fusion : **41** sources fusionnées tombent dans un îlot ≠ ancre — l'écart vs « 43 » du diag précédent vient de l'ajout des fusions S1 qui sont, elles, intra-îlot.)
- **Conséquence sur la répartition** : la fusion S1 #4 ne déplace **aucune vente** entre îlots (121A-D = 0 vente, même îlot que l'ancre). Mais elle **masque le doublon** au lieu de le corriger : le numéro 121 reste présent en îlot 34 (vrai) ET son clone fantôme reste rattaché au bâti 90 en îlot 39. Tant que l'immat fantôme et le bgid faux-matching subsistent, 121 est **compté deux fois** côté inventaire copro/social (4 unités sociales fantômes sous le bâti 90).

---

## CONCLUSION

**(a) 121 CHARIAL est-il un intrus à dé-associer ?**
**OUI.** Les 121A/B/C/D sont des **intrus** dans le bgid G1YT (le vrai bgid G1YT = 90+92 seuls, preuve LIVE `l_libelle_adr`). Leur immat AA9271602 et leurs 25 lots sont **fantômes** (dénormalisés du bâti 90-92). Le **vrai** 121 vit dans le bgid AX8P (parcelle DT0120, îlot 34). → il faut **dé-associer** 121A-D : retirer l'immat fantôme et corriger le bgid faux-matching (idéalement les rattacher au vrai bâti 121/AX8P ou les laisser hors-immat), **PLUTÔT que de les fusionner sous 90**.

**(b) Combien des 5 groupes S1 sont de VRAIES co-immat ?**
**3 VRAIES** (preuve BDNB `l_libelle_adr`) : `6B Ste Anne→4` (bgid déclare 4/6/6B), `19B St Antoine→19` (déclare 19/19B), `28B Pionchon→24` (déclare 24/26/28). **2 sur immat FANTÔME** : `11B St Maximin→23` (bgid déclare 23/25 seulement ; aucun bgid de la copro CARRE DES LYS ne déclare 11/11B) et `121A-D Charial→90` (bgid déclare 90/92 seulement).

**(c) Ampleur de la sur-propagation immat par alias-bgid sur DL (E2)**
**23 adresses** portent un immat hérité via bgid (dont **19 en `num_voie` strict**). Tranchées en LIVE pour les 5 S1 : 3 légitimes / 2 fantômes. Les 14 autres `num_voie` hors-S1 restent à auditer (probables suffixes-façades légitimes pour la plupart, mais non vérifiés ici).

**(d) Cause exacte du doublon d'îlot**
Deux entités "121 Charial" coexistent : le **vrai 121** (bgid AX8P / parcelle DT0120 / îlot **34**) et les **phantom 121A-D** (bgid G1YT = bâti 90-92 / parcelle DT0089 / îlot **39**, immat fantôme, tagués social). Le numéro 121 apparaît donc dans 2 îlots. Le doublon est **structurel (bgid)**, pas dû à la fusion.

**Le fix_fusion_s1 déjà appliqué est-il correct ?**
- **CORRECT pour 3 groupes** : 6B Ste Anne, 19B St Antoine, 28B Pionchon (vraies co-immat confirmées BDNB ; fusion légitime, parc/ventes-neutre).
- **À CORRIGER pour 2 groupes** :
  - **G1YT (121A-D → 90)** : à **EXCLURE** du fix_fusion_s1. Traiter en **dé-association** (retrait immat fantôme + correction bgid faux-matching). Sinon : 4 unités sociales fantômes se retrouvent fusionnées sous une ancre non-sociale (90), et le doublon 121 (îlots 34/39) reste masqué au lieu d'être résolu.
  - **RBD4 (11B → 23 ST MAXIMIN)** : même nature de fantôme (bgid ne déclare pas 11/11B ; vrai 11 dans bgid 29R7). À **EXCLURE** également et traiter en dé-association. (11B est par ailleurs taguée `cible_0vente_active` en KV, distincte de l'ancre.)

**Recommandation nette sur G1YT : DÉ-ASSOCIER, ne pas fusionner.** Et étendre la même décision au groupe 11B (2e fantôme symétrique). Les 3 autres groupes S1 peuvent rester fusionnés.

---

### Annexe — méthode / reproductibilité
- Détection S1 : groupage des unités rendues (non-secondaires) par `batiment_groupe_id` sur `.prefusions1.bak`, filtre `len≥2` + immat unique non-null (réplique exacte de `fix_fusion_s1_immat.py` l.78-91) → 5 groupes.
- Preuve d'appartenance bgid : **BDNB LIVE** `batiment_groupe_complet?select=batiment_groupe_id,l_libelle_adr&batiment_groupe_id=eq.<bgid>` (liste des façades BAN réellement portées par le bgid) — **test discriminant**.
- Preuve parcelle : **BDNB LIVE** `rel_batiment_groupe_parcelle` (bgid→parcelle), conversion `69383000`→`69123383`, vs **RNC LIVE** `reference_cadastrale_1/2/3` (resource `3ea8e2c3-0038-464a-b17e-cd5c91f65ce2`, query `numero_immatriculation__exact`). Non-discriminant au niveau bgid (cf. §E1).
- E2 : balayage des 1385 adresses ; critère immat non-null & `_bdnb_match≠immat` & cle absente de `coproprietes[]`.
- E3 : comparaison `_ilot` light + `assignments[cle].ilot` KV (tous None côté KV pour CHARIAL → îlot effectif = `_ilot` light).
- Preuve LOCALE seule = insuffisante (copros sans `reference_cadastrale`/`adresse_complementaire`) ; la conclusion repose sur la preuve **LIVE** BDNB+RNC.
