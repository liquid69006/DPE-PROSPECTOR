# Diag Secteur Prospector — Phase 0 EXPLORE Montchat

> READ-ONLY. Aucune modification de code/donnees. Rapport seul.
> Date : 2026-06-01. Perimetre : mode **Secteur Prospector**, agence `dauphine-lacassagne` (session bufferne), preparation deploiement zone **Montchat** (Lyon 3e) + toggle DL <-> Montchat + ilotage KML 134 ilots.
> Convention preuve : **[PREUVE]** = code/donnee lus ; **[DEDUCTION]** = inference ; **[HORS-DEPOT]** = fichier sur le poste hors repo Git.

---

## TL;DR (reponses au gate G0)

1. **E1 — Sources Montchat = SCRIPT RE-RUNNABLE, pas procurement.** Les entrees de `make_light.py` sont produites par une chaine de scripts **[HORS-DEPOT]** sur le poste (`C:\Users\Station 5\*.py`) : 4 extracteurs (`rnc_extract.py`, `dvf_extract_dauphine.py`, `bdnb_extract_dauphine.py`/`bdnb_extract_motte_picquet.py`, `filosofi_extract.py`) + `secteur_prospector_dl.py` (croisement MAJIC x DVF) -> consolides par `consolidate_secteur.py` en `data/secteur_dauphine_lacassagne.json`. **Le perimetre est defini par un POLYGONE GPS Shapely code en dur dans chaque script** (point-in-polygon), + filtre commune INSEE `69383`. Montchat = **dupliquer ces scripts avec le polygone Montchat** (deja connu : `secteurs.json` + `majic_sci_2025.py`) ; pas de procurement manuel requis (sources nationales telechargees par les scripts). Seul caveat : les sources brutes locales (parquet MAJIC, RNC T3, DVF zip) sont **[HORS-DEPOT]**, c'est Yann qui les a.
2. **E2 — make_light = HARDCODE par zone (pas parametre).** Constantes de chemins/INSEE/polygone/IRIS en dur en tete. MP a son propre fichier separe `make_light_motte_picquet.py`. **Le patron d'ajout d'une zone = dupliquer le fichier** (DL -> MP -> Montchat), pas `--secteur`. (NB : la modularisation `--secteur` existe pour les outils de *qualification* `scripts/`, PAS pour `make_light*`.)
3. **E3 — Couche ilot KML DEJA EXISTANTE pour DL.** `make_light.py` ne pose QUE `code_iris` (WFS IRIS, INSEE `69383` hardcode). Le champ `_ilot` est pose **en aval** par `scripts/_apply_ilot_kml_dl.py` (point-in-polygon KML + snap 5 m + 'X' fallback + arbitrage par-bgid). **C'est exactement le pipeline a recopier pour Montchat** (`_apply_ilot_kml_montchat.py`). L'arbre UI est **ilot top-level** (refactor 2026-05-24), `code_iris` conserve pour stats.
4. **E4 — 3 cles KV Secteur, toutes keyees par AGENCE (pas par zone) :** `secteur_assignments:{agence}`, `secteur_repartition:{agence}`, `secteur_attribution:{agence}`. Side-files locaux : suffixe `_dl` / `_mp`. **Montchat aura besoin d'un suffixe `_montchat`** pour ses side-files, ET d'un namespace KV separe (DEDUCTION : suffixer l'agenceId cote KV, ex `dauphine-lacassagne-montchat`, car le KV n'a aucune dimension zone aujourd'hui).
5. **E5 — Front Secteur = MULTI-AGENCE STRICT, mono-zone-par-agence. PAS multi-zone.** `secteurResolve()` (index.html l.2406) mappe `agenceId -> [fichier, idKV, nom, ville]`, une seule zone par agence. Contrairement a SCI (`#sci-filter-zone`), Secteur n'a **aucun** selecteur de zone ni lecture de `AGENCES_CONFIG.zones`. Le toggle DL/Montchat = **ajout** d'une variable `secteurZone` + extension de `secteurResolve` en table a 2 dimensions (agence x zone) + re-chargement light/KV/titre.
6. **E6 — MP = template COMPLET pour la CHAINE DE FOND, mais PARTIEL pour ilotage + qualification.** MP a : sources extractors, `make_light_motte_picquet.py`, `secteur_motte_picquet_light.json` (1277 adr), entree `secteurResolve`. MP n'a PAS : couche `_ilot` KML (0 `_ilot`, IRIS-only), side-files `_arbitres`/`_cles_invalides`/`_bgid_resolus`/`_nom_ambigu_resolus`, needles metier (TODO parisiennes). **DL reste le template de bout-en-bout (seul a avoir l'ilotage KML) ; MP est le template du dedoublement make_light.**

---

## E1 — DONNEES SOURCES (le point gating)

### La chaine de production (toute [HORS-DEPOT] sur `C:\Users\Station 5\`)

`secteur_dauphine_lacassagne.json` (l'entree `CONS` de make_light) n'est PAS une entree externe : c'est la **sortie de `consolidate_secteur.py`** [PREUVE : `consolidate_secteur.py` l.7 `OUT = ...\data\secteur_dauphine_lacassagne.json`], qui agrege 4 fichiers produits par 4 scripts dedies :

| Sortie (root, [HORS-DEPOT]) | Script producteur | Source nationale | Filtre perimetre |
|---|---|---|---|
| `rnc_dauphine_lacassagne.json` (= bloc `coproprietes`) | `rnc_extract.py` | RNC T3 2025 CSV ANAH (data.gouv, ~452 Mo) [l.20-24] | INSEE `69383` / CP `69003` [l.111] **puis polygone** sur long/lat du registre [l.122] |
| `dvf_dauphine_lacassagne.json` (= bloc `mutations_dvf`) | `dvf_extract_dauphine.py` | DVF DGFiP 2024+2025 .txt.zip (data.gouv) [l.26-29] | commune dep `69`+`383` [l.78] -> geocodage BAN -> **polygone** [l.183] |
| `bdnb_dauphine_lacassagne.json` (= `BDNB` input make_light) | `bdnb_extract_dauphine.py` | API BDNB | (a verifier dans le script ; non lu en detail) |
| `filosofi_dauphine_lacassagne.json` (cle `iris`) | `filosofi_extract.py` (+`filosofi_integrate.py`, `rp_logement_integrate.py`) | INSEE Filosofi IRIS + base logement | IRIS du secteur |
| `secteur_dauphine_lacassagne.json` (cle `adresses`, croisement) | `secteur_prospector_dl.py` | parquet MAJIC `majic_locaux2_2025.parquet` x `dvf_dauphine_lacassagne.json` | INSEE `69383` [l.30] + geocodage BAN -> **polygone** [l.42,194] |
| **`data/secteur_dauphine_lacassagne.json`** (consolide, **IN-REPO**) | **`consolidate_secteur.py`** | les 4 ci-dessus | — (assemble dvf+rnc+filo+crois) [l.43-106] |

[PREUVE] Le polygone DL est **identique** et code en dur (format `[lon,lat]`) dans `rnc_extract.py` (l.26-34), `dvf_extract_dauphine.py` (l.31-39) ET `secteur_prospector_dl.py` (l.33-41). C'est le **meme polygone** que `secteurs.json[dauphine-lacassagne].geo.zones[0]` (format inverse `[lat,lon]`).

### Ces fichiers existent-ils deja pour Montchat ?

[PREUVE] **NON.** `ls data/*montchat*` ne renvoie que `diag_sci_montchat.md` + `plan_secteur_montchat.md`. Aucun `secteur_montchat.json`, `dvf_montchat.json`, `secteur_montchat_light.json`. Cote root : pas de `*_montchat*.json` (seulement DL et motte_picquet).

### CONCLUSION E1 (nette)

**Montchat = RE-RUN d'un SCRIPT sur le nouveau perimetre, pas procurement manuel.** Les scripts telechargent eux-memes les sources nationales (RNC/DVF/BDNB/Filosofi) et filtrent par INSEE + polygone. Le polygone Montchat est **deja connu** (`secteurs.json[dauphine-lacassagne].geo.zones[1].polygone`, 22 sommets ; le KML 134 ilots fournira un decoupage interne plus fin mais l'EMPRISE existe deja). Reserves :
- Les sources brutes locales (parquet MAJIC, CSV RNC T3, zips DVF) sont **[HORS-DEPOT]** : presence a verifier cote Yann (les scripts les telechargent/reutilisent en cache `C:\Users\Station 5\`).
- **Particularite Montchat = INSEE.** Les scripts DL filtrent en DUR sur `69383` (Lyon 3e). Montchat est administrativement Lyon 3e (`69383`) MAIS le plan (l.82) signale un risque de debordement sur le 8e (`69388`). [DEDUCTION] A verifier : si le polygone Montchat reste dans `69383`, le filtre INSEE est inchange ; sinon il faut elargir a `["383","388"]` (les scripts actuels sont mono-INSEE scalaire, `secteurs.json` est deja en LISTE pret a ca).

---

## E2 — PIPELINE PAR-ZONE (`make_light.py` vs `make_light_motte_picquet.py`)

[PREUVE] Les deux fichiers existent : `C:\Users\Station 5\make_light.py` (DL, 57 Ko, modifie 2026-06-01) et `C:\Users\Station 5\make_light_motte_picquet.py` (MP, 47 Ko, 2026-05-20). Tous deux **[HORS-DEPOT]**.

### Hardcode vs parametre

**HARDCODE par zone.** [PREUVE make_light.py l.124-130] :
```
CONS = r"C:\Users\Station 5\DPE-PROSPECTOR\data\secteur_dauphine_lacassagne.json"
DVF  = r"C:\Users\Station 5\dvf_dauphine_lacassagne.json"
BDNB = r"C:\Users\Station 5\bdnb_dauphine_lacassagne.json"
OUT  = r"C:\Users\Station 5\DPE-PROSPECTOR\data\secteur_dauphine_lacassagne_light.json"
WFS  = "...&CQL_FILTER=code_insee=%2769383%27..."   # IRIS Lyon 3e en DUR
```
Aucun argument `--secteur`, aucune lecture de `secteurs.json`. La commune INSEE (`69383`) est cablee dans l'URL WFS. Les tables curees `ALIAS_RNC`, `COPRO_FORCE`, `FUSION_RNC_EXTRA_NUMS` sont specifiques DL (adresses lyonnaises).

> NB important : la modularisation `--secteur` decrite dans `PIPELINE.md` (root) §7 concerne les **outils de qualification** (`scripts/_scan*`, `fix_kv`, `enrich*`, `pipeline.py`, `secteur_config.py`) qui lisent `secteurs.json[<slug>]`. **`make_light*` n'en fait PAS partie** — il est duplique par fichier. [PREUVE : `data/PIPELINE.md` l.15,27 "`make_light*.py` est HORS DEPOT ... non versionne"].

### INPUTS / OUTPUTS exacts

**make_light.py (DL)** — INPUTS : `CONS` (consolide), `DVF`, `BDNB`, WFS IRIS live (l.502), API BAN (geocodage fallback l.93), API BDNB (parcelles l.60), API RNIC tabular live (syndic frais l.26). OUTPUT : `data/secteur_dauphine_lacassagne_light.json`.

**make_light_motte_picquet.py (MP)** — [DEDUCTION, structure miroir] memes types d'entrees pointant vers `secteur_motte_picquet.json` / `dvf_motte_picquet.json` / `bdnb_motte_picquet.json`, WFS sur INSEE `75115`+`75107` (MP est multi-arrondissement). OUTPUT : `data/secteur_motte_picquet_light.json`. (Fichier non lu integralement ; existence + sortie confirmees [PREUVE : `data/secteur_motte_picquet_light.json` 2.2 Mo present].)

### Ce que MP fait DIFFEREMMENT (= patron d'ajout de zone)

[PREUVE chaine `data/PIPELINE.md` §5] MP gere le **multi-arrondissement** (`75115`+`75107`, cf. `secteurs.json` code_commune en liste) et a des tables ALIAS/garde specifiques Paris (`VOIES_HORS_SECTEUR`, `NO_VOIE_FICTIF_MIN=9000`, `fix_horsperimetre_mp`). Le **patron a suivre pour Montchat** : copier `make_light.py` (DL, meme commune `69383`, plus proche geographiquement) -> `make_light_montchat.py`, re-pointer les 4 constantes vers les fichiers Montchat, garder le WFS IRIS `69383`, vider les tables `ALIAS_RNC`/`COPRO_FORCE`/`FUSION_RNC_EXTRA_NUMS` (Montchat part de zero, pas encore de correctifs terrain).

---

## E3 — COUCHE ILOTS (le point cle pour le KML 134 ilots)

### Ce que make_light pose : `code_iris` SEULEMENT (pas `_ilot`)

[PREUVE make_light.py l.501-517] make_light charge la geometrie IRIS via WFS IGN (`code_insee=69383`), construit `irisgeo`, et la fonction `code_iris(lon,lat)` fait un point-in-polygon IRIS (avec fallback IRIS le plus proche au bord). Chaque copro/adresse recoit `code_iris` (l.576, 725). **make_light ne pose AUCUN `_ilot`** — grep `ilot` dans make_light.py ne renvoie que le commentaire docstring l.7 ("arbre IRIS>ilot>adresse").

### Ce qui pose `_ilot` : un script AVAL dedie KML (DEJA EXISTANT pour DL)

[PREUVE] Dans le light DL produit, `_ilot` est present sur **1385/1385** adresses (85 valeurs distinctes). Il est ecrit par **`scripts/_apply_ilot_kml_dl.py`** (et son dry-run lecture-seule `scripts/_join_kml_ilots_dl.py`). Backup `.preilot.bak` present. **C'est le pipeline point-in-polygon KML -> ilot deja en place qu'on reutilise pour Montchat.**

Logique de `_apply_ilot_kml_dl.py` [PREUVE l.1-321], directement transposable :
- Parse 2 KML (`Secteur DL - non raye.kml` + `Secteur DL - raye.kml`) -> polygones Shapely, mapping de renommage `RENAME = {"3A":"3","3B":"13","X":"11"}` (l.35) ;
- **PASS 1** : pour chaque adresse (lon,lat) -> `ilot_pip` (point-in-polygon strict via STRtree, l.81) ; sinon `ilot_snap` (plus proche polygone <= **5 m**, l.90) ; sinon `'X'` (hors-secteur) ; coords absentes -> `null` ; cle malformee -> `null` exclue ;
- **PASS 2** : arbitrage **par-bgid** (majorite des votes d'ilot des adresses du meme batiment, tie-break = ilot contenant le centroide du bati) -> homogeneise les bgids splits + remonte les null/X ;
- `--apply` ecrit `a["_ilot"]` + backup `.preilot.bak`.

> Note : les chemins KML pointent vers `C:/Users/Station 5/Downloads/Secteur DL - ...kml` [HORS-DEPOT] (l.32-33), MAIS les memes KML sont aussi committes dans `data/kml/Secteur_DL_-_*.kml` [PREUVE : `ls data/kml/`].

### Point precis ou brancher les 134 ilots KML Montchat

[DEDUCTION, basee sur le pipeline DL existant] Ordre Montchat :
1. `make_light_montchat.py` -> light avec `code_iris` (WFS `69383`) **conserve** (stats Filosofi/INSEE) ;
2. **puis** un nouveau `scripts/_apply_ilot_kml_montchat.py` calque sur `_apply_ilot_kml_dl.py`, parse `data/kml/Ilotage_Montchat.kml` (134 polygones), applique les 2 fixes du plan (`118->195`, refermer `162` -> a mettre dans `RENAME`/pre-traitement), `code_ilot`/`_ilot` par point-in-polygon, snap **~25 m** (le plan demande 25 m, vs 5 m DL — parametre `SNAP_MAX_M`), `null`+signalement sinon. `code_iris` reste intact.
3. L'arbre UI consomme `_ilot` (cf. E5) ; IRIS sert uniquement aux stats.

[PREUVE] Le champ ecrit est `_ilot` (string `"NN"` / `"X"` / `null`). Le plan parle de `code_ilot` : **conserver le nom `_ilot`** pour rester compatible avec le front (`ilotEffectif`/`renderSecteur` lisent `a._ilot`), OU ajouter `code_ilot` en plus si l'on veut distinguer KML vs IRIS — mais le front actuel attend `_ilot`. [DEDUCTION] Le plus simple = ecrire `_ilot` (134 valeurs Montchat) comme pour DL.

---

## E4 — SORTIES PAR-ZONE (fichiers + cles KV)

### (a) Light JSON + full

[PREUVE] DL :
- full consolide : `data/secteur_dauphine_lacassagne.json` (IN-REPO, produit par `consolidate_secteur.py`)
- light front : `data/secteur_dauphine_lacassagne_light.json` (IN-REPO, produit par `make_light.py`, charge par le front via GITHUB_RAW)

MP (E6) : `data/secteur_motte_picquet.json` (full) + `data/secteur_motte_picquet_light.json` (light).

### (b) Cles KV Secteur EXACTES (worker.js)

[PREUVE worker.js] Trois routes/cles, **toutes keyees par `{agenceId}`** (regex `[a-z0-9-]+`), AUCUNE dimension zone :

| Cle KV (exacte) | Route (regex + methode) | Contenu |
|---|---|---|
| `secteur_assignments:{agenceId}` | `/^\/secteur-assignments\/([a-z0-9-]+)$/` GET/POST (l.609-635) | `{assignments, fusions, noms}` = qualifs/ilot manuel/fusions/noms perso |
| `secteur_repartition:{agenceId}` | `/^\/secteur-repartition\/([a-z0-9-]+)$/` GET/POST (l.646-687) + PATCH `.../ilot` (l.721-740) | repartition ilots -> conseillers (wizard generation) |
| `secteur_attribution:{agenceId}` | `/^\/secteur-attribution\/([a-z0-9-]+)$/` GET/POST (l.696-713) | attribution secteurs -> conseillers (etape 2 wizard) |

[PREUVE] Le front lit `secteur_assignments` via `secteur-assignments/${secId}` ou `secId` vient de `secteurResolve()` (= l'agenceId, index.html l.2449). Pour DL : `secteur_assignments:dauphine-lacassagne`.

**Consequence majeure pour le toggle (DEDUCTION) :** comme le KV est keye par agence et que DL et Montchat partagent la **meme agence** `dauphine-lacassagne`, un toggle naif reutiliserait la MEME cle KV pour les 2 zones -> collision des qualifications. Le plan exige un **namespace KV separe**. Il faut donc forger un `secId` distinct par zone, p.ex. `dauphine-lacassagne` (DL) vs `dauphine-lacassagne-montchat` (Montchat) — la regex worker `[a-z0-9-]+` l'accepte sans changement worker. C'est la facon la plus simple de separer les namespaces sans toucher au worker.

### (c) Side-files locaux par-agence (suffixe de nommage)

[PREUVE `secteurs.json` paths + `ls data/`] Suffixe = **`_dl`** (et chemin agence_slug pour le light). DL a les 5 side-files cables :

| Side-file DL (present) | Role |
|---|---|
| `data/_arbitres_dl.json` | verdict-scope |
| `data/_cles_invalides_dl.json` | deny-list cles malformees |
| `data/_bgid_resolus_dl.json` | re-bind bgid |
| `data/_nom_ambigu_resolus_dl.json` | re-bind nom ambigu |
| `data/_social_overrides_dl.json` | overrides terrain (entrees sacrees) |
| `data/_kv_assign_dl.json` | miroir local KV (anti-drift) |
| `data/_enrich_majic_dl_full.json` | cache enrich MAJIC |
| `data/_bgid_parcelle_dl.json` | cache parcelles |

[PREUVE] MP n'a que `_kv_assign_mp.json`, `_kv_assign_mp.backup_preaudit.json`, `_enrich_majic_mp_full.json` (pas d'`_arbitres_mp`/`_cles_invalides_mp`/`_social_overrides_mp` visible — coherent avec `PIPELINE.md` §9 "MP n'a aujourd'hui que social_overrides").

### Suffixe Montchat a creer

[DEDUCTION conforme convention] Suffixe **`_montchat`** (le plan suggere `_montchat` ou `_mtc` ; `_montchat` est plus lisible et coherent avec `agence_slug`). A creer en Phase 3 :
- side-files : `data/_arbitres_montchat.json`, `data/_cles_invalides_montchat.json`, `data/_kv_assign_montchat.json`, etc. (init vides) ;
- KV : namespace `secteur_assignments:dauphine-lacassagne-montchat` (+ repartition/attribution idem) [DEDUCTION] ;
- light : `data/secteur_montchat_light.json` + full `data/secteur_montchat.json`.

---

## E5 — FRONT SECTEUR

### Chargement d'une zone

[PREUVE index.html l.2406-2417] `secteurResolve()` = table de mapping **agenceId -> [fichier light, idKV, nom header, ville]** :
```js
const M = {
  'dauphine-lacassagne': ['secteur_dauphine_lacassagne_light.json', 'dauphine-lacassagne', 'Dauphiné-Lacassagne (Lyon 3e)', 'Lyon 3'],
  'motte-picquet':       ['secteur_motte_picquet_light.json',        'motte-picquet',        'Motte-Picquet (Paris 15e - 7e)', 'Paris 15'],
};
return M[agenceId] || M['dauphine-lacassagne'];
```
[PREUVE l.2419-2457] `loadSecteurData()` : resout `[secFile, secId, secName, secVille]`, met a jour `secteurVille` (lien Maps), `#secteur-titre` (l.2423-2424 `'🗺 Secteur Prospector — ' + secName`), fetch light via `${GITHUB_RAW}/data/${secFile}` (l.2433), fetch KV via `${API_URL}/secteur-assignments/${secId}` (l.2449). Titre HTML statique : `#secteur-titre` (l.765, "...Dauphiné-Lacassagne (Lyon 3e)").

### Multi-AGENCE seulement, ou multi-ZONE ?

[PREUVE] **Multi-AGENCE strict, UNE zone par agence.** `secteurResolve` est indexe uniquement par `agenceId`. **Secteur ne lit PAS `AGENCES_CONFIG.zones`** (grep : `zones` n'apparait pas dans le code Secteur ; c'est SCI qui peuple `#sci-filter-zone` dynamiquement depuis `s.zone` des donnees, cf. `diag_sci_montchat.md` E2). **Secteur n'a AUCUN equivalent de `#sci-filter-zone`** : pas de selecteur de zone, pas de variable `secteurZone`. L'arbre groupe par `ilotEffectif(a)` (= `as.ilot` KV puis `a._ilot` light), tree **ilot top-level** depuis le refactor 2026-05-24 [PREUVE l.5037-5042], `code_iris` rétrograde a un usage de stats (sticky-IRIS l.2527+).

### Ou/comment inserer le toggle DL/Montchat (intra-agence)

[DEDUCTION, pattern reutilisable confirme par le code] Le toggle n'est PAS data-driven (contrairement a SCI) : il faut l'ajouter. Plan recommande :
- **Variable d'etat** `let secteurZone = 'dauphine-lacassagne';` (calque sur `secteurVille`, l.2255), persistee localStorage (calque sctGenLockedLoad).
- **`secteurResolve()` (l.2406)** : passer d'une table `agence -> tuple` a une table **zone-aware** quand `agenceId === 'dauphine-lacassagne'` : 2 entrees (`dauphine-lacassagne` -> light DL + KV `dauphine-lacassagne` ; `dauphine-lacassagne-montchat` -> `secteur_montchat_light.json` + KV `dauphine-lacassagne-montchat`). Retourner selon `secteurZone`.
- **UI toggle** : 2 boutons (Dauphiné-Lacassagne | Montchat) inseres pres du header `#mode-switch` (index.html l.580) ou pres de `#secteur-titre` (l.765), visibles seulement si `agenceId === 'dauphine-lacassagne'` ([DEDUCTION] gate bufferne : le plan dit "visible en session bufferne" = condition sur agenceId DL). `onclick` -> set `secteurZone` -> `loadSecteurData()` (qui relit secteurResolve, recharge light+KV, met a jour le titre).
- **Aucun changement worker** (KV regex accepte deja l'idKV suffixe).
- **test_render_secteur.js** : etendre a Montchat (le test a des plages de lignes hardcodees a resynchroniser apres edition index.html — gotcha connu MEMORY.md).

---

## E6 — ETAT MP (template complet ?)

[PREUVE] Ce qui EXISTE pour MP cote Secteur :
- `make_light_motte_picquet.py` [HORS-DEPOT, present] ;
- extracteurs sources : `rnc_extract_motte_picquet.py`, `dvf_extract_motte_picquet.py`, `bdnb_extract_motte_picquet.py`, `filosofi_extract_motte_picquet.py`, `secteur_prospector_mp.py` + sources root `secteur_motte_picquet.json` / `dvf_motte_picquet.json` / `bdnb_motte_picquet.json` / `rnc_motte_picquet.json` ;
- `data/secteur_motte_picquet.json` (full 17 Mo) + `data/secteur_motte_picquet_light.json` (light 2.2 Mo, **1277 adresses**) avec chaine de correctifs complete (~40 `.bak`, cf. `data/PIPELINE.md` §5) ;
- entree dans `secteurResolve()` (index.html l.2414) ;
- `data/_kv_assign_mp.json` + `_social_overrides_mp` (implicite via secteurs.json), `_enrich_majic_mp_full.json`.

[PREUVE] Ce qui MANQUE pour MP :
- **AUCUN `_ilot`** : `secteur_motte_picquet_light.json` a 0 adresse avec `_ilot`, 1277 avec `code_iris` (17 IRIS distincts). **MP est IRIS-only, pas de couche KML.** -> MP n'aide PAS pour l'ilotage Montchat.
- Pas de side-files `_arbitres_mp` / `_cles_invalides_mp` / `_bgid_resolus_mp` / `_nom_ambigu_resolus_mp` (seul `social_overrides` est cable cote MP, cf. `PIPELINE.md` §9).
- Needles metier MP non constituees (`secteurs.json[motte-picquet].metier._TODO` : needles parisiennes a faire ; scan social MP **bloque**, cf. `PIPELINE.md` §7 etape 6).

### CONCLUSION E6

**MP est un template COMPLET pour la chaine de fond (dedoublement make_light + sources + light + entree secteurResolve)** — il prouve que le pattern "1 fichier make_light par zone" fonctionne. **Mais MP est PARTIEL pour ce qui est specifique a Montchat** : l'ilotage KML n'existe QUE pour DL (`_apply_ilot_kml_dl.py`), et la qualification fine MP n'est pas faite. **Donc : DL = template de l'ilotage KML + qualification ; MP = template du dedoublement make_light.** Montchat hereditera des deux (chaine make_light facon MP/DL, ilotage facon DL).

---

## CONCLUSION (gate G0)

- **(a) Sources Montchat = SCRIPT RE-RUNNABLE.** Chaine `rnc_extract` / `dvf_extract_dauphine` / `bdnb_extract_dauphine` / `filosofi_extract` / `secteur_prospector_dl` -> `consolidate_secteur.py`, perimetre = polygone Shapely + INSEE en dur. Montchat = dupliquer ces scripts avec le polygone Montchat (deja dans `secteurs.json`) + verifier l'INSEE (69383, debordement 69388 a confirmer). Pas de procurement, SAUF presence des sources brutes locales [HORS-DEPOT] a confirmer cote Yann.
- **(b) make_light = HARDCODE par zone, duplique par fichier.** Patron : copier `make_light.py` (DL) -> `make_light_montchat.py`, re-pointer 4 constantes, garder WFS IRIS 69383, vider les tables ALIAS. (Modularisation `--secteur` = uniquement les outils de qualification `scripts/`, pas make_light.)
- **(c) Couche ilot KML : ancrage = nouveau `scripts/_apply_ilot_kml_montchat.py` calque sur `_apply_ilot_kml_dl.py`**, applique APRES make_light, ecrit `_ilot` par point-in-polygon (snap 25 m, fixes 118->195 / 162) ; `code_iris` (WFS) reste pose par make_light et CONSERVE pour Filosofi/INSEE. Arbre UI deja ilot-top-level (l.5037).
- **(d) Cles KV : `secteur_assignments|repartition|attribution:{agenceId}`, keyees par AGENCE.** Suffixe side-files Montchat = `_montchat`. Namespace KV separe = forger un idKV distinct `dauphine-lacassagne-montchat` (accepte par la regex worker, zero changement worker).
- **(e) Front = MULTI-AGENCE strict, mono-zone.** Pas de multi-zone (contrairement a SCI). Toggle = AJOUT : variable `secteurZone` + `secteurResolve` zone-aware (table 2D agence x zone pour DL) + boutons header (gate `agenceId==='dauphine-lacassagne'`) + re-`loadSecteurData()`. Refactor leger, localise.
- **(f) MP = template COMPLET du dedoublement make_light, PARTIEL pour ilotage/qualif.** DL reste le template de bout-en-bout (seul a avoir l'ilotage KML).

### AJUSTEMENTS proposes aux phases 1-7 de la spec

1. **Phase 1 (sources) — branche SCRIPT confirmee, PAS procurement.** Ajuster le libelle : "relancer la chaine d'extracteurs DL avec le polygone Montchat". Ajouter une **etape 0 de Phase 1** : verifier la presence des 3 sources brutes locales [HORS-DEPOT] (`majic_locaux2_2025.parquet`, `rnc_t3_2025.csv`, `dvf_2024/2025.txt.zip`) chez Yann — seul point ou une action data de Yann peut etre requise (fournir les bruts, pas un procurement filtre). **Trancher l'INSEE** : Montchat = `69383` seul, ou `69383`+`69388` ? (impacte le filtre des extracteurs, aujourd'hui mono-INSEE scalaire). Les scripts Montchat devront recopier le polygone Montchat dans `rnc_extract`, `dvf_extract`, `secteur_prospector` ET `bdnb_extract` (4 copies a creer, pas 1).
2. **Phase 2 (make_light) — pas d'ambiguite : `make_light_montchat.py` nouveau fichier [HORS-DEPOT]**, calque DL. **L'ilotage KML est une ETAPE SEPAREE post-make_light** (nouveau `scripts/_apply_ilot_kml_montchat.py`, IN-REPO, calque `_apply_ilot_kml_dl.py`), pas integre dans make_light (coherent avec DL). Bien committer `data/kml/Ilotage_Montchat.kml` ET le script d'apply. Parametre snap = 25 m (vs 5 m DL).
3. **Phase 3 (KV) — preciser l'idKV.** Le namespace separe se fait cote idKV (`dauphine-lacassagne-montchat`), pas cote nom de cle KV (worker inchange). Init side-files `_*_montchat` vides. **Aucun changement worker.js requis** (a confirmer en Phase 4).
4. **Phase 4 (front toggle) — NON simplifiable par config** (contrairement a ce que le SCI laissait esperer) : Secteur n'est PAS multi-zone aujourd'hui. C'est un **ajout de code** (variable `secteurZone` + secteurResolve 2D + UI), pas un simple flag. Reste leger et localise (l.2406 + l.580/765). Gotcha test_render : resync des plages de lignes hardcodees + etendre le test a Montchat.
5. **Phase 5 (qualification) — playbook DL applicable**, MAIS needles lyonnaises de `secteurs.json[dauphine-lacassagne].metier` directement reutilisables (Montchat = meme Lyon, memes bailleurs Grand Lyon / SACVL — contrairement a MP qui exige des needles parisiennes neuves). C'est un AVANTAGE : Montchat herite des needles DL sans le blocage MP.
6. **Phases 6-7 — inchangees** (verif test_render 2 (voire 3) zones, doc). Ajouter a la doc : la couche `_apply_ilot_kml_*` comme etape officielle du pipeline (aujourd'hui c'est un script `_`-prefixe "scratch" mais c'est en realite structurel pour DL et Montchat).

### Recapitulatif preuve / deduction / hors-depot

- **[PREUVE]** : chaine de scripts sources (lus : `rnc_extract.py`, `dvf_extract_dauphine.py`, `secteur_prospector_dl.py`, `consolidate_secteur.py`, tete `make_light.py`), absence fichiers Montchat, `_ilot` pose par `_apply_ilot_kml_dl.py` (lu integralement), `code_iris` par make_light (l.501-517), cles KV worker.js (l.609-740), `secteurResolve`/`loadSecteurData` (l.2406-2457), arbre ilot-top-level (l.5037), MP light sans `_ilot` (1277 adr, 17 IRIS), side-files DL vs MP (`ls data/`), polygone Montchat (`secteurs.json` l.41-67).
- **[DEDUCTION]** : structure make_light_motte_picquet (non lu integralement), idKV `dauphine-lacassagne-montchat`, snap 25 m, gate bufferne sur agenceId, ordre du pipeline Montchat.
- **[HORS-DEPOT]** : tous les `make_light*.py`, les extracteurs `*_extract*.py`, sources brutes (`majic_locaux2_2025.parquet`, `rnc_t3_2025.csv`, DVF zips), fichiers root `*_dauphine_lacassagne.json`/`*_motte_picquet.json`, KML DL d'origine (`C:\Users\Station 5\Downloads\Secteur DL - *.kml` — copies committees dans `data/kml/`). **Aucun `Ilotage_Montchat.kml` n'existe encore** (a fournir par Yann).
