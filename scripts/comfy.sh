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
# Ensure ComfyUI-Manager is present in workspace custom_nodes before rewiring
if [ ! -d "${CUSTOM_NODES_DIR}/ComfyUI-Manager" ] && [ -d "/opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Manager" ]; then
  mkdir -p "${CUSTOM_NODES_DIR}"
  cp -a "/opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Manager" "${CUSTOM_NODES_DIR}/"
fi
# Ensure ComfyUI-Downloader is present in workspace custom_nodes before rewiring
if [ ! -d "${CUSTOM_NODES_DIR}/ComfyUI-Downloader" ] && [ -d "/opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Downloader" ]; then
  mkdir -p "${CUSTOM_NODES_DIR}"
  cp -a "/opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Downloader" "${CUSTOM_NODES_DIR}/"
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
  --output-directory "$OUT_DIR" \
  $CPU_FLAG
