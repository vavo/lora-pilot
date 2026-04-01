# Windows Preview Installer

This preview build ships the installer and launcher, but the runtime payload still lives in the separate `windows-runtime-artifacts` download because GitHub Actions prefers absurdity over convenience.

## Preview install flow

1. Download and extract both artifacts into the same folder:
   - `windows-installer`
   - `windows-runtime-artifacts`
2. Run `LoRAPilotSetup.exe` as Administrator.
3. Open an elevated PowerShell in that folder and run:

```powershell
.\Install-LoRAPilotPreview.ps1
```

4. If WSL setup required a reboot, rerun:

```powershell
.\Install-LoRAPilotPreview.ps1 -Resume
```

The helper patches `windows-runtime-manifest.json` to local file paths, writes a BOM-free `windows-runtime-manifest.local.json`, and calls `LoRAPilotLauncher.exe install --manifest-url ...` for you.
