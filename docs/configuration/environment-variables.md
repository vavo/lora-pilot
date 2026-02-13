# Environment Variables

This page documents environment variables currently used by LoRA Pilot runtime scripts, ControlPilot services, Docker Compose files, and Docker image build args.

## High-Impact Quick Reference

If you only care about the knobs that usually matter:

| Area | Variables |
|---|---|
| Container image/runtime | `LORA_PILOT_IMAGE`, `TZ`, `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES` |
| Core ports | `PORTAL_PORT`, `COMFY_PORT`, `KOHYA_PORT`, `INVOKE_PORT`, `DIFFPIPE_PORT`, `AI_TOOLKIT_PORT` |
| Auth/secrets | `HF_TOKEN`, `SUPERVISOR_ADMIN_PASSWORD`, `JUPYTER_TOKEN`, `CODE_SERVER_PASSWORD` |
| Service update controls | `SERVICE_UPDATES_BOOT_RECONCILE`, `SERVICE_UPDATES_CONFIG_PATH`, `SERVICE_UPDATES_ROLLBACK_LOG_PATH` |
| Diffusion Pipe behavior | `DIFFPIPE_CONFIG`, `DIFFPIPE_NUM_GPUS`, `DIFFPIPE_LOGDIR`, `DIFFPIPE_TENSORBOARD` |
| Media/Tag sync behavior | `MEDIAPILOT_SYNC_ON_BOOT`, `MEDIAPILOT_FORCE_ENV_DEFAULTS`, `TAGPILOT_SYNC_ON_BOOT` |

## Inspect Effective Values

```bash
# Show container env (running values)
docker exec lora-pilot env | sort

# Show bootstrapped secrets
docker exec lora-pilot sed -n '1,160p' /workspace/config/secrets.env

# Show MediaPilot app env file (if present)
docker exec lora-pilot sed -n '1,200p' /workspace/apps/MediaPilot/.env
```

## Runtime Config Sources

Runtime values are layered in this order:

1. Docker Compose environment entries (from `.env` and host shell).
2. Defaults from `docker-compose*.yml` and `config/env.defaults`.
3. Bootstrapping in `scripts/bootstrap.sh` (creates `/workspace/config/secrets.env` and sets defaults).
4. Per-service startup scripts (for example `scripts/start-jupyter.sh`, `scripts/comfy.sh`).

Practical implication:
- Same variable can be defined in multiple places.
- Later layers can override earlier defaults.
- Some startup scripts force values regardless of base env defaults.

## Compose/Host Variables

These are read by Compose itself and injected into the container where applicable.

| Variable | Default | Scope |
|---|---|---|
| `LORA_PILOT_IMAGE` | `notrius/lora-pilot:latest` | Compose image tag |
| `LORA_PILOT_CONTAINER_NAME` | `lora-pilot` (`-dev`, `-minimal` in variants) | Compose container name |
| `LORA_PILOT_NETWORK_NAME` | `lora-pilot-network` (`-dev-network`, `-minimal-network` in variants) | Compose network name |
| `TZ` | `America/New_York` in compose, `Etc/UTC` in Dockerfile | Container timezone |
| `NVIDIA_VISIBLE_DEVICES` | `all` | GPU visibility (GPU compose profiles) |
| `NVIDIA_DRIVER_CAPABILITIES` | `compute,utility,display` | GPU driver capabilities |

## Core Runtime Variables

| Variable | Default | Used by |
|---|---|---|
| `WORKSPACE_ROOT` | `/workspace` | bootstrap + service scripts |
| `PORTAL_PORT` | `7878` | ControlPilot (`portal.sh`) |
| `JUPYTER_PORT` | `8888` | Jupyter service |
| `CODE_SERVER_PORT` | `8443` | code-server service |
| `COMFY_PORT` | `5555` | ComfyUI + MediaPilot comfy URL default |
| `KOHYA_PORT` | `6666` | Kohya service |
| `INVOKE_PORT` | `9090` | Invoke service |
| `DIFFPIPE_PORT` | `4444` | Diffusion Pipe / TensorBoard |
| `AI_TOOLKIT_PORT` | `8675` | AI Toolkit UI |
| `AI_TOOLKIT_DB_PATH` | `/workspace/config/ai-toolkit/aitk_db.db` | AI Toolkit sqlite path |
| `HF_TOKEN` | empty | HF downloads + API token persistence |
| `SUPERVISOR_ADMIN_PASSWORD` | random at first boot if not provided | Supervisor HTTP auth |
| `JUPYTER_TOKEN` | random at first boot if not provided | Jupyter auth |
| `CODE_SERVER_PASSWORD` | random at first boot if not provided | stored in `secrets.env` and surfaced by helper tooling |
| `SERVICE_UPDATES_BOOT_RECONCILE` | `1` | boot reconcile toggle |
| `SERVICE_UPDATES_CONFIG_PATH` | `/workspace/config/service-updates.toml` | service update policy file |
| `SERVICE_UPDATES_ROLLBACK_LOG_PATH` | `/workspace/config/service-updates-rollback.jsonl` | service update audit log |
| `UMASK` | `0022` | post-bootstrap umask |

Notes:

- `scripts/bootstrap.sh` writes `JUPYTER_TOKEN`, `CODE_SERVER_PASSWORD`, `SUPERVISOR_ADMIN_PASSWORD`, and optional `HF_TOKEN` into `/workspace/config/secrets.env`.
- If `HF_TOKEN` is empty but legacy `hf_token` exists, bootstrap maps `hf_token -> HF_TOKEN`.

## Service-Specific Runtime Variables

### Jupyter

| Variable | Default | Notes |
|---|---|---|
| `JUPYTER_ALLOW_ORIGIN_PAT` | empty | Appended to RunPod/localhost default allowlist regex |
| `JUPYTER_RUNTIME_DIR` | forced to `/tmp/jupyter-runtime` in `start-jupyter.sh` | Runtime files kept off workspace mount |

Note:
- `start-jupyter.sh` forces `HOME` and XDG paths under `/workspace/home/root` and sets runtime dir to `/tmp/jupyter-runtime`.

### Diffusion Pipe

| Variable | Default | Notes |
|---|---|---|
| `DIFFPIPE_CONFIG` | empty | If unset, service starts TensorBoard only |
| `DIFFPIPE_LOGDIR` | `/workspace/logs/diffusion-pipe` | TensorBoard logdir |
| `DIFFPIPE_NUM_GPUS` | `1` | Passed to `deepspeed --num_gpus` |
| `DIFFPIPE_EXTRA_ARGS` | empty | Appended to training command |
| `DIFFPIPE_TENSORBOARD` | `1` | Starts side TensorBoard when training config is set |
| `NCCL_P2P_DISABLE` | `1` | Exported by script |
| `NCCL_IB_DISABLE` | `1` | Exported by script |

### Invoke

| Variable | Default | Notes |
|---|---|---|
| `INVOKEAI_HOST` | `0.0.0.0` | Exported for invoke runtime |
| `INVOKEAI_PORT` | value of `INVOKE_PORT` | Exported for invoke runtime |

### Copilot Sidecar

| Variable | Default | Notes |
|---|---|---|
| `COPILOT_SIDECAR_PORT` | `7879` | Sidecar bind port (localhost) |
| `COPILOT_SIDECAR_URL` | `http://127.0.0.1:7879` | ControlPilot backend target URL |
| `COPILOT_GITHUB_TOKEN` | empty | Optional token source for sidecar process |
| `COPILOT_HOME` | `/workspace/home/root` | Sidecar HOME |
| `COPILOT_XDG_CONFIG_HOME` | `/workspace/home/root/.config` | Sidecar config root |
| `COPILOT_CWD` | `/workspace` | Default execution cwd |
| `COPILOT_TIMEOUT_SECONDS` | `1800` | Sidecar request timeout |

### code-server Runtime

| Variable | Default | Notes |
|---|---|---|
| `CODE_SERVER_PORT` | `8443` | Bind port |
| `CODE_SERVER_PASSWORD` | generated when missing | Loaded from `/workspace/config/secrets.env` |

Note:
- `start-code-server.sh` uses fixed workspace-backed dirs under `/workspace/code-server/*` and `/workspace/home/root` for state.

### Model Management + ControlPilot Internals

| Variable | Default | Used by |
|---|---|---|
| `MODELS_DIR` | `/workspace/models` | model parser + pull/delete workflows |
| `MODELS_MANIFEST` | `/workspace/config/models.manifest` | model manifest path |
| `DEFAULT_MODELS_MANIFEST` | `/opt/pilot/config/models.manifest.default` | fallback manifest path |
| `SUPERVISOR_CONFIG_PATH` | auto-detected if unset | optional explicit supervisor config path |
| `WORKSPACE_DU_CACHE_SECONDS` | `30` | workspace disk usage cache TTL |
| `WORKSPACE_DU_TIMEOUT_SECONDS` | `2.5` | workspace `du` timeout |
| `TELEMETRY_HISTORY_SAMPLE_SECONDS` | `30` | telemetry sample interval |
| `TELEMETRY_HISTORY_MAX_SECONDS` | `86400` | telemetry retention |
| `TELEMETRY_HISTORY_COMPACT_SECONDS` | `600` | telemetry compaction window |
| `RUNPOD_POD_ID` / `RUNPOD_HOST_ID` | empty | host identity in telemetry |

### Shutdown Behavior (RunPod-aware)

| Variable | Default | Used by |
|---|---|---|
| `RUNPOD_POD_SHUTDOWN` | auto-select | `remove/terminate/delete` or `stop/halt` |
| `RUNPOD_VOLUME_TYPE` | auto-select | helps choose stop vs remove |
| `RUNPOD_NETWORK_VOLUME_ID` | empty | if set, default action becomes `remove` |

### MediaPilot Integration

Bootstrap + ControlPilot normalize MediaPilot env in `/workspace/apps/MediaPilot/.env`.

| Variable | Default/Behavior |
|---|---|
| `MEDIAPILOT_SYNC_ON_BOOT` | `1` (sync workspace app copy when upstream commit differs) |
| `MEDIAPILOT_FORCE_ENV_DEFAULTS` | `0` (if `1`, overwrite key MediaPilot env defaults) |
| `MEDIAPILOT_OUTPUT_DIR` | `/workspace/outputs/comfy` |
| `MEDIAPILOT_INVOKEAI_DIR` | `/workspace/outputs/invoke` |
| `MEDIAPILOT_THUMBS_DIR` | `/workspace/cache/mediapilot/thumbs` |
| `MEDIAPILOT_DB_FILE` | `/workspace/config/mediapilot/data.db` |
| `MEDIAPILOT_COMFY_API_URL` | `http://127.0.0.1:${COMFY_PORT}` |
| `MEDIAPILOT_ALLOW_ORIGINS` | `*` |
| `MEDIAPILOT_ACCESS_PASSWORD` | if placeholder (`changeme`, etc.), ControlPilot clears it |

Additional MediaPilot env keys are defined in `apps/MediaPilot/.env.example` (for example bulk limits, auth cookie flags, and upscale workflow placeholders).

### TagPilot Sync/Standalone

| Variable | Default | Notes |
|---|---|---|
| `TAGPILOT_SYNC_ON_BOOT` | `1` | bootstrap syncs workspace TagPilot copy from bundled source |
| `TAGPILOT_PORT` | `3333` | only used by standalone `scripts/tagpilot.sh` |

### Compose-Variant-Only Variables

| Variable | Default | Where |
|---|---|---|
| `PYTHONUNBUFFERED` | `1` | `docker-compose.dev.yml` |
| `FLASK_ENV` | `development` | `docker-compose.dev.yml` |
| `DEBUG` | `1` | `docker-compose.dev.yml` |
| `OMP_NUM_THREADS` | `4` | `docker-compose.cpu.yml` |
| `MKL_NUM_THREADS` | `4` | `docker-compose.cpu.yml` |

## Build-Time Variables (Dockerfile ARG)

These only affect image build, not runtime container env unless baked into image behavior.

### Component toggles

`INSTALL_GPU_STACK`, `INSTALL_COMFY`, `INSTALL_KOHYA`, `INSTALL_INVOKE`, `INSTALL_DIFFPIPE`, `INSTALL_AI_TOOLKIT`, `INSTALL_AI_TOOLKIT_UI`, `INSTALL_COPILOT_CLI`

### Version/build pins

`COPILOT_CLI_VERSION`, `AI_TOOLKIT_REF`, `AI_TOOLKIT_DIFFUSERS_VERSION`, `TORCH_VERSION`, `TORCHVISION_VERSION`, `TORCHAUDIO_VERSION`, `TORCH_INDEX_URL`, `XFORMERS_VERSION`, `TRANSFORMERS_VERSION`, `PEFT_VERSION`, `INVOKEAI_VERSION`, `INVOKE_TORCH_VERSION`, `INVOKE_TORCHVISION_VERSION`, `INVOKE_TORCHAUDIO_VERSION`, `INVOKE_TORCH_INDEX_URL`, `CUDA_NVCC_PKG`, `CROC_VERSION`

Use `build.env.example` as the source template for build args.

## Minimal `.env` Example

```bash
TZ=America/New_York
PORTAL_PORT=7878
SUPERVISOR_ADMIN_PASSWORD=change_me
HF_TOKEN=
```

## When Changes Take Effect

| Change | Restart service | Recreate container |
|---|---:|---:|
| Update token via API (`/api/hf-token`, `/api/copilot/token`) | usually no | no |
| Edit `service-updates.toml` | no | no |
| Change `.env` port/image/GPU vars | no | yes |
| Change compose environment mappings | no | yes |
| Change script-forced values (for example jupyter runtime behavior) | yes (service) | maybe (if script not mounted) |
| Change Dockerfile build args | no | yes (new image required) |

Typical recreate command:

```bash
docker compose -f docker-compose.yml up -d --force-recreate
```

## Related

- [Docker Compose](docker-compose.md)
- [Models Manifest](models-manifest.md)
- [Supervisor](supervisor.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


