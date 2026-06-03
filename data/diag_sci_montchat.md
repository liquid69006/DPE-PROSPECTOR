# Diag SCI Prospector — préparation switch Dauphiné/Montchat

> READ-ONLY. Aucune modification de code/données. Rapport seul.
> Date : 2026-06-01. Périmètre : agence `dauphine-lacassagne` (session bufferné), mode SCI Prospector.

## TL;DR

**SCI Prospector est déjà multi-zone, et Montchat existe DÉJÀ partout dans la chaîne.**
- Le générateur `scripts/majic_sci_2025.py` définit DEUX polygones (`Dauphiné-Lacassagne` + `Montchat`) et tague chaque SCI avec son champ `zone`.
- Le fichier produit `data/dauphine-lacassagne-sci.json` contient **1917 SCI** : **1158 zone "Dauphiné-Lacassagne" + 759 zone "Montchat"** (preuve directe, comptage ci-dessous).
- L'UI a déjà un `<select id="sci-filter-zone">` peuplé dynamiquement depuis `s.zone` (index.html 5623-5630).
- `AGENCES_CONFIG["dauphine-lacassagne"].zones = ["Dauphiné-Lacassagne", "Montchat"]` (worker.js l.49).
- `data/secteurs.json` contient les DEUX polygones sous `dauphine-lacassagne.geo.zones[]`.

Conséquence : un « switch Dauphiné/Montchat » dans le header SCI **n'exige aucun nouveau pipeline ni refactor de fond** — les données et le tag zone sont là. C'est essentiellement un **ajout d'UI** (un sélecteur de zone dans le header / ou réutilisation du `sci-filter-zone` existant). La seule chose à « refaire pour Montchat » serait éventuellement de redéfinir/étendre le polygone Montchat depuis un nouveau KML, mais le mécanisme (polygone Shapely) est déjà en place.

---

## E1 — STRUCTURE de SCI Prospector

**SCI Prospector n'est PAS une page dédiée : c'est un MODE dans `index.html`** partagé avec DPE et Secteur, basculé par un routeur JS d'onglets.

### Switch des 3 modes (DPE / SCI / Secteur)
- État global : `index.html:2197` `let currentMode = 'dpe';`
- Liste des agences autorisées SCI côté front : `index.html:2198`
  `const AGENCES_SCI = ['dauphine-lacassagne', 'lopez', 'bagot', 'motte-picquet'];`
- Fonction de bascule : `index.html:2200` `function switchMode(mode)` — montre/masque les `<div>` sections et recolore le header.
  - `index.html:2204-2207` : affiche/masque `#section-dpe`, `#section-sci`, `#section-secteur`.
  - `index.html:2202` : `const isDpe = mode === 'dpe', isSci = mode === 'sci', isSect = mode === 'secteur';`
- Boutons d'onglets dans le header : `index.html:581-583`
  ```html
  <button class="mode-btn active-dpe" id="btn-mode-dpe" onclick="switchMode('dpe')">📊 DPE</button>
  <button class="mode-btn" id="btn-mode-sci" onclick="switchMode('sci')">🏢 SCI</button>
  <button class="mode-btn" id="btn-mode-secteur" onclick="switchMode('secteur')" style="display:none;">🗺 Secteur</button>
  ```
  Le bloc `#mode-switch` (index.html:580) est `display:none` par défaut et activé seulement pour les agences SCI/Secteur.

### Bloc SCI (rendu + état + fonctions)
- **Rendu HTML** : `<div id="section-sci">` de **index.html:706 à 761** (toolbar de filtres lignes 707-737, table `#table-sci` lignes 739-760).
- **CSS** : index.html:272-275 (`#section-sci`, thead orange).
- **État JS** : `allSci`, `sciAssignments`, `derniersCourriers`, `sciSaveTimer` (dispersés ; SCI utilise la couleur orange `--orange` / doré `#BEAF87` Century 21).
- **Fonctions `sci*`** :
  - `loadSciData()` index.html:5563 — charge la base (cf. E3)
  - `loadSciAssignments()` index.html:5649 / `saveSciAssignments()` 5668 / `scheduleAutoSaveSci()` 5663
  - `renderTableSci()` (appelée 5643), `renderDirigeant()` 5687, `sortTableSci(...)`, `resetFiltresSci()`, `toggleFiltreEtranger()`, `ouvrirModalCourrier()` (toolbar 732-734).
- Chargement initial : `index.html:1442` `loadSciAssignments().then(() => loadSciData())`.

**Conclusion E1 (preuve directe)** : mode partagé dans la SPA monolithique, pas de page dédiée. Bloc SCI = `#section-sci` (706-761) + bloc fonctions `loadSciData`/`renderTableSci` (~5563+).

---

## E2 — MODÈLE DE ZONE (Dauphiné codé en dur ? multi-zone prévu ?)

**Multi-zone DÉJÀ prévu et data-driven. "Dauphiné" n'est PAS la base unique : Montchat coexiste.**

### Preuve config (worker.js)
`worker.js:42-52`, agence `dauphine-lacassagne` :
```js
"dauphine-lacassagne": {
  nom: "Century 21 Dauphiné-Lacassagne",
  ville: "Lyon 3e",
  ...
  zones: ["Dauphiné-Lacassagne", "Montchat"],   // l.49 — DEUX zones
  sci_enabled: true,                              // l.50
  secteur_enabled: true,                          // l.51
},
```
Le champ `zones` est un **tableau** (déjà multi-valeur). Il est renvoyé au front via `/login` payload : `worker.js:424` `zones: cfg.zones`. Note : `AGENCES_CONFIG` ne porte PAS de champ « zone SCI » dédié distinct — `zones` est partagé/informationnel ; le vrai tag de zone par SCI vit dans la donnée (champ `zone`, cf. E3/E5).

### Preuve UI (index.html) — sélecteur de zone déjà présent et dynamique
- `<select id="sci-filter-zone">` : index.html:710-712 (option par défaut "Toutes les zones").
- Peuplement dynamique depuis les données réelles : `index.html:5623-5630` (dans `loadSciData`) :
  ```js
  const selZoneSci = document.getElementById('sci-filter-zone');
  const zonesDisponibles = [...new Set(allSci.map(s => s.zone).filter(Boolean))].sort();
  selZoneSci.innerHTML = '<option value="">Toutes les zones</option>';
  zonesDisponibles.forEach(z => { const o = document.createElement('option');
    o.value = z; o.textContent = z; selZoneSci.appendChild(o); });
  ```
  → Le filtre liste automatiquement toutes les valeurs distinctes de `s.zone`. Comme la donnée contient déjà "Dauphiné-Lacassagne" ET "Montchat", **les deux apparaissent déjà dans ce dropdown aujourd'hui**.

### Verdict E2
**AJOUT DE CONFIG / UI, PAS un refactor.** Le multi-zone est déjà :
- prévu dans `AGENCES_CONFIG.zones` (tableau),
- présent dans la donnée (`zone` par SCI),
- exposé dans un dropdown dynamique.

Un « switch Dauphiné/Montchat » dans le HEADER = soit (a) promouvoir le `sci-filter-zone` existant en switch header, soit (b) ajouter un petit sélecteur header qui pré-filtre `s.zone`. **Aucune refonte du chargement ni du pipeline.** (Déduction d'implémentation ; le reste est preuve directe.)

---

## E3 — CHARGEMENT DE LA BASE SCI Dauphiné

### Source de données = fichier JSON committé (PAS de KV pour la base elle-même)
La base SCI est un **fichier JSON statique servi depuis GitHub raw**, pas une clé KV.

`index.html:5600-5606` (branche agence simple, cas `dauphine-lacassagne`) :
```js
} else {
  // Compte simple — chemin standard agence-sci.json
  const path = agenceConfig.dataJsonPath.replace('.json', '-sci.json');
  const resp = await fetch(`${GITHUB_RAW}/${path}?t=${Date.now()}`);
  if (!resp.ok) throw new Error();
  const data = await resp.json();
  rawSci = data.sci || [];
}
```
- `agenceConfig.dataJsonPath` = `data/dauphine-lacassagne.json` (worker.js:47) → remplacé en **`data/dauphine-lacassagne-sci.json`**.
- `GITHUB_RAW` pointe sur `https://raw.githubusercontent.com/liquid69006/DPE-PROSPECTOR/main` (cf. usage worker.js:1385 même pattern).
- Composites lopez/bagot : fusion de plusieurs `{agence}-sci.json` (index.html:5570-5599) — non concerné par DL.

**Fichier base SCI Dauphiné = `data/dauphine-lacassagne-sci.json`** (committé dans le repo). Structure : `{ millesime, derniere_maj, sci:[...] }`.

### Clés KV liées au SCI Prospector (le KV ne stocke PAS la base, mais les assignments/méta)
Pattern exact des clés KV (worker.js, `env.DPE_KV`) :

| Clé KV (pattern exact) | Route worker.js (regex + méthode) | Contenu |
|---|---|---|
| `sci-assignments:{agenceId}` | `/^\/sci-assignments\/([a-z0-9-]+)$/` — GET & POST (worker.js:589-606) | qualif/conseiller/statut prospection par SCI (objet) |
| `msb_key:{agence}` | (clé MSB, hors scope direct) | clé API MySendingBox |
| `dernierCourrier...` (lecture live MSB) | route `/dernierCourrier/:agence` (worker.js:1314+) | dates dernier courrier, calculé live (pas une base) |

Pour DL : **`sci-assignments:dauphine-lacassagne`** (preuve : worker.js:596 GET / 602 PUT, et index.html:5651/5672 `/sci-assignments/${agenceId}`).

Côté front, fallback localStorage : `sci_assign_{agenceId}` (index.html:5658, 5669).

**Conclusion E3** : base = fichier `data/dauphine-lacassagne-sci.json` (raw GitHub) ; le seul KV propre au SCI est `sci-assignments:dauphine-lacassagne` (assignments, pas la base). Montchat est DÉJÀ dans ce même fichier (champ `zone`), donc aucune nouvelle clé KV ni nouveau fichier base n'est requis pour exposer Montchat.

---

## E4 — HEADER & point d'insertion du switch

### Construction du header
- HTML header : `index.html:575-586`, `<div class="header-inner">`.
  - Logo : l.576 `<div class="header-logo">DPE <span>Prospector</span></div>` (préfixe piloté par `#logo-prefix`/`#logo-suffix`, cf. switchMode 2217-2223).
  - Nom agence : l.577 `<div class="header-agence" id="header-agence-name">—</div>`.
  - **Bloc de switch de mode** : `index.html:580-584` `<div class="mode-switch" id="mode-switch">` (les 3 boutons DPE/SCI/Secteur). C'est le point naturel pour un switch de zone SCI.
- Recoloration header selon mode : `switchMode()` index.html:2225-2232.

### Point d'insertion recommandé pour le switch Dauphiné/Montchat
Deux candidats, par ordre de moindre effort :
1. **Réutiliser `<select id="sci-filter-zone">`** (index.html:710) déjà dynamique (E2) — option la plus simple, zéro nouvelle plomberie ; il suffirait de le styliser/déplacer ou de l'ajouter au header.
2. **Ajouter un sélecteur dédié dans `#mode-switch`** (index.html:580-584) ou juste à côté, visible uniquement en mode SCI (`isSci`).

### Patterns réutilisables existants (header dynamique)
- **Titre dynamique Secteur** : `index.html:765` `<h2 id="secteur-titre">…Dauphiné-Lacassagne (Lyon 3e)</h2>`, mis à jour par `loadSecteurData()` index.html:2423-2424 :
  ```js
  const tt = document.getElementById('secteur-titre');
  if (tt) tt.textContent = '🗺 Secteur Prospector — ' + secName;
  ```
- **Résolveur agence→zone/nom/ville réutilisable** : `function secteurResolve()` index.html:2406-2417 — une **table de mapping** `agenceId -> [fichier, idKV, nomAffiché, ville]`. C'est EXACTEMENT le pattern à copier pour un switch de zone (mapper `zone -> {nom, ville Maps, …}`). Extrait :
  ```js
  const M = {
    'dauphine-lacassagne': ['secteur_dauphine_lacassagne_light.json', 'dauphine-lacassagne', 'Dauphiné-Lacassagne (Lyon 3e)', 'Lyon 3'],
    'motte-picquet':       ['secteur_motte_picquet_light.json', 'motte-picquet', 'Motte-Picquet (Paris 15e - 7e)', 'Paris 15'],
  };
  return M[agenceId] || M['dauphine-lacassagne'];
  ```
- **Variable `secteurVille`** (index.html:2255, fixée 2422) : précédent direct d'une « variable de zone » qui pilote l'affichage + le lien Google Maps. Un `sciZone` analogue serait cohérent.

**Conclusion E4** : header = index.html:575-586 ; insertion la plus propre dans `#mode-switch` (580) en visible-si-SCI, OU réutilisation directe de `#sci-filter-zone` (710). Pattern réutilisable = `secteurResolve()` (2406) + `secteur-titre` (765/2423) + variable `secteurVille` (2255).

---

## E5 — PIPELINE (génération de la base, définition du périmètre) — LE PLUS IMPORTANT

### Le générateur est IN-REPO et déjà multi-zone
**`scripts/majic_sci_2025.py`** (in-repo, 339 lignes) génère `data/dauphine-lacassagne-sci.json`.
Docstring l.1-18 : « Extrait les SCI propriétaires dans les zones **Dauphiné-Lacassagne et Montchat** depuis le fichier MAJIC 2025 (locaux, parquet). »

### SOURCES
1. **MAJIC 2025** (parquet local `majic_locaux2_2025.parquet`, passé en `--fichier`) — source primaire des SCI propriétaires.
   - Filtre : `code_insee == "69383"` (Lyon 3e) **+** `forme_juridique == "6540"` (SCI). (majic_sci_2025.py:266)
   - Dédup par `section + numero_parcelle + numero_siren` (l.271-272).
   - Comptage portefeuille national par SIREN (`nb_biens_total`, l.256-261, 310).
2. **API BAN** (`api-adresse.data.gouv.fr/search/csv`) — géocodage batch des adresses pour obtenir lon/lat (l.78, 101-210).
3. **API Recherche Entreprises** (`recherche-entreprises.api.gouv.fr/search`) — enrichissement dirigeants/siège/état actif (l.79, 221-242).
   - Pas de DVF, pas de RNC, pas de BDNB dans ce pipeline SCI (≠ pipeline Secteur).

### DÉFINITION DU PÉRIMÈTRE = POLYGONES GPS (Shapely), pas IRIS/îlots/bbox
Mécanisme exact (majic_sci_2025.py:31-76) :
```python
from shapely.geometry import Point, Polygon
ZONES = {
    "Dauphiné-Lacassagne": Polygon([ [lon,lat], ... 13 sommets ... ]),   # l.35-50
    "Montchat":            Polygon([ [lon,lat], ... 22 sommets ... ]),   # l.51-75
}
```
Affectation de zone par point-in-polygon (l.212-219) :
```python
def dans_zone(lon, lat):
    if lon is None: return None
    pt = Point(lon, lat)
    for nom, poly in ZONES.items():
        if poly.contains(pt):
            return nom
    return None
```
Le géocodeur appelle `dans_zone` (l.161) ; chaque SCI reçoit son `zone` (l.281, 305). Seules les SCI dans un polygone sont gardées : `df_zone = df_dedup[df_dedup["zone"].notna()]` (l.284). Sortie l.304-316 avec champ `"zone": row["zone"]`.

**=> Le critère de périmètre est un POLYGONE de coordonnées [lon, lat] codé en Python.** C'est exactement ce qu'on redéfinit/affine depuis un KML : extraire les sommets du KML Montchat et les coller dans `ZONES["Montchat"]`.

### secteurs.json contient aussi le polygone (réutilisable)
`data/secteurs.json` → `dauphine-lacassagne.geo.zones[]` contient **les DEUX polygones** (Dauphiné + Montchat), au format `[lat, lon]` (attention : ordre inversé vs le script Python qui est `[lon, lat]`). Champs geo : `dep:"69"`, `code_commune:["383"]`, `codes_postaux:["69003"]`, `bdnb_dep_prefix:["69383000"]`, `rnc_dep_prefix:["69123383"]`. Note `_meta.geo_lists_note` : listes pour supporter le multi-commune/arrondissement. Ce fichier est éditable à la main et **n'est pas lu par le worker** (config pipeline pure).

### KML disponibles dans le repo
`data/kml/` contient `Secteur_DL_-_new.kml`, `Secteur_DL_-_non_raye.kml`, `Secteur_DL_-_raye.kml`. **Aucun KML nommé "Montchat" n'existe encore** — c'est le KML que Yann fournira pour (re)définir le périmètre Montchat. Le polygone Montchat actuellement codé (22 sommets) vient probablement d'un KML antérieur ; il pourra être remplacé/affiné.

### Donnée produite — structure (preuve directe, comptage)
`data/dauphine-lacassagne-sci.json` :
- Clés top : `["millesime", "derniere_maj", "sci"]`
- `sci` : **1917 entrées**
- Répartition `zone` : **{ "Dauphiné-Lacassagne": 1158, "Montchat": 759 }**
- Champs par SCI : `adresse_bien, code_droit, gerants, millesime, nb_biens_total, parcelle, sci_active, sci_nom, sci_siren, siege_social, zone`
- Le champ trahissant le critère de périmètre = **`zone`** (string "Dauphiné-Lacassagne" | "Montchat"). Pas de `code_iris`/`ilot` ; le périmètre est appliqué en amont (polygone) et matérialisé dans `zone`.

**Conclusion E5** : pipeline in-repo, source MAJIC+BAN+RechercheEntreprises, **périmètre = polygone GPS Shapely**. Montchat est déjà généré (759 SCI). Pour « refaire Montchat depuis un KML » : extraire les sommets du KML → remplacer `ZONES["Montchat"]` (et idéalement `secteurs.json geo.zones[Montchat].polygone`, en respectant l'ordre lat/lon de chaque fichier) → relancer `python scripts/majic_sci_2025.py --fichier <parquet MAJIC>`. (Le parquet MAJIC source est local/hors-dépôt.)

---

## CONCLUSION

**(a) STRUCTURE de SCI Prospector** — MODE partagé dans la SPA `index.html` (pas de page dédiée). Bloc rendu `#section-sci` index.html:706-761 ; fonctions `loadSciData` (5563), `loadSciAssignments` (5649), `renderTableSci`/`renderDirigeant` (5687). Switch des 3 modes via `switchMode(mode)` (2200) + boutons header `#mode-switch` (580-584). Preuve directe.

**(b) MULTI-ZONE-READY ou refactor** — **MULTI-ZONE DÉJÀ READY = simple ajout d'UI, AUCUN refactor de fond.** Montchat existe déjà : config `zones:["Dauphiné-Lacassagne","Montchat"]` (worker.js:49), donnée taguée `zone` (759 entrées Montchat), dropdown dynamique `sci-filter-zone` (index.html:710 + peuplement 5623-5630). Point exact pour le switch header : `#mode-switch` (index.html:580) ou réutilisation de `#sci-filter-zone` (710).

**(c) CLÉS KV** — la base SCI N'EST PAS en KV : c'est le fichier committé `data/dauphine-lacassagne-sci.json` servi via GitHub raw (index.html:5600-5606). Le seul KV propre au SCI = **`sci-assignments:dauphine-lacassagne`** (route `/^\/sci-assignments\/([a-z0-9-]+)$/` GET/POST, worker.js:589-606 ; fallback localStorage `sci_assign_dauphine-lacassagne`).

**(d) POINT D'INSERTION du switch header** — `index.html` : bloc `#mode-switch` ligne 580 (ou à côté, visible si `isSci`). **Pattern réutilisable** = `secteurResolve()` (2406-2417, table de mapping agence→[fichier,id,nom,ville]) + titre dynamique `#secteur-titre` mis à jour en 2423-2424 + variable `secteurVille` (2255). Un `sciZone` calqué sur `secteurVille` + une table `ZONES_SCI` calquée sur `secteurResolve` = la voie la plus cohérente avec le code existant.

**(e) DÉFINITION DU PÉRIMÈTRE à répliquer pour Montchat** — **polygone GPS (Shapely `Polygon`), point-in-polygon**, dans `scripts/majic_sci_2025.py` (`ZONES` l.34-76, `dans_zone` l.212-219). Pas d'IRIS, pas d'îlots, pas de bbox, pas de liste d'adresses. Doublé dans `data/secteurs.json` → `dauphine-lacassagne.geo.zones[]` (format [lat,lon]). **Pour Montchat depuis un nouveau KML** : extraire les sommets du KML, remplacer le polygone `ZONES["Montchat"]` (ordre [lon,lat] dans le .py) et/ou `geo.zones[Montchat].polygone` (ordre [lat,lon] dans secteurs.json), puis relancer le script sur le parquet MAJIC. Le polygone Montchat est DÉJÀ présent (22 sommets) ; le KML servira à le redéfinir/affiner. KML existants : `data/kml/Secteur_DL_-_*.kml` (aucun "Montchat" pour l'instant).

### Preuve directe vs déduction / hors-dépôt
- **Preuve directe (code/données lus)** : tout E1, E3, E5 (script lu intégralement + comptage JSON), config worker.js, dropdown index.html, `secteurs.json`.
- **Déduction** : recommandations d'implémentation du switch en E2(d)/E4 (où insérer, quel pattern copier) — non encore codées.
- **Hors-dépôt / introuvable** : le **parquet MAJIC source** (`majic_locaux2_2025.parquet`, local) ; le **DVF DL** référencé dans secteurs.json (`C:\Users\Station 5\dvf_dauphine_lacassagne.json`, hors scope SCI) ; **aucun KML Montchat** dans le repo (à fournir par Yann).
