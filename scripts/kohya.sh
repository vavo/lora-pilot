#!/usr/bin/env bash
set -euo pipefail
PORT="${KOHYA_PORT:-6666}"
exec /opt/venvs/core/bin/python /opt/pilot/repos/kohya_ss/kohya_gui.py --listen 0.0.0.0 --server_port "$PORT" --headless
