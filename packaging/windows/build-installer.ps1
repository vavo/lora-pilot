param(
    [string]$AppVersion = "",
    [string]$ManifestUrl = ""
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $AppVersion) {
    if ($env:GITHUB_REF -like "refs/tags/*") {
        $AppVersion = $env:GITHUB_REF_NAME
    } elseif ($env:GITHUB_SHA) {
        $AppVersion = "sha-$($env:GITHUB_SHA.Substring(0, 12))"
    } else {
        $AppVersion = "dev"
    }
}
if (-not $ManifestUrl) {
    if ($env:GITHUB_REPOSITORY) {
        $releaseTag = $AppVersion
        if ($env:WINDOWS_RUNTIME_RELEASE_TAG) {
            $releaseTag = $env:WINDOWS_RUNTIME_RELEASE_TAG
        }
        $ManifestUrl = "https://github.com/$($env:GITHUB_REPOSITORY)/releases/download/$releaseTag/windows-runtime-manifest.json"
    } elseif ($env:WINDOWS_RUNTIME_MANIFEST_URL) {
        $ManifestUrl = $env:WINDOWS_RUNTIME_MANIFEST_URL
    }
}

$distDir = Join-Path $root "dist\windows-installer"
$inputDir = Join-Path $distDir "input"
$launcherOut = Join-Path $inputDir "LoRAPilotLauncher.exe"
New-Item -ItemType Directory -Force -Path $inputDir | Out-Null

Push-Location (Join-Path $root "apps\WindowsLauncher")
try {
    go mod download
    go test ./...
    go build -o $launcherOut .\cmd\windowslauncher
} finally {
    Pop-Location
}

$iscc = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup compiler not found at $iscc"
}

& $iscc `
    "/DAppVersion=$AppVersion" `
    "/DManifestUrl=$ManifestUrl" `
    "/DLauncherSource=$launcherOut" `
    (Join-Path $PSScriptRoot "LoRAPilotSetup.iss")
