#!/usr/bin/env bash
set -euo pipefail

PORT="${INVOKE_PORT:-9090}"
ROOT="${WORKSPACE_ROOT:-/workspace}/invokeai"
mkdir -p "$ROOT"
mkdir -p "${WORKSPACE_ROOT:-/workspace}/models"
OUT_DIR="${WORKSPACE_ROOT:-/workspace}/outputs/invoke"
mkdir -p "$OUT_DIR"

export INVOKEAI_ROOT="$ROOT"
export INVOKEAI_HOST="${INVOKEAI_HOST:-0.0.0.0}"
export INVOKEAI_PORT="${INVOKEAI_PORT:-$PORT}"

# Always run Invoke from its own venv
source /opt/venvs/invoke/bin/activate

# Point InvokeAI models to shared workspace tree if supported
if invokeai-config --help >/dev/null 2>&1; then
  invokeai-config --root "$ROOT" set ModelsDir "${WORKSPACE_ROOT:-/workspace}/models" >/dev/null 2>&1 || true
  invokeai-config --root "$ROOT" set OutputDir "$OUT_DIR" >/dev/null 2>&1 || true
fi
# Fallback: ensure Invoke's default models path points at the shared workspace tree
if [ ! -e "$ROOT/models" ]; then
  ln -s "${WORKSPACE_ROOT:-/workspace}/models" "$ROOT/models"
fi
if [ ! -e "$ROOT/outputs" ]; then
  ln -s "$OUT_DIR" "$ROOT/outputs"
fi

# Nuke any accidental "config.yaml" we wrote in older attempts
# (Invoke uses invokeai.yaml / app_config in a different place)
if [ -f "$ROOT/config.yaml" ]; then
  mv "$ROOT/config.yaml" "$ROOT/config.yaml.broken.$(date +%s)" || true
fi

exec invokeai-web --root "$ROOT"
