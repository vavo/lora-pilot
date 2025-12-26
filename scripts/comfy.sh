#!/usr/bin/env bash
set -euo pipefail
PORT="${COMFY_PORT:-5555}"
exec /opt/venvs/core/bin/python /opt/pilot/repos/ComfyUI/main.py --listen 0.0.0.0 --port "$PORT"
