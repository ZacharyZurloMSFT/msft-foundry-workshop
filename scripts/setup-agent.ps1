<#
.SYNOPSIS
    Create the RAG agent in the Azure AI Foundry project and persist AGENT_ID
    on the backend container app.
#>
[CmdletBinding()] param()

. $PSScriptRoot\_common.ps1
Require-Command python
Require-Command az

$o   = Get-DeployOutputs
$rg  = $o.resourceGroup
$env = $o.environmentName
$backendApp = "ca-backend-$env"

$env:AZURE_AI_PROJECT_ENDPOINT      = $o.AZURE_AI_PROJECT_ENDPOINT
$env:AZURE_OPENAI_CHAT_DEPLOYMENT   = $o.chatDeploymentName
$env:AZURE_SEARCH_INDEX_NAME        = $o.AZURE_SEARCH_INDEX_NAME

Write-Info "Creating Foundry agent against $($o.AZURE_AI_PROJECT_ENDPOINT)"

$backendDir = Join-Path $RepoRoot 'src\backend'
$venvPy = Join-Path $backendDir '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    Push-Location $backendDir
    try {
        python -m venv .venv
        & $venvPy -m pip install --quiet --upgrade pip
        & $venvPy -m pip install --quiet -e .
    } finally { Pop-Location }
}
& $venvPy (Join-Path $RepoRoot 'scripts\setup-agent.py')
if ($LASTEXITCODE -ne 0) { throw "setup-agent.py failed." }

$configPath = Join-Path $backendDir '.agent-config.json'
if (-not (Test-Path $configPath)) { throw ".agent-config.json not written by setup-agent.py." }
$agentId = (Get-Content $configPath -Raw | ConvertFrom-Json).agent_id
if (-not $agentId) { throw "agent_id missing from .agent-config.json." }

Write-Info "Setting AGENT_ID=$agentId on $backendApp"
az containerapp update `
    --name $backendApp `
    --resource-group $rg `
    --set-env-vars "AGENT_ID=$agentId" `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to set AGENT_ID env var." }

Write-Ok "Agent $agentId wired to backend."
Write-Host "Next: .\scripts\seed-documents.ps1  (optional)"
