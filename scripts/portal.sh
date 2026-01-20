#!/usr/bin/env bash
set -euo pipefail

PORT="${PORTAL_PORT:-7878}"
APP_DIR="/opt/pilot/apps/Portal"
SECRETS="/workspace/config/secrets.env"

source /opt/venvs/core/bin/activate
if [ -f "$SECRETS" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS"
fi
exec uvicorn app:app --host 0.0.0.0 --port "${PORT}" --reload --app-dir "${APP_DIR}"
