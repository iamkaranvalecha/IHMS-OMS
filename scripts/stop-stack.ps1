# Stop the IHMS-OMS Docker stack.
param(
    [switch]$Volumes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: stop-stack.ps1 [-Volumes]"
    Write-Host "  Runs docker compose down (add -Volumes to remove named volumes)."
    exit 0
}

$args = @("down", "--remove-orphans")
if ($Volumes) {
    $args += "-v"
}

Write-Host "==> Stopping stack"
Invoke-DockerCompose @args
Write-Host "==> Stack stopped"
