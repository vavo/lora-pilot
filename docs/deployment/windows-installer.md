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
- For branch and PR pushes, keep the runtime bundle as a workflow artifact and let downstream smoke tests consume that artifact directly.

### Windows installer workflow

- For branch and PR pushes, start only after the runtime workflow succeeds, download that workflow artifact, rewrite the manifest to localhost URLs, and validate the bundle behind a local HTTP server on the runner.
- For tagged releases, wait for the public runtime release assets to become reachable.
- Run `go test ./...` and build `LoRAPilotLauncher.exe`.
- Compile `LoRAPilotSetup.iss` with Inno Setup.
- Upload `LoRAPilotSetup.exe`.
- Publish only tagged builds as release assets.
- Use [windows-preview-release-template.md](windows-preview-release-template.md) when cutting a Windows preview tag so the release notes and asset expectations stay consistent.

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
