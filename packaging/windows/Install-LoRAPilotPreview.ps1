param(
    [string]$RuntimeDir = "",
    [string]$LauncherPath = "",
    [switch]$Resume
)

$ErrorActionPreference = "Stop"

function Resolve-LauncherPath {
    param([string]$ExplicitPath)

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        $candidates += $ExplicitPath
    }
    $candidates += "$env:LOCALAPPDATA\Programs\LoRAPilot\LoRAPilotLauncher.exe"

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "LoRAPilotLauncher.exe was not found. Run LoRAPilotSetup.exe first or pass -LauncherPath."
}

if ([string]::IsNullOrWhiteSpace($RuntimeDir)) {
    $RuntimeDir = $PSScriptRoot
}

$RuntimeDir = (Resolve-Path $RuntimeDir).Path
$manifestPath = Join-Path $RuntimeDir "windows-runtime-manifest.json"
$patchedManifestPath = Join-Path $RuntimeDir "windows-runtime-manifest.local.json"

if (-not (Test-Path $manifestPath)) {
    throw "windows-runtime-manifest.json was not found in $RuntimeDir"
}

$rootfs = Get-ChildItem $RuntimeDir -Filter "lora-pilot-wsl-rootfs-*.tar.zst" | Select-Object -First 1
$overlay = Get-ChildItem $RuntimeDir -Filter "lora-pilot-wsl-overlay-*.tar.zst" | Select-Object -First 1
if (-not $rootfs) {
    throw "lora-pilot-wsl-rootfs-*.tar.zst was not found in $RuntimeDir"
}
if (-not $overlay) {
    throw "lora-pilot-wsl-overlay-*.tar.zst was not found in $RuntimeDir"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$manifest.fresh_install.url = $rootfs.FullName
$manifest.upgrade_overlay.url = $overlay.FullName

$json = $manifest | ConvertTo-Json -Depth 6
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($patchedManifestPath, $json, $utf8NoBom)

$launcher = Resolve-LauncherPath -ExplicitPath $LauncherPath
$args = @("install")
if ($Resume) {
    $args += "--resume"
}
$args += @("--manifest-url", $patchedManifestPath)

& $launcher @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $launcher status --json
