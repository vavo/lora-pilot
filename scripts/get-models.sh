#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
MODELS_DIR="${MODELS_DIR:-${WORKSPACE_ROOT}/models}"
CONFIG_DIR="${WORKSPACE_ROOT}/config"

MANIFEST="${MODELS_MANIFEST:-${CONFIG_DIR}/models.manifest}"
DEFAULT_MANIFEST="${DEFAULT_MODELS_MANIFEST:-/opt/pilot/config/models.manifest.default}"

VENV_PY="${VENV_PY:-/opt/venvs/core/bin/python}"
HF_BIN="${HF_BIN:-}"

# Prefer the newer `hf` CLI, fall back to huggingface-cli
resolve_hf_bin() {
  if [[ -n "${HF_BIN:-}" ]]; then
    return
  fi
  if command -v hf >/dev/null 2>&1; then
    HF_BIN="$(command -v hf)"
  elif command -v huggingface-cli >/dev/null 2>&1; then
    HF_BIN="$(command -v huggingface-cli)"
  elif [[ -x "/opt/venvs/core/bin/hf" ]]; then
    HF_BIN="/opt/venvs/core/bin/hf"
  elif [[ -x "/opt/venvs/core/bin/huggingface-cli" ]]; then
    HF_BIN="/opt/venvs/core/bin/huggingface-cli"
  else
    echo "ERROR: hf (Hugging Face CLI) not found. Install huggingface_hub." >&2
    exit 1
  fi
}

usage() {
  cat <<EOF
Usage:
  models list
  models pull <name> [--dir SUBDIR]
  models pull-all
  models where
  models help

Manifest:
  ${MANIFEST}
Default (image):
  ${DEFAULT_MANIFEST}

Env:
  WORKSPACE_ROOT=/workspace
  MODELS_DIR=/workspace/models
  MODELS_MANIFEST=/workspace/config/models.manifest
  HF_TOKEN=... (optional, for gated HF downloads)
EOF
}

ensure_seeded_manifest() {
  mkdir -p "${CONFIG_DIR}" "${MODELS_DIR}"
  if [[ ! -f "${MANIFEST}" && -f "${DEFAULT_MANIFEST}" ]]; then
    cp -f "${DEFAULT_MANIFEST}" "${MANIFEST}"
    echo "Seeded manifest -> ${MANIFEST}"
    echo "Edit it if you want. Humans love editing files."
  fi
}

require_manifest() {
  ensure_seeded_manifest
  if [[ ! -f "${MANIFEST}" ]]; then
    echo "ERROR: manifest not found: ${MANIFEST}"
    echo "Also not found: ${DEFAULT_MANIFEST}"
    exit 1
  fi
}

safe_model_dest() {
  local subdir="$1" py
  py="${VENV_PY}"
  if [[ ! -x "${py}" ]]; then
    py="$(command -v python3 || true)"
  fi
  [[ -n "${py}" ]] || { echo "ERROR: python3 not found for model path validation" >&2; exit 4; }

  "${py}" - "${MODELS_DIR}" "${subdir}" <<'PY'
import os
import sys

base = sys.argv[1]
subdir = sys.argv[2]

if not subdir or os.path.isabs(subdir):
    raise SystemExit(f"ERROR: invalid model subdir: {subdir!r}")

base_real = os.path.realpath(base)
dest_real = os.path.realpath(os.path.join(base_real, subdir))

try:
    common = os.path.commonpath([base_real, dest_real])
except ValueError:
    common = ""

if common != base_real:
    raise SystemExit(f"ERROR: model subdir escapes MODELS_DIR: {subdir!r}")

print(dest_real)
PY
}

# Manifest format (| separated):
# name|kind|source|subdir|include|size(optional)
# kind: url | hf_file | hf_repo
#
# hf_file source: <repo_id>:<path_in_repo>
# hf_repo source: <repo_id>
# include (hf_repo only): comma-separated glob patterns
read_line_for_name() {
  local name="$1"
  awk -F'|' -v n="${name}" '
    /^[[:space:]]*#/ {next}
    /^[[:space:]]*$/ {next}
    $1==n {print; found=1; exit}
    END { if (!found) exit 2 }
  ' "${MANIFEST}"
}

list_names() {
  awk -F'|' '
    /^[[:space:]]*#/ {next}
    /^[[:space:]]*$/ {next}
    {printf "%-24s  %-8s  %s\n",$1,$2,$3}
  ' "${MANIFEST}"
}

download_url() {
  local url="$1" destdir="$2"
  mkdir -p "${destdir}"
  local fn
  fn="$(basename "${url%%\?*}")"
  echo "Downloading URL -> ${destdir}/${fn}"
  curl -fL --retry 5 --retry-delay 2 -o "${destdir}/${fn}.part" "${url}"
  mv -f "${destdir}/${fn}.part" "${destdir}/${fn}"
}

hf_download_file() {
  local repo="$1" path="$2" destdir="$3"
  resolve_hf_bin
  mkdir -p "${destdir}"
  echo "HF file -> ${repo}:${path} -> ${destdir}"
  HF_TOKEN="${HF_TOKEN:-}" "${HF_BIN}" download \
    "${repo}" "${path}" \
    --local-dir "${destdir}"
}

hf_download_repo() {
  local repo="$1" destdir="$2" include_csv="${3:-}"
  resolve_hf_bin
  mkdir -p "${destdir}"
  echo "HF repo -> ${repo} -> ${destdir}"
  if [[ -n "${include_csv}" ]]; then
    IFS=',' read -r -a pats <<< "${include_csv}"
    local args=()
    for p in "${pats[@]}"; do
      [[ -n "${p// /}" ]] && args+=( --include "${p}" )
    done
    HF_TOKEN="${HF_TOKEN:-}" "${HF_BIN}" download \
      "${repo}" \
      --local-dir "${destdir}" \
      "${args[@]}"
  else
    HF_TOKEN="${HF_TOKEN:-}" "${HF_BIN}" download \
      "${repo}" \
      --local-dir "${destdir}"
  fi
}

pull_one() {
  local name="$1" override_subdir="${2:-}"
  local line kind source subdir include size
  line="$(read_line_for_name "${name}")" || {
    echo "ERROR: unknown model: ${name}"
    exit 2
  }

  IFS='|' read -r _name kind source subdir include size <<< "${line}"

  if [[ -n "${override_subdir}" ]]; then
    subdir="${override_subdir}"
  fi

  local dest
  dest="$(safe_model_dest "${subdir}")"
  case "${kind}" in
    url)
      download_url "${source}" "${dest}"
      ;;
    hf_file)
      local repo="${source%%:*}"
      local path="${source#*:}"
      hf_download_file "${repo}" "${path}" "${dest}"
      ;;
    hf_repo)
      hf_download_repo "${source}" "${dest}" "${include}"
      ;;
    *)
      echo "ERROR: bad kind in manifest for ${name}: ${kind}"
      exit 3
      ;;
  esac

  echo "Done: ${name} -> ${dest}"
}

cmd="${1:-}"
shift || true

case "${cmd}" in
  "" )
    usage
    ;;
  help|-h|--help)
    usage
    ;;
  where)
    ensure_seeded_manifest
    echo "MANIFEST=${MANIFEST}"
    echo "MODELS_DIR=${MODELS_DIR}"
    ;;
  list)
    require_manifest
    list_names
    ;;
  pull)
    require_manifest
    name="${1:-}"
    [[ -n "${name}" ]] || { usage; exit 1; }
    shift || true
    subdir=""
    if [[ "${1:-}" == "--dir" ]]; then
      subdir="${2:-}"
      [[ -n "${subdir}" ]] || { echo "ERROR: --dir needs a value"; exit 1; }
    fi
    pull_one "${name}" "${subdir}"
    ;;
  pull-all)
    require_manifest
    while IFS= read -r name; do
      [[ -n "${name}" ]] || continue
      pull_one "${name}"
    done < <(awk -F'|' ' /^[[:space:]]*#/ {next} /^[[:space:]]*$/ {next} {print $1} ' "${MANIFEST}")
    ;;
  *)
    usage
    exit 1
    ;;
esac
