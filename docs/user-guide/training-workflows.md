# Training workflows

_Last updated: 2026-09-20_

Your first LoRA is an experiment. You choose a model, show it a collection of examples, and inspect what it learned. LoRA Pilot gives you a guided path through that loop and leaves the full training applications available when you need more control.

## Start with a question you can answer

Save your dataset under `/workspace/datasets/1_*`, review its captions, and make sure the required model files are present. In a RunPod terminal, run `nvidia-smi` to check that the GPU is visible. These commands run directly inside the pod. Only an external Docker Compose host needs a `docker exec` prefix.

Choose a short run that can tell you whether the subject or style is being learned. Keep the prompt, seed, and base model consistent when comparing results. Increasing every parameter at once makes the result more expensive and less informative.

## Use guided training for SDXL or FLUX.1 dev

Open **Guided training**, or choose **Train a LoRA** beside a prepared dataset. Select the model family, review the dataset, name the output, and choose Quick test, Balanced, or Extended. SDXL uses your configured checkpoint and VAE. FLUX.1 dev uses a separate Kohya recipe with its full-size diffusion model, autoencoder, CLIP-L, and FP16 T5 encoder.

The preflight checks required files and detects competing GPU work. If a missing file has a catalog entry, ControlPilot offers a download. Choose **Add to training queue** to save the experiment. The queue dispatches one guided run at a time and waits when it detects a managed trainer, NVIDIA compute process, or ComfyUI job. It does not stop other applications for you.

Use Pause queue to hold the next launch, Cancel to remove a waiting run, or Stop to terminate the current managed run. A queue pause leaves current training running. External applications can still create GPU contention after a check, so avoid starting another trainer while a run is active.

Each run keeps its settings and logs in persistent history, with a unique output directory. View run opens its details. Use settings prepares a new experiment from that configuration. Repeat run queues it again against the current dataset. A ControlPilot restart preserves history, marks previously running jobs interrupted, and pauses pending work for inspection.

After success, **Copy to LoRA library** preserves the original checkpoints while making copies available to ComfyUI. **Try my LoRA** generates the same prompt and seed with and without the selected LoRA and shows both images. You can also open the prepared graph in ComfyUI without queueing it. Read the [TrainPilot guide](../components/trainpilot.md) for profile values, storage paths, and recovery behavior.

## Automate the guided queue

The following request saves an SDXL experiment and makes it eligible for dispatch. Replace the dataset and configuration with your actual paths. Use the same authentication policy as ControlPilot when password protection is enabled.

```bash
curl -s -X POST http://localhost:7878/api/training/runs \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name":"1_my_dataset",
    "output_name":"my_lora_run",
    "family":"sdxl",
    "profile":"quick_test",
    "toml_path":"/workspace/config/trainpilot/newlora.toml"
  }'
```

Set `family` to `flux1` for the guided FLUX.1 dev recipe; it does not use the SDXL TOML. Read `/api/training/runs` for queue status and `/api/training/runs/<id>` for a saved run's details. The [API reference](../development/api-reference.md) covers preflight, cancellation, repeat, and comparison requests. Existing `/api/trainpilot/*` integrations remain available, with their earlier process-local behavior.

## Choose Kohya when you need its full controls

The Kohya SS interface on port `6666` exposes settings beyond the guided profiles. Use it when you need a different dataset arrangement or want to control training parameters directly. Keep model, dataset, and output paths under the persistent workspace, and start with a short run before investing in a larger experiment.

Kohya browser jobs are not added to the guided queue. ControlPilot can detect their active GPU processes, but it does not own their configuration, cancellation, or history. Inspect their logs through Services and the output location you selected in Kohya.

## Choose AI Toolkit for its training workflow

AI Toolkit on port `8675` provides its own configuration and job interface. Its bundled source lives under `/opt/pilot/repos/ai-toolkit`, outputs are mapped to `/workspace/outputs/ai-toolkit`, and its database defaults to `/workspace/config/ai-toolkit/aitk_db.db`.

Create and monitor these runs in AI Toolkit. Its database and output mapping provide its own persistence; its jobs are not records in ControlPilot's guided history. Use Services to inspect application logs if its interface cannot start or reconnect.

## Choose Diffusion Pipe for the advanced path

ControlPilot's **Advanced training** page uses the Diffusion Pipe API. This path exposes configuration for a different training stack and requires the relevant transformer, VAE, text-encoder, dataset, and output paths. It is intended for users who need those controls and can inspect the generated configuration.

`POST /dpipe/train/validate` checks a proposed setup. `/dpipe/train/start` launches it, `/dpipe/train/stop` stops the tracked process, and `GET /dpipe/train/logs` reads its recent log output. Start requests now check for competing managed training and detected GPU work. They return a conflict instead of joining the guided queue.

The service on port `4444` supplies shared TensorBoard access and can run without an active Diffusion Pipe training job. Starting TensorBoard does not start a trainer.

## Read the evidence before the next run

Open TensorBoard when you want to inspect recorded metrics. Its shared sources include Diffusion Pipe logs, guided SDXL and FLUX events, and output directories used by Kohya and AI Toolkit. Fresh runs may need time to create event files. `GET /api/tensorboard/status` reports the configured sources and whether events are available.

For guided runs, inspect Logs & diagnostics and Selected run configuration. Full launcher logs remain under `/workspace/config/training/<run-id>/run.log`, and checkpoints live under `/workspace/outputs/<name>-<run-id>`. A failed run can still contain a useful saved checkpoint, but its failure should be understood before another run is queued.

If training cannot start, check the first meaningful error, the required model paths, and the GPU workload. If memory runs out, revisit the profile and trainer settings instead of repeatedly restarting the same experiment. If a queued dataset changed, review it and create a fresh run. If ControlPilot restarted, inspect interrupted processes before repeating them.

A useful iteration changes one thing for a reason. Compare the result, decide what remained weak, and then adjust your dataset or settings. The [dataset preparation guide](dataset-preparation.md), [model management guide](model-management.md), and [LoRA evaluation guide](../getting-started/loRA-training-101/is-my-lora-good.md) connect those decisions to the tools in your workspace.
