# User Guide

Task-oriented guide for day-to-day LoRA Pilot usage.

## Start Here

1. [ControlPilot](control-pilot.md)  
   Service control, logs, models/datasets UI, system telemetry.
2. [Model Management](model-management.md)  
   Pull/delete models and keep `/workspace/models` clean.
3. [Dataset Preparation](dataset-preparation.md)  
   TagPilot workflow and dataset hygiene.
4. [Training Workflows](training-workflows.md)  
   Train with TrainPilot, Kohya, AI Toolkit, and Diffusion Pipe paths.
5. [Inference](inference.md)  
   ComfyUI and InvokeAI workflows with shared model/output paths.

## Use-Case Shortcuts

- Need to restart a broken service quickly: [ControlPilot](control-pilot.md)
- Need missing model files before training: [Model Management](model-management.md)
- Need to clean captions/tags before training: [Dataset Preparation](dataset-preparation.md)
- Need profile-driven fast training start: [Training Workflows](training-workflows.md)
- Need generation + review loop: [Inference](inference.md)

## Default URLs

- ControlPilot: `http://localhost:7878`
- ComfyUI: `http://localhost:5555`
- Kohya SS: `http://localhost:6666`
- InvokeAI: `http://localhost:9090`
- JupyterLab: `http://localhost:8888`
- code-server: `http://localhost:8443`

## Suggested Workflow

1. Pull required base models.
2. Build/validate dataset.
3. Run first short training pass.
4. Generate in ComfyUI/InvokeAI.
5. Curate outputs and iterate.

## Related

- [Getting Started](../getting-started/README.md)
- [Configuration](../configuration/README.md)
- [Components](../components/README.md)
- [Troubleshooting](../getting-started/troubleshooting.md)

---

_Last updated: 2026-02-11_
