#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${MEDIAPILOT_REPO_URL:-https://github.com/vavo/MediaPilot.git}"
REF="${1:-main}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${ROOT}/apps/MediaPilot"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "Cloning ${REPO_URL} (${REF})..."
git clone --depth 1 --branch "${REF}" "${REPO_URL}" "${TMP_DIR}/src"

UPSTREAM_COMMIT="$(git -C "${TMP_DIR}/src" rev-parse HEAD)"
echo "Upstream commit: ${UPSTREAM_COMMIT}"

rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"
rsync -a --delete --exclude .git "${TMP_DIR}/src/" "${TARGET_DIR}/"
printf '%s\n' "${UPSTREAM_COMMIT}" > "${TARGET_DIR}/.upstream-commit"

cat <<MSG
MediaPilot vendored to ${TARGET_DIR}
Recorded upstream commit in ${TARGET_DIR}/.upstream-commit
Next step: reapply ControlPilot-specific customizations if upstream changed static/API paths.
MSG
