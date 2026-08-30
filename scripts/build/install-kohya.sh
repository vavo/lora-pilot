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

req="requirements_runpod.txt"
[[ -f "${req}" ]] || req="requirements_linux.txt"
[[ -f "${req}" ]] || req="requirements.txt"

core_dependency_pattern='^(tensorrt|torch|torchvision|torchaudio|xformers|triton|bitsandbytes|diffusers|transformers|peft|huggingface-hub|accelerate|tensorflow|tensorboard|-r[[:space:]]+requirements\.txt)'
grep -v -E "${core_dependency_pattern}" "${req}" > /tmp/kohya-req.txt
if [[ "${req}" != "requirements.txt" ]]; then
  grep -v -E "${core_dependency_pattern}" requirements.txt >> /tmp/kohya-req.txt
fi

pip_install_in_venv /opt/venvs/core -c /opt/pilot/config/core-constraints.txt -r /tmp/kohya-req.txt
rm -f /tmp/kohya-req.txt

[[ -x /opt/venvs/core/bin/hf ]] || { echo "Hugging Face CLI missing after Kohya install" >&2; exit 1; }
/opt/venvs/core/bin/hf version

sitepkg="$("/opt/venvs/core/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${sitepkg}/kohya_sd_scripts.pth"
printf '%s\n' \
  'from easygui import global_state as _gs' \
  'globals().update(_gs.__dict__)' \
  > "${sitepkg}/global_state.py"
