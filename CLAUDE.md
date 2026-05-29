# CLAUDE.md — DPE-PROSPECTOR

> Ce fichier est ton briefing d'entrée. Lis-le en début de session.
> Pour le détail métier/pipeline, va voir `PIPELINE.md`.
> Pour la vue produit, va voir `README.md`.

---

## 1. Le projet en 30 secondes

DPE-PROSPECTOR est un outil de prospection immobilière multi-agences hébergé sur Cloudflare. Il sert 7 agences (5 simples + 2 composites), basées en région parisienne, à Lyon et sur la côte normande. Le projet est piloté par Yann Bufferné, qui n'est pas développeur — toutes les modifications passent par Claude Code en mode dangerous, sur un poste Windows unique (`C:\Users\Station 5\DPE-PROSPECTOR`).

**Trois modes** exposés dans la même SPA (`index.html`), chacun activable par agence via des flags. Toutes les agences n'ont pas accès à tous les modes — voir §3 pour le détail :

- **DPE Prospector** : alertes nouveaux DPE déposés à l'ADEME → emails quotidiens (toutes les agences)
- **SCI Prospector** : prospection propriétaires SCI (matching MAJIC, courriers physiques via MySendingBox) — activé pour **DL, MP et lopez seulement**
- **Secteur Prospector** : cartographie d'un secteur (RNC × BDNB × DVF) — activé pour **DL et MP seulement**

---

## 2. Stack

| Couche | Techno |
|---|---|
| Frontend | SPA monolithique `index.html` (~6600 lignes) + `manifest.json` + `sw.js` (PWA) |
| Backend | Cloudflare Worker `worker.js` (monolithique, ~1590 lignes), routes API multi-agences |
| Persistance | Cloudflare KV (namespace `DPE_KV`), id `87089aeabed3429a92aa9845c0e1c838` |
| Hosting | Cloudflare Pages (frontend) + Workers (API) |
| Pipeline data | Python 3.11, scripts dans `scripts/` (300+ fichiers d'audits/fixes/diagnostics) |
| Emails | Brevo (API key en secret Wrangler) |
| Courriers physiques | MySendingBox (MSB) — clé API stockée en **KV** (`msb_key:{agence}`), pas en secret Wrangler |
| CI/CD | GitHub Actions (`deploy-pages.yml`, `deploy-worker.yml`, `dpe_monitor.yml`, etc.) |

**APIs externes consommées** :
- ADEME : `https://data.ademe.fr/data-fair/api/v1/datasets/meg-83tjwtg8dyz4vv7h1dqe/lines`
- Brevo : `https://api.brevo.com/v3/smtp/email`
- GitHub API : workflows dispatch via route `/map-a0`
- MySendingBox : envoi de courriers physiques

**Sources data utilisées** : ADEME (DPE), DVF, RNC, BDNB, MAJIC.

Pas de `package.json`, pas de NPM. Libs tierces embarquées dans `lib/` (docxtemplater, pizzip, polices, logos).

---

## 3. Les 7 agences

| ID agence | Type | Ville(s) | DPE | SCI | Secteur |
|---|---|---|---|---|---|
| `motte-picquet` | simple | Paris 15e | ✅ | ✅ | ✅ |
| `pernety` | simple | Paris 14e | ✅ | ❌ | ❌ |
| `dauphine-lacassagne` | simple | Lyon (DL) | ✅ | ✅ | ✅ |
| `houlgate` | simple | Houlgate | ✅ | ❌ | ❌ |
| `villers` | simple | Villers-sur-Mer | ✅ | ❌ | ❌ |
| `lopez` | **composite** | Paris 14e & 15e | ✅ | ✅ | ❌ (pas d'accès Secteur, volontaire) |
| `bagot` | **composite** | Houlgate & Villers-sur-Mer | ✅ | ❌ | ❌ |

- `lopez` = `motte-picquet` + `pernety`
- `bagot` = `houlgate` + `villers`

⚠️ **Les composites n'ont pas de fichiers de données dédiés** (pas de `lopez-sci.json`, pas de `bagot.json`). Ils agrègent à la volée les fichiers de leurs sous-agences.

Configuration : `AGENCES_CONFIG` dans `worker.js` (publique, immuable) + KV pour le mutable (conseillers, mots de passe, qualifications).

---

## 4. ⚠️ RÈGLES D'OR — à ne JAMAIS violer

### 4.1 Les agences composites (piège n°1)

**3 mécanismes coexistent dans le code pour gérer les composites**. Avant de coder une route qui filtre par agence, identifie lequel s'applique à ton cas :

1. **`AGENCES_CONFIG[id].dpe_agences` / `sci_agences`** (le plus général) — c'est l'approche par défaut côté worker, utilisée par la majorité des routes (cf. `worker.js` lignes ~109, ~111, ~124, ~126).
2. **`COMPOSITE_AGENCES = { 'lopez': ['motte-picquet', 'pernety'], 'bagot': ['houlgate', 'villers'] }`** — utilisé uniquement par `/msb-backfill` pour l'instant.
3. **Branches hardcodées `if (agenceId === 'lopez') { ... }`** — présentes sur certaines routes (worker.js ~538, ~1047, ~1049).

**Avant de coder une nouvelle route qui filtre par agence :** ouvre la route similaire la plus proche et regarde comment elle gère le cas composite. Ne pas appliquer aveuglément un seul des 3 patterns. Le bug `/msb-backfill` (HTTP 502 sur lopez) venait exactement de l'oubli total de cette gestion.

### 4.2 `dpe_cache.json` est commité dans le repo, PAS dans `.gitignore`

Historique : ce fichier était à un moment dans `.gitignore`, **avec un BOM UTF-8 invisible en début de fichier** qui faisait échouer `git add` silencieusement. Résultat : le cache ne persistait pas entre runs GitHub Actions → tous les DPE des 30 derniers jours étaient envoyés chaque matin. Corrigé en commit `4cc7e163` du 17 mai 2026 (« Fix persistance dpe_cache.json : retrait du .gitignore + commit Git direct »).

**Ne JAMAIS remettre `dpe_cache.json` dans `.gitignore`. Vérifier l'absence de BOM UTF-8 en début de `.gitignore` après toute modification.** Le workflow `dpe_monitor.yml` commite le cache directement après chaque run :
```
git add dpe_cache.json data/*.json
git commit -m "Update cache and data [skip ci]"
git push
```

### 4.3 Pattern de routing dans `worker.js`

Le worker est volontairement monolithique. Pas de refactor en mini-framework sans décision explicite de Yann.

**Pattern à utiliser pour toute nouvelle route** : regex match + check méthode, comme partout ailleurs dans `worker.js` :
```js
const xxxMatch = path.match(/^\/route\/([a-z0-9-]+)$/);
if (xxxMatch && method === 'POST') {
  const agenceId = xxxMatch[1];
  // ...
}
```

Ne PAS utiliser `if (url.pathname.startsWith('/...'))` — ce n'est pas le pattern du worker, ça casserait la cohérence.

### 4.4 Chemins Windows hardcodés : acceptés

Le projet tourne sur un seul poste. Les chemins en dur `C:\Users\Station 5\...` dans certains scripts sont volontaires pour l'instant. Ne pas les généraliser/portabiliser sans demande explicite.

### 4.5 Backups : ne pas supprimer

Plusieurs conventions de backup coexistent, toutes volontaires :
- `.preX.bak` (ex. `.pre106baraban.bak`, `.preDL.bak`) — snapshots avant correctifs Python
- `.backup_*` — autres formats de sauvegarde
- `.bak.json` — variante JSON

Il y en a beaucoup (~165), c'est normal. **Aucun cleanup sans validation explicite.**

### 4.6 Dry-runs avant modification : la norme

Yann demande systématiquement un **dry-run / état des lieux read-only** avant toute modification non triviale. Sur un chantier complexe : déléguer à un subagent Explore qui produit un rapport, valider le plan avec Yann, **puis** modifier. Ne jamais sauter cette étape.

---

## 5. Conventions de code

### Commits Git
Format : `type(scope): message court`
- `feat(msb):`, `feat(secteur):`, `feat(sci):`, `feat(dpe):` — nouvelle fonctionnalité
- `fix(dl):`, `fix(mp):`, `fix(scan):` — correctif
- `chore(...)`, `refactor(...)` — maintenance
- Ajouter `[skip ci]` quand un commit ne doit pas redéclencher les workflows

Exemples réels : `feat(msb): route POST /msb-backfill/:agence`, `fix(dl): reclasse 27 faux positifs social`

### Nommage de fichiers Python (scripts/)
- `fix_*.py` — correctifs terrain (chirurgicaux, souvent par secteur)
- `_diag_*.py`, `_audit_*.py`, `_scan_*.py` — diagnostic en lecture seule
- `_apply_*.py` — application batch
- `enrich_*.py` — enrichissement MAJIC/SCI
- `patch_*.py`, `_patch_*.py` — correctifs paramétrés

### Nommage de fichiers data
- `{agence}.json` — données DPE
- `{agence}-sci.json` — données SCI
- `secteur_{agence}.json` — secteur "full"
- `secteur_{agence}_light.json` — secteur compacté pour le front (~2MB)
- `_*.json` (préfixe underscore) — caches/dumps internes du pipeline

### Langue
Français dominant (UI, commentaires métier, docstrings, commits). Anglais toléré pour les helpers techniques génériques.

---

## 6. Workflow de travail (humain ↔ Claude Code ↔ Claude.ai)

- **Claude.ai (cette conversation, projet "DPE-PROSPECTOR")** : architecte/stratège. Décide quoi faire, fournit des prompts précis, valide les choix.
- **Claude Code (sur le poste de Yann)** : exécute. Lit/modifie les fichiers, commite, pushe.
- **Yann** : décide, valide, fait le ping-pong entre les deux.

**Pour les chantiers complexes, privilégier le pattern "subagent decomposition"** : Claude Code délègue à un agent Explore en read-only pour faire l'état des lieux avant toute modification, puis dispatche d'autres subagents pour l'implémentation. Réduit fortement le ping-pong et protège le contexte.

**Règle absolue : dry-run avant toute modif non triviale** (cf. §4.6). Modifier seulement après validation explicite de Yann.

---

## 7. Pièges connus & limitations acceptées

Ces points sont **connus**, **acceptés en l'état**, et ne doivent **pas** être "réparés" sans demande explicite :

- `worker.js` monolithique (pas de modularisation prévue à court terme)
- `index.html` monolithique (~6600 lignes)
- Chemins Windows hardcodés dans plusieurs scripts
- Pas de tests CI (le fichier `test_render_secteur.js` existe mais n'est pas lancé par GitHub Actions)
- Pas de JSON Schema formalisé pour les données
- Scripts `make_light_*.py` hors repo (générés localement à partir de sources DVF/RNC/BDNB brutes que Yann a en local)
- Backups `.preX.bak` / `.backup_*` / `.bak.json` s'accumulent (volontaire, traçabilité)
- Logs/diags/audits intermédiaires conservés dans `data/` (volontaire)
- **Le `!` de Claude Code route en bash, pas en PowerShell.** Pour les commandes Windows-spécifiques (`Out-File`, `Remove-Item`, secrets Wrangler interactifs comme `load_jwt.ps1`), utiliser la session PowerShell directe — pas le `!` depuis Claude Code.
- **Fallback JWT_SECRET silencieux** : `worker.js` ligne ~338 utilise `env.JWT_SECRET || "dev-secret-change-me"`. Si le secret n'est pas configuré en prod, le code ne crashe pas — c'est un piège silencieux à connaître mais accepté.

---

## 8. Sujets à traiter (un jour, pas urgent)

À mentionner si Claude Code les rencontre, mais à **ne pas attaquer sans accord explicite** :

- TTL manquant sur les tokens de reset password (KV `reset:{token}`) — risque sécurité
- UI d'administration des rôles conseiller/admin (route existe, UI manque)
- Activer `test_render_secteur.js` dans un workflow CI
- Documenter le workflow KV prod ↔ local (dumps `_kv_assign_*.json`)
- **Cleanup migration KV `dernierCourrier:` → `dernierCourrierMap:`** : les ~1634 anciennes clés sont à supprimer manuellement plus tard (cf. commit 242df88)

---

## 9. Données sensibles & secrets

**Ne JAMAIS commiter en clair** :
- Valeurs de secrets Wrangler (`BREVO_API_KEY`, `JWT_SECRET`, `PWD_*`, `GH_TOKEN`)
- Clés MSB (stockées en **KV** : `msb_key:{agence}`)
- Mots de passe en clair (toujours hash SHA-256 dans KV `pwd:{agence}`)
- Contenu de `ZONES_JSON` (secret GitHub Actions)

**À noter** : `GH_REPO` n'est **pas un secret** — il est hardcodé dans `worker.js` ligne ~763 : `const GH_REPO = "liquid69006/DPE-PROSPECTOR"` (attention à la casse : `DPE-PROSPECTOR`, pas `dpe-prospector`).

Les secrets se gèrent via :
- Wrangler : `wrangler secret put NOM_DU_SECRET`
- GitHub Actions : Settings → Secrets and variables → Actions
- KV (pour les clés MSB) : via le worker ou `wrangler kv:key put`

---

## 10. Pointeurs vers le reste de la doc

| Fichier | À consulter pour |
|---|---|
| `PIPELINE.md` | Méthodologie pipeline data, patterns de correction terrain (Cambronne, Suffren, Disambig…), décisions rejetées (passe bgid-orphelin) |
| `README.md` | Vue produit, présentation de l'app |
| `data/secteurs.json` | Config pipeline par secteur (chemins, needles, zones géo). **À éditer manuellement** — pas lu par le worker, voulu hors du code de prod |
| `.github/workflows/*.yml` | Détail des workflows de déploiement et cron |

---

## 11. À l'horizon (chantiers planifiés, non commencés)

Ces modules sont prévus mais pas démarrés. Ils s'intégreront dans la stack existante (pas de standalone), priorité ROI :

1. **Scoring Prospector** — scoring unifié cross-data (DPE × SCI × Secteur)
2. **Mandat Prospector** — CRM léger prospection → mandat
3. **Acheteur Prospector** — SCI vendeuses (DVF) → leads acheteurs
4. **Extension Secteur Prospector** aux agences manquantes
5. **Gestion locative interne** — quittancement, arrérés, comptabilité bailleurs (intégrée à DPE-PROSPECTOR)
6. **Intégrations externes** — WhatsApp Business API, Twilio SMS, Google Calendar

Si Claude Code touche à ces sujets sans contexte explicite, **demander confirmation à Yann avant d'avancer**.
