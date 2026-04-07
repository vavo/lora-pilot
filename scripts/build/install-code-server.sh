#!/usr/bin/env bash
set -euo pipefail

: "${CODE_SERVER_VERSION:?CODE_SERVER_VERSION is required}"

retry_curl() {
  curl --fail --silent --show-error --location \
    --retry 5 \
    --retry-all-errors \
    --retry-delay 5 \
    "$@"
}

version_tag="${CODE_SERVER_VERSION}"
case "${version_tag}" in
  v*) ;;
  *) version_tag="v${version_tag}" ;;
esac

arch="$(dpkg --print-architecture)"
case "${arch}" in
  amd64)
    asset_name="code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz"
    asset_dir="code-server-${CODE_SERVER_VERSION}-linux-amd64"
    asset_sha256="86a2cb89038846c2ae6ca1945a56eaad473b23f145727f9d923f6d174b436f2c"
    ;;
  arm64)
    asset_name="code-server-${CODE_SERVER_VERSION}-linux-arm64.tar.gz"
    asset_dir="code-server-${CODE_SERVER_VERSION}-linux-arm64"
    asset_sha256="9b58b51f3d223a4f4b27d75550dd385c638aeee017342436cdc027ab6cd3a5d9"
    ;;
  *)
    echo "Unsupported architecture for code-server: ${arch}" >&2
    exit 1
    ;;
esac

download_url="https://github.com/coder/code-server/releases/download/${version_tag}/${asset_name}"
tmp_dir="$(mktemp -d)"
archive_path="${tmp_dir}/${asset_name}"
install_root="/usr/lib/code-server"
cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

retry_curl "${download_url}" -o "${archive_path}"
printf '%s  %s\n' "${asset_sha256}" "${archive_path}" | sha256sum -c -
tar -xzf "${archive_path}" -C "${tmp_dir}"

rm -rf "${install_root}"
mkdir -p "${install_root}"
cp -a "${tmp_dir}/${asset_dir}/." "${install_root}/"
ln -sf "${install_root}/bin/code-server" /usr/bin/code-server

/usr/bin/code-server --version
