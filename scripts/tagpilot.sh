#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_DIR="${ROOT}/apps/TagPilot"
PORT="${TAGPILOT_PORT:-3333}"

# Keep the standalone launcher on the same bundled source as bootstrap.
if [ -d /opt/pilot/apps/TagPilot ]; then
  mkdir -p "${APP_DIR}"
  source_hash="$(cd /opt/pilot/apps/TagPilot && find . -type f ! -path './__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
  recorded_hash=""
  if [ -f "${APP_DIR}/.bundle-sync-sha" ]; then
    recorded_hash="$(tr -d '\r\n' < "${APP_DIR}/.bundle-sync-sha")"
  fi
  if [ "$source_hash" != "$recorded_hash" ]; then
    (
      cd /opt/pilot/apps/TagPilot
      tar cf - --exclude='__pycache__' --exclude='.bundle-sync-sha' .
    ) | (
      cd "${APP_DIR}"
      tar xf -
    )
    find "${APP_DIR}" -type f ! -path "${APP_DIR}/.bundle-sync-sha" ! -path "${APP_DIR}/__pycache__/*" -print0 | while IFS= read -r -d '' file; do
      relative="${file#${APP_DIR}/}"
      [ -f "/opt/pilot/apps/TagPilot/${relative}" ] || rm -f "$file"
    done
    printf '%s\n' "$source_hash" > "${APP_DIR}/.bundle-sync-sha"
  fi
fi

cd "${APP_DIR}"
exec /opt/venvs/core/bin/python -m http.server "${PORT}"
