#!/usr/bin/env bash
set -euo pipefail
cd /opt/pilot/repos/kohya_ss

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"

# Prefer official launcher if present
if [ -f "./gui.sh" ]; then
  exec bash ./gui.sh --listen "$HOST" --server_port "$PORT"
fi

# Fallback
exec /opt/venvs/core/bin/python -u kohya_gui.py --listen "$HOST" --server_port "$PORT"
