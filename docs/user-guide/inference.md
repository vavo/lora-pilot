# Inference

LoRA Pilot gives you two inference engines out of the box: ComfyUI for graph-based control and InvokeAI for faster day-to-day generation. Both share the same workspace models and write outputs to persistent storage.

## 🎯 Pick Your Engine

| Engine | Best for | URL | Output Path |
|---|---|---|---|
| ComfyUI | Custom workflows, node-level control, automation | `http://localhost:5555` | `/workspace/outputs/comfy` |
| InvokeAI | Simpler UI-driven generation and iteration | `http://localhost:9090` | `/workspace/outputs/invoke` |

Control hub:
- **ControlPilot**: `http://localhost:7878`

## 🚀 Quick Start

1. Open ControlPilot -> `Services`.
2. Confirm `comfy` and `invoke` are running.
3. Download/checkpoint assets from `Models` tab (shared `/workspace/models`).
4. Generate in ComfyUI or InvokeAI.
5. Review results in MediaPilot.

## 🔗 Shared Model and Output Layout

| Resource | Path | Used by |
|---|---|---|
| Base/LoRA/control models | `/workspace/models` | ComfyUI + InvokeAI + trainers |
| ComfyUI outputs | `/workspace/outputs/comfy` | ComfyUI, MediaPilot |
| InvokeAI outputs | `/workspace/outputs/invoke` | InvokeAI, MediaPilot |

This means you do not need to duplicate models per tool.

## 🧩 ComfyUI Workflow (Control-First)

1. Open `ComfyUI` from ControlPilot or go to `http://localhost:5555`.
2. Load checkpoint and (optionally) LoRA in your workflow.
3. Set prompt, negative prompt, sampler, scheduler, steps, CFG.
4. Queue prompt and generate.
5. Validate output in ControlPilot Comfy preview or MediaPilot.

ControlPilot exposes helper endpoints for Comfy:
- `GET /api/comfy/status`
- `GET /api/comfy/latest-image`
- `GET /proxy/comfy/{path}`
- `WS /ws/comfy` (live preview events)

## 🖼️ InvokeAI Workflow (UI-First)

1. Open InvokeAI from `Services` or directly at `http://localhost:9090`.
2. Pick model from shared workspace model pool.
3. Enter prompt/settings and generate.
4. Outputs land in `/workspace/outputs/invoke`.
5. Review/organize in MediaPilot.

## 🔁 Recommended Iteration Loop

1. Explore and prototype quickly in InvokeAI.
2. Move final-quality or automated pipelines to ComfyUI workflows.
3. Curate results in MediaPilot (search, tags, bulk actions).
4. Feed selected images back into datasets (TagPilot) for retraining.

## 🧪 Useful Commands

```bash
# Service status
docker exec lora-pilot supervisorctl status comfy invoke

# Tail logs
docker exec lora-pilot tail -n 200 /workspace/logs/comfy.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.out.log

# Check latest Comfy image via API
curl -s http://localhost:7878/api/comfy/latest-image
```

## 🛠️ Troubleshooting

### ComfyUI or InvokeAI won’t open
- Check supervisor status:
```bash
docker exec lora-pilot supervisorctl status comfy invoke
```
- Verify port mappings in `docker-compose.yml` for `5555` and `9090`.

### Model exists on disk but not visible in UI
- Confirm the file is under `/workspace/models` and readable.
- For InvokeAI, verify `/workspace/apps/invoke/models` resolves to shared models.

### Images generate but don’t appear in MediaPilot
- Verify MediaPilot paths in `/workspace/apps/MediaPilot/.env`:
  - `MEDIAPILOT_OUTPUT_DIR=/workspace/outputs/comfy`
  - `MEDIAPILOT_INVOKEAI_DIR=/workspace/outputs/invoke`

### Generation is slow or OOM
- Reduce resolution, batch size, or steps.
- Use lighter checkpoints for quick iteration.
- Close concurrent heavy services while generating.

## Related

- [ComfyUI](../components/comfyui.md)
- [InvokeAI](../components/invokeai.md)
- [MediaPilot](../components/mediapilot.md)
- [Model Management](model-management.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
