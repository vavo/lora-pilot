#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_DIFFPIPE:-1}" != "1" ]]; then
  echo "Skipping Diffusion Pipe install (INSTALL_DIFFPIPE=${INSTALL_DIFFPIPE:-0})"
  exit 0
fi

: "${DIFFPIPE_REF:?DIFFPIPE_REF is required}"
: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${TORCHAUDIO_VERSION:?TORCHAUDIO_VERSION is required}"
: "${TORCH_INDEX_URL:?TORCH_INDEX_URL is required}"
: "${XFORMERS_VERSION:?XFORMERS_VERSION is required}"
: "${BITSANDBYTES_VERSION:?BITSANDBYTES_VERSION is required}"
: "${DIFFPIPE_DIFFUSERS_VERSION:?DIFFPIPE_DIFFUSERS_VERSION is required}"
: "${DIFFPIPE_TRANSFORMERS_VERSION:?DIFFPIPE_TRANSFORMERS_VERSION is required}"
: "${INVOKE_ACCELERATE_VERSION:?INVOKE_ACCELERATE_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"

/opt/pilot/build/lib/git_checkout.sh --recurse-submodules \
  https://github.com/tdrussell/diffusion-pipe.git \
  /opt/pilot/repos/diffusion-pipe \
  "${DIFFPIPE_REF}"

create_venv /opt/venvs/diffpipe "setuptools<81.0" wheel
pip_install_in_venv /opt/venvs/diffpipe \
  torch==${TORCH_VERSION} \
  torchvision==${TORCHVISION_VERSION} \
  torchaudio==${TORCHAUDIO_VERSION} \
  --index-url ${TORCH_INDEX_URL}
pip_install_in_venv /opt/venvs/diffpipe \
  -c /opt/pilot/config/diffpipe-constraints.txt \
  "xformers==${XFORMERS_VERSION}" \
  "bitsandbytes==${BITSANDBYTES_VERSION}" \
  "diffusers==${DIFFPIPE_DIFFUSERS_VERSION}" \
  "transformers==${DIFFPIPE_TRANSFORMERS_VERSION}" \
  "accelerate==${INVOKE_ACCELERATE_VERSION}" \
  "peft==${PEFT_VERSION}" \
  tensorboard
pip_install_in_venv /opt/venvs/diffpipe \
  -c /opt/pilot/config/diffpipe-constraints.txt \
  -r /opt/pilot/repos/diffusion-pipe/requirements.txt
pip_install_in_venv /opt/venvs/diffpipe "setuptools<81.0"
