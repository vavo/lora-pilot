# Cloud Platforms

This page documents cloud deployment paths that are explicitly supported by repository code and configuration.

## Supported By Repo Evidence

| Platform path | Status | Evidence |
|---|---|---|
| RunPod | Supported | One-click template URL in `README.md`; RunPod-aware runtime behavior in scripts/services |
| Generic Docker host (cloud VM) | Supported | `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.cpu.yml` |
| Kubernetes/Helm/Terraform modules | Not found in repo | No deployable manifests/modules wired to this app runtime |

## RunPod (Primary Cloud Path)

### 1. Deploy

- Use template: [RunPod template](https://console.runpod.io/deploy?template=gg1utaykxa&ref=o3idfm0n)
- App entrypoint runs bootstrap then supervisor:
  - `/opt/pilot/bootstrap.sh`
  - `/usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf`

### 2. Persist the right storage

Repository behavior assumes durable state under `/workspace`.

Critical persisted paths:

- `/workspace/models`
- `/workspace/datasets`
- `/workspace/outputs`
- `/workspace/config`
- `/workspace/cache`
- `/workspace/logs`

### 3. Optional RunPod-related env

- `HF_TOKEN`
- `SUPERVISOR_ADMIN_PASSWORD`
- `RUNPOD_POD_SHUTDOWN`
- `RUNPOD_VOLUME_TYPE`
- `RUNPOD_NETWORK_VOLUME_ID`

### 4. Access

- ControlPilot on `PORTAL_PORT` (default `7878`)
- Jupyter origin policy already includes RunPod proxy domains by default (`start-jupyter.sh`)

## RunPod-Aware Runtime Behavior

### Shutdown API behavior

`/api/shutdown/schedule` ultimately uses `apps/Portal/services/shutdown.py` logic:

- If `RUNPOD_POD_ID` is set:
  - `RUNPOD_POD_SHUTDOWN=remove|terminate|delete` -> `runpodctl remove pod <id>`
  - `RUNPOD_POD_SHUTDOWN=stop|halt` -> `runpodctl stop pod <id>`
  - Otherwise it derives action from `RUNPOD_VOLUME_TYPE`/`RUNPOD_NETWORK_VOLUME_ID`
- If RunPod command path is unavailable, it falls back to `shutdown -h now`

### Secret compatibility

Bootstrap maps legacy RunPod-style `hf_token` to `HF_TOKEN` when `HF_TOKEN` is not already set.

## Generic Cloud VM Deployment (AWS/GCP/Azure/OCI/etc)

This repo ships a Docker Compose deployment path, not provider-specific orchestration.

Minimal flow:

1. Provision a GPU-capable VM with Docker and NVIDIA runtime.
2. Clone repo and create env file:
   - `cp .env.example .env`
3. Start:
   - `docker compose -f docker-compose.yml up -d`
4. Persist `./workspace` on a durable cloud volume.

## Post-Deploy Verification

```bash
docker compose ps
docker compose logs -f lora-pilot
curl -s http://localhost:7878/api/services
curl -s http://localhost:7878/api/telemetry
```

Expected:

- `api/services` returns service states for supervisor-managed programs.
- `api/telemetry` returns host/memory/disk/GPU payload.

## Not Found In Repo

- First-party Terraform modules for cloud deployment
- Helm chart / Kubernetes manifests integrated with this runtime
- Cloud-specific load balancer / ingress templates tied to LoRA Pilot internals

## Related

- [Configuration](../configuration/README.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Supervisor](../configuration/supervisor.md)
- [Production](production.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


