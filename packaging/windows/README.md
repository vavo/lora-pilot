# Windows WSL Packaging

This directory holds the Windows-facing packaging layer for LoRA Pilot.

## What lives here

- `build-runtime-artifacts.sh`: builds the Linux image, exports the WSL fresh-install rootfs bundle, exports the in-place upgrade overlay, and writes `windows-runtime-manifest.json`.
- `LoRAPilotSetup.iss`: Inno Setup bootstrapper definition.
- `build-installer.ps1`: Windows CI entrypoint that builds the launcher and compiles the installer.

## Local workflow from macOS

You can implement and review everything from macOS, but do not trust a Mac to validate Windows install behavior. That would be adorable, not useful.

Typical local steps:

```bash
git worktree add ../lora-pilot-windows -b feat/windows-wsl-installer origin/main
cd ../lora-pilot-windows
make runtime-artifacts
```

The `runtime-artifacts` target writes:

- `dist/windows-runtime/lora-pilot-wsl-rootfs-<version>.tar.zst`
- `dist/windows-runtime/lora-pilot-wsl-overlay-<version>.tar.zst`
- `dist/windows-runtime/windows-runtime-manifest.json`

## Release expectations

- Linux CI is responsible for publishing runtime artifacts.
- Branch and PR pushes keep runtime bundles as workflow artifacts for smoke tests.
- Windows CI is responsible for building `LoRAPilotLauncher.exe` and `LoRAPilotSetup.exe`.
- Branch installer smoke builds consume the runtime artifact from the matching runtime workflow and validate it behind a local HTTP server on the runner.
- Tagged releases still wait for public manifest and runtime URLs before publishing the installer.
- End-to-end installer validation runs only on a self-hosted Windows 11 runner with WSL persistence. GitHub-hosted Windows runners are fine for compilation, not for pretending reboot-sensitive installer QA is solved.
