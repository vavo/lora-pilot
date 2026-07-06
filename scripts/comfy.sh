#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${COMFY_PORT:-5555}"
COMFY_DIR="/opt/pilot/repos/ComfyUI"
OUT_DIR="$WORKSPACE_ROOT/outputs/comfy"
USER_DIR="$WORKSPACE_ROOT/apps/comfy/user"
CUSTOM_NODES_DIR="$WORKSPACE_ROOT/apps/comfy/custom_nodes"
MODELS_ROOT="$WORKSPACE_ROOT/models"
ensure_model_dirs() {
  mkdir -p "$MODELS_ROOT"/{audio_encoders,checkpoints,clip,clip_vision,configs,controlnet,diffusers,diffusion_models,embeddings,gligen,hypernetworks,latent_upscale_models,loras,model_patches,photomaker,style_models,text_encoders,unet,upscale_models,vae,vae_approx}
}
configure_comfy_manager() {
  local config_path="${USER_DIR}/__manager/config.ini"
  COMFY_MANAGER_CONFIG_PATH="${config_path}" \
  COMFY_MANAGER_NETWORK_MODE="${COMFY_MANAGER_NETWORK_MODE:-personal_cloud}" \
  COMFY_MANAGER_SECURITY_LEVEL="${COMFY_MANAGER_SECURITY_LEVEL:-normal}" \
  COMFY_MANAGER_ALLOW_GIT_URL_INSTALL="${COMFY_MANAGER_ALLOW_GIT_URL_INSTALL:-}" \
  COMFY_MANAGER_ALLOW_PIP_INSTALL="${COMFY_MANAGER_ALLOW_PIP_INSTALL:-}" \
  python - <<'PY'
import configparser
import os
from pathlib import Path

config_path = Path(os.environ["COMFY_MANAGER_CONFIG_PATH"])
config_path.parent.mkdir(parents=True, exist_ok=True)

config = configparser.ConfigParser(strict=False)
config.read(config_path)
if not config.has_section("default"):
    config["default"] = {}

default = config["default"]
choices = {
    "network_mode": ("COMFY_MANAGER_NETWORK_MODE", {"public", "private", "offline", "personal_cloud"}),
    "security_level": ("COMFY_MANAGER_SECURITY_LEVEL", {"strong", "normal", "normal-", "weak"}),
}
for key, (env_name, allowed) in choices.items():
    value = os.environ[env_name].strip().lower()
    if value not in allowed:
        raise SystemExit(f"{env_name} must be one of: {', '.join(sorted(allowed))}")
    default[key] = value

bool_aliases = {
    "true": "true",
    "1": "true",
    "yes": "true",
    "on": "true",
    "false": "false",
    "0": "false",
    "no": "false",
    "off": "false",
}
for key, env_name in (
    ("allow_git_url_install", "COMFY_MANAGER_ALLOW_GIT_URL_INSTALL"),
    ("allow_pip_install", "COMFY_MANAGER_ALLOW_PIP_INSTALL"),
):
    raw = os.environ.get(env_name, "").strip().lower()
    if not raw:
        continue
    if raw not in bool_aliases:
        raise SystemExit(f"{env_name} must be true or false")
    default[key] = bool_aliases[raw]

with config_path.open("w") as config_file:
    config.write(config_file)
PY
}
link_optional_asset_dir() {
  local target_dir="$1"
  [ -d "$target_dir" ] || return 0
  ln -sf "${USER_CSS}" "${target_dir}/user.css"
  ln -sf "${USERDATA}" "${target_dir}/userdata"
  ln -sf "${TEMPLATES}" "${target_dir}/comfy.templates.json"
}

# Stable, writable "home" and caches (RunPod volumes + root-owned /home is common)
export HOME="${HOME:-$WORKSPACE_ROOT/home/root}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKSPACE_ROOT/cache/xdg}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKSPACE_ROOT/config/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKSPACE_ROOT/cache/xdg-data}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$WORKSPACE_ROOT/cache/pip}"

mkdir -p \
  "$WORKSPACE_ROOT/logs" \
  "$WORKSPACE_ROOT/outputs" \
  "$OUT_DIR" \
  "$CUSTOM_NODES_DIR" \
  "$USER_DIR" \
  "$WORKSPACE_ROOT/models" \
  "$HOME" \
  "$XDG_CACHE_HOME" \
  "$XDG_CONFIG_HOME" \
  "$XDG_DATA_HOME" \
  "$PIP_CACHE_DIR"

# Use core venv
source /opt/venvs/core/bin/activate
ensure_model_dirs

# Create optional user assets so ComfyUI doesn't spam 404s in console
USER_CSS="${USER_DIR}/user.css"
USERDATA="${USER_DIR}/userdata"
TEMPLATES="${USER_DIR}/comfy.templates.json"
if [ ! -f "$USER_CSS" ]; then
  printf '/* Custom ComfyUI user styles */\n' > "$USER_CSS"
fi
if [ ! -f "$USERDATA" ]; then
  printf '{}\n' > "$USERDATA"
fi
if [ ! -f "$TEMPLATES" ]; then
  printf '[]\n' > "$TEMPLATES"
fi
configure_comfy_manager

CPU_FLAG=""
if ! python - <<'PY'
import torch, sys
sys.exit(0 if torch.cuda.is_available() else 1)
PY
then
  CPU_FLAG="--cpu"
fi

rm -rf "${COMFY_DIR}/user"
ln -s "${USER_DIR}" "${COMFY_DIR}/user"
# Expose user assets in all common frontend/static roots.
link_optional_asset_dir "${COMFY_DIR}"
link_optional_asset_dir "${COMFY_DIR}/web"
link_optional_asset_dir "${COMFY_DIR}/web/static"
link_optional_asset_dir "${COMFY_DIR}/web/assets"
link_optional_asset_dir "${COMFY_DIR}/web/dist"

# Mirror user assets into installed frontend package roots if present.
FRONTEND_STATIC_DIRS="$(
  python - <<'PY' || true
import importlib.util
import pathlib

seen = set()
for module_name in ("comfyui_frontend_package", "comfyui_frontend"):
    spec = importlib.util.find_spec(module_name)
    if not spec or not spec.origin:
        continue
    pkg_dir = pathlib.Path(spec.origin).resolve().parent
    for rel in ("static", "dist", "web", "web/static", "web/dist"):
        candidate = pkg_dir / rel
        if candidate.is_dir():
            s = str(candidate)
            if s not in seen:
                seen.add(s)
                print(s)
PY
)"
if [[ -n "${FRONTEND_STATIC_DIRS}" ]]; then
  while IFS= read -r frontend_dir; do
    [[ -n "${frontend_dir}" ]] || continue
    link_optional_asset_dir "${frontend_dir}"
  done <<< "${FRONTEND_STATIC_DIRS}"
fi
# Manager is enabled through ComfyUI's built-in comfyui_manager package with its legacy UI.
for stale_manager_dir in "${CUSTOM_NODES_DIR}/ComfyUI-Manager" "${CUSTOM_NODES_DIR}/comfyui-manager"; do
  if [ -d "${stale_manager_dir}" ]; then
    rm -rf "${stale_manager_dir}"
  fi
done
# Ensure ComfyUI-Downloader is present in workspace custom_nodes before rewiring
if [ ! -d "${CUSTOM_NODES_DIR}/ComfyUI-Downloader" ] && [ -d "/opt/pilot/bundled/comfy-custom-nodes/ComfyUI-Downloader" ]; then
  mkdir -p "${CUSTOM_NODES_DIR}"
  cp -a "/opt/pilot/bundled/comfy-custom-nodes/ComfyUI-Downloader" "${CUSTOM_NODES_DIR}/"
fi
# Point Comfy models to the shared workspace tree
rm -rf "${COMFY_DIR}/models"
ln -s "${WORKSPACE_ROOT}/models" "${COMFY_DIR}/models"
# Point Comfy custom nodes to workspace apps/comfy/custom_nodes
rm -rf "${COMFY_DIR}/custom_nodes"
ln -s "${CUSTOM_NODES_DIR}" "${COMFY_DIR}/custom_nodes"
cd "$COMFY_DIR"

exec python main.py \
  --listen 0.0.0.0 \
  --port "$PORT" \
  --enable-manager-legacy-ui \
  --output-directory "$OUT_DIR" \
  $CPU_FLAG
