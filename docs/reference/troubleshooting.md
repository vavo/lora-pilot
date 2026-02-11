# Troubleshooting (Reference)

This page is a quick reference for runtime issues tied to concrete LoRA Pilot behavior in repo code/scripts.

## Fast Triage

```bash
supervisorctl status
curl -s http://127.0.0.1:7878/api/services
tail -n 200 /workspace/logs/controlpilot.err.log
```

## Common Issues

### ControlPilot API not reachable on `7878`

Checks:

- `supervisorctl status controlpilot`
- `tail -n 200 /workspace/logs/controlpilot.err.log`
- Confirm `PORTAL_PORT` value and port mapping in compose.

### Service appears down in UI

Use API and supervisor together:

```bash
curl -s http://127.0.0.1:7878/api/services
supervisorctl status
```

If states disagree, trust `supervisorctl` first, then inspect `*.err.log`.

### Dataset not visible in ControlPilot

`GET /api/datasets` only lists directories under `/workspace/datasets` that start with `1_`.

Fix:
- Rename folder to `1_<name>` or create via `/api/datasets/create` (which auto-prefixes).

### Dataset upload/import fails

`/api/datasets/upload` rejects unsafe ZIP content:

- absolute paths
- `..` traversal
- symlinks

Rebuild ZIP without symlinks and with normal relative file paths.

### TagPilot save behaves inconsistently for huge sets

Use incremental endpoint flow:

- `POST /api/tagpilot/save-item` with `reset=true` on first item
- send items
- final call with `done=true` to produce ZIP

### Copilot unavailable in ControlPilot

Checks:

```bash
supervisorctl status copilot
curl -s http://127.0.0.1:7879/status
curl -s http://127.0.0.1:7878/api/copilot/status
```

Notes:
- `copilot` supervisor program is `autostart=false`.
- Sidecar binds localhost only by default.

### Docs file endpoint returns `400` or `404`

`/api/docs/file` accepts only safe relative `.md` paths.

Rejected patterns include:
- absolute paths
- paths with `..`
- path segments containing `:`
- non-`.md` suffixes

### MediaPilot stuck on loader in subpath deployments

Repo changelog indicates subpath-safe fixes were added in `v2.2` for `/mediapilot`.

Checks:
- Ensure you are running an image build that includes `v2.2` changes.
- Hard-refresh client cache after update.

If still broken, inspect:
- `/workspace/logs/controlpilot.err.log`
- `/workspace/logs/controlpilot.out.log`

## Useful Log Paths

- `/workspace/logs/controlpilot.err.log`
- `/workspace/logs/comfy.err.log`
- `/workspace/logs/kohya.err.log`
- `/workspace/logs/invoke.err.log`
- `/workspace/logs/ai-toolkit.err.log`
- `/workspace/logs/copilot.err.log`
- `/workspace/logs/supervisord.log`

## Related

- [Getting Started Troubleshooting](../getting-started/troubleshooting.md)
- [API Reference](../development/api-reference.md)
- [Supervisor](../configuration/supervisor.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
