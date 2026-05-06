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

exec npm run start
