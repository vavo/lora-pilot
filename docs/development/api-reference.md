# API Reference

_Last updated: 2026-09-20_

ControlPilot backend is a FastAPI app served on `PORTAL_PORT` (default `7878`).

## Conventions

- Base URL: `http://localhost:7878`
- Response format: JSON (except proxied binary/static payloads)
- OpenAPI UI: disabled (`docs_url=None`, `redoc_url=None`)
- CORS: `allow_origins=["*"]`
- `/api/*` responses get no-cache headers from middleware

## Workspace status API

`GET /api/build` returns `revision` and `built_at` from the image's embedded metadata. Missing or invalid fields are `null`. `GET /api/diagnostics` returns the build identity, allowlisted GPU and service fields, a collection timestamp and a plain-text `summary` suitable for copying. These endpoints use the same ControlPilot authentication policy as other API routes and do not contact remote version indexes.

`GET /api/activity` returns `items`, `paused` and `unavailable`. Each item identifies its kind, state, creation time, display label, optional progress percentage and destination section. Guided training entries also identify their run. A source failure is reported in `unavailable` while other sources remain available. Responses exclude raw logs and configuration. Progress can be `null` when the source has not reported a usable percentage.

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
| `GET` | `/api/tensorboard/status` | Shared TensorBoard source status for Diffusion Pipe + TrainPilot + Kohya + AI Toolkit |

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

`apps/Portal/services/models_api.py` owns the Models router and request validation.
`services/model_downloads.py` owns subprocess execution, progress parsing and the
process-local download queue. `app.py` supplies manifest/storage paths, the pull
timeout and a callback that reads the current Hugging Face token. Authentication
and cache headers remain Portal middleware. Each router has its own queue;
restarting Portal still clears queued jobs and recent activity.

### Backend ownership

| Module under `apps/Portal/services/` | Responsibility |
|---|---|
| `models_api.py` | Nine Models routes, request validation, installation plan checks, and HTTP error mapping |
| `model_downloads.py` | Job state, active-job reuse, subprocess output/progress, workflow sequencing, and deletion guards |
| `models.py` | Manifest parsing, installed-state checks, and model deletion |
| `model_files.py` | Canonical file destinations and legacy file handling |
| `model_install.py` | Bundled workflow requirements and installation preflight |

`ModelPullQueue` uses a lock around job registration and deletion guards. Workflow components run in sequence within one workflow worker; the queue does not impose a global download concurrency limit. Finished and failed jobs expire after ten minutes when cleanup runs. The blocking pull timeout defaults to 1,200 seconds; background pulls do not use that timeout.

Run the focused API and installation checks from the repository root using a Python environment with the Portal test dependencies:

```bash
python3 -m unittest discover -s tests -p 'test_models_api.py'
python3 -m unittest discover -s tests -p 'test_model_install.py'
```

### Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/models` | Parsed manifest entries |
| `POST` | `/api/models/{name}/pull` | Blocking model pull |
| `POST` | `/api/models/{name}/pull/start` | Starts background pull job |
| `GET` | `/api/models/{name}/pull/status` | Pull job status |
| `GET` | `/api/models/pulls` | Recent pull jobs |
| `POST` | `/api/models/{name}/delete` | Deletes mapped model files |
| `GET` | `/api/models/workflows` | Bundled workflow requirements |
| `POST` | `/api/models/workflows/{workflow_id}/plan` | Reviews selected files, source access and storage |
| `POST` | `/api/models/workflows/{workflow_id}/install` | Revalidates the plan and queues missing files |
| `POST` | `/api/hf-token` | Set HF token (query or JSON body) |
| `GET` | `/api/hf-token` | Returns `{ "set": bool }` |

## Dataset + TagPilot API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/datasets` | Lists dataset dirs (`/workspace/datasets/1_*`) with image counts, caption coverage, and preview paths |
| `GET` | `/api/datasets/{name}/preview?file={relative_path}` | Returns a bounded JPEG thumbnail for a dataset image |
| `POST` | `/api/datasets/create` | Body: `{"name":"..."}` |
| `POST` | `/api/datasets/upload` | Multipart `file` zip upload + extract |
| `DELETE` | `/api/datasets/{name}` | Deletes dataset + best-effort zip cleanup |
| `PATCH` | `/api/datasets/{name}` | Body: `{"name":"new_name"}` |
| `GET` | `/api/tagpilot/load` | Query: `name` |
| `POST` | `/api/tagpilot/save` | Query `name` + multipart `file` |
| `POST` | `/api/tagpilot/save-item` | Incremental item save/finalize endpoint |
| `GET` | `/api/tagpilot/providers` | Provider status for Gemini/Grok/OpenAI; does not expose secret values |
| `POST` | `/api/tagpilot/providers/{provider}/key` | Saves or clears the provider key in `/workspace/config/secrets.env` |
| `POST` | `/api/tagpilot/generate` | Multipart image generation through Gemini/Grok/OpenAI |

Dataset entries retain `name`, `label`, `images`, `size_bytes`, `has_tags`, and `path`, and add `captioned_images` and `preview_files`. Caption coverage counts images with a matching nonempty `.txt` or `.caption` file in the same directory. `preview_files` contains up to three relative image paths; URL-encode the dataset name and query value when requesting a preview.

The preview route preserves aspect ratio within 180 by 180 pixels and returns `image/jpeg`. It rejects absolute paths, traversal, symbolic links, non-image files, inputs larger than 32 MiB, and images above 40 million pixels. Responses use private caching and follow ControlPilot's authentication policy.

`/api/tagpilot/save-item` multipart fields:

- `file`
- `tags` (optional)
- `reset` (optional bool)
- `done` (optional bool)

`/api/tagpilot/generate` multipart fields:

- `image`
- `provider`: `gemini`, `grok`, or `openai`
- `mode`: `tags` or `caption`
- `prompt` (optional)

Successful responses return:

```json
{"text":"tag, caption, or provider output","provider":"openai","model":"gpt-5.4-mini"}
```

Missing provider keys and invalid inputs return `400`. Upstream provider failures return JSON `424` responses so reverse proxies do not convert provider errors into generic gateway pages.

## Copilot API (through ControlPilot)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/copilot/status` | Sidecar reachability + status |
| `POST` | `/api/copilot/chat` | Pass-through to sidecar `/chat` |
| `GET` | `/api/copilot/token` | Returns `{ "set": bool }` |
| `POST` | `/api/copilot/token` | Body: `{"token":"..."}` (empty clears) |

Sidecar URL is configured by `COPILOT_SIDECAR_URL` (default `http://127.0.0.1:7879`).

## Persistent guided training API

The guided interface uses `/api/training`. These routes follow ControlPilot authentication and persist run records under the workspace. The legacy SDXL API remains available separately below.

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/training/preflight` | Checks recipe model files and reports detected GPU conflicts. |
| `GET` | `/api/training/runs` | Returns filtered, paginated run summaries, total matches, queued count, pause state, conflicts, and active run ID. |
| `POST` | `/api/training/runs` | Saves a configuration snapshot and queues a uniquely identified run. |
| `POST` | `/api/training/queue` | Accepts `{"paused":true}` or `false`; pausing does not stop current work. |
| `GET` | `/api/training/runs/{id}` | Returns status, artifacts, timing, saved configuration, effective configuration when available, and up to 500 recent log lines. |
| `POST` | `/api/training/runs/{id}/cancel` | Cancels a queued run or stops a currently managed process. |
| `POST` | `/api/training/runs/{id}/repeat` | Queues a new run using saved configuration and the current dataset. |
| `POST` | `/api/training/runs/{id}/library` | Copies successful artifacts into a per-run LoRA library directory without removing originals. |
| `POST` | `/api/training/runs/{id}/comparison/prepare` | Copies the selected artifact, checks live ComfyUI node/model availability, and saves a comparison graph without queueing it. |
| `GET` | `/api/training/runs/{id}/comparison/workflow` | Downloads the prepared API-format workflow JSON. |
| `POST` | `/api/training/runs/{id}/comparison` | Prepares and submits the paired comparison to ComfyUI. |
| `GET` | `/api/training/runs/{id}/comparison` | Returns persisted comparison state and result image URLs. |
| `POST` | `/api/training/runs/{id}/comparison/reset` | Explicitly resets comparison tracking only when the ComfyUI queue is empty. |

The run listing accepts `search` (LoRA or dataset name, up to 200 characters), `family`, `status`, `offset`, and `limit` (default 50, maximum 100). Filtering happens before pagination. `total` counts matching records, while `queued_count` counts all queued runs independently of the filters. Run detail includes `timing.stage`, `elapsed_seconds`, and `remaining_seconds`; unavailable durations are null.

`GET /api/training/runs/{id}/artifacts/{filename}` streams an eligible checkpoint as an attachment. Queued or active runs return HTTP 409; missing or linked checkpoints are excluded. The endpoint does not move or publish the file.

Preflight and run creation accept `dataset_name`, `output_name`, `family`, `profile`, and optional `toml_path`. Supported families are `sdxl` and `flux1`; profiles are `quick_test`, `regular`, and `high_quality`. `output_name` begins with an ASCII letter or digit and contains at most 80 letters, digits, underscores, or hyphens. Optional `source_run_id` selects a saved configuration from the same family; the chosen profile is applied to the new run.

Run creation returns the new record and UUID. Each run has a separate output directory. The queue accepts at most 50 active or waiting runs and returns HTTP 409 when full. Missing models fail before queueing. A dataset changed since queueing fails at launch, with an explanation saved in the record. After a restart, interrupted processes are not automatically resumed and pending dispatch remains paused. Only one ControlPilot worker can own the queue for a workspace.

Comparison requests contain `artifact`, `prompt`, and optional `seed` and `strength`. Seeds range from zero to `4294967295`; strength ranges from zero to two. A successful training record and saved artifact are required. Active managed training and duplicate or unconfirmed comparison submissions return HTTP 409. A lost submission response is persisted as `unknown`, requiring inspection and an explicit reset before retrying. Resetting tracking does not cancel a ComfyUI job or remove its outputs.

## Reviewed storage cleanup API

`GET /api/storage` returns category sizes, workspace filesystem capacity, warnings, and eligible cleanup candidates. Candidates have opaque IDs, display labels, file counts, logical sizes, and estimated reclaimable sizes. Only private files from terminal guided runs are eligible. The scan ignores linked files and protects original datasets, shared models, and run history.

`POST /api/storage/preview` accepts `{"ids":["candidate-id"]}` with one to 200 unique candidate IDs. It checks workload status and the current selection, then returns a review token, selected items, file count, and estimated reclaimable bytes. The token expires after five minutes and exists only in the current ControlPilot process.

After the user explicitly confirms the review, `POST /api/storage/cleanup` accepts `{"token":"review-token"}`. It consumes the token once and repeats workload, selection, and file identity checks before removal. Stale previews, changed files, or workload conflicts return HTTP 409. A successful response reports `complete`, `removed_files`, `estimated_reclaimed_bytes`, and a message. If a filesystem change or removal error occurs partway through, `complete` is false and the counts describe only files already removed; scan again before retrying. Cleanup is permanent and preserves run records, original datasets, and shared model files. These routes use the same authentication as the rest of ControlPilot.

## Legacy TrainPilot API

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/trainpilot/start` | Starts TrainPilot subprocess |
| `POST` | `/api/trainpilot/stop` | Stops TrainPilot subprocess |
| `POST` | `/api/trainpilot/model-check` | Checks TOML-referenced checkpoint/VAE paths |
| `GET` | `/api/trainpilot/logs` | Combined logs, process state, current-run metadata, and LoRA artifacts |
| `POST` | `/api/trainpilot/move-loras` | Body: `{"run_id":"..."}`; moves eligible files into the shared LoRA directory |
| `GET` | `/api/trainpilot/toml` | Returns default TOML content |

`/api/trainpilot/start` body:

```json
{
  "dataset_name": "1_my_dataset",
  "output_name": "my_run",
  "profile": "regular",
  "toml_path": "/workspace/config/trainpilot/newlora.toml"
}
```

The profile values are `quick_test` (Quick test), `regular` (Balanced), and `high_quality` (Extended).

The logs response retains `lines`, `running`, `run_id`, `exit_code`, `lora_files`, and `move_available`. It also returns `moved`, `run`, `output_dir`, `lora_destination`, and `artifacts`. Each artifact contains `name` and `size_bytes`. Run metadata includes the dataset, output name, profile, start time, stop state, and finish time when available. After a move, the response retains the moved files' names and sizes for the result screen.

Use the current `run_id` when calling the move endpoint. A stale run ID or an existing destination filename returns HTTP 409. The handler only selects new or changed `.safetensors` files from the successful run's output directory. It returns the moved filenames and destination on success. This is a move, so the source files leave the output directory.

This legacy API keeps training state in one ControlPilot process; restarting it clears that metadata while preserving output files. The current guided interface uses the persistent API above instead. Legacy start requests retain their payload and response shapes but now reject detected GPU conflicts with HTTP 409. Legacy runs are not imported into the persistent history automatically.

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
| `POST` | `/chat` | Executes `copilot` with the prompt piped on stdin |

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

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
