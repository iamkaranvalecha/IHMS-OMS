# Refresh EC-OPS JWT and recreate orchestrator so the new token is injected.
#
# Usage:
#   .\scripts\refresh-ecops-token.ps1 -Username admin -Password 'Password1!'
param(
    [string]$Username,
    [string]$Password,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: refresh-ecops-token.ps1 [-Username name] [-Password pass]"
    Write-Host "  Fetches a new EC-OPS token and force-recreates the orchestrator container."
    exit 0
}

$tokenArgs = @()
if ($Username) { $tokenArgs += @("-Username", $Username) }
if ($Password) { $tokenArgs += @("-Password", $Password) }

& "$PSScriptRoot\ecops-token.ps1" @tokenArgs
Start-RealUpstreamOrchestrator -Detached
Wait-MockStackHealthy
if (Test-OrchestratorEcopsAuth) {
    Write-Host "==> Token refreshed — Place order should work now"
}
else {
    Write-Error "EC-OPS auth still failing after token refresh"
    exit 1
}
