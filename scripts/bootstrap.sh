cat > scripts/bootstrap.sh <<'EOF'
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
  "${WORKSPACE_ROOT}/models" \
  "${WORKSPACE_ROOT}/datasets" \
  "${WORKSPACE_ROOT}/outputs" \
  "${WORKSPACE_ROOT}/cache" \
  "${WORKSPACE_ROOT}/config" \
  "${WORKSPACE_ROOT}/apps" \
  "${WORKSPACE_ROOT}/custom_nodes" \
  "${WORKSPACE_ROOT}/logs"

# Ensure runtime/config dirs exist (prevents /root fallbacks)
mkdir -p \
  "${XDG_CONFIG_HOME}" "${XDG_CACHE_HOME}" "${XDG_DATA_HOME}" \
  "${JUPYTER_RUNTIME_DIR}" "${JUPYTER_DATA_DIR}" "${JUPYTER_CONFIG_DIR}" \
  "${HF_HOME}" "${HUGGINGFACE_HUB_CACHE}" "${TRANSFORMERS_CACHE}" \
  "${TORCH_HOME}" "${PIP_CACHE_DIR}" \
  "${CODE_SERVER_CONFIG_DIR}" "${CODE_SERVER_DATA_DIR}"

# Secrets (persist)
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

export CODE_SERVER_PASSWORD="${CODE_SERVER_PASSWORD:-}"
export JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"

# Best-effort permissions (some mounts don’t allow chown)
chown -R pilot:pilot "${WORKSPACE_ROOT}" 2>/dev/null || true

echo "=== LoRA Pilot bootstrap complete ==="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Jupyter:  http://<host>:${JUPYTER_PORT}  (token in ${SECRETS_FILE})"
echo "code-server: http://<host>:${CODE_SERVER_PORT}  (password in ${SECRETS_FILE})"
EOF
chmod +x scripts/bootstrap.sh
