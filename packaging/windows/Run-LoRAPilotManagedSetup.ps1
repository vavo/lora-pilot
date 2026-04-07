param(
    [string]$LauncherPath = "",
    [string]$ManifestUrl = "",
    [string]$ProgressPath = "",
    [string]$WebsiteUrl = "https://lorapilot.com",
    [switch]$Resume,
    [switch]$Launch
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

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

function Resolve-ProgressPath {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return $ExplicitPath
    }

    return "$env:LOCALAPPDATA\LoRAPilot\install-progress.json"
}

function Read-ProgressState {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        return Get-Content $Path -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Set-ProgressVisual {
    param(
        [System.Windows.Forms.ProgressBar]$ProgressBar,
        [System.Windows.Forms.Label]$MessageLabel,
        [System.Windows.Forms.Label]$DetailLabel,
        [System.Windows.Forms.Label]$PercentLabel,
        [object]$State
    )

    if ($null -eq $State) {
        $MessageLabel.Text = "Preparing LoRA Pilot setup..."
        $DetailLabel.Text = "First install can take several minutes."
        $PercentLabel.Text = ""
        $ProgressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
        $ProgressBar.MarqueeAnimationSpeed = 24
        return
    }

    $MessageLabel.Text = if ($State.message) { [string]$State.message } else { "Preparing LoRA Pilot setup..." }
    $DetailLabel.Text = if ($State.error) { [string]$State.error } elseif ($State.detail) { [string]$State.detail } else { " " }

    if ($State.indeterminate) {
        $ProgressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
        $ProgressBar.MarqueeAnimationSpeed = 24
        $PercentLabel.Text = ""
        return
    }

    $ProgressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
    $ProgressBar.MarqueeAnimationSpeed = 0

    $value = 0
    if ($State.percent -is [int] -or $State.percent -is [long] -or $State.percent -is [double]) {
        $value = [Math]::Max(0, [Math]::Min(100, [int][Math]::Round([double]$State.percent)))
    }
    $ProgressBar.Value = $value
    $PercentLabel.Text = "$value%"
}

$LauncherPath = Resolve-LauncherPath -ExplicitPath $LauncherPath
$ProgressPath = Resolve-ProgressPath -ExplicitPath $ProgressPath

$arguments = @("setup")
if ($Resume) {
    $arguments += "--resume"
}
if ($Launch) {
    $arguments += "--launch"
}
if (-not [string]::IsNullOrWhiteSpace($ManifestUrl)) {
    $arguments += @("--manifest-url", $ManifestUrl)
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "LoRA Pilot Setup"
$form.StartPosition = "CenterScreen"
$form.ClientSize = New-Object System.Drawing.Size(560, 238)
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.TopMost = $true
$form.BackColor = [System.Drawing.ColorTranslator]::FromHtml("#fff7ef")
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "LoRA Pilot"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 20)
$titleLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#d86459")
$titleLabel.Location = New-Object System.Drawing.Point(24, 20)
$titleLabel.AutoSize = $true
$form.Controls.Add($titleLabel)

$subtitleLabel = New-Object System.Windows.Forms.Label
$subtitleLabel.Text = "Installing the managed WSL runtime"
$subtitleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 11)
$subtitleLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#334155")
$subtitleLabel.Location = New-Object System.Drawing.Point(28, 58)
$subtitleLabel.AutoSize = $true
$form.Controls.Add($subtitleLabel)

$messageLabel = New-Object System.Windows.Forms.Label
$messageLabel.Text = "Preparing LoRA Pilot setup..."
$messageLabel.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 12)
$messageLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#111827")
$messageLabel.Location = New-Object System.Drawing.Point(28, 102)
$messageLabel.Size = New-Object System.Drawing.Size(504, 28)
$form.Controls.Add($messageLabel)

$detailLabel = New-Object System.Windows.Forms.Label
$detailLabel.Text = "First install can take several minutes."
$detailLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$detailLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#475569")
$detailLabel.Location = New-Object System.Drawing.Point(28, 132)
$detailLabel.Size = New-Object System.Drawing.Size(504, 40)
$form.Controls.Add($detailLabel)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(28, 176)
$progressBar.Size = New-Object System.Drawing.Size(430, 16)
$progressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
$progressBar.MarqueeAnimationSpeed = 24
$form.Controls.Add($progressBar)

$percentLabel = New-Object System.Windows.Forms.Label
$percentLabel.Text = ""
$percentLabel.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 10)
$percentLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#111827")
$percentLabel.Location = New-Object System.Drawing.Point(474, 172)
$percentLabel.Size = New-Object System.Drawing.Size(58, 24)
$percentLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleRight
$form.Controls.Add($percentLabel)

$websiteLink = New-Object System.Windows.Forms.LinkLabel
$websiteLink.Text = "lorapilot.com"
$websiteLink.LinkColor = [System.Drawing.ColorTranslator]::FromHtml("#d86459")
$websiteLink.ActiveLinkColor = [System.Drawing.ColorTranslator]::FromHtml("#b24e44")
$websiteLink.VisitedLinkColor = [System.Drawing.ColorTranslator]::FromHtml("#d86459")
$websiteLink.Location = New-Object System.Drawing.Point(28, 204)
$websiteLink.AutoSize = $true
$websiteLink.add_LinkClicked({
    Start-Process $WebsiteUrl | Out-Null
})
$form.Controls.Add($websiteLink)

$noteLabel = New-Object System.Windows.Forms.Label
$noteLabel.Text = "Leave this window open while LoRA Pilot prepares the runtime."
$noteLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$noteLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#64748b")
$noteLabel.Location = New-Object System.Drawing.Point(140, 204)
$noteLabel.Size = New-Object System.Drawing.Size(392, 20)
$form.Controls.Add($noteLabel)

$process = Start-Process -FilePath $LauncherPath -ArgumentList $arguments -PassThru -WindowStyle Hidden

$form.Show()
try {
    while (-not $process.HasExited) {
        $state = Read-ProgressState -Path $ProgressPath
        Set-ProgressVisual -ProgressBar $progressBar -MessageLabel $messageLabel -DetailLabel $detailLabel -PercentLabel $percentLabel -State $state
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 250
    }

    $finalState = Read-ProgressState -Path $ProgressPath
    Set-ProgressVisual -ProgressBar $progressBar -MessageLabel $messageLabel -DetailLabel $detailLabel -PercentLabel $percentLabel -State $finalState
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 200
} finally {
    $form.Close()
    $form.Dispose()
}

exit $process.ExitCode
