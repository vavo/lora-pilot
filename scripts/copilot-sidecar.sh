#!/usr/bin/env bash
set -euo pipefail

PORT="${COPILOT_SIDECAR_PORT:-7879}"
APP_DIR="/opt/pilot/apps/CopilotSidecar"

# Persist Copilot CLI config/auth under /workspace
export HOME="${COPILOT_HOME:-/workspace/home/root}"
# Match the image defaults so auth done in an interactive shell is visible to the sidecar.
export XDG_CONFIG_HOME="${COPILOT_XDG_CONFIG_HOME:-/workspace/home/root/.config}"

mkdir -p "$HOME" "$XDG_CONFIG_HOME"

source /opt/venvs/core/bin/activate
exec uvicorn app:app --host 127.0.0.1 --port "${PORT}" --app-dir "${APP_DIR}"
