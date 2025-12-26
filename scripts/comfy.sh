#!/usr/bin/env bash
set -euo pipefail
cd /opt/pilot/repos/ComfyUI
exec /opt/venvs/core/bin/python main.py --listen 0.0.0.0 --port "${COMFY_PORT:-5555}"
