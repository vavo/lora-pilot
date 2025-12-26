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
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config,inputs} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg}

# Ensure pilot exists (RunPod sometimes cares)
if ! id -u pilot >/dev/null 2>&1; then
  groupadd -g "$PILOT_GID" pilot || true
  useradd -m -s /bin/bash -u "$PILOT_UID" -g "$PILOT_GID" pilot || true
fi

# Workspace permissions (best effort; bind mounts can be weird)
chown -R pilot:pilot "$WORKSPACE_ROOT" || true
chmod -R a+rwx "$WORKSPACE_ROOT" || true

# Secrets: prefer env values if provided, otherwise persist/generate once
SECRETS_FILE="$WORKSPACE_ROOT/config/secrets.env"
touch "$SECRETS_FILE" || true

# Load existing secrets if present
# shellcheck disable=SC1090
source "$SECRETS_FILE" 2>/dev/null || true

export JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-}"

if [ -z "${JUPYTER_TOKEN}" ]; then
  JUPYTER_TOKEN="$(openssl rand -hex 16)"
  export JUPYTER_TOKEN
fi

if [ -z "${CODE_SERVER_PASSWORD}" ]; then
  CODE_SERVER_PASSWORD="$(openssl rand -hex 16)"
  export CODE_SERVER_PASSWORD
fi

# Save secrets (overwrite file to avoid duplicates)
cat > "$SECRETS_FILE" <<EOF
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
EOF
chmod 600 "$SECRETS_FILE" || true
chown pilot:pilot "$SECRETS_FILE" || true

# Runtime dirs must live in /workspace (avoid /root and keep persistence on RunPod)
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
  "$JUPYTER_DATA_DIR" \
  "$JUPYTER_RUNTIME_DIR" \
  "$IPYTHONDIR" \
  "$CODE_SERVER_DATA_DIR" \
  "$CODE_SERVER_CONFIG_DIR"

# Wire ComfyUI storage into /workspace (apps in image, data in workspace)
COMFY_DIR="/opt/pilot/repos/ComfyUI"
if [ -d "$COMFY_DIR" ]; then
  ln -sfn "$WORKSPACE_ROOT/models"       "$COMFY_DIR/models"
  ln -sfn "$WORKSPACE_ROOT/custom_nodes" "$COMFY_DIR/custom_nodes"
  ln -sfn "$WORKSPACE_ROOT/outputs"      "$COMFY_DIR/output"
  ln -sfn "$WORKSPACE_ROOT/inputs"       "$COMFY_DIR/input"
  mkdir -p "$WORKSPACE_ROOT/cache/comfy"
  ln -sfn "$WORKSPACE_ROOT/cache/comfy"  "$COMFY_DIR/temp" || true
fi

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: $WORKSPACE_ROOT"
echo "Jupyter:     http://<host>:${JUPYTER_PORT:-8888}/lab?token=<see $SECRETS_FILE>"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in $SECRETS_FILE)"
echo "ComfyUI:     http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:       http://<host>:${KOHYA_PORT:-6666}"
