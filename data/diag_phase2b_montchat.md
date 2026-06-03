# Diag PHASE 2b - Finitions ilotage Montchat

> EXECUTION (production de fichiers). AUCUN commit / git add / push.
> Date : 2026-06-02. NI DL/MP NI index.html / test_render_secteur.js touches.
> PYTHONUTF8=1, prints ASCII-safe. STOP a la fin (gate G2-final).

---

## Constat prealable : le script vivait dans scripts/, pas a la racine

Le brief annoncait `_apply_ilot_kml_montchat.py` hors-depot dans `C:\Users\Station 5\`.
En realite il etait deja in-repo : `scripts/_apply_ilot_kml_montchat.py`. C'est lui
qui a ete (re)joue. La racine n'en contient pas de copie.

---

## VOLET 1 - Arbitrage par-bgid (deja porte, identique DL)

### Logique DL (reference, `scripts/_apply_ilot_kml_dl.py`)

PASS 2 (lignes **172-267**), resume :
- regroupe les adresses par `batiment_groupe_id` (lignes 177-180) ;
- pour chaque bgid, compte les **votes** = ilots reels poses en PASS 1 (PIP ou snap),
  en excluant `X`/`None`/cle malformee (lignes 195-202) ;
- si un ilot domine -> `chosen` = lui (lignes 211-213) ; en cas d'**egalite**, tie-break
  par **centroide du bati** : moyenne lon/lat des adresses du bgid, PIP de ce centroide ;
  si le centroide tombe dans un des ilots ex-aequo -> on le prend, sinon fallback
  deterministe `sorted(tied, key=(len, s))[0]` (lignes 215-231) ;
- applique `chosen` a TOUTES les adresses du bgid, **y compris les orphelines X/None**
  (lignes 236-247) -> c'est ce qui "remonte" un orphelin quand un *frere* de meme
  bgid a ete place. Principe : meme bgid = meme bati physique, pas de risque cross-rue.

### Etat dans `_apply_ilot_kml_montchat.py`

**Logique DEJA presente et identique** (PASS 2, lignes **224-276**) : meme regroupement
par bgid, memes votes hors X/None, meme tie-break centroide + meme fallback
`sorted(tied, key=(len, s))[0]`. **Ordre respecte** : PIP -> snap 15 m -> arbitrage
bgid -> reste 'X'/null. **Aucune modification du script n'a ete necessaire pour le
Volet 1** ; le snap 15 m est conserve.

### Mesure AVANT / APRES arbitrage bgid (snap 15 m)

| etape | X | null | orphelins total |
|---|---|---|---|
| PASS 1 (PIP + snap 15) | 52 | 2 | **54** |
| PASS 2 (apres arbitrage bgid) | 39 | 2 | **41** |

**13 orphelins resolus** par l'arbitrage bgid (les "13 null/X -> ilot").

### Orphelins RESTANTS : 41 (39 X + 2 null)

- **2 null** = sans coordonnees, donc jamais PIP-ables ni arbitrables :
  `2|RUE|ANDRE`, `|RUE|CELLARD`.
- **39 X** = **TOUS** classes "**bgid entierement orphelin**" : chaque adresse du bgid
  est elle-meme orpheline (>15 m de tout ilot), donc 0 vote a heriter. L'arbitrage
  bgid ne peut rien faire (il ne cree pas d'ilot, il propage un vote existant).
  Aucun cas "pas de bgid" et aucun cas "bgid a un vote non applique" (anomalie) :
  l'arbitrage est complet.

Concentration des 39 X (geocodage en retrait > 15 m du bord d'ilot, avenues larges /
bordures de perimetre) : COURS ALBERT THOMAS (10), RUE DAUPHINE (8), AVENUE
LACASSAGNE (5), RUE CARRY (4), RUE BARA (5), PLACE CHATEAU (3), RUE DAVID (2),
divers (2). snap_nearest typique 16-47 m. Liste complete : voir sortie
`scripts/_diag_phase2b_montchat.py`. Ce sont des candidats Phase 5 (re-geocodage
BAN cible ou snap superieur post-qualification) - pas un defaut structurel.

---

## VOLET 2 - Ilot "162" (2 anneaux du placemark)

Re-parse des 2 anneaux du placemark unique "162" :

| anneau | aire | centroide (lon/lat) | span | adresses light dedans |
|---|---|---|---|---|
| sliver | 6.18e-09 | 4.887034 / 45.749532 | **17.3 m x 47.5 m** (triangle degenere) | **0** |
| corps | 4.85e-07 | 4.887272 / 45.750126 | 96.8 m x 80.8 m | **11** |

- **distance entre centroides = 68.5 m** (bande ambigue 50-100 m).
- `intersects = True`, `touches = True`, `overlaps = False`, **aire d'intersection = 0**
  -> les 2 anneaux se **touchent** (partagent un bord, a la latitude 45.749766) sans
  se chevaucher. Ce n'est PAS le cas "118" (2 placemarks distincts, 2 blocs eloignes
  portant chacun des adresses).
- Le sliver est un **triangle degenere contigu sans aucune adresse** (0 light, 0 RNC,
  0 DVF), pendant que le corps porte 11 adresses (12 avec 1 snap a <=15 m).

### VERDICT : UNIFICATION CORRECTE -> on GARDE "162" unifie. PAS de renommage "196".

Justification : les 2 anneaux sont **contigus (touch)**, pas 2 blocs distincts. La
distance de 68.5 m entre centroides est un artefact de la geometrie etiree/degeneree
du sliver, pas le signe de 2 blocs separes (cf. "118" qui etait > 100 m ET portait des
adresses dans chaque bloc). Renommer le sliver en "196" creerait un ilot **fantome a
0 adresse**. L'`unary_union` produit par le script (1 polygone "162" ferme, 12 adr) est
le bon comportement. **Aucune action "196", aucun changement de script.** Nombre
d'ilots distincts reste **133** (132 KML + le rename 118->195 deja fait en Phase 2).

---

## VOLET 3 - Les 4 ilots vides (177, 225, 230, 232)

Croisement : copros RNC (`secteur_montchat.json`, coords _longitude/_latitude),
adresses FULL, adresses LIGHT et mutations DVF tombant DANS le polygone de chaque
ilot vide.

| ilot | centroide (lon/lat) | span | copros RNC | adr FULL | adr LIGHT | DVF | STATUT |
|---|---|---|---|---|---|---|---|
| **177** | 4.896333 / 45.750750 | 111x96 m | 0 | 0 | 0 | 0 | **VIDE LEGITIME** (non-residentiel : bordure E perimetre, cours A. Thomas) |
| **230** | 4.889659 / 45.742473 | 100x134 m | 0 | 0 | 0 | 0 | **VIDE LEGITIME** (non-residentiel) |
| **232** | 4.890740 / 45.742485 | 90x122 m | 0 | 0 | 0 | 0 | **VIDE LEGITIME** (non-residentiel) |
| **225** | 4.889057 / 45.744819 | 212x126 m | 0 | 1 | 1 | 0 | **FAUX TROU** (1 bati bgid coherence-merge vers 192, cf. ci-dessous) |

### 177 / 230 / 232 : vides legitimes confirmes

Aucune copro RNC, aucune adresse (FULL ni LIGHT), aucune mutation DVF a l'interieur.
Polygones de bordure / equipement (non-residentiel). Rien a investiguer.

### 225 : faux trou (artefact d'arbitrage bgid, comportement DL fidele)

Le polygone 225 contient geometriquement **1 adresse** : `162|AVENUE|LACASSAGNE`
(4.889969 / 45.745019), PIP **direct dans 225** (covers=True, dist 0 ; a 13.6 m de 192).
Or dans le light elle porte `_ilot = "192"`. Cause :

- elle partage le bgid `bdnb-bg-FCDU-LVKT-QJW2` avec `223|AVENUE|LACASSAGNE`
  (4.889756 / 45.745242), qui PIP **dans 192** (dist 0 ; a 13.0 m de 225).
- le bati straddle la frontiere 192/225 (les 2 ilots ne se chevauchent pas). Votes du
  bgid = {192:1 (223), 225:1 (162)} -> **egalite** -> tie-break centroide. Le centroide
  des 2 points (4.889863 / 45.745131) tombe **dans aucun des 2** (dans la rue) ->
  fallback deterministe `sorted({"192","225"})[0]` = **"192"**. Les 2 adresses du bgid
  partent donc ensemble en 192.

C'est **exactement** le comportement DL (meme tie-break, meme fallback). 162 et 223
LACASSAGNE sont le **meme bati physique** (meme bgid) : les garder groupes dans 192
est l'effet recherche de la coherence-bati, pas un bug. **225 n'est donc PAS un trou de
geocodage/perimetre** (0 donnee non-rattachee independante) : c'est un vide induit par
la coherence bgid. Statut : **vide legitime par coherence-bati** (a documenter, rien a
corriger sauf decision terrain explicite de re-decoupage 192/225).

### Bilan Volet 3 : 3 vides legitimes (equipement) + 1 vide legitime par coherence-bgid. **0 vrai trou.**

---

## VERIFS FINALES

- **Backup pre-2b** : `secteur_montchat_light.json.preilot2b.bak` cree AVANT re-ecriture.
- **Idempotence prouvee** : re-application `--apply --snap 15` -> signature des champs
  parc (`nb_ventes_logement` / `ventes_par_an_logement` / `nb_ventes` /
  `batiment_groupe_id` par cle) **identique** avant/apres (md5 `6624aa76...`).
  Le script recalcule `_ilot` from scratch par PIP (n'accumule pas).
- **`.preilot.bak` restaure propre** : l'`--apply` ecrase `.preilot.bak` avec le light
  deja ilote ; la baseline pre-ilot propre (0 `_ilot`) a ete sauvegardee puis restauree
  apres apply -> `.preilot.bak` re-verifie a **0 `_ilot`** (baseline intacte).
- **Orphelins** : 54 (avant arbitrage) -> **41** (39 X + 2 null) apres arbitrage bgid.
- **Ilots** : **133** distincts (rename 118->195), **129 peuples**, 4 vides
  (177/225/230/232). adr/ilot min/med/max = 1 / 8 / 57.
- **162** : present, unifie, **12 adresses** (verdict : garde). **195** : present,
  **5 adresses**. (195 toujours present.)
- **Parc INCHANGE** : `test_render_secteur.js` SECTEUR=montchat -> secL = **15769** ==
  replique 2-passes (ecart 0) ; champs parc non touches par l'ilotage (confirme par
  signature md5 identique). Header montchat inchange vs Phase 2.
- **test_render_secteur.js** :
  - `SECTEUR=montchat` -> **exit 0** (parc 15769, hr-actif 144==predicat).
  - `SECTEUR=dauphine_lacassagne` -> **exit 0** (non regresse ; parc 22381 ; hr-actif
    36==predicat). NB : la variable d'env DL est `dauphine_lacassagne` (underscore),
    pas l'id agence `dauphine-lacassagne`.

---

## Fichiers (AUCUN commite)

In-repo (NON commites) :
- `data/secteur_montchat_light.json` (re-ilote, identique a Phase 2 : 1399 adr, 129
  ilots, 39 X, 2 null)
- `data/secteur_montchat_light.json.preilot2b.bak` (backup pre-2b)
- `data/secteur_montchat_light.json.preilot.bak` (baseline pre-ilot propre, restauree)
- `scripts/_diag_phase2b_montchat.py` (diag read-only : orphelins restants + ilots vides)
- `data/diag_phase2b_montchat.md` (ce rapport)

Script d'ilotage `scripts/_apply_ilot_kml_montchat.py` : **inchange** (logique bgid deja
presente et identique DL ; verdict 162 = garder ; aucun "196" a appliquer).

## Conclusion

Les 3 volets convergent vers "rien a corriger structurellement" : l'arbitrage bgid
etait deja porte (identique DL) et resout 13/54 orphelins ; les 41 restants sont des
bgids entierement orphelins (re-geocodage Phase 5) ou des adresses sans coords ;
l'unification "162" est correcte (anneaux contigus, sliver vide) ; les 4 ilots vides
sont tous legitimes (3 equipement + 1 coherence-bgid), **0 vrai trou**. Parc inchange,
test_render exit 0 DL + Montchat.
