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

# Resolve parameter file:
#   1. Explicit -ParameterFile wins.
#   2. Otherwise use infra\parameters\<EnvironmentName>.bicepparam if it exists.
#   3. Otherwise fall back to infra\parameters\default.bicepparam and override
#      environmentName / location on the command line so any unique env name
#      "just works" without needing to create a new file.
$usingDefaultParamFile = $false
if (-not $ParameterFile) {
    $envParamFile     = Join-Path $RepoRoot "infra\parameters\$EnvironmentName.bicepparam"
    $defaultParamFile = Join-Path $RepoRoot "infra\parameters\default.bicepparam"
    if (Test-Path $envParamFile) {
        $ParameterFile = $envParamFile
    } elseif (Test-Path $defaultParamFile) {
        $ParameterFile = $defaultParamFile
        $usingDefaultParamFile = $true
        Write-Info "No parameter file for '$EnvironmentName'; using default.bicepparam with CLI overrides."
    }
}
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

$deployArgs = @(
    'deployment', 'group', 'create',
    '--resource-group', $ResourceGroup,
    '--name', $deploymentName,
    '--template-file', (Join-Path $RepoRoot 'infra\main.bicep'),
    '--parameters', $ParameterFile,
    '--parameters', "principalId=$PrincipalId"
)
if ($usingDefaultParamFile) {
    # Override the placeholder values in default.bicepparam so the user's
    # unique EnvironmentName / Location drive resource naming.
    $deployArgs += @('--parameters', "environmentName=$EnvironmentName")
    $deployArgs += @('--parameters', "location=$Location")
}
$deployArgs += @('--output', 'json')

$deployJson = az @deployArgs

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
