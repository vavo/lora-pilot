#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${DIFFPIPE_PORT:-4444}"
REPO="/opt/pilot/repos/diffusion-pipe"
BASE_APP_DIR="${ROOT}/apps/diffusion-pipe"
LOGDIR="${DIFFPIPE_LOGDIR:-${ROOT}/logs/diffusion-pipe}"
TRAINPILOT_LOGDIR="${TRAINPILOT_TENSORBOARD_LOGDIR:-${ROOT}/logs/TrainPilot}"
TB_ROOT="${TENSORBOARD_ROOT_LOGDIR:-${ROOT}/logs/tensorboard}"
CONFIG="${DIFFPIPE_CONFIG:-}"
NUM_GPUS="${DIFFPIPE_NUM_GPUS:-1}"

export NCCL_P2P_DISABLE="${NCCL_P2P_DISABLE:-1}"
export NCCL_IB_DISABLE="${NCCL_IB_DISABLE:-1}"

mkdir -p "${BASE_APP_DIR}" "${LOGDIR}" "${TRAINPILOT_LOGDIR}" "${TB_ROOT}"
rm -rf "${TB_ROOT}/diffpipe" "${TB_ROOT}/trainpilot"
ln -s "${LOGDIR}" "${TB_ROOT}/diffpipe"
ln -s "${TRAINPILOT_LOGDIR}" "${TB_ROOT}/trainpilot"

cd "${REPO}"
TB_CMD=(/opt/venvs/core/bin/python -m tensorboard.main)
TENSORBOARD_WARNING_FILTER="ignore:pkg_resources is deprecated as an API:UserWarning"
TENSORBOARD_PYTHONWARNINGS="${PYTHONWARNINGS:+${PYTHONWARNINGS},}${TENSORBOARD_WARNING_FILTER}"

ensure_tensorboard_ready() {
  PYTHONWARNINGS="${TENSORBOARD_PYTHONWARNINGS}" /opt/venvs/core/bin/python - <<'PY'
import tensorboard.main  # noqa: F401
import pkg_resources  # noqa: F401
PY
}

extra_args=()
if [[ -n "${DIFFPIPE_EXTRA_ARGS:-}" ]]; then
  # Split extra args on spaces (simple, predictable).
  read -r -a extra_args <<< "${DIFFPIPE_EXTRA_ARGS}"
fi

if [[ -n "${CONFIG}" ]]; then
  if [[ "${DIFFPIPE_TENSORBOARD:-1}" == "1" ]]; then
    if ! ensure_tensorboard_ready; then
      echo "TensorBoard import failed in /opt/venvs/core. Rebuild the image or reinstall setuptools<81.0." >&2
      exit 1
    fi
    PYTHONWARNINGS="${TENSORBOARD_PYTHONWARNINGS}" \
      "${TB_CMD[@]}" --logdir "${TB_ROOT}" --bind_all --port "${PORT}" &
    TB_PID=$!
    trap 'kill "${TB_PID}" 2>/dev/null || true' EXIT
  fi
  exec /opt/venvs/core/bin/deepspeed --num_gpus="${NUM_GPUS}" train.py --deepspeed --config "${CONFIG}" "${extra_args[@]}"
fi

echo "DIFFPIPE_CONFIG not set. Starting TensorBoard only on port ${PORT}."
if ! ensure_tensorboard_ready; then
  echo "TensorBoard import failed in /opt/venvs/core. Rebuild the image or reinstall setuptools<81.0." >&2
  exit 1
fi
PYTHONWARNINGS="${TENSORBOARD_PYTHONWARNINGS}" exec "${TB_CMD[@]}" --logdir "${TB_ROOT}" --bind_all --port "${PORT}"
