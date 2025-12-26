#!/usr/bin/env bash
set -euo pipefail

DEFAULTS_FILE="/opt/pilot/config/env.defaults"
if [[ -f "$DEFAULTS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEFAULTS_FILE"
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
SECRETS_FILE="${WORKSPACE_ROOT}/config/secrets.env"

mkdir -p \
  "${WORKSPACE_ROOT}/config" \
  "${WORKSPACE_ROOT}/cache" \
  "${WORKSPACE_ROOT}/logs" \
  "${WORKSPACE_ROOT}/apps" \
  "${WORKSPACE_ROOT}/models" \
  "${WORKSPACE_ROOT}/datasets" \
  "${WORKSPACE_ROOT}/outputs" \
  "${WORKSPACE_ROOT}/custom_nodes"

# Force “no /root writes”
export HOME="${HOME:-/home/pilot}"
export USER="${USER:-pilot}"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${WORKSPACE_ROOT}/config/xdg}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${WORKSPACE_ROOT}/cache/xdg}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-${WORKSPACE_ROOT}/cache/xdg-data}"

export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-${WORKSPACE_ROOT}/cache/jupyter/runtime}"
export JUPYTER_DATA_DIR="${JUPYTER_DATA_DIR:-${WORKSPACE_ROOT}/cache/jupyter/data}"
export JUPYTER_CONFIG_DIR="${JUPYTER_CONFIG_DIR:-${WORKSPACE_ROOT}/config/jupyter}"

export CODE_SERVER_CONFIG_DIR="${CODE_SERVER_CONFIG_DIR:-${WORKSPACE_ROOT}/config/code-server}"
export CODE_SERVER_DATA_DIR="${CODE_SERVER_DATA_DIR:-${WORKSPACE_ROOT}/cache/code-server}"

export HF_HOME="${HF_HOME:-${WORKSPACE_ROOT}/cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-${WORKSPACE_ROOT}/cache/torch}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-${WORKSPACE_ROOT}/cache/pip}"

mkdir -p \
  "${XDG_CONFIG_HOME}" "${XDG_CACHE_HOME}" "${XDG_DATA_HOME}" \
  "${JUPYTER_RUNTIME_DIR}" "${JUPYTER_DATA_DIR}" "${JUPYTER_CONFIG_DIR}" \
  "${CODE_SERVER_CONFIG_DIR}" "${CODE_SERVER_DATA_DIR}" \
  "${HF_HOME}" "${TORCH_HOME}" "${PIP_CACHE_DIR}"

if [[ -f "$SECRETS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
else
  CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-$(openssl rand -hex 16)}"
  JUPYTER_TOKEN="${JUPYTER_TOKEN:-$(openssl rand -hex 16)}"
  cat > "$SECRETS_FILE" <<EOF2
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
EOF2
fi

chown -R pilot:pilot "${WORKSPACE_ROOT}" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in ${SECRETS_FILE})"
