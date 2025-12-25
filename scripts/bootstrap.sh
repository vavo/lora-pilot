#!/usr/bin/env bash
set -euo pipefail

DEFAULTS_FILE="/opt/pilot/config/env.defaults"
SECRETS_FILE=""

if [[ -f "$DEFAULTS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$DEFAULTS_FILE"
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
SECRETS_FILE="${WORKSPACE_ROOT}/config/secrets.env"

mkdir -p \
  "${WORKSPACE_ROOT}/models" \
  "${WORKSPACE_ROOT}/datasets" \
  "${WORKSPACE_ROOT}/outputs" \
  "${WORKSPACE_ROOT}/cache" \
  "${WORKSPACE_ROOT}/config" \
  "${WORKSPACE_ROOT}/apps"

# Secrets (persist in /workspace)
if [[ -f "$SECRETS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
else
  CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-$(openssl rand -hex 16)}"
  JUPYTER_TOKEN="${JUPYTER_TOKEN:-$(openssl rand -hex 16)}"
  cat > "$SECRETS_FILE" <<EOF
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN}"
EOF
fi

# Export again (in case secrets were loaded)
export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"

# Ensure caches exist
mkdir -p \
  "${XDG_CACHE_HOME}" \
  "${HF_HOME}" \
  "${HUGGINGFACE_HUB_CACHE}" \
  "${TRANSFORMERS_CACHE}" \
  "${TORCH_HOME}" \
  "${PIP_CACHE_DIR}"

# Best-effort permissions (some mounts don't allow chown)
chown -R pilot:pilot "${WORKSPACE_ROOT}" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT}  (password in ${SECRETS_FILE})"
