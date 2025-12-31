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
  models            (GUI)
  models gui
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

require_whiptail() {
  # Force a sane TERM for whiptail (code-server shells sometimes pass odd values)
  export TERM="xterm-256color"
  if ! command -v whiptail >/dev/null 2>&1; then
    echo "ERROR: whiptail not found."
    echo "Install it (apt-get update && apt install -y whiptail) or use CLI: models list/pull."
    exit 1
  fi
}

require_tty() {
  if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo "ERROR: GUI mode requires a TTY. Run this in an interactive shell (e.g., docker exec -it ...)." >&2
    exit 1
  fi
}

# Categories: SDXL | FLUX | WAN | OTHERS
classify_model() {
  local name="$1" source="$2" subdir="$3"
  local key
  key="$(printf '%s %s %s' "${name}" "${source}" "${subdir}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${key}" == *"flux"* ]]; then
    echo "FLUX"
    return
  fi
  if [[ "${key}" == *"wan"* ]]; then
    echo "WAN"
    return
  fi
  if [[ "${key}" == *"sdxl"* || "${key}" == *"sd_xl"* || "${key}" == *"stable-diffusion-xl"* || "${key}" == *"-xl"* || "${key}" == *"xl-"* ]]; then
    echo "SDXL"
    return
  fi
  echo "OTHERS"
}

checkbox_label() {
  local label="$1" enabled="$2"
  if [[ "${enabled}" -eq 1 ]]; then
    echo "[x] ${label}"
  else
    echo "[ ] ${label}"
  fi
}

build_menu_items() {
  local f_sdxl="$1" f_flux="$2" f_wan="$3" f_others="$4"
  menu_items=()
  menu_items+=( "toggle_sdxl" "$(checkbox_label "SDXL" "${f_sdxl}")" )
  menu_items+=( "toggle_flux" "$(checkbox_label "FLUX" "${f_flux}")" )
  menu_items+=( "toggle_wan" "$(checkbox_label "WAN" "${f_wan}")" )
  menu_items+=( "toggle_others" "$(checkbox_label "OTHERS" "${f_others}")" )
  menu_items+=( "__sep" "------------------------------" )

  local has_models=0
  declare -A seen=()

  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    IFS='|' read -r name kind source subdir include <<< "${line}"

    [[ -n "${seen[${name}]:-}" ]] && continue
    seen["${name}"]=1

    local cat
    cat="$(classify_model "${name}" "${source}" "${subdir}")"
    case "${cat}" in
      SDXL) [[ "${f_sdxl}" -eq 1 ]] || continue ;;
      FLUX) [[ "${f_flux}" -eq 1 ]] || continue ;;
      WAN) [[ "${f_wan}" -eq 1 ]] || continue ;;
      OTHERS) [[ "${f_others}" -eq 1 ]] || continue ;;
    esac

    has_models=1
    local desc="${kind}"
    if [[ -n "${subdir}" ]]; then
      desc="${desc} -> ${subdir}"
    fi
    menu_items+=( "${name}" "${desc}" )
  done < "${MANIFEST}"

  if [[ "${has_models}" -eq 0 ]]; then
    menu_items+=( "__none" "<no models match current filters>" )
  fi
}

download_with_gauge() {
  local name="$1"
  local log_file
  log_file="$(mktemp)"

  # Check if HF_TOKEN is required but not set
  if [[ -z "${HF_TOKEN:-}" ]]; then
    HF_TOKEN=$(whiptail --title "Hugging Face Token Required" \
      --inputbox "Hugging Face token is required to download this model.\n\nDon't have one? Get it here: https://huggingface.co/settings/tokens\n\nEnter your token:" \
      12 70 \
      3>&1 1>&2 2>&3) || return 1
    
    if [[ -z "${HF_TOKEN}" ]]; then
      whiptail --title "Error" --msgbox "No token provided. Download cancelled." 8 50
      return 1
    fi
  fi

  # Export the token for the subprocess
  export HF_TOKEN

  (
    pull_one "${name}" >"${log_file}" 2>&1
  ) &
  local pid=$!

  (
    local pct=0
    while kill -0 "${pid}" 2>/dev/null; do
      echo "${pct}"
      echo "# Downloading ${name}..."
      pct=$(( (pct + 4) % 100 ))
      sleep 0.2
    done
    echo 100
    echo "# Finalizing..."
  ) | whiptail --title "Downloading" --gauge "Downloading ${name}" 8 70 0 --nocancel

  local rc=0
  wait "${pid}" || rc=$?

  if [[ "${rc}" -ne 0 ]]; then
    local tail_out=""
    if [[ -s "${log_file}" ]]; then
      tail_out="$(tail -n 20 "${log_file}" 2>/dev/null)"
    fi
    local msg
    msg="$(printf "Download failed for %s.\n\nLast output:\n%s\n\nLog: %s" \
      "${name}" "${tail_out}" "${log_file}")"
    whiptail --title "Download Failed" --msgbox "${msg}" 16 80
    return "${rc}"
  fi

  rm -f "${log_file}"
  whiptail --title "Done" --msgbox "Downloaded ${name}." 8 50
}

gui() {
  require_tty
  require_manifest
  require_whiptail

  local f_sdxl=1
  local f_flux=1
  local f_wan=1
  local f_others=1

  while true; do
    build_menu_items "${f_sdxl}" "${f_flux}" "${f_wan}" "${f_others}"
    local choice
    choice="$(whiptail --title "Models" \
      --menu "Toggle filters at the top. Select a model to download." \
      25 100 17 \
      "${menu_items[@]}" \
      3>&1 1>&2 2>&3)" || {
        rc=$?
        echo "models gui: whiptail failed (rc=${rc}). Ensure TERM is set and a TTY is available. Falling back to CLI list."
        list_names
        exit "${rc}"
      }

    case "${choice}" in
      toggle_sdxl) f_sdxl=$((1 - f_sdxl)) ;;
      toggle_flux) f_flux=$((1 - f_flux)) ;;
      toggle_wan) f_wan=$((1 - f_wan)) ;;
      toggle_others) f_others=$((1 - f_others)) ;;
      __sep|__none) ;;
      *)
        download_with_gauge "${choice}" || true
        ;;
    esac
  done
}

# Manifest format (| separated):
# name|kind|source|subdir|include
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
    --local-dir "${destdir}" \
    --local-dir-use-symlinks False
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
      --local-dir-use-symlinks False \
      "${args[@]}"
  else
    HF_TOKEN="${HF_TOKEN:-}" "${HF_BIN}" download \
      "${repo}" \
      --local-dir "${destdir}" \
      --local-dir-use-symlinks False
  fi
}

pull_one() {
  local name="$1" override_subdir="${2:-}"
  local line kind source subdir include
  line="$(read_line_for_name "${name}")" || {
    echo "ERROR: unknown model: ${name}"
    exit 2
  }

  IFS='|' read -r _name kind source subdir include <<< "${line}"

  if [[ -n "${override_subdir}" ]]; then
    subdir="${override_subdir}"
  fi

  local dest="${MODELS_DIR}/${subdir}"
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
  ""|gui)
    gui
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
