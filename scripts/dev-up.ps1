# Start mock stack in the background (detached) and wait for health.
# Best for Cursor/VS Code dev: stack runs while you keep coding.
#
# Usage:
#   .\scripts\dev-up.ps1
#   .\scripts\dev-up.ps1 -OpenUi
param(
    [switch]$OpenUi,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: dev-up.ps1 [-OpenUi]"
    Write-Host "  Configures mock .env, starts docker compose detached, waits for health."
    exit 0
}

& "$PSScriptRoot\mock-stack.ps1" -Check
if (-not $env:ECOPS_READ_TIMEOUT) {
    $env:ECOPS_READ_TIMEOUT = "10"
}

Write-Host "==> Starting mock stack (detached)"
Invoke-DockerCompose up --build --wait -d
Wait-MockStackHealthy
Write-StackSummary -Mode "mock (background)"

if ($OpenUi) {
    Open-CheckoutUi
}
