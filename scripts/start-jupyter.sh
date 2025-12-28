#!/usr/bin/env bash
set -euo pipefail

WS="${WORKSPACE_ROOT:-/workspace}"
PORT="${JUPYTER_PORT:-8888}"

# Put Jupyter runtime/config somewhere writable on RunPod volumes.
PH="${WS}/home/pilot"
export HOME="${PH}"
export XDG_CONFIG_HOME="${PH}/.config"
export XDG_DATA_HOME="${PH}/.local/share"
export XDG_CACHE_HOME="${PH}/.cache"

export JUPYTER_CONFIG_DIR="${PH}/.jupyter"
export JUPYTER_DATA_DIR="${PH}/.local/share/jupyter"
export JUPYTER_RUNTIME_DIR="${PH}/.local/share/jupyter/runtime"

mkdir -p \
  "${XDG_CONFIG_HOME}" \
  "${JUPYTER_CONFIG_DIR}" \
  "${JUPYTER_DATA_DIR}" \
  "${JUPYTER_RUNTIME_DIR}" \
  "${WS}/logs" \
  "${WS}/config"

# Token comes from secrets.env (your bootstrap prints that location)
SECRETS="${WS}/config/secrets.env"
TOKEN=""
if [ -f "${SECRETS}" ]; then
  TOKEN="$(awk -F= '/^JUPYTER_TOKEN=/{print $2}' "${SECRETS}" | tail -n1 || true)"
fi

exec /opt/venvs/tools/bin/jupyter-lab \
  --ServerApp.ip=0.0.0.0 \
  --ServerApp.port="${PORT}" \
  --ServerApp.open_browser=False \
  --ServerApp.allow_remote_access=True \
  --ServerApp.allow_origin='*' \
  --ServerApp.disable_check_xsrf=True \
  --ServerApp.root_dir="${WS}" \
  --ServerApp.password='' \
  --IdentityProvider.token="${TOKEN}" \
  --ServerApp.token="${TOKEN}"
