# Windows Preview Release Template

Use this when publishing a Windows preview build from the `feat/windows-wsl-installer` branch or any later Windows preview branch.

## Suggested Tag Format

- `v0.1.0-preview.1`
- `v0.1.0-beta.1`
- `v0.1.0-rc.1`

Tags containing `preview`, `alpha`, `beta`, or `rc` are published as GitHub pre-releases by the current workflows.

## Publish Commands

```bash
git -C /Users/vavo/DEV/lora-pilot-windows status
git -C /Users/vavo/DEV/lora-pilot-windows tag -a v0.1.0-preview.1 -m "Windows preview 1"
git -C /Users/vavo/DEV/lora-pilot-windows push origin v0.1.0-preview.1
```

## Expected Release Assets

- `LoRAPilotSetup.exe`
- `windows-runtime-manifest.json`
- `*.sha256`

The actual runtime bundles are expected to live behind the public URLs embedded in `windows-runtime-manifest.json`, typically on Cloudflare R2 via `r2.dev` or a custom domain. GitHub Releases is not a 20 GB object store no matter how politely you ask.

## Copy/Paste Release Notes

```md
## Windows Preview

This is a Windows preview build of LoRA Pilot delivered through a WSL-backed installer.

### Included

- `LoRAPilotSetup.exe`
- Windows runtime manifest
- Cloudflare-hosted WSL rootfs bundle for fresh installs
- Cloudflare-hosted WSL overlay bundle for runtime updates

### Install Notes

- Run `LoRAPilotSetup.exe` as Administrator.
- If Windows asks for a reboot during WSL setup, reboot and rerun the install flow.
- The installer downloads runtime bundles from the public URLs referenced by `windows-runtime-manifest.json`, not from GitHub release attachments.
- If you downloaded both `windows-installer` and `windows-runtime-artifacts` preview artifacts instead of using a tagged release, run `Install-LoRAPilotPreview.ps1` from an elevated PowerShell after installing.

### Known Limitations

- Preview quality, not GA.
- SmartScreen or Defender warnings are still possible, especially if signing is not configured yet or the publisher reputation is brand new.
- GPU validation on a real NVIDIA-backed Windows machine is still pending.
- Additional installer and lifecycle edge cases are still being tested.

### Tested So Far

- WSL install and reboot-resume
- Runtime import into managed `LoRAPilot` distro
- Launcher `install`, `start`, `stop`, `status`, and `open`
- ControlPilot startup
- ComfyUI startup
- InvokeAI startup

### Feedback Wanted

- Fresh install failures
- WSL setup / reboot edge cases
- Port conflicts
- SmartScreen / Defender behavior
- General launcher reliability
```

## Recommended Release Title

- `LoRA Pilot v0.1.0-preview.1`

## Recommended GitHub Release Settings

- Type: `Pre-release`
- Target: the current Windows preview branch head
- Leave “latest release” disabled for preview tags
