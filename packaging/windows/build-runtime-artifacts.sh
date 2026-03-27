#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

IMAGE="${IMAGE:-lora-pilot}"
TAG="${TAG:-wsl-runtime}"
FULL_IMAGE="${IMAGE}:${TAG}"
PLATFORM="${PLATFORM:-linux/amd64}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/dist/windows-runtime}"
APP_VERSION="${APP_VERSION:-$(git -C "${ROOT_DIR}" describe --tags --always --dirty 2>/dev/null || echo dev)}"
RUNTIME_VERSION="${RUNTIME_VERSION:-${APP_VERSION}}"
VCS_REF="${VCS_REF:-$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)}"
BUILD_DATE="${BUILD_DATE:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}"
PUBLISHED_AT="${PUBLISHED_AT:-${BUILD_DATE}}"
MIN_WINDOWS_BUILD="${MIN_WINDOWS_BUILD:-19045}"
RUNTIME_BASE_URL="${RUNTIME_BASE_URL:-}"

rootfs_name="lora-pilot-wsl-rootfs-${RUNTIME_VERSION}.tar.zst"
overlay_name="lora-pilot-wsl-overlay-${RUNTIME_VERSION}.tar.zst"
manifest_name="windows-runtime-manifest.json"
rootfs_path="${OUTPUT_DIR}/${rootfs_name}"
overlay_path="${OUTPUT_DIR}/${overlay_name}"
manifest_path="${OUTPUT_DIR}/${manifest_name}"

mkdir -p "${OUTPUT_DIR}"

if [[ -z "${RUNTIME_BASE_URL}" ]]; then
  if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
    release_ref="${GITHUB_REF_NAME:-${APP_VERSION}}"
    RUNTIME_BASE_URL="https://github.com/${GITHUB_REPOSITORY}/releases/download/${release_ref}"
  else
    RUNTIME_BASE_URL="https://example.invalid/lora-pilot/${APP_VERSION}"
  fi
fi

sha256_tool() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

write_sha_file() {
  local file_path="$1"
  local hash_value
  hash_value="$(sha256_tool "${file_path}")"
  printf '%s  %s\n' "${hash_value}" "$(basename "${file_path}")" > "${file_path}.sha256"
}

container_id=""
cleanup() {
  if [[ -n "${container_id}" ]]; then
    docker rm -f "${container_id}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Building ${FULL_IMAGE} for ${PLATFORM}"
docker buildx build \
  --platform "${PLATFORM}" \
  --tag "${FULL_IMAGE}" \
  --build-arg APP_VERSION="${APP_VERSION}" \
  --build-arg RUNTIME_VERSION="${RUNTIME_VERSION}" \
  --build-arg VCS_REF="${VCS_REF}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --load \
  "${ROOT_DIR}"

container_id="$(docker create --platform "${PLATFORM}" "${FULL_IMAGE}" sleep infinity)"

echo "Exporting fresh-install rootfs to ${rootfs_path}"
tmp_rootfs="${OUTPUT_DIR}/rootfs-${RUNTIME_VERSION}.tar"
docker export "${container_id}" -o "${tmp_rootfs}"
zstd -f -19 "${tmp_rootfs}" -o "${rootfs_path}"
rm -f "${tmp_rootfs}"

echo "Exporting in-place upgrade overlay to ${overlay_path}"
docker start "${container_id}" >/dev/null
docker exec "${container_id}" tar --zstd -cpf - \
  --absolute-names \
  /opt/pilot \
  /opt/venvs \
  /usr/local/bin/pilot \
  /usr/local/bin/models \
  /usr/local/bin/pilot-models \
  /usr/local/bin/modelsgui \
  /etc/profile.d/core-venv.sh \
  /etc/supervisor/supervisord.conf \
  > "${overlay_path}"
docker stop "${container_id}" >/dev/null

write_sha_file "${rootfs_path}"
write_sha_file "${overlay_path}"

ROOTFS_SHA256="$(sha256_tool "${rootfs_path}")"
OVERLAY_SHA256="$(sha256_tool "${overlay_path}")"
export APP_VERSION RUNTIME_VERSION PUBLISHED_AT MIN_WINDOWS_BUILD RUNTIME_BASE_URL ROOTFS_SHA256 OVERLAY_SHA256
export ROOTFS_NAME="${rootfs_name}" OVERLAY_NAME="${overlay_name}"

python3 - <<'PY' > "${manifest_path}"
import json
import os

payload = {
    "app_version": os.environ["APP_VERSION"],
    "runtime_version": os.environ["RUNTIME_VERSION"],
    "published_at": os.environ["PUBLISHED_AT"],
    "min_windows_build": int(os.environ["MIN_WINDOWS_BUILD"]),
    "fresh_install": {
        "url": f"{os.environ['RUNTIME_BASE_URL'].rstrip('/')}/{os.environ['ROOTFS_NAME']}",
        "sha256": os.environ["ROOTFS_SHA256"],
    },
    "upgrade_overlay": {
        "url": f"{os.environ['RUNTIME_BASE_URL'].rstrip('/')}/{os.environ['OVERLAY_NAME']}",
        "sha256": os.environ["OVERLAY_SHA256"],
    },
    "ports": {
        "controlpilot": 7878,
        "jupyter": 8888,
        "code_server": 8443,
        "comfyui": 5555,
        "kohya": 6666,
        "tensorboard": 4444,
        "invokeai": 9090,
        "ai_toolkit": 8675,
        "copilot_sidecar": 7879,
    },
}

print(json.dumps(payload, indent=2, sort_keys=True))
PY

write_sha_file "${manifest_path}"

echo "Runtime artifacts written to ${OUTPUT_DIR}"
