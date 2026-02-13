# Debugging

This page covers practical debugging flows for the current LoRA Pilot runtime.

## Fast Triage

1. Confirm container is running.
2. Check supervisor-managed service states.
3. Inspect the right service log.
4. Hit the relevant API status endpoint.

```bash
docker compose ps
curl -s http://localhost:7878/api/services
docker compose exec lora-pilot supervisorctl status
```

## Log Locations

Supervisor and service logs live under `/workspace/logs`.

| Service | Stdout log | Stderr log |
|---|---|---|
| `controlpilot` | `/workspace/logs/controlpilot.out.log` | `/workspace/logs/controlpilot.err.log` |
| `comfy` | `/workspace/logs/comfy.out.log` | `/workspace/logs/comfy.err.log` |
| `kohya` | `/workspace/logs/kohya.out.log` | `/workspace/logs/kohya.err.log` |
| `diffpipe` | `/workspace/logs/diffpipe.out.log` | `/workspace/logs/diffpipe.err.log` |
| `invoke` | `/workspace/logs/invoke.out.log` | `/workspace/logs/invoke.err.log` |
| `jupyter` | `/workspace/logs/jupyter.out.log` | `/workspace/logs/jupyter.err.log` |
| `code-server` | `/workspace/logs/code-server.out.log` | `/workspace/logs/code-server.err.log` |
| `ai-toolkit` | `/workspace/logs/ai-toolkit.out.log` | `/workspace/logs/ai-toolkit.err.log` |
| `copilot` | `/workspace/logs/copilot.out.log` | `/workspace/logs/copilot.err.log` |

Supervisor main log:

- `/workspace/logs/supervisord.log`

## Service Control Debugging

```bash
docker compose exec lora-pilot supervisorctl status
docker compose exec lora-pilot supervisorctl restart controlpilot
docker compose exec lora-pilot supervisorctl restart comfy
```

ControlPilot equivalents:

- `GET /api/services`
- `POST /api/services/{name}/{action}`
- `GET /api/services/{name}/log?lines=200`

## Workflow-Specific Debugging

### Models

- Start pull job: `POST /api/models/{name}/pull/start`
- Watch progress: `GET /api/models/{name}/pull/status`
- List recent jobs: `GET /api/models/pulls`

### TrainPilot

- Start: `POST /api/trainpilot/start`
- Stop: `POST /api/trainpilot/stop`
- Combined logs: `GET /api/trainpilot/logs`
- Check missing checkpoint/VAE paths from TOML: `POST /api/trainpilot/model-check`

### Diffusion Pipe

- Validate model paths: `POST /dpipe/train/validate`
- Start/stop: `POST /dpipe/train/start`, `POST /dpipe/train/stop`
- Logs: `GET /dpipe/train/logs`

### MediaPilot

- Check embed/env status: `GET /api/mediapilot/status`
- If unavailable, inspect `controlpilot` logs for mount/load errors.

### Copilot Sidecar

- Through ControlPilot: `GET /api/copilot/status`
- Sidecar direct (internal port): `GET http://127.0.0.1:7879/status`

## GPU Debugging

```bash
docker compose exec lora-pilot nvidia-smi
docker compose exec lora-pilot /opt/pilot/gpu-smoke-test.sh
curl -s http://localhost:7878/api/telemetry
```

If GPU is unavailable, `scripts/comfy.sh` falls back to `--cpu` mode.

## Common Runtime Pitfalls

### Missing or stale secrets

Bootstrap writes `/workspace/config/secrets.env` with generated tokens/passwords. If auth behavior looks wrong, inspect that file first.

### Writable path issues

Most services assume writable `/workspace` paths for cache/config/log/output. Validate mounts and permissions before deeper debugging.

### RunPod shutdown surprises

Shutdown scheduling uses `RUNPOD_*` env to decide stop vs remove behavior. Confirm:

- `RUNPOD_POD_SHUTDOWN`
- `RUNPOD_VOLUME_TYPE`
- `RUNPOD_NETWORK_VOLUME_ID`

## Dev-Mode Debugging

`docker-compose.dev.yml` mounts source and scripts into the container.

Useful pattern:

1. Run dev compose profile.
2. Set `PORTAL_RELOAD=1` (used by `scripts/portal.sh`) for auto-reload in ControlPilot.
3. Tail `controlpilot` logs while reproducing.

## Useful Commands

```bash
docker compose logs -f lora-pilot
docker compose exec lora-pilot tail -n 200 /workspace/logs/controlpilot.err.log
docker compose exec lora-pilot tail -n 200 /workspace/logs/comfy.err.log
docker compose exec lora-pilot tail -n 200 /workspace/logs/invoke.err.log
```

## Related

- [API Reference](api-reference.md)
- [Supervisor](../configuration/supervisor.md)
- [Performance Tuning](../deployment/performance-tuning.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


