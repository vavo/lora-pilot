#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_INVOKE:-1}" != "1" ]]; then
  echo "Skipping InvokeAI install (INSTALL_INVOKE=${INSTALL_INVOKE:-0})"
  exit 0
fi

: "${INVOKEAI_VERSION:?INVOKEAI_VERSION is required}"
: "${INVOKE_TORCH_INDEX_URL:?INVOKE_TORCH_INDEX_URL is required}"
: "${INVOKE_XFORMERS_VERSION:?INVOKE_XFORMERS_VERSION is required}"
: "${INVOKE_HF_HUB_VERSION:?INVOKE_HF_HUB_VERSION is required}"
: "${INVOKE_TRANSFORMERS_VERSION:?INVOKE_TRANSFORMERS_VERSION is required}"
: "${INVOKE_ACCELERATE_VERSION:?INVOKE_ACCELERATE_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"

create_venv /opt/venvs/invoke setuptools wheel
add_shared_core_site_packages /opt/venvs/invoke /opt/venvs/core

pip_install_unconstrained_in_venv /opt/venvs/invoke \
  --extra-index-url "${INVOKE_TORCH_INDEX_URL}" \
  -c /opt/pilot/config/invoke-constraints.txt \
  "invokeai[cuda]==${INVOKEAI_VERSION}"

pip_install_unconstrained_in_venv /opt/venvs/invoke \
  --extra-index-url "${INVOKE_TORCH_INDEX_URL}" \
  -c /opt/pilot/config/invoke-constraints.txt \
  "xformers==${INVOKE_XFORMERS_VERSION}"

pip_install_unconstrained_in_venv /opt/venvs/invoke \
  -c /opt/pilot/config/invoke-constraints.txt \
  "huggingface_hub[hf_transfer]==${INVOKE_HF_HUB_VERSION}"

pip_install_unconstrained_in_venv /opt/venvs/invoke \
  -c /opt/pilot/config/invoke-constraints.txt \
  "transformers==${INVOKE_TRANSFORMERS_VERSION}" \
  "accelerate==${INVOKE_ACCELERATE_VERSION}" \
  "peft==${PEFT_VERSION}" \
  "numpy<2" \
  "pillow<11"
