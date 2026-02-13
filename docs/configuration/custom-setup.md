# Custom Setup

This page covers practical overrides when default Compose behavior is not enough: custom images, custom mounts, port remaps, bootstrap toggles, and update policy wiring.

## 1) Use Override Files, Not Ad-Hoc Edits

Recommended pattern:

```bash
cp .env.example .env
cat > docker-compose.override.yml <<'YAML'
services:
  lora-pilot:
    environment:
      - PORTAL_PORT=8787
    ports:
      - "8787:8787"
YAML

docker compose up -d
```

Keep `docker-compose.yml` as base and put local changes in `docker-compose.override.yml`.

## 2) Pin Custom Image

If you build your own image, set in `.env`:

```env
LORA_PILOT_IMAGE=your-registry/lora-pilot:custom
```

Base compose already reads `LORA_PILOT_IMAGE`.

## 3) Split Storage Mounts

Default is `./workspace:/workspace`. If you want separate host paths:

```yaml
services:
  lora-pilot:
    volumes:
      - ./workspace:/workspace
      - /mnt/fast/models:/workspace/models
      - /mnt/fast/datasets:/workspace/datasets
      - /mnt/bulk/outputs:/workspace/outputs
```

## 4) Port Remapping

Set in `.env` and restart:

```env
PORTAL_PORT=8787
COMFY_PORT=5655
INVOKE_PORT=9190
```

Compose maps each service as `${PORT}:${PORT}`, so keep host/container values aligned unless you explicitly edit `ports`.

## 5) Bootstrap Sync/Behavior Toggles

`scripts/bootstrap.sh` reads these runtime toggles:

| Variable | Default | Effect |
|---|---|---|
| `MEDIAPILOT_SYNC_ON_BOOT` | `1` | Sync workspace MediaPilot copy from bundled source when upstream commit changes |
| `MEDIAPILOT_FORCE_ENV_DEFAULTS` | `0` | Force overwrite key MediaPilot `.env` defaults |
| `TAGPILOT_SYNC_ON_BOOT` | `1` | Sync workspace TagPilot copy from bundled source |
| `SERVICE_UPDATES_BOOT_RECONCILE` | `1` | Run service update reconcile script on boot |

Example:

```yaml
services:
  lora-pilot:
    environment:
      - TAGPILOT_SYNC_ON_BOOT=0
      - MEDIAPILOT_FORCE_ENV_DEFAULTS=1
```

## 6) Service Update Policy

Policy file:
- `/workspace/config/service-updates.toml`

Audit log:
- `/workspace/config/service-updates-rollback.jsonl`

Override paths if needed:

```env
SERVICE_UPDATES_CONFIG_PATH=/workspace/config/service-updates.toml
SERVICE_UPDATES_ROLLBACK_LOG_PATH=/workspace/config/service-updates-rollback.jsonl
```

## 7) Run Development Mode Cleanly

Use `docker-compose.dev.yml` when you need source mounts and interactive debugging:
- mounts `apps/Portal`, `apps/MediaPilot`, `scripts`, `supervisor`
- enables `PYTHONUNBUFFERED=1`, `FLASK_ENV=development`, `DEBUG=1`
- keeps `stdin_open: true` and `tty: true`

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec lora-pilot bash
```

## 8) CPU-Only Setup

When GPU runtime is unavailable:

```bash
docker compose -f docker-compose.cpu.yml up -d
```

This profile:
- does not use NVIDIA runtime
- exposes only `7878`, `8888`, `8675`
- sets `OMP_NUM_THREADS` and `MKL_NUM_THREADS`

## 9) Build-Time Customization + Runtime Use

Build args are in `Dockerfile`/`build.env.example` (for example `INSTALL_INVOKE`, `INSTALL_DIFFPIPE`, `AI_TOOLKIT_REF`, `INVOKEAI_VERSION`).

Typical flow:
1. Build your image with custom args.
2. Push/tag image.
3. Set `LORA_PILOT_IMAGE` in `.env`.
4. Recreate container with Compose.

## 10) Operator Checklist

Before calling setup “done”, verify:

```bash
docker compose ps
curl -s http://localhost:${PORTAL_PORT:-7878}/api/services
docker compose exec lora-pilot supervisorctl status
docker compose exec lora-pilot ls -la /workspace/{models,datasets,outputs,config,logs}
```

## 11) Common Override Recipes

### Keep default workspace, move only models to fast disk

```yaml
services:
  lora-pilot:
    volumes:
      - ./workspace:/workspace
      - /mnt/nvme/models:/workspace/models
```

### Run on alternate host ports (no internal path changes)

```yaml
services:
  lora-pilot:
    ports:
      - "8787:7878"
      - "5655:5555"
      - "9190:9090"
```

### Disable boot reconcile for service updates in staging

```yaml
services:
  lora-pilot:
    environment:
      - SERVICE_UPDATES_BOOT_RECONCILE=0
```

### Enable faster troubleshooting loop in dev

Use `docker-compose.dev.yml` so Portal/scripts/supervisor config are mounted from repo and editable without rebuilding image.

## 12) Change Application Matrix

| Change Type | Needs `supervisorctl restart` | Needs container recreate (`docker compose up -d`) |
|---|---:|---:|
| UI/API-level settings only | sometimes | no |
| Edit `/workspace/config/service-updates.toml` | no | no |
| Edit mounted script in dev compose | yes (target service) | no |
| Change `.env` port/image/runtime vars | no | yes |
| Change volume mappings | no | yes |
| Change Dockerfile build args | no | yes (new image + recreate) |

## 13) Anti-Patterns

- Editing `docker-compose.yml` directly for local-only changes: use `docker-compose.override.yml`.
- Storing models outside `/workspace/models` without mount mapping: tools won’t see them consistently.
- Mixing old `docker-compose` and new `docker compose` command styles in team docs/scripts.
- Restarting entire container for every issue: prefer `supervisorctl restart <service>` first.

## Related

- [Docker Compose](docker-compose.md)
- [Environment Variables](environment-variables.md)
- [Supervisor](supervisor.md)
- [Building](../development/building.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


