# Shared helpers for the deployment scripts.
# Dot-source from other scripts:  . $PSScriptRoot\_common.ps1

$ErrorActionPreference = 'Stop'

$script:RepoRoot   = Resolve-Path (Join-Path $PSScriptRoot '..')
$script:StateDir   = Join-Path $RepoRoot '.deploy-state'
$script:OutputsFile = Join-Path $StateDir 'outputs.json'

function Ensure-StateDir {
    if (-not (Test-Path $script:StateDir)) {
        New-Item -ItemType Directory -Path $script:StateDir -Force | Out-Null
    }
}

function Write-Info    ($msg) { Write-Host "→ $msg" -ForegroundColor Cyan }
function Write-Ok      ($msg) { Write-Host "✔ $msg" -ForegroundColor Green }
function Write-Warn2   ($msg) { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Err     ($msg) { Write-Host "✖ $msg" -ForegroundColor Red }

function Require-Command ($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Required command '$name' not found on PATH."
    }
}

function Get-DeployOutputs {
    if (-not (Test-Path $script:OutputsFile)) {
        throw "Deployment outputs not found at $($script:OutputsFile). Run scripts\deploy-infra.ps1 first."
    }
    return Get-Content $script:OutputsFile -Raw | ConvertFrom-Json
}

function Save-DeployOutputs ($obj) {
    Ensure-StateDir
    $obj | ConvertTo-Json -Depth 20 | Set-Content -Path $script:OutputsFile -Encoding UTF8
}

function Get-SignedInPrincipalId {
    return (az ad signed-in-user show --query id -o tsv)
}

function Wait-ForHttpOk {
    param(
        [Parameter(Mandatory)] [string] $Url,
        [int] $MaxAttempts = 30,
        [int] $DelaySeconds = 15
    )
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $r }
        } catch { }
        Write-Host "  attempt $i/$MaxAttempts — not ready, waiting $DelaySeconds s..."
        Start-Sleep -Seconds $DelaySeconds
    }
    throw "Timed out waiting for $Url"
}
