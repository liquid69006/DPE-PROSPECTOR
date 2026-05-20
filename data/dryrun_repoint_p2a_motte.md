# DRY-RUN — RE-POINT P2a (copro RNC enterrée) — motte_picquet

Mode : **APPLY** · re-points = **1**

Parc (modèle renderSecteur §6) : **28973 → 28980 (delta +7)**. Switch BDNB(estimation)→RNC(lots autoritaires) sur chaque bgid : delta = lots_RNC − nb_log_bdnb_phantom. Négatif = correction d'un sur-comptage BDNB (PIPELINE §6 stipule explicitement « lots RNC prioritaire »). Aucune vente perdue (relocalisation).

| # | phantom (DVF) | v_log_phan | → ancre copro | immat | lots_RNC | nb_log_bdnb (phan) | Δ_parc bgid | mécanisme |
|--:|---|--:|---|---|--:|--:|--:|---|
| 1 | `9\|RUE\|GUESCLIN` | 8 | `3\|PASSAGE\|GUESCLIN` | AB1748391 | 104 | 97 | +7 (97 BDNB → 104 RNC) | RE-POINT |

**Ventes relocalisées au rendu** (champs `ventes_*` **INCHANGÉS**) — chaque phantom devient secondaire de l'ancre, ses ventes apparaissent sous la copro RNC :
| phantom | v_log | v_tot | → copro | nom | syndic |
|---|--:|--:|---|---|---|
| `9\|RUE\|GUESCLIN` | 8 | 13 | `3\|PASSAGE\|GUESCLIN` | Résidence Du Guesclin | URBANIA VAL D OUEST |

---
*`scripts/fix_repoint_p2a.py` — dry-run par défaut, n'écrit que ce rapport.*