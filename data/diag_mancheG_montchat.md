# Manche G — Resorption des orphelins d'ilot MONTCHAT (re-geocodage BAN)

> **Phase 5, Manche G.** Objectif : resorber les orphelins d'ilot
> (`_ilot in {'X', None}`) du light `data/secteur_montchat_light.json`
> (etat POST-Manche-A) par re-geocodage BAN forward + re-attribution ilot
> (`_apply_ilot_kml_montchat.py --apply --snap 15`).
>
> Scripts : `scripts/_regeocode_orphans_montchat.py` (cree),
> `scripts/_apply_ilot_kml_montchat.py` (re-lance). Backups :
> `.premancheG.bak` (etat POST-A avant re-geocodage), `.preilot.bak` (avant re-ilotage).
> Side-file : `data/_regeocode_orphans_montchat.json` (avant/apres par orphelin).
> **Aucun commit, aucun `git add`.** DL/MP et `index.html` non touches.

---

## ETAPE 0 — Liste reelle des orphelins (re-derivee POST-Manche-A)

Definition retenue (alignee `test_render_secteur.js` l.147/374) :
**orphelin = adresse RENDUE** (`NOT (_fusion_auto && (_fusion_cible || _fusion_auto_target))`)
**ET** `_ilot in {'X', None}`.

| | n |
|---|---:|
| Orphelins **rendus** POST-A | **32** |
| dont `_ilot == 'X'` (avec coords) | 30 |
| dont `_ilot == None` (sans coords) | 2 |

> **Ecart vs Manche 0 (41 = 39 X + 2 null)** : le 41 fige comptait TOUTES les
> adresses (y compris les **9 secondaires de fusion**, non rendues, qui n'affichent
> rien a l'ecran). Le perimetre reel d'action = **32 rendus** (30 X + 2 null).
> CELLARD (`|RUE|CELLARD`) est toujours dans `adresses[]` mais reste en DENY
> (Manche A) : `_ilot=None`, sans coords, **non geocodee** (cle invalide).
> TRARIEUX a bien ete renommee `74|RUE|TRARIEUX` en Manche A → ilotee (219), **plus orpheline**.

Liste des 32 (cle, coords, bgid, `_ilot`) — voir `_regeocode_orphans_montchat.json`.
30 X ont des coords ; 2 null sans coords (`2|RUE|ANDRE`, `|RUE|CELLARD`).

---

## ETAPE 1 — Re-geocodage BAN forward (housenumber)

Requete : cle `NUM|TYPE|VOIE` → « NUM VOIE <CP> Lyon » avec CP derive de
`code_iris[:5]` (69383→69003 Lyon 3e, 69388→69008 Lyon 8e ; null-coords testees
69003 puis 69008). API `api-adresse.data.gouv.fr/search/?type=housenumber&limit=1`.
**Ecriture coords SEULEMENT si fiable** : `score >= 0.5` **ET** voie BAN == voie cle
(normalisation ST→SAINT, DR→DOCTEUR, GAL→GENERAL, retrait type/articles).

| Decision | n | Detail |
|---|---:|---|
| **FIABLE** (match BAN housenumber, voie OK) | **29** | coords ecrites |
| **PAS_MATCH** | 2 | `4B\|PLACE\|CHATEAU` (pas de 4B → BAN snap « Rue Chaponnay » score 0.42) · `2\|RUE\|ANDRE` (null, BAN « Rue General Andre » voie ≠ score 0.54) |
| **SKIP_DENY** | 1 | `\|RUE\|CELLARD` (cle invalide DENY Manche A — non geocodee) |

### Constat majeur : coords deja BAN-exactes (re-geocodage ~no-op)

Sur les **29 FIABLE**, **28 ont des coords STRICTEMENT INCHANGEES** (BAN retourne
exactement la coord deja presente dans le light). **1 seul** bouge, de facon
microscopique :

| Orphelin | coords avant | coords apres | delta |
|---|---|---|---|
| `22\|RUE\|DAVID` | 4.869904, 45.753311 | 4.869904, 45.753312 | ~0.1 m (lat) |

> **Lecture** : `make_light_montchat` a deja geocode ces adresses au **point BAN
> housenumber** (la coord la plus precise possible). Le re-geocodage BAN ne peut
> donc PAS les rapprocher d'un ilot — elles sont **deja a leur meilleure position
> et restent > 15 m de tout polygone**. Le levier « re-geocodage » est **epuise**
> pour ce secteur ; la seule voie de resorption restante serait d'**elargir le
> snap** (cf. sweep : 52 X a 15 m → 20 X a 25 m) — hors scope de cette manche
> (snap fixe a 15 m).

Scores BAN typiques 0.61–0.75 (housenumber exact, voie concordante).

---

## ETAPE 2 — Re-attribution ilot (snap 15 m, point-in-polygon + arbitrage bgid)

`_apply_ilot_kml_montchat.py --apply --snap 15` relance, **idempotent**
(recalcule `_ilot` from scratch sur les coords courantes). Ordre respecte :
(1) coords mises a jour (ETAPE 1) → (2) ilotage sur ces coords.

```
[KML] ilots (apres fixes 118->195 + 162 unifie) : 133 noms uniques
[PASS 1] direct PIP    : 1216 (86.8%)
[PASS 1] snap <=15m    :  131 (9.4%)
[PASS 1] X (>15m)      :   52 (3.7%)   <- toutes adresses (incl. secondaires fusion)
[PASS 1] null          :    2 (0.1%)
[PASS 2] bgids splits  : 40  | resolus 40 | reassignees 54 (dont 13 null/X -> ilot)
RESULTATS : 1360/1401 ilotees (97.1%) | X=39 | null=2 | ilots peuples 129/133
```

---

## ETAPE 3 — Resolus / restants

| | n |
|---|---:|
| Orphelins rendus POST-A | 32 |
| **Resolus** (orphelin → ilot affecte) | **0** |
| **Restants** | **32** (30 X + 2 null) |

La liste des **32 rendus orphelins est IDENTIQUE avant/apres** : aucun n'a ete
resorbe. Coherent avec le constat ETAPE 1 (coords deja BAN-exactes, toutes
> 15 m). Distance de snap utilisee : **15 m** (aucun snap n'a abouti sur ces 32).

### Raison par restant (distance au plus proche ilot)

| Orphelin | dist ilot | in bbox | raison |
|---|---:|:---:|---|
| `4B\|PLACE\|CHATEAU` | 15.2 m | oui | bord (proche ilot, > snap 15 ; pas de match BAN) |
| `154\|COURS\|ALBERT THOMAS` | 17.6 m | oui | bord |
| `135\|RUE\|DAUPHINE` | 17.7 m | NON | bord (frontiere DL ↔ Montchat) |
| `36\|RUE\|VIALA` | 17.9 m | oui | bord |
| `152\|COURS\|ALBERT THOMAS` | 18.4 m | oui | bord |
| `54\|AVENUE\|LACASSAGNE` | 18.9 m | oui | bord |
| `137\|RUE\|DAUPHINE` | 19.4 m | NON | bord (frontiere DL) |
| `150\|COURS\|ALBERT THOMAS` | 19.7 m | oui | bord |
| `136\|COURS\|ALBERT THOMAS` | 20.0 m | oui | bord |
| `132\|COURS\|ALBERT THOMAS` | 20.1 m | oui | bord |
| `126\|COURS\|ALBERT THOMAS` | 20.8 m | oui | bord |
| `104\|COURS\|ALBERT THOMAS` | 21.1 m | oui | bord |
| `51B\|AVENUE\|LACASSAGNE` | 22.5 m | NON | bord (frontiere DL) |
| `58\|AVENUE\|LACASSAGNE` | 22.5 m | oui | bord |
| `62\|RUE\|ST MAXIMIN` | 24.4 m | oui | bord |
| `1\|PLACE\|CHATEAU` | 25.9 m | oui | hors tout ilot (dans bbox) |
| `60\|AVENUE\|ROCKEFELLER` | 28.6 m | **NON** | **HORS bbox KML** (sud-est, Rockefeller) |
| `43\|RUE\|GUILLOUD` | 28.7 m | oui | hors tout ilot (dans bbox) |
| `2\|RUE\|BARA` | 29.2 m | oui | hors tout ilot (dans bbox) |
| `84\|RUE\|DAUPHINE` | 29.3 m | **NON** | **HORS bbox KML** (frontiere DL) |
| `11\|RUE\|BARA` | 30.9 m | oui | hors tout ilot (dans bbox) |
| `25\|RUE\|MONTBRILLANT` | 36.4 m | oui | hors tout ilot (dans bbox) |
| `141\|RUE\|DAUPHINE` | 39.7 m | **NON** | **HORS bbox KML** (frontiere DL) |
| `3\|PLACE\|CHATEAU` | 42.4 m | oui | hors tout ilot (dans bbox) |
| `69\|RUE\|FEUILLAT` | 43.2 m | oui | hors tout ilot (dans bbox) |
| `22\|RUE\|DAVID` | 44.4 m | oui | hors tout ilot (dans bbox) |
| `5\|RUE\|CARRY` | 45.5 m | oui | hors tout ilot (dans bbox) |
| `143\|RUE\|DAUPHINE` | 46.1 m | **NON** | **HORS bbox KML** (frontiere DL) |
| `12\|RUE\|BARA` | 47.0 m | oui | hors tout ilot (dans bbox) |
| `12\|RUE\|CARRY` | 47.2 m | oui | hors tout ilot (dans bbox) |
| `2\|RUE\|ANDRE` | — | — | sans coords (null) ; pas de match BAN fiable (voie « General Andre ») |
| `\|RUE\|CELLARD` | — | — | sans coords (null) ; cle invalide DENY (non geocodee) |

Synthese raisons : **15 bord** (proche ilot, 15–25 m > snap 15) · **13 hors tout
ilot** (dans bbox mais > 25 m, sur axes/arriere-cour) · **2 sans coords** (null).

---

## ETAPE 4 — Verifications

### Parc INCHANGE = 15 809 (OUI)
`test_render_secteur.js` (renderSecteur reel, regle 2-passes) :

| | secL | ecart |
|---|---:|---:|
| AVANT (`.premancheG.bak`, POST-A) | 15 809 | — |
| APRES (re-geocode + re-ilot) | **15 809** | **0** |

Le re-geocodage n'a touche QUE `longitude`/`latitude`/`_coord_source` (+ `_ilot`
via le script ilot) ; **aucun** `nb_log_bdnb`/`nb_lots_habitation`/copro/bgid
modifie. **Parc strictement neutre — pas d'alerte.**

### Distribution ilot (apres)
- Ilotees : **1360 / 1401** (97.1 %)
- Ilots peuples : **129 / 133** ; vides : 4 (`177`, `225`, `230`, `232`)
- `'195'` (fix 118→195) : 5 adresses · `'162'` (anneaux unis) : 12 adresses
- Orphelins (toutes adresses) : 39 X + 2 null = 41 ; **rendus** : 30 X + 2 null = 32
- Top ilots : 203 (57), 212 (35), 112 (34), 110 (33), 209/208 (29)

### FLAGS hors-perimetre (possible erreur extraction RNC/MAJIC — a signaler, PAS a corriger ici)
5 orphelins re-geocodes (coords BAN) tombent **HORS bbox KML** (lon 4.8698→4.8983 /
lat 45.7404→45.7549) :
- `141\|RUE\|DAUPHINE`, `143\|RUE\|DAUPHINE`, `135\|RUE\|DAUPHINE`,
  `137\|RUE\|DAUPHINE` — **frontiere DL ↔ Montchat** (Rue Dauphine est a cheval,
  cf. Manche A §3 recouvrement : 22 cles DAUPHINE communes). Ces n° hauts (135–143)
  sont cote DL ; leur presence dans le light Montchat est un **chevauchement de
  perimetre attendu**, pas une erreur d'extraction.
- `60\|AVENUE\|ROCKEFELLER` — sud-est, Avenue Rockefeller borde le secteur ;
  BAN la place a 29 m du plus proche ilot, hors bbox. A surveiller (limite sud).

> Aucune adresse n'est placee « loin » (toutes < 50 m d'un ilot) → **pas
> d'erreur d'extraction RNC/MAJIC franche detectee**. Les 5 hors-bbox sont des
> bords/frontieres geographiques, coherents avec le chevauchement DL connu.
> `84\|RUE\|DAUPHINE` est juste sous le seuil bbox (lat 45.7526 < ... non : lon
> 4.8695 < 4.8698) — egalement frontiere DL.

### test_render_secteur.js — exit 0 sur les DEUX secteurs
- **Montchat** (`SECTEUR=montchat`) : `RESULTAT : OK`, exit **0**, secL=15 809.
- **DL** (defaut `dauphine_lacassagne`) : `RESULTAT : OK`, exit **0**, secL=22 381
  (non regresse, fichier non touche).

---

## Conclusion

Re-geocodage BAN **applique** (29 coords FIABLE re-ecrites, dont 28 identiques +
1 a +0.1 m), re-ilotage snap 15 m **relance** (idempotent). **0 orphelin rendu
resorbe** : les coords etaient deja au point BAN housenumber exact, toutes a
> 15 m d'un ilot. Le levier re-geocodage est **sature** pour Montchat — la
resorption residuelle (32 restants : 15 bord 15–25 m, 13 hors-ilot dans bbox,
2 null) demanderait soit un **snap elargi** (→ 25 m resorberait l'essentiel des
« bord »), soit un **traitement manuel** (cas null + 4B CHATEAU sans housenumber
BAN), **hors scope snap-15 de cette manche**.

**Parc strictement inchange (15 809), test_render exit 0 DL + Montchat.**
5 flags hors-bbox = frontiere DL / bord Rockefeller (chevauchement attendu, pas
d'erreur d'extraction). **Aucun commit, aucun `git add`, aucun push.**

*DL/MP et `index.html` intacts.*
