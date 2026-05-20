# DRY-RUN — RE-POINT pivot BDNB (parc-neutre) — motte_picquet

Mode : **APPLY** · re-points = **1** (12 DL + 1 MP total ; ce rapport = secteur courant)

Parc (modele renderSecteur §6) : **28980 -> 28980 (delta +0)** · parc-neutre = OUI.

Ventes relocalisees au rendu (champs INCHANGES) : 2 v_log / 2 v_tot (orphelins). Plus la chaine de fusion deja absorbee par chaque orph qui suit.

| # | orph (cle) | v_log | -> ancre copro | immat | lots | chaine de fusion absorbee (sources de l'orph -> ancre) |
|--:|---|--:|---|---|--:|---|
| 1 | `3\|PLACE\|CAMBRONNE` | 2 | `6\|PLACE\|CAMBRONNE` | AB5809108 | 19 | `5\|PLACE\|CAMBRONNE` |

---
*`scripts/fix_pivot_bdnb_lot.py` - dry-run par defaut, n'ecrit que ce rapport.*