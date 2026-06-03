# Vérification RNC → BDNB — API live vs snapshot (lecture seule)

API ouverte `api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc` (sans clé), table de relation `numero_immat` ↔ `batiment_groupe_id`. Compare l'ensemble live à `data/bdnb_dauphine_lacassagne.json`.

## Bilan

| Indicateur | Valeur |
|---|--:|
| Copros vérifiées | 633 |
| Copros snapshot ≠ live | 27 |
| **Copros où le snapshot a omis des bâtiments** | **27** |
| Bâtiments live absents du snapshot | 28 (~1269.83 lgts) |
| Bâtiments snapshot absents du live | 0 |

## Top 20 — omissions du snapshot par logements

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AA6767180 | SDC ALBERT THOMAS | 0 | 1 | 1 | 128.0 | bdnb-bg-1K5S-G75D-PMQN |
| 2 | AA0762245 | LE PERGOLESE II | 0 | 1 | 1 | 96.0 | bdnb-bg-6SBM-R9F7-GP62 |
| 3 | AC4464848 | LE PERGOLESE III | 0 | 1 | 1 | 96.0 | bdnb-bg-6SBM-R9F7-GP62 |
| 4 | AC4130548 | SDC COURS ALBERT THOMAS | 0 | 1 | 1 | 88.0 | bdnb-bg-MKGQ-UFU9-924X |
| 5 | AA2367605 | 80 bis rue Feuillat | 0 | 1 | 1 | 71.0 | bdnb-bg-T3QK-M61N-9RTG |
| 6 | AA3216041 | 123 bis cours Albert Thomas | 0 | 1 | 1 | 71.0 | bdnb-bg-T3QK-M61N-9RTG |
| 7 | AA4815643 | 41 RUE PROFESSEUR ROCHAIX | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 8 | AA6892657 | 6 BALTHAZAR | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 9 | AA8266108 | 2 /4  RUE BALTHAZARD | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 10 | AC0685511 | ALBERT THOMAS 104 | 0 | 1 | 1 | 55.0 | bdnb-bg-Y7LD-5N7C-MAKU |
| 11 | AA4814810 | LES PINS | 0 | 1 | 1 | 50.0 | bdnb-bg-JMUE-VX7J-RR9W |
| 12 | AF3596129 | LE CARRE JEANNE D'ARC | 0 | 1 | 1 | 50.0 | bdnb-bg-KHGT-PGMN-ULLQ |
| 13 | AB8384588 | 20 RUE DOMREMY | 0 | 2 | 2 | 47.0 | bdnb-bg-6N14-CG3Y-368U bdnb-bg-JEMQ-4EVE-PBW5 |
| 14 | AD0905141 | SDC 0247 2 COURS EUGENIE | 0 | 1 | 1 | 46.0 | bdnb-bg-47CA-SSEN-59KD |
| 15 | AA6892400 | LE REBATEL - MS15801 | 0 | 1 | 1 | 40.0 | bdnb-bg-93HE-L5TK-1T1J |
| 16 | AD5687900 | LES TERRASSES DE VITTON | 0 | 1 | 1 | 40.0 | bdnb-bg-71JU-3SD2-VSLD |
| 17 | AC5764881 | LA ROCHELIERE - MS178053 | 1 | 2 | 1 | 38.58 | bdnb-bg-48AL-SC64-A3ET |
| 18 | AA7362809 | LE JARDIN BARA | 0 | 1 | 1 | 36.0 | bdnb-bg-ED7P-8YCZ-L6UX |
| 19 | AA2791176 | SDC CARINAE | 0 | 1 | 1 | 26.0 | bdnb-bg-A7ZQ-2FYK-N2Z2 |
| 20 | AD0026757 | SDC 110 AVENUE LACASSAGNE | 1 | 2 | 1 | 25.47 | bdnb-bg-HUMZ-YPJ4-PPDK |

## Top 20 — omissions du snapshot par nombre de bâtiments

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AB8384588 | 20 RUE DOMREMY | 0 | 2 | 2 | 47.0 | bdnb-bg-6N14-CG3Y-368U bdnb-bg-JEMQ-4EVE-PBW5 |
| 2 | AA6767180 | SDC ALBERT THOMAS | 0 | 1 | 1 | 128.0 | bdnb-bg-1K5S-G75D-PMQN |
| 3 | AA0762245 | LE PERGOLESE II | 0 | 1 | 1 | 96.0 | bdnb-bg-6SBM-R9F7-GP62 |
| 4 | AC4464848 | LE PERGOLESE III | 0 | 1 | 1 | 96.0 | bdnb-bg-6SBM-R9F7-GP62 |
| 5 | AC4130548 | SDC COURS ALBERT THOMAS | 0 | 1 | 1 | 88.0 | bdnb-bg-MKGQ-UFU9-924X |
| 6 | AA2367605 | 80 bis rue Feuillat | 0 | 1 | 1 | 71.0 | bdnb-bg-T3QK-M61N-9RTG |
| 7 | AA3216041 | 123 bis cours Albert Thomas | 0 | 1 | 1 | 71.0 | bdnb-bg-T3QK-M61N-9RTG |
| 8 | AA4815643 | 41 RUE PROFESSEUR ROCHAIX | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 9 | AA6892657 | 6 BALTHAZAR | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 10 | AA8266108 | 2 /4  RUE BALTHAZARD | 0 | 1 | 1 | 69.0 | bdnb-bg-XR8J-ADB7-B1HT |
| 11 | AC0685511 | ALBERT THOMAS 104 | 0 | 1 | 1 | 55.0 | bdnb-bg-Y7LD-5N7C-MAKU |
| 12 | AA4814810 | LES PINS | 0 | 1 | 1 | 50.0 | bdnb-bg-JMUE-VX7J-RR9W |
| 13 | AF3596129 | LE CARRE JEANNE D'ARC | 0 | 1 | 1 | 50.0 | bdnb-bg-KHGT-PGMN-ULLQ |
| 14 | AD0905141 | SDC 0247 2 COURS EUGENIE | 0 | 1 | 1 | 46.0 | bdnb-bg-47CA-SSEN-59KD |
| 15 | AA6892400 | LE REBATEL - MS15801 | 0 | 1 | 1 | 40.0 | bdnb-bg-93HE-L5TK-1T1J |
| 16 | AD5687900 | LES TERRASSES DE VITTON | 0 | 1 | 1 | 40.0 | bdnb-bg-71JU-3SD2-VSLD |
| 17 | AC5764881 | LA ROCHELIERE - MS178053 | 1 | 2 | 1 | 38.58 | bdnb-bg-48AL-SC64-A3ET |
| 18 | AA7362809 | LE JARDIN BARA | 0 | 1 | 1 | 36.0 | bdnb-bg-ED7P-8YCZ-L6UX |
| 19 | AA2791176 | SDC CARINAE | 0 | 1 | 1 | 26.0 | bdnb-bg-A7ZQ-2FYK-N2Z2 |
| 20 | AD0026757 | SDC 110 AVENUE LACASSAGNE | 1 | 2 | 1 | 25.47 | bdnb-bg-HUMZ-YPJ4-PPDK |
