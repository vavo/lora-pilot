#!/usr/bin/env bash
set -euo pipefail

PORT="${PORTAL_PORT:-7878}"
APP_DIR="/opt/pilot/apps/Portal"
SECRETS="/workspace/config/secrets.env"
RELOAD="${PORTAL_RELOAD:-0}"

source /opt/venvs/core/bin/activate
if [ -f "$SECRETS" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS"
fi
args=(app:app --host 0.0.0.0 --port "$PORT" --app-dir "$APP_DIR")
origin="${MCP_PUBLIC_URL:-}"
# MCP checks the socket peer, not a client address derived from X-Forwarded-For.
if [[ -n ${RUNPOD_POD_ID:-} && ( -z $origin || ${origin%/} == "https://${RUNPOD_POD_ID}-$PORT.proxy.runpod.net" ) ]]; then
  args+=(--no-proxy-headers)
fi
if [[ $RELOAD == 1 ]]; then args+=(--reload); fi
exec uvicorn "${args[@]}"
