#!/usr/bin/env bash
set -euo pipefail

cd /opt/pilot/repos/ComfyUI

HOST="0.0.0.0"
PORT="${COMFY_PORT:-5555}"

# Persisted writable dirs on RunPod
mkdir -p /workspace/models /workspace/custom_nodes /workspace/outputs /workspace/comfy-user 2>/dev/null || true

# Install ComfyUI-Manager once (persisted on /workspace volume)
if [ ! -d "/workspace/custom_nodes/ComfyUI-Manager/.git" ]; then
  echo "[comfy] Installing ComfyUI-Manager into /workspace/custom_nodes..."
  git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git /workspace/custom_nodes/ComfyUI-Manager || true
fi

# Make sure ComfyUI sees custom_nodes from workspace
export COMFYUI_CUSTOM_NODES_DIR="/workspace/custom_nodes"

# Prevent permission issues writing inside /opt/pilot/repos
export COMFYUI_USER_DIRECTORY="/workspace/comfy-user"

exec /opt/venvs/core/bin/python -u main.py \
  --listen "$HOST" \
  --port "$PORT" \
  --output-directory /workspace/outputs
