#!/usr/bin/env bash
set -euo pipefail

cd /opt/pilot/repos/kohya_ss

# Headless web UI (Gradio) on port 6666
exec /opt/venvs/core/bin/python kohya_gui.py \
  --listen 0.0.0.0 \
  --server_port "${KOHYA_PORT:-6666}"
