#!/usr/bin/env bash
set -euo pipefail

cd /opt/pilot/repos/ComfyUI

HOST="0.0.0.0"
PORT="${COMFY_PORT:-5555}"

# Prefer workspace dirs but don't die if they are read-only
mkdir -p /workspace/models /workspace/custom_nodes /workspace/outputs 2>/dev/null || true

exec /opt/venvs/core/bin/python -u main.py \
  --listen "$HOST" \
  --port "$PORT" \
  --output-directory /workspace/outputs
