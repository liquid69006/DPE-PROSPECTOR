# Diag MANCHE D Montchat (Phase 5, pose tags mono/copro_non_immat)
> DRY-RUN. PYTHONUTF8=1, ASCII-safe. **AUCUNE ecriture KV, AUCUN POST, AUCUN commit / git add.** Date : 2026-06-03.
> Namespace KV : `secteur_assignments:dauphine-lacassagne-montchat`. Light, DL/MP, index.html NON touches.

---

## 0. ECARTS vs cibles du brief (a lire avant tout)

Le brief annoncait **519 tags** (234 mono + 285 copro = 74+211) et **KV 103 -> 622**, en supposant le perimetre 576 DISJOINT des 103 B2a. La RE-DERIVATION fidele (recompute, jamais les comptes pre-calcules) revele **deux ecarts structurels** que le brief demandait justement de flaguer :

**Ecart 1 - les 211 angle-mort ne sont PAS tous copro_non_immat.** Le brief posait la regle de coherence : *aucun angle-mort 0-PM classe copro ne doit avoir `nb_log_bdnb==1`* (sinon = mono, pas copro). Or sur les angle-mort du perimetre net, seuls **57 ont `nb_log_bdnb>1`** (eligibles copro) ; les autres ont `nb_log_bdnb==1` ou `None` -> les tagger copro VIOLERAIT la regle de coherence du brief. Ils sont donc NON tagges (residu 0-PM mono-logement / sans logement BDNB). Le diag ETAPE 2 lui-meme nommait ces 211 *ANGLE-MORT PP* (0 proprio PM), pas copro_non_immat : la conversion 211->copro etait une hypothese du brief, non une sortie de l'ETAPE 2.

**Ecart 2 - le perimetre 576 RECOUVRE les 103 B2a (intersection 95).** Les tags B2a sont KV-only (PAS ecrits dans le light), donc les 103 cles restent `!in_copro` dans le light et **retombent dans le perimetre 576** : 95 des 103 B2a y sont. Une re-derivation naive re-classerait ces 95 (et en re-taggerait 35 differemment, ex. bureaux->mono - or *bureaux* est un signal terrain manuel NON derivable de la propriete MAJIC). Pour respecter *"sans re-tagger aucun des 103"*, **les 103 cles B2a sont EXCLUES du tagging D** -> intersection forcee VIDE, 0 bureau ecrase.

**Resultat corrige : 278 tags D** (192 mono + 86 copro_non_immat), KV **103 -> 381** (+278/0/0). Pas 519/622.

---

## 1. Distribution finale

Perimetre = `!in_copro & !numero_immatriculation & !is_fa` lu sur le light POST-B1 (signaux ETAPE 2) = **576** hors-RNC. On en EXCLUT les **95** cles deja taggees B2a (anti-re-tag) -> **481** a tagger. Classif RE-DERIVEE (recompte proprietaires PM par parcelle depuis parquet, filtre syndic).

| Classe (perimetre net 481) | n | Tag pose |
|---|--:|---|
| MONO (1 SIREN, ratio>=0.9) | 122 | `mono` |
| COPRO (>=2 SIREN) | 29 | `copro_non_immat` |
| ANGLE-MORT 0-PM, nb_log>1 | 57 | `copro_non_immat` |
| ANGLE-MORT 0-PM, nb_log<=1/None | 25 | **aucun** (coherence) |
| MONO_weak (1 SIREN, ratio<0.9) | 46 | **aucun** (residu) |
| **TOTAL net** | **349** | |

**Tags poses (manche D) = 278** : 192 mono + 86 copro_non_immat (29 copro >=2SIREN + 57 angle-mort nb_log>1).
Non-tagges net = 71 (46 mono_weak + 25 angle nb_log<=1). Verif total : 278 tags + 71 non-tagges = 349 (perimetre net) ; + 95 B2a = 444 = 576.

## 2. Coherences

| Verif | Attendu | Resultat |
|---|---|---|
| angle-mort tagge copro_non_immat avec `nb_log_bdnb==1` | 0 | **0** OK (les 25 angle-mort nb_log<=1 sont EXCLUS du tagging) |
| copro tagge >=2 SIREN avec `nb_log_bdnb<=1` | 0 | **3** FLAGUE (voir ci-dessous) |
| intersection D vs B2a (103) | VIDE | **0** OK (VIDE) |

Les 25 angle-mort `nb_log_bdnb<=1`/`None` sont NON tagges (residu 0-PM mono-logement ou facade sans logement BDNB) : la regle de coherence du brief (pas d'angle-mort copro a nb_log==1) est donc RESPECTEE par construction.

**FLAG - 3 copro_non_immat issus de >=2 SIREN MAJIC mais `nb_log_bdnb<=1`/`None`** : tag CONSERVE (>=2 proprietaires PM distincts sur la parcelle = preuve directe de pluri-propriete ; le `nb_log_bdnb` BDNB de la facade est manquant/sous-estime, ce n'est pas un signal mono). A confirmer hors-bande :
- `113|COURS|ALBERT THOMAS` nb_log=None n_sirens=2
- `1|RUE|CONSTANT` nb_log=1 n_sirens=2
- `1|RUE|FELIX ROLLET` nb_log=None n_sirens=2

## 3. Diff KV attendu

Le worker POST ecrase tout l'objet `assignments` : le candidat contient donc les **103 B2a** (inchanges) + **278 nouveaux D**.

| | assignments |
|---|--:|
| B2a (mirror actuel) | 103 |
| candidat (POST complet) | 381 |

**Diff = +278 ajouts, 0 modif, 0 retrait.** KV 103 -> 381.

## 4. Neutralite parc / ventes

Les tags `as.type` sont KV-only : **le light n'est PAS touche**, donc parc `secL` et Sigma ventes calcules par `renderSecteur` sur le light brut sont **inchanges** (15 848 / 932).

Detail regle UI : pour les hors-RNC residentiels, le parc compte deja `nb_log_bdnb`. Un tag `copro_non_immat` conserve `nb_log_bdnb` (neutre). Un tag `mono` represente une mono-propriete : selon la regle DL, l'UI peut ramener l'effectif a 1 logement (`getEffectiveLog`). **Mais ce calcul est cote index.html (non touche ici)** ; le light et donc le parc brut servi restent identiques. Adresses mono avec `nb_log_bdnb>1` (ou un recalcul UI mono->1 modifierait l'affichage) : **61** (liste de tracabilite ; pas un bug, comportement DL attendu - signale ici pour audit).

> NEUTRALITE STRICTE cote donnees servies : tags KV uniquement, light intact. Parc 15 848 et Sigma 932 INCHANGES.

## 5. Les 46 MONO_weak non-tagges (residu terrain)

1 seul proprio PM mais ratio < 0.9 (parcelle sous-couverte) -> **aucun tag**, comme le garde DL ratio>=0.9 les exclut.

| cle | nb_log | ratio | n_sirens |
|---|--:|--:|--:|
| 14|RUE|HARMONIE | 40 | 0.025 | 1 |
| 9|RUE|EGLISE | 25 | 0.04 | 1 |
| 10|IMPASSE|LINDBERG | 23 | 0.087 | 1 |
| 11B|IMPASSE|LINDBERG | 23 | 0.087 | 1 |
| 7|RUE|DOC PAUL DIDAY | 20 | 0.3 | 1 |
| 36|RUE|JEANNE D ARC | 20 | 0.1 | 1 |
| 11|RUE|BARA | 18 | 0.167 | 1 |
| 44|RUE|LOUIS | 18 | 0.056 | 1 |
| 96|BOULEVARD|PINEL | 8 | 0.375 | 1 |
| 2|RUE|DOCTEUR REBATEL | 8 | 0.25 | 1 |
| 7|RUE|LOUIS | 7 | 0.429 | 1 |
| 22|RUE|STE MARIE | 7 | 0.857 | 1 |
| 14|RUE|JEAN QUITOUT | 4 | 0.75 | 1 |
| 18|RUE|ALFRED DE MUSSET | 4 | 0.5 | 1 |
| 247|AVENUE|LACASSAGNE | 2 | 0.5 | 1 |
| 48|RUE|LOUIS | None | 0 | 1 |
| 7|IMPASSE|MOREL | None | 0 | 1 |
| 10|RUE|LOUISE | None | 0 | 1 |
| 100|AVENUE|LACASSAGNE | None | 0 | 1 |
| 100|RUE|BALME | None | 0 | 1 |
| 107|RUE|TRARIEUX | None | 0 | 1 |
| 113|COURS|RICHARD VITTON | None | 0 | 1 |
| 115|AVENUE|LACASSAGNE | None | 0 | 1 |
| 139|COURS|ALBERT THOMAS | None | 0 | 1 |
| 14|RUE|CHAMBOVET | None | 0 | 1 |
| 15|RUE|CLAUDIUS PENET | None | 0 | 1 |
| 1B|RUE|CERISIERS | None | 0 | 1 |
| 20|RUE|EGLISE | None | 0 | 1 |
| 206|ROUTE|GENAS | None | 0 | 1 |
| 207|AVENUE|LACASSAGNE | None | 0 | 1 |
| 25|RUE|EGLISE | None | 0 | 1 |
| 3|RUE|ALFRED DE VIGNY | None | 0 | 1 |
| 31|RUE|COIGNET | None | 0 | 1 |
| 31|RUE|CYRANO | None | 0 | 1 |
| 33B|RUE|FERDINAND BUISSON | None | 0 | 1 |
| 41|RUE|BONNAND | None | 0 | 1 |
| 44B|RUE|FEUILLAT | None | 0 | 1 |
| 49|RUE|LOUIS | None | 0 | 1 |
| 5|IMPASSE|MOREL | None | 0 | 1 |
| 5|RUE|JEANNE D ARC | None | 0 | 1 |
| 5|RUE|RENE ET MARGUERITE PELLET | None | 0 | 1 |
| 57|COURS|DOCTEUR LONG | None | 0 | 1 |
| 6|RUE|JEANNE D ARC | None | 0 | 1 |
| 64|RUE|FERDINAND BUISSON | None | 0 | 1 |
| 80|COURS|DOCTEUR LONG | None | 0 | 1 |
| 96|ROUTE|GENAS | None | 0 | 1 |

## 6. Candidat KV + scripts + commande POST

- Candidat : `data/_kv_assign_montchat.D.candidate.json` (381 entrees = 103 B2a + 278 D).
- Backup+diff : `scripts/_D_backup_diff_montchat.py` (GET prod -> backup -> safety diff +278/0/0).
- POST anti-drift : `scripts/_D_post_montchat.py` (GET==backup -> POST -> re-GET verify -> miroir).

**Commande POST (Yann, session PowerShell avec JWT)** :
```powershell
. scripts\load_jwt.ps1
python scripts\_D_backup_diff_montchat.py
python scripts\_D_post_montchat.py
```

*Aucun POST, aucun commit dans cette manche (DRY-RUN).*
