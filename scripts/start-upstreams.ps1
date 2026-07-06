# Start KB-IHMS and EC-OPS sibling repos in Docker and wait for health.
param(
    [string]$KbIhmsPath = "../KB-IHMS",
    [string]$EcOpsPath = "../EC-OPS",
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\env-utils.ps1"
Set-Location (Get-RepoRoot)

if ($Help) {
    Write-Host "Usage: start-upstreams.ps1 [-KbIhmsPath path] [-EcOpsPath path]"
    exit 0
}

function Start-RepoCompose {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Url
    )

    $resolved = Resolve-Path -Path $Path -ErrorAction SilentlyContinue
    if (-not $resolved) {
        throw "$Name repo not found at $Path - clone it as a sibling folder first."
    }

    Write-Host "==> Starting $Name at $Url"
    Push-Location $resolved.Path
    try {
        Invoke-DockerCompose up -d --build
    }
    finally {
        Pop-Location
    }
}

Start-RepoCompose -Path $KbIhmsPath -Name "KB-IHMS" -Url "http://localhost:5000"
Start-RepoCompose -Path $EcOpsPath -Name "EC-OPS" -Url "http://localhost:8002"
Wait-RealUpstreamsHealthy

Write-Host "==> Real upstreams ready"
