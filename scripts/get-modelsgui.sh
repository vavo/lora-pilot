#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${CONFIG_DIR:-/workspace/config}"
MANIFEST="${MODELS_MANIFEST:-${CONFIG_DIR}/models.manifest}"
DEFAULT_MANIFEST="${DEFAULT_MODELS_MANIFEST:-/opt/pilot/config/models.manifest.default}"

BASE_DIR="${BASE_DIR:-/workspace/models}"
TITLE="${TITLE:-Model Downloader}"
WHIPTAIL_BIN="${WHIPTAIL_BIN:-whiptail}"
LOGFILE="${LOGFILE:-/tmp/model_downloader.log}"

die() { echo "ERROR: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

ensure_term() {
  if [[ -z "${TERM:-}" || "${TERM:-}" == "dumb" ]]; then
    export TERM="xterm-256color"
  fi
}

is_interactive_tty() {
  [[ -t 0 && -e /dev/tty ]]
}

# -------- deps --------
need_cmd awk
need_cmd sed
need_cmd mkdir
need_cmd tr
need_cmd mktemp
need_cmd python
python -c "import huggingface_hub" >/dev/null 2>&1 || die "python package missing: huggingface_hub"

# For hf_file we can use hf/huggingface-cli if available, else python
FILE_DL="python"
if have_cmd hf; then
  FILE_DL="hf"
elif have_cmd huggingface-cli; then
  FILE_DL="huggingface-cli"
fi

if [[ ! -f "$MANIFEST" ]]; then
  [[ -f "$DEFAULT_MANIFEST" ]] || die "Manifest not found: $MANIFEST (default: $DEFAULT_MANIFEST)"
  MANIFEST="$DEFAULT_MANIFEST"
fi
mkdir -p "$BASE_DIR"
: > "$LOGFILE"

# -------- parse manifest into arrays --------
declare -a IDS NAMES KINDS SOURCES SUBDIRS INCLUDES SIZES

i=0
while IFS= read -r raw || [[ -n "$raw" ]]; do
  line="$(trim "$raw")"
  [[ -z "$line" ]] && continue
  [[ "$line" == \#* ]] && continue

  IFS='|' read -r f_name f_kind f_source f_subdir f_include f_size <<< "$line"
  f_name="$(trim "${f_name:-}")"
  f_kind="$(trim "${f_kind:-}")"
  f_source="$(trim "${f_source:-}")"
  f_subdir="$(trim "${f_subdir:-}")"
  f_include="$(trim "${f_include:-}")"
  f_size="$(trim "${f_size:-}")"

  [[ -z "$f_name" || -z "$f_kind" || -z "$f_source" || -z "$f_subdir" ]] && continue

  IDS[i]="$i"
  NAMES[i]="$f_name"
  KINDS[i]="$f_kind"
  SOURCES[i]="$f_source"
  SUBDIRS[i]="$f_subdir"
  INCLUDES[i]="$f_include"
  SIZES[i]="$f_size"

  ((i+=1))
done < "$MANIFEST"

[[ ${#IDS[@]} -gt 0 ]] || die "No valid model entries found in $MANIFEST"

# -------- filtering --------
category_for_name() {
  local name="$1"
  local n="${name,,}"
  if [[ "$n" == sdxl-* || "$n" == *-xl* || "$n" == *xl* ]]; then
    echo "SDXL"
  elif [[ "$n" == flux* ]]; then
    echo "Flux"
  elif [[ "$n" == wan* ]]; then
    echo "Wan"
  else
    echo "Others"
  fi
}

passes_filter() {
  local idx="$1"
  local filter="$2"
  [[ "$filter" == "All" ]] && return 0
  local cat
  cat="$(category_for_name "${NAMES[idx]}")"
  [[ "$cat" == "$filter" ]]
}

# -------- selection UIs (whiptail) --------
select_filter_whiptail() {
  ensure_term
  have_cmd "$WHIPTAIL_BIN" || return 2
  is_interactive_tty || return 2

  local tmp rc out
  tmp="$(mktemp)"
  set +e
  "$WHIPTAIL_BIN" --title "$TITLE" \
    --menu "Filter models:" \
    15 60 6 \
    "All"    "Show everything" \
    "SDXL"   "SDXL and XL models" \
    "Flux"   "FLUX models" \
    "Wan"    "WAN models" \
    "Others" "Everything else" \
    --output-fd 3 \
    </dev/tty >/dev/tty 2>>"$LOGFILE" 3>"$tmp"
  rc=$?
  set -e

  out="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp"

  if [[ $rc -eq 0 ]]; then echo "$out"; return 0; fi
  if [[ $rc -eq 1 ]]; then echo ""; return 1; fi
  return 2
}

select_models_whiptail() {
  local filter="$1"

  ensure_term
  have_cmd "$WHIPTAIL_BIN" || return 2
  is_interactive_tty || return 2

  local HEIGHT="${HEIGHT:-22}"
  local WIDTH="${WIDTH:-110}"
  local LISTHEIGHT="${LISTHEIGHT:-14}"

  local -a menu_items=()
  local count=0

  for idx in "${IDS[@]}"; do
    passes_filter "$idx" "$filter" || continue
    local name="${NAMES[idx]}"
    local kind="${KINDS[idx]}"
    local sub="${SUBDIRS[idx]}"
    local size="${SIZES[idx]}"
    local desc="$kind -> $sub"
    [[ -n "$size" ]] && desc="$desc ($size)"
    menu_items+=("$idx" "$name | $desc" "OFF")
    ((count+=1))
  done

  [[ $count -gt 0 ]] || return 3

  local tmp rc out
  tmp="$(mktemp)"
  set +e
  "$WHIPTAIL_BIN" --title "$TITLE" \
    --checklist "Select models to download (filter: $filter)" \
    "$HEIGHT" "$WIDTH" "$LISTHEIGHT" \
    "${menu_items[@]}" \
    --output-fd 3 \
    </dev/tty >/dev/tty 2>>"$LOGFILE" 3>"$tmp"
  rc=$?
  set -e

  out="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp"

  if [[ $rc -eq 0 ]]; then echo "$out" | tr -d '"'; return 0; fi
  if [[ $rc -eq 1 ]]; then echo ""; return 1; fi
  return 2
}

# -------- selection UIs (text fallback) --------
select_filter_text() {
  echo "Whiptail UI unavailable. Using text filter selection." | tee -a "$LOGFILE" >&2
  echo "Choose filter: All / SDXL / Flux / Wan / Others" >&2
  read -r -p "> " ans || true
  ans="$(trim "${ans:-}")"
  [[ -z "$ans" ]] && { echo ""; return 1; }
  case "$ans" in
    All|SDXL|Flux|Wan|Others) echo "$ans"; return 0 ;;
    *) die "Invalid filter: $ans" ;;
  esac
}

select_models_text() {
  local filter="$1"

  echo "Available models (filter: $filter):" >&2
  for idx in "${IDS[@]}"; do
    passes_filter "$idx" "$filter" || continue
    name="${NAMES[idx]}"
    kind="${KINDS[idx]}"
    sub="${SUBDIRS[idx]}"
    size="${SIZES[idx]}"
    printf "  [%s] %-22s  %-7s  -> %-24s  %s\n" "$idx" "$name" "$kind" "$sub" "${size:-}" >&2
  done

  echo "" >&2
  echo "Enter numbers separated by spaces (example: 0 3 7), or 'all', or empty to cancel:" >&2
  read -r -p "> " ans || true
  ans="$(trim "${ans:-}")"
  [[ -z "$ans" ]] && { echo ""; return 1; }

  if [[ "$ans" == "all" ]]; then
    local -a chosen=()
    for idx in "${IDS[@]}"; do
      passes_filter "$idx" "$filter" || continue
      chosen+=("$idx")
    done
    printf "%s " "${chosen[@]}"
    echo
    return 0
  fi

  local -a chosen=()
  for tok in $ans; do
    [[ "$tok" =~ ^[0-9]+$ ]] || die "Bad selection token: '$tok'"
    [[ "$tok" -ge 0 && "$tok" -lt "${#IDS[@]}" ]] || die "Selection out of range: '$tok'"
    passes_filter "$tok" "$filter" || die "Selection $tok not in filter '$filter'"
    chosen+=("$tok")
  done

  printf "%s " "${chosen[@]}"
  echo
  return 0
}

# -------- downloads --------
hf_download_file() {
  local source="$1"
  local outdir="$2"

  local repo="" file=""
  if [[ "$source" == *"/blob/"* ]]; then
    repo="${source%%/blob/*}"
    file="${source#*/blob/*/}"
  elif [[ "$source" == *":"* ]]; then
    repo="${source%%:*}"
    file="${source#*:}"
  else
    die "Bad hf_file source '$source' (expected 'org/repo:filename' or 'org/repo/blob/<rev>/path')"
  fi

  mkdir -p "$outdir"

  if [[ "$FILE_DL" == "hf" ]]; then
    hf download "$repo" "$file" --local-dir "$outdir"
  elif [[ "$FILE_DL" == "huggingface-cli" ]]; then
    huggingface-cli download "$repo" "$file" --local-dir "$outdir" --local-dir-use-symlinks False
  else
    python - "$repo" "$file" "$outdir" <<'PY'
import sys, os
from huggingface_hub import hf_hub_download

repo = sys.argv[1]
filename = sys.argv[2]
outdir = sys.argv[3]
os.makedirs(outdir, exist_ok=True)
path = hf_hub_download(repo_id=repo, filename=filename, local_dir=outdir, local_dir_use_symlinks=False)
print(path)
PY
  fi
}

hf_download_repo_python() {
  local repo="$1"
  local outdir="$2"
  local include="$3"

  mkdir -p "$outdir"

  python - "$repo" "$outdir" "$include" <<'PY'
import sys, os
from huggingface_hub import snapshot_download

repo = sys.argv[1]
outdir = sys.argv[2]
include = sys.argv[3]

os.makedirs(outdir, exist_ok=True)

allow = None
if include.strip():
    allow = [p.strip() for p in include.split(",") if p.strip()]

snapshot_download(
    repo_id=repo,
    local_dir=outdir,
    local_dir_use_symlinks=False,
    allow_patterns=allow,
)
print("Snapshot downloaded to", outdir, "allow_patterns=", allow)
PY
}

# -------- flow --------
filter=""
if filter="$(select_filter_whiptail)"; then
  :
else
  rc=$?
  [[ $rc -eq 1 ]] && exit 0
  filter="$(select_filter_text)" || exit 0
fi

filter="$(trim "$filter")"
[[ -n "$filter" ]] || exit 0

selected=""
if selected="$(select_models_whiptail "$filter")"; then
  :
else
  rc=$?
  [[ $rc -eq 1 ]] && exit 0
  selected="$(select_models_text "$filter")" || exit 0
fi

selected="$(echo "$selected" | tr -d '"')"
selected="$(trim "$selected")"
[[ -n "$selected" ]] || exit 0

for idx in $selected; do
  name="${NAMES[idx]}"
  kind="${KINDS[idx]}"
  source="${SOURCES[idx]}"
  subdir="${SUBDIRS[idx]}"
  include="${INCLUDES[idx]}"
  size="${SIZES[idx]}"
  target="$BASE_DIR/$subdir"

  echo "==> $name ($kind) -> $target ${size:+[$size]}" | tee -a "$LOGFILE"

  case "$kind" in
    hf_file)
      hf_download_file "$source" "$target" 2>&1 | tee -a "$LOGFILE"
      ;;
    hf_repo)
      hf_download_repo_python "$source" "$target" "$include" 2>&1 | tee -a "$LOGFILE"
      ;;
    *)
      echo "Skipping '$name': unknown kind '$kind'" | tee -a "$LOGFILE"
      ;;
  esac

  echo "" | tee -a "$LOGFILE"
done

if have_cmd "$WHIPTAIL_BIN" && is_interactive_tty; then
  ensure_term
  "$WHIPTAIL_BIN" --title "$TITLE" --msgbox "Done. Log: $LOGFILE" 10 80 </dev/tty >/dev/tty || true
else
  echo "Done. Log: $LOGFILE"
fi
