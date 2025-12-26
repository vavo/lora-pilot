#!/usr/bin/env bash
set -euo pipefail

if [ -f /opt/pilot/config/env.defaults ]; then
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PILOT_UID="${PILOT_UID:-1000}"
PILOT_GID="${PILOT_GID:-1000}"

mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,ipython,xdg,xdg-data,code-server}

if ! id -u pilot >/dev/null 2>&1; then
  groupadd -g "$PILOT_GID" pilot || true
  useradd -m -s /bin/bash -u "$PILOT_UID" -g "$PILOT_GID" pilot || true
fi

if [ "$(stat -c '%u' "$WORKSPACE_ROOT")" != "$(id -u pilot)" ]; then
  chown -R pilot:pilot "$WORKSPACE_ROOT" 2>/dev/null || true
fi

export HOME=/home/pilot
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"

export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-$WORKSPACE_ROOT/cache/jupyter/runtime}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/cache/code-server}"
export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-$WORKSPACE_ROOT/config/code-server}"

SECRETS_FILE="$WORKSPACE_ROOT/config/secrets.env"
mkdir -p "$(dirname "$SECRETS_FILE")"
umask 077

if [ -f "$SECRETS_FILE" ]; then
  source "$SECRETS_FILE" || true
fi

if [ -z "${JUPYTER_TOKEN:-}" ]; then
  JUPYTER_TOKEN="$(openssl rand -hex 16)"
fi

if [ -z "${CODE_SERVER_PASSWORD:-}" ]; then
  CODE_SERVER_PASSWORD="$(openssl rand -hex 16)"
fi

cat > "$SECRETS_FILE" <<EOT
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
EOT

chown pilot:pilot "$SECRETS_FILE" || true
chmod 600 "$SECRETS_FILE" || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: /workspace"
echo "Jupyter:  http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in ${SECRETS_FILE})"
echo "ComfyUI: http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:   http://<host>:${KOHYA_PORT:-6666}"
