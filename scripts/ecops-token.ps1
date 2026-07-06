# Obtain EC-OPS JWT and write ECOPS_BEARER_TOKEN into .env (or print to stdout).
#
# Usage:
#   .\scripts\ecops-token.ps1
#   $env:ECOPS_USERNAME='admin'; $env:ECOPS_PASSWORD='Password1!'; .\scripts\ecops-token.ps1
#   .\scripts\ecops-token.ps1 -Print   # stdout only, do not update .env
param(
    [switch]$Print,
    [switch]$Help,
    [string]$Username,
    [string]$Password
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

Import-DotEnv

if ($Username) { $env:ECOPS_USERNAME = $Username }
if ($Password) { $env:ECOPS_PASSWORD = $Password }

if ($Help) {
    Write-Host "Usage: ecops-token.ps1 [-Print]"
    Write-Host "  Fetches JWT from POST {ECOPS_URL}/auth/token"
    Write-Host "  Env: ECOPS_TOKEN_URL overrides host-side token endpoint"
    Write-Host "  Env: ECOPS_USERNAME, ECOPS_PASSWORD (prompted if unset)"
    exit 0
}

$ecopsUrl = $env:ECOPS_TOKEN_URL
if (-not $ecopsUrl) {
    $port = if ($env:ECOPS_PORT) { $env:ECOPS_PORT } else { "8002" }
    $base = if ($env:ECOPS_BASE_URL) { $env:ECOPS_BASE_URL } else { "http://localhost:$port" }
    $ecopsUrl = Get-HostReachableUrl -Url $base
}

$username = $env:ECOPS_USERNAME
$password = $env:ECOPS_PASSWORD

if (-not $username) {
    $username = Read-Host "EC-OPS username"
}
if (-not $password) {
    $secure = Read-Host "EC-OPS password" -AsSecureString
    $password = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

try {
    Write-Host "==> POST ${ecopsUrl}/auth/token"
    $response = Invoke-RestMethod `
        -Uri "$ecopsUrl/auth/token" `
        -Method Post `
        -ContentType "application/x-www-form-urlencoded" `
        -Body @{ username = $username; password = $password }
}
catch {
    Write-Error "Failed to fetch token from ${ecopsUrl}/auth/token - is EC-OPS running? $_"
    exit 1
}

$token = $response.access_token
if (-not $token) {
    Write-Error "Response did not include access_token"
    exit 1
}

if ($Print) {
    Write-Output $token
    exit 0
}

Set-EnvVar -Key ECOPS_BEARER_TOKEN -Value $token
Set-EnvVar -Key CATALOG_SOURCE -Value ihms
Set-EnvVar -Key CATALOG_FALLBACK_TO_JSON -Value false
$ihmsBase = if ($env:IHMS_BASE_URL) { $env:IHMS_BASE_URL } else { "http://host.docker.internal:5000" }
$ecopsBase = if ($env:ECOPS_BASE_URL) { $env:ECOPS_BASE_URL } else { "http://host.docker.internal:8002" }
Set-EnvVar -Key IHMS_BASE_URL -Value $ihmsBase
Set-EnvVar -Key ECOPS_BASE_URL -Value $ecopsBase

Write-Host "==> ECOPS_BEARER_TOKEN written to .env (CATALOG_SOURCE=ihms)"
