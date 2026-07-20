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

ln -sf /opt/pilot/repos/kohya_ss/requirements.txt /tmp/requirements.txt

req="requirements_runpod.txt"
[[ -f "${req}" ]] || req="requirements_linux.txt"
[[ -f "${req}" ]] || req="requirements.txt"

grep -v -E '^(tensorrt|torch|torchvision|torchaudio|xformers|triton|bitsandbytes|diffusers|transformers|peft|huggingface-hub|accelerate|tensorflow|tensorboard)' \
  "${req}" > /tmp/kohya-req.txt

printf '%s\n' 'numpy<2' > /tmp/kohya-constraints.txt
pip_install_in_venv /opt/venvs/core -c /tmp/kohya-constraints.txt -r /tmp/kohya-req.txt
rm -f /tmp/kohya-req.txt /tmp/kohya-constraints.txt

sitepkg="$("/opt/venvs/core/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${sitepkg}/kohya_sd_scripts.pth"
printf '%s\n' \
  'from easygui import global_state as _gs' \
  'globals().update(_gs.__dict__)' \
  > "${sitepkg}/global_state.py"
