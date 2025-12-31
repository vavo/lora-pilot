#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_DIR="${ROOT}/apps/TagPilot"
PORT="${TAGPILOT_PORT:-3333}"

# Ensure the app is seeded into workspace
if [ -d /opt/pilot/apps/TagPilot ] && [ ! -e "${APP_DIR}" ]; then
  mkdir -p "${ROOT}/apps"
  cp -a /opt/pilot/apps/TagPilot "${APP_DIR}"
fi

cd "${APP_DIR}"
exec /opt/venvs/core/bin/python -m http.server "${PORT}"
