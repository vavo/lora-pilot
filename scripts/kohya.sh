#!/usr/bin/env bash
set -euo pipefail

cd /opt/pilot/repos/kohya_ss

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"

# Run python Gradio entry directly using the core venv.
# Do NOT call gui.sh (it expects kohya's own venv/conda).
exec /opt/venvs/core/bin/python -u kohya_gui.py \
  --listen "$HOST" \
  --server_port "$PORT"
