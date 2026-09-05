#!/usr/bin/env bash
set -euo pipefail

if [ -f /opt/pilot/config/env.defaults ]; then
  # shellcheck disable=SC1091
  source /opt/pilot/config/env.defaults
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
SERVICE_AUTOSTART_CONFIG_FILE="${SERVICE_AUTOSTART_CONFIG_PATH:-$WORKSPACE_ROOT/config/service-autostart.toml}"

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

bundle_tree_hash() {
  local dir="$1"
  (
    cd "$dir" || exit 1
    find . \
      -path './.env' -prune -o \
      -path './data' -prune -o \
      -path './__pycache__' -prune -o \
      -path './.bundle-sync-sha' -prune -o \
      -type f -print0 \
      | LC_ALL=C sort -z \
      | xargs -0 sha256sum
  ) | sha256sum | awk '{print $1}'
}

remove_stale_bundle_files() {
  local source_dir="$1"
  local target_dir="$2"
  (
    cd "$target_dir" || exit 1
    find . -type f -print0
  ) | while IFS= read -r -d '' relative_file; do
    case "$relative_file" in
      ./.env|./data/*|./__pycache__/*|*/__pycache__/*|./.bundle-sync-sha)
        continue
        ;;
    esac
    if [ ! -f "$source_dir/${relative_file#./}" ]; then
      rm -f "$target_dir/${relative_file#./}"
    fi
  done
}

sync_bundled_tree() {
  local source_dir="$1"
  local target_dir="$2"
  local marker_file="$target_dir/.bundle-sync-sha"
  local source_hash
  local recorded_hash

  source_hash="$(bundle_tree_hash "$source_dir")"
  recorded_hash=""
  if [ -f "$marker_file" ]; then
    recorded_hash="$(tr -d '\r\n' < "$marker_file")"
  fi
  if [ -n "$recorded_hash" ] && [ "$recorded_hash" = "$source_hash" ]; then
    return 0
  fi

  mkdir -p "$target_dir"
  remove_stale_bundle_files "$source_dir" "$target_dir"
  (
    cd "$source_dir" || exit 1
    tar cf - --exclude='.env' --exclude='data' --exclude='__pycache__' --exclude='.bundle-sync-sha' .
  ) | (
    cd "$target_dir" || exit 1
    tar xf -
  )
  printf '%s\n' "$source_hash" > "${marker_file}.tmp.$$"
  mv -f "${marker_file}.tmp.$$" "$marker_file"
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

# Refresh the persistent model catalogue when a new image bundles a newer
# manifest. Preserve an explicitly customized runtime manifest.
MODEL_MANIFEST_SOURCE="${DEFAULT_MODELS_MANIFEST:-/opt/pilot/config/models.manifest.default}"
MODEL_MANIFEST_TARGET="${MODELS_MANIFEST:-$WORKSPACE_ROOT/config/models.manifest}"
MODEL_MANIFEST_HASH_FILE="$WORKSPACE_ROOT/config/.models.manifest.bundle.sha256"
if [ -f "$MODEL_MANIFEST_SOURCE" ]; then
  model_manifest_source_hash="$(sha256sum "$MODEL_MANIFEST_SOURCE" | awk '{print $1}')"
  model_manifest_refresh=0
  if [ ! -f "$MODEL_MANIFEST_TARGET" ]; then
    model_manifest_refresh=1
  elif [ ! -f "$MODEL_MANIFEST_HASH_FILE" ]; then
    # First boot after this migration: replace the legacy seeded file once.
    model_manifest_refresh=1
  else
    model_manifest_recorded_hash="$(head -n 1 "$MODEL_MANIFEST_HASH_FILE" 2>/dev/null || true)"
    model_manifest_active_hash="$(sha256sum "$MODEL_MANIFEST_TARGET" | awk '{print $1}')"
    if [ "$model_manifest_active_hash" = "$model_manifest_recorded_hash" ]; then
      model_manifest_refresh=1
    else
      echo "Preserving customized model manifest: $MODEL_MANIFEST_TARGET" >&2
    fi
  fi

  if [ "$model_manifest_refresh" = "1" ]; then
    cp -f "$MODEL_MANIFEST_SOURCE" "$MODEL_MANIFEST_TARGET"
    echo "Refreshed model manifest from bundled image version"
  fi
  printf '%s\n' "$model_manifest_source_hash" > "${MODEL_MANIFEST_HASH_FILE}.tmp.$$"
  mv -f "${MODEL_MANIFEST_HASH_FILE}.tmp.$$" "$MODEL_MANIFEST_HASH_FILE"
fi

SERVICE_UPDATES_CONFIG_FILE="${SERVICE_UPDATES_CONFIG_PATH:-$WORKSPACE_ROOT/config/service-updates.toml}"
SERVICE_UPDATES_ROLLBACK_LOG="${SERVICE_UPDATES_ROLLBACK_LOG_PATH:-$WORKSPACE_ROOT/config/service-updates-rollback.jsonl}"
if [ ! -f "$SERVICE_UPDATES_CONFIG_FILE" ]; then
  cat > "$SERVICE_UPDATES_CONFIG_FILE" <<'EOT'
enabled = false
restart_after_update = true

[services.invoke]
auto_update = false
target_version = ""
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

# Refresh bundled apps into workspace while preserving runtime state.
if [ -d /opt/pilot/apps ]; then
  for src in /opt/pilot/apps/*; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    dest="$WORKSPACE_ROOT/apps/$name"
    if [ ! -e "$dest" ]; then
      mkdir -p "$dest"
    fi
    sync_bundled_tree "$src" "$dest"
  done
  find "$WORKSPACE_ROOT/apps" -type f -name '*.sh' -print0 | xargs -0 -r chmod +x || true
fi

# Refresh bundled docs into workspace while preserving a customized copy.
if [ -d /opt/pilot/docs ]; then
  mkdir -p "$WORKSPACE_ROOT/docs"
  sync_bundled_tree /opt/pilot/docs "$WORKSPACE_ROOT/docs"
fi

# MediaPilot defaults (single-port embed under ControlPilot)
MEDIAPILOT_APP_DIR="$WORKSPACE_ROOT/apps/MediaPilot"
if [ -d "$MEDIAPILOT_APP_DIR" ]; then
  MEDIAPILOT_SOURCE_DIR="/opt/pilot/apps/MediaPilot"
  MEDIAPILOT_SYNC_ON_BOOT="${MEDIAPILOT_SYNC_ON_BOOT:-1}"
  if [ "$MEDIAPILOT_SYNC_ON_BOOT" = "1" ] && [ -d "$MEDIAPILOT_SOURCE_DIR" ]; then
    mediapilot_sync_bundle() {
      local src_commit_file="$MEDIAPILOT_SOURCE_DIR/.upstream-commit"
      local dst_commit_file="$MEDIAPILOT_APP_DIR/.upstream-commit"
      local dst_hash_file="$MEDIAPILOT_APP_DIR/.bundle-sync-sha"
      local src_commit=""
      local dst_commit=""
      local src_hash=""
      local dst_hash=""
      local should_sync="0"

      src_commit="$(tr -d '\r\n' < "$src_commit_file" 2>/dev/null || true)"
      dst_commit="$(tr -d '\r\n' < "$dst_commit_file" 2>/dev/null || true)"
      dst_hash="$(tr -d '\r\n' < "$dst_hash_file" 2>/dev/null || true)"
      src_hash="$(bundle_tree_hash "$MEDIAPILOT_SOURCE_DIR" 2>/dev/null || true)"
      if [ -n "$src_hash" ] && [ -z "$dst_hash" ]; then
        dst_hash="$(bundle_tree_hash "$MEDIAPILOT_APP_DIR" 2>/dev/null || true)"
      fi

      if [ -n "$src_commit" ] && [ "$src_commit" != "$dst_commit" ]; then
        should_sync="1"
      fi
      if [ -n "$src_hash" ] && [ "$src_hash" != "$dst_hash" ]; then
        should_sync="1"
      fi

      if [ "$should_sync" != "1" ]; then
        return 0
      fi

      echo "Syncing MediaPilot workspace copy to upstream commit ${src_commit:-unknown}"
      (
        cd "$MEDIAPILOT_SOURCE_DIR" || exit 1
        tar cf - --exclude='.env' --exclude='data' --exclude='__pycache__' .
      ) | (
        cd "$MEDIAPILOT_APP_DIR" || exit 1
        tar xf -
      )

      remove_stale_bundle_files "$MEDIAPILOT_SOURCE_DIR" "$MEDIAPILOT_APP_DIR"

      if [ -n "$src_hash" ]; then
        printf '%s\n' "$src_hash" > "$dst_hash_file"
      fi
    }

    if ! mediapilot_sync_bundle; then
      echo "MediaPilot sync failed; continuing with existing workspace copy." >&2
    fi
  fi

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

# TagPilot sync: keep workspace copy aligned with bundled app updates.
TAGPILOT_APP_DIR="$WORKSPACE_ROOT/apps/TagPilot"
TAGPILOT_SOURCE_DIR="/opt/pilot/apps/TagPilot"
TAGPILOT_SYNC_ON_BOOT="${TAGPILOT_SYNC_ON_BOOT:-1}"
if [ "$TAGPILOT_SYNC_ON_BOOT" = "1" ] && [ -d "$TAGPILOT_SOURCE_DIR" ]; then
  if ! sync_bundled_tree "$TAGPILOT_SOURCE_DIR" "$TAGPILOT_APP_DIR"; then
    echo "TagPilot sync failed; continuing with existing workspace copy." >&2
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

# RunPod secret compatibility: map legacy/lowercase token name.
if [ -z "${HF_TOKEN:-}" ] && [ -n "${hf_token:-}" ]; then
  export HF_TOKEN="${hf_token}"
fi

tmp_secrets="${SECRETS_FILE}.tmp.$$"
{
  if [ -f "$SECRETS_FILE" ]; then
    grep -Ev '^(export )?(JUPYTER_TOKEN|CODE_SERVER_PASSWORD|SUPERVISOR_ADMIN_PASSWORD|HF_TOKEN)=' "$SECRETS_FILE" || true
  fi
  printf 'export JUPYTER_TOKEN="%s"\n' "$JUPYTER_TOKEN"
  printf 'export CODE_SERVER_PASSWORD="%s"\n' "$CODE_SERVER_PASSWORD"
  printf 'export SUPERVISOR_ADMIN_PASSWORD="%s"\n' "$SUPERVISOR_ADMIN_PASSWORD"
  if [ -n "${HF_TOKEN:-}" ]; then
    printf 'export HF_TOKEN="%s"\n' "$HF_TOKEN"
  fi
} > "$tmp_secrets"
mv "$tmp_secrets" "$SECRETS_FILE"
chmod 600 "$SECRETS_FILE"

chmod 600 "$SECRETS_FILE" 2>/dev/null || true

# Resolve only after persisted settings have been loaded, and use the same path
# for autostart updates, ControlPilot, and the Supervisor process itself.
export SUPERVISOR_CONFIG_PATH="${SUPERVISOR_CONFIG_PATH:-/etc/supervisor/supervisord.conf}"
SUPERVISOR_CONF="$SUPERVISOR_CONFIG_PATH"
if [ ! -f "$SUPERVISOR_CONF" ] || [ ! -r "$SUPERVISOR_CONF" ]; then
  echo "Supervisor config is missing or unreadable: $SUPERVISOR_CONF" >&2
  exit 1
fi

if [ -f /opt/pilot/service-autostart-apply.py ] && [ -f "$SUPERVISOR_CONF" ]; then
  /opt/venvs/core/bin/python /opt/pilot/service-autostart-apply.py \
    --supervisor-conf "$SUPERVISOR_CONF" \
    --state-file "$SERVICE_AUTOSTART_CONFIG_FILE" \
    || echo "Service autostart apply failed; continuing bootstrap"
fi

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
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443} (password from ${SECRETS_FILE})"
echo "ComfyUI:     http://<host>:${COMFY_PORT:-5555}"
echo "Kohya:       http://<host>:${KOHYA_PORT:-6666}"
echo "DiffPipe TB: http://<host>:${DIFFPIPE_PORT:-4444}"
echo "Invoke:      http://<host>:${INVOKE_PORT:-9090}"
if [ -d /opt/pilot/repos/ai-toolkit/ui ]; then
  echo "AI Toolkit:  http://<host>:${AI_TOOLKIT_PORT:-8675}"
fi

umask "${UMASK:-0022}"
