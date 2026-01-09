#!/usr/bin/env bash
set -euo pipefail

if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"

# Workspace layout (avoid chmod/chown loops on mounted volumes)
mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,logs,cache,config,home} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,ipython,xdg,xdg-data,code-server}
mkdir -p "$WORKSPACE_ROOT/outputs"/{comfy,invoke}
mkdir -p "$WORKSPACE_ROOT/datasets"/{images,ZIPs}
mkdir -p "$WORKSPACE_ROOT/apps"/{comfy,diffusion-pipe,invoke,kohya,codeserver}

# Seed bundled apps into workspace (without clobbering existing)
if [ -d /opt/pilot/apps ]; then
  for src in /opt/pilot/apps/*; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    dest="$WORKSPACE_ROOT/apps/$name"
    if [ ! -e "$dest" ]; then
      cp -a "$src" "$dest"
    fi
  done
  find "$WORKSPACE_ROOT/apps" -type f -name '*.sh' -print0 | xargs -0 -r chmod +x || true
fi

# Standard model subdirectories (no chown to avoid RunPod volume issues)
mkdir -p "$WORKSPACE_ROOT/models"/{audio_encoders,checkpoints,clip,clip_vision,configs,controlnet,diffusers,diffusion_models,embeddings,gligen,hypernetworks,latent_upscale_models,loras,model_patches,photomaker,style_models,text_encoders,unet,upscale_models,vae,vae_approx}

# HOME should be on workspace so it's writable (but Jupyter runtime must be /tmp)
export HOME="${HOME:-$WORKSPACE_ROOT/home/root}"
mkdir -p "$HOME"
mkdir -p "$HOME/.triton/autotune" || true

# These should be on workspace (writable). Runtime moved later by start-jupyter.sh.
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"

export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-$WORKSPACE_ROOT/config/jupyter}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-$WORKSPACE_ROOT/cache/jupyter}"
export IPYTHONDIR="${IPYTHONDIR:-$WORKSPACE_ROOT/cache/ipython}"

export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-$WORKSPACE_ROOT/apps/codeserver/data}"
export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-$WORKSPACE_ROOT/apps/codeserver/config}"

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
: "${SUPERVISOR_ADMIN_PASSWORD:=$(openssl rand -hex 32)}"

cat > "$SECRETS_FILE" <<EOT
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
export SUPERVISOR_ADMIN_PASSWORD="${SUPERVISOR_ADMIN_PASSWORD}"
EOT

chmod 600 "$SECRETS_FILE" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: $WORKSPACE_ROOT"
echo "Jupyter:     http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443} (password in ${SECRETS_FILE})"
echo "ComfyUI:     http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:       http://<host>:${KOHYA_PORT:-6666}"
echo "DiffPipe TB: http://<host>:${DIFFPIPE_PORT:-4444}"
echo "Invoke:      http://<host>:${INVOKE_PORT:-9090}"

umask "${UMASK:-0022}"
