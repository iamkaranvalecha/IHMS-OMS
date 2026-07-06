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
