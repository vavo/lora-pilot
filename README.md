# LoRA Pilot (lora-pilot)

A Runpod-friendly container base for LoRA training/rendering workflows with a persistent `/workspace` contract.

## What’s in v0
- Ubuntu 22.04 base (CUDA runtime image)
- JupyterLab (port 8888)
- code-server (port 8443)
- Bootstrap that creates:
  - /workspace/models
  - /workspace/datasets
  - /workspace/outputs
  - /workspace/cache
  - /workspace/config

## Build
```bash
docker build -t lora-pilot:dev .
