# Inference

LoRA Pilot has two inference paths sharing the same model store:
- ComfyUI (`5555`) for workflow control.
- InvokeAI (`9090`) for faster UI-driven iteration.

## Engine Selection

| Engine | Pick it when | URL | Output Path |
|---|---|---|---|
| ComfyUI | You need reusable workflow graphs, node-level control, automation | `http://localhost:5555` | `/workspace/outputs/comfy` |
| InvokeAI | You want fast prompt iteration with less setup | `http://localhost:9090` | `/workspace/outputs/invoke` |

Control hub:
- ControlPilot: `http://localhost:7878`

## Shared Paths (No Duplication Needed)

| Path | Purpose |
|---|---|
| `/workspace/models` | Checkpoints, LoRAs, VAE, and related model assets |
| `/workspace/outputs/comfy` | Comfy generations |
| `/workspace/outputs/invoke` | InvokeAI generations |

## Quick Runbook

1. Confirm services:

```bash
docker exec lora-pilot supervisorctl status comfy invoke
```

2. Confirm model files exist in `/workspace/models`.
3. Generate in chosen engine.
4. Curate in MediaPilot.

## ComfyUI Workflow

1. Open ComfyUI.
2. Load checkpoint/LoRA nodes.
3. Set prompt, negative, sampler, scheduler, steps, CFG.
4. Queue generation.
5. Validate latest image via ControlPilot helper endpoint if needed.

Comfy helper endpoints:
- `GET /api/comfy/status`
- `GET /api/comfy/latest-image`
- `GET /proxy/comfy/{path}`
- `WS /ws/comfy`

Example:

```bash
curl -s http://localhost:7878/api/comfy/status
curl -s http://localhost:7878/api/comfy/latest-image
```

## InvokeAI Workflow

1. Open InvokeAI.
2. Select model (shared `/workspace/models`).
3. Generate and iterate prompt/settings.
4. Review files in `/workspace/outputs/invoke` and MediaPilot.

## Practical Iteration Pattern

1. Explore style/concept rapidly in InvokeAI.
2. Lock final repeatable setup in ComfyUI workflow graph.
3. Review/triage outputs in MediaPilot.
4. Promote good outputs back into datasets for retraining.

## Diagnostics

```bash
# Service logs
docker exec lora-pilot tail -n 200 /workspace/logs/comfy.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/invoke.err.log
```

## Troubleshooting

### UI not reachable
- Check service state (`supervisorctl status comfy invoke`).
- Check Compose port mapping for `5555` and `9090`.

### Model missing in engine UI
- Confirm file location and permissions under `/workspace/models`.
- For InvokeAI, verify shared-model wiring:

```bash
ls -la /workspace/apps/invoke/models
```

### Generated files not visible in MediaPilot
- Verify MediaPilot env points to both output dirs:
  - `MEDIAPILOT_OUTPUT_DIR=/workspace/outputs/comfy`
  - `MEDIAPILOT_INVOKEAI_DIR=/workspace/outputs/invoke`

### OOM or very slow generation
- Lower resolution and steps.
- Use lighter checkpoints for tests.
- Avoid running heavy training jobs concurrently with inference.

## Related

- [ComfyUI](../components/comfyui.md)
- [InvokeAI](../components/invokeai.md)
- [MediaPilot](../components/mediapilot.md)
- [Model Management](model-management.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


