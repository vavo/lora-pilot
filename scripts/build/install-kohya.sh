#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

if [[ "${INSTALL_KOHYA:-1}" != "1" ]]; then
  echo "Skipping Kohya install (INSTALL_KOHYA=${INSTALL_KOHYA:-0})"
  exit 0
fi

: "${KOHYA_REF:?KOHYA_REF is required}"

/opt/pilot/build/lib/git_checkout.sh --recurse-submodules \
  https://github.com/bmaltais/kohya_ss.git \
  /opt/pilot/repos/kohya_ss \
  "${KOHYA_REF}"

cd /opt/pilot/repos/kohya_ss

create_venv /opt/venvs/kohya "setuptools<81.0" wheel
install_service_gpu_stack /opt/venvs/kohya
pip_install_unconstrained_in_venv /opt/venvs/kohya \
  -c /opt/pilot/config/service-gpu-constraints.txt \
  -r requirements.txt "gradio<6" "bitsandbytes==${BITSANDBYTES_VERSION}" tensorboard
/opt/venvs/kohya/bin/python -m pip check

sitepkg="$("/opt/venvs/kohya/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${sitepkg}/kohya_sd_scripts.pth"
printf '%s\n' \
  'from easygui import global_state as _gs' \
  'globals().update(_gs.__dict__)' \
  > "${sitepkg}/global_state.py"
