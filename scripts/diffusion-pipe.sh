#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${DIFFPIPE_PORT:-4444}"
REPO="/opt/pilot/repos/diffusion-pipe"
BASE_APP_DIR="${ROOT}/apps/diffusion-pipe"
LOGDIR="${DIFFPIPE_LOGDIR:-${ROOT}/logs/diffusion-pipe}"
CONFIG="${DIFFPIPE_CONFIG:-}"
NUM_GPUS="${DIFFPIPE_NUM_GPUS:-1}"

export NCCL_P2P_DISABLE="${NCCL_P2P_DISABLE:-1}"
export NCCL_IB_DISABLE="${NCCL_IB_DISABLE:-1}"

mkdir -p "${BASE_APP_DIR}" "${LOGDIR}"

source /opt/venvs/core/bin/activate
cd "${REPO}"

extra_args=()
if [[ -n "${DIFFPIPE_EXTRA_ARGS:-}" ]]; then
  # Split extra args on spaces (simple, predictable).
  read -r -a extra_args <<< "${DIFFPIPE_EXTRA_ARGS}"
fi

if [[ -n "${CONFIG}" ]]; then
  if [[ "${DIFFPIPE_TENSORBOARD:-1}" == "1" ]]; then
    # Silence pkg_resources deprecation warning from tensorboard
    PYTHONWARNINGS="${PYTHONWARNINGS:-ignore:pkg_resources is deprecated as an API:UserWarning}" \
      /opt/venvs/core/bin/tensorboard --logdir "${LOGDIR}" --bind_all --port "${PORT}" &
    TB_PID=$!
    trap 'kill "${TB_PID}" 2>/dev/null || true' EXIT
  fi
  exec deepspeed --num_gpus="${NUM_GPUS}" train.py --deepspeed --config "${CONFIG}" "${extra_args[@]}"
fi

echo "DIFFPIPE_CONFIG not set. Starting TensorBoard only on port ${PORT}."
exec /opt/venvs/core/bin/tensorboard --logdir "${LOGDIR}" --bind_all --port "${PORT}"
