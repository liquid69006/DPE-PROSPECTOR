# PATCH `make_light_motte_picquet.py` — propagation immat dans passes `immat_fix` / `immat_horsrnc_fix`

**Cible** : `make_light_motte_picquet.py` (hors-repo, scripts locaux utilisateur).

**Bug** : les 2 passes correctives `immat_fix` (46 cas) et `immat_horsrnc_fix`
(58 cas) créent des adresses pour des copros RNC dont la `cle_adresse` n'existe
pas dans BDNB, mais ne propagent pas `numero_immatriculation`,
`nb_lots_habitation`, `syndic`, `taux_rotation`, `classement_rotation` depuis la
copro source. Résultat : 104 adresses MP apparaissent comme hors-RNC alors
qu'elles ont une copro liée via `cle_adresse`.

Validé sur snapshot 2026-05-21 : 100% des adresses avec `_bdnb_match in
{'immat_fix','immat_horsrnc_fix'}` ont `numero_immatriculation=None` ET
`nb_lots_habitation` absent ET `dans_majic=False`. Vs 677 adresses OK avec
`_bdnb_match='immat'` toutes correctement propagées.

## Patch (à coller dans `make_light_motte_picquet.py`)

### 1. Helper de propagation (à ajouter en haut du fichier, après les imports)

```python
import re

def _syn_ok(s):
    """Syndic valide = non vide et != 'non connu'."""
    return bool(s) and not re.match(r"\s*non connu\s*$", str(s), re.I)


def _taux_annuel(nb_ventes, nb_lots_habit):
    """Taux de rotation annuel en % sur 5 ans."""
    if not nb_lots_habit or nb_lots_habit <= 0:
        return None
    return round(nb_ventes / (5 * nb_lots_habit / 100), 1)


def _classement(taux):
    """Seuils observes dans snapshot : >3 Tres actif, >=2 Actif, >=1 Modere."""
    if taux is None:
        return None
    if taux > 3:
        return "Très actif"
    if taux >= 2:
        return "Actif"
    if taux >= 1:
        return "Modéré"
    return "Figé"


def propagate_copro_to_adresse(adresse, copro):
    """Propage les champs autoritatifs RNC de la copro vers l'adresse creee
    par les passes immat_fix / immat_horsrnc_fix.

    A appeler APRES la creation de l'adresse minimaliste, AVANT l'insertion
    finale dans la liste adresses[].

    Champs propages depuis la copro :
      - numero_immatriculation
      - nb_lots_habitation (si > 0 dans la copro)
      - syndic + _syndic_src (si l'adresse n'en a pas de valide)
      - taux_rotation / classement_rotation       (recalcul depuis nb_ventes_total)
      - taux_rotation_logement / classement_rotation_logement (recalcul depuis nb_ventes_logement)

    Ne touche PAS : cle, bgid, coord, ventes_par_an, nb_log_bdnb, usage, etc.
    """
    immat = copro.get("numero_immatriculation")
    if immat:
        adresse["numero_immatriculation"] = immat

    nlog = copro.get("nb_lots_habitation") or 0
    if nlog > 0:
        adresse["nb_lots_habitation"] = nlog
        nv_tot = adresse.get("nb_ventes_total") or 0
        nv_log = adresse.get("nb_ventes_logement") or 0
        t_tot = _taux_annuel(nv_tot, nlog)
        t_log = _taux_annuel(nv_log, nlog)
        if t_tot is not None:
            adresse["taux_rotation"] = t_tot
            adresse["classement_rotation"] = _classement(t_tot)
        if t_log is not None:
            adresse["taux_rotation_logement"] = t_log
            adresse["classement_rotation_logement"] = _classement(t_log)

    # Syndic : ne pas ecraser un syndic deja valide cote adresse (rnic_live etc.)
    if _syn_ok(copro.get("syndic")) and not _syn_ok(adresse.get("syndic")):
        adresse["syndic"] = copro["syndic"]
        adresse["_syndic_src"] = copro.get("_syndic_src") or "rnc"
```

### 2. Insertion dans la passe `immat_fix` (~46 cas)

Localiser la section qui assigne `_bdnb_match='immat_fix'` et
`_coord_source='rnc_immat_fix'`. Probablement quelque chose comme :

```python
# AVANT (extrait probable)
for copro in coproprietes:
    if copro["cle_adresse"] not in adresses_by_cle:
        # Adresse copro absente du pivot BDNB, on la cree
        new_adr = {
            "cle": copro["cle_adresse"],
            "adresse": copro["adresse"],
            "longitude": copro["longitude"],
            "latitude": copro["latitude"],
            "_bdnb_match": "immat_fix",
            "_coord_source": "rnc_immat_fix",
            "batiment_groupe_id": deduce_bgid_via_gps(copro),
            # ... autres champs BDNB
        }
        adresses.append(new_adr)
```

Ajouter l'appel à `propagate_copro_to_adresse` AVANT le `adresses.append` :

```python
# APRES (patch applique)
for copro in coproprietes:
    if copro["cle_adresse"] not in adresses_by_cle:
        new_adr = {
            "cle": copro["cle_adresse"],
            "adresse": copro["adresse"],
            "longitude": copro["longitude"],
            "latitude": copro["latitude"],
            "_bdnb_match": "immat_fix",
            "_coord_source": "rnc_immat_fix",
            "batiment_groupe_id": deduce_bgid_via_gps(copro),
        }
        propagate_copro_to_adresse(new_adr, copro)   # <<< AJOUT
        adresses.append(new_adr)
```

### 3. Insertion dans la passe `immat_horsrnc_fix` (~58 cas)

Même logique pour la passe qui assigne `_bdnb_match='immat_horsrnc_fix'` et
`_coord_source='rnc_immat_horsrnc_fix'`. Probablement traitement des
B-suffixes / disambig `#immat` qui sont ABSENTS du pivot BDNB initial.

Ajouter `propagate_copro_to_adresse(new_adr, copro)` AVANT l'insertion finale
dans `adresses`.

## Validation post-patch

Après application du patch et regénération du light :

```powershell
PYTHONUTF8=1 python -c "
import json
light = json.loads(open('data/secteur_motte_picquet_light.json',encoding='utf-8').read())
cbc = {c.get('cle_adresse'): c for c in light['coproprietes'] if c.get('cle_adresse')}
broken = 0
for a in light['adresses']:
    if a.get('_fusion_auto'): continue
    cp = cbc.get(a['cle'])
    if cp and cp.get('numero_immatriculation') and not a.get('numero_immatriculation'):
        broken += 1
print(f'Adresses BROKEN apres patch : {broken}  (attendu 0)')
"
```

Cible : `Adresses BROKEN apres patch : 0`.

## Impact attendu

- **Parc strictement neutre** : `parc_model` utilisait déjà `co.get(a["cle"])`
  pour les contributions, donc les copros étaient déjà comptées correctement.
- **UI** : -104 adresses du listing "hors-RNC actifs" du dashboard Motte-Picquet
  (passent en "RNC ancrée").
- **Dashboard rotation** : les adresses recoivent leurs `taux_rotation` et
  `classement_rotation`, alignés sur le calcul des autres adresses RNC.
- **Aucun risque** sur les corrections terrain en place (`_fusion_auto`,
  `_fusion_cible`, `_fusion_auto_label`, etc. ne sont pas touchés).

## Application à Dauphiné-Lacassagne

Patch quasi-identique à porter dans `make_light_dauphine_lacassagne.py` si les
deux passes `immat_fix` / `immat_horsrnc_fix` existent aussi côté DL (à
vérifier — scan analogue sur secteur_dauphine_lacassagne_light.json).

## Cas particuliers à surveiller

- **Adresses fused** (`_fusion_auto=True`) : la propagation peut être inutile,
  voire problématique si l'adresse fused ne doit pas porter d'immat (cas
  Cambronne). Le code patch ne touche pas le flag fusion, mais ajoute l'immat.
  Si `_fusion_auto=True` est posé après la passe immat_*, le résultat reste
  cohérent (l'adresse fused est skip dans `parc_model`).
- **Disambig `#immat`** : les cles comme `32|RUE|PERIGNON #AB7675259` sont
  traitées comme n'importe quelle autre cle ; la propagation marche tant que la
  copro a la même cle_adresse exacte (`#AB7675259` inclus).
- **`dans_majic`** : la propagation NE force PAS `dans_majic=True`. Si une
  adresse n'est pas dans MAJIC, c'est légitime de garder `False`. Le bug
  rapporté (`dans_majic=False` chez 104 broken) est une corrélation, pas une
  cause.
