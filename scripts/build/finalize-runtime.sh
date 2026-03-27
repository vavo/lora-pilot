#!/usr/bin/env bash
set -euo pipefail

files=(
  /opt/pilot/bootstrap.sh
  /opt/pilot/gpu-smoke-test.sh
  /opt/pilot/start-jupyter.sh
  /opt/pilot/start-code-server.sh
  /opt/pilot/comfy.sh
  /opt/pilot/start-kohya.sh
  /opt/pilot/kohya.sh
  /opt/pilot/diffusion-pipe.sh
  /opt/pilot/invoke.sh
  /opt/pilot/tagpilot.sh
  /opt/pilot/portal.sh
  /opt/pilot/copilot-sidecar.sh
  /opt/pilot/ai-toolkit.sh
  /opt/pilot/wsl-start.sh
  /opt/pilot/wsl-stop.sh
  /opt/pilot/wsl-apply-update.sh
  /opt/pilot/service-autostart-apply.py
  /opt/pilot/service-updates-reconcile.py
  /opt/pilot/get-models.sh
  /opt/pilot/get-modelsgui.sh
  /usr/local/bin/pilot
)

for file in "${files[@]}"; do
  sed -i 's/\r$//' "${file}"
  head -n 1 "${file}" | grep -q '^#!' || {
    echo "Missing shebang in ${file}" >&2
    exit 1
  }
  chmod +x "${file}"
done

ln -sf /opt/pilot/get-models.sh /usr/local/bin/models
ln -sf /opt/pilot/get-models.sh /usr/local/bin/pilot-models
ln -sf /opt/pilot/get-modelsgui.sh /usr/local/bin/modelsgui

mkdir -p \
  /opt/pilot/runtime \
  /workspace \
  /workspace/logs \
  /workspace/outputs \
  /workspace/outputs/comfy \
  /workspace/outputs/invoke \
  /workspace/datasets \
  /workspace/datasets/images \
  /workspace/datasets/ZIPs \
  /workspace/models \
  /workspace/config \
  /workspace/cache \
  /workspace/home

cp /opt/pilot/config/core-constraints.txt /workspace/config/core-constraints.txt || true
