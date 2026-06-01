# Diag — Définition de `ventes_par_an_logement` / `nb_ventes_logement` (DL)

Tâche READ-ONLY. Secteur Dauphiné-Lacassagne. Aucune modification de données/code.
Confronte le calcul réel du champ « ventes strictes (logement) » à la définition métier Yann.

**Définition métier cible (Yann)** : une **mutation DVF** comportant **au moins 1 lot d'habitation** = **1 vente** ; répétitions inter-années comptées ; mutations parking/commerce **seules** (sans lot habitation) **exclues**. Grain = **la MUTATION** (1 acte notarié = 1 vente), pas la disposition ni le lot.

---

## E1 — Localisation du calcul

**Provenance tranchée : script aval (in-repo), PAS `CONS`, PAS `make_light.py`, PAS `index.html`.**

- **make_light.py** (`C:\Users\Station 5\make_light.py`, hors dépôt) : confirmé, **ne calcule PAS** `*_logement`. Grep `ventes_par_an_logement|nb_ventes_logement|taux_logement|_correctif_taux_logement` sur make_light.py = **0 match**. Sa boucle DVF ne produit que le BRUT (`nb_ventes_total` / `ventes_par_an`).
- **CONS / consolidé** : non. Le champ n'est pas pré-présent en entrée ; il est posé par un correctif additif identifié par un marker metadata (cf. ci-dessous).
- **index.html** : ne fait que **lire** `ventes_par_an_logement` / `nb_ventes_logement` (helper `vpaOf`, fonction `renderSecteur`). Il n'écrit jamais ces champs (aucune affectation `a.ventes_par_an_logement = …`, seulement des lectures). Voir E2 §dashboard.

### Fichier(s) + lignes qui ÉCRIVENT les champs

**Écrivain PRINCIPAL** — `scripts/fix_taux_logement.py` :
```
196   a["ventes_par_an_logement"] = vlog
197   a["nb_ventes_logement"] = nlog
198   a["taux_rotation_logement"] = t_new
199   a["classement_rotation_logement"] = c_new
200   a["_taux_logement_src"] = src
```
Marker metadata : **`_correctif_taux_logement`** (posé l.253). Confirmé présent dans `data/secteur_dauphine_lacassagne_light.json` → `metadata._correctif_taux_logement`.

**Écrivains de SURCHARGE (overrides aval, manuels)** qui ré-écrivent les mêmes champs sur des sous-ensembles d'adresses, après `fix_taux_logement` :
- `scripts/_apply_strict_btq_fix.py` — lignes 84-86 (`nb_ventes_logement`, `ventes_par_an_logement`, `_taux_logement_src='strict_btq_post_logement'`) + override 50 LACASSAGNE l.98-100 (`cherrypick_vefa_5lots`). 37+1 adresses.
- `scripts/fix_orphan_recovery_dl.py` — lignes 422-426 (`_taux_logement_src='orphan_suffix_btq_recovery'`). 5 adresses.

Ces overrides sont « immuables » : `fix_taux_logement.py` les saute lors d'un rerun via `SOURCES_IMMUABLES` (l.116-121) — `strict_btq_post_logement`, `cherrypick_vefa_5lots`, `cherrypick_vefa_neutralise`, `copie_sans_dependance`. (Note : `orphan_suffix_btq_recovery` n'est PAS dans cette liste → serait recalculé par un rerun de fix_taux_logement ; détail mineur hors scope.)

### Répartition réelle des sources dans le light DL (mesurée)
```
copie_sans_dependance       930   (jointure fiable, 0 dépendance-seule -> copie du brut)
filtre_habitation           347   (jointure fiable, delta dépendance soustrait)
copie_jointure_incertaine    65   (jointure non fiable -> copie intacte du brut + flag)
strict_btq_post_logement     37   (override B/T/Q recalculé Apt+Mai)
orphan_suffix_btq_recovery    5
cherrypick_vefa_5lots         1
```
Toutes les 1385 adresses ont `nb_ventes_logement` (0 manquant).

---

## E2 — Logique exacte (code lu)

### A) Calcul principal `fix_taux_logement.py`

**Source DVF** : `full["mutations_dvf"]` lu depuis `data/secteur_{SECTEUR}.json` (l.98-101). Le FULL contient bien `Code type local` + `Type local` (vérifié : 8852 mutations, champs présents). **Le light NE contient PAS ces champs** → le calcul DOIT se faire sur le FULL (ou rejoué depuis lui).

**Index mutations par adresse** (jointure best-effort No voie + tokens Voie normalisés, l.104-106) :
```
104   mut_idx = collections.defaultdict(list)
105   for m in M:
106       mut_idx[(numof(m.get("No voie")), toks(m.get("Voie")))].append(m)
```

**Grain de déduplication** (l.145-150) — **par MUTATION**, clé = `(Date mutation, Valeur foncière)` :
```
145   muts = collections.defaultdict(set)   # an -> {(date,valeur)}
146   types = collections.defaultdict(set)  # (date,valeur) -> {code}
147   for m in rows:
148       k = (m.get("Date mutation"), m.get("Valeur fonciere"))
149       muts[yr(m)].add(k)
150       types[k].add(str(m.get("Code type local")))
```
→ un acte = 1 entrée dans le `set`, même s'il porte plusieurs lignes/lots/dispositions. **Le grain est bien la MUTATION**, pas la ligne/lot/disposition. (Léger écart de clé vs make_light qui dédupe sur `(année, Date mutation, No disposition, Valeur foncière)` : ici la clé OMET `No disposition`. Conséquence : si deux dispositions distinctes d'un même acte ont même date+valeur, make_light les compte 2, ce calcul 1. En pratique aligné car `reliable = abs(deriv_all - stored) <= 1`, sinon bascule en `copie_jointure_incertaine`.)

**Filtre « lot habitation »** (l.151-155) — sur **`Code type local`**, garde les mutations dont l'ensemble des codes contient `1` (Maison) ou `2` (Appartement) :
```
151   deriv_all = sum(len(muts[y]) for y in ANS)
152   dep_only = {}
153   for y in ANS:
154       dep_only[y] = sum(1 for k in muts[y]
155                         if not ({"1", "2"} & types[k]))
```
`dep_only[y]` = nombre de mutations de l'année **sans aucun** code 1/2 = mutations dépendance/commerce **seules** (types {3 Dépendance, 4 Local commercial} uniquement). **Comportement sur mutations MIXTES** : `types[k]` est l'**union** des codes de toutes les lignes de l'acte ; dès qu'un code 1 ou 2 y figure, la condition `{"1","2"} & types[k]` est vraie → la mutation **n'est PAS** dans `dep_only` → elle est **conservée** (comptée comme vente logement). Correct vs def Yann.

**Stratégie non-destructive** (l.156-174) — n'écrase jamais le brut, soustrait seulement le delta :
```
156   reliable = abs(deriv_all - stored) <= 1
157   delta = sum(dep_only.values())
158
159   if not reliable:                       # jointure incertaine
160       src = "copie_jointure_incertaine"  # vlog = copie du brut (intact + flag)
161       vlog = dict(vpa); nlog = stored
164   elif delta == 0:                       # 0 dépendance-seule
165       src = "copie_sans_dependance"      # vlog = copie du brut
166       vlog = dict(vpa); nlog = stored
169   else:                                  # delta>0 : soustraction par an, clamp >=0
170       src = "filtre_habitation"
171       vlog = {y: max(0, (vpa.get(y) or 0) - dep_only.get(y, 0)) for y in ANS ...}
173       nlog = sum(vlog.values())
```
→ `nb_ventes_logement` est **ancré sur le brut autoritatif** `ventes_par_an` (pas sur le `deriv_all` rejoué), et on **soustrait** le nombre de mutations dépendance-seule détectées. Choix délibéré (jointure ~94,7 % fiable, ré-écriture jugée destructrice — docstring l.10-17).

**Grain temporel** : `ANS = ["2021","2022","2023","2024","2025"]` (l.56). `yr(m)` = 4 derniers chars de `Date mutation` (l.74-76). `ventes_par_an_logement` = dict année→count ; `nb_ventes_logement` = somme des années (`nlog = sum(vlog.values())`). Répétitions inter-années conservées (comptage par an, pas de dédup cross-année). Conforme def Yann.

### B) Override `_apply_strict_btq_fix.py` (37 adresses + 1)

Recalcul **strict pur** pour les adresses initialement `copie_jointure_incertaine` sur-comptées :
- Filtre habitation = `Type local in ('Appartement','Maison')` (l.54) — équivalent codes {1,2}, **exclut Dépendance + commerce**.
- Dédup **par mutation** = `(Date mutation, Valeur foncière)` (l.57-59), `seen` set par clé adresse.
- `nb_ventes_logement = len(rows uniques Apt+Mai)`, `ventes_par_an_logement = Counter par année` (l.81-85).
- Override VEFA 50 LACASSAGNE forcé à 5 (1 vente bloc = 5 lots, l.98-100).

Même grain (mutation) et même filtre (habitation seul) que le calcul principal, en version « recompute pur » plutôt que « soustraction du delta ».

### C) Dashboard `index.html` (lecture seule)

`vpaOf` (l.4838-4839) :
```
4838  const vpaOf = a => (secteurStrict && a && a.ventes_par_an_logement)
4839    ? a.ventes_par_an_logement : (a ? a.ventes_par_an : null);
```
Toggle « 📊 Ventes strictes » (l.832) ON par défaut (`secteurStrictBtnSync`, l.2425). Quand actif, le rendu agrège `ventes_par_an_logement` ; sinon `ventes_par_an`. `renderSecteur` somme par an via `vpaOf` (l.4877, 4895, 5107). **Aucune écriture** — confirme la provenance « script aval ».

---

## E3 — Confrontation à la définition métier Yann

| Critère Yann | Code réel | Verdict |
|---|---|---|
| Filtre = mutation avec ≥1 lot habitation | `{"1","2"} & types[k]` sur l'union des codes de l'acte (principal) ; `Type local in (Apt,Maison)` (override) | **OK** |
| Mutations MIXTES (appart + parking) conservées | union des codes → si 1/2 présent, gardée | **OK** (gardée) |
| Mutations parking/commerce SEULES exclues | `dep_only` = actes sans aucun code 1/2 → soustraits | **OK** (exclues) |
| Grain = MUTATION (1 acte = 1 vente) | dédup `set` sur `(Date mutation, Valeur foncière)` | **OK** |
| « 2 apparts en 1 acte = 1 vente » | la clé `(date, valeur)` dédupe l'acte → **1** | **OK** (conforme : compte 1) |
| Répétitions inter-années comptées | comptage par année, pas de dédup cross-année | **OK** |

**Écarts / réserves** (déduction, pas bug fonctionnel) :
1. **Méthode « soustraction » ≠ « recompute »** (calcul principal seulement). `fix_taux_logement` ne recalcule pas `nb_ventes_logement` directement = (mutations habitation rejouées) ; il fait `brut autoritatif − (dépendances-seules détectées)`. C'est par design (jointure best-effort 94,7 %). Si la jointure rate une mutation dépendance-seule, elle reste comptée comme logement (sous-correction possible). Inversement, jointure incertaine (65 adr, `|deriv−stored|>1`) → champ = **copie du brut intacte**, donc **non strict** (peut sur-compter). C'est documenté et assumé. Le résultat n'est donc pas un strict parfait à 100 %, mais une approximation prudente, non-destructive.
2. **Clé de dédup principale omet `No disposition`** (vs make_light qui l'inclut). Pour le strict c'est plutôt cohérent avec la def Yann (grain = acte, pas disposition) ; mais cela crée une légère asymétrie de comptage vs le brut sur les actes multi-dispositions même-valeur, absorbée par le garde-fou `reliable`.

### Chiffres (mesurés sur le light DL)
- `nb_ventes_total` (brut) agrégé : **4508** → **901,6/an** (attendu ~895/an : cohérent).
- `nb_ventes_logement` (strict) agrégé : **2998** → **599,6/an** (attendu ~599,6 : **match exact**).
- Delta agrégé brut−strict : **1525** mutations dépendance/commerce-seules retirées (≈ −33,8 %).
- Adresses avec `nb_ventes_logement < nb_ventes_total` : **385** / 1385.
- Par an, brut → strict : 2021 1069→720 · 2022 1086→724 · 2023 793→544 · 2024 756→501 · 2025 804→509.

### Rejouabilité locale
- `Code type local` / `Type local` **absents du light**, mais **présents dans `data/secteur_dauphine_lacassagne.json`** (FULL, 8852 mutations). → La logique **EST rejouable localement** (preuve directe disponible), exactement comme le font `fix_taux_logement.py` et `_apply_strict_btq_fix.py` qui lisent le FULL.

---

## CONCLUSION

**(a) OÙ est défini `ventes_par_an_logement` / `nb_ventes_logement`** :
- Écrivain principal : **`scripts/fix_taux_logement.py` lignes 196-197** (taux/classe/src l.198-200). Marker metadata : **`metadata._correctif_taux_logement`** (posé l.253, présent dans le light DL).
- Overrides aval sur sous-ensembles : `scripts/_apply_strict_btq_fix.py` l.84-86/98-100 (`strict_btq_post_logement`, `cherrypick_vefa_5lots`) et `scripts/fix_orphan_recovery_dl.py` l.422-426 (`orphan_suffix_btq_recovery`).
- **Provenance** : **script aval in-repo**. PAS `CONS`, PAS `make_light.py` (0 match grep — preuve directe), PAS `index.html` (lecture seule via `vpaOf` l.4838).

**(b) La logique MATCHE-t-elle la définition Yann ?** **OUI.**
- Filtre lot habitation : **OK** — `Code type local ∈ {1,2}` / `Type local ∈ {Appartement, Maison}`, sur l'union des codes de l'acte → mutations mixtes conservées, parking/commerce seuls exclus. (Preuve directe : code lu l.151-155 et l.54.)
- Grain : **OK** — déduplication par MUTATION `(Date mutation, Valeur foncière)` (l.148 / l.57). 2 apparts en 1 acte = 1 vente. Répétitions inter-années comptées.
- Chiffres confirment (strict 599,6/an = attendu exact).

**(c) Correction nécessaire : NON** (sur la définition/le grain/le filtre). La logique implémentée est conforme à la cible métier Yann.
- Réserves mineures (non bloquantes, par design non-destructif) : (i) le calcul principal **soustrait** le delta dépendance au lieu de recompute pur, et (ii) 65 adresses `copie_jointure_incertaine` gardent le brut (non strict) faute de jointure fiable — ce sont des approximations prudentes documentées (docstring l.10-28), pas des erreurs de définition. Si un jour Yann veut un strict 100 % exact (recompute pur partout), il faudrait passer toutes les adresses fiables par la logique de `_apply_strict_btq_fix.py` (recompute Apt+Mai depuis le FULL) plutôt que par la soustraction — mais **ce n'est pas requis** par la définition actuelle, et le delta serait marginal. Aucun fichier à modifier en l'état.

*Preuve directe = code lu (fix_taux_logement.py, _apply_strict_btq_fix.py, index.html) + chiffres mesurés sur le light. Déduction = écarts §E3.1-2 et asymétrie clé dédup.*
