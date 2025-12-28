#!/usr/bin/env bash
set -euo pipefail

echo "[smoke] python:"
python --version

echo "[smoke] jupyter:"
jupyter lab --version

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[smoke] nvidia-smi:"
  nvidia-smi || true
else
  echo "[smoke] nvidia-smi not found (ok on Mac/CPU)"
fi

echo "[smoke] OK"
