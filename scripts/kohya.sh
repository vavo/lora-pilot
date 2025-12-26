#!/usr/bin/env bash
set -euo pipefail

# Run kohya_ss training entrypoint
exec /opt/venvs/kohya/bin/python /opt/pilot/repos/kohya_ss/train_network.py "$@"
