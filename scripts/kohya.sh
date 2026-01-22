#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"
ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_ROOT="${ROOT}/apps/kohya"

export PATH="/opt/venvs/core/bin:$PATH"
export PYTHONUNBUFFERED=1
export PYTHONPATH="/opt/pilot/repos/kohya_ss/sd-scripts:${PYTHONPATH:-}"

mkdir -p "$ROOT/logs" "$APP_ROOT"

# Fix setuptools deprecation warning for Kohya
/opt/venvs/core/bin/pip install "setuptools<81.0" --quiet

# Kohya sometimes tries to install Windows-specific torch requirements; neutralize them.
WIN_REQ="/opt/pilot/repos/kohya_ss/requirements_pytorch_windows.txt"
if [ -f "$WIN_REQ" ]; then
  printf "# disabled by LoRA Pilot (use core venv torch)\n" > "$WIN_REQ"
fi

cd /opt/pilot/repos/kohya_ss
exec /opt/venvs/core/bin/python -u kohya_gui.py \
  --listen "$HOST" \
  --server_port "$PORT"
