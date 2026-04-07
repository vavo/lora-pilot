#!/usr/bin/env bash
set -euo pipefail

if [[ "${INSTALL_COPILOT_CLI:-1}" != "1" ]]; then
  echo "Skipping Copilot CLI install (INSTALL_COPILOT_CLI=${INSTALL_COPILOT_CLI:-0})"
  exit 0
fi

retry_curl() {
  curl --fail --silent --show-error --location \
    --retry 5 \
    --retry-all-errors \
    --retry-delay 5 \
    "$@"
}

version_tag="${COPILOT_CLI_VERSION:-latest}"
case "${version_tag}" in
  latest) ;;
  v*) ;;
  *) version_tag="v${version_tag}" ;;
esac

arch="$(dpkg --print-architecture)"
case "${arch}" in
  amd64)
    asset_name="copilot-linux-x64.tar.gz"
    asset_sha256="b9b8a67a023f3923a76a6819a11d069293a0ff1209a04588c4f3d048c03c7328"
    ;;
  arm64)
    asset_name="copilot-linux-arm64.tar.gz"
    asset_sha256="2bdeddf816f63a39a3b129278770af19dd371392424260a52d10c44c68774751"
    ;;
  *)
    echo "Unsupported architecture for Copilot CLI: ${arch}" >&2
    exit 1
    ;;
esac

download_url="https://github.com/github/copilot-cli/releases/download/${version_tag}/${asset_name}"
tmp_dir="$(mktemp -d)"
archive_path="${tmp_dir}/${asset_name}"
cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

retry_curl "${download_url}" -o "${archive_path}"
printf '%s  %s\n' "${asset_sha256}" "${archive_path}" | sha256sum -c -
tar -xzf "${archive_path}" -C "${tmp_dir}"
install -m 0755 "${tmp_dir}/copilot" /usr/local/bin/copilot

command -v copilot
copilot --version || true
