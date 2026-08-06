<#
.SYNOPSIS
    Upload the sample .txt files under docs/samples to the RAG backend so they
    get chunked, embedded, and indexed.
.EXAMPLE
    .\scripts\seed-documents.ps1
    .\scripts\seed-documents.ps1 -BackendUrl http://localhost:8000
#>
[CmdletBinding()]
param(
    [string] $BackendUrl,
    [string] $SamplesDir
)

. $PSScriptRoot\_common.ps1

if (-not $BackendUrl) {
    $o = Get-DeployOutputs
    $BackendUrl = "https://$($o.BACKEND_FQDN)"
}
if (-not $SamplesDir) { $SamplesDir = Join-Path $RepoRoot 'docs\samples' }
if (-not (Test-Path $SamplesDir)) { throw "Samples dir not found: $SamplesDir" }

Write-Info "Waiting for backend health at $BackendUrl/health ..."
Wait-ForHttpOk -Url "$BackendUrl/health" -MaxAttempts 30 -DelaySeconds 15 | Out-Null
Write-Ok "Backend healthy."

$files = Get-ChildItem -Path $SamplesDir -Filter *.txt
if (-not $files) { Write-Warn2 "No .txt files in $SamplesDir"; return }

foreach ($f in $files) {
    Write-Host -NoNewline "→ Uploading $($f.Name) ... "
    try {
        $form = @{ file = Get-Item $f.FullName }
        Invoke-RestMethod -Uri "$BackendUrl/api/documents/upload" -Method Post -Form $form -TimeoutSec 60 | Out-Null
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAILED — $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Ok "Seed complete. Try: $BackendUrl/api/documents"
