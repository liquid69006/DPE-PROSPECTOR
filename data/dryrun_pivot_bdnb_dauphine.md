# DRY-RUN — RE-POINT pivot BDNB (parc-neutre) — dauphine_lacassagne

Mode : **APPLY** · re-points = **11** (12 DL + 1 MP total ; ce rapport = secteur courant)

Parc (modele renderSecteur §6) : **22267 -> 22267 (delta +0)** · parc-neutre = OUI.

Ventes relocalisees au rendu (champs INCHANGES) : 56 v_log / 63 v_tot (orphelins). Plus la chaine de fusion deja absorbee par chaque orph qui suit.

| # | orph (cle) | v_log | -> ancre copro | immat | lots | chaine de fusion absorbee (sources de l'orph -> ancre) |
|--:|---|--:|---|---|--:|---|
| 1 | `9\|RUE\|PROFESSEUR PAUL SISLEY` | 16 | `7B\|RUE\|PROFESSEUR PAUL SISLEY` | AA0012898 | 225 | `11\|RUE\|PROFESSEUR PAUL SISLEY`, `7\|RUE\|PROFESSEUR PAUL SISLEY` |
| 2 | `12\|RUE\|LOUIS JASSERON` | 6 | `13\|RUE\|LOUIS JASSERON` | AC6278774 | 17 | `10\|RUE\|LOUIS JASSERON`, `14\|RUE\|LOUIS JASSERON` |
| 3 | `14\|RUE\|ST MAXIMIN` | 6 | `1\|RUE\|ROSSAN` | AB2460335 | 53 | `12\|RUE\|ST MAXIMIN` |
| 4 | `38\|RUE\|BARABAN` | 5 | `37\|RUE\|BARABAN` | AC9726381 | 29 | `36\|RUE\|BARABAN` |
| 5 | `260\|RUE\|PAUL BERT` | 5 | `264B\|RUE\|PAUL BERT` | AE1699040 | 8 | `262\|RUE\|PAUL BERT` |
| 6 | `12\|RUE\|CARRY` | 4 | `6\|RUE\|CARRY` | AC1825504 | 12 | `14\|RUE\|CARRY` |
| 7 | `48\|RUE\|ST MAXIMIN` | 3 | `51\|RUE\|ST MAXIMIN` | AB2784080 | 50 | `50\|RUE\|ST MAXIMIN` |
| 8 | `18\|RUE\|ETIENNE RICHERAND` | 3 | `19\|RUE\|ETIENNE RICHERAND` | AG2447720 | 8 | `20\|RUE\|ETIENNE RICHERAND` |
| 9 | `10\|RUE\|DAUPHINE` | 3 | `1\|RUE\|ST MAXIMIN` | AF0858860 | 14 | `8\|RUE\|DAUPHINE` |
| 10 | `14\|RUE\|ST SIDOINE` | 3 | `12\|RUE\|ST SIDOINE` | AB2206571 | 165 | `16\|RUE\|ST SIDOINE`, `18\|RUE\|ST SIDOINE` |
| 11 | `46\|RUE\|ST MAXIMIN` | 2 | `43\|RUE\|ST MAXIMIN` | AB1744747 | 22 | `44\|RUE\|ST MAXIMIN` |

---
*`scripts/fix_pivot_bdnb_lot.py` - dry-run par defaut, n'ecrit que ce rapport.*