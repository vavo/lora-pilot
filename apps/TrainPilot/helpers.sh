#!/usr/bin/env bash
# helpers.sh — env, UI, dataset, TOML wrappers, math, presets
set -euo pipefail

die(){ echo "ERR: $*" >&2; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1" >&2; exit 1; }; }

prepare_env() {
  export ACCELERATE_CONFIG_FILE=${ACCELERATE_CONFIG_FILE:-/workspace/home/root/.cache/huggingface/accelerate/default_config.yaml}
  export HF_HOME=${HF_HOME:-/workspace/home/root/.cache/huggingface}
  export TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE:-/workspace/home/root/.cache/huggingface}
  export TOKENIZERS_PARALLELISM=${TOKENIZERS_PARALLELISM:-false}
  export TERM=${TERM:-xterm-256color}
  export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore::FutureWarning,ignore::DeprecationWarning}"

  DATASET_ROOT="${DATASET_ROOT:-/workspace/datasets}"
  IMAGES_DIR="${IMAGES_DIR:-$DATASET_ROOT/images}"
  TOML="${TOML:-/workspace/apps/TrainPilot/newlora.toml}"
  OUTS_BASE="${OUTS_BASE:-/workspace/outputs}"
  KOHYA_ROOT="${KOHYA_ROOT:-/opt/pilot/repos/kohya_ss}"

  CLEAR_TRAIN_PARENT="${CLEAR_TRAIN_PARENT:-1}"
  SECONDS_PER_STEP="${SECONDS_PER_STEP:-0.55}"
  MAX_REPEATS_CAP="${MAX_REPEATS_CAP:-6}"

  mkdir -p "$OUTS_BASE" "$IMAGES_DIR" "$(dirname "$ACCELERATE_CONFIG_FILE")" "$HF_HOME"

  PYTHON_BIN="${PYTHON_BIN:-/opt/venvs/core/bin/python}"
  require "$PYTHON_BIN"
}

# ---------- UI ----------
require_whiptail() { command -v whiptail >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq whiptail >/dev/null; }; }

center_pad() {
  local t="${1-}" w="${2-80}" l p
  l=${#t}; p=$(( (w - l) / 2 )); (( p < 0 )) && p=0
  printf "%*s%s" "$p" "" "$t"
}

# Generic menu with Next/Quit
pick_menu(){
  local title="$1"; shift
  local prompt="$1"; shift
  whiptail --title "$title" --ok-button "Next" --cancel-button "Quit" \
           --menu "$prompt" 20 80 12 "$@" 3>&1 1>&2 2>&3
}

# Profile picker as a menu (NOT radio list) with Next/Back
pick_profile_menu(){
  whiptail --title "Training Profile" --ok-button "Next" --cancel-button "Back" \
           --menu "Choose a profile (highlight + Next):" 16 76 6 \
           "quick_test"   "400–600 steps (sanity check)" \
           "regular"      "800–1200 steps (daily driver)" \
           "high_quality" "1800–2400 steps (fidelity)" \
           3>&1 1>&2 2>&3
}

input_box(){ whiptail --title "$1" --ok-button "Next" --cancel-button "Back" --inputbox "$2" 10 80 "${3-}" 3>&1 1>&2 2>&3; }
confirm_box(){ whiptail --title "$1" --yes-button "Start" --no-button "Back" --yesno "$2" 28 94; }
info_box(){ whiptail --title "$1" --ok-button "Continue" --msgbox "$2" 12 76; }

# ---------- Files / datasets ----------
unixify_file(){ sed -i 's/\r$//' "$1"; tail -c1 "$1" | grep -q $'\n' || echo >> "$1"; }

list_datasets(){
  find "$DATASET_ROOT" -maxdepth 1 -mindepth 1 -type d -name '1_*' | sort | while read -r d; do
    base="$(basename "$d")"; name="${base#1_}"
    cnt=$(find "$d" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) | wc -l | awk '{print $1}')
    printf "%s\t%s\t%s\n" "$name" "$cnt" "$d"
  done
}

index_of_name(){ local needle="$1"; shift; local i=0; for n in "$@"; do [[ "$n" == "$needle" ]] && { echo "$i"; return 0; }; ((i++)); done; return 1; }

count_images(){ find "$1" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) | wc -l | awk '{print $1}'; }

# ---------- TOML helpers (via toml_edit.py) ----------
# NOTE: use python3 and resolve relative to this file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

toml_set() {  # toml_set <file> <dotted.key> <str|raw> <value>
  "$PYTHON_BIN" "$SCRIPT_DIR/toml_edit.py" set "$1" "$2" "$3" "$4"
}
toml_del() {  # toml_del <file> <dotted.key>
  "$PYTHON_BIN" "$SCRIPT_DIR/toml_edit.py" del "$1" "$2"
}
toml_get() {  # toml_get <file> <dotted.key>
  "$PYTHON_BIN" "$SCRIPT_DIR/toml_edit.py" get "$1" "$2"
}

# Back-compat shims for your current train.sh
toml_get_str_grep(){ local f="$1" k="$2"; toml_get "$f" "$k"; }
toml_get_int_grep(){ # toml_get_int_grep <file> <key> <default>
  local f="$1" k="$2" def="${3:-0}" v
  v="$(toml_get "$f" "$k" | tr -d '[:space:]')" || true
  if [[ "$v" =~ ^-?[0-9]+$ ]]; then echo "$v"; else echo "$def"; fi
}
toml_get_str(){ toml_get_str_grep "$@"; }
toml_get_int(){ toml_get_int_grep "$@"; }

compute_repeats(){
  local profile="$1" img_cnt="$2" tier
  tier="$(size_tier "$img_cnt")"
  base="$(base_repeats "$profile" "$tier")"
  # cap by MAX_REPEATS_CAP
  (( base > MAX_REPEATS_CAP )) && base="$MAX_REPEATS_CAP"
  echo "$base"
}


# ---------- Math & presets ----------
size_tier(){
  local n="$1" t="SMALL"
  (( n <= 30 )) && t="TINY"
  (( n >= 61 )) && t="MEDIUM"
  (( n >= 151 )) && t="LARGE"
  (( n >= 301 )) && t="XL"
  echo "$t"
}

epoch_caps(){ # imgs repeats batch ga max_epochs -> echo steps_per_epoch updates_per_epoch epoch_cap_steps
  local imgs="$1" reps="$2" batch="$3" ga="$4" max_epochs="$5"
  local spe=$(( (imgs * reps + batch - 1) / batch ))
  local upe=$(( (spe + ga - 1) / ga ))
  (( upe < 1 )) && upe=1
  echo "$spe" "$upe" $(( max_epochs * upe ))
}

base_repeats(){
  local profile="$1" tier="$2"
  case "$profile" in
    quick_test) echo 1 ;;
    regular)
      case "$tier" in TINY) echo 4;; SMALL) echo 2;; *) echo 1;; esac ;;
    high_quality)
      case "$tier" in TINY) echo 8;; SMALL) echo 6;; MEDIUM) echo 3;; *) echo 1;; esac ;;
    *) echo 1 ;;
  esac
}

profile_presets(){ # sets globals for chosen profile & tier
  local profile="$1" tier="$2"
  case "$profile" in
    quick_test)
      UNET_LR="0.00008"; TE_LR="0"; TE_ON=false; TE_STOP=0
      MIXED_PREC="fp16"; N_OFF="0.02"; LR_FLOOR="0.2"
      case "$tier" in
        TINY)   DIM=16; ALPHA=8;;
        SMALL)  DIM=32; ALPHA=16;;
        MEDIUM) DIM=32; ALPHA=16;;
        LARGE|XL) DIM=64; ALPHA=32;;
      esac
      SPI=20; MIN_STEPS=400; MAX_STEPS=600; MAX_EPOCHS=10   # display cap only; STEPS mode enforced by train.sh
      GA=1
      ;;
    regular)
      UNET_LR="0.00005"; TE_LR="0.000005"; TE_ON=true
      if [[ "$tier" == "TINY" ]]; then TE_STOP=1; else TE_STOP=2; fi
      MIXED_PREC="bf16"; N_OFF="0.015"; LR_FLOOR="0.15"
      case "$tier" in
        TINY)   DIM=32; ALPHA=16;;
        SMALL)  DIM=32; ALPHA=16;;
        MEDIUM) DIM=48; ALPHA=24;;
        LARGE|XL) DIM=64; ALPHA=32;;
      esac
      SPI=20; MIN_STEPS=800; MAX_STEPS=1200; MAX_EPOCHS=20
      ;;
    high_quality)
      UNET_LR="0.000045"; TE_LR="0.000005"; TE_ON=true
      if [[ "$tier" == "XL" ]]; then TE_STOP=3; else TE_STOP=2; fi
      MIXED_PREC="bf16"; N_OFF="0.01"; LR_FLOOR="0.1"
      case "$tier" in
        TINY)   DIM=32; ALPHA=16;;
        SMALL)  DIM=48; ALPHA=24;;
        MEDIUM) DIM=64; ALPHA=32;;
        LARGE|XL) DIM=64; ALPHA=32;;
      esac
      SPI=34; MIN_STEPS=1600; MAX_STEPS=2400; MAX_EPOCHS=30
      ;;
    *) die "Unknown profile: $profile" ;;
  esac
}

write_accelerate_cfg(){
  local path="$1"
  cat > "$path" <<'YAML'
compute_environment: "LOCAL_MACHINE"
distributed_type: "NO"
mixed_precision: "no"
use_cpu: false
debug: false
num_processes: 1
machine_rank: 0
num_machines: 1
gpu_ids: "0"
rdzv_backend: "static"
same_network: false
main_training_function: "main"
downcast_bf16: false
dynamo_config:
  dynamo_backend: "no"
YAML
}
