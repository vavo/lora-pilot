cat > scripts/bootstrap.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Load defaults (workspace dirs, ports, XDG/Jupyter paths)
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

# Ensure all runtime dirs exist (prevents /root fallback)
mkdir -p \
  "${XDG_CONFIG_HOME:-${WORKSPACE_ROOT}/config/xdg}" \
  "${XDG_CACHE_HOME:-${WORKSPACE_ROOT}/cache/xdg}" \
  "${XDG_DATA_HOME:-${WORKSPACE_ROOT}/cache/xdg-data}" \
  "${JUPYTER_RUNTIME_DIR:-${WORKSPACE_ROOT}/cache/jupyter/runtime}" \
  "${JUPYTER_DATA_DIR:-${WORKSPACE_ROOT}/cache/jupyter/data}" \
  "${JUPYTER_CONFIG_DIR:-${WORKSPACE_ROOT}/config/jupyter}" \
  "${CODE_SERVER_CONFIG_DIR:-${WORKSPACE_ROOT}/config/code-server}" \
  "${CODE_SERVER_DATA_DIR:-${WORKSPACE_ROOT}/cache/code-server}" \
  "${HF_HOME:-${WORKSPACE_ROOT}/cache/huggingface}" \
  "${TORCH_HOME:-${WORKSPACE_ROOT}/cache/torch}" \
  "${PIP_CACHE_DIR:-${WORKSPACE_ROOT}/cache/pip}"

# Create secrets if missing
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

# Make sure workspace is writable by the runtime user
chown -R pilot:pilot "${WORKSPACE_ROOT}" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT:-8888}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT:-8443}  (password in ${SECRETS_FILE})"
EOF

chmod +x scripts/bootstrap.sh
