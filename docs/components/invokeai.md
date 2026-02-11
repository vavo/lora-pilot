# InvokeAI

InvokeAI is the second inference engine bundled in LoRA Pilot. It runs as a supervised service and is wired to the shared workspace model tree so it can reuse the same assets as ComfyUI and training tools.

## 🎯 Overview

LoRA Pilot’s InvokeAI integration provides:
- Web UI served on port `9090` (default)
- Shared model directory (`/workspace/models`)
- Shared output directory (`/workspace/outputs/invoke`)
- Supervisor management (`invoke` service)
- Update support through ControlPilot service updates (pip-based)

## 🚀 Access

- **Services tab** in ControlPilot: open `Invoke AI`
- **Direct URL**: `http://localhost:9090`
- **Supervisor service name**: `invoke`
- **Startup script**: `/opt/pilot/invoke.sh`

## 📁 Runtime Layout

| Path | Purpose |
|---|---|
| `/workspace/apps/invoke` | InvokeAI root (`INVOKEAI_ROOT`) |
| `/workspace/models` | Shared model storage used across LoRA Pilot |
| `/workspace/outputs/invoke` | InvokeAI image outputs |
| `/workspace/logs/invoke.out.log` | InvokeAI stdout log |
| `/workspace/logs/invoke.err.log` | InvokeAI stderr log |

Startup behavior in `scripts/invoke.sh`:
- Activates `/opt/venvs/invoke`
- Tries `invokeai-config --root <root> set ModelsDir <shared_models>`
- Tries `invokeai-config --root <root> set OutputDir <shared_output>`
- Falls back to symlinks (`<root>/models` and `<root>/outputs`)
- Launches `invokeai-web --root <root>`

## ⚙️ Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `INVOKE_PORT` | Service port | `9090` |
| `INVOKEAI_HOST` | Bind host for Invoke runtime | `0.0.0.0` |
| `INVOKEAI_PORT` | Runtime port passed to Invoke | value of `INVOKE_PORT` |
| `WORKSPACE_ROOT` | Root for app/models/outputs paths | `/workspace` |

## 🧰 Typical Workflow

1. Download/install models in ControlPilot (`Models` tab) so files land in `/workspace/models`.
2. Open InvokeAI from `Services`.
3. Generate images.
4. Review outputs from:
   - Invoke itself (`/workspace/outputs/invoke`)
   - MediaPilot (`/mediapilot/`), which scans Invoke outputs by default.

## 🔄 Service Operations

```bash
# Status
docker exec lora-pilot supervisorctl status invoke

# Restart
docker exec lora-pilot supervisorctl restart invoke

# Logs
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.err.log
```

## 🛠️ Troubleshooting

### InvokeAI UI does not open
- Verify service is running:
```bash
docker exec lora-pilot supervisorctl status invoke
```
- Check port mapping in `docker-compose.yml` (`${INVOKE_PORT}:${INVOKE_PORT}`).

### Models do not show up in InvokeAI
- Confirm shared path exists:
```bash
ls -la /workspace/models
ls -la /workspace/apps/invoke/models
```
- `apps/invoke/models` should resolve to `/workspace/models` (config or symlink).

### Generated images are missing in MediaPilot
- Verify MediaPilot env points to Invoke outputs:
```bash
grep MEDIAPILOT_INVOKEAI_DIR /workspace/apps/MediaPilot/.env
```
- Expected default: `/workspace/outputs/invoke`.

### Startup errors after version updates
- Recheck logs:
```bash
docker exec lora-pilot tail -n 300 /workspace/logs/invoke.err.log
```
- If needed, restart service and retest.

## Related

- [Inference Guide](../user-guide/inference.md)
- [ComfyUI](comfyui.md)
- [MediaPilot](mediapilot.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
