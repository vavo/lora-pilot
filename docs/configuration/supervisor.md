# Supervisor

LoRA Pilot uses `supervisord` as the in-container process manager.

## Startup Path

Container command (Dockerfile `CMD`):

1. `scripts/bootstrap.sh`
2. `/usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf`

Main config in repo: `supervisor/supervisord.conf` (copied to `/etc/supervisor/supervisord.conf` in image).

## Supervisor Interfaces

Defined in config:

- Unix socket: `/tmp/supervisor.sock` (`chmod=0700`)
- HTTP interface: `127.0.0.1:9001`
  - Username: `admin`
  - Password: `${SUPERVISOR_ADMIN_PASSWORD:-supervisor_secure_password_2024}`

`supervisorctl` is configured to use the unix socket:

- `serverurl=unix:///tmp/supervisor.sock`

## Managed Programs

| Program | Autostart | Command |
|---|---:|---|
| `jupyter` | `true` | `/opt/pilot/start-jupyter.sh` |
| `code-server` | `true` | `/opt/pilot/start-code-server.sh` |
| `comfy` | `true` | `/bin/bash -lc '/opt/pilot/comfy.sh'` |
| `kohya` | `true` | `/bin/bash -lc '/opt/pilot/start-kohya.sh'` |
| `diffpipe` | `true` | `/bin/bash -lc 'exec /opt/pilot/diffusion-pipe.sh'` |
| `invoke` | `true` | `/bin/bash -lc 'exec /opt/pilot/invoke.sh'` |
| `controlpilot` | `true` | `/bin/bash -lc 'exec /opt/pilot/portal.sh'` |
| `copilot` | `false` | `/bin/bash -lc '... exec /opt/pilot/copilot-sidecar.sh'` |
| `ai-toolkit` | `true` | `/bin/bash -lc '... npm run update_db; exec npm run start'` |

Notes:

- `copilot` loads `/workspace/config/secrets.env` when present and maps `COPILOT_GITHUB_TOKEN` into `GH_TOKEN`/`GITHUB_TOKEN`.
- `ai-toolkit` exits cleanly if UI assets/node are unavailable (build without UI).

## Logs

Supervisor + service logs are persisted under `/workspace/logs`:

- Supervisor main log: `/workspace/logs/supervisord.log`
- Per-service logs:
  - `<service>.out.log`
  - `<service>.err.log`

Examples:

- `/workspace/logs/controlpilot.out.log`
- `/workspace/logs/comfy.err.log`

## Control Surface in ControlPilot API

Service control is implemented in `apps/Portal/app.py`.

### Status and actions

- `GET /api/services`
- `POST /api/services/{name}/{action}` where `action` is `start|stop|restart`
- `GET /api/services/{name}/log?lines=<n>`

Service names accepted by API:

- `jupyter`, `code-server`, `comfy`, `kohya`, `diffpipe`, `invoke`, `ai-toolkit`, `controlpilot`, `copilot`

### Autostart settings

- `POST /api/services/{name}/settings/autostart`

Behavior:

- Edits `autostart=` in supervisor config section `[program:<name>]`
- Writes config file back to disk
- Runs `supervisorctl reread` (best effort)

Config file lookup order:

1. `SUPERVISOR_CONFIG_PATH` env var (if set)
2. `/etc/supervisor/supervisord.conf`
3. `/opt/pilot/supervisor/supervisord.conf`
4. repo path fallback when running from source

## In-App Service Updates

ControlPilot includes update orchestration for selected services:

- Supported: `invoke` (pip), `comfy`/`kohya`/`diffpipe`/`ai-toolkit` (git)
- Endpoints:
  - `GET /api/services/versions`
  - `POST /api/services/{name}/update/start`
  - `GET /api/services/{name}/update/status`

Config + audit files (under `/workspace/config` by default):

- `service-updates.toml`
- `service-updates-rollback.jsonl`

Boot-time reconcile is controlled by `SERVICE_UPDATES_BOOT_RECONCILE` and runs `service-updates-reconcile.py` when enabled.

## Quick CLI Ops (Inside Container)

```bash
supervisorctl status
supervisorctl restart controlpilot
supervisorctl stop comfy
supervisorctl start comfy
```

## Security Notes

- Supervisor HTTP listener is localhost-only (`127.0.0.1`).
- Password should be set via `SUPERVISOR_ADMIN_PASSWORD` (bootstrap writes a random value if missing).
- Primary operational control path in LoRA Pilot is unix-socket-backed `supervisorctl`, not exposed publicly by default.

## Related

- [Environment Variables](environment-variables.md)
- [Docker Compose](docker-compose.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
