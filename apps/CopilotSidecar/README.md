# Copilot Sidecar (ControlPilot)

This is a small HTTP sidecar that wraps the `copilot` CLI in programmatic mode and is intended to be run by supervisord inside the LoRA Pilot container.

It is intentionally simple:
- It pipes the request prompt to `copilot` over stdin for each request.
- It enables tooling via `--allow-all-tools` (and optionally paths/urls).
- It persists Copilot CLI config under `/workspace` so it survives container restarts.

## Environment

- `COPILOT_SIDECAR_PORT` (default `7879`)
- `COPILOT_TIMEOUT_SECONDS` (default `1800`)
- `COPILOT_HOME` (default `/workspace/home/root`)
- `COPILOT_XDG_CONFIG_HOME` (default `/workspace/home/root/.config`)
- `COPILOT_CWD` (default `/workspace`)

## API

The sidecar has no authentication middleware. Keep it internal and use ControlPilot’s `/api/copilot/*` routes for authenticated clients. See the [sidecar API reference](../../docs/development/api-reference.md#copilot-sidecar-api-internal-service) for response and error handling.

- `GET /health` returns `{"ok":true}`
- `GET /openapi.json` returns the schema (Swagger/ReDoc UI disabled)
- `GET /status`
- `POST /chat` JSON:
  - `prompt` (required)
  - `cwd` (optional; must be under `/workspace`)
  - `allow_all_tools` (default true)
  - `allow_all_paths` (default true)
  - `allow_all_urls` (default false)
  - `timeout_seconds` (optional positive integer; defaults to `COPILOT_TIMEOUT_SECONDS`, normally 1800)

Chat returns `ok`, `returncode`, `duration_seconds`, `stdout`, `stderr` and `command`. CLI errors and timeouts use HTTP 200 with `ok:false`; a timeout uses exit code 124.
