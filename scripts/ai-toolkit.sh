#!/usr/bin/env bash
set -euo pipefail

if [ ! -d /opt/pilot/repos/ai-toolkit/ui ]; then
  echo "ai-toolkit ui not found (build with INSTALL_AI_TOOLKIT_UI=1)" >&2
  exit 0
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node is not installed (build with INSTALL_AI_TOOLKIT_UI=1)" >&2
  exit 0
fi

if [ -f /workspace/config/secrets.env ]; then
  set +u
  source /workspace/config/secrets.env
  set -u
fi

export TOOLKIT_ROOT=/opt/pilot/repos/ai-toolkit
export PATH="/opt/venvs/ai-toolkit/bin:$PATH"
export PYTHON=/opt/venvs/ai-toolkit/bin/python
export PIP=/opt/venvs/ai-toolkit/bin/pip
export VIRTUAL_ENV=/opt/venvs/ai-toolkit
export AI_TOOLKIT_DB_PATH="${AI_TOOLKIT_DB_PATH:-/workspace/config/ai-toolkit/aitk_db.db}"

mkdir -p "$(dirname "$AI_TOOLKIT_DB_PATH")"
touch "$AI_TOOLKIT_DB_PATH"
export DATABASE_URL="file:${AI_TOOLKIT_DB_PATH}"

cd /opt/pilot/repos/ai-toolkit/ui
npm run update_db

if [ ! -f .next/BUILD_ID ]; then
  echo "AI Toolkit UI build artifacts missing; building at runtime..."
  npm run build
fi

PORT="${AI_TOOLKIT_PORT:-8675}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
  echo "Invalid AI_TOOLKIT_PORT" >&2
  exit 1
fi
# Preserve the upstream worker/UI pair while honoring the configured UI port.
exec ./node_modules/.bin/concurrently --restart-tries -1 --restart-after 1000 -n WORKER,UI \
  "node dist/cron/worker.js" "node dist/cron/fileServer.js start --port $PORT"
