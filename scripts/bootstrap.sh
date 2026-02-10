#!/usr/bin/env bash
set -euo pipefail

if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"

upsert_env_var() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp="${file}.tmp.$$"
  awk -v key="$key" -v value="$value" '
    BEGIN { updated = 0 }
    $0 ~ ("^" key "=") { print key "=" value; updated = 1; next }
    { print }
    END { if (!updated) print key "=" value }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

ensure_env_var() {
  local file="$1"
  local key="$2"
  local value="$3"
  if ! grep -qE "^${key}=" "$file"; then
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

# Workspace layout (avoid chmod/chown loops on mounted volumes)
mkdir -p \
  "$WORKSPACE_ROOT"/{apps,models,datasets,outputs,logs,cache,config,home} \
  "$WORKSPACE_ROOT"/config/{jupyter,code-server,xdg} \
  "$WORKSPACE_ROOT"/cache/{jupyter,ipython,xdg,xdg-data,code-server}
mkdir -p "$WORKSPACE_ROOT/config/ai-toolkit"
mkdir -p "$WORKSPACE_ROOT/outputs"/{comfy,invoke,ai-toolkit}
mkdir -p "$WORKSPACE_ROOT/datasets"/{images,ZIPs}
mkdir -p "$WORKSPACE_ROOT/apps"/{comfy,diffusion-pipe,invoke,kohya,codeserver}

SERVICE_UPDATES_CONFIG_FILE="${SERVICE_UPDATES_CONFIG_PATH:-$WORKSPACE_ROOT/config/service-updates.toml}"
SERVICE_UPDATES_ROLLBACK_LOG="${SERVICE_UPDATES_ROLLBACK_LOG_PATH:-$WORKSPACE_ROOT/config/service-updates-rollback.jsonl}"
if [ ! -f "$SERVICE_UPDATES_CONFIG_FILE" ]; then
  cat > "$SERVICE_UPDATES_CONFIG_FILE" <<'EOT'
enabled = false
restart_after_update = true

[services.invoke]
auto_update = false
target_version = ""

[services.comfy]
auto_update = false
target_ref = ""

[services.kohya]
auto_update = false
target_ref = ""

[services.diffpipe]
auto_update = false
target_ref = ""

[services."ai-toolkit"]
auto_update = false
target_ref = ""
EOT
fi

# AI Toolkit workspace mapping (avoid storing datasets/models/outputs inside the repo)
if [ -d /opt/pilot/repos/ai-toolkit ]; then
  mkdir -p "$WORKSPACE_ROOT/datasets" "$WORKSPACE_ROOT/models" "$WORKSPACE_ROOT/outputs/ai-toolkit"
  AI_TOOLKIT_DB_PATH="${AI_TOOLKIT_DB_PATH:-$WORKSPACE_ROOT/config/ai-toolkit/aitk_db.db}"
  mkdir -p "$(dirname "$AI_TOOLKIT_DB_PATH")"
  touch "$AI_TOOLKIT_DB_PATH"

  ensure_link() {
    local link_path="$1"
    local target_path="$2"
    if [ -L "$link_path" ]; then
      local cur
      cur="$(readlink "$link_path" || true)"
      if [ "$cur" != "$target_path" ]; then
        rm -f "$link_path"
        ln -s "$target_path" "$link_path"
      fi
      return 0
    fi
    if [ -e "$link_path" ]; then
      echo "AI Toolkit: '$link_path' exists and is not a symlink; leaving as-is (expected -> $target_path)" >&2
      return 0
    fi
    ln -s "$target_path" "$link_path"
  }

  ensure_link /opt/pilot/repos/ai-toolkit/datasets "$WORKSPACE_ROOT/datasets"
  ensure_link /opt/pilot/repos/ai-toolkit/models "$WORKSPACE_ROOT/models"
  ensure_link /opt/pilot/repos/ai-toolkit/output "$WORKSPACE_ROOT/outputs/ai-toolkit"
  ensure_link /opt/pilot/repos/ai-toolkit/aitk_db.db "$AI_TOOLKIT_DB_PATH"
fi

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

# MediaPilot defaults (single-port embed under ControlPilot)
MEDIAPILOT_APP_DIR="$WORKSPACE_ROOT/apps/MediaPilot"
if [ -d "$MEDIAPILOT_APP_DIR" ]; then
  MEDIAPILOT_FORCE_ENV_DEFAULTS="${MEDIAPILOT_FORCE_ENV_DEFAULTS:-0}"
  MEDIAPILOT_ENV_CREATED="0"
  mkdir -p \
    "$WORKSPACE_ROOT/config/mediapilot" \
    "$WORKSPACE_ROOT/cache/mediapilot/thumbs"
  MEDIAPILOT_ENV_FILE="$MEDIAPILOT_APP_DIR/.env"
  if [ ! -f "$MEDIAPILOT_ENV_FILE" ] && [ -f "$MEDIAPILOT_APP_DIR/.env.example" ]; then
    cp "$MEDIAPILOT_APP_DIR/.env.example" "$MEDIAPILOT_ENV_FILE"
    MEDIAPILOT_ENV_CREATED="1"
  fi
  if [ -f "$MEDIAPILOT_ENV_FILE" ]; then
    if [ "$MEDIAPILOT_ENV_CREATED" = "1" ] || [ "$MEDIAPILOT_FORCE_ENV_DEFAULTS" = "1" ]; then
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_OUTPUT_DIR" "$WORKSPACE_ROOT/outputs/comfy"
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_INVOKEAI_DIR" "$WORKSPACE_ROOT/outputs/invoke"
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_THUMBS_DIR" "$WORKSPACE_ROOT/cache/mediapilot/thumbs"
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_DB_FILE" "$WORKSPACE_ROOT/config/mediapilot/data.db"
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_COMFY_API_URL" "http://127.0.0.1:${COMFY_PORT:-5555}"
      upsert_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_ALLOW_ORIGINS" "*"
    else
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_OUTPUT_DIR" "$WORKSPACE_ROOT/outputs/comfy"
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_INVOKEAI_DIR" "$WORKSPACE_ROOT/outputs/invoke"
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_THUMBS_DIR" "$WORKSPACE_ROOT/cache/mediapilot/thumbs"
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_DB_FILE" "$WORKSPACE_ROOT/config/mediapilot/data.db"
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_COMFY_API_URL" "http://127.0.0.1:${COMFY_PORT:-5555}"
      ensure_env_var "$MEDIAPILOT_ENV_FILE" "MEDIAPILOT_ALLOW_ORIGINS" "*"
    fi
  fi
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

if [ -n "${HF_TOKEN:-}" ]; then
  echo "export HF_TOKEN=\"${HF_TOKEN}\"" >> "$SECRETS_FILE"
fi

chmod 600 "$SECRETS_FILE" 2>/dev/null || true

SERVICE_UPDATES_BOOT_RECONCILE="${SERVICE_UPDATES_BOOT_RECONCILE:-1}"
case "${SERVICE_UPDATES_BOOT_RECONCILE}" in
  1|true|TRUE|yes|YES|on|ON)
    if [ -f /opt/pilot/service-updates-reconcile.py ]; then
      /opt/venvs/core/bin/python /opt/pilot/service-updates-reconcile.py \
        --config "$SERVICE_UPDATES_CONFIG_FILE" \
        --rollback-log "$SERVICE_UPDATES_ROLLBACK_LOG" \
        || echo "Service update reconcile failed; continuing bootstrap"
    fi
    ;;
  *)
    echo "Service update reconcile disabled (SERVICE_UPDATES_BOOT_RECONCILE=${SERVICE_UPDATES_BOOT_RECONCILE})"
    ;;
esac

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: $WORKSPACE_ROOT"
echo "Jupyter:     http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443} (password in ${SECRETS_FILE})"
echo "ComfyUI:     http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:       http://<host>:${KOHYA_PORT:-6666}"
echo "DiffPipe TB: http://<host>:${DIFFPIPE_PORT:-4444}"
echo "Invoke:      http://<host>:${INVOKE_PORT:-9090}"
if [ -d /opt/pilot/repos/ai-toolkit/ui ]; then
  echo "AI Toolkit:  http://<host>:${AI_TOOLKIT_PORT:-8675}"
fi

umask "${UMASK:-0022}"
