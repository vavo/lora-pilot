#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="/opt/pilot/repos/kohya_ss:/opt/pilot/repos/kohya_ss/sd-scripts:${PYTHONPATH:-}"

exec /opt/venvs/core/bin/python /opt/pilot/repos/kohya_ss/train_network.py "$@"
