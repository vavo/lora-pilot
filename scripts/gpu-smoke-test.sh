#!/usr/bin/env bash
set -euo pipefail

PY="/opt/venvs/core/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "[gpu-smoke] core venv not found at /opt/venvs/core (INSTALL_GPU_STACK was probably 0)"
  exit 1
fi

echo "[gpu-smoke] python:"
"$PY" -V

echo "[gpu-smoke] torch + cuda:"
"$PY" - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("torch cuda:", torch.version.cuda)
if torch.cuda.is_available():
    print("device count:", torch.cuda.device_count())
    print("device 0:", torch.cuda.get_device_name(0))
    a = torch.randn((1024, 1024), device="cuda")
    b = torch.randn((1024, 1024), device="cuda")
    c = a @ b
    print("matmul ok:", c.shape, c.dtype)
PY

echo "[gpu-smoke] xformers:"
"$PY" - <<'PY'
import xformers
print("xformers:", xformers.__version__)
PY

echo "[gpu-smoke] OK"
