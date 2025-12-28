#!/usr/bin/env bash
set -euo pipefail

# Load defaults (but do not let them force unwritable paths)
if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PILOT_UID="${PILOT_UID:-1000}"
PILOT_GID="${PILOT_GID:-1000}"

# RunPod-friendly "home": put all user state under the mounted workspace
PILOT_HOME="${PILOT_HOME:-$WORKSPACE_ROOT/home/pilot}"

# Create directories we actually need (keep it tight)
mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config,home} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,ipython,xdg,xdg-data,code-server} \
  "$PILOT_HOME"/{.config,.cache,.local/share}

# Ensure user exists (in image it's usually already there, but keep it safe)
if ! id -u pilot >/dev/null 2>&1; then
  groupadd -g "$PILOT_GID" pilot 2>/dev/null || true
  useradd -m -s /bin/bash -u "$PILOT_UID" -g "$PILOT_GID" pilot 2>/dev/null || true
fi

# Do NOT recursively chown the workspace. On RunPod volumes this often fails.
# Instead only try to chown the pilot home directory (and ignore failures).
chown -R pilot:pilot "$PILOT_HOME" 2>/dev/null || true
chown -R pilot:pilot "$WORKSPACE_ROOT/cache" 2>/dev/null || true
chown -R pilot:pilot "$WORKSPACE_ROOT/config" 2>/dev/null || true
chown -R pilot:pilot "$WORKSPACE_ROOT/logs" 2>/dev/null || true
chown -R pilot:pilot "$WORKSPACE_ROOT/outputs" 2>/dev/null || true

# Environment: everything points to writable workspace locations
export WORKSPACE_ROOT
export HOME="$PILOT_HOME"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$PILOT_HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PILOT_HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$PILOT_HOME/.local/share}"

export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-$WORKSPACE_ROOT/cache/jupyter/runtime}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/cache/code-server}"
export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-$WORKSPACE_ROOT/config/code-server}"

mkdir -p \
  "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" \
  "$JUPYTER_CONFIG_DIR" "$JUPYTER_DATA_DIR" "$JUPYTER_RUNTIME_DIR" \
  "$IPYTHONDIR" \
  "$CODE_SERVER_DATA_DIR" "$CODE_SERVER_CONFIG_DIR"

# Secrets (atomic write, no chown required)
SECRETS_FILE="$WORKSPACE_ROOT/config/secrets.env"
umask 077

# If it exists, load it
if [ -f "$SECRETS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE" || true
fi

: "${JUPYTER_TOKEN:=$(openssl rand -hex 16)}"
: "${CODE_SERVER_PASSWORD:=$(openssl rand -hex 16)}"

tmp="$(mktemp)"
cat > "$tmp" <<EOT
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
EOT

# Move into place. If the volume is weirdly immutable, don't crash boot.
if mv -f "$tmp" "$SECRETS_FILE" 2>/dev/null; then
  chmod 600 "$SECRETS_FILE" 2>/dev/null || true
else
  rm -f "$tmp" || true
fi

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in ${SECRETS_FILE})"
echo "ComfyUI: http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:   http://<host>:${KOHYA_PORT:-6666}"
echo "OneTrainer: http://<host>:${ONETRAINER_PORT:-4444}  (/vnc.html)"
