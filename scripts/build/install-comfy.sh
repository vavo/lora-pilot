#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_COMFY:-1}" != "1" ]]; then
  echo "Skipping ComfyUI install (INSTALL_COMFY=${INSTALL_COMFY:-0})"
  exit 0
fi

: "${COMFYUI_REF:?COMFYUI_REF is required}"
: "${COMFYUI_MANAGER_REF:?COMFYUI_MANAGER_REF is required}"
: "${COMFYUI_DOWNLOADER_REF:?COMFYUI_DOWNLOADER_REF is required}"
: "${COMFYUI_GGUF_REF:?COMFYUI_GGUF_REF is required}"
: "${COMFYUI_VHS_REF:?COMFYUI_VHS_REF is required}"

/opt/pilot/build/lib/git_checkout.sh \
  https://github.com/Comfy-Org/ComfyUI.git \
  /opt/pilot/repos/ComfyUI \
  "${COMFYUI_REF}"

grep -v -E '^(torch|torchvision|torchaudio|xformers|triton|bitsandbytes|numpy|pillow|Pillow|diffusers|transformers|peft|huggingface-hub|accelerate)' \
  /opt/pilot/repos/ComfyUI/requirements.txt > /tmp/comfy-req.txt

pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  -r /tmp/comfy-req.txt
rm -f /tmp/comfy-req.txt

manager_requirement="comfyui_manager==${COMFYUI_MANAGER_REF}"
manager_requirements_file="/opt/pilot/repos/ComfyUI/manager_requirements.txt"
if [[ ! -f "${manager_requirements_file}" ]]; then
  echo "ComfyUI manager requirements file not found: ${manager_requirements_file}" >&2
  exit 1
fi
if [[ "$(grep -Ec '^comfyui[-_]manager==[^[:space:]]+$' "${manager_requirements_file}")" != "1" ]]; then
  echo "Expected one pinned ComfyUI manager requirement" >&2
  exit 1
fi
# Keep upstream's extra dependencies while selecting our independently pinned Manager.
sed -E "s/^comfyui[-_]manager==[^[:space:]]+$/${manager_requirement}/" \
  "${manager_requirements_file}" > /tmp/comfy-manager-req.txt
pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  -r /tmp/comfy-manager-req.txt
rm -f /tmp/comfy-manager-req.txt

mkdir -p /opt/pilot/repos/ComfyUI/custom_nodes /opt/pilot/bundled/comfy-custom-nodes
/opt/pilot/build/lib/git_checkout.sh \
  https://github.com/romandev-codex/ComfyUI-Downloader.git \
  /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Downloader \
  "${COMFYUI_DOWNLOADER_REF}"

/opt/pilot/build/lib/git_checkout.sh \
  https://github.com/city96/ComfyUI-GGUF.git \
  /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-GGUF \
  "${COMFYUI_GGUF_REF}"
/opt/pilot/build/lib/git_checkout.sh \
  https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
  /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite \
  "${COMFYUI_VHS_REF}"

pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  -r /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-GGUF/requirements.txt \
  -r /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt
/opt/venvs/core/bin/python - <<'PYTHON'
import cv2
import gguf
import imageio_ffmpeg
print("ComfyUI video dependencies:", cv2.__version__, imageio_ffmpeg.get_ffmpeg_version())
PYTHON

for node in ComfyUI-Downloader ComfyUI-GGUF ComfyUI-VideoHelperSuite; do
  cp -a "/opt/pilot/repos/ComfyUI/custom_nodes/${node}" /opt/pilot/bundled/comfy-custom-nodes/
done

mkdir -p /workspace/apps/comfy/user
rm -rf /opt/pilot/repos/ComfyUI/user
ln -s /workspace/apps/comfy/user /opt/pilot/repos/ComfyUI/user
