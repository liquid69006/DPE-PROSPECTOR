# ============================================================
# load_jwt.ps1 - charge un JWT DPE-PROSPECTOR dans $env:DPE_JWT
# Compatible PowerShell 5.1 (pas de -AsPlainText sur Read-Host).
#
# Sourcer (pour que $env:DPE_JWT persiste dans la session caller) :
#   . scripts\load_jwt.ps1
#
# Etapes :
#  1. Read-Host -AsSecureString le JWT_SECRET (jamais en clair,
#     jamais dans l'historique)
#  2. Converti via [System.Net.NetworkCredential] et pose dans
#     $env:WORKER_JWT_SECRET (transient, efface en etape 5)
#  3. Lance scripts/sign_jwt_dpe.py (lit WORKER_JWT_SECRET) et capture
#     le JWT genere sur stdout. Token patron multi-agences couvrant les
#     5 secteurs : dauphine-lacassagne, motte-picquet, pernety,
#     houlgate, villers (slug racine = dauphine-lacassagne).
#  4. Pose le JWT dans $env:DPE_JWT
#  5. Efface $env:WORKER_JWT_SECRET imperativement (le secret ne traine
#     plus en memoire process)
#  6. Test GET /secteur-assignments/dauphine-lacassagne :
#     affiche "JWT OK" si 200, "JWT KO (xxx)" sinon
#
# Aucun secret ni token n'est jamais ecrit sur disque ni hardcode dans
# ce script. Versionnable sans risque.
# ============================================================

Write-Host "== load_jwt.ps1 =="

# Liste des agences couvertes par le token (slug racine = 1re entree).
# Modifiable ici si besoin (sans toucher au reste du script).
$AgenceRoot = "dauphine-lacassagne"
$AgencesCsv = "dauphine-lacassagne,motte-picquet,pernety,houlgate,villers"

# 1. Saisie SecureString (pas d'echo, pas dans l'historique)
$sec = Read-Host "JWT_SECRET (du wrangler secret put)" -AsSecureString
if (-not $sec) {
    Write-Host "[abort] secret vide" -ForegroundColor Red
    return
}

# 2. Convertir + poser dans WORKER_JWT_SECRET (transient)
$env:WORKER_JWT_SECRET = `
    [System.Net.NetworkCredential]::new('', $sec).Password
Remove-Variable sec -ErrorAction SilentlyContinue

# 3. Signer le JWT via python scripts/sign_jwt_dpe.py
$env:PYTHONUTF8 = "1"
$jwtRaw = python scripts\sign_jwt_dpe.py `
    --agence  $AgenceRoot `
    --agences $AgencesCsv `
    --role    patron
if ($LASTEXITCODE -ne 0) {
    Write-Host "[abort] sign_jwt_dpe.py exit=$LASTEXITCODE" -ForegroundColor Red
    Remove-Item Env:\WORKER_JWT_SECRET -ErrorAction SilentlyContinue
    return
}
$jwt = (@($jwtRaw) -join "").Trim()
if (-not $jwt) {
    Write-Host "[abort] JWT vide" -ForegroundColor Red
    Remove-Item Env:\WORKER_JWT_SECRET -ErrorAction SilentlyContinue
    return
}

# 4. Poser dans DPE_JWT
$env:DPE_JWT = $jwt

# 5. Effacer le secret transient
Remove-Item Env:\WORKER_JWT_SECRET -ErrorAction SilentlyContinue
Write-Host ("[ok] env:DPE_JWT pose (len={0}) ; WORKER_JWT_SECRET efface." `
    -f $env:DPE_JWT.Length)
$AgencesList = $AgencesCsv.Split(",")
Write-Host ("[ok] role=patron  agence={0}  agences=[{1}]  ttl=24h" `
    -f $AgenceRoot, ($AgencesList -join ", "))
Write-Host ("[ok] couverture : {0} secteurs ({1})" `
    -f $AgencesList.Count, ($AgencesList -join " + "))

# 6. Test GET sur le worker
$url = ("https://dpe-prospector-api.yann-bufferne.workers.dev" + `
        "/secteur-assignments/dauphine-lacassagne")
try {
    $h = @{
        Authorization = "Bearer $env:DPE_JWT"
        "User-Agent"  = "Mozilla/5.0"
    }
    $null = Invoke-RestMethod -Uri $url -Headers $h -Method Get `
        -ErrorAction Stop
    Write-Host "JWT OK (200)" -ForegroundColor Green
} catch {
    $code = 0
    if ($_.Exception.Response) {
        $code = $_.Exception.Response.StatusCode.value__
    }
    if ($code -eq 401) {
        Write-Host "JWT KO (401)" -ForegroundColor Red
    } else {
        Write-Host ("JWT KO (status={0}) : {1}" -f $code, $_.Exception.Message) `
            -ForegroundColor Red
    }
}
