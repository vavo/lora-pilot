#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${COMFY_PORT:-5555}"
COMFY_DIR="/opt/pilot/repos/ComfyUI"

# Stable, writable "home" and caches (RunPod volumes + root-owned /home is common)
export HOME="${HOME:-$WORKSPACE_ROOT/home/pilot}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$WORKSPACE_ROOT/cache/pip}"

mkdir -p \
  "$WORKSPACE_ROOT/logs" \
  "$WORKSPACE_ROOT/outputs" \
  "$WORKSPACE_ROOT/models" \
  "$WORKSPACE_ROOT/custom_nodes" \
  "$HOME" \
  "$XDG_CACHE_HOME" \
  "$XDG_CONFIG_HOME" \
  "$XDG_DATA_HOME" \
  "$PIP_CACHE_DIR"

# Use core venv
source /opt/venvs/core/bin/activate

CPU_FLAG=""
if ! python - <<'PY'
import torch, sys
sys.exit(0 if torch.cuda.is_available() else 1)
PY
then
  CPU_FLAG="--cpu"
fi

cd "$COMFY_DIR"

exec python main.py \
  --listen 0.0.0.0 \
  --port "$PORT" \
  --output-directory "$WORKSPACE_ROOT/outputs" \
  $CPU_FLAG