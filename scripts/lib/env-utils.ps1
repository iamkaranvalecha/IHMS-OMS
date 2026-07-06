# Shared helpers for IHMS-OMS PowerShell scripts (Windows / Docker Desktop).

function Get-RepoRoot {
    (Resolve-Path (Join-Path $PSScriptRoot ".." "..")).Path
}

function Set-EnvVar {
    param(
        [Parameter(Mandatory)]
        [string]$Key,
        [Parameter(Mandatory)]
        [string]$Value,
        [string]$EnvPath = (Join-Path (Get-RepoRoot) ".env")
    )

    if (-not (Test-Path $EnvPath)) {
        New-Item -Path $EnvPath -ItemType File -Force | Out-Null
    }

    $pattern = "^$([regex]::Escape($Key))="
    $line = "${Key}=${Value}"
    $found = $false
    $newContent = @()

    foreach ($row in Get-Content -Path $EnvPath -ErrorAction SilentlyContinue) {
        if ($row -match $pattern) {
            $newContent += $line
            $found = $true
        }
        else {
            $newContent += $row
        }
    }

    if (-not $found) {
        $newContent += $line
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($EnvPath, [string[]]$newContent, $utf8NoBom)
}

function Import-DotEnv {
    param(
        [string]$EnvPath = (Join-Path (Get-RepoRoot) ".env")
    )

    if (-not (Test-Path $EnvPath)) {
        return
    }

    Get-Content $EnvPath | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
            return
        }
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim()
            if ($val -match '^"(.*)"$') {
                $val = $matches[1]
            }
            Set-Item -Path "env:$name" -Value $val
        }
    }
}

function Get-HostReachableUrl {
    param([string]$Url)

    if ($Url -match '^https://host\.docker\.internal(?::\d+)?(.*)$') {
        return "https://localhost$($matches[1])"
    }
    if ($Url -match '^http://host\.docker\.internal(?::\d+)?(.*)$') {
        return "http://localhost$($matches[1])"
    }
    return $Url
}

function Test-UrlReachable {
    param(
        [Parameter(Mandatory)]
        [string]$Url,
        [int]$TimeoutSec = 5
    )

    try {
        $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return $true
    }
    catch {
        return $false
    }
}

function Test-IhmsCatalogReachable {
    param(
        [Parameter(Mandatory)]
        [string]$BaseUrl
    )

    foreach ($path in @("/api/products", "/api/inventory")) {
        if (Test-UrlReachable -Url "${BaseUrl}${path}") {
            return $path
        }
    }
    return $null
}

function Invoke-DockerCompose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    & docker compose @Args
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed (exit $LASTEXITCODE): docker compose $($Args -join ' ')"
    }
}

function Get-StackPorts {
    Import-DotEnv
    [PSCustomObject]@{
        Orchestrator = if ($env:ORCHESTRATOR_PORT) { $env:ORCHESTRATOR_PORT } else { "8000" }
        Ui           = if ($env:UI_PORT) { $env:UI_PORT } else { "5180" }
        Ihms         = if ($env:IHMS_PORT) { $env:IHMS_PORT } else { "8080" }
        Ecops        = if ($env:ECOPS_PORT) { $env:ECOPS_PORT } else { "8012" }
    }
}

function Wait-UrlReady {
    param(
        [Parameter(Mandatory)]
        [string]$Url,
        [string]$Label = $Url,
        [int]$Attempts = 60,
        [int]$DelaySec = 2
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        if (Test-UrlReachable -Url $Url -TimeoutSec 3) {
            Write-Host "==> $Label ready at $Url"
            return
        }
        Start-Sleep -Seconds $DelaySec
    }

    throw "$Label not ready at $Url after $($Attempts * $DelaySec)s"
}

function Wait-MockStackHealthy {
    param([int]$Attempts = 60)

    $ports = Get-StackPorts
    Wait-UrlReady -Url "http://localhost:$($ports.Orchestrator)/health" -Label "orchestrator" -Attempts $Attempts
    Wait-UrlReady -Url "http://localhost:$($ports.Ui)/health" -Label "checkout-ui" -Attempts $Attempts
}

function Wait-RealUpstreamsHealthy {
    param([int]$Attempts = 90)

    $ihmsPath = Test-IhmsCatalogReachable -BaseUrl "http://localhost:5000"
    if (-not $ihmsPath) {
        throw "KB-IHMS not reachable on http://localhost:5000"
    }
    Write-Host "==> KB-IHMS ready at http://localhost:5000$ihmsPath"

    foreach ($url in @("http://localhost:8002/health", "http://localhost:8002/docs")) {
        if (Test-UrlReachable -Url $url) {
            Write-Host "==> EC-OPS ready at $url"
            return
        }
    }
    throw "EC-OPS not reachable on http://localhost:8002"
}

function Open-CheckoutUi {
    $ports = Get-StackPorts
    $url = "http://localhost:$($ports.Ui)"
    Write-Host "==> Opening $url"
    Start-Process $url
}

function Write-StackSummary {
    param([string]$Mode = "mock")

    $ports = Get-StackPorts
    Write-Host ""
    Write-Host "==> Stack ready ($Mode)"
    Write-Host "    UI:  http://localhost:$($ports.Ui)"
    Write-Host "    API: http://localhost:$($ports.Orchestrator)/catalog"
    Write-Host "    Trace: http://localhost:$($ports.Orchestrator)/health/upstreams"
    Write-Host ""
    Write-Host "Place order: open UI, add to cart, click Place order"
}
