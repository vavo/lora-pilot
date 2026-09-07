#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_DIR="${ROOT}/apps/TagPilot"
PORT="${TAGPILOT_PORT:-3333}"

# Use the same ownership inventory as bootstrap.
if [ -d /opt/pilot/apps/TagPilot ] && { [ ! -d "${APP_DIR}" ] || [ "${TAGPILOT_SYNC_ON_BOOT:-1}" = "1" ]; }; then
  /opt/venvs/core/bin/python /opt/pilot/bundle-sync.py /opt/pilot/apps/TagPilot "${APP_DIR}"
fi

cd "${APP_DIR}"
exec /opt/venvs/core/bin/python -m http.server "${PORT}"
