#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${INVOKE_PORT:-9090}"

# Keep InvokeAI state in /workspace so it persists on RunPod volumes
export INVOKEAI_ROOT="${INVOKEAI_ROOT:-/workspace/apps/invokeai}"

mkdir -p "$INVOKEAI_ROOT" 2>/dev/null || true

# Start the web UI
exec /opt/venvs/core/bin/invokeai-web --host "$HOST" --port "$PORT"
