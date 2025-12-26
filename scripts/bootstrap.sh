#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PILOT_UID="${PILOT_UID:-1000}"
PILOT_GID="${PILOT_GID:-1000}"

mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,custom_nodes,logs,cache,config} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,jupyter/runtime,code-server,xdg,xdg-data,ipython}

# Ensure pilot user exists
if ! id -u pilot >/dev/null 2>&1; then
  groupadd -g "$PILOT_GID" pilot || true
  useradd -m -s /bin/bash -u "$PILOT_UID" -g "$PILOT_GID" pilot || true
fi

# Make workspace writable by pilot (RunPod volume usually OK, bind mounts vary)
chown -R pilot:pilot "$WORKSPACE_ROOT" || true

# Secrets (persist in /workspace)
SECRETS="$WORKSPACE_ROOT/config/secrets.env"
if [ ! -f "$SECRETS" ]; then
  JUPYTER_TOKEN="${JUPYTER_TOKEN:-$(openssl rand -hex 16)}"
  CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-$(openssl rand -hex 16)}"
  cat >"$SECRETS" <<EOF
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
EOF
  chown pilot:pilot "$SECRETS" || true
fi

# Load secrets into env for supervisord + apps
# shellcheck disable=SC1090
source "$SECRETS"
export PASSWORD="${CODE_SERVER_PASSWORD}"   # code-server reads PASSWORD

# Persist “user-ish” config into /workspace instead of /home/pilot when possible
export HOME=/home/pilot
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"

export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-$WORKSPACE_ROOT/cache/jupyter/runtime}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/cache/code-server}"
export CODE_SERVER_EXTENSIONS_DIR="${CODE_SERVER_EXTENSIONS_DIR:-$WORKSPACE_ROOT/cache/code-server/extensions}"

# ComfyUI: make it use /workspace models via extra_model_paths.yaml (ComfyUI auto-loads it)
if [ -d /opt/pilot/repos/ComfyUI ]; then
  cat > /opt/pilot/repos/ComfyUI/extra_model_paths.yaml <<'EOF'
runpod_workspace:
  base_path: /workspace
  checkpoints: models/checkpoints
  loras: models/loras
  vae: models/vae
  clip: models/clip
  embeddings: models/embeddings
  controlnet: models/controlnet
  upscale_models: models/upscale_models
EOF
  chown pilot:pilot /opt/pilot/repos/ComfyUI/extra_model_paths.yaml || true
fi

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace:   ${WORKSPACE_ROOT}"
echo "Jupyter:     http://<host>:8888/lab?token=${JUPYTER_TOKEN}"
echo "code-server: http://<host>:8443  (password in ${SECRETS})"
echo "ComfyUI:     http://<host>:5555"
echo "Kohya:       http://<host>:6666"
