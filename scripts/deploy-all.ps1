<#
.SYNOPSIS
    End-to-end deploy: infra → images → apps → search index → Foundry agent → sample docs.
.EXAMPLE
    .\scripts\deploy-all.ps1
    .\scripts\deploy-all.ps1 -EnvironmentName dev -Location centralus -SkipSeed
#>
[CmdletBinding()]
param(
    [string] $EnvironmentName = 'dev',
    [string] $Location        = 'centralus',
    [string] $SubscriptionId,
    [string] $PrincipalId,
    [switch] $SkipSeed
)

. $PSScriptRoot\_common.ps1

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
& $PSScriptRoot\create-index.ps1
& $PSScriptRoot\setup-agent.ps1
if (-not $SkipSeed) {
    & $PSScriptRoot\seed-documents.ps1
} else {
    Write-Info "Skipping sample-document seed (-SkipSeed)."
}

$stopwatch.Stop()
$o = Get-DeployOutputs
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Ok "Deploy complete in $($stopwatch.Elapsed.ToString('hh\:mm\:ss'))"
Write-Host "  Frontend: https://$($o.FRONTEND_FQDN)"
Write-Host "  Backend:  https://$($o.BACKEND_FQDN)"
Write-Host "============================================================" -ForegroundColor Green
