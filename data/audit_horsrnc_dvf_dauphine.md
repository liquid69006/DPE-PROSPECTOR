# Audit hors-RNC + ventes DVF — secteur dauphine_lacassagne

Lecture seule. Cible = prédicat *Hors-RNC actifs* de renderSecteur (non fusionnée, clé ≠ cle_adresse copro, sans immat, `nb_ventes_logement>0`).

> **Lecture critique.** Une cible n'est **sûrement** rattachable que si l'identité est *forte* : immat via BDNB `rel_batiment_groupe_rnc`, **ou** variante orthographique exacte de `cle_adresse`, **ou** même `batiment_groupe_id` que la copro (même bâtiment → parc-neutre, classe des 7 déjà appliquées). Les autres (proximité GPS seule, match sur nom/adresse libre, RNC live) sont des **pistes à confirmer manuellement** : les appliquer en masse **détruit du parc** (ce sont des bâtiments DISTINCTS proches d'une copro, dont on retirerait le stock BDNB réel sans que la copro le gagne).

## Bilan

| Indicateur | Valeur |
|---|--:|
| Cibles hors-RNC + ventes | **119** |
| → **A-fort** (rattachable sûr, parc-sûr) | **53** |
| → A-faible (piste, confirmation manuelle) | 38 |
| → B (monopropriété / non immatriculée) | **28** |
| Ventes-log à relocaliser — A-fort | **207** |
| Ventes-log — A-faible (non sûr) | 111 |
| **Parc A-fort seul** : 22268 → 22193 | **-75** (53 modélisés) |
| Parc A-fort+faible (illustre la destruction) : 22268 → 21754 | -514 |

### Répartition A par voie de résolution (force)

| Étape | n | force |
|---|--:|---|
| a_bdnb | 53 | strong |
| c_gps | 38 | weak |

### Répartition A par mécanisme

| Mécanisme | n |
|---|--:|
| ALIAS_RNC meme bgid (parc-neutre) | 50 |
| ALIAS_RNC miroir bgid | 38 |
| RE-POINT (ancre fusionnee dans la cible) | 3 |

## Top 10 A-FORT par ventes-logement à relocaliser

| Adresse (cle) | v_log | v_tot | via | immat | copro | syndic | lots | mécanisme |
|---|--:|--:|---|---|---|---|--:|---|
| `9|RUE|PROFESSEUR PAUL SISLEY` | 16 | 16 | a_bdnb | AA0012898 | ATRIUM SISLEY | GAGNEUX SERVICES IMM | 225 | ALIAS_RNC meme bgid (parc-neutre) |
| `53|RUE|ETIENNE RICHERAND` | 10 | 15 | a_bdnb | AC3598851 | LE BEAUBOURG | non connu | 64 | RE-POINT (ancre fusionnee dans la cible) |
| `36|RUE|ST PHILIPPE` | 9 | 9 | a_bdnb | AC8791634 | 34/36 Rue Saint Philippe | COTRIMO GESTION | 28 | ALIAS_RNC meme bgid (parc-neutre) |
| `194|AVENUE|FELIX FAURE` | 8 | 8 | a_bdnb | AD9012642 | 23 Métallurgie & 194 F. Fa | CABINET PETRUCCI CON | 36 | ALIAS_RNC meme bgid (parc-neutre) |
| `168|AVENUE|FELIX FAURE` | 8 | 11 | a_bdnb | AA2730372 | SDC LE PRESIDENT | ADMINISTION D'IMMEUB | 40 | ALIAS_RNC meme bgid (parc-neutre) |
| `209|AVENUE|FELIX FAURE` | 8 | 8 | a_bdnb | AD3386570 | SDC VILLA SYRACUSE | REGIE FRANCOIS GOFFI | 34 | ALIAS_RNC meme bgid (parc-neutre) |
| `15|RUE|ST EUSEBE` | 7 | 7 | a_bdnb | AA2028389 | SDC ESPACE EMERAUDE BAT B | LYMMOBILIER | 33 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|RUE|MONTBRILLANT` | 6 | 6 | a_bdnb | AB6211445 | LE PRIVILEGE MONTBRILLANT  | FONCIA SAINT LOUIS | 59 | ALIAS_RNC meme bgid (parc-neutre) |
| `12|RUE|LOUIS JASSERON` | 6 | 6 | a_bdnb | AA7487564 | L'ENEIDE 1 - MS15805 | LAMY | 29 | ALIAS_RNC meme bgid (parc-neutre) |
| `89|RUE|BELLECOMBE` | 6 | 10 | a_bdnb | AB2463065 | LE BELLECOMBE SAINT ANTOIN | FONCIA LYON | 72 | ALIAS_RNC meme bgid (parc-neutre) |

## A-FORT — rattachables sûrs (toutes)

| cle | v_log | via | immat | anchor | copro | lots | mécanisme |
|---|--:|---|---|---|---|--:|---|
| `9|RUE|PROFESSEUR PAUL SISLEY` | 16 | a_bdnb | AA0012898 | `7B|RUE|PROFESSEUR PAUL SISLEY` | ATRIUM SISLEY | 225 | ALIAS_RNC meme bgid (parc-neutre) |
| `53|RUE|ETIENNE RICHERAND` | 10 | a_bdnb | AC3598851 | `51|RUE|ETIENNE RICHERAND` | LE BEAUBOURG | 64 | RE-POINT (ancre fusionnee dans la cible) |
| `36|RUE|ST PHILIPPE` | 9 | a_bdnb | AC8791634 | `34|RUE|ST PHILIPPE` | 34/36 Rue Saint Philippe | 28 | ALIAS_RNC meme bgid (parc-neutre) |
| `168|AVENUE|FELIX FAURE` | 8 | a_bdnb | AA2730372 | `170|AVENUE|FELIX FAURE` | SDC LE PRESIDENT | 40 | ALIAS_RNC meme bgid (parc-neutre) |
| `194|AVENUE|FELIX FAURE` | 8 | a_bdnb | AD9012642 | `23|RUE|METALLURGIE` | 23 Métallurgie & 194 F.  | 36 | ALIAS_RNC meme bgid (parc-neutre) |
| `209|AVENUE|FELIX FAURE` | 8 | a_bdnb | AD3386570 | `7||PTR ST EUSEBE` | SDC VILLA SYRACUSE | 34 | ALIAS_RNC meme bgid (parc-neutre) |
| `15|RUE|ST EUSEBE` | 7 | a_bdnb | AA2028389 | `12|RUE|ST EUSEBE` | SDC ESPACE EMERAUDE BAT  | 33 | ALIAS_RNC meme bgid (parc-neutre) |
| `12|RUE|LOUIS JASSERON` | 6 | a_bdnb | AA7487564 | `17|RUE|LOUIS JASSERON` | L'ENEIDE 1 - MS15805 | 29 | ALIAS_RNC meme bgid (parc-neutre) |
| `14|RUE|ST MAXIMIN` | 6 | a_bdnb | AB2460335 | `1|RUE|ROSSAN` | TERRASSES ET VILLAS ST M | 53 | ALIAS_RNC meme bgid (parc-neutre) |
| `89|RUE|BELLECOMBE` | 6 | a_bdnb | AB2463065 | `13|RUE|ST ANTOINE` | LE BELLECOMBE SAINT ANTO | 72 | ALIAS_RNC meme bgid (parc-neutre) |
| `9|RUE|MONTBRILLANT` | 6 | a_bdnb | AB6211445 | `9B|RUE|MONTBRILLANT` | LE PRIVILEGE MONTBRILLAN | 59 | ALIAS_RNC meme bgid (parc-neutre) |
| `12|RUE|VILLON` | 5 | a_bdnb | AA7891641 | `10|RUE|VILLON` | RESIDENCE LE PARC VILLON | 34 | ALIAS_RNC meme bgid (parc-neutre) |
| `260|RUE|PAUL BERT` | 5 | a_bdnb | AE1699040 | `264B|RUE|PAUL BERT` | LE CLOS ROUGET DE L'ISLE | 8 | ALIAS_RNC meme bgid (parc-neutre) |
| `2|RUE|LOUIS JASSERON` | 5 | a_bdnb | AF5264262 | `3|RUE|LOUIS JASSERON` | LES BALCONS DE LA PART D | 25 | ALIAS_RNC meme bgid (parc-neutre) |
| `38|RUE|BARABAN` | 5 | a_bdnb | AC9726381 | `37|RUE|BARABAN` | L'OLEANDRE | 29 | ALIAS_RNC meme bgid (parc-neutre) |
| `51|RUE|ST ANTOINE` | 5 | a_bdnb | AD9391244 | `50|RUE|ST ANTOINE` | LE PATIO SAINT-ANTOINE - | 25 | ALIAS_RNC meme bgid (parc-neutre) |
| `6|RUE|ST EUSEBE` | 5 | a_bdnb | AG4913810 | `8|RUE|ST EUSEBE` | LE  SAINT EUSEBE | 15 | ALIAS_RNC meme bgid (parc-neutre) |
| `7|RUE|MAURICE FLANDIN` | 5 | a_bdnb | AB1493691 | `6|RUE|MAURICE FLANDIN` | LE PRIVILÈGE LAFAYETTE | 18 | ALIAS_RNC meme bgid (parc-neutre) |
| `93|RUE|BELLECOMBE` | 5 | a_bdnb | AB5869177 | `94|RUE|BELLECOMBE` | SDC LE BELLECOMBE | 21 | ALIAS_RNC meme bgid (parc-neutre) |
| `12|RUE|CARRY` | 4 | a_bdnb | AC1825504 | `6|RUE|CARRY` | 6/8, rue Carry | 12 | ALIAS_RNC meme bgid (parc-neutre) |
| `131|AVENUE|FELIX FAURE` | 4 | a_bdnb | AA8736043 | `139|AVENUE|FELIX FAURE` | PRT DIEU SQUARE CARRE PR | 83 | ALIAS_RNC meme bgid (parc-neutre) |
| `182|AVENUE|FELIX FAURE` | 4 | a_bdnb | AC2489979 | `9|RUE|METALLURGIE` | LE FELIX FAURE | 52 | ALIAS_RNC meme bgid (parc-neutre) |
| `30|RUE|ST ANTOINE` | 4 | a_bdnb | AC3226362 | `25|RUE|ST ANTOINE` | LA COUR SAINT ANTOINE | 63 | ALIAS_RNC meme bgid (parc-neutre) |
| `56|AVENUE|LACASSAGNE` | 4 | a_bdnb | AA4814810 | `54|AVENUE|LACASSAGNE` | LES PINS | 50 | RE-POINT (ancre fusionnee dans la cible) |
| `10|RUE|DAUPHINE` | 3 | a_bdnb | AF0858860 | `1|RUE|ST MAXIMIN` | 1 R SAINT MAXIMIN | 14 | ALIAS_RNC meme bgid (parc-neutre) |
| `14|RUE|ST SIDOINE` | 3 | a_bdnb | AB2206571 | `12|RUE|ST SIDOINE` | LA VICTORIENNE | 165 | ALIAS_RNC meme bgid (parc-neutre) |
| `18|RUE|ETIENNE RICHERAND` | 3 | a_bdnb | AG2447720 | `19|RUE|ETIENNE RICHERAND` | SDC 19 RUE ETIENNE RICHE | 8 | ALIAS_RNC meme bgid (parc-neutre) |
| `18|RUE|ST ANTOINE` | 3 | a_bdnb | AE9439365 | `17|RUE|ST ANTOINE` | LE SAINT ANTOINE | 45 | ALIAS_RNC meme bgid (parc-neutre) |
| `21|RUE|STE ANNE DE BARABAN` | 3 | a_bdnb | AC8951105 | `21A|RUE|STE ANNE DE BARABAN` | SDC 21 RUE SAINTE ANNE D | 26 | ALIAS_RNC meme bgid (parc-neutre) |
| `22|RUE|ETIENNE RICHERAND` | 3 | a_bdnb | AB0141341 | `21|RUE|ETIENNE RICHERAND` | SDC 21 RUE ETIENNE RICHE | 14 | ALIAS_RNC meme bgid (parc-neutre) |
| `237|AVENUE|FELIX FAURE` | 3 | a_bdnb | AC0225904 | `336|RUE|PAUL BERT` | PAUL BERT - FELIX FAURE | 16 | ALIAS_RNC meme bgid (parc-neutre) |
| `316|RUE|PAUL BERT` | 3 | a_bdnb | AC6168629 | `318|RUE|PAUL BERT` | RESIDENCE 318 RUE PAUL B | 6 | RE-POINT (ancre fusionnee dans la cible) |
| `3|RUE|ST EUSEBE` | 3 | a_bdnb | AB0287870 | `2|RUE|ST EUSEBE` | LE SAINT EUSEBE | 14 | ALIAS_RNC meme bgid (parc-neutre) |
| `48|RUE|ST MAXIMIN` | 3 | a_bdnb | AB2784080 | `51|RUE|ST MAXIMIN` | RESIDENCE MANET | 50 | ALIAS_RNC meme bgid (parc-neutre) |
| `5|RUE|MONTBRILLANT` | 3 | a_bdnb | AA9253212 | `5B|RUE|MONTBRILLANT` | 5 BIS RUE DE MONTBRILLAN | 6 | ALIAS_RNC meme bgid (parc-neutre) |
| `32|RUE|PROFESSEUR PAUL SISLEY` | 2 | a_bdnb | AA7236011 | `31|RUE|PROFESSEUR PAUL SISLEY` | LES DAHLIAS - MS130778 | 32 | ALIAS_RNC meme bgid (parc-neutre) |
| `46|RUE|ST MAXIMIN` | 2 | a_bdnb | AB1744747 | `43|RUE|ST MAXIMIN` | LES JARDINS D'HELIOS | 22 | ALIAS_RNC meme bgid (parc-neutre) |
| `63|RUE|VILLETTE` | 2 | a_bdnb | AA0787333 | `11|AVENUE|GEORGES POMPIDOU` | LES TERRASSES DE LA GARE | 80 | ALIAS_RNC meme bgid (parc-neutre) |
| `64|RUE|DAUPHINE` | 2 | a_bdnb | AA8932717 | `62|RUE|DAUPHINE` | PARC SISLEY | 21 | ALIAS_RNC meme bgid (parc-neutre) |
| `74|RUE|ETIENNE RICHERAND` | 2 | a_bdnb | AF6417042 | `30|RUE|ANTOINE CHARIAL` | SDC LE CASTELLANNE | 55 | ALIAS_RNC meme bgid (parc-neutre) |
| `84|RUE|ANTOINE CHARIAL` | 2 | a_bdnb | AA7209463 | `86|RUE|ANTOINE CHARIAL` | LE CLOS DE LA ROSERAIE - | 38 | ALIAS_RNC meme bgid (parc-neutre) |
| `17|RUE|ST VICTORIEN` | 1 | a_bdnb | AA9260977 | `16|RUE|ST VICTORIEN` | LE SAINT VICTORIEN | 69 | ALIAS_RNC meme bgid (parc-neutre) |
| `20|RUE|GUILLOUD` | 1 | a_bdnb | AB1910728 | `20T|RUE|GUILLOUD` | 20 TER RUE GUILLOUD | 32 | ALIAS_RNC meme bgid (parc-neutre) |
| `23|RUE|STE ANNE DE BARABAN` | 1 | a_bdnb | AB8780330 | `24|RUE|STE ANNE DE BARABAN` | SAINTE ANNE | 47 | ALIAS_RNC meme bgid (parc-neutre) |
| `24|AVENUE|LACASSAGNE` | 1 | a_bdnb | AG1556893 | `24||ET 24 BIS AVENUE LACASSAGNE` | BRICKS 2 | 64 | ALIAS_RNC meme bgid (parc-neutre) |
| `25|RUE|ROGER BRECHAN` | 1 | a_bdnb | AB4648424 | `23|RUE|ROGER BRECHAN` | COTE PARC SISLEY-LYN | 17 | ALIAS_RNC meme bgid (parc-neutre) |
| `2|RUE|METALLURGIE` | 1 | a_bdnb | AB8301665 | `1|RUE|METALLURGIE` | 1 RUE DE LA METALLURGIE | 21 | ALIAS_RNC meme bgid (parc-neutre) |
| `30|RUE|PROFESSEUR PAUL SISLEY` | 1 | a_bdnb | AC7505134 | `30||30B R DU PROFESSEUR PAUL SISLEY` | SDC SDC LE SISLEY | 43 | ALIAS_RNC meme bgid (parc-neutre) |
| `40|RUE|ST MAXIMIN` | 1 | a_bdnb | AB5878327 | `39|RUE|ST MAXIMIN` | SDC LE CASSIOPEE | 33 | ALIAS_RNC meme bgid (parc-neutre) |
| `41|COURS|ALBERT THOMAS` | 1 | a_bdnb | AG6298160 | `41|COURS|ALBERT THOMAS 24 RUE DES TUILIERS` | LE SPHINX | 34 | ALIAS_RNC meme bgid (parc-neutre) |
| `5|RUE|MEYNIS` | 1 | a_bdnb | AB8324360 | `5B|RUE|MEYNIS` | 5 BIS RUE MEYNIS | 9 | ALIAS_RNC meme bgid (parc-neutre) |
| `5|RUE|ROSSAN` | 1 | a_bdnb | AC1757376 | `1|RUE|GUILLOUD` | LE N1 RUE GUILLOUD | 70 | ALIAS_RNC meme bgid (parc-neutre) |
| `97|RUE|BARABAN` | 1 | a_bdnb | AD7354640 | `99|RUE|BARABAN` | SDC 99 RUE BARABAN | 7 | ALIAS_RNC meme bgid (parc-neutre) |

## A-FAIBLE — pistes (confirmation manuelle, NON applicables en masse)

| cle | v_log | via | immat | anchor | copro | lots |
|---|--:|---|---|---|---|--:|
| `30|RUE|ETIENNE RICHERAND` | 12 | c_gps(16m) | AA0358655 | `28|RUE|ETIENNE RICHERAND` | Antoine Charial | 211 |
| `59|RUE|BARABAN` | 11 | c_gps(16m) | AB1482132 | `56|RUE|BARABAN` | 56 RUE BARABAN | 27 |
| `44|RUE|TURBIL` | 8 | c_gps(19m) | AE0617704 | `48|RUE|TURBIL` | 120- 48 rue Turbil 69003 | 18 |
| `3|RUE|MAURICE FLANDIN` | 7 | c_gps(27m) | AB1493691 | `6|RUE|MAURICE FLANDIN` | LE PRIVILÈGE LAFAYETTE | 18 |
| `143|RUE|DAUPHINE` | 6 | c_gps(14m) | AD0379297 | `141|RUE|DAUPHINE` | SDC 141 RUE DU DAUPHINE | 13 |
| `29|RUE|STE ANNE DE BARABAN` | 6 | c_gps(15m) | AA1700848 | `27|RUE|STE ANNE DE BARABAN` | LES JARDINS DE BABYLONE | 99 |
| `12|RUE|MOISSONNIER` | 5 | c_gps(18m) | AD3458353 | `7|RUE|MOISSONNIER` | 7 RUE MOISSONNIER | 13 |
| `9|RUE|ST EUSEBE` | 5 | c_gps(23m) | AB1809680 | `11|RUE|ST EUSEBE` | LE JARDIN DU 3EME | 42 |
| `125|RUE|DAUPHINE` | 3 | c_gps(30m) | AD5054531 | `131|RUE|DAUPHINE` | SDC 131 RUE DU DAUPHINE | 7 |
| `272|RUE|PAUL BERT` | 3 | c_gps(16m) | AD1124098 | `281|RUE|PAUL BERT` | 281 RUE PAUL BERT | 17 |
| `310|COURS|LAFAYETTE` | 3 | c_gps(11m) | AB4665733 | `308|COURS|LAFAYETTE` | 308 LAFAYETTE | 13 |
| `6|RUE|METALLURGIE` | 3 | c_gps(22m) | AC2489979 | `9|RUE|METALLURGIE` | LE FELIX FAURE | 52 |
| `75|RUE|DAUPHINE` | 3 | c_gps(11m) | AD5267315 | `71|RUE|DAUPHINE` | SDC 71 RUE DU DAUPHINE | 14 |
| `9|RUE|GABILLOT` | 3 | c_gps(29m) | AB8046419 | `18|RUE|GABILLOT` | LE REGENCY - MS160242 | 28 |
| `10|RUE|TEINTURIERS` | 2 | c_gps(25m) | AA3284353 | `6|RUE|TEINTURIERS` | L'HELIODORE | 16 |
| `11|RUE|DAVID` | 2 | c_gps(21m) | AB3954260 | `9|RUE|DAVID` | LACASSAGNE DAVID | 84 |
| `124|RUE|ANTOINE CHARIAL` | 2 | c_gps(15m) | AB7442684 | `131|RUE|ANTOINE CHARIAL` | 131 Rue Antoine Charial | 29 |
| `139|RUE|DAUPHINE` | 2 | c_gps(24m) | AD0379297 | `141|RUE|DAUPHINE` | SDC 141 RUE DU DAUPHINE | 13 |
| `234|RUE|PAUL BERT` | 2 | c_gps(22m) | AC3758810 | `243|RUE|PAUL BERT` | SDC 243 RUE PAUL BERT | 11 |
| `325|RUE|PAUL BERT` | 2 | c_gps(18m) | AB2859320 | `308|RUE|PAUL BERT` | LE SAINT EUSEBE | 30 |
| `48|AVENUE|GEORGES POMPIDOU` | 2 | c_gps(18m) | AB9345703 | `46|AVENUE|GEORGES POMPIDOU` | SDC BARABAN VI | 74 |
| `4|RUE|MAURICE FLANDIN` | 2 | c_gps(27m) | AB1493691 | `6|RUE|MAURICE FLANDIN` | LE PRIVILÈGE LAFAYETTE | 18 |
| `76|RUE|DAUPHINE` | 2 | c_gps(30m) | AA6762058 | `59|RUE|DAUPHINE` | SDC 59 RUE DU DAUPHINE | 24 |
| `122|RUE|BARABAN` | 1 | c_gps(13m) | AD5237797 | `115|RUE|BARABAN` | SDC LE DUO I | 35 |
| `13|RUE|METALLURGIE` | 1 | c_gps(22m) | AC2489979 | `9|RUE|METALLURGIE` | LE FELIX FAURE | 52 |
| `157|RUE|ANTOINE CHARIAL` | 1 | c_gps(10m) | AE4525572 | `154|RUE|ANTOINE CHARIAL` | VILLA CHARIAL | 11 |
| `15|RUE|DAVID` | 1 | c_gps(20m) | AB2810141 | `17|RUE|DAVID` | 17 DAVID | 16 |
| `21|RUE|GUILLOUD` | 1 | c_gps(16m) | AA7407463 | `16|RUE|GUILLOUD` | LE SISLEY - MS32872 | 50 |
| `225|AVENUE|FELIX FAURE` | 1 | c_gps(13m) | AB9711508 | `227|AVENUE|FELIX FAURE` | SDC 227 AVENUE FELIX FAU | 9 |
| `254|COURS|LAFAYETTE` | 1 | c_gps(9m) | AD1420348 | `256|COURS|LAFAYETTE` | 256 COURS LAFAYETTE | 5 |
| `277|RUE|PAUL BERT` | 1 | c_gps(18m) | AE1699040 | `264B|RUE|PAUL BERT` | LE CLOS ROUGET DE L'ISLE | 8 |
| `279|RUE|PAUL BERT` | 1 | c_gps(10m) | AD1124098 | `281|RUE|PAUL BERT` | 281 RUE PAUL BERT | 17 |
| `33|AVENUE|LACASSAGNE` | 1 | c_gps(19m) | AA1647494 | `27|AVENUE|LACASSAGNE` | RESIDENCE FLORENTINE | 369 |
| `3|RUE|ROSSAN` | 1 | c_gps(15m) | AB2460335 | `1|RUE|ROSSAN` | TERRASSES ET VILLAS ST M | 53 |
| `45|AVENUE|GEORGES POMPIDOU` | 1 | c_gps(27m) | AB9345703 | `46|AVENUE|GEORGES POMPIDOU` | SDC BARABAN VI | 74 |
| `5|RUE|ST MAXIMIN` | 1 | c_gps(19m) | AB6522890 | `3|RUE|ST MAXIMIN` | 3 R SAINT MAXIMIN | 19 |
| `65|RUE|ETIENNE RICHERAND` | 1 | c_gps(20m) | AC3617586 | `67|RUE|ETIENNE RICHERAND` | LES BALCONS DE STE ANNE | 53 |
| `8|RUE|ST PHILIPPE` | 1 | c_gps(8m) | AC7889439 | `10|RUE|ST PHILIPPE` | LE CLOS SAINT PHILIPPE | 12 |

## Cibles B (structurellement hors-RNC)

| cle | v_log | v_tot | nb_log_bdnb | usage | dernier essai |
|---|--:|--:|--:|---|---|
| `106|RUE|BARABAN` | 13 | 17 | 61 | Résidentiel collectif | d_rnc_live |
| `22|AVENUE|GEORGES POMPIDOU` | 10 | 11 | 37 | Résidentiel collectif | d_rnc_live |
| `8|RUE|CLAUDIUS PIONCHON` | 9 | 9 | None | Tertiaire | d_rnc_live |
| `28|RUE|PROFESSEUR PAUL SISLEY` | 6 | 6 | 18 | Résidentiel collectif | d_rnc_live |
| `11|RUE|RIBOUD` | 5 | 5 | 13 | Résidentiel collectif | d_rnc_live |
| `15|RUE|ETIENNE RICHERAND` | 5 | 10 | 45 | Résidentiel collectif | d_rnc_live |
| `7|RUE|METALLURGIE` | 5 | 8 | 21 | Résidentiel collectif | d_rnc_live |
| `8|RUE|DOCTEUR REBATEL` | 5 | 6 | 25 | Résidentiel collectif | d_rnc_live |
| `16|RUE|ETIENNE RICHERAND` | 4 | 4 | 61 | Résidentiel collectif | d_rnc_live |
| `22|RUE|LOUIS JASSERON` | 4 | 4 | 37 | Résidentiel collectif | d_rnc_live |
| `31|RUE|STE ANNE DE BARABAN` | 4 | 9 | 1 | Tertiaire | d_rnc_live |
| `47|RUE|PROFESSEUR PAUL SISLEY` | 4 | 4 | 2 | Résidentiel collectif | d_rnc_live |
| `4|RUE|JEAN RENOIR` | 4 | 16 | 35 | Résidentiel collectif | d_rnc_live |
| `4|RUE|MARCEL PEHU` | 4 | 4 | 32 | Résidentiel collectif | d_rnc_live |
| `5|RUE|MARCEL PEHU` | 4 | 4 | 32 | Résidentiel collectif | d_rnc_live |
| `71|RUE|PAUL BERT` | 4 | 4 | None | Secondaire | d_rnc_live |
| `51|AVENUE|GEORGES POMPIDOU` | 3 | 3 | 18 | Résidentiel collectif | d_rnc_live |
| `52|AVENUE|GEORGES POMPIDOU` | 3 | 3 | 18 | Résidentiel collectif | d_rnc_live |
| `5|RUE|JEAN PIERRE LEVY` | 3 | 24 | 36 | Résidentiel collectif | d_rnc_live |
| `10|RUE|METALLURGIE` | 2 | 3 | 2 | Résidentiel collectif | d_rnc_live |
| `10|RUE|TERNOIS` | 2 | 4 | 80 | Résidentiel collectif | d_rnc_live |
| `21|RUE|CLAUDIUS PIONCHON` | 2 | 2 | 35 | Résidentiel collectif | d_rnc_live |
| `21|RUE|ST ANTOINE` | 2 | 2 | 16 | Résidentiel collectif | d_rnc_live |
| `6|RUE|PROFESSEUR PAUL SISLEY` | 2 | 3 | 6 | Résidentiel collectif | d_rnc_live |
| `14|RUE|PREVOYANTS DE L AVENIR` | 1 | 1 | 1 | Résidentiel individuel | d_rnc_live |
| `4|RUE|TERNOIS` | 1 | 1 | 80 | Résidentiel collectif | d_rnc_live |
| `69|RUE|BARABAN` | 1 | 42 | None | Dépendance | d_rnc_live |
| `6|RUE|PREVOYANTS DE L AVENIR` | 1 | 1 | 1 | Résidentiel individuel | d_rnc_live |