# TrainPilot

TrainPilot is the quick-start training automation layer for Kohya in LoRA Pilot. It wraps a curated SDXL training flow around dataset selection, profile presets, and TOML patching.

## 🎯 Overview

TrainPilot provides:
- Fast profile-based LoRA training startup
- Headless launch from ControlPilot (no whiptail dialogs)
- Automatic dataset staging and output folder setup
- Preflight model checks from selected TOML (checkpoint + VAE existence)
- Combined runtime logs (TrainPilot + Kohya `train.log`)

Current implementation runs `sd-scripts/sdxl_train_network.py` and is SDXL-focused.

## 🚀 Access

### Through ControlPilot (recommended)
- Open `TrainPilot` tab in ControlPilot (`http://localhost:7878`)
- Select dataset, output name, profile, then `Start`

### Script path
- `/workspace/apps/TrainPilot/trainpilot.sh`

### Base config file
- `/workspace/apps/TrainPilot/newlora.toml`

## ⚙️ Profiles (Current Defaults)

| Profile | Steps (base) | Max Epochs | Rank/Alpha | Batch | Precision |
|---|---:|---:|---|---:|---|
| `quick_test` | `600` | `12` | `32/16` | `1` (+ grad acc `2`) | `fp16` |
| `regular` | `1200` | `25` | `48/24` | `2` (+ grad acc `2`) | `bf16` |
| `high_quality` | `2400` | `45` | `64/32` | `4` (+ grad acc `1`) | `bf16` |

Additional behavior:
- Large datasets (`>80` images) increase target step count.
- Effective steps are clamped by computed epoch caps.

## 🧪 What Happens on Start

1. **Model preflight**
   - `POST /api/trainpilot/model-check` parses TOML and validates:
   - `pretrained_model_name_or_path`
   - `vae`
   - Missing local files can be mapped to `models.manifest` entries for one-click download.

2. **TOML copy + patch**
   - Source TOML is copied to `/workspace/outputs/<output_name>/<output_name>.toml`.
   - Profile values patch learning rates, rank/alpha, precision, steps, attention flags.

3. **Dataset staging**
   - Dataset is copied into `train_data_dir/<repeats>_<dataset_name>`.
   - Training uses staged data path from the patched TOML.

4. **Training launch**
   - Runs:
   - `/opt/venvs/core/bin/python -u sd-scripts/sdxl_train_network.py --config ... --sdpa`
   - Logs stream to:
   - `/workspace/outputs/<output_name>/_logs/train.log`

## 🖥️ ControlPilot API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/trainpilot/start` | `POST` | Start headless TrainPilot run |
| `/api/trainpilot/stop` | `POST` | Stop running process |
| `/api/trainpilot/model-check` | `POST` | Validate TOML model paths |
| `/api/trainpilot/logs` | `GET` | Combined TrainPilot + Kohya logs |
| `/api/trainpilot/toml` | `GET` | Current base TOML content |

## 🧵 Script Modes

### A) Interactive mode (whiptail)
```bash
cd /workspace/apps/TrainPilot
bash trainpilot.sh
```

### B) Headless mode (used by ControlPilot)
```bash
cd /workspace/apps/TrainPilot
NO_CONFIRM=1 DATASET_NAME=my_dataset OUTPUT_NAME=my_lora PROFILE=regular TOML=/workspace/apps/TrainPilot/newlora.toml bash trainpilot.sh
```

### C) Queue mode
```bash
cd /workspace/apps/TrainPilot
bash trainpilot.sh --queue \
  "/workspace/apps/TrainPilot/newlora.toml:my_dataset:run_a:quick_test" \
  "/workspace/apps/TrainPilot/newlora.toml:my_dataset:run_b:regular"
```

Queue item format:
- `TOML:DATASET[:OUTPUT[:PROFILE]]`

## 📌 Required Inputs

Minimum requirements:
- A dataset directory under `/workspace/datasets/1_*`
- Valid TOML file with local paths for:
  - `pretrained_model_name_or_path`
  - `vae`

If those model files are missing, ControlPilot can offer manifest-based download before start.

## 🛠️ Troubleshooting

### TrainPilot fails immediately
- Check executable/script presence:
```bash
ls -l /workspace/apps/TrainPilot/trainpilot.sh
```
- Validate TOML exists:
```bash
ls -l /workspace/apps/TrainPilot/newlora.toml
```

### No datasets listed
- Ensure dataset folders follow `1_*` convention in `/workspace/datasets`.
- Check datasets API:
```bash
curl -s http://localhost:7878/api/datasets
```

### Logs are empty or confusing
- Read raw training log directly:
```bash
tail -n 200 /workspace/outputs/<output_name>/_logs/train.log
```

### Process hangs or OOM
- Start with `quick_test`.
- Lower batch and/or rank in TOML.
- Verify CUDA/GPU availability in container.

## Related

- [Kohya SS](kohya-ss.md)
- [Training Workflows](../user-guide/training-workflows.md)
- [LoRA Training 101](../getting-started/loRA-training-101/README.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
