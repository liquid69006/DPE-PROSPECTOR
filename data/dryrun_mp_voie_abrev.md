# DRY-RUN — MP abréviation de voie (ALIAS_RNC miroir bgid)

Mode : **APPLY** · rattachements = **9** (5 cibles utilisateur + 4 dépendances chaîne)

Parc (modèle renderSecteur §6) : **29004 → 28973 (delta -31)**. Un delta ≤ 0 = retrait de doublons BDNB (la copro RNC reste comptée via ses lots à l'ancre), **jamais une perte de parc réel**.

Ventes relocalisées au rendu (champs ventes INCHANGÉS) : cibles 17 v_log / 25 v_tot ; dépendances 8 v_log / 9 v_tot.

| # | rôle | cle (abrégée) | v_log | v_tot | ventes/an | → ancre copro | immat | lots | syndic | mode |
|--:|:--:|---|--:|--:|---|---|---|--:|---|---|
| 1 | T | `3\|RUE\|CAPT SCOTT` | 8 | 11 | 2022:4 2023:4 2024:2 2025:1 | `3\|RUE\|CAPITAINE SCOTT` | AA8895435 | 30 | CABINET MICHAU | miroir bgid (dédup) |
| 2 | T | `4\|RUE\|GAL DE CASTELNAU` | 4 | 4 | 2021:2 2025:2 | `4\|RUE\|GENERAL DE CASTELNAU` | AI7024987 | 28 | JEAN CHARPENTIER-SOPAGI  | miroir bgid (dédup) |
| 3 | T | `11\|RUE\|GAL DE LARMINAT` | 3 | 4 | 2021:1 2022:2 2023:1 | `11\|RUE\|GENERAL DE LARMINAT` | AC8648685 | 26 | CABINET LOISELET PERE FI | miroir bgid (dédup) |
| 4 | T | `7\|RUE\|GAL DE CASTELNAU` | 1 | 1 | 2024:1 | `7\|RUE\|GENERAL DE CASTELNAU` | AA4713186 | 18 | GRIFFATON & CO | miroir bgid (dédup) |
| 5 | T | `8\|RUE\|GAL DE LARMINAT` | 1 | 5 | 2023:1 2024:3 2025:1 | `8\|RUE\|GENERAL DE LARMINAT` | AA9446949 | 41 | GERASCO | miroir bgid (dédup) |
| 6 | D | `1\|RUE\|CAPT SCOTT` | 8 | 9 | 2021:1 2022:1 2023:1 2024:5 2025:1 | `1\|RUE\|CAPITAINE SCOTT` | AF6894638 | 27 | CABINET IFNOR | même bgid (parc-neutre) |
| 7 | D | `12\|RUE\|ALASSEUR` | 0 | 0 | — | `8\|RUE\|GENERAL DE LARMINAT` | AA9446949 | 41 | GERASCO | miroir bgid (dédup) |
| 8 | D | `5\|RUE\|GAL DE CASTELNAU` | 0 | 0 | — | `5\|RUE\|GENERAL DE CASTELNAU` | AC0121202 | 20 | CABINET PIERRE BONNEFOI  | même bgid (parc-neutre) |
| 9 | D | `6\|RUE\|GAL DE CASTELNAU` | 0 | 0 | — | `4\|RUE\|GENERAL DE CASTELNAU` | AI7024987 | 28 | JEAN CHARPENTIER-SOPAGI  | miroir bgid (dédup) |

---
*scripts/fix_mp_voie_abrev.py — dry-run par défaut, n'écrit que ce rapport.*