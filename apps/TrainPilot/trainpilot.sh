#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

NO_CONFIRM="${NO_CONFIRM:-0}"
PROFILE="${PROFILE:-}"
DATASET_NAME="${DATASET_NAME:-}"
OUTPUT_NAME="${OUTPUT_NAME:-}"

: "${NO_CONFIRM:=0}"
: "${PROFILE:=}"
: "${DATASET_NAME:=}"
: "${OUTPUT_NAME:=}"

# Headless defaults: if caller set NO_CONFIRM=1 we avoid whiptail and require inputs
if [[ "${NO_CONFIRM}" == "1" ]]; then
  [[ -n "${DATASET_NAME}" ]] || die "DATASET_NAME required when NO_CONFIRM=1"
  [[ -n "${PROFILE}" ]] || PROFILE="regular"
  [[ -n "${OUTPUT_NAME}" ]] || OUTPUT_NAME="${DATASET_NAME}"
fi

# ------------------------------------------------------
# QUEUE MODE
# ------------------------------------------------------
if [[ "${1:-}" == "--queue" ]]; then
  shift
  (( $# > 0 )) || { echo "Usage: $0 --queue \"TOML:DATASET[:OUTPUT[:PROFILE]]\"" >&2; exit 1; }
  idx=1
  for item in "$@"; do
    IFS=: read -r _toml _ds _out _prof <<<"$item"
    [[ -n "$_toml" && -n "$_ds" ]] || { echo "Queue item #$idx malformed: '$item'"; exit 1; }
    PROFILE="${_prof:-${PROFILE:-regular}}" \
    DATASET_NAME="$_ds" \
    OUTPUT_NAME="${_out:-$_ds}" \
    TOML="$_toml" \
    NO_CONFIRM=1 \
    bash "$0"
    ((idx++))
  done
  echo "=== Queue complete ==="
  exit 0
fi

if [[ "${NO_CONFIRM}" != "1" ]]; then
  require_whiptail
fi
prepare_env

# In headless mode, avoid any whiptail calls (fail fast if they slip through).
if [[ "${NO_CONFIRM}" == "1" ]]; then
  info_box(){ echo "INFO: $1 - $2"; }
  pick_menu(){ die "pick_menu called in headless mode"; }
  pick_profile_menu(){ die "pick_profile_menu called in headless mode"; }
  input_box(){ die "input_box called in headless mode"; }
  confirm_box(){ return 0; }
fi

# ------------------------------------------------------
# DATASET DISCOVERY
# ------------------------------------------------------
mapfile -t DATASETS < <(list_datasets)
((${#DATASETS[@]})) || die "No datasets found."

MENU_ITEMS=()
NAMES=(); COUNTS=(); PATHS=()

for line in "${DATASETS[@]}"; do
  name="${line%%$'\t'*}"
  rest="${line#*$'\t'}"
  cnt="${rest%%$'\t'*}"
  path="${rest#*$'\t'}"
  NAMES+=("$name")
  COUNTS+=("$cnt")
  PATHS+=("$path")
done

for i in "${!NAMES[@]}"; do
  tag=$((i+1))
  MENU_ITEMS+=("$tag" "$(center_pad "${NAMES[$i]} (${COUNTS[$i]} imgs)" 68)")
done

STEP="dataset"
CHOSEN_IDX=""

# If running headless (NO_CONFIRM=1) and dataset provided, preselect it (accept absolute path too)
if [[ "${NO_CONFIRM}" == "1" && -n "${DATASET_NAME}" ]]; then
  ds_path="${DATASET_NAME}"
  if [[ ! -d "${ds_path}" ]]; then
    ds_path="/workspace/datasets/${DATASET_NAME}"
  fi
  if [[ ! -d "${ds_path}" ]]; then
    ds_path="/workspace/datasets/1_${DATASET_NAME}"
  fi
  if [[ ! -d "${ds_path}" ]]; then
    die "Dataset path not found: ${DATASET_NAME}"
  fi
  base_name="$(basename "${ds_path}")"
  if [[ "${base_name}" == 1_* ]]; then
    DATASET_NAME="${base_name#1_}"
  else
    DATASET_NAME="${base_name}"
  fi
  CHOSEN_IDX=0
  NAMES=("${DATASET_NAME}")
  COUNTS=($(count_images "${ds_path}"))
  PATHS=("${ds_path}")
  IMG_CNT="${COUNTS[0]:-0}"
  STEP="profile"
fi

# ------------------------------------------------------
# STATE MACHINE
# ------------------------------------------------------
while :; do
  case "$STEP" in

    dataset)
      if [[ -n "${DATASET_NAME:-}" ]]; then
        CHOSEN_IDX="$(index_of_name "$DATASET_NAME" "${NAMES[@]}")" || die "Unknown dataset"
      else
        CHOICE=$(pick_menu "Select Dataset" "Choose dataset" "${MENU_ITEMS[@]}") || exit 0
        CHOSEN_IDX=$((CHOICE-1))
        DATASET_NAME="${NAMES[$CHOSEN_IDX]}"
      fi
      IMG_CNT="${COUNTS[$CHOSEN_IDX]}"
      STEP="profile"
      ;;

    profile)
      if [[ -z "$PROFILE" ]]; then
        CHOICE=$(pick_profile_menu) || { STEP="dataset"; continue; }
        PROFILE="$CHOICE"
      fi
      STEP="output"
      ;;

    output)
      def_out="${OUTPUT_NAME:-$DATASET_NAME}"
      if [[ "${NO_CONFIRM}" == "1" ]]; then
        OUTPUT_NAME="${OUTPUT_NAME:-$def_out}"
        echo "Headless: output name set to '${OUTPUT_NAME}'"
        STEP="summary"
        continue
      fi
      OUTPUT_NAME=$(input_box "Output Name" "Set output name" "$def_out") || { STEP="profile"; continue; }
      [[ -n "${OUTPUT_NAME// /}" ]] || { info_box "Invalid" "Empty name."; continue; }
      STEP="summary"
      ;;

    summary)
      OUT_DIR="$OUTS_BASE/$OUTPUT_NAME"
      mkdir -p "$OUT_DIR/_logs"

      [[ -f "$TOML" ]] || die "TOML not found."
      COPIED_TOML="$OUT_DIR/${OUTPUT_NAME}.toml"
      cp "$TOML" "$COPIED_TOML"
      unixify_file "$COPIED_TOML"

      SRC_PATH="${PATHS[$CHOSEN_IDX]}"
      SRC_IMAGES="$(count_images "$SRC_PATH" || echo 0)"
      if (( SRC_IMAGES == 0 )) && [[ -d "$SRC_PATH/images" ]]; then
        SRC_PATH="$SRC_PATH/images"
        SRC_IMAGES="$(count_images "$SRC_PATH" || echo 0)"
      fi
      if (( SRC_IMAGES == 0 )); then
        best_dir=""
        best_count=0
        while IFS= read -r d; do
          c="$(count_images "$d" || echo 0)"
          if (( c > best_count )); then
            best_count="$c"
            best_dir="$d"
          fi
        done < <(find "${PATHS[$CHOSEN_IDX]}" -maxdepth 3 -type d)
        if (( best_count > 0 )); then
          SRC_PATH="$best_dir"
          SRC_IMAGES="$best_count"
          echo "Headless: using nested dataset dir '${SRC_PATH}' (${SRC_IMAGES} images)"
        fi
      fi
      IMG_CNT="${SRC_IMAGES}"

      # --------------------------------------------------
      # PROFILE PARAMS
      # --------------------------------------------------
      case "$PROFILE" in
        quick_test)
          train_steps=600
          net_dim=32; net_alpha=16
          conv_dim=32; conv_alpha=16
          dropout=0.05
          batch=1; ga=2
          tok=200
          lr=0.00025; lr_te=0.00002
          precision="fp16"
          ;;
        regular)
          train_steps=1200
          net_dim=48; net_alpha=24
          conv_dim=48; conv_alpha=24
          dropout=0.05
          batch=2; ga=2
          tok=225
          lr=0.00025; lr_te=0.00003
          precision="bf16"
          ;;
        high_quality)
          train_steps=2400
          net_dim=64; net_alpha=32
          conv_dim=64; conv_alpha=32
          dropout=0.05
          batch=4; ga=1
          tok=225
          lr=0.00025; lr_te=0.00003
          precision="bf16"
          ;;
      esac

      # Big datasets extend training
      if (( IMG_CNT > 80 )); then
        train_steps=$((train_steps + train_steps / 3))
      fi

      # --------------------------------------------------
      # WRITE TOML OVERRIDES
      # --------------------------------------------------
      toml_set "$COPIED_TOML" "network_dim"  "raw" "$net_dim"
      toml_set "$COPIED_TOML" "network_alpha" "raw" "$net_alpha"
      toml_set "$COPIED_TOML" "network_dropout" "raw" "$dropout"
      toml_set "$COPIED_TOML" "conv_dim"  "raw" "$conv_dim"
      toml_set "$COPIED_TOML" "conv_alpha" "raw" "$conv_alpha"

      toml_set "$COPIED_TOML" "train_batch_size" "raw" "$batch"
      toml_set "$COPIED_TOML" "gradient_accumulation_steps" "raw" "$ga"
      toml_set "$COPIED_TOML" "max_token_length" "raw" "$tok"

      toml_set "$COPIED_TOML" "learning_rate" "raw" "$lr"
      toml_set "$COPIED_TOML" "learning_rate_te" "raw" "$lr_te"
      toml_set "$COPIED_TOML" "learning_rate_te1" "raw" "$lr_te"
      toml_set "$COPIED_TOML" "learning_rate_te2" "raw" "$lr_te"

      toml_set "$COPIED_TOML" "max_train_steps" "raw" "$train_steps"

      # precision override
      if [[ "$precision" == "bf16" ]]; then
        toml_set "$COPIED_TOML" "mixed_precision" "str" "bf16"
        toml_set "$COPIED_TOML" "full_bf16" "raw" "true"
      else
        toml_set "$COPIED_TOML" "mixed_precision" "str" "fp16"
        toml_set "$COPIED_TOML" "full_bf16" "raw" "false"
      fi

      # Force PyTorch SDPA (no xformers / no mem-eff)
      toml_set "$COPIED_TOML" "xformers" "raw" "false"
      toml_set "$COPIED_TOML" "mem_eff_attn" "raw" "false"
      toml_set "$COPIED_TOML" "sdpa" "raw" "true"

      # --------------------------------------------------
      # DATA PREP
      # --------------------------------------------------
      TRAIN_DIR="$(toml_get_str "$COPIED_TOML" "train_data_dir")"
      TRAIN_DIR="${TRAIN_DIR%/}"
      [[ -z "$TRAIN_DIR" ]] && TRAIN_DIR="/workspace/datasets/images"

      REPEATS_USED="$(compute_repeats "$PROFILE" "$IMG_CNT")"
      TARGET="$TRAIN_DIR/${REPEATS_USED}_${DATASET_NAME}"
      echo "Headless: SRC_PATH='${SRC_PATH}' TRAIN_DIR='${TRAIN_DIR}' TARGET='${TARGET}'"

      if [[ "${NO_CONFIRM}" == "1" ]]; then
        echo "Preparing Images: Cleaning + copying dataset."
      else
        info_box "Preparing Images" "Cleaning + copying dataset."
      fi

      if (( IMG_CNT == 0 )); then
        echo "ERROR: No images found in dataset source: ${SRC_PATH}" >&2
        exit 1
      fi

      mkdir -p "$TRAIN_DIR"
      if [[ "$SRC_PATH" != "$TRAIN_DIR"* ]]; then
        find "$TRAIN_DIR" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
      else
        echo "Headless: source lives under train dir; skipping cleanup"
      fi
      mkdir -p "$TARGET"
      cp -a "${SRC_PATH}/." "$TARGET/"

      # --------------------------------------------------
      # RUN TRAINING
      # --------------------------------------------------
      CMD=("$PYTHON_BIN" -u sd-scripts/sdxl_train_network.py
           --config "$COPIED_TOML"
           --output_dir "$OUT_DIR"
           --output_name "$OUTPUT_NAME"
           --train_data_dir "$TRAIN_DIR"
           --sdpa)

      if ! grep -Eq '^[[:space:]]*resolution' "$COPIED_TOML"; then
        CMD+=(--resolution "1024,1024")
      fi

      clear || true
      echo "=== Starting Kohya SDXL LoRA ==="
      echo "Log file: $OUT_DIR/_logs/train.log"
      echo

      (cd "$KOHYA_ROOT" && stdbuf -oL -eL "${CMD[@]}" 2>&1 |
        tee -a "$OUT_DIR/_logs/train.log")
      status=$?

      echo "=== Training finished (exit $status) ==="
      (( NO_CONFIRM == 0 )) && {
        if (( status == 0 )); then info_box "Done" "Training completed."
        else info_box "Failed" "Training failed: $status."
        fi
      }
      exit "$status"
      ;;
  esac
done
