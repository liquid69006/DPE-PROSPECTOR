# Diag INFRA MAJIC-parcelle — cartographie DL + plan de replication MONTCHAT

> **Tache READ-ONLY (cartographie + plan).** Aucune modification, aucun commit,
> aucun appel BDNB-live ni MAJIC. Seul fichier ecrit : ce rapport.
> Date : 2026-06-03. PYTHONUTF8=1, prints ASCII-safe.
>
> **Objet** : cartographier les 3 briques de la chaine MAJIC-parcelle de DL
> (1. declaration `secteurs.json` ; 2. cache `_bgid_parcelle_dl.json` via BDNB-live ;
> 3. `enrich_majic.py --secteur dl`) et **planifier** leur replication pour MONTCHAT
> (INSEE 69383 Lyon 3e + 69388 Lyon 8e), **SANS rien executer**.
>
> **Convention** : **[PREUVE]** = code/donnee lus ; **[DEDUCTION]** = inference.

---

## E1 — Brique 1 : declaration du secteur dans `data/secteurs.json`

### Structure DL lue [PREUVE]

Le bloc `"dauphine-lacassagne"` (cle = slug tiret) contient 4 sous-objets :

| Champ | Valeur DL | Lu par |
|---|---|---|
| `short` | `"dl"` | `secteur_config.SecteurConfig.short` -> nom de sortie `_enrich_majic_<short>.json` (Phase 1) |
| `agence_slug` | `"dauphine-lacassagne"` | informatif |
| `nom_affichage` | `"Century 21 Dauphine-Lacassagne"` | informatif |
| `geo.dep` | `"69"` (scalaire) | filtre MAJIC `("departement","=",cfg.dep)` |
| `geo.code_commune` | `["383"]` (LISTE) | filtre MAJIC `("code_commune","in",cfg.code_commune)` + groupby + `pref_by_commune()` |
| `geo.rnc_dep_prefix` | `["69123383"]` (LISTE) | scripts RNC-live (hors chaine MAJIC) |
| `geo.bdnb_dep_prefix` | `["69383000"]` (LISTE) | `pref_by_commune()` -> reconstruit la cle parcelle BDNB (`{ '383':'69383000' }`) |
| `geo.codes_postaux` | `["69003"]` (LISTE) | informatif / scripts amont |
| `geo.zones[]` | 2 polygones : `"Dauphine-Lacassagne"` + **`"Montchat"`** | frontend Leaflet + scripts geo (PAS lu par enrich_majic) |
| `paths.*` | 11 chemins (voir ci-dessous) | `SecteurConfig` resout en absolu (ROOT-relatif) |
| `metier.hlm_needles` | 26 needles bailleurs Lyon | `_diag_social_combined_dvf_majic_dl.py` (social_pct) |
| `metier.public_non_hlm` | 18 needles public non-HLM | idem |
| `metier.seuils.social_pct_min` | `60` | seuil social |
| `metier.seuils.mut_apt_per_year_min` | `2` | faux-positif social via rotation DVF |

### Ce que LIT exactement `enrich_majic.py` / `enrich_majic_full.py` [PREUVE]

Les deux scripts passent **uniquement** par `secteur_config.load_secteur(slug)` (`from secteur_config import load_secteur, slugs` — l.22 full / l.27 phase1). Champs effectivement consommes par la chaine MAJIC :

- **`geo.dep`** (`cfg.dep`) -> filtre parquet `departement` [PREUVE full l.140, phase1 l.228/232].
- **`geo.code_commune`** (`cfg.code_commune`, liste) -> filtre parquet `code_commune in [...]` [PREUVE full l.141].
- **`geo.bdnb_dep_prefix`** + `code_commune` -> `cfg.pref_by_commune()` = `dict(zip(code_commune, bdnb_dep_prefix))` -> reconstruit la cle parcelle `f"{pref}{sec}{plan.zfill(4)}"` [PREUVE full l.151-154 ; secteur_config l.92-95].
- **`paths.light`** (`cfg.light`) -> JSON du secteur [PREUVE full l.87/99].
- **`paths.cache_bg`** (`cfg.cache_bg`) -> cache `_bgid_parcelle_<sct>.json` (lu + reecrit) [PREUVE full l.88/102/123].
- **`paths.enrich_majic`** (`cfg.enrich_majic`) -> fichier de sortie Phase 2 [PREUVE full l.89/309]. Phase 1 ecrit `data/_enrich_majic_<short>.json` (construit a partir de `cfg.short`, PAS de `paths.enrich_majic`) [PREUVE phase1 l.158].
- **`short`** (`cfg.short`) -> nom sortie Phase 1 [PREUVE phase1 l.155/158].

**`MAJIC` est HARDCODE** dans les 2 scripts : `r"C:\Users\Station 5\majic_locaux2_2025.parquet"` (PAS dans secteurs.json) [PREUVE full l.27, phase1 l.32].

**Validation stricte de `SecteurConfig.__init__`** [PREUVE secteur_config l.47-85] : le constructeur indexe en dur `raw["short"]`, `raw["geo"][{dep,code_commune,rnc_dep_prefix,bdnb_dep_prefix,codes_postaux}]`, `raw["metier"][{hlm_needles,public_non_hlm,seuils.social_pct_min,seuils.mut_apt_per_year_min}]`, et `raw["paths"][{light,kv_local,social_overrides,enrich_majic,cache_bg,dvf_path}]`. **Tout champ manquant -> KeyError au chargement.** Les paths optionnels (graceful `None` si absent) : `nom_ambigu_resolus`, `bgid_resolus`, `arbitres`, `cles_invalides` [PREUVE l.69-82]. Le slug doit aussi exister dans le dict (`load_secteur` leve `SystemExit "slug inconnu"` sinon) [PREUVE l.103-105].

### Le slug `montchat` n'existe PAS [PREUVE]

`secteurs.json` ne contient que `dauphine-lacassagne` et `motte-picquet`. La zone Montchat existe **uniquement comme 2e polygone DANS `dauphine-lacassagne.geo.zones`** (l.40-67), **PAS comme secteur autonome**. Donc `enrich_majic_full.py --secteur montchat` echoue aujourd'hui sur `SystemExit "slug inconnu: 'montchat'"` (et `montchat` n'est pas dans `choices=slugs()+[...]` non plus). **Brique 1 = bloquante.**

### Quirk coordonnees [PREUVE]

- `secteurs.json._meta.format_note` : **polygones en `[lat, lng]`** (Leaflet) [PREUVE l.5].
- `C:\Users\Station 5\perimetre_montchat.json` : `{"poly": [[lon,lat],...]}` -> **`[lon, lat]`** (1er nombre ~4.86, 2e ~45.75) [PREUVE]. **Ordre INVERSE de secteurs.json.**
- **La zone "Montchat" deja presente dans `dauphine-lacassagne.geo.zones` est en `[lat,lng]` correct** (45.75…, 4.86…) [PREUVE l.43-66] -> reutilisable telle quelle pour le slug montchat, **sans reconversion**. Si on prefere repartir de `perimetre_montchat.json`, **swapper chaque paire** `[lon,lat]->[lat,lng]`.

### Quirk 69385 (Lyon 5e declare RNC, geo dans Montchat) [DEDUCTION]

- Le quirk concerne **11 copros declarees arrondissement RNC 69385** mais geographiquement dans Montchat (gardees Manche A) [contexte tache].
- **Impact sur la jointure MAJIC = nul SI leurs parcelles sont en commune 383/388.** La chaine MAJIC ne joint **jamais par arrondissement RNC** : elle joint **par parcelle BDNB** (`code_commune` de la PARCELLE, pas l'arrondissement de declaration RNC). Le filtre parquet est `code_commune in cfg.code_commune` ; le groupby + `pref_by_commune()` n'exploite que `code_commune` MAJIC reel.
- **Donc : NE PAS ajouter 385 aux `code_commune`** sauf si l'on constate (a l'execution) que des parcelles de ces 11 copros portent `code_commune=385` dans MAJIC. **A verifier a l'execution de la brique 3** (point de vigilance, non-bloquant) : si une des 11 copros 69385 a une parcelle resolue en `69385000…`, alors (a) `pref_by_commune` n'aurait pas la cle `385` (KeyError au groupby cote full) ET (b) ses lots seraient filtres hors du read parquet -> MAJIC rate. Dans ce cas : ajouter `"385"` a `code_commune` et `"69385000"` a `bdnb_dep_prefix` (alignes par index). **[DEDUCTION] le plus probable est que ces parcelles sont en 383/388 (geo Montchat), le 385 n'etant qu'un artefact de declaration RNC** -> tolerer, ne rien ajouter, verifier a posteriori.

### BLOC `montchat` PROPOSE pour `secteurs.json` (NON ecrit)

```json
"montchat": {
  "short": "montchat",
  "agence_slug": "dauphine-lacassagne",
  "nom_affichage": "Century 21 Dauphine-Lacassagne (secteur Montchat)",

  "geo": {
    "dep": "69",
    "code_commune":    ["383", "388"],
    "rnc_dep_prefix":  ["69123383", "69123388"],
    "bdnb_dep_prefix": ["69383000", "69388000"],
    "codes_postaux":   ["69003", "69008"],
    "zones": [
      {
        "nom": "Montchat",
        "codes_postaux": ["69003", "69008"],
        "polygone": [
          [45.752807471686765, 4.8696556919393],
          [45.750648569367286, 4.873968991938966],
          [45.74554776311837,  4.8712261737505],
          [45.74309361037359,  4.878425233301357],
          [45.74276386559836,  4.878697742930143],
          [45.74164596308222,  4.884055610780678],
          [45.739037436828085, 4.892083206597164],
          [45.74349477437073,  4.89467820901416],
          [45.746809758539996, 4.89646416496484],
          [45.74891686986501,  4.896869278651252],
          [45.751589171037665, 4.8975505195815],
          [45.752963814591624, 4.8984527035141525],
          [45.75343915074612,  4.896685159480938],
          [45.75400441009205,  4.893941783846714],
          [45.75409433718764,  4.892339947067768],
          [45.75431055205931,  4.887625722940868],
          [45.75424631868333,  4.8851585260613035],
          [45.75438763201271,  4.883096391355906],
          [45.75499142129863,  4.878401352518125],
          [45.75499142129863,  4.877296637497693],
          [45.754901495648596, 4.875437033880047],
          [45.75461887123453,  4.874092963938381]
        ]
      }
    ]
  },

  "paths": {
    "light":            "data/secteur_montchat_light.json",
    "kv_local":         "data/_kv_assign_montchat.json",
    "social_overrides": "data/_social_overrides_montchat.json",
    "enrich_majic":     "data/_enrich_majic_montchat_full.json",
    "cache_bg":         "data/_bgid_parcelle_montchat.json",
    "dvf_path":         "C:\\Users\\Station 5\\dvf_montchat.json"
  },

  "metier": {
    "hlm_needles": [ "...REUTILISER LES 26 NEEDLES DL (memes bailleurs Grand Lyon / SACVL / Alliade)..." ],
    "public_non_hlm": [ "...REUTILISER LES 18 NEEDLES DL..." ],
    "seuils": {
      "social_pct_min": 60,
      "mut_apt_per_year_min": 2
    }
  }
}
```

**Notes sur le bloc** :
- Le **polygone `zones`** ci-dessus est **copie verbatim** de la zone "Montchat" deja presente dans `dauphine-lacassagne.geo.zones` (deja en `[lat,lng]` correct). [PREUVE]
- **`code_commune` = `["383","388"]`** : la pile orange B2 a deja confirme parquet 383 (61243 lignes) + 388 (55628 lignes) [PREUVE diag B2 l.125].
- **needles HLM/public** : **reutiliser telles quelles les 26+18 needles DL** (memes bailleurs Lyon) [DEDUCTION conforme B2 l.126-127]. NE PAS laisser vides (KeyError non, mais social_pct=0 -> faux negatifs sociaux systematiques).
- **paths optionnels** (`nom_ambigu_resolus`, `bgid_resolus`, `arbitres`, `cles_invalides`) : volontairement OMIS -> graceful `None`, pas de crash [PREUVE secteur_config]. A ajouter si une manche ulterieure les utilise.
- **`dvf_path`** : le fichier `dvf_montchat.json` doit exister AVANT tout script lisant DVF (ex. `_diag_social_combined_dvf_majic`). **Pour enrich_majic seul, `dvf_path` n'est PAS lu** -> peut pointer un fichier inexistant tant qu'on ne lance que la brique 3 (Path() lazy, jamais ouvert par enrich). **[DEDUCTION]** statut DVF Montchat a confirmer hors-scope.
- **Alternative non-intrusive** : ajouter aussi `"montchat"` et l'alias eventuel dans `choices=slugs()+[...]` des 2 scripts — **inutile** car `slugs()` lit dynamiquement les cles de secteurs.json (donc `montchat` apparaitra automatiquement dans `choices` une fois le bloc ajoute) [PREUVE secteur_config l.39-41].

---

## E2 — Brique 2 : construction du cache `_bgid_parcelle_<sct>.json` (BDNB-live)

### Script constructeur = `enrich_majic_full.py` lui-meme [PREUVE]

Il n'existe **pas** de script standalone dedie : le cache parcelle est construit **a la volee par `enrich_majic_full.py`**, fonction `fetch_bdnb_parcelles_batch()` [PREUVE l.54-74]. `enrich_majic.py` (Phase 1) **consomme** le cache mais ne le construit pas (`cache_bg = json.loads(cache_bg_path.read_text())` sans fallback -> **crash si absent**) [PREUVE phase1 l.171]. D'autres scripts (`scan_horsrnc_parcelle.py`, `_resolve_bgid_live_dl.py`, etc.) interrogent BDNB rel_parcelle pour d'autres usages mais ne maintiennent pas ce cache canonique.

### Mecanique exacte [PREUVE]

- **Endpoint BDNB** : `https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.<bgid>` [PREUVE l.61-62].
- **Entree** = l'ensemble des `batiment_groupe_id` distincts du light (`bgids = {a["batiment_groupe_id"] for a in ad}`) [PREUVE l.114-118].
- **Filtrage** : seuls les bgids **absents du cache** sont requetes (`missing = [b for b in bgids if b and b not in cache_bg]`) [PREUVE l.57] -> **idempotent / incremental** : un 2e run ne requete que les nouveaux.
- **1 appel HTTP PAR bgid manquant** (pas de batch), `time.sleep(0.05)` entre chaque [PREUVE l.60-73].
- **Sortie** : `cache_bg[bg] = [parcelle_id, ...]` (liste des `parcelle_id` non-null retournes) ; ecrit dans `cfg.cache_bg` (indent=2, utf-8) **uniquement si** au moins 1 ajout [PREUVE l.70, l.122-125].
- **Format parcelle_id** = BDNB brut, ex `69383000DO0024` (= dep2+commune3+`000`+section2+plan4) [PREUVE cache DL lu]. Decoupe par `parc_to_majic()` : `sec=p[8:10]`, `plan=int(p[10:].lstrip('0'))` [PREUVE full l.46-51].
- **`--skip-bdnb-completion`** : flag pour sauter la completion live (utilise le cache tel quel) [PREUVE l.82-83, l.120].

### Cache DL existant [PREUVE]

- `data/_bgid_parcelle_dl.json` : **901 entrees**, couvre **883/884** bgids du light DL (1 manquant). Format `{"bdnb-bg-XXXX-YYYY-ZZZZ": ["69383000DO0024"]}`. Toutes parcelles DL en prefixe `69383000`.
- `data/_bgid_parcelle_mp.json` : 1000 entrees (MP, 2 communes 115+107).

### Volume MONTCHAT a resoudre [PREUVE]

- `secteur_montchat_light.json` : **1430 adresses**, **633 coproprietes**, **1143 `batiment_groupe_id` distincts**.
- Les adresses light **ne portent AUCUN champ parcelle** (`parcelle keys in addr = []`) [PREUVE] -> tout passe par le cache bgid->parcelle.
- **Sidecar `_horsrnc_bdnb_live_montchat.json`** : dict de **672 bgids**, valeur = `{"immats":[...], "meta":{}}`. **`meta` est VIDE, AUCUNE donnee parcelle** [PREUVE]. Ce sidecar ne contient QUE des lookups RNC-immat (manche B1), **pas exploitable comme cache parcelle**. Les 672 bgids du sidecar sont **tous inclus** dans les 1143 du light (`sidecar - light = 0`).
- **`_bgid_parcelle_montchat.json` N'EXISTE PAS** [PREUVE] -> cache vide au depart.

> **Estimation appels BDNB** : `enrich_majic_full --secteur montchat` (sans `--skip-bdnb-completion`) requetera **~1143 bgids** (cache vide -> tous "missing"). A `sleep(0.05)` + ~latence reseau ~0.2-0.4s/appel -> **~1143 appels HTTP serial**, **duree estimee ~5 a 10 min** (DL = 901 appels d'historique ~analogues). Idempotent : si interrompu, relancer ne requete que le reste (mais le cache n'est ecrit qu'en fin de fonction `fetch_bdnb_parcelles_batch` apres la boucle complete -> **un crash en cours de boucle perd les bgids deja requetes**. **[DEDUCTION] point de fragilite** : pas de checkpoint intermediaire ; cf. vigilance plan).

### Gotcha format parcelle DVF vs RNC-live [PREUVE/DEDUCTION]

- Cote **Paris** (memo MP) : DVF `75115000DI0003` != RNC-live `75056115DI0003` (INSEE 75056 + arr). **Cette divergence concerne RNC-live, PAS la chaine MAJIC** : la chaine MAJIC utilise la parcelle **BDNB** (`rel_batiment_groupe_parcelle`, format `<dep><commune>000<sec><plan>`), pas la cle RNC.
- Cote **Lyon** : commune INSEE = 69383 / 69388 ; le **prefixe BDNB parcelle est `69383000` / `69388000`** (= dep69 + commune383/388 + `000`), aligne sur `geo.bdnb_dep_prefix` [PREUVE cache DL]. Le decoupage `parc_to_majic` (`sec=p[8:10]`, `plan=p[10:]`) puis la reconstruction `pref_by_commune[cc]+sec+plan.zfill(4)` referme la boucle MAJIC<->BDNB de facon coherente [PREUVE full l.46-51, l.151-154]. **Aucune divergence DVF/RNC ne traverse la brique MAJIC.**

---

## E3 — Brique 3 : `enrich_majic.py` / `enrich_majic_full.py --secteur <sct>`

### Inputs [PREUVE]

1. **`cfg.light`** (le JSON secteur) : itere `doc["adresses"]` (cle, `batiment_groupe_id`, `nb_log_bdnb`, `nb_ventes_logement`, `numero_immatriculation`, `_fusion_auto`, `sci_nom`) + `doc["coproprietes"]` indexe par `cle_adresse` [PREUVE full l.99-103].
2. **`cfg.cache_bg`** (cache bgid->parcelle de la brique 2).
3. **`majic_locaux2_2025.parquet`** (hardcode) : lu en BULK (full) filtre `departement` + `code_commune in [...]` [PREUVE full l.139-142].

### Jointure parcelle -> proprietaires [PREUVE]

- Chaque adresse light -> bgid -> `cache_bg[bgid]` -> liste parcelles -> **1ere parcelle `parcs[0]`** (full l.193 ; phase1 l.222) -> sous-DataFrame MAJIC `by_parc[p0]`.
- MAJIC bulk indexe par `groupby(["code_commune","section","numero_parcelle"])`, cle reconstruite via `pref_by_commune()` [PREUVE full l.151-156].
- **Proprietaire = `numero_siren`** : `df[df.numero_siren.notna()].groupby("numero_siren")` -> par SIREN `{siren, denomination, lots, pct_lots}` (full) ; Phase 1 ajoute `forme_juridique_libelle` + `code_droit_libelle` (droits) [PREUVE phase1 l.90-106].
- **Filtrage syndics/gerants** : la colonne `code_droit_libelle` est **disponible** (`Syndic de copropriete`, `Gerant/mandataire/gestionnaire`, `Usufruitier`, `Nu-proprietaire`, `Proprietaire`) [PREUVE diag B2 l.98-101]. **MAIS `enrich_majic_full.py` NE FILTRE PAS** par `code_droit_libelle` (il groupe TOUS les SIREN, syndics inclus) [PREUVE full l.204-213] ; `enrich_majic.py` Phase 1 **expose** les `droits` par SIREN mais ne filtre pas non plus [PREUVE phase1 l.97]. **Le filtrage syndic/gerant/usufruit est fait EN AVAL** par le classifieur `_scan_sansventes_majic_dl.py` et le dry-run B2, **pas dans enrich** [PREUVE diag B2 l.96-108]. -> **enrich = collecte brute ; la regle de propriete s'applique apres.**

### Sorties [PREUVE]

- **Fichier** : `enrich_majic_full` ecrit `cfg.enrich_majic` (DL = `data/_enrich_majic_dl_full.json`) ; `enrich_majic` Phase 1 ecrit `data/_enrich_majic_<short>.json` [PREUVE]. **PAS d'ecriture du light** -> brique non-destructive (parc inchange).
- **Par adresse** (`results[]`) : `cle, bgid, bdnb (=nb_log_bdnb), vlog, in_copro, has_immat, is_fa, parcelles_bdnb, status, majic_lots, majic_adresses[], sirens[] ({siren,denomination,lots,pct_lots}), ratio_pm_bdnb (=lots_total/bdnb), is_mono, multi_facades_brut, voisins_majic[]` [PREUVE full l.179-262].
- **`social_pct` n'est PAS produit par enrich** : il est calcule en aval par `_diag_social_combined_dvf_majic_dl.py` (HLM_lots*100/RNC_habit, needles + `groupe_personne_libelle`='office HLM') [PREUVE diag B2 l.80-94]. enrich ne fait que fournir les SIREN+denominations bruts.
- **`status`** : `ok` / `no_majic` (parcelle sans lot PM) / `no_parcelle` (bgid hors cache) [PREUVE full l.188-199].

### Regle DL confirmee [PREUVE]

- **MONO (Phase 2)** = `n_sirens == 1 ET pct_top >= 100 ET ratio_pm_bdnb >= 0.9` [PREUVE full l.218-221]. (Phase 1 : `1 SIREN >= 95% ET lots==total` [PREUVE phase1 l.110-111].)
- **COPRO** = `>= 2 SIREN proprietaires distincts` [PREUVE diag B2 l.119, classifieur aval].
- **0 PM = angle-mort PP** (RGPD : parquet PM-only, 116869/116871 lignes Lyon avec SIREN) -> `ratio_pm_bdnb < 0.15` => DL=`PP_PURE`(cible), B2=`AMBIGU` [PREUVE diag B2 l.67-78, l.120]. **0 PM ne bascule JAMAIS en MONO automatiquement.**
- Nuances aval (`_scan_sansventes_majic_dl`) : `top_pct>=80 -> MONO_*` ; `>=5 SIREN & top<50% -> FRAGMENTEE` ; `ratio<0.15 -> PP_PURE` [PREUVE diag B2 l.63-65].

### Parametrable `--secteur` vs DL-hardcode [PREUVE]

| Element | Parametrable (`cfg.*`) | Hardcode |
|---|---|---|
| dep / code_commune / bdnb_prefix | OUI (`cfg.dep`, `cfg.code_commune`, `pref_by_commune`) | — |
| chemins light / cache / sortie | OUI (`cfg.light`, `cfg.cache_bg`, `cfg.enrich_majic`) | — |
| needles HLM / seuils social | OUI (`cfg.hlm_needles`, `cfg.social_pct_min`) — **mais consommes en AVAL** | — |
| chemin parquet MAJIC | — | `r"C:\Users\Station 5\majic_locaux2_2025.parquet"` (full l.27 / phase1 l.32) |
| endpoint BDNB rel_parcelle | — | URL en dur (full l.61) |
| seuils mono (0.9 / 100% / 95%) | — | en dur dans le code |
| filtre code_droit (syndic) | — | **absent d'enrich** (fait en aval, hardcode DL dans `_scan_sansventes`) |

> **Conclusion E3** : enrich_majic est **deja `--secteur`-parametrable** (geo + paths). Le slug `montchat` sera accepte **automatiquement** des que le bloc secteurs.json est ajoute (`choices=slugs()+[...]`). **Aucune modif de code enrich requise** pour Montchat — uniquement secteurs.json (brique 1) + cache (brique 2). Les regles metier (social needles, filtre syndic) vivent en AVAL et devront, elles, etre passees `--secteur montchat` (a verifier que `_scan_sansventes_majic_dl.py` et `_diag_social_combined_*` acceptent le slug — ils lisent aussi `load_secteur`, donc OK des que le bloc existe).

---

## PLAN ordonne — replication des 3 briques pour MONTCHAT (NON execute)

### Brique 1 — declarer `montchat` dans `data/secteurs.json`  [BLOQUANT]

- **Fichier MAJ** : `data/secteurs.json` (ajouter le bloc propose en E1).
- **Commande** : edition manuelle (pas de script). Verifier ensuite `python -c "from secteur_config import load_secteur; load_secteur('montchat')"` (charge sans KeyError).
- **Volume BDNB** : 0. **Duree** : minutes.
- **Vigilances vs DL** :
  - (a) **2 communes `["383","388"]`** (DL=1 seule). `code_commune` / `rnc_dep_prefix` / `bdnb_dep_prefix` / `codes_postaux` doivent etre **alignes par index** (383<->69383000<->69003 ; 388<->69388000<->69008). Un desalignement casse `pref_by_commune()` -> mauvaise cle parcelle. **[BLOQUANT]**
  - (b) **Zone KML** : **copier verbatim** la zone "Montchat" deja dans `dauphine-lacassagne.geo.zones` (deja en `[lat,lng]`). Ne PAS recopier `perimetre_montchat.json` brut (`[lon,lat]`, ordre inverse). **[COSMETIQUE pour enrich** (qui ne lit pas zones)**, BLOQUANT pour le rendu front/geo].**
  - (c) **needles HLM/public** : reutiliser les 26+18 DL. Vides -> social_pct=0 systematique (faux negatifs). **[BLOQUANT pour la manche social, cosmetique pour enrich brut].**
  - (d) **`dvf_path`** : pointer `dvf_montchat.json` ; non-lu par enrich, lu par le diag social. **Verifier l'existence du DVF Montchat hors-scope** avant la manche social. **[non-bloquant pour briques 2-3].**

### Brique 2 — construire `data/_bgid_parcelle_montchat.json` (BDNB-live)  [BLOQUANT]

- **Fichier CREE** : `data/_bgid_parcelle_montchat.json`.
- **Commande** : `python scripts/enrich_majic_full.py --secteur montchat` (la completion BDNB est integree ; **PAS** `--skip-bdnb-completion` au 1er run). Le meme run enchaine sur la brique 3 (le cache et l'enrich sont produits par le meme script).
- **Volume BDNB** : **~1143 appels** (1 par bgid distinct du light ; cache vide au depart). **Duree estimee ~5-10 min** (sleep 0.05 + latence). [PREUVE comptage 1143 bgids ; DEDUCTION duree par analogie DL 901].
- **Vigilances vs DL** :
  - (a) **2 communes** : les parcelles reviendront en `69383000…` ET `69388000…`. Tant que `bdnb_dep_prefix` contient les 2 (brique 1), `pref_by_commune` les mappe. **[depend de brique 1].**
  - (c) **quirk 69385** : si une parcelle revient en `69385000…` (peu probable), le groupby MAJIC plantera (`pref_by_commune` sans cle `385`) OU ratera (filtre parquet `in [383,388]`). **Surveiller a l'execution** : si des bgids des 11 copros 69385 reviennent `no_majic` avec parcelle `69385…`, ajouter `385`/`69385000`/`69005` aux listes. **[non-bloquant a priori, a verifier].**
  - **Fragilite** : le cache n'est ecrit qu'en fin de boucle `fetch_bdnb_parcelles_batch` -> **un crash reseau en cours perd la progression**. Si l'API est instable, **[DEDUCTION]** envisager de lancer par tranches (mais le code ne le supporte pas nativement -> relancer simplement, idempotent une fois le 1er run complet). **[cosmetique/operationnel].**
  - **Sidecar inutilisable** : `_horsrnc_bdnb_live_montchat.json` (672 bgids) **ne fournit AUCUNE parcelle** (meta vide) -> ne reduit PAS les appels. Les 1143 sont a requeter from scratch. **[PREUVE].**

### Brique 3 — `enrich_majic_full.py --secteur montchat` (jointure parcelle->proprietaires)  [decoule de 2]

- **Fichier CREE** : `data/_enrich_majic_montchat_full.json` (path `enrich_majic` du bloc).
- **Commande** : meme run que brique 2 (le 1er `enrich_majic_full --secteur montchat` fait completion cache PUIS sweep). **Re-runs** : `--skip-bdnb-completion` pour ne pas re-requeter BDNB.
- **Volume BDNB** : 0 (apres brique 2). **Duree** : read parquet 383+388 (~117k lignes) ~15-30s + sweep 1430 adresses ~qq s. **[DEDUCTION analogie DL].**
- **Vigilances vs DL** :
  - (a) **2 communes** : `cfg.code_commune=["383","388"]` -> read parquet sur les 2 (deja gere, cf. MP=115+107). `pref_by_commune()` mappe les 2. **[depend de brique 1].**
  - (d) **slug deja supporte** : OUI une fois brique 1 faite (`slugs()` dynamique). Aucune modif d'enrich. **[non-bloquant].**
  - **Aval** : appliquer ensuite l'arbre B2 / `_scan_sansventes_majic_dl` / `_diag_social_combined` en mode `--secteur montchat` (verifier que ces scripts acceptent le slug — ils passent par `load_secteur`, donc OK). C'est la **manche D/E/F** proprement dite, **hors de cette tache**.

### Synthese bloquant vs cosmetique

| Item | Statut |
|---|---|
| Bloc `montchat` dans secteurs.json (paths complets, communes/prefixes alignes) | **BLOQUANT** |
| needles HLM/public DL reportees | **BLOQUANT (manche social)** |
| zone KML en `[lat,lng]` (verbatim depuis DL.zones) | BLOQUANT (front) / cosmetique (enrich) |
| cache `_bgid_parcelle_montchat.json` (~1143 appels BDNB) | **BLOQUANT** |
| quirk 69385 dans code_commune | **a verifier a l'execution** (probable non-besoin) |
| dvf_montchat.json existant | non-bloquant pour briques 2-3 |
| checkpoint cache BDNB | cosmetique/operationnel |

---

## CONCLUSION

**(a) secteurs.json** — DL = bloc `dauphine-lacassagne` lu via `secteur_config.load_secteur` (source unique). enrich lit `geo.{dep,code_commune,bdnb_dep_prefix}` + `paths.{light,cache_bg,enrich_majic}` + `short` ; `metier.*` est consomme en AVAL (social). Slug `montchat` **absent** (existe seulement comme polygone dans DL.zones). Bloc `montchat` propose ci-dessus (INSEE 383+388, prefixes BDNB 69383000+69388000 alignes, zone verbatim, needles DL, seuils 60/2). **MAJIC parquet est hardcode, pas dans secteurs.json.**

**(b) cache `_bgid_parcelle`** — construit par `enrich_majic_full.py` lui-meme (`fetch_bdnb_parcelles_batch`, endpoint `https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq.<bgid>`, **1 appel/bgid**, idempotent). Format `bgid -> ["69383000DO0024"]`. **Montchat : 1143 bgids distincts a resoudre**, cache absent, sidecar `_horsrnc_bdnb_live_montchat.json` SANS parcelle (meta vide) -> **~1143 appels BDNB, ~5-10 min**.

**(c) enrich_majic** — inputs : cache parcelle + parquet MAJIC (bulk filtre dep+commune) + light. Jointure **par parcelle BDNB** (1ere parcelle du bgid). Proprietaire = `numero_siren` ; sortie `_enrich_majic_<sct>_full.json` (sirens/lots/pct/ratio/is_mono), light NON touche. Regle DL confirmee : **1 SIREN >=100% + ratio>=0.9 -> MONO ; >=2 SIREN -> COPRO ; 0 PM -> angle-mort PP (jamais mono auto)**. **enrich ne filtre PAS les syndics ni ne calcule social_pct** (fait en aval). Deja `--secteur`-parametrable ; **aucune modif code** pour montchat.

**(d) PLAN** — 1) editer secteurs.json (bloc montchat) [bloquant, 0 appel] -> 2) `enrich_majic_full.py --secteur montchat` 1er run = build cache **~1143 appels BDNB (~5-10 min)** + sweep -> 3) re-runs avec `--skip-bdnb-completion`. **Vigilances** : (a) 2 communes 383+388 = listes alignees par index [bloquant], (b) zone KML `[lat,lng]` verbatim depuis DL.zones [front], (c) quirk 69385 a surveiller a l'execution (probable non-besoin), (d) slug supporte automatiquement des que le bloc existe. Manches D/E/F (classif) = aval, hors de cette tache.

**Total appels BDNB estimes : ~1143** (1/bgid, cache vide). **Tout hors-depot signale** : `majic_locaux2_2025.parquet`, `perimetre_montchat.json`, `dvf_*.json`, `make_light*.py` sont sur le poste hors repo.

---

*Aucune modification effectuee hors ce rapport. Aucun commit, aucun git add, aucun appel BDNB/MAJIC. Aucun fichier temporaire cree.*
