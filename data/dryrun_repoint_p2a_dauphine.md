# DRY-RUN — RE-POINT P2a (copro RNC enterrée) — dauphine_lacassagne

Mode : **APPLY** · re-points = **3**

Parc (modèle renderSecteur §6) : **22268 → 22267 (delta -1)**. Switch BDNB(estimation)→RNC(lots autoritaires) sur chaque bgid : delta = lots_RNC − nb_log_bdnb_phantom. Négatif = correction d'un sur-comptage BDNB (PIPELINE §6 stipule explicitement « lots RNC prioritaire »). Aucune vente perdue (relocalisation).

| # | phantom (DVF) | v_log_phan | → ancre copro | immat | lots_RNC | nb_log_bdnb (phan) | Δ_parc bgid | mécanisme |
|--:|---|--:|---|---|--:|--:|--:|---|
| 1 | `53\|RUE\|ETIENNE RICHERAND` | 10 | `51\|RUE\|ETIENNE RICHERAND` | AC3598851 | 64 | 64 | +0 (64 BDNB → 64 RNC) | RE-POINT |
| 2 | `56\|AVENUE\|LACASSAGNE` | 4 | `54\|AVENUE\|LACASSAGNE` | AA4814810 | 50 | 50 | +0 (50 BDNB → 50 RNC) | RE-POINT |
| 3 | `316\|RUE\|PAUL BERT` | 3 | `318\|RUE\|PAUL BERT` | AC6168629 | 6 | 7 | -1 (7 BDNB → 6 RNC) | RE-POINT |

**Ventes relocalisées au rendu** (champs `ventes_*` **INCHANGÉS**) — chaque phantom devient secondaire de l'ancre, ses ventes apparaissent sous la copro RNC :
| phantom | v_log | v_tot | → copro | nom | syndic |
|---|--:|--:|---|---|---|
| `53\|RUE\|ETIENNE RICHERAND` | 10 | 15 | `51\|RUE\|ETIENNE RICHERAND` | LE BEAUBOURG | non connu |
| `56\|AVENUE\|LACASSAGNE` | 4 | 7 | `54\|AVENUE\|LACASSAGNE` | LES PINS | FONCIA LYON |
| `316\|RUE\|PAUL BERT` | 3 | 3 | `318\|RUE\|PAUL BERT` | RESIDENCE 318 RUE PAUL BERT | CABINET GINET SA |

---
*`scripts/fix_repoint_p2a.py` — dry-run par défaut, n'écrit que ce rapport.*