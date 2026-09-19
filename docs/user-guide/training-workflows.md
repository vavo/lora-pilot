# Training Workflows

_Last updated: 2026-09-19_

This page is the practical training runbook for LoRA Pilot as it exists now.

## Stack Chooser

| Stack | Best Use | Interface | Notes |
|---|---|---|---|
| TrainPilot | Fastest first run (SDXL-focused flow) | ControlPilot **Guided training** / API | Applies profile defaults and launches Kohya training script |
| Kohya SS | Manual full-control LoRA config | `http://localhost:6666` | Most configurable UI path |
| AI Toolkit | Modern FLUX/SDXL workflows | `http://localhost:8675` | Separate stack with persistent DB/output mapping |
| Diffusion Pipe | Experimental/DeepSpeed path | ControlPilot **Advanced training** + TensorBoard `:4444` | API-driven config generation; single active run in API guard |

## Prerequisites (All Stacks)

Run the commands below directly in a RunPod terminal. From a Docker Compose host, prefix them with `docker exec lora-pilot`.

Save the dataset under `/workspace/datasets/1_*` and confirm that the required model files are present in `/workspace/models`. Inspect the services relevant to your chosen trainer before launching a run:

```bash
supervisorctl status kohya ai-toolkit diffpipe controlpilot
```

Run `nvidia-smi` in the pod to confirm that its GPU is visible. Prepare and review captions in TagPilot, then start with a short training experiment. Compare its outputs in ComfyUI or InvokeAI before changing the dataset or increasing the training budget.

## Workflow A: TrainPilot (Recommended First Pass)

TrainPilot is a guided wrapper over Kohya training in ControlPilot.

### UI Path

Open **Guided training** in ControlPilot, or choose **Train a LoRA** beside a prepared dataset. Check the selected collection and its caption count, give the LoRA a name, then choose **Quick test**, **Balanced**, or **Extended**. These labels map to the API values `quick_test`, `regular`, and `high_quality`.

Review the model-file checks before choosing **Start training**. ControlPilot offers to start missing services and can offer downloads for missing model files that it recognizes in the catalog. Follow progress on the page and expand **Logs & diagnostics** for the trainer's output.

After a successful run, inspect the filenames and choose **Move to LoRA library** when you want ComfyUI to find them in the shared LoRA folder. Resolve any existing-name conflict before retrying. The result survives browser reloads during the same ControlPilot process; restarting the server clears the summary while preserving saved files. The [TrainPilot guide](../components/trainpilot.md) covers profile behavior and configuration in more detail.

### API Path

```bash
curl -s -X POST http://localhost:7878/api/trainpilot/start \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name":"1_my_dataset",
    "output_name":"my_lora_run",
    "profile":"quick_test",
    "toml_path":"/workspace/config/trainpilot/newlora.toml"
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

## Shared TensorBoard

You can view training metrics for all currently supported stacks on the same TensorBoard instance:

- `diffpipe` stack: logs are written to `/workspace/logs/diffusion-pipe` and exposed under `ControlPilot → Services → diffpipe`
- `TrainPilot`: uses `/workspace/logs/TrainPilot` and is available from **Guided training** or `diffpipe` card
- `Kohya SS`: scans `/workspace/outputs` for tensorboard events and is available via `Services` → Kohya
- `AI Toolkit`: scans `/workspace/outputs/ai-toolkit` and is available via `Services` → AI Toolkit

ControlPilot uses a single shared endpoint:

```bash
curl -s http://localhost:7878/api/tensorboard/status
```

If no `events.out.tfevents.*` files exist yet, the UI explains it is waiting for training output so you can still open or diagnose early.

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
nvidia-smi
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

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

