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
        4. wait for /health = 200 (backend HTTP is up)
        5. wait for /ready = 200 (KB + agent registered — retries until Foundry
           data-plane RBAC has propagated, typically 5-10 minutes)
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

Write-Info "Waiting for backend /health (HTTP process up)..."
Wait-ForHttpOk -Url "$backendUrl/health" -MaxAttempts 40 -DelaySeconds 15 | Out-Null
Write-Ok "Backend is up. Waiting for KB + agent init (Foundry RBAC propagation, ~5-10 min)..."

# Poll /ready — returns 200 only after the backend has successfully registered
# the KB + agent with Foundry, which requires the data-plane RBAC assignments
# from Bicep to have propagated. The backend retries every 30s in the background.
$readyDeadline = (Get-Date).AddMinutes(25)
$lastMsg = ""
while ((Get-Date) -lt $readyDeadline) {
    try {
        $r = Invoke-WebRequest -Uri "$backendUrl/ready" -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Ok "Backend reports ready — KB + agent are registered with Foundry."
            $lastMsg = ""
            break
        }
    } catch {
        # /ready returns 503 while startup is retrying — that surfaces here as an
        # HttpRequestException. Parse the response body if we can.
        $resp = $_.Exception.Response
        if ($resp) {
            try {
                $stream = $resp.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $body = $reader.ReadToEnd() | ConvertFrom-Json
                $msg = "kb_ready=$($body.kb_ready) agent_ready=$($body.agent_ready)"
                if ($body.last_error) { $msg += " last_error=$($body.last_error.Substring(0, [Math]::Min(80, $body.last_error.Length)))..." }
                if ($msg -ne $lastMsg) { Write-Host "  $msg"; $lastMsg = $msg }
            } catch { }
        }
    }
    Start-Sleep -Seconds 30
}
if ((Get-Date) -ge $readyDeadline) {
    Write-Warn2 "Backend /ready did not flip to 200 within 25 min. Chat may still work — check backend logs."
}

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
