# Diag PHASE 2 - make_light_montchat + chaine aval generique

> EXECUTION (production de fichiers). AUCUN commit / git add / push.
> Date : 2026-06-01. NI make_light.py DL NI donnees DL (secteur_dauphine_lacassagne*)
> touchees. PYTHONUTF8=1, prints ASCII-safe. STOP a la fin (gate G2).

---

## ETAPE 0 - Les 11 copros RNC arrondissement "69385"

Champ d'adresse utile : `numero_et_voie_adresse_de_reference` (+ `_nom_copropriete`,
`code_postal_adresse_de_reference`, `_longitude/_latitude`, `commune_adresse_de_reference`).
Le `cle_adresse` est `NUM|TYPE|VOIE`.

**Verdict : les 11 sont a GARDER.** Toutes ont CP 69003 (Lyon 3e), commune Lyon, des
rues incontestablement Montchat (Dauphine, Lacassagne, Villebois Mareuil, Palais
d'Ete, Professeur Rochaix, Jeanne d'Arc, Roux Soignat, Saint-Isidore, Balthazar),
et des coords dans la bbox Montchat. Le code arrondissement 69385 (Lyon 5e) est le
**quirk RNC** signale en Phase 1 (arrondissement declare != coordonnees). AUCUNE
n'est une rue de Fourviere/Lyon 5e (pas de Rue de la Favorite / Montee...). Donc
**0 deny-list** Phase 5 sur ce lot.

| immat | rue (adresse de reference) | nom copro | lon / lat | verdict |
|---|---|---|---|---|
| AC6769996 | 75 RUE DU DAUPHINE | 75 RUE DU DAUPHINE | 4.869971 / 45.753095 | GARDER (Montchat) |
| AC7341035 | 15 RUE VILLEBOIS MAREUIL | LES TERRASSES DE MAREUIL | 4.874394 / 45.753238 | GARDER (Montchat) |
| AC7391022 | 3-5-7 RUE DU PALAIS D'ETE | LE PALAIS D'ETE | 4.874326 / 45.746163 | GARDER (Montchat) |
| AC8010274 | 63 RUE DU PROFESSEUR ROCHAIX | LE ROCHAIX | 4.877486 / 45.744833 | GARDER (Montchat) |
| AC8318594 | 12 A 20 RUE JEANNE D'ARC | LA VILLA FOUCAULD | 4.876089 / 45.751733 | GARDER (Montchat) |
| AD3160348 | 71 AVENUE LACASSAGNE | LE REVERSY | 4.871973 / 45.751890 | GARDER (Montchat) |
| AD3535994 | 1 RUE ROUX SOIGNAT | SDC VILLA CATALPA | 4.881824 / 45.747476 | GARDER (Montchat) |
| AD5117908 | RUE SAINT-ISIDORE | LE SECRET D'ISIDORE | 4.881329 / 45.750000 | GARDER (Montchat) |
| AD7135940 | 53 RUE DU PROFESSEUR ROCHAIX | RESIDENCE D'ARSONVAL | 4.877614 / 45.745482 | GARDER (Montchat) |
| AD9466327 | 201/203 AVENUE LACASSAGNE | LES TERRASSES LACASSAGNE | 4.886221 / 45.746490 | GARDER (Montchat) |
| AE8348203 | 18 RUE BALTHAZAR | Le Cheverny | 4.879005 / 45.745803 | GARDER (Montchat) |

---

## ETAPE A - Cartographie de la chaine aval DL (generique vs DL-specifique)

Ordre des correctifs lus dans `metadata` du light DL (PIPELINE.md S5) : rnc_immat ->
invisible_insecteur -> horsrnc -> doublon -> taux_logement -> usage_bdnb -> PUIS ~36
correctifs DL-terrain.

| Script | Correctif metadata | Statut | Comment on le replique pour Montchat |
|---|---|---|---|
| `make_light.py` | (generation) | DL-hardcode (constantes) MAIS structure generique | **make_light_montchat.py** : 4 constantes re-pointees + WFS 2 communes + tables ALIAS videes |
| `fix_rnc_bdnb_attribution.py` | `_correctif_rnc_immat` | **GENERIQUE** (SECTEUR-param, cibles derivees light+bdnb, 0 sidecar, 0 adresse curee) | **REPLIQUE** : `SECTEUR=montchat python ...` |
| `fix_invisible_insecteur_bgids.py` | `_correctif_invisible_insecteur` | DL-specifique (chemins DL en dur + sidecar live `_rnc_bdnb_live_missing.json` propre a DL) | **SKIP** (passe de verif live ; relève de la qualification Phase 5, pas du structurel) |
| `fix_horsrnc_attribution.py` | `_correctif_horsrnc` | logique SECTEUR-param MAIS depend du cache live `_horsrnc_bdnb_live{_suf}.json` (absent pour Montchat) | **SKIP** (necessite d'abord ses producteurs live `verif_horsrnc_bdnb.py`/`evalue_rattach_horsrnc.py` ; Phase 5) |
| `fix_doublon_adresse.py` | `_correctif_doublon` | logique **GENERIQUE** (dedup cle exacte/meme bgid) mais chemins DL en dur (cas literal seulement dans la docstring) | **REPLIQUE** : variante `fix_doublon_adresse_montchat.py` (chemins re-pointes). Resultat = **0 doublon** (no-op, light propre) |
| `fix_taux_logement.py` | `_correctif_taux_logement` | **GENERIQUE** (SECTEUR-param ; lit `Code type local` du FULL `secteur_<sec>.json`) | **REPLIQUE** : `fix_taux_logement_montchat.py` n'est PAS necessaire (deja SECTEUR-param) -> `SECTEUR=montchat python ...`. ETAPE CLE marche libre |
| `propage_usage_bdnb.py` | `_correctif_usage_bdnb` | **GENERIQUE** (SECTEUR-param, lit `data/bdnb_<sec>.json`) | **REPLIQUE** : `SECTEUR=montchat python ...` |
| `_apply_ilot_kml_dl.py` | (pose `_ilot`) | DL-hardcode (2 KML DL, RENAME DL, MALFORMED_CLE DL, snap 5) | **REPLIQUE** : `_apply_ilot_kml_montchat.py` (KML Montchat, fixes 118->195 + 162, snap tune) |

Note importante : `fix_taux_logement.py` etait deja **SECTEUR-parametrable** via `os.environ["SECTEUR"]`
(constate par lecture, non presume) -> pas de copie `_montchat` necessaire. Idem
`fix_rnc_bdnb_attribution.py` et `propage_usage_bdnb.py`. Seuls `fix_doublon_adresse.py`
(chemins DL en dur) et l'ilotage (DL-specifique) ont exige une copie `_montchat`.

`Code type local` (logement=1 maison /2 appart ; 3 dependance ; 4 commerce) :
`fix_taux_logement` le lit dans `full["mutations_dvf"]` = `data/secteur_montchat.json`
(le consolide in-repo). Verifie present (1478x'3', 860x'2', 91x'1', 74x'4', 49x'').

Les passes hors-RNC (`horsrnc`/`invisible_insecteur`) sont **generiques en logique**
mais dependent de sidecars produits par des passes de **verification BDNB live**
(api.bdnb.io) propres a chaque secteur, non encore generes pour Montchat. Elles
relevent du raffinement terrain (resolution des copros "invisibles" via relations
BDNB many-to-many) -> rattachees a la Phase 5, hors du perimetre structurel Phase 2.

---

## ETAPE B - make_light_montchat.py

Copie de `C:\Users\Station 5\make_light.py` -> `make_light_montchat.py` (hors-depot).
Changements (logique inchangee) :

- `CONS` = `DPE-PROSPECTOR/data/secteur_montchat.json` (consolide Phase 1, 7.17 Mo)
- `DVF`  = `C:\Users\Station 5\dvf_montchat.json`
- `BDNB` = `C:\Users\Station 5\bdnb_montchat.json`
- `OUT`  = `DPE-PROSPECTOR/data/secteur_montchat_light.json`
- `WFS`  CQL_FILTER : `code_insee=%2769383%27` -> `code_insee IN ('69383','69388')` (16 IRIS, 2 communes)
- `cle_to_query()` : suffixe geocodage BAN "69003 Lyon" -> "Lyon" (ne pas figer le CP 3e sur le 8e)
- filtre citycode geocodage : `g[3] == "69383"` -> `g[3] in ("69383","69388")`
- **Tables VIDEES** (Montchat vierge) :
  - `ALIAS_RNC` : ~80 alias d'adresses lyonnaises curees DL -> `{}`
  - `COPRO_FORCE` : `{"61|RUE|BARABAN": "AB2515468"}` -> `{}`
  - `FUSION_RNC_EXTRA_NUMS` : `{"AJ0217901": {41}, "AB9349846": {41}}` -> `{}`
- `code_iris` CONSERVE (pose par make_light, stats Filosofi/INSEE) ; l'ilot KML vient en aval.

**LANCE OK** (WFS + BAN + BDNB live, sans erreur). Light "avant ilot" :
16 IRIS, 633 copros, 1296 adresses, 1.58 Mo. 2 adr coord nulle (sur 173 avant
fallback), BDNB match 1294/1296.

Aussi : copie de `bdnb_montchat.json` (root) -> `DPE-PROSPECTOR/data/bdnb_montchat.json`
(les fix scripts aval lisent `data/bdnb_<sec>.json`, comme DL/MP).

---

## ETAPE C - Chaine aval generique appliquee (dans l'ordre)

| # | Passe | Commande | Effet |
|---|---|---|---|
| 1 | RNC->BDNB attribution | `SECTEUR=montchat python scripts/fix_rnc_bdnb_attribution.py --apply` | +103 lignes (93 B1/B2 + 10 B3), 973 lots RNC rendus visibles ; 1296 -> 1399 adr |
| 1b | (horsrnc / invisible) | SKIP | sidecars live absents (Phase 5) |
| 2 | dedup doublon | `python scripts/fix_doublon_adresse_montchat.py` | **0 doublon** -> no-op (light propre, aucun .bak cree) |
| 3 | **taux_logement** | `SECTEUR=montchat python scripts/fix_taux_logement.py --apply` | champs *_logement ADDITIFS ; strict 932 vs brut 1217 (-23.4%) |
| 4 | usage_bdnb | `SECTEUR=montchat python scripts/propage_usage_bdnb.py --apply` | `usage_principal_bdnb` sur 1397/1399 |
| 5 | **ilotage KML** | `python scripts/_apply_ilot_kml_montchat.py --snap 15 --apply` | `_ilot` sur 1399 adr (voir tuning) |

Scripts `_montchat` crees (in-repo) :
- `scripts/fix_doublon_adresse_montchat.py` (copie + 2 chemins re-pointes)
- `scripts/_apply_ilot_kml_montchat.py` (re-ecrit : parse KML Montchat + fixes + sweep snap)

### Ilotage KML : fixes + tuning snap

Le KML `data/kml/Ilotage_Montchat.kml` = 133 placemarks / 134 polygones :
- **"162"** = 1 placemark a **2 anneaux** (un sliver triangulaire aire 6.18e-9 + le
  corps 6 pts). FIX = `unary_union` des anneaux du meme placemark -> un seul polygone
  ferme "162" (= "refermer l'ilot 162").
- **"118"** = **2 placemarks** distincts (npts 23 et 7). FIX = renommer le **plus petit
  en aire** (1.037e-06) en **"195"** -> noms uniques, "195" apparait.

Apres fixes : **133 noms uniques**, 0 doublon, 195 present, 162 present.

**Tuning snap (PIP=1214 constant, 86.8%)** :

| rayon | snap | orphelins X (PASS1) | snaps > 15 m (cross-rue ?) |
|---|---|---|---|
| 5 m | 96 | 87 | 0 |
| 10 m | 99 | 84 | 0 |
| **15 m (RETENU)** | **131** | **52** | **0** |
| 25 m | 163 | 20 | **32** |

**Rayon retenu = 15 m.** Justification cross-rue : c'est le PLUS GRAND rayon teste
ou AUCUN snap n'excede le seuil cross-rue (15 m). Inspection de la bande 10-15 m
(32 snaps) : l'ilot le plus proche domine systematiquement le 2e de >=5 m (souvent
pas de 2e ilot dans 25 m), donc snaps NON ambigus = adresses geocodees en retrait
~10-14 m du bord d'ilot (batiments en recul / avenues larges type Lacassagne, rues
Dauphine/Docteur Rebatel/Esquirol). 25 m recupererait ~19 orphelins de plus mais
introduit 32 snaps > 15 m (cross-rue probable, ex 7/14 RUE CARRY -> 102 a 24.6 m vers
un autre bloc) -> ecarte. `code_iris` reste intact.

Apres PASS 2 (arbitrage per-bgid, 40 splits resolus, 54 adr reassignees dont 13
null/X remontees) : **39 orphelins X final, 2 null**.

Reste du pipeline (comptage DVF dedup mutation, copros slim lots RNC prioritaires,
passe B/T/Q +16 cles, fusion bgid garde `l_libelle_adr` 146 groupes) : fait par
make_light_montchat, verifie present dans les compteurs de sortie.

---

## ETAPE D - Light Montchat FINAL + verifs

### Top-level keys = DL (identiques)
`['metadata','iris','coproprietes','adresses','dvf_orphans_excluded']`.
`dvf_orphans_excluded` n'est PAS produit par make_light : c'est un artefact terrain
DL (6 exclusions DVF curees a la main). Montchat vierge -> ajoute **`[]`** (liste
vide = aucune exclusion, structurellement identique, semantiquement correct ;
le front ne lit pas ce champ - verifie grep index.html = 0 match).

### 133 ilots peuples
- **129 / 133 ilots peuples** ; 4 vides (`177, 225, 230, 232`).
- adresses/ilot : min **1** / mediane **8** / max **57** (ilot 203).
- **"195" peuple : 5 adresses** ; **"162" peuple : 12 adresses** (ferme, OK).
- orphelins au snap retenu (15 m) : **39 X** + **2 null** (3.0 % des 1399).

### nb_ventes_logement / ventes_par_an_logement
Presents sur **1399/1399** adresses. Total brut **1217** vs strict logement **932**
(76.6 %, -23.4 %) -- ordre de grandeur coherent avec DL (-23 a -32 %).

### Copros / ventes / parc
- **633 copros** (633 avec immatriculation).
- parc dedup bg:bgid (replique 2-passes renderSecteur) = **15 769 lgts** (> 0, coherent).
- header montchat (brut) : 1185 adresses . 572 RNC . 541 BDNB . 15 769 lgts . 243,4 ventes/an.

### test_render_secteur.js
- **DL : exit 0** (inchange, parc secL=22381 == replique).
- **`SECTEUR=montchat` : exit 0** (parc secL=15769 == replique 2-passes ; strict<=brut ;
  recherche ; seuils sctClassAnnuel ; hr-actif 144==predicat).
- **Aucune edition du test n'a ete necessaire** : les assertions DL-specifiques sont
  DEJA gatees `if (DAUPH)` (B3 Montbrillant, strict "Actif", fixture marche libre).
  L'assertion "au moins 1 ligne injectee" (markers immat_fix) passe car Montchat a
  103 lignes `_bdnb_match=immat_fix` (issues de fix_rnc_bdnb_attribution). L'assertion
  hr-actif passe (144 adr hors-RNC actives). DL et MP non casses.
- `.bak` Montchat = etat pre-attribution (1296 adr, cree par fix_rnc_bdnb_attribution
  --apply) -> sert de baseline "pre-fix" (parc monotone 10632 -> 15769).

---

## Fichiers produits (AUCUN commite)

Hors-depot (`C:\Users\Station 5\`) :
- `make_light_montchat.py`

In-repo (`DPE-PROSPECTOR\`, NON commites) :
- `data/secteur_montchat_light.json` (light final, 1399 adr)
- `data/bdnb_montchat.json` (copie root -> data/, requis par fix scripts aval)
- `scripts/fix_doublon_adresse_montchat.py`
- `scripts/_apply_ilot_kml_montchat.py`
- backups : `secteur_montchat_light.json.bak` (pre-attribution),
  `.pretauxlog.bak`, `.preusage.bak`, `.preilot.bak`
- `data/diag_phase2_montchat.md` (ce rapport)

## Problemes / points a signaler

1. **2 passes hors-RNC SKIPPEES** (horsrnc / invisible_insecteur) : generiques en
   logique mais dependantes de sidecars BDNB live propres au secteur. A faire en
   Phase 5 (lancer leurs producteurs `verif_horsrnc_bdnb.py` / `verif_rnc_bdnb_live`
   en mode SECTEUR=montchat avant de les rejouer). Impact Phase 2 : nul (structurel OK).
2. **4 ilots vides** (177/225/230/232) + **39 orphelins X** + 2 null : normal pour un
   secteur vierge (pas encore de correction terrain ni de re-geocodage BAN cible).
   A revisiter en Phase 5 (la passe ilot peut etre re-jouee a un snap superieur APRES
   qualification, ou les orphelins re-geocodes).
3. **bdnb_montchat.json duplique** (root + data/) : aligne sur la convention DL/MP
   (root pour make_light, data/ pour les fix scripts). A garder synchro si re-extraction.
4. Buffer perimetre = fallback degres (pyproj absent, cf Phase 1) : sans impact ici
   (l'ilotage refait le PIP fin au niveau ilot).
