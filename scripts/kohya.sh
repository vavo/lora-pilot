#!/usr/bin/env bash
set -euo pipefail
cd /opt/pilot/repos/kohya_ss

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"

# Prefer the repo's RunPod/headless entrypoints if they exist
if [ -f "./setup-runpod.sh" ]; then
  # runpod setup script isn't the server, but repo often pairs it with runpod requirements
  :
fi

# Try common headless launchers (varies by kohya versions)
if [ -f "./gui.sh" ]; then
  # many kohya builds use gui.sh but it may still depend on desktop libs
  exec bash ./gui.sh --listen "$HOST" --server_port "$PORT"
fi

# Fallback: run the python entry, but ensure it binds to host/port
# (if this still imports easygui, the Dockerfile shim + tk package will cover it)
exec /opt/venvs/core/bin/python -u kohya_gui.py --listen "$HOST" --server_port "$PORT"
