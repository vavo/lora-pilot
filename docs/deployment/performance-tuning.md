# Performance Tuning

This page documents performance controls that are explicitly present in this repository.

## High-Impact Knobs

| Area | Variables / controls | Notes |
|---|---|---|
| Runtime mode | `docker-compose.yml` (GPU), `docker-compose.cpu.yml` (CPU) | CPU compose profile sets `OMP_NUM_THREADS` / `MKL_NUM_THREADS` |
| Diffusion Pipe | `DIFFPIPE_CONFIG`, `DIFFPIPE_NUM_GPUS`, `DIFFPIPE_EXTRA_ARGS`, `DIFFPIPE_TENSORBOARD`, `DIFFPIPE_LOGDIR` | `DIFFPIPE_CONFIG` unset -> TensorBoard-only mode |
| Telemetry overhead | `WORKSPACE_DU_CACHE_SECONDS`, `WORKSPACE_DU_TIMEOUT_SECONDS` | Controls `/api/telemetry` workspace usage cost |
| Telemetry history sampling | `TELEMETRY_HISTORY_SAMPLE_SECONDS`, `TELEMETRY_HISTORY_MAX_SECONDS`, `TELEMETRY_HISTORY_COMPACT_SECONDS` | Controls history granularity/retention |
| HF transfer speed | `HF_HUB_ENABLE_HF_TRANSFER=1`, `HF_XET_HIGH_PERFORMANCE=1` | Set in image env defaults |
| Port-level traffic | `PORTAL_PORT`, `COMFY_PORT`, `KOHYA_PORT`, etc. | Allows isolating/segmenting service access patterns |

## GPU Path

### Verify GPU stack quickly

```bash
/opt/pilot/gpu-smoke-test.sh
```

This script checks:

- torch + CUDA availability
- GPU matmul execution
- `xformers` import

### Compose profile

GPU profile (`docker-compose.yml`) sets:

- `runtime: nvidia`
- `NVIDIA_VISIBLE_DEVICES`
- `NVIDIA_DRIVER_CAPABILITIES`

## CPU-Only Path

Use CPU profile:

```bash
docker compose -f docker-compose.cpu.yml up -d
```

Notes from repo config:

- CPU profile exposes fewer ports by default.
- `OMP_NUM_THREADS` / `MKL_NUM_THREADS` are available for tuning.
- Compose `deploy` resource limits are not enforced in local Docker Compose (commented in file).

## Storage And I/O Strategy

Performance in this stack is mostly I/O-bound once model files grow.

Repository runtime design assumes:

- One persistent `/workspace`
- Shared model root across tools (`/workspace/models`)
- Shared outputs (`/workspace/outputs/*`)

Practical effect:

- Fewer duplicate model copies between Comfy/Invoke/AI Toolkit
- Better warm-cache behavior on repeated runs

## Service-Specific Notes

### ComfyUI

`scripts/comfy.sh`:

- Uses workspace-backed caches (`XDG_*`, `PIP_CACHE_DIR`)
- Auto-switches to `--cpu` when CUDA is unavailable
- Symlinks Comfy model root to `/workspace/models`

### InvokeAI

`scripts/invoke.sh`:

- Uses dedicated invoke venv
- Forces shared model/output directories to workspace paths

### Diffusion Pipe

`scripts/diffusion-pipe.sh`:

- Uses `DIFFPIPE_NUM_GPUS` for DeepSpeed launch
- Exposes optional extra args with `DIFFPIPE_EXTRA_ARGS`
- Exports conservative NCCL defaults (`NCCL_P2P_DISABLE=1`, `NCCL_IB_DISABLE=1`)

### Jupyter

`scripts/start-jupyter.sh` forces runtime dir to `/tmp/jupyter-runtime` to avoid workspace mount permission/path overhead issues.

## Runtime Monitoring

### Container/system level

```bash
docker stats lora-pilot
nvidia-smi
```

### App-level telemetry

```bash
curl -s http://localhost:7878/api/telemetry
curl -s "http://localhost:7878/api/telemetry/history?max_seconds=3600"
```

Use these to monitor:

- CPU/load/memory
- GPU util + VRAM
- Disk usage and workspace data growth

## Quick Tuning Profiles

### Single-GPU cloud node (default)

- Use GPU compose profile
- Set `DIFFPIPE_NUM_GPUS=1`
- Keep `/workspace` on the fastest persistent volume you can allocate

### CPU-only debugging node

- Use `docker-compose.cpu.yml`
- Start with `OMP_NUM_THREADS=4`, `MKL_NUM_THREADS=4`
- Reduce concurrently running services if host is oversubscribed

## Not Found In Repo

- Automated benchmark suite with baseline comparisons
- Built-in autotuner for per-model/per-GPU parameter search
- Provider-specific performance autoscaling policies

## Related

- [Environment Variables](../configuration/environment-variables.md)
- [Docker Compose](../configuration/docker-compose.md)
- [Debugging](../development/debugging.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


