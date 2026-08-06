<#
.SYNOPSIS
    Swap placeholder images on the backend and frontend Container Apps for the
    freshly-built ACR images.
#>
[CmdletBinding()]
param(
    [string] $Tag = 'latest'
)

. $PSScriptRoot\_common.ps1
Require-Command az

$o   = Get-DeployOutputs
$rg  = $o.resourceGroup
$env = $o.environmentName
$acrServer = $o.acrLoginServer

$backendApp  = "ca-backend-$env"
$frontendApp = "ca-frontend-$env"

Write-Info "Updating backend container app ($backendApp) → ${acrServer}/backend:$Tag"
az containerapp update `
    --name $backendApp `
    --resource-group $rg `
    --image "$acrServer/backend:$Tag" `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to update backend container app." }
Write-Ok "Backend updated."

Write-Info "Updating frontend container app ($frontendApp) → ${acrServer}/frontend:$Tag"
az containerapp update `
    --name $frontendApp `
    --resource-group $rg `
    --image "$acrServer/frontend:$Tag" `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to update frontend container app." }
Write-Ok "Frontend updated."

Write-Host ""
Write-Host "Backend URL:  https://$($o.BACKEND_FQDN)"
Write-Host "Frontend URL: https://$($o.FRONTEND_FQDN)"
Write-Host ""
Write-Host "Next: .\scripts\create-index.ps1"
