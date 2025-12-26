#!/usr/bin/env bash
set -euo pipefail
[ -f /workspace/config/secrets.env ] && source /workspace/config/secrets.env || true
export PASSWORD="${CODE_SERVER_PASSWORD:-}"
mkdir -p /workspace/config/code-server /workspace/cache/code-server
exec /usr/bin/code-server \
  --bind-addr 0.0.0.0:"${CODE_SERVER_PORT:-8443}" \
  --auth password \
  --disable-telemetry \
  --user-data-dir /workspace/cache/code-server \
  /workspace
