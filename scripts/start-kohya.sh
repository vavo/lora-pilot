#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"
ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_ROOT="${ROOT}/apps/kohya"

export PATH="/opt/venvs/core/bin:$PATH"
export PYTHONUNBUFFERED=1
export PYTHONPATH="/opt/pilot/repos/kohya_ss/sd-scripts:${PYTHONPATH:-}"
KOHYA_TRANSFORMERS_VERSION="${KOHYA_TRANSFORMERS_VERSION:-4.57.6}"

mkdir -p "$ROOT/logs" "$APP_ROOT"

# Fix setuptools deprecation warning for Kohya
# Suppression and source patching are applied during image build.
export PYTHONWARNINGS="ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources"

# Verify the fix
SETUPTOOLS_VERSION=$(/opt/venvs/core/bin/python -c "import setuptools; print(setuptools.__version__)" 2>/dev/null || echo "unknown")
echo "Setuptools version: $SETUPTOOLS_VERSION"

if ! /opt/venvs/core/bin/python - <<'PY' >/dev/null 2>&1
from transformers import Dinov2WithRegistersConfig
PY
then
  echo "Repairing core transformers for Kohya: installing ${KOHYA_TRANSFORMERS_VERSION}"
  /opt/venvs/core/bin/pip install --quiet --no-cache-dir "transformers==${KOHYA_TRANSFORMERS_VERSION}"
fi

cd /opt/pilot/repos/kohya_ss
exec /opt/venvs/core/bin/python -u kohya_gui.py \
  --listen "$HOST" \
  --server_port "$PORT"
