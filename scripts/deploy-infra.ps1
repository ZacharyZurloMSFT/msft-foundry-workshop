<#
.SYNOPSIS
    Deploy the RAG workshop infrastructure using Bicep + az CLI.
.DESCRIPTION
    Creates a resource group and deploys infra/main.bicep with the specified
    parameter file. Captures all deployment outputs to .deploy-state/outputs.json
    for the follow-on scripts.
.EXAMPLE
    .\scripts\deploy-infra.ps1
    .\scripts\deploy-infra.ps1 -EnvironmentName dev -Location centralus
#>
[CmdletBinding()]
param(
    [string] $EnvironmentName = 'dev',
    [string] $Location        = 'centralus',
    [string] $ResourceGroup,
    [string] $ParameterFile,
    [string] $PrincipalId,
    [string] $SubscriptionId
)

. $PSScriptRoot\_common.ps1

Require-Command az

if (-not $ResourceGroup) { $ResourceGroup = "rg-$EnvironmentName" }
if (-not $ParameterFile) { $ParameterFile = Join-Path $RepoRoot "infra\parameters\$EnvironmentName.bicepparam" }
if (-not (Test-Path $ParameterFile)) { throw "Parameter file not found: $ParameterFile" }

if ($SubscriptionId) {
    Write-Info "Setting subscription: $SubscriptionId"
    az account set --subscription $SubscriptionId | Out-Null
}

$account = az account show -o json | ConvertFrom-Json
Write-Info "Subscription: $($account.name) ($($account.id))"

if (-not $PrincipalId) {
    Write-Info "Resolving signed-in user principal ID..."
    $PrincipalId = Get-SignedInPrincipalId
}
Write-Info "Principal ID: $PrincipalId"

Write-Info "Ensuring resource group $ResourceGroup in $Location..."
az group create --name $ResourceGroup --location $Location --output none
Write-Ok "Resource group ready."

$deploymentName = "rag-workshop-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))"
Write-Info "Deploying Bicep (this can take 10-20 minutes)..."
Write-Info "  parameters: $ParameterFile"
Write-Info "  deployment: $deploymentName"

$deployJson = az deployment group create `
    --resource-group $ResourceGroup `
    --name $deploymentName `
    --template-file (Join-Path $RepoRoot 'infra\main.bicep') `
    --parameters $ParameterFile `
    --parameters "principalId=$PrincipalId" `
    --output json

if ($LASTEXITCODE -ne 0) { throw "Bicep deployment failed." }

$deploy = $deployJson | ConvertFrom-Json
$outputs = @{}
foreach ($p in $deploy.properties.outputs.PSObject.Properties) {
    $outputs[$p.Name] = $p.Value.value
}
$outputs['resourceGroup']   = $ResourceGroup
$outputs['location']        = $Location
$outputs['environmentName'] = $EnvironmentName
$outputs['subscriptionId']  = $account.id
$outputs['principalId']     = $PrincipalId
$outputs['tenantId']        = $account.tenantId

Save-DeployOutputs $outputs
Write-Ok "Deployment outputs saved to $script:OutputsFile"

Write-Host ""
Write-Ok "Infrastructure deployed."
Write-Host "  ACR:      $($outputs.acrLoginServer)"
Write-Host "  Backend:  https://$($outputs.BACKEND_FQDN)"
Write-Host "  Frontend: https://$($outputs.FRONTEND_FQDN)"
Write-Host ""
Write-Host "Next: .\scripts\build-and-push.ps1"
