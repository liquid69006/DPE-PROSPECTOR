# Audit - bug "wrong bgid voisin" (make_light num_voie/gps)

> Lecture seule. Cache `data/_pivot_bdnb_cache.json` peuple. Aucune modification des donnees light.

## Cause-racine
make_light fait la jointure BDNB en 3 paliers (PIPELINE Sec 4) : (1) `immat` via copro RNC, (2) `num_voie` BDNB (par voie/numero approxime), (3) `gps` (<50m). Les paliers 2 et 3 peuvent assigner a une adresse impaire (ex. 23 FREMICOURT) le bgid du voisin pair (ex. bgid de 22 FREMICOURT = autre copro distincte) parce que BDNB indexe le bati sous l'adresse paire principale. Le pipeline pivot forward cherche ensuite la copro via ce mauvais bgid -> rate. La passe reverse couvre la plupart de ces cas via copro -> bgid -> pivots BAN.

## Bilan par secteur

| secteur | candidates (hors-RNC + weak match) | correct | **wrong** | wrong+vlog>0 | actionable (vrai bgid avec copro RNC) |
|---|--:|--:|--:|--:|--:|
| dauphine_lacassagne | 641 | 348 | **293** | 12 | **0** |
| motte_picquet | 396 | 231 | **165** | 4 | **0** |

## Cas ACTIONNABLES (wrong bgid + vlog>0 + true bgid heberge copro RNC connue, non encore fuses)

### dauphine_lacassagne : aucun cas

### motte_picquet : aucun cas

## Cas wrong-bgid + vlog>0 SANS copro actionnable (vraie monopropriete / non immat)

### dauphine_lacassagne : 12 cas (residuels cat. B)

| cle hors-RNC | v_log | bgid light | TRUE bgid | match |
|---|--:|---|---|---|
| `6\|RUE\|ST EUSEBE` | 5 | `...LV-MDEK-PE5T` | (introuvable BAN) | num_voie |
| `9\|RUE\|ST EUSEBE` | 5 | `...8S-PG6T-JXF4` | (introuvable BAN) | num_voie |
| `71\|RUE\|PAUL BERT` | 4 | `...VN-TN1Z-KE2S` | (introuvable BAN) | gps |
| `125\|RUE\|DAUPHINE` | 3 | `...5T-JZFB-UVR7` | (introuvable BAN) | num_voie |
| `18\|RUE\|ST ANTOINE` | 3 | `...FK-6Z9V-TUP1` | `...MC-KXL7-E97N` | num_voie |
| `75\|RUE\|DAUPHINE` | 3 | `...EK-6E83-3BX4` | (introuvable BAN) | num_voie |
| `6\|RUE\|PROFESSEUR PAUL SISLEY` | 2 | `...81-DZPJ-QXMN` | `...HW-P9KF-JSGH` | num_voie |
| `21\|RUE\|GUILLOUD` | 1 | `...LG-5MRC-2XQ6` | `...19-EARQ-9D7B` | num_voie |
| `13\|RUE\|METALLURGIE` | 1 | `...4Y-G9R6-B2ZS` | (introuvable BAN) | num_voie |
| `6\|RUE\|PREVOYANTS DE L AVENIR` | 1 | `...FV-76BN-BDJJ` | (introuvable BAN) | num_voie |
| `225\|AVENUE\|FELIX FAURE` | 1 | `...BN-MPP6-46DX` | (introuvable BAN) | num_voie |
| `14\|RUE\|PREVOYANTS DE L AVENIR` | 1 | `...LN-1W4S-BPXX` | (introuvable BAN) | num_voie |

### motte_picquet : 4 cas (residuels cat. B)

| cle hors-RNC | v_log | bgid light | TRUE bgid | match |
|---|--:|---|---|---|
| `10\|RUE\|PERIGNON` | 5 | `...E2-LG3N-FXCZ` | (introuvable BAN) | num_voie |
| `51\|RUE\|FEDERATION` | 1 | `...BY-G4B7-X44K` | (introuvable BAN) | num_voie |
| `55\|RUE\|FEDERATION` | 1 | `...61-2FJK-3SDH` | (introuvable BAN) | num_voie |
| `71\|QUAI\|JACQUES CHIRAC` | 1 | `...BC-228Y-4AEN` | (introuvable BAN) | gps |

## ETAPE 3 - Recommandations

**(a) Correction amont make_light (regen requise, RISQUE)** : modifier le palier `num_voie`/`gps` pour valider que l'adresse figure dans `l_libelle_adr` du bgid BDNB candidat. Si non, tenter via `rel_batiment_groupe_adresse` (BAN cle_interop -> bgid authoritative). Cout : +N appels API par regen, mais regen INTERDITE en l'etat (PIPELINE Sec 3) -> il faudrait rejouer toute la chaine `fix_*` apres regen. **A eviter**.

**(b) Correction aval pipeline reverse (DEJA EN PLACE, extension possible)** : le `pipeline_bdnb_pivot_reverse.py` iter depuis chaque copro RNC -> bgid copro -> pivots BAN -> match hr-active. Couvre par construction le cas "wrong bgid + true bgid heberge copro" (le match utilise la canonique BAN, pas le bgid light). **Si des cas restent en wrong-bgid actionnables ICI, c'est que la reverse a rate par bgid-non-cache au moment du run -> re-executer `pipeline_bdnb_pivot_reverse.py`**, le cache est desormais etendu par cet audit (toutes les bgids hors-RNC weak indexees BDNB).

**(c) Correction des bgids errones eux-memes (CHIRURGICAL, RECOMMANDE pour les cas isoles)** : pour les wrong-bgid sans copro actionnable mais ou le TRUE bgid est connu, le bgid peut etre corrige par adoption MIRROR du true bgid via un fix dedie. **Risque : changer le bgid peut deplacer la contribution parc**. Mesurer parc_model avant. **A instruire individuellement** pour cas a haut impact.

**Conclusion** : (b) est la voie deja consacree. Cet audit vient enrichir le cache et identifier explicitement les actionnables restants -> les appliquer via le mecanisme miroir-bgid existant (cf. fix_pivot_bdnb_reverse_lot) si non couverts.

---
*`scripts/audit_bgid_neighbor.py` - lecture seule. Cache + rapport seuls ecrits.*