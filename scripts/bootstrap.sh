#!/usr/bin/env bash
set -euo pipefail

# Load defaults (bash-safe)
if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PILOT_UID="${PILOT_UID:-1000}"
PILOT_GID="${PILOT_GID:-1000}"

mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg}

# Ensure the 'pilot' user exists with the right ids (RunPod sometimes cares)
if ! id -u pilot >/dev/null 2>&1; then
  groupadd -g "$PILOT_GID" pilot || true
  useradd -m -s /bin/bash -u "$PILOT_UID" -g "$PILOT_GID" pilot || true
fi

# If workspace is owned by root (common on bind mounts), fix it once.
# On huge dirs this can be slow, so we do a cheap check first.
if [ "$(stat -c '%u' "$WORKSPACE_ROOT")" != "$(id -u pilot)" ]; then
  chown -R pilot:pilot "$WORKSPACE_ROOT" || true
fi

# Runtime dirs must live in /workspace (no /root writes)
export HOME=/home/pilot
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"

export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-$WORKSPACE_ROOT/cache/jupyter/runtime}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/cache/code-server}"
export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-$WORKSPACE_ROOT/config/code-server}"

mkdir -p \
  "$JUPYTER_RUNTIME_DIR" \
  "$JUPYTER_DATA_DIR" \
  "$IPYTHONDIR" \
  "$CODE_SERVER_DATA_DIR" \
  "$CODE_SERVER_CONFIG_DIR"

# Generate secrets once (persisted in workspace)
SECRETS_FILE="$WORKSPACE_ROOT/config/secrets.env"
if [ ! -f "$SECRETS_FILE" ]; then
  CODE_SERVER_PASSWORD="$(openssl rand -hex 16)"
  JUPYTER_TOKEN="$(openssl rand -hex 16)"
  cat > "$SECRETS_FILE" <<EOT
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
EOT
  chmod 600 "$SECRETS_FILE"
  chown pilot:pilot "$SECRETS_FILE" || true
fi

# Load secrets into environment for current process
# shellcheck disable=SC1090
source "$SECRETS_FILE"

# Write code-server config (password auth)
cat > "$CODE_SERVER_CONFIG_DIR/config.yaml" <<EOT
bind-addr: 0.0.0.0:${CODE_SERVER_PORT:-8443}
auth: password
password: ${CODE_SERVER_PASSWORD}
cert: false
disable-telemetry: true
EOT
chown -R pilot:pilot "$WORKSPACE_ROOT/config" "$WORKSPACE_ROOT/cache" || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in ${SECRETS_FILE})"
