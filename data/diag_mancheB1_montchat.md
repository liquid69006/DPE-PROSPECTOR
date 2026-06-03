# Diag Manche B1 — Résorption orange STRUCTUREL MONTCHAT (passes hors-RNC)

> **Phase 5, Manche B1.** Production des sidecars BDNB-live Montchat + lancement
> des 2 passes structurelles différées en Phase 2 (`fix_horsrnc_attribution` +
> `fix_invisible_insecteur_bgids`), version `_montchat`. **AUCUN commit / git add /
> push.** DL/MP et `index.html` non touchés. PYTHONUTF8=1, prints ASCII-safe.
> Date : 2026-06-03. **PAS de split mono/copro_non_immat** (= Manche B2).

---

## ÉTAPE 1 — Playbook DL hors-RNC (READ-ONLY) + risque double-comptage

### Chaîne réelle (producteurs live → consommateurs)

Les 2 passes « différées » ne lisent PAS l'API directement : elles consomment des
**sidecars produits par 2 passes de vérification BDNB-live** (lecture seule). La
chaîne complète :

| Script | Rôle | Champ posé / produit | Générique re-pointable ? | Re-point Montchat |
|---|---|---|---|---|
| `verif_horsrnc_bdnb.py` | **producteur** sidecar hors-RNC. Pour chaque bgid d'adresse hors-RNC : query `rel_batiment_groupe_rnc` (immats many-to-many) + `batiment_groupe_rnc` (nom/nb_log) | écrit `_horsrnc_bdnb_live{_SUF}.json` = `{bgid: {immats:[...], meta:{...}}}` | **GÉNÉRIQUE** (`os.environ["SECTEUR"]`, cache resumable) | `SECTEUR=montchat python ...` → `_horsrnc_bdnb_live_montchat.json` |
| `evalue_rattach_horsrnc.py` | aide dry-run (réplique dedup parc, verdicts PROPRE/DÉJÀ-COMPTÉ) | rapport `.md` seulement | DL-hardcodé (chemins en dur) **mais lecture seule, non requis** | non répliqué (la logique de verdict est DÉJÀ embarquée dans le consommateur `fix_horsrnc_attribution`) |
| `fix_horsrnc_attribution.py` | **consommateur** : rattache copro RNC INVISIBLE (cle_adresse orpheline) au bgid déjà porté par une adresse hors-RNC | injecte ligne `adresses` avec `numero_immatriculation`, `nb_lots_habitation`, `batiment_groupe_id`, `_bdnb_match=immat_horsrnc_fix` | **GÉNÉRIQUE** (SECTEUR-param, 0 table ALIAS, 0 adresse curée) | copie `fix_horsrnc_attribution_montchat.py` (chemins figés montchat, backup `.premancheB1.bak`, trace `_correctif_horsrnc_montchat`) |
| `verif_rnc_bdnb_live.py` | **producteur** sidecar invisible. Pour chaque copro RNC : query `rel_batiment_groupe_rnc?numero_immat=eq.X` → bgids live ABSENTS du snapshot | écrit `_rnc_bdnb_live_missing{_SUF}.json` = `{immat: [bgid_manquants]}` | **GÉNÉRIQUE** (`os.environ["SECTEUR"]`) | `SECTEUR=montchat python ...` → `_rnc_bdnb_live_missing_montchat.json` |
| `fix_invisible_insecteur_bgids.py` | **consommateur** : copro invisible dont le bâti in-secteur est au snapshot sous immat jumelle | injecte ligne `adresses` `_bdnb_match=immat_live_fix` | **DL-spécifique** (BDNB/LIGHT/SIDECAR en dur + garde libellé `"69003"`) | copie `fix_invisible_insecteur_bgids_montchat.py` (chemins montchat ; garde CP 69003 conservée car Montchat = Lyon 3e CP 69003) |

### CRUCIAL — Risque double-comptage & redondance avec make_light_montchat

**Que font RÉELLEMENT ces 2 passes, vs ce que make_light a déjà fait ?**

`make_light_montchat` fait DÉJÀ la jointure BDNB (chaque adresse a `nb_log_bdnb`
+ `batiment_groupe_id`). Les 2 passes n'ajoutent PAS de bâtiment au parc : elles
**rendent visibles des COPROS RNC** dont la `cle_adresse` était orpheline (jamais
liée à une ligne `adresses`) en injectant une ligne `adresses` portant
`numero_immatriculation`. Le bgid est **déjà compté** dans le parc (via la cle
`bg:<bgid>` de la dedup `renderSecteur`) — la valeur du bâti **bascule seulement**
de l'estimation `nb_log_bdnb` vers les **lots RNC prioritaires** (même clé `bg:`).

**Garde-fou anti-double-comptage (vérifié dans le code)** : le consommateur
`fix_horsrnc_attribution` **rejette** (`DEJA-COMPTE`) toute copro dont le bgid porte
déjà une copro RNC **visible** (sinon on sommerait deux fois les lots). Invariants
durs (assert) : bgid in-secteur, cle injectée unique et absente. → **pas de
nouveau bâtiment, pas de re-comptage** : la hausse parc = uniquement le **switch
BDNB→RNC** par bgid (peut être positif OU négatif si RNC < estimation BDNB).

**Redondance** : la passe `invisible_insecteur` est **entièrement redondante avec
la jointure BDNB de make_light_montchat pour ce secteur** (voir ÉTAPE 3 : 0 CLEAN —
tous les bgids jumelles in-secteur étaient déjà capturés). La passe `horsrnc`, elle,
n'est PAS redondante : elle attrape 29 copros RNC dont la `cle_adresse` n'a jamais
été appariée (lien raté du pipeline), invisibles malgré la jointure BDNB.

---

## ÉTAPE 2 — Sidecars BDNB-live Montchat produits

Périmètre interrogé : les 672 bgids distincts des 807 adresses hors-RNC + les
633 copros immatriculées du light (INSEE 69383/69388, CP 69003). API ouverte
`api.bdnb.io` (sans clé), caches resumables.

| Sidecar produit | Producteur | Volume |
|---|---|---|
| `data/_horsrnc_bdnb_live_montchat.json` | `verif_horsrnc_bdnb.py` (SECTEUR=montchat) | **672 bgids** interrogés. 171 adr hors-RNC ont ≥1 immat RNC côté BDNB ; **36 adr → 30 copros INVISIBLE** (« lien raté » = cibles `horsrnc`) ; 132 adr → copro déjà visible (cosmétique) ; 9 adr → immat hors registre |
| `data/_rnc_bdnb_live_missing_montchat.json` | `verif_rnc_bdnb_live.py` (SECTEUR=montchat) | **633 copros** vérifiées ; 27 copros où le snapshot a omis des bâtiments → **28 bgids live absents du snapshot** (cibles `invisible_insecteur`) |

Rapports `.md` également écrits : `verif_horsrnc_bdnb_report_montchat.md`,
`verif_rnc_bdnb_live_report_montchat.md`.

---

## ÉTAPE 3 — Les 2 passes version Montchat (dry-run → apply)

Scripts créés (in-repo, NON commités) :
`scripts/fix_horsrnc_attribution_montchat.py`,
`scripts/fix_invisible_insecteur_bgids_montchat.py`. Tables ALIAS DL : N/A
(aucune dans ces 2 scripts). Backup commun **`.premancheB1.bak`** (créé par la
passe horsrnc, jamais écrasé par la suivante).

### Passe 1 — `fix_horsrnc_attribution_montchat` (DRY-RUN puis APPLY)

- **30 copros invisibles candidates** → **29 à injecter (PROPRE)** + **1 rejet
  `DEJA-COMPTE`** (`AD5172010`, sibling visible `AD0026757` sur bgid `HUMZ` →
  correctement écartée, anti-double-comptage).
- Lots RNC rendus visibles : 499. **Δ parc NET estimé : +24** (estimation du script).
- APPLY : **1401 → 1430 adresses** ; backup `.premancheB1.bak` créé ;
  trace `metadata._correctif_horsrnc_montchat` posée.
- **Idempotent** : re-run dry-run → 0 à injecter (1 candidate = le reject DEJA-COMPTE).

### Passe 2 — `fix_invisible_insecteur_bgids_montchat` (DRY-RUN puis APPLY)

- 28 bgids cibles → **0 CLEAN** (rien à injecter). Ventilation des SKIP :
  ~14 `SKIP_DEJA_COMPTE` (bgid déjà dans une adresse = make_light l'a déjà capté),
  ~10 `SKIP_HORS_SNAPSHOT` (bgid hors périmètre Montchat : Albert Thomas / Bara /
  frontière DL, absents de `bdnb_montchat.json`), 2 `SKIP_COPRO_DEJA_VISIBLE`.
- APPLY : **no-op** (« Rien à appliquer ») — light non modifié, **aucune trace
  `_correctif_invisible_montchat`** posée (comportement idempotent correct).
- **Conclusion** : passe **redondante avec la jointure BDNB de make_light_montchat**
  pour ce secteur. Tous les bgids jumelles in-secteur étaient déjà présents.

---

## ÉTAPE 4 — Vérifications

### Hors-RNC attribuées / restantes ; pile orange

**Définition dashboard** : hors-RNC = `cle ∉ coproprietes[]` **ET** pas de
`numero_immatriculation`. Orange = hors-RNC + (`nb_ventes_logement>0` OU `nb_log_bdnb>1`).

| | adresses | hors-RNC | orange |
|---|--:|--:|--:|
| AVANT B1 (`.premancheB1.bak`) | 1401 | 771 | **530** |
| APRÈS B1 | 1430 | 771 | **530** |
| Δ | +29 | **0** | **0** |

> **Point important (non-blocage, comportement documenté du script)** : la passe
> `horsrnc` rend visibles **29 COPROS** (en injectant une NOUVELLE ligne `adresses`
> dont `cle = cle_adresse` de la copro), mais **ne supprime/fusionne PAS** la ligne
> hors-RNC d'origine (au numéro de base) qui portait le bgid. Cette ligne garde sa
> propre `cle` sans immat → reste hors-RNC. C'est explicite dans la NOTE du script
> (« le bâti apparaîtra en 2 lignes ; doublon VISUEL ; fusion auto = changement
> séparé »). **La pile orange par la métrique hors-RNC stricte est donc INCHANGÉE
> (530)** : la valeur structurelle de B1 est de rendre 29 copros RNC visibles
> (+parc, autorité RNC), PAS de vider le compteur orange. Le vidage orange relève
> de la fusion / du split de Manche B2.
>
> (manche0 annonçait 536 ; la valeur réelle pré-B1 est **530** — l'écart vient des
> 2 INJECT + rebinds de Manche A appliqués depuis la cartographie manche0.)

### PARC — secL avant → après, DÉCOMPOSÉ + preuve 0 double-comptage

**Source d'autorité** : `secL` est normalement calculé par
`scripts/test_render_secteur.js` (qui extrait `renderSecteur()` d'`index.html`).
**Ce test lève actuellement une exception sur DL ET Montchat** (`Unexpected
token '}'` / `ReferenceError: sctClassAnnuel`) : c'est le **gotcha documenté**
(plages de lignes codées en dur dans le test, dérivées depuis une édition
d'`index.html`). **Breakage PRÉ-EXISTANT**, identique sur DL (light jamais touché
par B1) → **hors périmètre Manche B1** (on ne touche pas `index.html` ni les
plages du test). On reproduit donc le calcul via
`scripts/_parc_replique_montchat.py` = **PORT FIDÈLE du bloc `expected` du test**
(lignes 357-433, REBASE 2026-05-31, règle 2-passes bgRncLots + bgBdnbResid).
**Validation** : sur le light pré-B1 il rend **15809 exactement** = la valeur
secL faisant autorité en Manche A.

| Parc `secL` | valeur |
|---|--:|
| **AVANT B1** (`.premancheB1.bak`) | **15 809** |
| **APRÈS B1** | **15 848** |
| **Δ** | **+39** |

**Décomposition par bgid (somme des Δ par bgid = +39, EXACTEMENT le Δ secL)** —
chaque ligne est un **switch estimation BDNB → lots RNC sur le MÊME bgid** (mode
APRÈS = RNC partout) :

| bgid | avant | après | Δ | note |
|---|--:|--:|--:|---|
| 9UK8-BZBS-3K3E | 15 | 30 | +15 | 13 DIDAY (RNC 30 > BDNB 15) |
| WD61-MA1W-WWJ2 | 7 | 20 | +13 | 2 ROUX SOIGNAT |
| JKVQ-4C9J-ZEB5 | 0 | 10 | +10 | **NEW** (bgid non résid. avant → 17 FERDINAND BUISSON) |
| XUYG-9RFQ-2893 | 0 | 6 | +6 | **NEW** (21 CYRANO) |
| HGKH / 4XL5 / QCRW / AMBS | … | … | +2 ×4 | switch RNC |
| RKND / 162L / FKDA / N267 / EBED / UV37 | … | … | +1 ×6 | switch RNC |
| KQRW-RM22-LGPD | 3 | 2 | **−1** | RNC < BDNB (72 COURS DOCTEUR LONG) |
| DEXU-MMEQ-6MND | 12 | 10 | **−2** | RNC < BDNB (13 DOCTEUR BONHOMME) |
| 9E4J-8L3P-REUY | 26 | 10 | **−16** | RNC < BDNB (44 ROUTE GENAS « LES AMANDIERS » : BDNB sur-estimait) |

**Σ = +15+13+10+6 +2·4 +1·6 −1 −2 −16 = +39.** → **PREUVE 0 double-comptage** :
17 bgids changent de valeur, **tous** par bascule estimation→RNC sur la même clé
`bg:`. **Aucun bgid n'est compté deux fois** ; 2 bgids « NEW » étaient à 0 avant
(adresse hors-RNC d'usage non-résidentiel ou `nb_log_bdnb=0` → ne contribuaient
pas ; la copro RNC les expose désormais) ; 3 bgids **baissent** (RNC autoritaire
corrige une sur-estimation BDNB). Hausse **entièrement explicable adresse par
adresse** → pas d'alerte.

### Σ ventes — inchangé

| | nb_ventes_logement | nb_ventes_total |
|---|--:|--:|
| AVANT | 932 | 1217 |
| APRÈS | 932 | 1217 |

→ **Σ ventes INCHANGÉ** (les lignes injectées copient les `ventes_par_an*` de la
copro, qui valaient 0 ici, et ne créent/perdent aucune mutation DVF). OUI.

### Orphelins d'îlot

Les 29 lignes injectées arrivaient **sans `_ilot`** (orphelins 41 → 70 transitoire).
Comme des bgid/adresses ont changé, **relance `_apply_ilot_kml_montchat.py
--snap 15 --apply`** (PIP+snap complet, idempotent, backup `.preilot.bak`) :

| | orphelins (null/X) |
|---|--:|
| pré-B1 | 41 |
| post-horsrnc (avant ilot) | 70 |
| **post-ilot (final)** | **40** (38 X + 2 null) |

→ Les 29 injects sont **tous îlotés** ; **1 orphelin net résorbé** (41 → 40).
Parc post-ilot **inchangé = 15 848** (l'îlotage est parc-neutre). 4 îlots vides
inchangés (177/225/230/232).

### `test_render_secteur.js`

| | exit | cause |
|---|--:|---|
| DL (défaut) | **1** | `Unexpected token '}'` / `ReferenceError: sctClassAnnuel` — **plages de lignes du test désynchronisées d'`index.html`** (gotcha documenté). DL non touché par B1 → breakage **pré-existant**. |
| Montchat | **1** | idem (même cause, mêmes plages) |

**Le test n'atteint jamais le calcul de secL** (il lève dans l'extraction de
`renderSecteur`). **Substitut validé** : `scripts/_parc_replique_montchat.py`
reproduit le bloc `expected` du test à l'identique et rend **15809 exactement**
sur le baseline pré-B1 → écart 0 vs la règle 2-passes. **Resync des plages du
test = chantier index.html distinct, hors périmètre Manche B1.**

---

## Fichiers produits (AUCUN commité, AUCUN git add)

In-repo (`DPE-PROSPECTOR\`) :
- `data/secteur_montchat_light.json` (1430 adr, parc 15848)
- `data/_horsrnc_bdnb_live_montchat.json` (sidecar, 672 bgids)
- `data/_rnc_bdnb_live_missing_montchat.json` (sidecar, 27 copros)
- `data/verif_horsrnc_bdnb_report_montchat.md`, `data/verif_rnc_bdnb_live_report_montchat.md`
- `scripts/fix_horsrnc_attribution_montchat.py`, `scripts/fix_invisible_insecteur_bgids_montchat.py`
- `scripts/_parc_replique_montchat.py` (substitut parc, port fidèle du test)
- backups : `secteur_montchat_light.json.premancheB1.bak` (pré-B1, parc 15809),
  `secteur_montchat_light.json.preilot.bak` (post-horsrnc, pré-ré-îlotage)
- `data/diag_mancheB1_montchat.md` (ce rapport)

## Blocages / points à signaler

1. **`test_render_secteur.js` cassé (exit 1) sur DL ET Montchat** : gotcha plages
   codées en dur, **pré-existant** (DL non touché). Non corrigé (toucher
   index.html / le test = hors périmètre B1). Substitut parc validé fourni.
2. **Passe `invisible_insecteur` = no-op (0 CLEAN)** : entièrement **redondante**
   avec la jointure BDNB de `make_light_montchat` pour ce secteur. Trace metadata
   non posée (correct, idempotent). Aucune action requise.
3. **Orange INCHANGÉ (530)** : B1 rend 29 copros visibles SANS vider le compteur
   hors-RNC (la ligne hors-RNC porteuse subsiste, doublon visuel par design). Le
   vidage orange = fusion / split Manche B2. **Pas un blocage** — comportement
   documenté du script. Aucune sur-attribution, aucun double-comptage.
