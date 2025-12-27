#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${COMFY_PORT:-5555}"
ROOT="${WORKSPACE_ROOT:-/workspace}"

export PATH="/opt/venvs/core/bin:$PATH"
export PYTHONUNBUFFERED=1

mkdir -p "$ROOT/outputs" "$ROOT/comfy/user" "$ROOT/logs"

# Ensure Comfy's user dir points to workspace (writable)
if [ ! -L /opt/pilot/repos/ComfyUI/user ]; then
  rm -rf /opt/pilot/repos/ComfyUI/user || true
  ln -s "$ROOT/comfy/user" /opt/pilot/repos/ComfyUI/user || true
fi

cd /opt/pilot/repos/ComfyUI
exec /opt/venvs/core/bin/python -u main.py \
  --listen "$HOST" \
  --port "$PORT" \
  --output-directory "$ROOT/outputs"
