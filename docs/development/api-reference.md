# API Reference

ControlPilot backend is a FastAPI app served on `PORTAL_PORT` (default `7878`).

## Conventions

- Base URL: `http://localhost:7878`
- Response format: JSON (except proxied binary/static payloads)
- OpenAPI UI: disabled (`docs_url=None`, `redoc_url=None`)
- CORS: `allow_origins=["*"]`
- `/api/*` responses get no-cache headers from middleware

## Service Management API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/services` | Supervisor status for known services |
| `GET` | `/api/services/versions` | Installed/latest version metadata |
| `POST` | `/api/services/{name}/{action}` | `action`: `start`, `stop`, `restart` |
| `POST` | `/api/services/{name}/update/start` | Starts async update job |
| `GET` | `/api/services/{name}/update/status` | Update job state/tail |
| `POST` | `/api/services/{name}/settings/autostart` | Body: `{"enabled": true|false}` |
| `GET` | `/api/services/{name}/log` | Query: `lines` (default `100`) |

Known service names:

- `jupyter`
- `code-server`
- `comfy`
- `kohya`
- `diffpipe`
- `invoke`
- `ai-toolkit`
- `controlpilot`
- `copilot`

## Models API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/models` | Parsed manifest entries |
| `POST` | `/api/models/{name}/pull` | Blocking model pull |
| `POST` | `/api/models/{name}/pull/start` | Starts background pull job |
| `GET` | `/api/models/{name}/pull/status` | Pull job status |
| `GET` | `/api/models/pulls` | Recent pull jobs |
| `POST` | `/api/models/{name}/delete` | Deletes mapped model files |
| `POST` | `/api/hf-token` | Set HF token (query or JSON body) |
| `GET` | `/api/hf-token` | Returns `{ "set": bool }` |

## Dataset + TagPilot API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/datasets` | Lists dataset dirs (`/workspace/datasets/1_*`) |
| `POST` | `/api/datasets/create` | Body: `{"name":"..."}` |
| `POST` | `/api/datasets/upload` | Multipart `file` zip upload + extract |
| `DELETE` | `/api/datasets/{name}` | Deletes dataset + best-effort zip cleanup |
| `PATCH` | `/api/datasets/{name}` | Body: `{"name":"new_name"}` |
| `GET` | `/api/tagpilot/load` | Query: `name` |
| `POST` | `/api/tagpilot/save` | Query `name` + multipart `file` |
| `POST` | `/api/tagpilot/save-item` | Incremental item save/finalize endpoint |

`/api/tagpilot/save-item` multipart fields:

- `file`
- `tags` (optional)
- `reset` (optional bool)
- `done` (optional bool)

## Copilot API (through ControlPilot)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/copilot/status` | Sidecar reachability + status |
| `POST` | `/api/copilot/chat` | Pass-through to sidecar `/chat` |
| `GET` | `/api/copilot/token` | Returns `{ "set": bool }` |
| `POST` | `/api/copilot/token` | Body: `{"token":"..."}` (empty clears) |

Sidecar URL is configured by `COPILOT_SIDECAR_URL` (default `http://127.0.0.1:7879`).

## TrainPilot API

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/trainpilot/start` | Starts TrainPilot subprocess |
| `POST` | `/api/trainpilot/stop` | Stops TrainPilot subprocess |
| `POST` | `/api/trainpilot/model-check` | Checks TOML-referenced checkpoint/VAE paths |
| `GET` | `/api/trainpilot/logs` | Combined process + training log diagnostics |
| `GET` | `/api/trainpilot/toml` | Returns default TOML content |

`/api/trainpilot/start` body:

```json
{
  "dataset_name": "1_my_dataset",
  "output_name": "my_run",
  "profile": "regular",
  "toml_path": "/opt/pilot/apps/TrainPilot/newlora.toml"
}
```

Allowed `profile` values:

- `quick_test`
- `regular`
- `high_quality`

## Diffusion Pipe API

Routes are mounted with `/dpipe` prefix.

| Method | Path | Notes |
|---|---|---|
| `POST` | `/dpipe/train/validate` | Validates configured model paths exist |
| `POST` | `/dpipe/train/start` | Writes configs + launches DeepSpeed training |
| `POST` | `/dpipe/train/stop` | Stops tracked training process |
| `GET` | `/dpipe/train/logs` | Returns in-memory log tail |

Required input fields for `/dpipe/train/start` include:

- `dataset_path`
- `config_dir`
- `output_dir`
- `transformer_path`
- `vae_path`
- `llm_path`
- `clip_path`

`learning_rate` is accepted as payload key alias for `lr`.

## Comfy Integration API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/comfy/status` | Comfy reachability probe |
| `GET` | `/api/comfy/latest-image` | Latest generated image metadata |
| `GET` | `/proxy/comfy/{path:path}` | HTTP proxy to Comfy |
| `WS` | `/ws/comfy` | WebSocket bridge |

## Telemetry + Shutdown API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/telemetry` | Host/container/GPU snapshot |
| `GET` | `/api/telemetry/history` | Query: `max_seconds` |
| `POST` | `/api/shutdown/schedule` | Body: `{"value":30,"unit":"minutes"}` |
| `POST` | `/api/shutdown/cancel` | Cancels pending shutdown |
| `GET` | `/api/shutdown/status` | Pending schedule state |

Shutdown `unit` must be one of:

- `seconds`
- `minutes`
- `hours`
- `days`

## Docs + Embedded App Status API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/docs` | Returns top-level README content |
| `GET` | `/api/changelog` | Returns CHANGELOG content |
| `GET` | `/api/docs/sitemap` | Returns `docs/README.md` |
| `GET` | `/api/docs/file` | Query: `path` (safe relative `.md` only) |
| `GET` | `/api/mediapilot/status` | MediaPilot embed/env status summary |

`/api/docs/file` rejects:

- absolute paths
- traversal (`..`)
- non-`.md` targets

## Copilot Sidecar API (Internal Service)

Default base URL: `http://127.0.0.1:7879`

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | Simple health check |
| `GET` | `/status` | Copilot CLI/config/runtime status |
| `POST` | `/chat` | Executes `copilot -p ...` |

`/chat` body fields:

- `prompt` (required)
- `cwd` (must be under `/workspace`)
- `allow_all_tools` (default `true`)
- `allow_all_paths` (default `true`)
- `allow_all_urls` (default `false`)
- `timeout_seconds` (optional override)

## Error Patterns

- `400`: invalid action or payload values
- `404`: unknown resource/service/model or missing file
- `422`: missing/invalid typed input
- `500`: subprocess/runtime failures

## Quick Smoke Calls

```bash
curl -s http://localhost:7878/api/services
curl -s http://localhost:7878/api/models
curl -s http://localhost:7878/api/telemetry
curl -s http://localhost:7878/api/docs/sitemap
```

## Related

- [Debugging](debugging.md)
- [Supervisor](../configuration/supervisor.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
