#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"
ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_ROOT="${ROOT}/apps/kohya"

export PATH="/opt/venvs/kohya/bin:$PATH"
export PYTHONUNBUFFERED=1
export PYTHONPATH="/opt/pilot/repos/kohya_ss/sd-scripts:${PYTHONPATH:-}"

mkdir -p "$ROOT/logs" "$APP_ROOT"

# Kohya imports pkg_resources through setup_common.py; keep this warning out of service logs.
export PYTHONWARNINGS="${PYTHONWARNINGS:+${PYTHONWARNINGS},}ignore:pkg_resources is deprecated as an API:UserWarning"

/opt/venvs/kohya/bin/python - <<'PYTHON'
from transformers import CLIPFeatureExtractor, Dinov2WithRegistersConfig
PYTHON

cd /opt/pilot/repos/kohya_ss
exec /opt/venvs/kohya/bin/python -u kohya_gui.py \
  --listen "$HOST" \
  --server_port "$PORT"
