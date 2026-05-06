#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_AI_TOOLKIT:-1}" != "1" ]]; then
  echo "Skipping AI Toolkit install (INSTALL_AI_TOOLKIT=${INSTALL_AI_TOOLKIT:-0})"
  exit 0
fi

: "${AI_TOOLKIT_REF:?AI_TOOLKIT_REF is required}"
: "${AI_TOOLKIT_DIFFUSERS_VERSION:?AI_TOOLKIT_DIFFUSERS_VERSION is required}"
: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${TORCHAUDIO_VERSION:?TORCHAUDIO_VERSION is required}"
: "${TORCH_INDEX_URL:?TORCH_INDEX_URL is required}"
: "${BUILDPLATFORM:=}"
: "${TARGETPLATFORM:=}"

/opt/pilot/build/lib/git_checkout.sh \
  https://github.com/ostris/ai-toolkit.git \
  /opt/pilot/repos/ai-toolkit \
  "${AI_TOOLKIT_REF}"

/opt/pilot/build/patches/patch-ai-toolkit.sh /opt/pilot/repos/ai-toolkit "${INSTALL_AI_TOOLKIT_UI:-1}"

rm -rf /opt/pilot/repos/ai-toolkit/datasets /opt/pilot/repos/ai-toolkit/output /opt/pilot/repos/ai-toolkit/models
ln -s /workspace/datasets /opt/pilot/repos/ai-toolkit/datasets
ln -s /workspace/outputs/ai-toolkit /opt/pilot/repos/ai-toolkit/output
ln -s /workspace/models /opt/pilot/repos/ai-toolkit/models

create_venv /opt/venvs/ai-toolkit "setuptools<81.0" wheel
pip_install_unconstrained_in_venv /opt/venvs/ai-toolkit \
  --index-url "${TORCH_INDEX_URL}" \
  "torch==${TORCH_VERSION}" \
  "torchvision==${TORCHVISION_VERSION}" \
  "torchaudio==${TORCHAUDIO_VERSION}"

if [[ "${AI_TOOLKIT_DIFFUSERS_VERSION}" != "git" ]]; then
  echo "AI Toolkit latest expects upstream git-pinned Diffusers; got AI_TOOLKIT_DIFFUSERS_VERSION=${AI_TOOLKIT_DIFFUSERS_VERSION}" >&2
  exit 1
fi

pip_install_unconstrained_in_venv /opt/venvs/ai-toolkit \
  -r /opt/pilot/repos/ai-toolkit/requirements.txt

/opt/venvs/ai-toolkit/bin/python -c 'import peft; import timm; import open_clip; import lycoris; import lycoris.kohya; import torchao; import optimum.quanto'

if [[ "${INSTALL_AI_TOOLKIT_UI:-1}" == "1" ]]; then
  export PATH="/opt/venvs/ai-toolkit/bin:${PATH}"
  export PYTHON=/opt/venvs/ai-toolkit/bin/python
  export PIP=/opt/venvs/ai-toolkit/bin/pip
  export VIRTUAL_ENV=/opt/venvs/ai-toolkit
  cd /opt/pilot/repos/ai-toolkit/ui
  npm install
  DATABASE_URL=file:/tmp/aitk_db.db npx prisma generate
  if [[ -z "${BUILDPLATFORM}" || -z "${TARGETPLATFORM}" || "${BUILDPLATFORM}" == "${TARGETPLATFORM}" ]]; then
    npm run build
  else
    echo "Skipping AI Toolkit UI build during cross-platform build (${BUILDPLATFORM} -> ${TARGETPLATFORM}); runtime will build missing assets on first start."
  fi
  npm cache clean --force
fi
