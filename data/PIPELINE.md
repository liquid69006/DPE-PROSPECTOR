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
  `28|RUE|DUPLEIX`→`28|PLACE|DUPLEIX`).
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
  (MP, lot parc-neutre — bgid déjà commun, instruits cas par cas).
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
`fix_guilloud_range` (_correctif_guilloud)

**Motte-Picquet**
`make_light_motte_picquet.py` → `fix_rnc_bdnb_attribution`
(_correctif_rnc_immat) → `fix_horsrnc_attribution`
(_correctif_horsrnc) → `fix_taux_logement` (_correctif_taux_logement)
→ `propage_usage_bdnb` (_correctif_usage_bdnb) →
`fix_dupleix_phantom` (_correctif_dupleix) →
`fix_horsperimetre_mp` (_correctif_horsperimetre) →
`fix_acollas_range` (_correctif_acollas) →
`fix_mp_ranges_pn` (_correctif_mp_ranges)

Backups `.bak` correspondants : `.bak` (pré-1er correctif),
`.pretauxlog.bak`, `.prehorsrnc.bak`, `.predoublon.bak`,
`.preusage.bak`, `.premeynis.bak`, `.predupleix.bak`,
`.prehorsperim.bak`, `.preacollas.bak`, `.preguilloud.bak`,
`.prempranges.bak` (gitignorés, locaux). `SECTEUR=<sec>` pilote
les scripts génériques.

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

---
*Doc de référence — tenir à jour à chaque nouveau correctif
(ajouter à §5, créer le `.bak`, la note `_correctif_*`, vérifier
exit 0).*
