#!/usr/bin/env bash
set -euo pipefail

WS="${WORKSPACE_ROOT:-/workspace}"
PORT="${CODE_SERVER_PORT:-8443}"

# Put user state somewhere writable on RunPod volumes.
PH="${WS}/home/root"
mkdir -p \
  "${PH}" \
  "${PH}/.config" \
  "${PH}/.local/share" \
  "${PH}/.cache" \
  "${WS}/code-server/data" \
  "${WS}/code-server/extensions" \
  "${WS}/logs"

export HOME="${PH}"
export XDG_CONFIG_HOME="${PH}/.config"
export XDG_DATA_HOME="${PH}/.local/share"
export XDG_CACHE_HOME="${PH}/.cache"

# Optional: read password from secrets.env if you store it there.
# code-server's install uses "PASSWORD" env var for --auth password.
SECRETS="${WS}/config/secrets.env"
if [ -f "${SECRETS}" ]; then
  # shellcheck disable=SC1090
  source "${SECRETS}" || true
fi

if [ -n "${CODE_SERVER_PASSWORD:-}" ]; then
  export PASSWORD="${CODE_SERVER_PASSWORD}"
fi

BINARY="$WS/apps/code-server/bin/code-server"
if [ ! -x "$BINARY" ]; then BINARY=/usr/bin/code-server; fi
if [ ! -x "$BINARY" ]; then
  echo "VS Code Server is optional. Install it from ControlPilot > Services first." >&2
  exit 1
fi
exec "$BINARY" \
  --bind-addr "0.0.0.0:${PORT}" \
  --user-data-dir "${WS}/code-server/data" \
  --extensions-dir "${WS}/code-server/extensions" \
  --auth password \
  "${WS}"
