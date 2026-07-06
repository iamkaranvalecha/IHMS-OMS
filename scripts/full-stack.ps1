# Start the full IHMS-OMS Docker stack (mock IHMS + mock EC-OPS + orchestrator + UI).
param(
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: full-stack.ps1"
    Write-Host "  Configures mock .env and runs docker compose up --build --wait."
    exit 0
}

& "$PSScriptRoot\mock-stack.ps1" -Check
if (-not $env:ECOPS_READ_TIMEOUT) {
    $env:ECOPS_READ_TIMEOUT = "10"
}

Invoke-DockerCompose up --build --wait

$uiPort = if ($env:UI_PORT) { $env:UI_PORT } else { "5180" }
$apiPort = if ($env:ORCHESTRATOR_PORT) { $env:ORCHESTRATOR_PORT } else { "8000" }

Write-Host ""
Write-Host "==> Stack ready"
Write-Host "    UI:  http://localhost:${uiPort}"
Write-Host "    API: http://localhost:${apiPort}/catalog"
Write-Host "    Trace: curl http://localhost:${apiPort}/health/upstreams"
Write-Host ""
Write-Host "Place order: open UI, add to cart, click Place order"
