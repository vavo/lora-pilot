# Windows Installation Guide for LoRA Pilot

LoRA Pilot on Windows is delivered as a native `Setup.exe` that manages a WSL2 distro for the Linux runtime. Docker Desktop is not part of the primary install path anymore. It had its turn.

## Requirements

- Windows 11 or Windows 10 22H2+
- 16 GB RAM minimum, 32 GB recommended for training
- 100 GB+ free disk space
- NVIDIA Windows driver with WSL GPU support if you want GPU acceleration
- Admin rights for the installer, because WSL setup is not a democracy

## Install Flow

1. Download `LoRAPilotSetup.exe` from the GitHub release page.
2. Run the installer as Administrator.
3. Let the bootstrapper:
   - check Windows version, disk space, and WSL availability
   - enable or reuse WSL2
   - download the matching runtime manifest and runtime bundle
   - import the managed `LoRAPilot` distro under `%LOCALAPPDATA%\LoRAPilot\wsl\LoRAPilot`
   - create Start Menu shortcuts
4. If Windows requires a reboot during WSL setup, reboot and rerun the installer or launcher with `install --resume`.
5. Launch `LoRA Pilot` from the Start Menu. ControlPilot opens on `http://localhost:7878` after the runtime becomes healthy.

## What Gets Installed

- Windows launcher binary under `%LOCALAPPDATA%\Programs\LoRAPilot`
- Launcher state and logs under `%LOCALAPPDATA%\LoRAPilot`
- Managed WSL distro named `LoRAPilot`
- Persistent app data inside the distro under `/workspace`

## First Launch Notes

- The launcher waits for `http://127.0.0.1:7878/healthz` before opening the browser.
- The Linux runtime still uses the existing bootstrap + `supervisord` flow.
- Default service ports stay the same: `7878`, `8888`, `8443`, `5555`, `6666`, `4444`, `9090`, `8675`, and `7879`.

## Uninstall Behavior

- Standard uninstall removes the Windows launcher assets and local metadata.
- Full purge also unregisters the `LoRAPilot` WSL distro and removes `%LOCALAPPDATA%\LoRAPilot`.

## Troubleshooting

### WSL setup asked for a reboot

- Reboot Windows.
- Rerun `LoRAPilotSetup.exe` or `LoRAPilotLauncher.exe install --resume`.

### ControlPilot never opens

- Check `%LOCALAPPDATA%\LoRAPilot\logs`.
- Inside WSL, runtime logs are still under `/workspace/logs`.
- Run `LoRAPilotLauncher.exe status --json` to confirm distro presence and health.

### Port `7878` is already in use

```powershell
netstat -ano | findstr :7878
```

Stop the conflicting process, then launch LoRA Pilot again.

### GPU is not available inside WSL

```powershell
nvidia-smi
wsl --status
wsl --update
```

Then relaunch LoRA Pilot. If the Windows driver is wrong, WSL will not save you from yourself.
