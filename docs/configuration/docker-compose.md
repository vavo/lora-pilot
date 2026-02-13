# Docker Compose

LoRA Pilot ships three Compose variants in the repo. Use the standard file for normal GPU use, dev for source-mounted hacking, and cpu for minimal no-GPU runs.

## Compose Files

| File | Mode | Key Behavior |
|---|---|---|
| `docker-compose.yml` | Standard (GPU) | Uses `runtime: nvidia`, exposes full service ports, includes healthcheck |
| `docker-compose.dev.yml` | Development (GPU) | Source/script mounts, debug env flags, interactive `stdin_open` + `tty` |
| `docker-compose.cpu.yml` | Minimal CPU | No GPU runtime, fewer ports, CPU thread env (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`) |

## Quick Start

```bash
# 1) Create runtime env file
cp .env.example .env

# 2) Start standard stack
docker compose -f docker-compose.yml up -d

# 3) Verify services
docker compose ps
curl -s http://localhost:7878/api/services
```

Variant commands:

```bash
# Development profile
docker compose -f docker-compose.dev.yml up -d

# CPU profile
docker compose -f docker-compose.cpu.yml up -d
```

## Default Exposed Ports

Standard/dev compose expose:
- `7878` ControlPilot
- `8888` Jupyter
- `8443` code-server
- `5555` ComfyUI
- `6666` Kohya
- `9090` InvokeAI
- `4444` Diffusion Pipe / TensorBoard
- `8675` AI Toolkit

CPU compose exposes:
- `7878`, `8888`, `8675`

## Image Selection

Compose files use a prebuilt image by default:

```env
LORA_PILOT_IMAGE=notrius/lora-pilot:latest
```

If you build your own image, point Compose to it by setting `LORA_PILOT_IMAGE` in `.env`.

## Persistent Storage

All variants mount `./workspace:/workspace`.

That single mount holds:
- models: `/workspace/models`
- datasets: `/workspace/datasets`
- outputs: `/workspace/outputs`
- logs: `/workspace/logs`
- runtime config/secrets: `/workspace/config`

## Core Environment Variables

Set these in `.env` before `docker compose up`:

| Variable | Default | Purpose |
|---|---|---|
| `TZ` | `America/New_York` | Container timezone |
| `HF_TOKEN` | empty | Hugging Face auth for gated/private models |
| `SUPERVISOR_ADMIN_PASSWORD` | empty | Supervisor HTTP auth password seed |
| `PORTAL_PORT` | `7878` | ControlPilot port |
| `COMFY_PORT` | `5555` | ComfyUI port |
| `KOHYA_PORT` | `6666` | Kohya port |
| `INVOKE_PORT` | `9090` | InvokeAI port |
| `DIFFPIPE_PORT` | `4444` | Diffusion Pipe / TensorBoard port |
| `AI_TOOLKIT_PORT` | `8675` | AI Toolkit UI port |

GPU-related (standard/dev):
- `NVIDIA_VISIBLE_DEVICES`
- `NVIDIA_DRIVER_CAPABILITIES`

## Operational Commands

```bash
# Start / stop
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml down

# Logs
docker compose -f docker-compose.yml logs -f lora-pilot

# Shell
docker compose -f docker-compose.yml exec lora-pilot bash

# Service state inside container
docker compose -f docker-compose.yml exec lora-pilot supervisorctl status
```

## Common Pitfalls

### GPU compose fails on hosts without NVIDIA runtime
- Use CPU profile:
```bash
docker compose -f docker-compose.cpu.yml up -d
```

### Port conflicts on localhost
- Change mapped ports via `.env` (for example `PORTAL_PORT=8787`) and restart.

### Nothing seems to persist
- Confirm you started from repo root and `./workspace` is mounted.
- Confirm data is written under `/workspace`, not ephemeral paths.

### Healthcheck reports unhealthy
- It checks `http://localhost:${PORTAL_PORT}/api/services` inside the container.
- Validate ControlPilot logs:
```bash
docker compose exec lora-pilot tail -n 200 /workspace/logs/controlpilot.err.log
```

## Related

- [Environment Variables](environment-variables.md)
- [Supervisor](supervisor.md)
- [Custom Setup](custom-setup.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


