<#
.SYNOPSIS
    End-to-end deploy: infra → images → apps → wait for backend to self-configure.

.DESCRIPTION
    The backend does the following automatically on startup (from inside the VNet
    using its managed identity):
        - Creates/updates the Azure AI Search index
        - Creates the Foundry RAG agent
        - Auto-seeds sample documents from its baked-in samples/ directory

    That means we cannot (and should not) run create-index.ps1 / setup-agent.ps1
    from a developer machine — AI Search and the Foundry project have
    publicNetworkAccess: Disabled and are only reachable from inside the VNet.

    This orchestrator:
        1. deploy-infra.ps1
        2. build-and-push.ps1
        3. update-apps.ps1
        4. wait for /health = "ok"
    Optional: pass -UploadDocs <folder> to POST additional files to the backend.

.EXAMPLE
    .\scripts\deploy-all.ps1
    .\scripts\deploy-all.ps1 -EnvironmentName dev -Location centralus
    .\scripts\deploy-all.ps1 -UploadDocs C:\customer\docs
#>
[CmdletBinding()]
param(
    [string] $EnvironmentName = 'dev',
    [string] $Location        = 'centralus',
    [string] $SubscriptionId,
    [string] $PrincipalId,
    [string] $UploadDocs
)

. $PSScriptRoot\_common.ps1
Ensure-StateDir

$stopwatch = [Diagnostics.Stopwatch]::StartNew()

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RAG Workshop — full deploy ($EnvironmentName / $Location)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$infraArgs = @{ EnvironmentName = $EnvironmentName; Location = $Location }
if ($SubscriptionId) { $infraArgs['SubscriptionId'] = $SubscriptionId }
if ($PrincipalId)    { $infraArgs['PrincipalId']    = $PrincipalId }

& $PSScriptRoot\deploy-infra.ps1 @infraArgs
& $PSScriptRoot\build-and-push.ps1
& $PSScriptRoot\update-apps.ps1

$o = Get-DeployOutputs
$backendUrl = "https://$($o.BACKEND_FQDN)"

Write-Info "Waiting for backend /health (may take a few minutes for cold-start + index/agent init)..."
Wait-ForHttpOk -Url "$backendUrl/health" -MaxAttempts 40 -DelaySeconds 15 | Out-Null
Write-Ok "Backend is healthy. Index, agent, and sample docs are ready."

Write-Info "Foundry data-plane RBAC (Foundry User) can take 5-10 min to propagate."
Write-Info "If the first chat returns PermissionDenied, wait and retry."

if ($UploadDocs) {
    & $PSScriptRoot\seed-documents.ps1 -BackendUrl $backendUrl -SamplesDir $UploadDocs
}

$stopwatch.Stop()
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Ok "Deploy complete in $($stopwatch.Elapsed.ToString('hh\:mm\:ss'))"
Write-Host "  Frontend: https://$($o.FRONTEND_FQDN)"
Write-Host "  Backend:  $backendUrl"
Write-Host "============================================================" -ForegroundColor Green
