#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
[ -f /workspace/config/secrets.env ] && source /workspace/config/secrets.env || true

# code-server expects PASSWORD env var for password auth  [oai_citation:3‡GitLab](https://gitlab.b-data.ch/coder/code-server/-/tree/2.1688-vsc1.39.2?utm_source=chatgpt.com)
export PASSWORD="${CODE_SERVER_PASSWORD:-}"

mkdir -p "${CODE_SERVER_CONFIG_DIR:-/workspace/config/code-server}" "${CODE_SERVER_DATA_DIR:-/workspace/cache/code-server}"

exec /usr/bin/code-server \
  --bind-addr 0.0.0.0:"${CODE_SERVER_PORT:-8443}" \
  --auth password \
  --disable-telemetry \
  --user-data-dir "${CODE_SERVER_DATA_DIR:-/workspace/cache/code-server}" \
  /workspace
