# File Structure

This page documents both the repository layout and the runtime `/workspace` layout created by bootstrap.

## Repository Layout (Source Tree)

Top-level directories used by LoRA Pilot:

- `apps/`
  - `Portal/` (ControlPilot FastAPI + static UI)
  - `TagPilot/`
  - `MediaPilot/`
  - `TrainPilot/`
  - `CopilotSidecar/`
- `scripts/` (runtime/service entrypoints, bootstrap, helpers)
- `config/` (defaults + model manifests)
- `supervisor/` (`supervisord.conf`)
- `docs/` (documentation source)
- `docker-compose/` + top-level compose files

## Runtime Layout (`/workspace`)

`scripts/bootstrap.sh` creates/maintains these directories:

- `/workspace/apps`
- `/workspace/models`
- `/workspace/datasets`
  - `/workspace/datasets/images`
  - `/workspace/datasets/ZIPs`
- `/workspace/outputs`
  - `/workspace/outputs/comfy`
  - `/workspace/outputs/invoke`
  - `/workspace/outputs/ai-toolkit`
- `/workspace/logs`
- `/workspace/cache`
- `/workspace/config`
- `/workspace/home`

Additional runtime paths initialized by bootstrap:

- `/workspace/config/secrets.env`
- `/workspace/config/service-updates.toml`
- `/workspace/config/service-updates-rollback.jsonl`
- `/workspace/config/ai-toolkit/aitk_db.db`
- `/workspace/config/mediapilot/data.db`
- `/workspace/cache/mediapilot/thumbs`

## Service Logs

ControlPilot and supervisor store logs under `/workspace/logs`:

- `controlpilot.out.log`, `controlpilot.err.log`
- `comfy.out.log`, `comfy.err.log`
- `kohya.out.log`, `kohya.err.log`
- `diffpipe.out.log`, `diffpipe.err.log`
- `invoke.out.log`, `invoke.err.log`
- `ai-toolkit.out.log`, `ai-toolkit.err.log`
- `jupyter.out.log`, `jupyter.err.log`
- `code-server.out.log`, `code-server.err.log`
- `copilot.out.log`, `copilot.err.log`
- `supervisord.log`

## Bundled vs Persistent Paths

- Bundled image content: `/opt/pilot/...`
- Persistent user/project data: `/workspace/...`

Important examples:

- Bundled default manifest: `/opt/pilot/config/models.manifest.default`
- Runtime manifest override: `/workspace/config/models.manifest`
- Bundled docs: `/opt/pilot/docs`
- Workspace docs fallback: `/workspace/docs`

## Runtime Sockets/Temps

- Supervisor unix socket: `/tmp/supervisor.sock`
- Jupyter runtime dir: `/tmp/jupyter-runtime`

## Not Found in Repo

- A machine-readable schema for `/workspace` (JSON/YAML contract) is **Not found in repo**.

## Related

- [Supervisor](../configuration/supervisor.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Models Manifest](../configuration/models-manifest.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
