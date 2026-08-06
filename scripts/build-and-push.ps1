<#
.SYNOPSIS
    Build backend + frontend container images with `az acr build` and push to ACR.
.DESCRIPTION
    Uses ACR Tasks so no local Docker is required. Reads ACR name and backend
    FQDN from .deploy-state/outputs.json.
#>
[CmdletBinding()]
param(
    [string] $Tag = 'latest'
)

. $PSScriptRoot\_common.ps1
Require-Command az

$o = Get-DeployOutputs
$acr        = $o.acrName
$backendFqdn = $o.BACKEND_FQDN
if (-not $acr)        { throw "acrName missing from deployment outputs." }
if (-not $backendFqdn) { throw "BACKEND_FQDN missing from deployment outputs." }

$backendCtx  = Join-Path $RepoRoot 'src\backend'
$frontendCtx = Join-Path $RepoRoot 'src\frontend'

Write-Info "Building backend → ${acr}.azurecr.io/backend:$Tag"
az acr build `
    --registry $acr `
    --image "backend:$Tag" `
    --file (Join-Path $backendCtx 'Dockerfile') `
    $backendCtx
if ($LASTEXITCODE -ne 0) { throw "Backend image build failed." }
Write-Ok "Backend image pushed."

$viteBase = "https://$backendFqdn"
Write-Info "Building frontend → ${acr}.azurecr.io/frontend:$Tag (VITE_API_BASE_URL=$viteBase)"
az acr build `
    --registry $acr `
    --image "frontend:$Tag" `
    --file (Join-Path $frontendCtx 'Dockerfile') `
    --build-arg "VITE_API_BASE_URL=$viteBase" `
    $frontendCtx
if ($LASTEXITCODE -ne 0) { throw "Frontend image build failed." }
Write-Ok "Frontend image pushed."

Write-Host ""
Write-Ok "Images ready in ${acr}.azurecr.io"
Write-Host "Next: .\scripts\update-apps.ps1"
