#!/usr/bin/env bash
set -euo pipefail

PORT="${PORTAL_PORT:-7878}"
APP_DIR="/opt/pilot/apps/Portal"

source /opt/venvs/core/bin/activate
exec uvicorn app:app --host 0.0.0.0 --port "${PORT}" --reload --app-dir "${APP_DIR}"
