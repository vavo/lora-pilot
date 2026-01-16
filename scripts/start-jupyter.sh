#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${JUPYTER_PORT:-8888}"
SECRETS="${ROOT}/config/secrets.env"
ALLOW_ORIGIN_PAT="${JUPYTER_ALLOW_ORIGIN_PAT:-https://.*\\.proxy\\.runpod\\.net}"

# Force a sane HOME (ignore ENV HOME if it's on a funky mount)
export HOME="${ROOT}/home/root"
export XDG_CACHE_HOME="${HOME}/.cache"
export XDG_CONFIG_HOME="${HOME}/.config"
export XDG_DATA_HOME="${HOME}/.local/share"

# Jupyter runtime MUST be on a filesystem that supports chmod correctly.
# /tmp almost always behaves. Workspace mounts often don't.
export JUPYTER_RUNTIME_DIR="/tmp/jupyter-runtime"

mkdir -p "${ROOT}/logs" "${ROOT}/config" "${HOME}" \
         "${XDG_CACHE_HOME}" "${XDG_CONFIG_HOME}" "${XDG_DATA_HOME}" \
         "${JUPYTER_RUNTIME_DIR}"

# Lock down perms so jupyter_server secure_write stops screaming
chmod 700 "${HOME}" "${HOME}/.local" "${HOME}/.local/share" "${JUPYTER_RUNTIME_DIR}" || true

# Load secrets if present
if [ -f "${SECRETS}" ]; then
  set -a
  source "${SECRETS}"
  set +a
fi

# Ensure token exists (write once)
if [ -z "${JUPYTER_TOKEN:-}" ]; then
  JUPYTER_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"
  echo "JUPYTER_TOKEN=${JUPYTER_TOKEN}" >> "${SECRETS}"
fi

exec /opt/venvs/tools/bin/jupyter lab \
  --ip=0.0.0.0 \
  --port="${PORT}" \
  --no-browser \
  --ServerApp.root_dir="${ROOT}" \
  --IdentityProvider.token="${JUPYTER_TOKEN}" \
  --ServerApp.allow_root=True \
  --ServerApp.allow_remote_access=True \
  --ServerApp.allow_origin_pat="${ALLOW_ORIGIN_PAT}" \
  --ServerApp.trust_xheaders=True
