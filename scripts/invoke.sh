#!/usr/bin/env bash
set -euo pipefail

export INVOKEAI_ROOT="${INVOKEAI_ROOT:-/workspace/apps/invokeai}"
mkdir -p "$INVOKEAI_ROOT" 2>/dev/null || true

# Your installed invokeai-web does NOT support --host/--port (per log).
exec /opt/venvs/core/bin/invokeai-web --root "$INVOKEAI_ROOT"
