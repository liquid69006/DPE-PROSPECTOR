# Diag etat des lieux FRONT Montchat — post option B (HEAD = dfcd766)

> READ-ONLY. Aucune modification de code/donnees/KV. Rapport seul.
> Date : 2026-06-03. Perimetre : SPA `index.html` (7356 lignes) apres l'overhaul
> "Secteurs option B / beta" (commits `d98342d`..`dfcd766`) qui a ete COMMITTE ET
> POUSSE. On re-cartographie le front courant pour readapter le Montchat restant.
> Convention preuve : **[PREUVE]** = code/donnee lus (n. ligne) ; **[DEDUCTION]** = inference.

---

## CORRECTION IMPORTANTE DE LA PREMISSE (preuve git)

La consigne dit "le commit Montchat n'est PAS pousse". **C'est FAUX au moment du
diag.** [PREUVE git] :
- `git rev-parse HEAD` == `git rev-parse origin/main` == `git ls-remote origin main`
  == `dfcd766`. Donc HEAD est l'etat reel du remote.
- Les commits du build Montchat `141fd12` ("build structurel Montchat
  sources+light+ilotage+toggle") et `fecfa33` ("Montchat manche A") sont
  **ancetres de origin/main** (`git merge-base --is-ancestor 141fd12 origin/main`
  -> vrai). Idem `72d7cbd`/`a7a4c57` (kml_manifest), `a135cd9`..`dfcd766` (option B).
- Tous les fichiers Montchat sont **dans HEAD et pousses** : `secteur_montchat_light.json`,
  `kml/Ilotage_Montchat.kml`, `kml_manifest.json`, `_arbitres_montchat.json`,
  `_cles_invalides_montchat.json` (`git cat-file -e HEAD:<f>` OK pour les 5).

**Le SEUL element Montchat non commite = la modif working-tree de
`data/secteur_montchat_light.json`** (`git status` -> ` M`, +936 insertions).
La version POUSSEE (HEAD) a **1401 adresses** (1399 `_ilot`) ; la version
working-tree locale a **1430 adresses** (1428 `_ilot`). C'est la seule chose
"non poussee" cote Montchat (issue de manches de qualif ulterieures non commitees).

---

## E1 — MENU / PANNEAU SECTEUR ACTUEL (post option B)

### Header `#section-secteur` [PREUVE l.763-782]
- `#secteur-titre` (l.765) : titre dynamique pilote par `loadSecteurData` (l.2528-2529).
- **`#secteur-zone-toggle` (l.767-772)** : le toggle DL/Montchat, place
  IMMEDIATEMENT apres le titre dans le meme flex-row header (l.764).
  - 2 boutons : `#szone-dl` (l.768, `onclick="secteurSetZone('dl')"`) et
    `#szone-mtc` (l.770, `onclick="secteurSetZone('montchat')"`).
  - `style="display:none"` par defaut, passe a `inline-flex` par
    `secteurZoneSyncBtns()` quand `agenceId==='dauphine-lacassagne'` (l.2514).
  - **VERDICT toggle : toujours dans le header, en 2e position (apres le titre),
    visible, NON masque ni recouvert par l'option B.** L'overhaul n'a touche ni
    le header ni le toggle (le diff `dfcd766` ne porte que sur les libelles uni +
    le lock ; le toggle a ete pose par `141fd12`, intact).

### Barre d'outils (l.783-860) — inchangee par option B
- recherche `#secteur-search` ; 4 dropdowns (Categorie / RNC / Ventes / Logement) ;
  `📊 Ventes strictes` (`secteurToggleStrict`) ; presets `😴 Dormantes` /
  `❓ A qualifier` ; `⚡ Generer secteurs` (`#secteur-gen-btn` -> `sctGenOpen`) ;
  cadenas `#secteur-genlock-btn` (`sctGenToggleLockSettings`) ;
  **`🎯 Secteurs & conseillers` (`#secteur-uni-btn` -> `sctUniOpen`, l.855)**.

### Ce que l'option B a CHANGE [PREUVE `git show dfcd766`]
1. **Bouton "🔄 Reattribuer secteurs" RETIRE** de la barre (l'ancien bouton
   flottant `sctAttrib*` ; le diff supprime la ligne `>🔄 Réattribuer secteurs<`).
   ATTENTION a ne pas confondre : le bouton **"➕ Reattribuer les vacants"**
   DANS le panneau uni (l.1088-1091) **SUBSISTE** (feature differente : repartit
   le pool de vacants, ne touche pas les bases).
2. **De-beta** : libelles `(beta)` retires du bouton `#secteur-uni-btn` et du
   titre du panneau ; le pied de panneau ne dit plus "Phase A — aucune ecriture KV"
   mais mentionne "« 💾 Enregistrer » pour sauvegarder" (persistance KV active
   depuis `cdb2f3c`/`6c62bba`, route `/secteur-uni/:agence`).
3. **"Generer les secteurs" desactive si verrou** : dans `sctUniOpen` (l.4515-4525),
   `#sct-uni-gen-btn` est `disabled`+grise si `localStorage[sctGenLockKey()]==='true'`.

### Panneau unifie `#sct-uni-overlay` (option B) [PREUVE l.1070-1120]
Modale "Secteurs & conseillers" : colonnes conseillers + selecteur secteur(=couleur)
(`#sct-uni-cols`), barre d'actions : `➕ Reattribuer les vacants` (`sctUniRunBalance`),
`⚡ Generer les secteurs` (`#sct-uni-gen-btn` -> close + `sctGenOpen`),
`💾 Enregistrer` (`sctUniSave` -> POST `/secteur-uni/`), `↺ Reinitialiser`
(`sctUniReset`), `🗺️ Voir la carte` (`sctUniViewMap`), `📥 Exporter A0`
(`sctUniExportA0`). Le wizard historique `#sct-gen-overlay` (l.917-1011) coexiste
toujours (Generer/Nouvelle repartition/Voir la carte/Enregistrer).

---

## E2 — TOGGLE MONTCHAT — VERIFICATION (pas suppose)

### `secteurResolve()` — TOUJOURS zone-aware [PREUVE l.2475-2493]
La fonction teste `if (agenceId === 'dauphine-lacassagne' && secteurZone === 'montchat')`
et retourne le tuple Montchat. **Evaluation node (extraction + run sur les 2 zones)** :
```
DL  zone=dl       -> ["secteur_dauphine_lacassagne_light.json","dauphine-lacassagne","Dauphine-Lacassagne (Lyon 3e)","Lyon 3"]
DL  zone=montchat -> ["secteur_montchat_light.json","dauphine-lacassagne-montchat","Montchat (Lyon 3e/8e)","Lyon 3"]
MP  zone=montchat -> ["secteur_motte_picquet_light.json","motte-picquet",...]  (zone ignoree -> gate OK)
```
**CONFIRME** : light = `secteur_montchat_light.json`, idKV = `dauphine-lacassagne-montchat`,
nom header = "Montchat (Lyon 3e/8e)". Gate agence OK (MP ne bascule jamais).

### `secteurSetZone(z)` — present, fait le bon travail [PREUVE l.2497-2506]
`if (z===secteurZone) return;` -> set `secteurZone=z` -> `secteurZoneSyncBtns()` ->
**reset etat zone-dependant** (`secteurAssign/Fusions/Noms/SciByCle={}`, `secteurOpenIlot=null`,
`sctGenState.ilots=[]`/`repartition={}`) -> `loadSecteurData()`. Conforme.

### `loadSecteurData()` — utilise `secteurResolve()` partout [PREUVE l.2524-2563]
- `const [secFile, secId, secName, secVille] = secteurResolve();` (l.2526).
- titre <- `secName` (l.2529) ; light fetch `${GITHUB_RAW}/data/${secFile}` (l.2539) ;
  **KV fetch `${API_URL}/secteur-assignments/${secId}` (l.2555)** ; SCI fetch
  `${GITHUB_RAW}/data/${secId}-sci.json` (l.2540).
- **AUCUN `agenceId` en dur** dans les fetch secteur. L'option B (panneau uni) lit
  AUSSI `secId` zone-aware pour ses 3 routes data.

### Tous les fetch `/secteur-*` + `/map-a0/*` et leur cle [PREUVE grep + lecture]
| Route fetch (front) | Cle utilisee | Zone-aware ? |
|---|---|---|
| `GET/POST /secteur-assignments/${secId}` (l.2555, 2608, etc.) | `secId` | OUI |
| `GET /secteur-repartition/${secId}` (l.4543) + PATCH `.../ilot` | `secId` | OUI |
| `GET/POST /secteur-attribution/${secId}` | `secId` | OUI |
| `GET/POST /secteur-uni/${secId}` (l.4595 GET, l.4878 POST) | `secId` | OUI |
| `POST /map-a0/generate/${secId}`, `GET /map-a0/status/${secId}` (l.5184, 5205) | `secId` | OUI |
| `GET /conseillers/${agenceId}` (l.4529) | **`agenceId`** | NON (VOULU) |

Le SEUL fetch par `agenceId` est `/conseillers/` (l.4529). **C'est correct et
attendu** : les conseillers sont une ressource d'AGENCE (partagee DL/Montchat), il
n'y a pas de liste de conseillers par zone. Aucune regression.

Cote worker [PREUVE worker.js l.609-852] : toutes les routes matchent
`/^\/secteur-*\/([a-z0-9-]+)$/` et `/^\/map-a0\/(generate|status)\/([a-z0-9-]+)$/`.
La regex `[a-z0-9-]+` accepte `dauphine-lacassagne-montchat`. La cle KV est
`secteur_assignments:${agenceId}` ou `${agenceId}` = le segment capture = le secId
envoye par le front -> **namespace KV par zone effectif, ZERO changement worker**.

### `sctGenLockKey()` — verrou per-zone [PREUVE l.4101-4106]
`return 'sctGen_locked_' + secId` (secId zone-aware) -> verrou separe DL vs Montchat. Bon.

### Side-files `_arbitres_montchat` / `_cles_invalides_montchat`
[PREUVE grep] **PIPELINE-ONLY, jamais charges par le front** : aucun fetch de
`_arbitres_*`/`_cles_invalides_*` dans `index.html` (ils sont lus par les scripts
Python de qualification). CONFIRME conforme au diag d'origine. Contenu actuel :
`_arbitres_montchat.json` = `[]` (0), `_cles_invalides_montchat.json` = 1 entree.

### CONCLUSION E2
**Le switch DL<->Montchat charge REELLEMENT le bon light + le bon namespace KV par
zone.** L'option B n'a introduit AUCUNE regression : le panneau uni (nouveau) lit
lui aussi `secteurResolve()[1]` pour ses 3 routes (`secteur-repartition`,
`secteur-uni`) et le verrou est per-secId. Aucun nouveau panneau ne lit un
`agenceId` en dur (sauf `/conseillers/`, ressource d'agence, voulu).

---

## E3 — CARTES LEAFLET (scoping KML par zone)

### Mecanisme [PREUVE l.4942-4961]
`sctResolveKmlFiles()` : fetch `data/kml_manifest.json` (cache module `_sctKmlManifest`),
puis `zone = secteurZone || 'dl'`, `list = manifest[agenceId][zone]`. Fallback en dur
`SCT_MAP_KML_FALLBACK[agenceId][zone]` (l.4934-4939) si le fetch echoue. Retourne
`list.map(fn => 'data/kml/' + fn)`.

### `kml_manifest.json` [PREUVE lu]
```json
{ "dauphine-lacassagne": {
    "dl": ["Secteur_DL_-_new.kml","Secteur_DL_-_raye.kml","Secteur_DL_-_non_raye.kml"],
    "montchat": ["Ilotage_Montchat.kml"] } }
```
Le fallback en dur (l.4934-4939) contient la MEME entree `montchat: ['Ilotage_Montchat.kml']`.

### `sctMapOpen()` [PREUVE l.4966-5161]
`L.map('sct-map-canvas')` + tuiles CartoDB Positron ; `await sctResolveKmlFiles()`
(l.4991) -> fetch tous les KML, parse Placemarks -> polygones colores par
`sctGenState.repartition`. **Une seule carte Leaflet** dans l'app (`L.map` n'apparait
qu'ici, l.4980).

### A0 (export PNG) [PREUVE l.5171-5246 + worker l.797-824 + scripts/generate_map_a0.py]
`sctMapExportA0` POST `/map-a0/generate/${secId}` -> worker dispatch
`generate-map-a0.yml` avec `agence_id = secId` -> `generate_map_a0.py` (l.75-106)
parse le suffixe `-montchat` -> `zone='montchat'`, lit `kml_manifest.json[base_agence][zone]`
-> charge `Ilotage_Montchat.kml`. **La chaine A0 est elle aussi zone-aware bout-en-bout.**

### VERDICT E3 : **Montchat CABLE.**
Quand `secteurZone==='montchat'`, la carte Leaflet (modale "Voir la carte") ET
l'export A0 chargent `Ilotage_Montchat.kml` via le manifeste (et le fallback en dur).
Les 133/134 ilots Montchat sont donc desservis par la carte. Le light a 130 valeurs
`_ilot` distinctes (1428/1430 adresses ilotees) -> l'arbre UI et la repartition
sct sont peuples sur Montchat.

> CAVEAT non bloquant : `SCT_MAP_KML_REMAP = {'3A':'3','3B':'13'}` (l.4964) est
> specifique DL (splits d'ilots DL). Pour Montchat les noms KML sont numeriques
> (118->195, 162 sont des fixes APPLIQUES dans le KML source, pas dans le remap
> front), donc le remap est inerte sur Montchat (`REMAP[rawName] || rawName`). OK.

---

## E4 — DEPENDANCES / CE QUI CASSERAIT EN PROD SI MONTCHAT ACTIVE AUJOURD'HUI

Le front (Pages) sert l'`index.html` POUSSE ; light/KML/manifest sont fetches depuis
`GITHUB_RAW = raw.githubusercontent.com/.../main` (l.1303) = branche `main` POUSSEE.
HEAD == origin/main, donc tout ce qui est dans HEAD est servi en prod.

| Ressource fetchee en zone Montchat | Committee ? | Poussee ? | Effet PROD si Montchat active |
|---|---|---|---|
| `GITHUB_RAW/data/secteur_montchat_light.json` | OUI (HEAD) | **OUI** (`141fd12`/`fecfa33` ancetres origin/main) | **OK** — charge. MAIS sert la version **1401 adresses** (HEAD), pas la 1430 locale working-tree (936 ins. non commitees) |
| `data/kml_manifest.json` (manifeste) | OUI | OUI (`72d7cbd`) | OK — fetch relatif servi par Pages |
| `data/kml/Ilotage_Montchat.kml` (carte + A0) | OUI | OUI (`141fd12`) | OK — carte/A0 chargent les ilots |
| KV `secteur_*:dauphine-lacassagne-montchat` | n/a (KV) | n/a | OK — GET vide gracieux (cles creees aux 1eres ecritures ; manche A peut deja en avoir pose) |
| `GITHUB_RAW/data/dauphine-lacassagne-montchat-sci.json` | **NON** (fichier absent) | **NON** | **Pas de casse** : SCI fetch est `r.ok ? json : null` + `.catch(()=>null)` (l.2540-2542) -> colonne SCI vide, fallback `light.sci_nom`. Cosmetique. |

**CONCLUSION E4 : RIEN ne casserait en prod si Montchat etait active aujourd'hui.**
Le toggle, le light pousse (1401 adr), le manifeste, le KML et les routes KV
zone-aware sont tous en place et pousses. Le pire effet est :
1. La prod servirait l'ancien light **1401 adresses** au lieu du **1430** local
   (les +29 adresses / re-tags de qualif working-tree ne sont pas poussees) ;
2. La colonne SCI serait vide sur Montchat (fichier SCI Montchat jamais genere).

---

## E5 — RESTE A FAIRE FRONT POUR MONTCHAT AVANT LE PUSH

Le gros oeuvre front est DEJA fait ET pousse (toggle, secteurResolve, loadSecteurData,
manifeste, fallback, carte, A0, lock per-zone). Il reste :

### Bloquant pour exposer Montchat "propre" (mais PAS pour ne-pas-casser)
- **(B1) Committer/pousser le `secteur_montchat_light.json` working-tree** (1430 adr,
  +936 ins.). Sinon la prod sert l'ancien 1401-adr. C'est une decision de Yann
  (les +29 viennent de manches de qualif locales non scellees). -> **decision +
  commit/push**, pas du code.
- **(B2) `test_render_secteur.js`** : verifier qu'il passe exit 0 sur DL **et**
  Montchat (gotcha connu MEMORY.md : plages de lignes hardcodees re-cassees a
  chaque edition d'`index.html`). L'option B a modifie `index.html` (l.~4515-4525,
  l.~1088-1118) -> **resynchroniser les plages du test avant tout commit front**.
  (A verifier/lancer ; non execute dans ce diag read-only.)

### Cosmetique / amelioration (non bloquant)
- **(C1) SCI Montchat** : generer `data/dauphine-lacassagne-montchat-sci.json` si on
  veut la colonne SCI peuplee. Sinon colonne vide (gere gracieusement). Hors front.
- **(C2) `SCT_MAP_KML_REMAP`** (l.4964) est DL-only et inerte sur Montchat — laisser
  tel quel ; si un jour un ilot Montchat est splite cote KML, etendre le remap.
- **(C3) Tampon de build** dans le header (l.781 "build 2026-05-18·strict+seuils")
  est obsolete — purement cosmetique.

### Deja fait (NE PAS refaire)
- Toggle header zone-aware visible (gate agence) ; secteurResolve 2D ;
  loadSecteurData/KV/lock per-zone ; manifeste + fallback montchat ; carte Leaflet
  + A0 montchat-aware (script CI inclus) ; side-files montchat pipeline-only.

---

## CONCLUSION (5 verdicts)

**(a) Menu Secteur post-option-B + place du toggle.** Header `#section-secteur`
inchange ; barre d'outils inchangee SAUF retrait du bouton flottant "🔄 Reattribuer
secteurs". Panneau uni "Secteurs & conseillers" de-beta + persistant (KV `/secteur-uni/`)
+ "Generer" desactive si verrou. **Le toggle `#secteur-zone-toggle` est toujours en
header, 2e position apres le titre (l.767), visible (gate agence DL), NON masque.**

**(b) Ce qui a survecu/change pour Montchat (PROUVE).** `secteurResolve()`
(zone-aware, evalue node : montchat -> light+idKV+nom corrects), `secteurSetZone()`,
`secteurZoneSyncBtns()`, `loadSecteurData()` : **TOUS intacts et zone-aware**.
Toutes les routes secteur-*/map-a0 utilisent `secId` (zone-aware) ; seule
`/conseillers/` utilise `agenceId` (voulu, ressource d'agence). **AUCUNE regression
introduite par l'option B** ; le namespace KV par zone fonctionne (worker regex OK,
zero changement worker requis).

**(c) Carte Leaflet Montchat.** **CABLEE.** `sctResolveKmlFiles` lit
`kml_manifest.json[dauphine-lacassagne][montchat] = ['Ilotage_Montchat.kml']` (+
fallback en dur identique). La modale carte ET l'export A0 (script CI inclus) sont
montchat-aware. 130 ilots distincts peuples dans le light.

**(d) Dependances non-poussees qui casseraient en prod.** **AUCUNE casse.** Tout le
Montchat front + light + KML + manifeste est POUSSE (HEAD == origin/main, build
`141fd12` ancetre). Seules limites : la prod servirait l'ancien light **1401 adr**
(version locale 1430 non commitee) ; le `*-sci.json` Montchat n'existe pas (colonne
SCI vide, gere gracieusement, pas de crash).

**(e) A faire AVANT le push.**
- BLOQUANT : (B1) decider + commit/push `secteur_montchat_light.json` 1430-adr
  working-tree ; (B2) resync + faire passer `test_render_secteur.js` sur DL ET
  Montchat (plages hardcodees re-cassees par l'edition option B).
- COSMETIQUE : (C1) generer le SCI Montchat ; (C2) remap KML DL-only inerte ;
  (C3) tampon build obsolete.
