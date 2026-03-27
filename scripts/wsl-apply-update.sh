#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "wsl-apply-update.sh must run as root" >&2
  exit 1
fi

ARCHIVE_PATH="${1:-}"
EXPECTED_RUNTIME_VERSION="${2:-}"

if [[ -z "${ARCHIVE_PATH}" ]]; then
  echo "usage: /opt/pilot/wsl-apply-update.sh <overlay-archive> [expected-runtime-version]" >&2
  exit 2
fi

if [[ ! -f "${ARCHIVE_PATH}" ]]; then
  echo "overlay archive not found: ${ARCHIVE_PATH}" >&2
  exit 1
fi

case "${ARCHIVE_PATH}" in
  *.tar.zst|*.tzst)
    tar --zstd -xpf "${ARCHIVE_PATH}" -C /
    ;;
  *.tar.gz|*.tgz)
    tar -xzpf "${ARCHIVE_PATH}" -C /
    ;;
  *.tar)
    tar -xpf "${ARCHIVE_PATH}" -C /
    ;;
  *)
    echo "unsupported archive format: ${ARCHIVE_PATH}" >&2
    exit 1
    ;;
esac

if [[ -n "${EXPECTED_RUNTIME_VERSION}" ]]; then
  actual_version="$(python3 - <<'PY'
import json
from pathlib import Path

path = Path("/opt/pilot/runtime/version.json")
if not path.exists():
    print("")
else:
    print(json.loads(path.read_text()).get("runtime_version", ""))
PY
)"
  if [[ "${actual_version}" != "${EXPECTED_RUNTIME_VERSION}" ]]; then
    echo "runtime version mismatch after update: expected ${EXPECTED_RUNTIME_VERSION}, got ${actual_version}" >&2
    exit 1
  fi
fi

echo "runtime update applied"
