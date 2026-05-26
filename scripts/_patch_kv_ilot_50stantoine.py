"""
Patch KV : 50|RUE|ST ANTOINE -> ilot=7 (etait _ilot='5' dans light, deplacer
vers ilot 7 cote KV pour rejoindre 50B + 52 + 54 ST ANTOINE).

Pattern habituel :
- GET /secteur-assignments/dauphine-lacassagne (etat KV cloud frais)
- Verifier 50|RUE|ST ANTOINE _ilot='5' dans light et ilot 7 contient 50B+54
- Backup _kv_assign_dl.json (local mirror)
- secteurAssign['50|RUE|ST ANTOINE'] = { ilot: 7 } (int comme parseInt UI)
- POST back, persist local _kv_assign_dl.json
"""
import json, os, sys, shutil, urllib.request, urllib.error
from datetime import datetime

ROOT  = r'C:\Users\Station 5\DPE-PROSPECTOR\data'
LIGHT = os.path.join(ROOT, 'secteur_dauphine_lacassagne_light.json')
KV    = os.path.join(ROOT, '_kv_assign_dl.json')

API   = 'https://dpe-prospector-api.yann-bufferne.workers.dev'
AGENCE = 'dauphine-lacassagne'
JWT = os.environ.get("DPE_JWT") or ""
if not JWT:
    sys.exit("  [abort] env var DPE_JWT absente. Set DPE_JWT avant le run.")

TARGET_CLE   = '50|RUE|ST ANTOINE'
TARGET_ILOT  = 7
EXPECTED_ILOT_LIGHT = '5'

def section(t):
    print('\n' + '=' * 78); print(t); print('=' * 78)

def http(method, url, body=None):
    import subprocess, tempfile
    cmd = ['curl.exe', '-sS', '-X', method,
           '-H', f'Authorization: Bearer {JWT}',
           '-H', 'Content-Type: application/json',
           '--max-time', '60', url]
    if body is not None:
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                          delete=False, encoding='utf-8')
        json.dump(body, tf); tf.close()
        cmd += ['--data-binary', '@' + tf.name]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise RuntimeError(f'curl exit {r.returncode} : {r.stderr[:300]}')
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f'json parse fail. body: {r.stdout[:500]}')

# ============ STEP 1 : pre-checks light ============
section('STEP 1 : verifications pre-patch (light local)')
with open(LIGHT, encoding='utf-8') as f:
    light = json.load(f)
hit = None
for a in light['adresses']:
    if a.get('cle') == TARGET_CLE:
        hit = a; break
if not hit:
    print(f'FAIL : {TARGET_CLE} introuvable dans light')
    sys.exit(2)
print(f'  light[{TARGET_CLE}]._ilot = {hit.get("_ilot")!r}  (attendu {EXPECTED_ILOT_LIGHT!r})')
if str(hit.get('_ilot')) != EXPECTED_ILOT_LIGHT:
    print('FAIL : _ilot light != 5'); sys.exit(2)
print(f'  immat={hit.get("numero_immatriculation")} bgid={hit.get("batiment_groupe_id")}')

ilot7 = [a for a in light['adresses']
         if str(a.get('_ilot') or '') == '7'
         or str(a.get('ilotEffectif') or '') == '7']
voies7 = sorted({a.get('cle') for a in ilot7
                 if 'ST ANTOINE' in (a.get('cle') or '').upper()})
print(f'  ilot 7 (ST ANTOINE) : {voies7}')
need = ['50B|RUE|ST ANTOINE', '54|RUE|ST ANTOINE']
missing = [k for k in need if k not in voies7]
if missing:
    print(f'FAIL : ilot 7 ne contient pas {missing}'); sys.exit(2)
print('  OK : ilot 7 contient deja 50B + 54 ST ANTOINE')

# ============ STEP 2 : GET KV cloud ============
section('STEP 2 : GET KV cloud (etat frais)')
try:
    cur = http('GET', f'{API}/secteur-assignments/{AGENCE}')
except urllib.error.HTTPError as e:
    print(f'FAIL GET : {e.code} {e.read().decode("utf-8", "ignore")[:200]}')
    sys.exit(3)
assignments = cur.get('assignments') or {}
fusions = cur.get('fusions') or {}
noms = cur.get('noms') or {}
print(f'  assignments count cloud : {len(assignments)}')
print(f'  fusions count : {len(fusions)}')
print(f'  noms count    : {len(noms)}')
existing = assignments.get(TARGET_CLE)
print(f'  cloud assignments[{TARGET_CLE}] = {existing!r}')

# Compare with local mirror
with open(KV, encoding='utf-8') as f:
    local = json.load(f)
loc_a = local.get('assignments') or {}
print(f'  local mirror count : {len(loc_a)}')
delta = (set(loc_a.keys()) ^ set(assignments.keys()))
if delta:
    print(f'  WARN : diff cles local/cloud (count={len(delta)}) ex: {list(delta)[:5]}')
else:
    print('  local mirror == cloud (cles)')

# ============ STEP 3 : backup local ============
section('STEP 3 : backup local _kv_assign_dl.json')
bak = KV + '.preilot50sta.bak'
shutil.copy2(KV, bak)
print(f'  backup -> {bak}')

# ============ STEP 4 : PATCH ============
section('STEP 4 : PATCH ilot=7 sur 50|RUE|ST ANTOINE')
entry = dict(existing) if isinstance(existing, dict) else {}
entry['ilot'] = TARGET_ILOT  # int (cohere parseInt UI)
assignments[TARGET_CLE] = entry
print(f'  new assignments[{TARGET_CLE}] = {entry!r}')

# POST
body = {'assignments': assignments, 'fusions': fusions, 'noms': noms}
try:
    rep = http('POST', f'{API}/secteur-assignments/{AGENCE}', body)
except urllib.error.HTTPError as e:
    print(f'FAIL POST : {e.code} {e.read().decode("utf-8", "ignore")[:200]}')
    sys.exit(4)
print(f'  POST response : {rep}')

# ============ STEP 5 : persist local ============
section('STEP 5 : persist local _kv_assign_dl.json')
local['assignments'] = assignments
local['fusions'] = fusions
local['noms'] = noms
with open(KV, 'w', encoding='utf-8') as f:
    json.dump(local, f, ensure_ascii=False, indent=2)
print(f'  written : {KV}')

# ============ STEP 6 : verify GET ============
section('STEP 6 : verification GET KV cloud')
chk = http('GET', f'{API}/secteur-assignments/{AGENCE}')
chk_a = chk.get('assignments') or {}
chk_entry = chk_a.get(TARGET_CLE)
print(f'  cloud assignments[{TARGET_CLE}] = {chk_entry!r}')
if not isinstance(chk_entry, dict) or chk_entry.get('ilot') != TARGET_ILOT:
    print('FAIL : verification cloud KO'); sys.exit(5)
print('  OK : ilot=7 confirme cloud')

print('\n[DONE]')
