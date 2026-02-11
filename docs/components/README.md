# Components

This section is the map of LoRA Pilot components. Keep this page as an index; use component pages for actual workflows and settings.

## Component Index

| Component | Role | Default Port/Route | Page |
|---|---|---|---|
| Kohya SS | Full training UI | `6666` | [Kohya SS](kohya-ss.md) |
| AI Toolkit | Modern training stack | `8675` | [AI Toolkit](ai-toolkit.md) |
| Diffusion Pipe | Experimental training + TensorBoard | `4444` | [Diffusion Pipe](diffusion-pipe.md) |
| ComfyUI | Node-based inference | `5555` | [ComfyUI](comfyui.md) |
| InvokeAI | UI-first inference | `9090` | [InvokeAI](invokeai.md) |
| TrainPilot | Guided Kohya launcher | ControlPilot tab | [TrainPilot](trainpilot.md) |
| TagPilot | Dataset prep/tagging | `/tagpilot/` on `7878` | [TagPilot](tagpilot.md) |
| MediaPilot | Output curation/gallery | `/mediapilot/` on `7878` | [MediaPilot](mediapilot.md) |
| Copilot Sidecar | Optional coding assistant backend | `7879` (internal/local) | [Copilot Sidecar](copilot-sidecar.md) |

## How They Fit Together

1. Prepare data in TagPilot.
2. Train with TrainPilot/Kohya/AI Toolkit/Diffusion Pipe.
3. Generate in ComfyUI or InvokeAI.
4. Review and curate in MediaPilot.

## Shared Paths

All components are wired to the same workspace:
- `/workspace/models`
- `/workspace/datasets`
- `/workspace/outputs`
- `/workspace/config`
- `/workspace/logs`

## Quick Ops

```bash
# Service state
docker exec lora-pilot supervisorctl status

# Logs
docker exec lora-pilot tail -n 200 /workspace/logs/controlpilot.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/comfy.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.out.log
```

## Related

- [User Guide](../user-guide/README.md)
- [Configuration](../configuration/README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
