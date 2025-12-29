#!/usr/bin/env bash
set -euo pipefail

if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"

# Workspace layout (avoid chmod/chown loops on mounted volumes)
mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config,home} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,ipython,xdg,xdg-data,code-server}

# HOME should be on workspace so it's writable (but Jupyter runtime must be /tmp)
export HOME="${HOME:-$WORKSPACE_ROOT/home/root}"
mkdir -p "$HOME"

# These should be on workspace (writable). Runtime moved later by start-jupyter.sh.
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"

export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/cache/code-server}"
export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-$WORKSPACE_ROOT/config/code-server}"

# Secrets (write with strict perms)
SECRETS_FILE="$WORKSPACE_ROOT/config/secrets.env"
mkdir -p "$(dirname "$SECRETS_FILE")"

umask 077
if [ -f "$SECRETS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE" || true
fi

: "${JUPYTER_TOKEN:=$(openssl rand -hex 16)}"
: "${CODE_SERVER_PASSWORD:=$(openssl rand -hex 16)}"

cat > "$SECRETS_FILE" <<EOT
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
EOT

chmod 600 "$SECRETS_FILE" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: $WORKSPACE_ROOT"
echo "Jupyter:     http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443} (password in ${SECRETS_FILE})"
echo "ComfyUI:     http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:       http://<host>:${KOHYA_PORT:-6666}"
echo "Invoke:      http://<host>:${INVOKE_PORT:-9090}"
