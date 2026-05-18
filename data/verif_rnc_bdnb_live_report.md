# Vérification RNC → BDNB — API live vs snapshot (lecture seule)

API ouverte `api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_rnc` (sans clé), table de relation `numero_immat` ↔ `batiment_groupe_id`. Compare l'ensemble live à `data/bdnb_dauphine_lacassagne.json`.

## Bilan

| Indicateur | Valeur |
|---|--:|
| Copros vérifiées | 553 |
| Copros snapshot ≠ live | 20 |
| **Copros où le snapshot a omis des bâtiments** | **20** |
| Bâtiments live absents du snapshot | 23 (~1276.35 lgts) |
| Bâtiments snapshot absents du live | 0 |

## Top 20 — omissions du snapshot par logements

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AB0222935 | LE PAVILLON DE FLORE II - MS32833 | 0 | 1 | 1 | 151.0 | bdnb-bg-W8VN-TH3A-X19Z |
| 2 | AC3226362 | LA COUR SAINT ANTOINE | 1 | 2 | 1 | 121.61 | bdnb-bg-U4S4-QR1D-QNE5 |
| 3 | AB8378317 | LES JARDINS DU CHATEAU | 1 | 2 | 1 | 115.67 | bdnb-bg-PU3N-4779-FEBT |
| 4 | AA8146995 | ESPERANCE 12 - ESPACE EMERAUDE | 0 | 1 | 1 | 95.0 | bdnb-bg-NZ67-8FQ2-8L1E |
| 5 | AC9670597 | 26 RUE DE TURBIL | 0 | 1 | 1 | 77.0 | bdnb-bg-TYWJ-CL2Y-E96B |
| 6 | AH0111229 | PAUL BERT 314/316 | 0 | 1 | 1 | 74.0 | bdnb-bg-MLQ3-6L3N-HFMK |
| 7 | AI3897188 | Résidence SAINT EUSEBE | 0 | 1 | 1 | 66.0 | bdnb-bg-MRTT-PSEJ-TWBW |
| 8 | AD5237797 | SDC LE DUO I | 1 | 2 | 1 | 61.09 | bdnb-bg-6JZ9-FA72-RT9X |
| 9 | AJ0217901 | LE GUILLOUD | 0 | 1 | 1 | 60.0 | bdnb-bg-YTPJ-Q2XB-2DEF |
| 10 | AB0818369 | SAINT-MAXIMIN | 0 | 1 | 1 | 53.0 | bdnb-bg-J3X7-528N-6TTX |
| 11 | AA3186756 | PARC MISTRAL | 0 | 2 | 2 | 52.0 | bdnb-bg-9EQE-Y8LA-N95M bdnb-bg-EJCA-TGBV-X3GU |
| 12 | AA4868378 | La Closerie des Tilleuls II | 1 | 2 | 1 | 50.98 | bdnb-bg-6D6N-M1N7-38NB |
| 13 | AC6278774 | L ENEIDE II - MS15806 | 0 | 1 | 1 | 46.0 | bdnb-bg-4DUC-A62Z-LN35 |
| 14 | AA8440844 | ESPACE EMERAUDE BAT H | 0 | 1 | 1 | 45.0 | bdnb-bg-UD36-AJ94-ZSUK |
| 15 | AH4739264 | URBAN PLACE | 0 | 1 | 1 | 44.0 | bdnb-bg-5PV4-4ZZM-SWV8 |
| 16 | AB1081009 | SDC 31 RUE CLAUDIUS PIONCHON | 0 | 1 | 1 | 42.0 | bdnb-bg-BXEH-4Z8G-SH57 |
| 17 | AD4134433 | 1 place des maison neuves | 0 | 2 | 2 | 36.0 | bdnb-bg-E44U-71Q9-CC2J bdnb-bg-NPQY-QDC3-YZW4 |
| 18 | AE7492838 | 202 AVENUE FELIX FAURE | 0 | 1 | 1 | 36.0 | bdnb-bg-37ZL-S88G-NPNJ |
| 19 | AA3284353 | L'HELIODORE | 0 | 1 | 1 | 32.0 | bdnb-bg-U297-N64A-4SXK |
| 20 | AI6621486 | COPROPRIETE 254 RUE PAUL BERT | 0 | 2 | 2 | 18.0 | bdnb-bg-5S72-KVML-QK4E bdnb-bg-RUV7-747H-Z31A |

## Top 20 — omissions du snapshot par nombre de bâtiments

| # | Immat | Copropriete | snap | live | +bât | +lgts | bgid live manquants au snapshot |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | AA3186756 | PARC MISTRAL | 0 | 2 | 2 | 52.0 | bdnb-bg-9EQE-Y8LA-N95M bdnb-bg-EJCA-TGBV-X3GU |
| 2 | AD4134433 | 1 place des maison neuves | 0 | 2 | 2 | 36.0 | bdnb-bg-E44U-71Q9-CC2J bdnb-bg-NPQY-QDC3-YZW4 |
| 3 | AI6621486 | COPROPRIETE 254 RUE PAUL BERT | 0 | 2 | 2 | 18.0 | bdnb-bg-5S72-KVML-QK4E bdnb-bg-RUV7-747H-Z31A |
| 4 | AB0222935 | LE PAVILLON DE FLORE II - MS32833 | 0 | 1 | 1 | 151.0 | bdnb-bg-W8VN-TH3A-X19Z |
| 5 | AC3226362 | LA COUR SAINT ANTOINE | 1 | 2 | 1 | 121.61 | bdnb-bg-U4S4-QR1D-QNE5 |
| 6 | AB8378317 | LES JARDINS DU CHATEAU | 1 | 2 | 1 | 115.67 | bdnb-bg-PU3N-4779-FEBT |
| 7 | AA8146995 | ESPERANCE 12 - ESPACE EMERAUDE | 0 | 1 | 1 | 95.0 | bdnb-bg-NZ67-8FQ2-8L1E |
| 8 | AC9670597 | 26 RUE DE TURBIL | 0 | 1 | 1 | 77.0 | bdnb-bg-TYWJ-CL2Y-E96B |
| 9 | AH0111229 | PAUL BERT 314/316 | 0 | 1 | 1 | 74.0 | bdnb-bg-MLQ3-6L3N-HFMK |
| 10 | AI3897188 | Résidence SAINT EUSEBE | 0 | 1 | 1 | 66.0 | bdnb-bg-MRTT-PSEJ-TWBW |
| 11 | AD5237797 | SDC LE DUO I | 1 | 2 | 1 | 61.09 | bdnb-bg-6JZ9-FA72-RT9X |
| 12 | AJ0217901 | LE GUILLOUD | 0 | 1 | 1 | 60.0 | bdnb-bg-YTPJ-Q2XB-2DEF |
| 13 | AB0818369 | SAINT-MAXIMIN | 0 | 1 | 1 | 53.0 | bdnb-bg-J3X7-528N-6TTX |
| 14 | AA4868378 | La Closerie des Tilleuls II | 1 | 2 | 1 | 50.98 | bdnb-bg-6D6N-M1N7-38NB |
| 15 | AC6278774 | L ENEIDE II - MS15806 | 0 | 1 | 1 | 46.0 | bdnb-bg-4DUC-A62Z-LN35 |
| 16 | AA8440844 | ESPACE EMERAUDE BAT H | 0 | 1 | 1 | 45.0 | bdnb-bg-UD36-AJ94-ZSUK |
| 17 | AH4739264 | URBAN PLACE | 0 | 1 | 1 | 44.0 | bdnb-bg-5PV4-4ZZM-SWV8 |
| 18 | AB1081009 | SDC 31 RUE CLAUDIUS PIONCHON | 0 | 1 | 1 | 42.0 | bdnb-bg-BXEH-4Z8G-SH57 |
| 19 | AE7492838 | 202 AVENUE FELIX FAURE | 0 | 1 | 1 | 36.0 | bdnb-bg-37ZL-S88G-NPNJ |
| 20 | AA3284353 | L'HELIODORE | 0 | 1 | 1 | 32.0 | bdnb-bg-U297-N64A-4SXK |
