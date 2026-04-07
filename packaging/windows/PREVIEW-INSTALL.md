# LoRA Pilot Windows Preview

This is a preview Windows release of LoRA Pilot delivered through a WSL2-backed installer.

It is meant to be testable, not invisible. Expect a few rough edges, especially around first-time WSL setup, SmartScreen, and GPU-specific behavior. The basic install/start path works. That is already more than many preview installers can say with a straight face.

## What This Release Includes

- `LoRAPilotSetup.exe`
- `windows-runtime-manifest.json`
- runtime checksum files
- public runtime bundles hosted on Cloudflare R2 and downloaded during setup

You do not need to manually download the large runtime bundles when using a tagged preview release. The installer fetches them for you.

## Requirements

- Windows 11 or Windows 10 22H2+
- Administrator rights
- WSL2 support enabled or installable on the machine
- roughly 100 GB free disk space if you want enough room for the runtime, models, and workspace data
- a decent internet connection, because the runtime bundle is not small and pretending otherwise would be unserious
- NVIDIA Windows drivers with WSL GPU support if you want GPU acceleration

## Quick Start

1. Download `LoRAPilotSetup.exe` from the GitHub pre-release.
2. Run it as Administrator.
3. Let the installer:
   - check Windows support
   - enable or reuse WSL
   - download the runtime manifest and runtime bundle
   - import the managed `LoRAPilot` WSL distro
   - create Start Menu shortcuts
4. If Windows requires a reboot for WSL setup, reboot and sign in again.
5. Start `LoRA Pilot` from the Start Menu.

ControlPilot should open on `http://127.0.0.1:7878` once the runtime becomes healthy.

## What Gets Installed

- Windows launcher:
  `%LOCALAPPDATA%\Programs\LoRAPilot\LoRAPilotLauncher.exe`
- State, logs, downloads, and managed WSL files:
  `%LOCALAPPDATA%\LoRAPilot`
- Managed WSL distro name:
  `LoRAPilot`
- Distro storage location:
  `%LOCALAPPDATA%\LoRAPilot\wsl\LoRAPilot`

Persistent app data remains inside the distro under `/workspace`.

## Start Menu Entries

- `LoRA Pilot`: starts the runtime and opens ControlPilot
- `Open ControlPilot`: opens the browser if ControlPilot is already running
- `Stop LoRA Pilot`: stops the managed runtime
- `Uninstall LoRA Pilot`: removes the Windows launcher and optionally the managed distro

## Useful Commands

Open an elevated PowerShell and use:

```powershell
$exe = "$env:LOCALAPPDATA\Programs\LoRAPilot\LoRAPilotLauncher.exe"

& $exe status --json
& $exe start
& $exe stop
& $exe open
```

That is much more informative than angrily clicking the same shortcut five times and expecting Windows to develop empathy.

## Troubleshooting

### Installer says WSL needs a reboot

- Reboot Windows.
- Sign back in.
- If setup does not resume automatically, run the installer again as Administrator.

### Installer fails during the WSL import step

Clean stale state and retry:

```powershell
wsl --unregister LoRAPilot
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\LoRAPilot\wsl\LoRAPilot" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:LOCALAPPDATA\LoRAPilot\state.json" -ErrorAction SilentlyContinue
```

Then rerun `LoRAPilotSetup.exe`.

### ControlPilot does not open

Check launcher status:

```powershell
$exe = "$env:LOCALAPPDATA\Programs\LoRAPilot\LoRAPilotLauncher.exe"
& $exe status --json
```

Check launcher logs:

- `%LOCALAPPDATA%\LoRAPilot\logs\launcher.log`

### Windows warns that the installer is suspicious

That is still possible on preview builds, especially before signing and reputation are fully in place. If Windows blocks execution, use the usual SmartScreen “More info” path only if you trust the source of the release.

### Port conflicts

LoRA Pilot expects these localhost ports:

- `7878`
- `8888`
- `8443`
- `5555`
- `6666`
- `4444`
- `9090`
- `8675`
- `7879`

If `7878` is taken, for example:

```powershell
netstat -ano | findstr :7878
```

Stop the conflicting process, then start LoRA Pilot again.

### GPU is missing inside WSL

Run:

```powershell
nvidia-smi
wsl --status
wsl --update
```

If the Windows NVIDIA driver is wrong, LoRA Pilot cannot compensate with optimism.

## Current Limitations

- Preview quality, not GA
- No offline single-file installer
- Windows GPU validation is still thinner than it should be
- Some install/retry edge cases are still being tightened

## If You Are Testing CI Artifacts Instead of a Tagged Preview Release

That is a separate, more annoying path.

Use:

- `LoRAPilotSetup.exe`
- `Install-LoRAPilotPreview.ps1`

The helper script exists for artifact-based smoke tests where the runtime is not published like a normal release yet. If you are using a tagged GitHub pre-release, you should not need it.
