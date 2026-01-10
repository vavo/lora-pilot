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
# This warning comes from Kohya SS itself importing pkg_resources
echo "Applying setuptools deprecation fix for Kohya..."

# Force install setuptools<81.0 to prevent pkg_resources deprecation warning
/opt/venvs/core/bin/pip install "setuptools<81.0" --quiet --upgrade --force-reinstall --no-warn-script-location

# Suppress the specific pkg_resources warning by setting PYTHONWARNINGS
export PYTHONWARNINGS="ignore::UserWarning:pkg_resources"

# Verify the fix
SETUPTOOLS_VERSION=$(/opt/venvs/core/bin/python -c "import setuptools; print(setuptools.__version__)" 2>/dev/null || echo "unknown")
echo "Setuptools version: $SETUPTOOLS_VERSION"

cd /opt/pilot/repos/kohya_ss
exec /opt/venvs/core/bin/python -u kohya_gui.py \
  --listen "$HOST" \
  --server_port "$PORT"
