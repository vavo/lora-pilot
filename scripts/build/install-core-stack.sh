#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${TORCHAUDIO_VERSION:?TORCHAUDIO_VERSION is required}"
: "${TORCH_INDEX_URL:?TORCH_INDEX_URL is required}"
: "${XFORMERS_VERSION:?XFORMERS_VERSION is required}"
: "${BITSANDBYTES_VERSION:?BITSANDBYTES_VERSION is required}"
: "${CORE_DIFFUSERS_VERSION:?CORE_DIFFUSERS_VERSION is required}"
: "${TRANSFORMERS_VERSION:?TRANSFORMERS_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"

if [[ "${INSTALL_GPU_STACK:-1}" == "1" ]]; then
  pip_install_in_venv /opt/venvs/core \
    "torch==${TORCH_VERSION}" \
    "torchvision==${TORCHVISION_VERSION}" \
    "torchaudio==${TORCHAUDIO_VERSION}" \
    --index-url "${TORCH_INDEX_URL}"

  pip_install_in_venv /opt/venvs/core \
    -c /opt/pilot/config/core-constraints.txt \
    "xformers==${XFORMERS_VERSION}" \
    "bitsandbytes==${BITSANDBYTES_VERSION}" \
    toml \
    accelerate \
    "diffusers==${CORE_DIFFUSERS_VERSION}" \
    "transformers==${TRANSFORMERS_VERSION}" \
    "peft==${PEFT_VERSION}" \
    safetensors \
    torchsde \
    "numpy<2" \
    "pillow<12" \
    tqdm \
    psutil
else
  echo "Skipping GPU stack install (INSTALL_GPU_STACK=${INSTALL_GPU_STACK:-0})"
fi

pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  "huggingface_hub[hf_transfer,hf_xet]"

pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  fastapi \
  "uvicorn[standard]" \
  pydantic \
  python-multipart \
  flask \
  flask-cors \
  requests \
  python-dotenv \
  python-socketio \
  websockets \
  pillow \
  httpx
