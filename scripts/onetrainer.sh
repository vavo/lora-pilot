#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${ONETRAINER_PORT:-4444}"
DISPLAY_NUM="${ONETRAINER_DISPLAY:-0}"
VNC_PORT="${ONETRAINER_VNC_PORT:-5900}"
RESOLUTION="${ONETRAINER_RESOLUTION:-1920x1080}"
DEPTH="${ONETRAINER_DEPTH:-24}"

export PATH="/opt/venvs/core/bin:$PATH"
export PYTHONUNBUFFERED=1
export DISPLAY=":${DISPLAY_NUM}"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-${ROOT}/cache/xdg-runtime}"
mkdir -p "${XDG_RUNTIME_DIR}" "${ROOT}/logs" "${ROOT}/onetrainer"

if [[ -z "${HF_HUB_DISABLE_XET+x}" ]]; then
  export HF_HUB_DISABLE_XET=1
fi

Xvfb "${DISPLAY}" -screen 0 "${RESOLUTION}x${DEPTH}" -nolisten tcp -ac &
XVFB_PID=$!
sleep 0.5

x11vnc -display "${DISPLAY}" -rfbport "${VNC_PORT}" -forever -shared -nopw -noxrecord -noxfixes -noxdamage &
VNC_PID=$!

if [ -x /usr/share/novnc/utils/novnc_proxy ]; then
  NOVNC_WEB="/usr/share/novnc"
  if [ -d "${NOVNC_WEB}" ]; then
    /usr/share/novnc/utils/novnc_proxy --web "${NOVNC_WEB}" --vnc "localhost:${VNC_PORT}" --listen "${PORT}" &
  else
    /usr/share/novnc/utils/novnc_proxy --vnc "localhost:${VNC_PORT}" --listen "${PORT}" &
  fi
elif command -v websockify >/dev/null 2>&1 && [ -d /usr/share/novnc ]; then
  websockify --web /usr/share/novnc "${PORT}" "localhost:${VNC_PORT}" &
else
  echo "ERROR: noVNC not found (install novnc/websockify)" >&2
  exit 1
fi
NOVNC_PID=$!

cleanup() {
  kill "${NOVNC_PID}" "${VNC_PID}" "${XVFB_PID}" 2>/dev/null || true
}
trap cleanup EXIT

cd /opt/pilot/repos/OneTrainer
/opt/venvs/core/bin/python -u scripts/train_ui.py &
OT_PID=$!
wait "${OT_PID}"
