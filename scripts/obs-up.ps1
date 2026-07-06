# Start mock stack with Prometheus observability profile.
param(
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: obs-up.ps1"
    exit 0
}

& "$PSScriptRoot\mock-stack.ps1" -Check
Invoke-DockerCompose --profile obs up --build --wait

Write-Host "==> Stack ready with Prometheus at http://localhost:9090"
