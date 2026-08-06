<#
.SYNOPSIS
    Build backend + frontend container images with `az acr build` and push to ACR.
.DESCRIPTION
    Uses ACR Tasks so no local Docker is required. Reads ACR name and backend
    FQDN from .deploy-state/outputs.json.

    Uses --no-wait + polling so we avoid the well-known Azure CLI on Windows
    UnicodeEncodeError when streaming build logs on a cp1252 console.
#>
[CmdletBinding()]
param(
    [string] $Tag = 'latest',
    [int]    $PollSeconds = 15,
    [int]    $TimeoutMinutes = 20
)

. $PSScriptRoot\_common.ps1
Require-Command az

$o = Get-DeployOutputs
$acr        = $o.acrName
$backendFqdn = $o.BACKEND_FQDN
if (-not $acr)         { throw "acrName missing from deployment outputs." }
if (-not $backendFqdn) { throw "BACKEND_FQDN missing from deployment outputs." }

$backendCtx  = Join-Path $RepoRoot 'src\backend'
$frontendCtx = Join-Path $RepoRoot 'src\frontend'

function Invoke-AcrBuild {
    param(
        [string]   $Image,
        [string]   $ContextDir,
        [string[]] $ExtraArgs = @()
    )
    Write-Info "Queuing ACR build: ${acr}.azurecr.io/$Image ..."
    $args = @(
        'acr','build',
        '--registry', $acr,
        '--image',    $Image,
        '--file',     (Join-Path $ContextDir 'Dockerfile'),
        '--no-wait'
    ) + $ExtraArgs + @($ContextDir)

    # `az acr build --no-wait` emits progress lines on stderr — including the run
    # ID (e.g. "Queued a build with ID: cj7") — and nothing on stdout in some CLI
    # versions. Capture stderr (via 2>&1) and grep the run ID out of the text.
    $captured = & az @args 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Failed to queue ACR build for $Image.`n$captured" }

    $runId = $null
    $m = [regex]::Match($captured, 'Queued a build with ID:\s+(\S+)')
    if ($m.Success) { $runId = $m.Groups[1].Value }
    if (-not $runId) {
        # Fallback: pull the most recent run for the registry
        $runId = az acr task list-runs --registry $acr --top 1 --query "[0].runId" -o tsv 2>$null
    }
    if (-not $runId) { throw "Could not determine ACR run ID.`n$captured" }
    Write-Info "Queued run $runId — polling status every $PollSeconds s..."

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $PollSeconds
        $status = az acr task show-run --registry $acr --run-id $runId --query "status" -o tsv 2>$null
        if (-not $status) { continue }
        Write-Host "  [$runId] $status"
        if ($status -eq 'Succeeded') {
            Write-Ok "$Image build succeeded (run $runId)."
            return
        }
        if ($status -in @('Failed','Canceled','Error','Timeout')) {
            Write-Err "Build $runId ended with status: $status"
            Write-Info "Fetching logs..."
            az acr task logs --registry $acr --run-id $runId 2>&1 | Select-Object -Last 60 | ForEach-Object { Write-Host $_ }
            throw "ACR build failed for $Image (run $runId, status $status)."
        }
    }
    throw "ACR build for $Image timed out after $TimeoutMinutes minutes (run $runId)."
}

Invoke-AcrBuild -Image "backend:$Tag" -ContextDir $backendCtx

$viteBase = "https://$backendFqdn"
Invoke-AcrBuild -Image "frontend:$Tag" -ContextDir $frontendCtx `
    -ExtraArgs @('--build-arg', "VITE_API_BASE_URL=$viteBase")

Write-Host ""
Write-Ok "Images ready in ${acr}.azurecr.io"
Write-Host "Next: .\scripts\update-apps.ps1"
