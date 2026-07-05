#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${TORCH_INDEX_URL:?TORCH_INDEX_URL is required}"
: "${XFORMERS_VERSION:?XFORMERS_VERSION is required}"
: "${BITSANDBYTES_VERSION:?BITSANDBYTES_VERSION is required}"
: "${CORE_DIFFUSERS_VERSION:?CORE_DIFFUSERS_VERSION is required}"
: "${TRANSFORMERS_VERSION:?TRANSFORMERS_VERSION is required}"
: "${UV_VERSION:?UV_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"
: "${ACCELERATE_VERSION:?ACCELERATE_VERSION is required}"
: "${HF_HUB_VERSION:?HF_HUB_VERSION is required}"

if [[ "${INSTALL_GPU_STACK:-1}" == "1" ]]; then
  pip_install_in_venv /opt/venvs/core \
    "torch==${TORCH_VERSION}" \
    "torchvision==${TORCHVISION_VERSION}" \
    --index-url "${TORCH_INDEX_URL}"

  if [[ -n "${TORCHAUDIO_VERSION:-}" ]]; then
    pip_install_in_venv /opt/venvs/core \
      -c /opt/pilot/config/core-constraints.txt \
      "torchaudio==${TORCHAUDIO_VERSION}" \
      --index-url "${TORCH_INDEX_URL}"
  else
    echo "Skipping torchaudio install (TORCHAUDIO_VERSION is empty for this CUDA profile)"
  fi

  pip_install_in_venv /opt/venvs/core \
    -c /opt/pilot/config/core-constraints.txt \
    "xformers==${XFORMERS_VERSION}" \
    "bitsandbytes==${BITSANDBYTES_VERSION}" \
    toml \
    "accelerate==${ACCELERATE_VERSION}" \
    "diffusers==${CORE_DIFFUSERS_VERSION}" \
    "transformers==${TRANSFORMERS_VERSION}" \
    "uv==${UV_VERSION}" \
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

if [[ "${INSTALL_GPU_STACK:-1}" == "1" ]]; then
  core_import_modules="uv transformers xformers"
  if [[ -n "${TORCHAUDIO_VERSION:-}" ]]; then
    core_import_modules="torchaudio ${core_import_modules}"
  fi
  CORE_IMPORT_MODULES="${core_import_modules}" /opt/venvs/core/bin/python - <<'PY'
import importlib.util
import os
for name in os.environ["CORE_IMPORT_MODULES"].split():
    if importlib.util.find_spec(name) is None:
        raise SystemExit(f"missing core Python module: {name}")
PY
fi

pip_install_in_venv /opt/venvs/core \
  -c /opt/pilot/config/core-constraints.txt \
  "huggingface_hub[hf_transfer,hf_xet]==${HF_HUB_VERSION}"

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
