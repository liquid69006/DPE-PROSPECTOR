# Diagnostic — `21 AVENUE CHARLES FLOQUET` / `2 BIS RUE CHAMPFLEURY` (MP)

> **Conclusion :** vraie **monopropriété** (hôtel particulier). **Aucun
> correctif applicable** — confirmation de la catégorie B documentée
> par `scripts/fix_mp_cibles_horsrnc.py` (l. 38-42) et de la
> classification *Monopropriété* du diag orphelines BDNB du 2026-05-19.

Lecture seule, aucune modification des données.

## 1. État du `secteur_motte_picquet_light.json`

| | clé | bgid | immat | nb_log_bdnb | v_log | `_fusion_auto` | usage |
|---|---|---|---|--:|--:|---|---|
| | `21\|AVENUE\|CHARLES FLOQUET` | `bdnb-bg-GZ79-JFXC-74CF` | ∅ | 1 | 1 | non | **Résidentiel individuel** |
| | `2\|RUE\|CHAMPFLEURY` | `bdnb-bg-AZSW-71TB-HGHR` | ∅ | 1 | 0 | non | **Résidentiel individuel** |
| réf. | `5\|RUE\|CHAMPFLEURY` | `bdnb-bg-HDBR-VL4E-HBBK` | AA8426090 | 15 | 1 | non | Résid. collectif |
| réf. | `6\|RUE\|CHAMPFLEURY` | `bdnb-bg-PEQ4-R33A-KUU4` | (fusion) | 14 | 4 | → `45\|AVENUE\|SUFFREN` | Résid. collectif |

Aucune variante `2B` / `2BIS` / `2 BIS` RUE CHAMPFLEURY n'existe dans
le light, le DVF brut (8 322 mutations), ni la BDNB brute (1 155
bâtiments). Seuls `2|RUE|CHAMPFLEURY`, `5|RUE|CHAMPFLEURY`,
`6|RUE|CHAMPFLEURY` sont présents.

## 2. Vérification RNC (snapshot + live tabular-api)

- **Snapshot light (821 copros MP)** : 2 copros mentionnent
  CHAMPFLEURY — `AA8426090` (5 Rue Champfleury, 18 lots) et
  `AB0758383` (45 av Suffren, nom *« 6 RUE CHAMPFLEURY »*, 29 lots,
  déjà couplée à `6|RUE|CHAMPFLEURY` via ALIAS_RNC). **Aucune copro
  mentionnant *« 2 BIS CHAMPFLEURY »* ni *« 21 CHARLES FLOQUET »*.**
- **RNC live** (`tabular-api` resource `3ea8e2c3…`,
  `adresse_reference__contains`) :
  - `CHAMPFLEURY` 75007 → **1 ligne**, AA8426090 (5 rue Champfleury).
    75015 → 0.
  - `FLOQUET` 75007 → **26 lignes, 0 avec n° 21** dans
    `adresse_reference` / `numero_voie_adresse` /
    `adresse_complementaire_1/2/3`.

## 3. BAN (référentiel national d'adresses)

- `2 bis rue Champfleury 75007` → BAN renvoie `2b Rue Champfleury
  75007 Paris` (`type=housenumber`, **score 0.68**) — l'adresse existe
  côté BAN mais **n'a aucune vente DVF ni copro RNC**.
- `21 avenue Charles Floquet 75007` → BAN renvoie l'adresse à
  **score 0.97** (housenumber confirmé).

## 4. Identification du mécanisme — *aucun ne s'applique*

- **Même `batiment_groupe_id` ?** Non : `GZ79` ≠ `AZSW` ≠ `HDBR` ≠
  `PEQ4`. BDNB modélise quatre bâtiments distincts (18-60 m
  séparation). Pas de candidat *« même bgid → parc-neutre »*.
- **Bgids différents mais même copro RNC ?** Impossible — il n'existe
  **aucune copro RNC commune** candidate (ni à l'une ni à l'autre
  adresse, ni nulle part dans le RNC national pour ces clés).
- **Adresse d'immatriculation principale ?** Néant — il n'y a **pas
  d'immatriculation** pour ce bâti.

## 5. Preuve DVF — nature du bien

L'unique mutation au **`21 AVENUE CHARLES FLOQUET`** sur les 8 322 du
secteur :

| Date | Nature | Valeur foncière | Type local | Pièces | Surface | Commune |
|---|---|--:|---|--:|--:|---|
| 06/09/2023 | Vente | **15 174 950 €** | **Maison** | 13 | 430 m² | PARIS 07 (75007) |

→ **Hôtel particulier (430 m², 13 pièces, 15,1 M€) vendu en un
seul lot**, ce qui est strictement cohérent avec :
- `usage_principal_bdnb='Résidentiel individuel'`
- `nb_log_bdnb=1`
- 1 vente DVF unique sur 5 ans, valeur foncière compatible avec un
  bien unique.

Aucune mutation `2 BIS / 2B RUE CHAMPFLEURY` en DVF brut (0 hit).

## 6. Conclusion & action

**Classification : Monopropriété confirmée** (hôtel particulier).

**Aucun correctif appliqué.** Forcer un `ALIAS_RNC` ou
`FUSION_RNC_EXTRA_NUMS` vers une copro inexistante introduirait des
données fausses et violerait les gardes des scripts (`copro AA??????
introuvable sur 2 BIS RUE CHAMPFLEURY` → ABORT immédiat).

Le cas reste, conformément, dans le filtre *« Hors-RNC actifs »* du
dashboard avec 1 vente strictement comptée — c'est l'exposition
correcte d'une vraie monopropriété résidentielle au sein du secteur.

**Ré-instruction inutile** sauf nouvelle preuve externe (Pappers /
acte notarié) d'une copro à cette adresse — auquel cas ce fichier
sera mis à jour.

---
*Source : `scripts/diag_orphelines_bdnb.py`,
`scripts/fix_mp_cibles_horsrnc.py` (l. 38-42), DVF brut
`data/dvf_motte_picquet.json`, BDNB `data/bdnb_motte_picquet.json`,
RNC tabular-api `3ea8e2c3-0038-464a-b17e-cd5c91f65ce2`, BAN
`api-adresse.data.gouv.fr`.*
