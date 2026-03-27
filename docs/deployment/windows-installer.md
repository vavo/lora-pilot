# Windows Installer

This guide documents the WSL-backed Windows installer for LoRA Pilot. The goal is simple: give Windows users a normal `.exe` install flow while keeping the existing Linux runtime intact.

## Delivery Model

- Installer: `LoRAPilotSetup.exe`
- Bootstrapper technology: Inno Setup
- Runtime manager: `LoRAPilotLauncher.exe` written in Go
- Runtime payload: versioned WSL rootfs bundle for fresh install plus an overlay archive for in-place upgrades
- Docker Desktop: explicitly not required

## Runtime Contracts

- Fresh install downloads `windows-runtime-manifest.json`, verifies checksums, decompresses the rootfs bundle, and imports the managed `LoRAPilot` distro.
- Upgrades download the overlay archive and apply it inside the existing distro via `/opt/pilot/wsl-apply-update.sh`.
- Runtime startup always goes through `/opt/pilot/wsl-start.sh`.
- Runtime shutdown always goes through `/opt/pilot/wsl-stop.sh`.
- Health is `GET /healthz` on ControlPilot.

## Launcher Commands

- `install [--resume]`
- `start`
- `stop`
- `status --json`
- `open`
- `uninstall [--purge]`

Local Windows state lives under `%LOCALAPPDATA%\LoRAPilot` and contains:

- `state.json`
- `logs\`
- `downloads\`
- `wsl\LoRAPilot\`

## Build And Release Flow

### Linux runtime workflow

- Build the existing Docker image with runtime metadata baked into `/opt/pilot/runtime/version.json`.
- Export `lora-pilot-wsl-rootfs-<version>.tar.zst`.
- Export `lora-pilot-wsl-overlay-<version>.tar.zst`.
- Generate `windows-runtime-manifest.json` and SHA256 sidecars.
- Upload artifacts and publish them on tagged releases.

### Windows installer workflow

- Run `go test ./...` and build `LoRAPilotLauncher.exe`.
- Compile `LoRAPilotSetup.iss` with Inno Setup.
- Upload `LoRAPilotSetup.exe` and publish it on tagged releases.

### Remote E2E workflow

- Run on a self-hosted Windows 11 runner with working WSL persistence.
- Install silently, start the runtime, verify `http://127.0.0.1:7878/healthz`, stop it, then purge it.
- Treat this as the release gate. Hosted Windows runners are fine for compile smoke, not for reboot-sensitive installer QA theater.

## Current Repo Layout

- Launcher source: `apps/WindowsLauncher/`
- Packaging scripts: `packaging/windows/`
- Linux runtime hooks: `scripts/wsl-start.sh`, `scripts/wsl-stop.sh`, `scripts/wsl-apply-update.sh`
- Runtime artifact builder: `packaging/windows/build-runtime-artifacts.sh`
- CI workflows: `.github/workflows/wsl-runtime-artifacts.yml`, `.github/workflows/windows-installer.yml`, `.github/workflows/windows-e2e.yml`
