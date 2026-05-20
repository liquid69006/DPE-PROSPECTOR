# Pipeline secteur — stratégie & conventions

Référence durable de la stratégie de génération/maintenance des
fichiers `secteur_<secteur>_light.json` (onglet **Secteur Prospector**
de `index.html`). Deux secteurs : `dauphine_lacassagne` (Lyon 3e),
`motte_picquet` (Paris 7e/15e).

## 1. Architecture

```
 SOURCES (hors dépôt, locales : data/secteur_*.json, dvf_*.json,
          bdnb_*.json, WFS IRIS, BAN)
        │
        ▼
 make_light.py  /  make_light_motte_picquet.py     ◀── HORS DÉPÔT
   (générateur de BASE, non versionné)                  (~/…/*.py)
        │  écrit data/secteur_<sec>_light.json (indent=2, UTF-8)
        ▼
 CHAÎNE de correctifs ADDITIFS (scripts/, versionnés)
   appliqués en séquence, chacun .bak + dry-run + --apply
        │
        ▼
 data/secteur_<sec>_light.json  ──fetch──▶  index.html renderSecteur()
                                            (Cloudflare Worker)
```

- **`make_light*.py` est HORS DÉPÔT** (`C:\Users\Station 5\*.py`) :
  non versionné, mais **source-of-truth** des règles structurelles.
- Les correctifs `scripts/fix_*.py` / `propage_*.py` SONT versionnés
  et appliqués **par-dessus** la base, dans l'ordre.

## 2. Contrat « correctif additif non destructif »

Tout `scripts/fix_*.py` / `propage_*.py` respecte :

1. **Dry-run par défaut**, écriture seulement sur `--apply`.
2. **Backup** distinct `.<nom>.bak` (écrit une fois ; les passes
   incrémentales le conservent — git versionne les états committés).
3. **Idempotent** : recalcul complet à chaque passage ; rejouer ne
   change rien.
4. **Additif** : on n'écrase JAMAIS un champ autoritatif
   (`ventes_par_an`, `nb_ventes_total`, `nb_lots_habitation`…). On
   AJOUTE des champs (`*_logement`, `usage_principal_bdnb`,
   `_fusion_*`…) ou on retire des artefacts confirmés.
5. **Trace** : note `metadata._correctif_<nom>` décrivant l'effet.
6. **Preuve de non-régression** : `node scripts/test_render_secteur.js`
   (+ `SECTEUR=motte_picquet`) doit sortir **exit 0** sur les 2
   secteurs après apply.

## 3. Décision SURGICAL vs REGEN (importante)

Une **régénération complète** = relancer `make_light*.py` → **écrase**
le light et **NE reproduit PAS** les correctifs additifs empilés,
notamment `usage_principal_bdnb` **dont dépend la bascule LIVE**
(affichage logements), plus taux_logement / hors-RNC / Meynis /
Dupleix… → régression majeure + dashboard cassé.

➡️ **Règle** : pour corriger un cas, on fait un **correctif
chirurgical additif** sur le light courant (préserve l'empilement,
diff minimal, vérifiable), **PAS** de regen destructif. Le fix est
aussi porté **à la source** dans `make_light*.py` (guard / ALIAS_RNC
/ COPRO_FORCE) pour qu'une regen future soit correcte — mais une
regen complète exigerait toujours de **rejouer toute la chaîne**
`fix_*`/`propage_*` (cf. §5).

## 4. Source-of-truth dans make_light*.py (hors dépôt)

Tables curées (style projet, documentées en commentaire) :

- `ALIAS_RNC = {cle_DVF: cle_adresse_copro}` — adresse DVF fantôme
  → copro réelle (ex. `10|RUE|MEYNIS`→`10|PASSAGE|MEYNIS`,
  `28|RUE|DUPLEIX`→`28|PLACE|DUPLEIX`). Aussi **multi-voie** :
  rattache un grand ensemble RNC éclaté sur plusieurs voies à son
  anchor copro quand bgid multiples (pas de bgid commun → ni
  fusion-bgid ni `FUSION_RNC_EXTRA_NUMS`). Ex. **ARMONIAL I**
  `AA0646265` (592 lots, ancre `16|BOULEVARD|GARIBALDI`, `nb_compl=14`
  tronqué) : 15 cles Carrier-Belleuse/Cèpre/Miollis → l'anchor
  (`fix_armonial`). Parc : co-occupés neutres, bgid intégralement
  absorbés subsumés par les lots RNC (dédup §6, comme Acollas).
- `COPRO_FORCE = {cle: immat}` — désambiguïse 2 copros même clé.
- (DL+MP) `FUSION_RNC_EXTRA_NUMS = {immat: {nums}}` — copros dont le
  RNC **tronque l'énumération des entrées** : nom portant une plage
  (« 4-10 », « 39-43 ») et/ou `adresse_complementaire_1/2/3` (3 slots
  open-data) ne listant qu'un sous-ensemble → la fusion RNC
  multi-numéros n'agrège qu'une partie **et consomme les bornes**, si
  bien que l'entrée médiane non listée reste isolée (même quand elle
  partage le bgid de la copro, la fusion-bgid l'ignore : déjà
  consommée / seule dans son groupe). Réinjecte les numéros manquants
  dans le **groupe de fusion RNC** (même chemin que le frère fusionné
  — PAS `ALIAS_RNC`, qui passerait par le chemin immat). Effet parc
  conforme §6 RNC-prioritaire : si bgid distinct, le bucket BDNB est
  subsumé par les lots RNC (retrait d'un double-comptage) ; si bgid
  déjà commun, **strictement parc-neutre** (déjà dédupé). Ex. :
  `AB1301613` « 4-10 AV EMILE ACOLLAS » `{4,6}` (MP, −34 lgts dédup) ;
  `AJ0217901`/`AB9349846` « 39-43 RUE GUILLOUD » `{41}` (DL,
  parc-neutre — double immatriculation, bgid commun) ;
  `AC6299499`{61}/`AF9892365`{43}/`AA1834670`{63}/`AF2096014`{16}
  (MP, lot parc-neutre — bgid déjà commun, instruits cas par cas) ;
  `AB0577296`{38}/`AA3511300`{135} (MP, parc-neutre **mesuré** — bgid
  distinct mais co-occupé par une autre copro RNC qui maintient le
  bucket parc ; instruits cas par cas, `AD5922125` exclu car fix
  lossy : copro 3 lots, bgid sans co-occupant).
- (MP) `VOIES_HORS_SECTEUR = {SEVRES, EGLISE, MAINE}` +
  `NO_VOIE_FICTIF_MIN = 9000` — garde en tête de boucle d'adresses :
  rejet **à la source** des artefacts hors-périmètre (voies réelles
  hors sous-secteur mal géocodées + codes voie DVF fictifs ≥9000),
  **défensif** (jamais de RNC écarté : `copro_by_cle` vérifié).
  *Validé* : regen complète isolée → 0 artefact, 0 RNC perdu.
- (MP) tri de la principale fusion-bgid priorise l'adresse portant
  une copro (`copro_by_cle`) — garantit la bonne résolution copro.

## 5. Chaîne des correctifs (ordre réel, par secteur)

`metadata` liste les correctifs dans l'ordre d'application.

**Dauphiné-Lacassagne**
`make_light.py` → `fix_rnc_bdnb_attribution` (_correctif_rnc_immat) →
`fix_invisible_insecteur_bgids` (_correctif_invisible_insecteur) →
`fix_horsrnc_attribution` (_correctif_horsrnc) →
`fix_doublon_adresse` (_correctif_doublon) →
`fix_taux_logement` (_correctif_taux_logement) →
`propage_usage_bdnb` (_correctif_usage_bdnb) →
`fix_meynis_phantom` (_correctif_meynis) →
`fix_guilloud_range` (_correctif_guilloud) →
`fix_alias_rnc_meme_bgid` (_correctif_alias_bgid) →
`fix_repoint_p2a` (_correctif_repoint_p2a)

**Motte-Picquet**
`make_light_motte_picquet.py` → `fix_rnc_bdnb_attribution`
(_correctif_rnc_immat) → `fix_horsrnc_attribution`
(_correctif_horsrnc) → `fix_taux_logement` (_correctif_taux_logement)
→ `propage_usage_bdnb` (_correctif_usage_bdnb) →
`fix_dupleix_phantom` (_correctif_dupleix) →
`fix_horsperimetre_mp` (_correctif_horsperimetre) →
`fix_acollas_range` (_correctif_acollas) →
`fix_mp_ranges_pn` (_correctif_mp_ranges) →
`fix_mp_ranges_b` (_correctif_mp_ranges_b) →
`fix_armonial` (_correctif_armonial) →
`fix_mp_cibles_horsrnc` (_correctif_cibles_horsrnc) →
`fix_alias_rnc_meme_bgid` (_correctif_alias_bgid) →
`fix_mp_voie_abrev` (_correctif_voie_abrev) →
`fix_repoint_p2a` (_correctif_repoint_p2a) →
`fix_detrie_repoint` (_correctif_detrie)

Backups `.bak` correspondants : `.bak` (pré-1er correctif),
`.pretauxlog.bak`, `.prehorsrnc.bak`, `.predoublon.bak`,
`.preusage.bak`, `.premeynis.bak`, `.predupleix.bak`,
`.prehorsperim.bak`, `.preacollas.bak`, `.preguilloud.bak`,
`.prempranges.bak`, `.prempb.bak`, `.prearmonial.bak`,
`.precibleshr.bak`, `.prealiasbg.bak`, `.prevoieabrev.bak`,
`.prerepointp2a.bak`, `.predetrie.bak` (gitignorés, locaux).
`SECTEUR=<sec>` pilote les scripts génériques.

`fix_alias_rnc_meme_bgid` (lot ALIAS_RNC même-bgid, parc-neutre) :
DL 36 + MP 14 adresses hors-RNC à ventes DVF, copro prouvée BDNB
`rel_batiment_groupe_rnc` ET **même `batiment_groupe_id`** que
l'ancre → relocalisation ventes, **parc strictement inchangé**
(le script ABORT si le modèle parc ≠ 0). Source : audit exhaustif
`scripts/audit_horsrnc_dvf.py` (rapports `data/audit_horsrnc_dvf_*`).
`test_render_secteur.js` : 2 baselines hardcodées **rebasées**
(2026-05-19, §7) — la ligne origine `5|RUE|MONTBRILLANT` est
désormais légitimement fusionnée par ce lot (B3 : on vérifie
l'origine *rendue OU fusionnée*) ; l'invariant « adresses rendues
monotones » devient « parc monotone » car une fusion ALIAS
**réduit** le nombre de lignes rendues (relocalisation, parc/ventes
conservés).

`fix_mp_voie_abrev` (_correctif_voie_abrev, MP, 2026-05-19) : 5
adresses DVF dont la **clé abrège la voie** (`CAPT`→`CAPITAINE`,
`GAL`→`GENERAL`) — make_light apparie la copro par `cle_adresse`
exacte / ALIAS_RNC **sans normalisation**, d'où échec d'immat et
chute au palier GPS aveugle. Copro prouvée immatriculée & présente
au snapshot → ALIAS_RNC **miroir bgid** (chemin immat, cf.
`fix_dupleix`/A2). **+4 dépendances** : un fantôme auto-fusionné
*dans* 4 des 5 cibles est re-pointé **individuellement** vers SA
copro (PIPELINE §9.5 ; `1|RUE|CAPT SCOTT`, 8 v_log → copro propre
`AF6894638`, **pas** `3 CAPITAINE`). Parc modèle `29004→28973`
(**−31** = retrait de 2 doublons BDNB `2C94` 15 / `8J73` 16, la
copro reste comptée via ses lots RNC à l'ancre — **aucune perte**).
Source : `scripts/diag_orphelines_bdnb.py` +
`scripts/fix_mp_voie_abrev.py` (`data/audit_orphelines_bdnb_motte.md`,
`data/dryrun_mp_voie_abrev.md`). `test_render_secteur.js` : **pas de
rebase** (baselines déjà tolérantes à la réduction de lignes par
fusion ALIAS — exit 0 les 2 secteurs, `secL == réplique exacte`).

`fix_repoint_p2a` (_correctif_repoint_p2a, DL+MP, 2026-05-20) : **4
RE-POINT A3** (3 DL + 1 MP) — copros RNC ancrées enterrées sous un
fantôme DVF principal (auto-bgid-fusion a choisi le phantome + ventes
comme principal au lieu de la copro `cle_adresse`). Pattern A3
identique à `fix_mp_cibles_horsrnc`. Audit source =
`scripts/audit_lacunes_pipeline.py` (P2a, 5 cas, **Grenelle écarté
provisoirement** : switch BDNB 89→RNC 35 = −54 sur bgid F3HZ ; nom
copro contient « MS103738 » → hypothèse logement social hors-syndic, à
vérifier RPLS avant intégration). Effet : DL `22268→22267` (−1, neutre
au lot près), MP `28980` (+7 Guesclin, RNC 104 > BDNB 97). 4 copros
aujourd'hui invisibles redeviennent visibles (LE BEAUBOURG @ 51
Richerand, LES PINS @ 54 Lacassagne, RESIDENCE 318 PAUL BERT,
Résidence Du Guesclin @ 3 Passage Guesclin). Source-of-truth déjà en
place (critère `copro_by_cle` du tri principal-bgid de make_light,
introduit pour Dupleix) — une regen résoudrait naturellement ces cas
pour autant qu'elles soient dans le bgid group à temps (cas P2b
exclus = ajout post-make_light). `test_render` exit 0 les 2 secteurs.

## 6. Règles de calcul (renderSecteur, index.html)

- **Parc** dédupliqué par **bâtiment** : clé `bg:<bgid>` (un bâti
  compté 1×), sinon `rnc:<immat>`, sinon `adr:<cle>`. Valeur :
  Σ lots RNC (`nb_lots_habitation`) **prioritaire** ; sinon, si bâti
  **résidentiel** (`usage_principal_bdnb` ∈ Résidentiel
  collectif/individuel) → `nb_log_bdnb` ; sinon **0** (tertiaire /
  secondaire / dépendance / inconnu / social non distinguable).
- **Header = Σ IRIS = Σ adresses** (même base à tous niveaux).
- **Ventes** : `ventes_par_an` (brut) / `ventes_par_an_logement`
  (strict, toggle « Ventes strictes » ON par défaut). Les fusions
  (`secteurFusions` manuel, `_fusion_auto` BDNB même bgid)
  **relocalisent** les ventes vers la copro **sans** toucher le
  parc (dédup `bg:bgid`) → conservation prouvée.
- **Filtre « Hors-RNC actifs »** : `!coproByCle[cle]` &
  `!numero_immatriculation` & `nb_ventes_logement>0`.

## 7. Vérification

`scripts/test_render_secteur.js` **extrait la vraie `renderSecteur()`**
d'`index.html` (plages de lignes codées en dur — **resynchroniser
après toute édition d'index.html**) et l'exécute en `vm` headless
sur les 2 secteurs + .bak. Invariants : pas d'exception, lignes
injectées rendues, anti-double-rendu copro, agrégats monotones,
toggle strict, **réplique exacte de la règle parc** (secL ==
attendu, écart 0), filtre hr-actif == prédicat data. Toute
modif comportementale de `renderSecteur()` ⇒ resync des plages SRC
+ rebase éventuel des baselines hardcodées (documenter le pourquoi).

## 8. Caveats

- `make_light*.py` **hors dépôt** : sauvegarder/versionner à part ;
  un poste sans ces fichiers ne peut pas regénérer.
- Une regen complète **n'est jamais faite sur la production** : la
  valider en **isolation** (OUT redirigé vers un scratch), puis
  rejouer la chaîne §5 si rebuild réellement voulu.
- `index.html` modifié ⇒ `deploy-worker.yml` redéploie le Worker.
- Logement social : **pas** de champ BDNB dédié (open data) →
  compté résidentiel (approx. documentée, volume marginal ;
  alternative = référentiel RPLS externe).

## 9. Workflow d'affinage post-génération

Boucle itérative d'**amélioration de la couverture RNC** appliquée
*par-dessus* le light généré (jamais de regen, cf. §3). Chaque passe
réduit le résiduel hors-RNC à ventes DVF en relocalisant des
adresses fantômes vers leur copropriété réelle. Ordre invariant :

1. **Cibler.** Extraire les adresses *Hors-RNC actives* = prédicat
   exact de `renderSecteur` (`!fusedSrc` & clé ∉ `cle_adresse`
   copro & `!numero_immatriculation` & `nb_ventes_logement>0`).
   C'est le seul périmètre pertinent (le filtre brut `!immat &
   vlog>0` sur-compte les adresses déjà appariées/fusionnées).

2. **Résoudre la copro** par preuve, dans l'ordre de fiabilité
   décroissante (`scripts/audit_horsrnc_dvf.py`) :
   a) BDNB `rel_batiment_groupe_rnc` (cache `_horsrnc_bdnb_live*`)
      → immat ∈ `coproprietes[]` ;
   b) variante orthographique **exacte** de `cle_adresse`
      (AIRES↔AYRES, GAL↔GENERAL, ST↔SAINT, particules) ;
   c) proximité GPS < 30 m + même voie ;
   d) RNC open data live (tabular-api RNIC `3ea8e2c3…`,
      `code_postal_adresse` + `adresse_reference`/compl.).

3. **Stratifier par sûreté-parc (RÈGLE CARDINALE).** Une cible
   n'est rattachable **en sécurité** que si l'identité est *forte* :
   immat BDNB-rel, OU ortho exacte, OU **même `batiment_groupe_id`**
   que l'ancre (= même bâti → parc-neutre). La **proximité GPS
   seule est destructrice** : elle apparie des bâtiments DISTINCTS
   voisins → on retire leur `nb_log_bdnb` réel sans que la copro le
   gagne (mesuré : −514 DL / −423 MP en lot complet). Toujours
   **modéliser le parc par strate** (`parc_model` répliquant §6)
   *avant* de conclure. `strong` = a/b/`same_bgid` ; `weak` =
   GPS/fuzzy/live → **piste prospection manuelle, jamais en masse**.

4. **Dry-run + validation.** Script `fix_*` dédié, dry-run par
   défaut (contrat §2), table complète (cible→ancre+immat+syndic+
   lots+ventes), **gardes anti-collision** (ancre présente & non
   fusionnée & ≠ cible ; aucune adresse fusionnée *dans* la cible ;
   ABORT si modèle parc ≠ attendu). Présenter le bilan, attendre le
   feu vert utilisateur (jamais d'`--apply` non validé).

5. **Mécanismes** (cf. §4) : `ALIAS_RNC même bgid` (parc-neutre,
   lot bulk-sûr) ; `ALIAS_RNC miroir bgid` (dédup BDNB, ≈ retrait
   d'un double-comptage) ; `RE-POINT` (ancre copro enterrée dans un
   fantôme principal-de-fusion → on inverse ; cas par cas) ;
   `FUSION_RNC_EXTRA_NUMS` (énumération RNC tronquée). Les `weak`
   et `RE-POINT` s'instruisent **individuellement**, pas en lot.

6. **Appliquer (additif) + prouver.** `--apply` (backup `.bak`
   dédié, note `_correctif_*`, source-of-truth dans `make_light*`
   §4) puis **non-régression obligatoire** `test_render_secteur.js`
   (2 secteurs, exit 0). Vérifs fortes attendues : parc == attendu
   (souvent strictement neutre), Σ`nb_ventes_total`/`_logement`
   **inchangées** (relocalisation, pas création), 0 double-rendu,
   `secL == réplique exacte`.

7. **Rebaser le harnais si besoin (§7).** Un correctif de
   **fusion** casse les baselines qui supposent que les correctifs
   n'*ajoutent* que des lignes : il **réduit** le nombre de lignes
   rendues (relocalisation). Rebaser les assertions hardcodées
   obsolètes (ex. « ligne origine X rendue » → « rendue **ou**
   fusionnée » ; « adresses monotones » → « parc monotone ») **en
   conservant les invariants réels** (parc/ventes conservés,
   `secL` exact) et **en documentant le pourquoi** (date + cause).

8. **Tracer.** PIPELINE §5 (chaîne + `.bak`), `metadata.
   _correctif_*`, mémoire projet (faits durables + gotchas, pas ce
   que le dépôt enregistre déjà). Commit (et push si demandé).

> Résiduel assumé après une passe : `weak` = leads manuels ;
> `RE-POINT` non instruits ; **B** = monopropriétés / copros non
> immatriculées confirmées (BDNB ∅, ortho ∅, GPS ∅, RNC live ∅) —
> structurellement hors-RNC, **rien à faire**.

---
*Doc de référence — tenir à jour à chaque nouveau correctif
(ajouter à §5, créer le `.bak`, la note `_correctif_*`, vérifier
exit 0).*
