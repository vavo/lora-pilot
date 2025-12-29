#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"

# Load secrets so JUPYTER_TOKEN is actually set (otherwise you get "auth disabled")
if [ -f "${WORKSPACE_ROOT}/config/secrets.env" ]; then
  # shellcheck disable=SC1090
  source "${WORKSPACE_ROOT}/config/secrets.env"
fi

# Writable HOME on workspace (fine), but runtime MUST be on local FS (/tmp) to allow chmod 0600
export HOME="${HOME:-${WORKSPACE_ROOT}/home/root}"
mkdir -p "$HOME" || true

# Force runtime dirs to /tmp so secure_write() can chmod properly
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg-runtime-root}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-/tmp/jupyter-runtime}"
mkdir -p "$XDG_RUNTIME_DIR" "$JUPYTER_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR" "$JUPYTER_RUNTIME_DIR" || true

# Keep config/data where you want them
export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"
mkdir -p "$JUPYTER_CONFIG_DIR" "$JUPYTER_DATA_DIR" "$IPYTHONDIR"

# Make sure Jupyter doesn't generate group/world-writable files
umask 077

exec /opt/venvs/tools/bin/jupyter-lab \
  --ip=0.0.0.0 \
  --port="$JUPYTER_PORT" \
  --no-browser \
  --ServerApp.allow_origin='*' \
  --ServerApp.allow_remote_access=True \
  --ServerApp.root_dir="$WORKSPACE_ROOT" \
  --ServerApp.token="${JUPYTER_TOKEN:-}"
