# Start checkout orchestrator + UI against real KB-IHMS (:5000) and EC-OPS (:8002).
#
# Prerequisites (run in sibling repos first — see VS Code tasks or docs/DOCKER.md):
#   KB-IHMS: docker compose up -d          -> http://localhost:5000
#   EC-OPS:  docker compose up -d --build  -> http://localhost:8002
#
# Usage:
#   $env:ECOPS_USERNAME='admin'; $env:ECOPS_PASSWORD='Password1!'; .\scripts\real-upstream.ps1
#   .\scripts\real-upstream.ps1 -Check    # verify upstreams only, do not start
param(
    [switch]$Check,
    [switch]$Detached,
    [switch]$Help,
    [string]$Username,
    [string]$Password
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Username) { $env:ECOPS_USERNAME = $Username }
if ($Password) { $env:ECOPS_PASSWORD = $Password }

if ($Help) {
    Write-Host "Usage: real-upstream.ps1 [-Check] [-Detached] [-Username name] [-Password pass]"
    Write-Host "  Ensures .env for real upstreams, fetches EC-OPS JWT, starts orchestrator + UI."
    exit 0
}

$envPath = Join-Path (Get-RepoRoot) ".env"
if (-not (Test-Path $envPath)) {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Created .env from .env.example"
}

Set-EnvVar -Key CATALOG_SOURCE -Value ihms
Set-EnvVar -Key CATALOG_FALLBACK_TO_JSON -Value false
Set-EnvVar -Key IHMS_BASE_URL -Value "http://host.docker.internal:5000"
Set-EnvVar -Key ECOPS_BASE_URL -Value "http://host.docker.internal:8002"
Set-EnvVar -Key ORCHESTRATOR_PORT -Value 8000
Set-EnvVar -Key UI_PORT -Value 5180
Set-EnvVar -Key ECOPS_MAPPING_PATH -Value "/app/catalog/ecops-mapping.json"

Write-Host "==> Checking KB-IHMS catalog at http://localhost:5000"
$ihmsPath = Test-IhmsCatalogReachable -BaseUrl "http://localhost:5000"
if (-not $ihmsPath) {
    Write-Error "KB-IHMS not reachable on http://localhost:5000 - start it first (see task: Upstreams: Start KB-IHMS + EC-OPS)."
    exit 1
}
Write-Host "    OK: GET http://localhost:5000${ihmsPath}"

Write-Host "==> Checking orchestrator can reach IHMS from Docker (host.docker.internal:5000)"
$null = & docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:8.12.1 `
    -fsS --connect-timeout 3 "http://host.docker.internal:5000${ihmsPath}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "host.docker.internal:5000 not reachable from a test container."
    Write-Warning "Ensure Docker Desktop is running and docker compose extra_hosts includes host.docker.internal."
}

Write-Host "==> Checking EC-OPS at http://localhost:8002/health"
if (-not (Test-UrlReachable -Url "http://localhost:8002/health")) {
    Write-Warning "EC-OPS /health not found - trying /docs"
    if (-not (Test-UrlReachable -Url "http://localhost:8002/docs")) {
        Write-Error "EC-OPS not reachable on http://localhost:8002 - start it first (see task: Upstreams: Start KB-IHMS + EC-OPS)."
        exit 1
    }
}

if ($Check) {
    Write-Host "==> Upstreams OK (-Check)"
    exit 0
}

Write-Host "==> Fetching EC-OPS bearer token into .env"
if ($env:ECOPS_USERNAME -and $env:ECOPS_PASSWORD) {
    & "$PSScriptRoot\ecops-token.ps1" -Username $env:ECOPS_USERNAME -Password $env:ECOPS_PASSWORD
}
else {
    Write-Host "    Set ECOPS_USERNAME and ECOPS_PASSWORD to skip prompts, or enter them now:"
    & "$PSScriptRoot\ecops-token.ps1"
}

Write-Host "==> Starting orchestrator + UI (real upstream mode)"
Write-Host "    Catalog: IHMS GET ${ihmsPath}"
Write-Host "    UI:      http://localhost:5180"
Write-Host "    API:     http://localhost:8000/catalog"
Start-RealUpstreamOrchestrator -Detached:$Detached
if ($Detached) {
    Wait-MockStackHealthy
    Test-OrchestratorEcopsAuth | Out-Null
    Write-StackSummary -Mode "real upstream (background)"
}
