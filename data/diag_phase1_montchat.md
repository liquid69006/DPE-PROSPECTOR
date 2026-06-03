# Diag PHASE 1 - Donnees sources MONTCHAT (extraction)

> EXECUTION read/write de scripts sources. AUCUN commit, AUCUN git add, AUCUN push.
> Date : 2026-06-01. Perimetre = quartier Montchat (Lyon 3e + 8e).
> Ne touche NI a make_light*.py NI aux donnees DL existantes.

---

## 1. ETAPE 1 - Perimetre Montchat

**Script** : `C:\Users\Station 5\build_perimetre_montchat.py`
**Source de verite** : `DPE-PROSPECTOR/data/kml/Ilotage_Montchat.kml` (134 ilots).
**Sortie** : `C:\Users\Station 5\perimetre_montchat.json` (cle `poly`).

Methode :
1. Parse des 134 `<Polygon>` (regex `<coordinates>`, format `lon,lat,alt`). Les 2
   `<name>` non-ilot (doc / "Couche sans titre") sont ignores (ce sont des
   `<Folder>`/`<Document>` names, pas des `<Polygon>`).
2. Anneaux refermes si necessaire + `Polygon(ring).buffer(0)` (repare
   auto-intersections). **0 anneau a refermer** : les 134 anneaux KML sont deja
   fermes (1er point == dernier), y compris l'ilot "162".
3. UNION des 134 polygones (`unary_union`) -> MultiPolygon.
4. **Buffer ~40 m** : **methode fallback degres `0.00045`** (pyproj NON installe
   dans l'environnement -> pas de reprojection L93). Resultat : le buffer fusionne
   l'union en **un seul Polygon** (pas de MultiPolygon residuel).
5. `simplify(0.00005, preserve_topology=True)` -> reste un Polygon simple.
   **Pas de MultiPolygon en sortie -> pas besoin d'enveloppe convexe.**
6. Ecriture des sommets `[[lon,lat],...]`.

Resultat perimetre :
- **45 sommets**
- **bbox lon 4.86941 -> 4.89876** (KML attendu 4.8698 -> 4.8983)
- **bbox lat 45.73990 -> 45.75538** (KML attendu 45.7404 -> 45.7549)
- coherence bbox vs KML : **OK** (englobe le KML, deborde de ~40 m = buffer)
- aire approx : **2.58 km2**

---

## 2. ETAPE 2 - Les 6 scripts `_montchat` crees

Tous dans `C:\Users\Station 5\`, copies des scripts DL avec UNIQUEMENT les
changements ci-dessous (logique inchangee). Entrees brutes INCHANGEES
(`rnc_t3_2025.csv`, `dvf_2024/2025.txt.zip`, `majic_locaux2_2025.parquet`,
API BDNB/WFS/BAN).

### Changement commun a tous : POLY
`POLY = [...]` litteral remplace par
`POLY = json.load(open(r"C:\Users\Station 5\perimetre_montchat.json"))["poly"]`.

### `rnc_extract_montchat.py`
- POLY <- perimetre_montchat.json
- INSEE/CP : `insee == "69383" or cp == "69003" or comm == "69383"` ->
  `insee in ("69383","69388") or cp in ("69003","69008") or comm in ("69383","69388")`
- OUT : `rnc_dauphine_lacassagne.json` -> `rnc_montchat.json`
- prints/docstring DL -> Montchat (cosmetique)

### `dvf_extract_montchat.py`
- POLY <- perimetre_montchat.json
- Filtre streaming `lire_lyon3` : `f[ci]=="383"` -> `f[ci] in ("383","388")`
  (departement reste `"69"`)
- OUT : `dvf_dauphine_lacassagne.json` -> `dvf_montchat.json`
- prints/docstring DL -> Montchat (cosmetique)

### `filosofi_extract_montchat.py`
- POLY <- perimetre_montchat.json
- WFS CQL : `code_insee=%2769383%27` ->
  `code_insee%20IN%20(%2769383%27,%2769388%27)` (les 2 communes)
- OUT : `filosofi_dauphine_lacassagne.json` -> `filosofi_montchat.json`
- champ `secteur` du payload + `_methodologie` -> Montchat (embarques)

### `bdnb_extract_montchat.py`
- POLY <- perimetre_montchat.json
- **IRIS** : le script DL scope l'API BDNB par liste d'IRIS en dur (Lyon 3e
  uniquement). Remplacee par les **16 IRIS (12 en 69383 + 4 en 69388) qui
  intersectent le polygone Montchat**, derives du WFS IGN contours_iris :
  `693830601, 693830602, 693830604, 693830701, 693830702, 693830703, 693830801,
  693830802, 693830803, 693830804, 693830901, 693830902, 693880203, 693880204,
  693880301, 693880302`. (Liste recoupee 1:1 avec les IRIS retenus par filosofi.)
- OUT : `bdnb_dauphine_lacassagne.json` -> `bdnb_montchat.json`

### `secteur_prospector_montchat.py`
- POLY <- perimetre_montchat.json
- INSEE : `INSEE = "69383"` (scalaire) -> `INSEE_SET = {"69383","69388"}` ;
  filtre MAJIC `d[d["code_insee"] == INSEE]` -> `d[d["code_insee"].isin(INSEE_SET)]`
- **Suffixe geocodage BAN** : `f"{lab} 69003 LYON 3EME"` en dur -> suffixe derive
  de l'INSEE de la ligne MAJIC (`CP_COMMUNE = {"69383":"69003 LYON 3EME",
  "69388":"69008 LYON 8EME"}`), pour ne pas geocoder les adresses du 8e avec le
  CP/commune du 3e.
- DVF_JSON : `dvf_dauphine_lacassagne.json` -> `dvf_montchat.json`
- OUT : `secteur_dauphine_lacassagne.json` -> `secteur_montchat.json` (root)
- champ `secteur` du payload + prints/docstring -> Montchat

### `consolidate_secteur_montchat.py`
- 4 entrees re-pointees vers `*_montchat.json` (root) :
  `dvf_montchat.json`, `rnc_montchat.json`, `filosofi_montchat.json`,
  `secteur_montchat.json`
- OUT : `DPE-PROSPECTOR\data\secteur_montchat.json`
- metadata `secteur`/`commune`/noms de fichiers sources -> Montchat (embarques)

### Tables ALIAS videes
**AUCUNE.** Les tables curees DL (`ALIAS_RNC`, `COPRO_FORCE`,
`FUSION_RNC_EXTRA_NUMS`, `VOIES_HORS_SECTEUR`, ...) **ne sont PAS dans ces 6
extracteurs** : elles vivent dans `make_light.py` (hors scope). Les seules tables
presentes dans `secteur_prospector` sont `VOIE` (canonicalisation generique des
types de voie, conservee) et `SCI_FJ` (formes juridiques SCI, generique,
conservee). Rien a vider.

---

## 3. Chaine executee (ordre rnc -> dvf -> filosofi -> bdnb -> croisement -> consolidate)

Tous les scripts ont tourne sans erreur. Volumes produits :

| Etape | Sortie | Volume |
|---|---|---|
| rnc | `rnc_montchat.json` | **646 copros RNC** (3002 candidats Lyon 3e+8e avant polygone) ; 29256 lots total, 12804 habitation |
| dvf | `dvf_montchat.json` | **2552 lignes / 1051 mutations distinctes** (2467 commune 383 + 85 commune 388) |
| filosofi | `filosofi_montchat.json` | **16 IRIS** intersectes (12 en 69383 + 4 en 69388) |
| bdnb | `bdnb_montchat.json` | **3591 batiments** dans le polygone (4545 sur les 16 IRIS avant PIP) ; 17458 logements ; 674 avec immat |
| croisement | `secteur_montchat.json` (root) | **1280 adresses** (1107 MAJIC dans polygone + DVF-only) ; 116871 lignes proprietaires 69383+69388 lues |
| consolidate | **`data/secteur_montchat.json`** | 7.17 Mo |

---

## 4. VERIFS

### Top-level keys vs DL : IDENTIQUES
`secteur_montchat.json` (data/) et `secteur_dauphine_lacassagne.json` ont les
**memes 5 cles top-level** (`adresses, coproprietes, iris, metadata,
mutations_dvf`) et les **memes cles `metadata`**.

### Volumes Montchat vs DL (ordre de grandeur)
|  | copros | adresses | mutations_dvf (lignes) | iris |
|---|---|---|---|---|
| **Montchat** | 646 | 1280 | 2552 | 16 |
| Dauphine-Lacassagne | 564 | 1166 | 8852 | 15 |

Montchat est legerement plus grand que DL (copros +82, adresses +114), coherent :
quartier voisin de taille comparable + leger debordement sur le 8e. (Le bloc
`mutations_dvf` DL = 8852 correspond a un millesime DVF plus large cote DL ; le
chiffre comparable = mutations distinctes Montchat = 1051.)

### Emprise GPS vs bbox KML
Sur 1753 points geolocalises (copros RNC `_longitude/_latitude` + adresses
croisement `longitude/latitude`) :
- **bbox lon 4.86951 -> 4.89780** (KML 4.8698 -> 4.8983) : OK
- **bbox lat 45.74013 -> 45.75529** (KML 45.7404 -> 45.7549) : OK
- **0 point aberrant** hors fenetre (pas de fuite Paris/autre commune).
- Les 2 communes {69383, 69388} sont presentes dans TOUS les blocs (IRIS,
  copros RNC, mutations DVF) -> pas de "trou" sur le 8e.

---

## 5. Warnings / points a signaler

1. **Buffer = fallback degres (0.00045), pas pyproj/L93** : `pyproj` n'est pas
   installe. Le buffer geographique ~40 m est legerement anisotrope (un peu plus
   large en lon qu'en lat aux latitudes lyonnaises) mais reste dans la tolerance
   ("petit exces d'emprise acceptable", le PIP fin se refait au niveau ilot en
   Phase 2). Si une precision metrique stricte est voulue plus tard :
   `pip install pyproj` puis re-run `build_perimetre_montchat.py`.

2. **11 copros RNC avec `code_officiel_arrondissement_commune = 69385`** (Lyon 5e)
   dans le bloc copros : ce sont des copros dont les coordonnees long/lat du
   registre tombent DANS le polygone Montchat (filtre geometrique), mais dont
   l'attribution administrative d'arrondissement RNC pointe 69385. Quirk connu du
   RNC (arrondissement declare != coordonnees). Geographiquement legitimes dans le
   perimetre. A garder a l'oeil en qualification (Phase 5) mais non bloquant.

3. **Filosofi/RP = null** (comme DL) : les attributs `nb_menages`,
   `revenu_median`, `part_locataires`, etc. restent a null (sources INSEE non
   accessibles dans l'environnement) -> `nb_residences_principales`,
   `part_locataires_moyenne`, `revenu_median_secteur` sont 0/None dans
   `stats_globales`. Comportement IDENTIQUE a DL (join pret par `code_iris`).
   Pas une regression.

4. **Pas d'orphelin polygone aberrant detecte** ; BDNB 3591/4545 batiments
   conserves apres PIP (les 954 ecartes sont en bord d'IRIS hors polygone).

---

## 6. Fichiers produits (aucun commite)

Scripts (root `C:\Users\Station 5\`) :
- `build_perimetre_montchat.py`
- `rnc_extract_montchat.py`, `dvf_extract_montchat.py`,
  `filosofi_extract_montchat.py`, `bdnb_extract_montchat.py`,
  `secteur_prospector_montchat.py`, `consolidate_secteur_montchat.py`

Donnees intermediaires (root) :
- `perimetre_montchat.json`, `rnc_montchat.json`, `dvf_montchat.json`,
  `filosofi_montchat.json`, `bdnb_montchat.json`, `secteur_montchat.json`

Sortie consolidee (in-repo, NON commitee) :
- `DPE-PROSPECTOR/data/secteur_montchat.json` (7.17 Mo)

> Prochaine etape (hors Phase 1) : `make_light_montchat.py` + ilotage KML
> (`_apply_ilot_kml_montchat.py`), cf. plan_secteur_montchat.md Phase 2.
