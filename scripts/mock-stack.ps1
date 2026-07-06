# Start the full mock checkout stack (mock IHMS + mock EC-OPS + orchestrator + UI).
#
# Resets .env to Docker-internal upstream URLs so a real-upstream .env cannot break
# `docker compose up` with "All connection attempts failed" on /catalog.
#
# Usage:
#   .\scripts\mock-stack.ps1
#   .\scripts\mock-stack.ps1 -Check   # write .env only, do not start
param(
    [switch]$Check,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: mock-stack.ps1 [-Check]"
    Write-Host "  Writes mock-stack .env and runs docker compose up --build."
    exit 0
}

Write-Host "==> Configuring .env for mock Docker stack"
Set-EnvVar -Key CATALOG_SOURCE -Value ihms
Set-EnvVar -Key CATALOG_FALLBACK_TO_JSON -Value false
Set-EnvVar -Key IHMS_BASE_URL -Value "http://ihms:8080"
Set-EnvVar -Key ECOPS_BASE_URL -Value "http://ecops:8002"
Set-EnvVar -Key ECOPS_BEARER_TOKEN -Value ""
Set-EnvVar -Key ECOPS_MAPPING_PATH -Value "/app/catalog/ecops-mapping.json"
Set-EnvVar -Key ORCHESTRATOR_PORT -Value 8000
Set-EnvVar -Key UI_PORT -Value 5180

Write-Host "    IHMS_BASE_URL=http://ihms:8080 (mock container)"
Write-Host "    ECOPS_BASE_URL=http://ecops:8002 (mock container)"
Write-Host "    UI: http://localhost:5180"
Write-Host "    API: http://localhost:8000/catalog (expect WIDGET-001 from mock IHMS)"

if ($Check) {
    Write-Host "==> Mock .env written (-Check)"
    exit 0
}

Write-Host "==> Starting full mock stack"
Invoke-DockerCompose up --build
