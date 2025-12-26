#!/usr/bin/env bash
set -euo pipefail
[ -f /workspace/config/secrets.env ] && source /workspace/config/secrets.env || true
exec /opt/venvs/tools/bin/jupyter-lab \
  --ip=0.0.0.0 \
  --port="${JUPYTER_PORT:-8888}" \
  --no-browser \
  --ServerApp.token="${JUPYTER_TOKEN:-}" \
  --ServerApp.allow_origin="*" \
  --ServerApp.root_dir=/workspace
