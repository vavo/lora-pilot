#!/usr/bin/env bash
set -euo pipefail

PORT="${INVOKE_PORT:-9090}"
ROOT="${WORKSPACE_ROOT:-/workspace}/invokeai"

mkdir -p "$ROOT"

# Prefer a stable CLI across versions: "invokeai-web --root ..."
# Many builds no longer accept --host/--port. We'll bind via env / uvicorn if supported,
# otherwise just run and let the reverse-proxy / runpod handle the mapping.
export INVOKEAI_ROOT="$ROOT"
export INVOKEAI_HOST="${INVOKEAI_HOST:-0.0.0.0}"
export INVOKEAI_PORT="${INVOKEAI_PORT:-$PORT}"

# Activate Invoke venv (separate from core venv)
source /opt/venvs/invoke/bin/activate

# Try modern CLI first; fall back if flags differ.
if invokeai-web --help 2>&1 | grep -q -- '--root'; then
  exec invokeai-web --root "$ROOT"
fi

# Fallback: some versions use "invokeai" entrypoint
if command -v invokeai >/dev/null 2>&1; then
  exec invokeai
fi

echo "No InvokeAI web entrypoint found in /opt/venvs/invoke. Installed packages:"
pip list | sed -n '1,120p'
exit 1
