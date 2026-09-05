#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_AI_TOOLKIT:-1}" != "1" ]]; then
  echo "Skipping AI Toolkit install (INSTALL_AI_TOOLKIT=${INSTALL_AI_TOOLKIT:-0})"
  exit 0
fi

: "${AI_TOOLKIT_REF:?AI_TOOLKIT_REF is required}"
: "${AI_TOOLKIT_DIFFUSERS_VERSION:?AI_TOOLKIT_DIFFUSERS_VERSION is required}"
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
install_service_gpu_stack /opt/venvs/ai-toolkit

if [[ "${AI_TOOLKIT_DIFFUSERS_VERSION}" != "git" ]]; then
  echo "AI Toolkit latest expects upstream git-pinned Diffusers; got AI_TOOLKIT_DIFFUSERS_VERSION=${AI_TOOLKIT_DIFFUSERS_VERSION}" >&2
  exit 1
fi

# Upstream pins target older Torch ABIs. Keep the selected 2.11 CUDA stack.
/opt/venvs/ai-toolkit/bin/python - <<'PYTHON'
from pathlib import Path
path = Path("/opt/pilot/repos/ai-toolkit/requirements_base.txt")
text = path.read_text()
for old, new in (("torchao==0.10.0", "torchao==0.17.0"),
                 ("torchcodec==0.9.1", "torchcodec==0.11.1")):
    if old not in text:
        raise SystemExit(f"AI Toolkit ABI patch target changed: {old}")
    text = text.replace(old, new)
path.write_text(text)
PYTHON
pip_install_unconstrained_in_venv /opt/venvs/ai-toolkit \
  --extra-index-url "${TORCH_INDEX_URL}" \
  -c /opt/pilot/config/service-gpu-constraints.txt \
  -r /opt/pilot/repos/ai-toolkit/requirements.txt

/opt/venvs/ai-toolkit/bin/python -m pip check

if [[ -z "${BUILDPLATFORM}" || -z "${TARGETPLATFORM}" || "${BUILDPLATFORM}" == "${TARGETPLATFORM}" ]]; then
  /opt/venvs/ai-toolkit/bin/python -c 'import peft; import timm; import open_clip; import lycoris; import lycoris.kohya; import torchao; import optimum.quanto'
  /opt/venvs/ai-toolkit/bin/python - <<'PYTHON'
from torchao.quantization.quant_api import quantize_, Float8WeightOnlyConfig, Int8WeightOnlyConfig
from torchao.quantization.quant_primitives import _DTYPE_TO_BIT_WIDTH
from torchao.dtypes import AffineQuantizedTensor
from torchcodec.decoders import VideoDecoder
PYTHON
else
  echo "Skipping AI Toolkit import smoke during cross-platform build (${BUILDPLATFORM} -> ${TARGETPLATFORM}); run runtime smoke on target hardware."
fi

if [[ "${INSTALL_AI_TOOLKIT_UI:-1}" == "1" ]]; then
  export PATH="/opt/venvs/ai-toolkit/bin:${PATH}"
  export PYTHON=/opt/venvs/ai-toolkit/bin/python
  export PIP=/opt/venvs/ai-toolkit/bin/pip
  export VIRTUAL_ENV=/opt/venvs/ai-toolkit
  cd /opt/pilot/repos/ai-toolkit/ui
  npm install
  npm_config_build_from_source=true npm rebuild sqlite3
  DATABASE_URL=file:/tmp/aitk_db.db npx prisma generate
  npm run build
  npm cache clean --force
fi
