# Verify orchestrator + UI health and print upstream diagnostics.
param(
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: health-check.ps1"
    exit 0
}

$ports = Get-StackPorts
Wait-MockStackHealthy

Write-Host ""
Write-Host "==> Upstreams"
$upstreams = Invoke-RestMethod "http://localhost:$($ports.Orchestrator)/health/upstreams"
$upstreams | ConvertTo-Json -Depth 6

if ($upstreams.ecops.auth_ok -ne $true) {
    Write-Warning "EC-OPS auth is NOT OK - Place order will fail with 'Invalid or expired credentials'"
    Write-Warning "Run: .\scripts\refresh-ecops-token.ps1 -Username admin -Password 'Password1!'"
}
else {
    Write-Host "==> EC-OPS auth OK"
}

Write-Host ""
Write-Host "==> Catalog (first item)"
$catalog = Invoke-RestMethod "http://localhost:$($ports.Orchestrator)/catalog"
if ($catalog.items -and $catalog.items.Count -gt 0) {
    $catalog.items[0] | ConvertTo-Json -Depth 4
}
else {
    $catalog | ConvertTo-Json -Depth 4
}
