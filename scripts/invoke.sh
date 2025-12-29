#!/usr/bin/env bash
set -euo pipefail

PORT="${INVOKE_PORT:-9090}"
ROOT="${WORKSPACE_ROOT:-/workspace}/invokeai"
mkdir -p "$ROOT"

export INVOKEAI_ROOT="$ROOT"
export INVOKEAI_HOST="${INVOKEAI_HOST:-0.0.0.0}"
export INVOKEAI_PORT="${INVOKEAI_PORT:-$PORT}"

# Always run Invoke from its own venv
source /opt/venvs/invoke/bin/activate

# Nuke any accidental "config.yaml" we wrote in older attempts
# (Invoke uses invokeai.yaml / app_config in a different place)
if [ -f "$ROOT/config.yaml" ]; then
  mv "$ROOT/config.yaml" "$ROOT/config.yaml.broken.$(date +%s)" || true
fi

exec invokeai-web --root "$ROOT"