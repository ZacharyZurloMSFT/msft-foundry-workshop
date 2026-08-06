<#
.SYNOPSIS
    Create (or update) the Azure AI Search index used by the RAG app.
.DESCRIPTION
    Wraps scripts/create-index.py. Uses the outputs from deploy-infra.ps1 to
    provide the required env vars, and relies on your `az login` credentials
    via DefaultAzureCredential.
#>
[CmdletBinding()] param()

. $PSScriptRoot\_common.ps1
Require-Command python
Require-Command az

$o = Get-DeployOutputs

$env:AZURE_SEARCH_ENDPOINT   = $o.AZURE_SEARCH_ENDPOINT
$env:AZURE_SEARCH_INDEX_NAME = $o.AZURE_SEARCH_INDEX_NAME
$env:AZURE_OPENAI_ENDPOINT   = $o.AZURE_OPENAI_ENDPOINT
$env:AZURE_OPENAI_EMBEDDING_DEPLOYMENT = $o.embeddingDeploymentName

Write-Info "Creating/updating AI Search index '$($o.AZURE_SEARCH_INDEX_NAME)' on $($o.AZURE_SEARCH_ENDPOINT)"

$backendDir = Join-Path $RepoRoot 'src\backend'
Push-Location $backendDir
try {
    if (-not (Test-Path (Join-Path $backendDir '.venv'))) {
        Write-Info "Creating Python venv..."
        python -m venv .venv
    }
    $venvPy = Join-Path $backendDir '.venv\Scripts\python.exe'
    Write-Info "Installing backend dependencies (quiet)..."
    & $venvPy -m pip install --quiet --upgrade pip
    & $venvPy -m pip install --quiet -e .
    & $venvPy (Join-Path $RepoRoot 'scripts\create-index.py')
    if ($LASTEXITCODE -ne 0) { throw "create-index.py failed." }
} finally {
    Pop-Location
}

Write-Ok "Index ready."
Write-Host "Next: .\scripts\setup-agent.ps1"
