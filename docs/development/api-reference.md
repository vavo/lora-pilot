# API Reference

_Last updated: 2026-10-03_

ControlPilot backend is a FastAPI app served on `PORTAL_PORT` (default `7878`). This reference covers first-party routes in ControlPilot, embedded MediaPilot and the internal Copilot sidecar. Upstream applications such as ComfyUI keep their own API contracts.

## Conventions

- Base URL: `http://localhost:7878`
- Request bodies use JSON unless a route specifies multipart fields or query parameters. Bodyless actions need no `{}` payload.
- Response format: JSON, except file downloads, images, static assets and proxy responses. Successful handlers normally return HTTP 200, including queued jobs; inspect their state fields for completion.
- OpenAPI schema: `GET /openapi.json`. Swagger UI and ReDoc are disabled. The schema describes typed inputs but omits middleware authentication, WebSockets, mounted apps and fields accepted through untyped dictionaries. The multi-method Comfy gateway currently shares operation IDs across methods, so normalize those IDs before generating a client.
- CORS: `CORS_ALLOWED_ORIGINS` is a comma-separated list, default `*`. `CORS_ALLOW_CREDENTIALS` defaults to false for the wildcard and true for an explicit origin list.
- `/api/*` responses receive no-cache headers after handler execution.
- `GET /healthz` returns `{"ok":true}` without authentication. It checks the Portal process, not GPU or downstream service readiness.
- Paths and filenames refer to the server/container filesystem. URL-encode path parameters and query values.

## Authentication and settings

ControlPilot defaults to password protection off. Once enabled, requests to `/api/*`, `/dpipe/*`, `/proxy/comfy/*` and the MediaPilot mount require the `controlpilot_session` cookie. Exceptions include ControlPilot login/status, MediaPilot login/status/health and MediaPilot static assets. The root frontend and `/openapi.json` remain outside this password gate. `/ws/comfy` checks the ControlPilot cookie separately.

Log in with `POST /api/settings/auth/login` and JSON `{"password":"..."}`; preserve the response cookie for subsequent requests. `GET /api/settings/auth/status` returns `enabled` and `authenticated`. With protection disabled, it reports authenticated without a cookie. An invalid password or missing session on a protected route returns HTTP 401. Logout removes the caller's cookie. Changing the password invalidates cookies derived from the previous password.

There is no general ControlPilot bearer-token API. The optional Comfy token applies only to `/comfy/*` and `/comfy/ws`; it cannot authenticate Settings, training, model downloads or `/proxy/comfy/*`.

| Method | Path | Input and result |
|---|---|---|
| `GET` | `/api/settings` | Auth/secret-presence flags, `comfy_access`, theme/sidebar, shutdown defaults, Copilot defaults and Jupyter origin pattern; no stored secret values |
| `GET` | `/api/settings/auth/status` | Public login state |
| `POST` | `/api/settings/auth/login` | JSON `{"password":"..."}`; sets session cookie when protection is enabled |
| `POST` | `/api/settings/auth/logout` | No body; clears session cookie |
| `POST` | `/api/settings/password` | `{"enabled":true,"password":"..."}`; nonempty password required when enabling; `{"enabled":false}` removes protection |
| `POST` | `/api/settings/ui` | Required `theme` and `sidebar_compact`; `dark` selects dark, other theme values select light |
| `POST` | `/api/settings/shutdown-defaults` | `shutdown_mode`: `""`, `stop`, or `remove`; `hours`, `mins`, `secs` default to 0, 1, 0 and clamp to 0–99, 0–59, 0–59; saves defaults without scheduling |
| `POST` | `/api/settings/copilot-defaults` | Required `allow_all_urls` boolean |
| `POST` | `/api/settings/jupyter` | Optional `token` (omit/null preserves; empty clears), `allow_origin_pat` (defaults empty); saves values and restarts Jupyter |
| `POST` | `/api/settings/copilot/restart` | No body; restarts the sidecar after token/settings changes |
| `POST` | `/api/settings/mediapilot/password` | `{"password":"..."}`; empty clears the separate MediaPilot password |
| `POST` | `/api/settings/comfy/protection` | `{"enabled":true}` or false; stops/starts ComfyUI when policy changes |
| `POST` | `/api/settings/comfy/token` | No body; generates/replaces token, returns plaintext `token` once with access status |
| `DELETE` | `/api/settings/comfy/token` | No body; revokes token without disabling protection |

Comfy policy/token changes require an enabled ControlPilot password, its session cookie, and an `Origin` header whose host (including port) matches `Host`. Missing password returns 422; rejected origin returns 403. Send the public origin when using a reverse proxy. The same rule applies to changing the ControlPilot password while Comfy protection is on; disable Comfy protection before removing that password (otherwise 409).

Comfy access status contains `enabled`, `token_set` and `gateway_path`. A protection change can return 503 after saving the policy if ComfyUI fails to restart; read Settings and service logs before retrying. Jupyter settings also persist before the restart attempt. See [Comfy access protection](../configuration/comfy-access.md) for the gateway setup.

## MCP transport and owner administration

MCP is a separate SDK endpoint at `/mcp`, absent from Portal OpenAPI. It uses scoped MCP bearer credentials and strict origin/host rules, independent of Portal cookies and wildcard CORS. `/mcp-artifacts/{artifact_id}` serves authorized private ZIP downloads with the same credential. See [MCP setup, tools and release gates](../configuration/mcp.md).

The Settings routes below also live outside Portal OpenAPI. They require an enabled ControlPilot password and authenticated owner cookie, except that status returns only `password_required: true`, `enabled: false` and the known `url` when no password is set. Mutations additionally require the current `password` in the JSON body, same `Origin`/Host (matching the configured origin when one exists), and `X-MCP-CSRF` from the status response. Bearer MCP credentials cannot administer connections. All responses are non-cacheable; requests are limited to 64 KiB.

| Method | Path | Input/result |
|---|---|---|
| `GET` | `/api/settings/mcp` | `password_required`, enabled/available/execution flags, endpoint, CSRF token, eligible objects/scopes, connections without token digests, pending approval disclosures |
| `POST` | `/api/settings/mcp` | `password`, `enabled`; claim ledger ownership and change global access |
| `POST` | `/api/settings/mcp/clients` | `password`, `label`, `scopes`, optional `datasets`, `runs`, `days` (1–30), `policy`, `enable` (default false); returns `id`, one-time `token` and `url`. `enable: true` enables MCP atomically with credential creation |
| `PATCH` | `/api/settings/mcp/clients/{client_id}` | Same grant fields; preserves identity/token, renews expiry and invalidates plans/queued authorization |
| `DELETE` | `/api/settings/mcp/clients/{client_id}` | `password`; permanently revoke connection |
| `POST` | `/api/settings/mcp/clients/{client_id}/rotate` | `password`; replace credential, returning the new `token` once |
| `POST` | `/api/settings/mcp/approvals/{plan_id}` | `password`, `approve`; approve/reject pending current plan |

The first authorized enable or client creation pins the current HTTPS origin when none is configured and activates MCP without a restart. An explicit `MCP_PUBLIC_URL` or detected RunPod origin cannot be overridden by the request. Creation defaults to leaving global enablement unchanged for API compatibility; the Settings UI sends `enable: true`. This field is not accepted on grant edits.

`policy` is `{ "enabled": false, "max_steps": 100, "max_seconds": 1800, "max_bytes": 8589934592 }` by default. Enabled policies auto-approve plans only within the connection's selected scopes, objects and bounds. Steps are 1–600, seconds 60–3600, bytes 1–34359738368. Grant changes require all fields that should remain selected. Disabling the ControlPilot password while MCP is enabled returns 409. Running work is preserved when MCP access is disabled or revoked.

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
| `POST` | `/api/services/{name}/install/start` | Installs optional code-server; no body |
| `GET` | `/api/services/{name}/update/status` | Update/install job state/tail |
| `POST` | `/api/services/{name}/settings/autostart` | Body: `{"enabled":true}` or `{"enabled":false}` |
| `GET` | `/api/services/{name}/log` | Query: `lines` (default `100`) |
| `GET` | `/api/tensorboard/status` | `port`, per-source `sources`, and `server` reachability/service state/start eligibility |
| `POST` | `/api/tensorboard/start` | No body; starts the DiffPipe service in TensorBoard-only mode; returns `{"status":"starting"}` |

Known service names are `jupyter`, `code-server`, `comfy`, `kohya`, `diffpipe`, `invoke`, `ai-toolkit`, `controlpilot` and `copilot`. These identifiers match Supervisor program names.

Each `/api/services` entry retains `name`, `display`, `state`, `state_raw`, `running` and `autostart`. Its additional `definition` object contains `label`, resolved `port`, `role`, `description`, `icon`, `order` and `capabilities`. Capabilities identify browser access, update support, TensorBoard source/label and whether stopping the service disconnects ControlPilot. An invalid port is `null`; unknown or mismatched Supervisor output produces `UNKNOWN` with `running: false`. The public definition excludes launcher commands, repository paths and environment variable names. See the [shared registry contract](../configuration/supervisor.md#keeping-service-definitions-consistent).

`GET /api/services` also reports `installed` (boolean); code-server has `definition.capabilities.install: true`. When absent, starting/restarting it or enabling autostart returns 409.

`POST /api/services/code-server/install/start` starts an asynchronous installation of the pinned release. No request body is needed; clients cannot choose a download URL, command or version. Other known services return 400; unknown names return 404. Duplicate calls reuse the running job; an existing installation returns `state: "done"`. The route uses the same ControlPilot authentication as other service controls.

Poll `GET /api/services/code-server/update/status` for installation progress, using the existing service-job endpoint. Jobs include `operation: "install"` (normal updates use `"update"`), `state`, `last_line`, `error` and `installed_after`. A completed install does not start the service or change autostart. Job status is process-local: after a Portal restart refresh `/api/services` to discover installed files or retry an interrupted install.

Version listings return installed/latest metadata and `update_supported`; update start accepts optional `{"target_version":"..."}`. Image-managed Git services reject runtime updates with 400. Poll update status for `state`, `error`, `last_line` and `output_tail`; no recorded job returns `state: "idle"`. Service log responses contain `log` and `path`.

TensorBoard status groups event directories under `diffpipe`, `trainpilot`, `kohya` and `ai-toolkit`, with run-level loaded/recent flags. `/api/tensorboard/start` returns 409 if `DIFFPIPE_CONFIG` would launch training, or if the service is not stopped/exited/fatal. A successful start response does not prove the TensorBoard HTTP server is ready; poll status.

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

Model pull actions take no body. Blocking pull returns `status` and `output`; background start returns a job, and polling can return `state` values `idle`, `queued`, `running`, `done`, or `error`. Jobs include `name`, `pid`, nullable `progress_pct`, `last_line`, `error`, timestamps and `output_tail`. `/api/models/pulls` wraps the list in `jobs`. Delete returns `status` and `deleted`, and rejects active downloads with 409.

Workflow plan accepts `{"optional":[]}` (optional file `name` values from the workflow catalog, not manifest model IDs). Inspect `files`, `can_install`, and `plan_id`; install requires the same selection plus `plan_id`. A stale/missing plan or failed checks returns 409. Success returns `jobs` and `installed_count`.

Set the Hugging Face token with JSON `{"token":"..."}`; empty clears it. The legacy `token` query parameter takes precedence when both are supplied. Prefer JSON to keep the token out of URLs.

## Dataset + TagPilot API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/datasets` | Lists dataset dirs (`/workspace/datasets/1_*`) with image counts, caption coverage, and preview paths |
| `GET` | `/api/datasets/{name}/preview` | Required query `file`: relative image path; returns a bounded JPEG thumbnail |
| `POST` | `/api/datasets/create` | Body: `{"name":"..."}` |
| `POST` | `/api/datasets/upload` | Multipart `file` zip upload + extract |
| `DELETE` | `/api/datasets/{name}` | Deletes dataset + best-effort zip cleanup |
| `PATCH` | `/api/datasets/{name}` | Body: `{"name":"new_name"}` |
| `GET` | `/api/tagpilot/load` | Query: required `name`, optional `offset` and `limit`; returns base64 files |
| `POST` | `/api/tagpilot/save` | Query `name` + multipart `file` |
| `POST` | `/api/tagpilot/save-item` | Required query `name` plus multipart fields below |
| `GET` | `/api/tagpilot/providers` | Provider status for Gemini/Grok/OpenAI; does not expose secret values |
| `POST` | `/api/tagpilot/providers/{provider}/key` | Saves or clears the provider key in `/workspace/config/secrets.env` |
| `POST` | `/api/tagpilot/generate` | Multipart image input; generates tags or a caption through Gemini/Grok/OpenAI |

Dataset entries retain `name`, `display`, `images`, `size_bytes`, `has_tags`, and `path`, and add `captioned_images` and `preview_files`. Caption coverage counts images with a matching nonempty `.txt` or `.caption` file in the same directory. `preview_files` contains up to three relative image paths; URL-encode the dataset name and query value when requesting a preview.

The preview route preserves aspect ratio within 180 by 180 pixels and returns `image/jpeg`. It rejects absolute paths, traversal, symbolic links, non-image files, inputs larger than 32 MiB, and images above 40 million pixels. The handler sets private cache headers, but Portal middleware overrides them with API no-store headers. Previews follow ControlPilot's authentication policy.

Dataset create normalizes names to `1_<name>` and returns `status`/`path`; an existing name returns 400. ZIP upload derives the dataset name from the archive filename and replaces an existing dataset of that name. TagPilot ZIP save also replaces the dataset contents. Default archive limits are 700 MiB uploaded, 10,000 members, 4 GiB extracted total, 2 GiB per member and a 100:1 compression ratio; configuration can override them. Invalid archive paths/symlinks are rejected. Dataset deletion removes its directory and attempts to remove matching ZIPs.

TagPilot load returns `name`, `files`, `offset`, `limit`, `total`, and `returned`; each file has `name`, `mime` and `b64`. Offset defaults to 0. Limit defaults to `TAGPILOT_LOAD_DEFAULT_LIMIT` (0, meaning all files); positive limits cap at `TAGPILOT_LOAD_MAX_LIMIT` (1,000). Negative pagination values return 400.

Provider-key writes take JSON `{"api_key":"..."}`; empty clears the key. Generation defaults to `mode=tags` and an empty prompt. It returns text, not a generated image.

`/api/tagpilot/save-item` multipart fields:

- `file`
- `tags` (optional)
- `reset` (default false; true deletes the existing dataset before writing this item)
- `done` (default false; true also rebuilds the dataset ZIP)

Item save writes a matching `.txt` caption and returns `status`, `path`, `file` and `done`, plus `zip` on finalization. Duplicate filenames receive a unique suffix.

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

`GET /api/datasets/{name}/quality` returns `complete`, `images`, finding counts and relative file findings without modifying the dataset. Scans are bounded and incomplete results are explicit.

`GET /api/training/first-lora` returns guide progress. `GET /api/training/first-lora/preview` returns the bundled sample PNG. `POST /api/training/first-lora/install` installs the bundled sample without overwriting existing files; `POST /api/training/first-lora/reviewed` records explicit review of the current dataset fingerprint. The guide uses the existing training and comparison APIs.

`POST /api/training/recommendation` accepts the training request and returns GPU capacity, suggested settings and optional evidence from a matching successful run. Training requests accept an optional `hardware` object containing `train_batch_size`, `gradient_accumulation_steps`, `network_dim` and FLUX-only `blocks_to_swap`. New run records can include sampled `performance` data. Missing measurements do not block training.

`POST /api/training/runs/{id}/export/preview` accepts `artifact`, `trigger_words`, `sample_prompt` and optional comparison-image indices in `images`. It returns a file list, manifest and preview token. `GET /api/training/runs/{id}/export` accepts the same fields as query parameters, repeated `images` parameters and the token, and streams a ZIP. A changed package returns HTTP 409 and requires a fresh preview.

The guided interface uses `/api/training`. These routes follow ControlPilot authentication and persist run records under the workspace. The legacy SDXL API remains available separately below.

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/training/preflight` | Checks recipe model files and reports detected GPU conflicts. |
| `GET` | `/api/training/runs` | Returns filtered, paginated run summaries, total matches, queued count, pause state, conflicts, and active run ID. |
| `POST` | `/api/training/runs` | Saves a configuration snapshot and queues a uniquely identified run. |
| `POST` | `/api/training/queue` | Accepts `{"paused":true}` or `false`; pausing does not stop current work. |
| `GET` | `/api/training/runs/{id}` | Returns status, artifacts, timing, saved configuration, effective configuration when available, and up to 500 recent log lines. |
| `POST` | `/api/training/runs/{id}/cancel` | Cancels a queued run or stops a currently managed process. |
| `POST` | `/api/training/runs/{id}/repeat` | No body; queues a new run using saved configuration and the current dataset. |
| `POST` | `/api/training/runs/{id}/resume` | No body; queues a continuation from saved state or weights when `recovery_option` is available. |
| `POST` | `/api/training/runs/{id}/library` | Copies successful artifacts by default; `{"action":"move"}` removes originals after all library destinations are verified. Moved files remain accessible through the run. |
| `POST` | `/api/training/runs/{id}/comparison/prepare` | Publishes selected or all checkpoints, checks live ComfyUI nodes/models, and saves the comparison graph without queueing it. |
| `GET` | `/api/training/runs/{id}/comparison/workflow` | Downloads the prepared API-format workflow JSON. |
| `POST` | `/api/training/runs/{id}/comparison` | Prepares and submits the baseline plus requested checkpoints to ComfyUI. |
| `GET` | `/api/training/runs/{id}/comparison` | Returns persisted comparison state and result image URLs. |
| `POST` | `/api/training/runs/{id}/comparison/reset` | Explicitly resets comparison tracking only when the ComfyUI queue is empty. |

The run listing accepts `search` (LoRA or dataset name, up to 200 characters), `family`, `status`, `offset`, and `limit` (default 50, maximum 100). Filtering happens before pagination. `total` counts matching records, while `queued_count` counts all queued runs independently of the filters. Run detail includes `timing.stage`, `elapsed_seconds`, and `remaining_seconds`; unavailable durations are null.

`GET /api/training/runs/{id}/artifacts/{filename}` streams an eligible checkpoint as an attachment. Queued or active runs return HTTP 409; missing or linked checkpoints are excluded. The endpoint does not move or publish the file.

Preflight and run creation accept `dataset_name`, `output_name`, `family`, `profile`, and optional `toml_path`. Supported families are `sdxl`, `flux1`, `sd15`, `sd35_medium`, and `sd35_large`; profiles are `quick_test`, `regular`, and `high_quality`. `output_name` begins with an ASCII letter or digit and contains at most 80 letters, digits, underscores, or hyphens. Optional `source_run_id` selects a saved configuration from the same family; the chosen profile is applied to the new run.

Only `dataset_name` and `output_name` are required; `family` defaults to `sdxl`, `profile` to `regular`, and `toml_path` to empty. Hardware override ranges are batch size 1–8, accumulation 1–16, network dimension 4–128 and blocks to swap 0–35.

Run creation returns the record with its 32-character hexadecimal `id`. Status values include `queued`, `running`, `stopping`, `succeeded`, `failed`, `stopped`, `cancelled` and `interrupted`. Each run has a separate output directory. The queue accepts at most 50 active or waiting runs and returns HTTP 409 when full. Missing models fail before queueing. A dataset changed since queueing fails at launch, with an explanation saved in the record. After a restart, interrupted processes are not automatically resumed and pending dispatch remains paused. Only one ControlPilot worker can own the queue for a workspace.

Run detail exposes nullable `recovery_option`. Resume creates a new run from complete saved optimizer/training state, or from an available checkpoint with a fresh optimizer and full training schedule. An unchanged dataset is required. Missing recovery data, an existing active continuation, an orphan process, or dataset changes return 409. Repeat starts fresh using the current dataset instead.

Comparison requests contain `prompt` and either `artifact` for one checkpoint or `all_checkpoints: true` for every saved checkpoint, with optional `seed` and `strength`. All-checkpoint comparisons support up to 64 saved files and return images in baseline, training checkpoint, then final-file order, with filename labels. Seeds range from zero to `4294967295`; strength ranges from zero to two. A successful training record and saved artifact are required. Active managed training and duplicate or unconfirmed comparison submissions return HTTP 409. A lost submission response is persisted as `unknown`, requiring inspection and an explicit reset before retrying. Resetting tracking does not cancel a ComfyUI job or remove its outputs.

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
| `GET` | `/api/trainpilot/toml` | Returns `content` and `path` for the default TOML |
| `POST` | `/api/trainpilot/toml` | JSON `{"content":"..."}`; validates syntax and overwrites the default TOML; returns `status` and `path` |

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

Send `learning_rate` in JSON (default `0.00002`); `lr` is the Python attribute name, not a supported request key. Additional defaults include `epochs=1000`, `batch_size=1`, `rank=32`, `gradient_accumulation_steps=4`, `num_repeats=10`, `save_every=2`, and `eval_every=1`. See `TrainRequest` in `/openapi.json` for the full option list.

`resolutions_input`, `frame_buckets` and nonempty `ar_buckets` are JSON-encoded **strings**, for example `"[512]"`, `"[1, 33]"` and `"[0.5, 1, 2]"`. `betas` accepts either a list or a JSON-encoded list. Dataset/config/output paths must stay within `/workspace/datasets`, `/workspace/configs` (plural), and `/workspace/outputs`, respectively, adjusted by `WORKSPACE_ROOT`. Model validation accepts local paths beneath the workspace, `/opt`, or the service user's home.

Validate takes just the four model-path fields and returns `{"ok":true,"missing":[]}` or `ok:false` with missing field/path entries. Start returns `status`, `pid` and the generated config path. Stop accepts an optional **query** `pid`; logs accepts query `pid` and `limit` (default 500) and returns `pid`, `lines`, and `activity`. An untracked stop returns `status: "noop"`. Process/log bookkeeping is in memory; restarting Portal clears it. A second start returns 400 while another DiffPipe run is starting/running, and detected managed-training conflicts return 409.

## Comfy Integration API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/comfy/status` | Comfy reachability probe |
| `GET` | `/api/comfy/latest-image` | Latest generated image metadata |
| `GET` | `/proxy/comfy/{path:path}` | HTTP proxy to Comfy |
| `WS` | `/ws/comfy` | Preview WebSocket bridge using `clientId=portal_preview`; ControlPilot cookie policy |
| `GET` | `/comfy` | Redirects to `/comfy/` |
| `GET`, `HEAD`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` | `/comfy/{path:path}` | Full streaming ComfyUI gateway; preserves query strings and upstream status/content |
| `WS` | `/comfy/ws` | Full WebSocket gateway; forwards the caller's query string |

The full gateway is public when Comfy protection is off. When on, use a ControlPilot cookie or `Authorization: Bearer <Comfy token>`. Cookie-authenticated writes and WebSockets also require a matching `Origin`; bearer-token requests do not. Unauthenticated HTTP calls return 401 (HTML requests to the gateway root redirect to ControlPilot); rejected WebSocket authentication uses close code 4401. Gateway HTTP connection failures return 502. The read-only `/proxy/comfy/{path:path}` route remains subject to ControlPilot authentication regardless of Comfy protection.

## Telemetry + Shutdown API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/telemetry` | Host/container/GPU snapshot |
| `GET` | `/api/telemetry/history` | Query: `max_seconds` (0/default returns all retained samples; positive values select the recent window) |
| `GET` | `/api/runpod/status` | Selected current-pod fields, workspace allocation and optional UTC-day billing; credentials stay on the backend |
| `POST` | `/api/shutdown/schedule` | Body: `{"value":30,"unit":"minutes"}` |
| `POST` | `/api/shutdown/cancel` | Cancels pending shutdown |
| `GET` | `/api/shutdown/status` | Pending schedule state |

RunPod status returns `enabled: false` outside a pod. On RunPod, `available` describes pod access; `storage.available` and `billing.available` independently describe optional features. Missing permissions return sanitized reason codes and messages. Cost fields distinguish `hourly_usd`, `session_estimate_usd` and `billing.total_usd`. No raw provider response or credential is returned. Successful pod reads are cached for 60 seconds, while allocation and billing reads are cached for 300 seconds.

Shutdown status includes the captured RunPod `action` and its storage `notice`. Scheduling reads the current pod before accepting the timer. Execution rechecks eligibility and sends one v2 action request without automatic retries. An accepted request is reported as `requested`, not proof that the pod has stopped.

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
| `GET` | `/api/docs/file` | Query: `path` (safe relative `.md` only); returns `content` and `source` |
| `GET` | `/api/docs/assets/{path:path}` | Streams an image beneath `docs/assets`; path excludes the `assets/` prefix |
| `GET` | `/api/mediapilot/status` | MediaPilot embed/env status summary |

`/api/docs/file` rejects:

- absolute paths
- traversal (`..`)
- non-`.md` targets

Docs content routes return JSON with `content` and `source`. Assets accept PNG, JPEG, GIF, WebP and SVG; invalid paths/types return 400 and missing files return 404.

## MediaPilot API

MediaPilot mounts at `/mediapilot` when available; check `/api/mediapilot/status` first. Its paths do not include `/api`. For example, list images at `/mediapilot/images`. See the [MediaPilot API contract](../components/mediapilot.md#api-request-and-response-contracts) for all routes, query parameters, bulk payloads and responses. Mounted MediaPilot has its own `/mediapilot/openapi.json`, `/mediapilot/docs`, and `/mediapilot/redoc`, subject to its authentication. The Portal schema does not include these mounted routes.

## Copilot Sidecar API (Internal Service)

Default base URL: `http://127.0.0.1:7879`. The sidecar has no authentication middleware; keep it internal and use the authenticated `/api/copilot/*` Portal routes for clients. Its schema is `GET /openapi.json`; Swagger/ReDoc are disabled.

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
- `timeout_seconds` (positive integer; defaults to `COPILOT_TIMEOUT_SECONDS`, normally 1,800)

Chat returns `ok`, `returncode`, `duration_seconds`, `stdout`, `stderr` and `command`. A CLI failure still returns HTTP 200 with `ok:false`; a CLI timeout returns `returncode:124`. Missing CLI returns 503. Portal-to-sidecar transport timeouts return 504. Portal status reports an unreachable sidecar as HTTP 200 with `sidecar_reachable:false`; clients must inspect the payload.

## Error Patterns

FastAPI errors normally use `{"detail":"message"}`; validation errors put a structured list in `detail`. Some proxies and bulk operations return other shapes, described above.

- `400`: invalid action or payload values
- `401`: missing session or invalid credentials
- `403`: rejected same-origin Settings request
- `404`: unknown resource/service/model or missing file
- `409`: busy workload, stale review token/plan, or conflicting resource state
- `413`: upload or dataset-preview size limits exceeded
- `422`: missing/invalid typed input or required settings
- `424`: TagPilot provider failure
- `500`: subprocess/runtime failures
- `502`, `503`, `504`: upstream, service availability or timeout failures

## Quick Smoke Calls

These read-only calls use the default local base URL. Use the public HTTPS origin for a remote deployment. If password protection is off, omit the login and cookie options.

```bash
BASE_URL=http://localhost:7878
curl --fail-with-body -sS "$BASE_URL/healthz"
curl --fail-with-body -sS "$BASE_URL/api/settings/auth/status"

# With protection enabled, supply the password from a local JSON file.
# login.json contains {"password":"your ControlPilot password"}.
COOKIE_JAR=$(mktemp)
chmod 600 "$COOKIE_JAR"
curl --fail-with-body -sS -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' --data-binary @login.json \
  "$BASE_URL/api/settings/auth/login"
curl --fail-with-body -sS -b "$COOKIE_JAR" "$BASE_URL/api/services"
curl --fail-with-body -sS -b "$COOKIE_JAR" "$BASE_URL/api/models"
curl --fail-with-body -sS -b "$COOKIE_JAR" "$BASE_URL/api/telemetry"
curl --fail-with-body -sS -b "$COOKIE_JAR" --get \
  --data-urlencode 'path=development/api-reference.md' "$BASE_URL/api/docs/file"
```

Optional checks for an existing dataset; these do not start training:

```bash
curl --fail-with-body -sS -b "$COOKIE_JAR" \
  "$BASE_URL/api/datasets/1_my_dataset/quality"
curl --fail-with-body -sS -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"dataset_name":"1_my_dataset","output_name":"my_run","family":"sdxl","profile":"quick_test"}' \
  "$BASE_URL/api/training/preflight"
```

Create `1_my_dataset` and install its required models first. Preflight returns checks and conflicts; inspect them before posting the same payload to `/api/training/runs`. After the calls, remove the temporary cookie jar with `rm -f "$COOKIE_JAR"`.

## Related

- [Debugging](debugging.md)
- [Supervisor](../configuration/supervisor.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Documentation Home](../README.md)

---

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
