# Training Workflows

This page is the practical training runbook for LoRA Pilot as it exists now.

## Stack Chooser

| Stack | Best Use | Interface | Notes |
|---|---|---|---|
| TrainPilot | Fastest first run (SDXL-focused flow) | ControlPilot `TrainPilot` tab / API | Applies profile defaults and launches Kohya training script |
| Kohya SS | Manual full-control LoRA config | `http://localhost:6666` | Most configurable UI path |
| AI Toolkit | Modern FLUX/SDXL workflows | `http://localhost:8675` | Separate stack with persistent DB/output mapping |
| Diffusion Pipe | Experimental/DeepSpeed path | ControlPilot `Dpipe` tab + TensorBoard `:4444` | API-driven config generation; single active run in API guard |

## Prerequisites (All Stacks)

1. Dataset exists in `/workspace/datasets/1_*`.
2. Required model files exist in `/workspace/models`.
3. Services are up:

```bash
docker exec lora-pilot supervisorctl status kohya ai-toolkit diffpipe controlpilot
```

4. GPU is visible (if using GPU flow):

```bash
docker exec lora-pilot nvidia-smi
```

## Standard Workflow

1. Prepare dataset in TagPilot.
2. Pull/check required base models.
3. Start with shortest useful run.
4. Evaluate outputs in ComfyUI/InvokeAI.
5. Iterate parameters and rerun.

## Workflow A: TrainPilot (Recommended First Pass)

TrainPilot is a guided wrapper over Kohya training in ControlPilot.

### UI Path

1. Open ControlPilot `TrainPilot`.
2. Pick dataset (`1_*` folder).
3. Set output name.
4. Choose profile:
   - `quick_test`
   - `regular`
   - `high_quality`
5. Start and watch logs.

### API Path

```bash
curl -s -X POST http://localhost:7878/api/trainpilot/start \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name":"1_my_dataset",
    "output_name":"my_lora_run",
    "profile":"quick_test",
    "toml_path":"/opt/pilot/apps/TrainPilot/newlora.toml"
  }'
```

### Useful Endpoints

- `POST /api/trainpilot/model-check` (validate checkpoint + VAE paths in TOML)
- `GET /api/trainpilot/logs`
- `POST /api/trainpilot/stop`
- `GET /api/trainpilot/toml`

### Output Convention

- Output root: `/workspace/outputs/<output_name>`
- Main training log: `/workspace/outputs/<output_name>/_logs/train.log`

## Workflow B: Kohya SS (Manual Control)

Use when you need fine-grained parameter control directly in Kohya UI.

### Quick Steps

1. Open `http://localhost:6666`.
2. Configure dataset/model/output paths under `/workspace`.
3. Start with conservative settings and short step count.
4. Validate generated checkpoints/samples.

### Ops Commands

```bash
docker exec lora-pilot supervisorctl status kohya
docker exec lora-pilot tail -n 200 /workspace/logs/kohya.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/kohya.err.log
```

## Workflow C: AI Toolkit (Modern Stack)

Use for modern workflows where AI Toolkit is preferred.

### Runtime Mapping

- Toolkit source: `/opt/pilot/repos/ai-toolkit`
- Output path mapping: `/workspace/outputs/ai-toolkit`
- DB path default: `/workspace/config/ai-toolkit/aitk_db.db`

### Quick Steps

1. Open `http://localhost:8675`.
2. Build/select config in Toolkit UI.
3. Point dataset/model paths to `/workspace/*`.
4. Run and monitor from Toolkit UI + service logs.

### Ops Commands

```bash
docker exec lora-pilot supervisorctl status ai-toolkit
docker exec lora-pilot tail -n 200 /workspace/logs/ai-toolkit.out.log
docker exec lora-pilot tail -n 200 /workspace/logs/ai-toolkit.err.log
```

## Workflow D: Diffusion Pipe (Experimental)

ControlPilot exposes Dpipe endpoints and UI for this stack.

### API Endpoints

- `POST /dpipe/train/validate`
- `POST /dpipe/train/start`
- `POST /dpipe/train/stop`
- `GET /dpipe/train/logs`

### Important Behavior

- API enforces single active tracked run.
- Service on port `4444` is TensorBoard-oriented and can run TB-only when no config is set.
- Dpipe start requires model paths (`transformer_path`, `vae_path`, `llm_path`, `clip_path`) and dataset/config/output paths.

### Ops Commands

```bash
docker exec lora-pilot supervisorctl status diffpipe
docker exec lora-pilot tail -n 200 /workspace/logs/diffpipe.out.log
```

## Artifacts and Logs by Stack

| Stack | Main Artifacts | Main Logs |
|---|---|---|
| TrainPilot/Kohya | `/workspace/outputs/<run>/` | `/workspace/outputs/<run>/_logs/train.log`, `/workspace/logs/kohya*.log` |
| AI Toolkit | `/workspace/outputs/ai-toolkit` | `/workspace/logs/ai-toolkit*.log` |
| Diffusion Pipe | configurable output path (Dpipe payload) | `/workspace/logs/diffpipe*.log`, `/dpipe/train/logs`, TensorBoard logdir |

## Iteration Pattern That Works

1. Run `quick_test`/short pass first.
2. Check whether trigger/subject/style is learned at all.
3. Increase duration/quality only if first pass is directionally correct.
4. Keep run names explicit (`subjectA_qt1`, `subjectA_reg2`, ...).

## Failure Playbook

### Start fails before training begins

- Validate service state and logs:

```bash
docker exec lora-pilot supervisorctl status controlpilot kohya ai-toolkit diffpipe
docker exec lora-pilot tail -n 200 /workspace/logs/controlpilot.err.log
```

### Missing model files

- Pull from Models UI or CLI:

```bash
docker exec lora-pilot models list
docker exec lora-pilot models pull <model_name>
```

### Run hangs or OOM

- Reduce batch size / rank / resolution.
- Stop run and retry short profile first.
- Verify GPU memory pressure:

```bash
docker exec lora-pilot nvidia-smi
```

### Logs look empty

- For TrainPilot, use `/api/trainpilot/logs` and direct file tail in output `_logs`.
- For Dpipe, use `/dpipe/train/logs` and `diffpipe` service logs.

## Related

- [Dataset Preparation](dataset-preparation.md)
- [Model Management](model-management.md)
- [TrainPilot](../components/trainpilot.md)
- [Kohya SS](../components/kohya-ss.md)
- [AI Toolkit](../components/ai-toolkit.md)
- [Diffusion Pipe](../components/diffusion-pipe.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
