# Copilot Sidecar (ControlPilot)

This is a small HTTP sidecar that wraps the `copilot` CLI in programmatic mode and is intended to be run by supervisord inside the LoRA Pilot container.

It is intentionally simple:
- It shells out to `copilot -p <prompt>` for each request.
- It enables tooling via `--allow-all-tools` (and optionally paths/urls).
- It persists Copilot CLI config under `/workspace` so it survives container restarts.

## Environment

- `COPILOT_SIDECAR_PORT` (default `7879`)
- `COPILOT_TIMEOUT_SECONDS` (default `1800`)
- `COPILOT_HOME` (default `/workspace/home/root`)
- `COPILOT_XDG_CONFIG_HOME` (default `/workspace/home/root/.config`)
- `COPILOT_CWD` (default `/workspace`)

## API

- `GET /status`
- `POST /chat` JSON:
  - `prompt` (required)
  - `cwd` (optional; must be under `/workspace`)
  - `allow_all_tools` (default true)
  - `allow_all_paths` (default true)
  - `allow_all_urls` (default false)
