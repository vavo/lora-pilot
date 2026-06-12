#!/usr/bin/env bash
set -euo pipefail

create_venv() {
  local venv_path="$1"
  shift

  "${PYTHON_BIN:-python}" -m venv "${venv_path}"
  "${venv_path}/bin/pip" install --upgrade pip "$@"
}

pip_install_in_venv() {
  local venv_path="$1"
  shift

  "${venv_path}/bin/pip" install --no-cache-dir "$@"
}

pip_install_unconstrained_in_venv() {
  local venv_path="$1"
  shift

  PIP_CONSTRAINT= "${venv_path}/bin/pip" install --no-cache-dir "$@"
}

site_packages_for_venv() {
  local venv_path="$1"

  "${venv_path}/bin/python" -c 'import site; print(site.getsitepackages()[0])'
}

add_shared_core_site_packages() {
  local venv_path="$1"
  local core_venv_path="${2:-/opt/venvs/core}"
  local core_site
  local target_site

  core_site="$(site_packages_for_venv "${core_venv_path}")"
  target_site="$(site_packages_for_venv "${venv_path}")"
  printf '%s\n' "${core_site}" > "${target_site}/99-lora-pilot-core-site.pth"
}
