#!/usr/bin/env bash
set -euo pipefail

. /opt/pilot/build/lib/python_venv.sh

: "${JUPYTERLAB_VERSION:?JUPYTERLAB_VERSION is required}"
: "${IPYWIDGETS_VERSION:?IPYWIDGETS_VERSION is required}"

create_venv /opt/venvs/core "setuptools<81.0" wheel
pip_install_in_venv /opt/venvs/core \
  "jupyterlab==${JUPYTERLAB_VERSION}" \
  "ipywidgets==${IPYWIDGETS_VERSION}"
