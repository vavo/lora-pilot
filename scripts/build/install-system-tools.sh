#!/usr/bin/env bash
set -euo pipefail

: "${CUDA_NVCC_PKG:?CUDA_NVCC_PKG is required}"
: "${CROC_VERSION:?CROC_VERSION is required}"

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  wget \
  unzip \
  openssl \
  tini \
  supervisor \
  software-properties-common \
  build-essential \
  iproute2 \
  procps \
  libgl1 \
  libglib2.0-0 \
  whiptail \
  zstd \
  "${CUDA_NVCC_PKG}" \
  mc \
  nano
apt-get -y autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/*

if [[ "${INSTALL_AI_TOOLKIT_UI:-1}" == "1" ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y --no-install-recommends nodejs
  rm -rf /var/lib/apt/lists/*
  node -v
  npm -v
fi

arch="$(dpkg --print-architecture)"
case "${arch}" in
  amd64) croc_arch="Linux-64bit" ;;
  arm64) croc_arch="Linux-ARM64" ;;
  *)
    echo "Unsupported arch for croc: ${arch}" >&2
    exit 1
    ;;
esac

url="https://github.com/schollz/croc/releases/download/v${CROC_VERSION}/croc_v${CROC_VERSION}_${croc_arch}.tar.gz"
tmp_dir="$(mktemp -d)"
curl -fL "${url}" -o "${tmp_dir}/croc.tgz"
tar -xzf "${tmp_dir}/croc.tgz" -C "${tmp_dir}"
croc_path="$(find "${tmp_dir}" -maxdepth 2 -type f -name croc -print -quit)"
if [[ -z "${croc_path}" ]]; then
  echo "croc binary not found in ${url}" >&2
  exit 1
fi
install -m 0755 "${croc_path}" /usr/local/bin/croc
rm -rf "${tmp_dir}"
croc --version
