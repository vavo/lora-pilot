#!/usr/bin/env bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/workspace}"
PORT="${DIFFPIPE_PORT:-4444}"
REPO="/opt/pilot/repos/diffusion-pipe"
BASE_APP_DIR="${ROOT}/apps/diffusion-pipe"
LOGDIR="${DIFFPIPE_LOGDIR:-${ROOT}/logs/diffusion-pipe}"
TRAINPILOT_LOGDIR="${TRAINPILOT_TENSORBOARD_LOGDIR:-${ROOT}/logs/TrainPilot}"
KOHYA_TENSORBOARD_LOGDIR="${KOHYA_TENSORBOARD_LOGDIR:-${ROOT}/outputs}"
AI_TOOLKIT_TENSORBOARD_LOGDIR="${AI_TOOLKIT_TENSORBOARD_LOGDIR:-${ROOT}/outputs/ai-toolkit}"
TB_ROOT="${TENSORBOARD_ROOT_LOGDIR:-${ROOT}/logs/tensorboard}"
CONFIG="${DIFFPIPE_CONFIG:-}"
NUM_GPUS="${DIFFPIPE_NUM_GPUS:-1}"

export NCCL_P2P_DISABLE="${NCCL_P2P_DISABLE:-1}"
export NCCL_IB_DISABLE="${NCCL_IB_DISABLE:-1}"

mkdir -p "${BASE_APP_DIR}" "${LOGDIR}" "${TRAINPILOT_LOGDIR}" "${KOHYA_TENSORBOARD_LOGDIR}" "${AI_TOOLKIT_TENSORBOARD_LOGDIR}" "${TB_ROOT}"

ensure_tb_link() {
  local target="$1"
  local link_path="$2"

  if [ -L "${link_path}" ]; then
    local current
    current="$(readlink "${link_path}" || true)"
    if [ "${current}" != "${target}" ]; then
      rm -f "${link_path}"
      ln -s "${target}" "${link_path}"
    fi
    return
  fi

  if [ -e "${link_path}" ]; then
    return
  fi

  ln -s "${target}" "${link_path}"
}

rm -rf "${TB_ROOT}/diffpipe" "${TB_ROOT}/trainpilot" "${TB_ROOT}/kohya" "${TB_ROOT}/ai-toolkit"
ensure_tb_link "${LOGDIR}" "${TB_ROOT}/diffpipe"
ensure_tb_link "${TRAINPILOT_LOGDIR}" "${TB_ROOT}/trainpilot"
ensure_tb_link "${KOHYA_TENSORBOARD_LOGDIR}" "${TB_ROOT}/kohya"
ensure_tb_link "${AI_TOOLKIT_TENSORBOARD_LOGDIR}" "${TB_ROOT}/ai-toolkit"

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
