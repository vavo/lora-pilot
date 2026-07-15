#!/usr/bin/env bash
set -euo pipefail

: "${CUDA_NVCC_PKG:?CUDA_NVCC_PKG is required}"
: "${CROC_VERSION:?CROC_VERSION is required}"
: "${NODE_MAJOR:?NODE_MAJOR is required}"
: "${NPM_VERSION:?NPM_VERSION is required}"

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  wget \
  zip \
  unzip \
  openssl \
  tini \
  supervisor \
  software-properties-common \
  gnupg \
  build-essential \
  iproute2 \
  libgl1 \
  libglib2.0-0 \
  whiptail \
  "${CUDA_NVCC_PKG}" \
  mc \
  nano
apt-get -y autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/*

if [[ "${INSTALL_AI_TOOLKIT_UI:-1}" == "1" ]]; then
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
  chmod 644 /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list
  apt-get update
  apt-get install -y --no-install-recommends nodejs
  npm install -g "npm@${NPM_VERSION}"
  apt-get clean
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
