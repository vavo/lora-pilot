# TrainPilot

_Last updated: 2026-09-20_

A useful training experiment should leave you with more than a file named `final_final`. It should tell you what you trained, which settings you used, and what changed in the result. Guided training brings that whole loop into ControlPilot: prepare a run, keep its history, and compare your LoRA with the original model.

## Choose the model you want to teach

Open **Guided training** and choose **SDXL** or **FLUX.1 dev**. Both use Kohya, but each has its own training recipe. SDXL uses your saved checkpoint and VAE configuration. FLUX.1 dev uses its diffusion model, autoencoder, CLIP-L encoder, and full FP16 T5 encoder. An inference-oriented quantized model is not a replacement for those training weights.

ControlPilot checks the required model paths before adding a run. When missing files match the catalog, it offers to download them. Gated downloads may require a Hugging Face token and access approved on the model's page. A successful file check means the required paths exist; it does not establish that the weights are valid or that a run will fit your GPU.

FLUX uses block swapping to move part of the model between GPU and system memory. This reduces pressure on GPU memory at the cost of transfers and substantial host memory use. Start with a short experiment on your actual hardware. This guided recipe does not claim a universal minimum GPU size.

## Begin with a reviewed dataset

Choose a saved dataset and inspect its images and caption coverage. The collection should live under `/workspace/datasets` using the `1_` naming convention. A name such as `teapot_sideviews_test` makes your training intent easier to recognize later.

When you add a run, ControlPilot saves its configuration and records the dataset's filenames, sizes, and modification times. Immediately before launching, it checks that the collection still matches. If you edited it while the run was waiting, that run fails with an explanation instead of silently training different inputs. Use its settings to queue a new experiment after reviewing the changes.

At launch, ControlPilot makes a private copy of the dataset inside the run's history directory. This keeps the trainer's staging and cache files away from your source collection. It is not a version-control system for datasets, and edits during the copy should still be avoided.

## Choose an experiment size

**Quick test**, **Balanced**, and **Extended** map to `quick_test`, `regular`, and `high_quality`. Longer training can help, but it can also teach the model to repeat your examples too closely. Start small enough that you can afford to learn something from the result.

For SDXL, Quick test begins with a 600-step target, a 12-epoch ceiling, rank 32, alpha 16, batch size 1, gradient accumulation of 2, and FP16 precision. Balanced begins at 1,200 steps and 25 epochs, with rank 48, alpha 24, batch size 2, accumulation of 2, and BF16. Extended begins at 2,400 steps and 45 epochs, with rank 64, alpha 32, batch size 4, accumulation of 1, and BF16. The wrapper adjusts these step targets for dataset size and clamps them to its epoch calculation.

For FLUX.1 dev, the three profiles use 600, 1,200, and 2,400 steps, respectively, with ranks 16, 32, and 64. They train the diffusion model's LoRA with batch size 1, BF16 precision, gradient checkpointing, and cached text-encoder outputs. They use a separate recipe rather than applying SDXL parameters to a different model architecture.

## Let the queue manage the next start

Choose **Add to training queue**. You can prepare another run while one is training. ControlPilot dispatches one guided run at a time and checks for other managed trainers, NVIDIA compute processes, and running or pending ComfyUI jobs before each launch.

When something owns the GPU, the queue explains what it detected. **Manage GPU services** takes you to the tools you can inspect or stop. ControlPilot does not automatically kill an unrelated workload. An idle application retaining GPU memory can also keep a run waiting. If GPU status cannot be checked, dispatch waits rather than assuming the GPU is free.

**Pause queue** prevents the next launch while allowing the current run to continue. **Cancel** removes a waiting run from dispatch. **Stop** terminates a currently managed run and leaves already saved files in place. These checks coordinate ControlPilot-managed launches; another tool or terminal can still start a process after a check and compete for memory.

## Keep the experiment after the tab closes

**Training queue & history** keeps each run's status, dataset reference, configuration snapshot, logs, and output location under `/workspace/config/training/<run-id>`. Outputs go into `/workspace/outputs/<name>-<run-id>`, so repeating the same name creates a separate experiment.

**View run** opens its details. **Use settings** brings the saved configuration back into the setup form for a new run. **Repeat run** queues another experiment from the saved configuration, using the dataset as it exists now. Neither action resumes a checkpoint automatically.

History survives browser reloads and ControlPilot restarts. After a restart, previously running jobs become **interrupted** and pending work remains paused for inspection. A child training process may still be alive, so check its logs and processes before repeating it. ControlPilot does not pretend it can reconstruct a process's exit result after losing ownership.

The history covers runs created through the new guided queue. Older terminal runs and the legacy `/api/trainpilot/start` API are not imported automatically. The interface displays the latest 100 records, while saved history remains on the workspace volume.

## Know which configuration reached the trainer

SDXL starts from `/workspace/config/trainpilot/newlora.toml`. **Advanced configuration** edits those defaults. Each queued run retains its own snapshot, and the wrapper applies the selected profile to a private copy at launch. **Selected run configuration** shows the effective configuration once it is available, including profile overrides.

The SDXL launcher is `/opt/pilot/apps/TrainPilot/trainpilot.sh`. FLUX invokes Kohya's `sd-scripts/flux_train_network.py` directly. Both use `/opt/venvs/kohya/bin/python` by default; the Kohya browser service does not need to be running to execute these scripts.

**Logs & diagnostics** shows the recent persisted log tail. The full launcher output remains in `/workspace/config/training/<run-id>/run.log`. SDXL also writes `_logs/train.log` inside its output directory. TensorBoard events for both guided families live under `/workspace/logs/TrainPilot`, with a separate directory for each run. The shared TensorBoard service can display them when it is running.

## See what your LoRA changes

A successful run shows the saved checkpoints and their location. **Copy to LoRA library** copies them into `/workspace/models/loras/ControlPilot/<run-id>`, preserving the original output files. An existing identical copy can be reused; a different file at the destination produces a conflict instead of being overwritten.

In **Try my LoRA**, choose a checkpoint and enter a prompt containing your trigger word. **Generate comparison** asks ComfyUI to create two images using the same base model, prompt, seed, sampling settings, and dimensions. One branch uses your LoRA at the selected strength. The two images appear together so you can judge the change directly.

The comparison checks the running ComfyUI node registry and available model choices before submission. It uses native nodes for SDXL and FLUX.1 dev. Start ComfyUI in Services if it is unavailable, and wait for managed training to finish before generating.

**Open prepared workflow in ComfyUI** loads the same graph into the editor without starting generation. The image includes a small frontend extension for this handoff. **Download workflow** also provides the prepared API-format JSON for manual loading. If a network interruption leaves submission uncertain, inspect ComfyUI before using the explicit reset action; the queue must be empty before resetting that state.

One comparison is a starting point. Try several prompts, views, and environments that matter to your project. A recognizable subject in a familiar composition may still struggle in a new setting. [Is my LoRA good?](../getting-started/loRA-training-101/is-my-lora-good.md) helps turn that observation into your next experiment.

## Keep existing scripts working

The terminal `trainpilot` command and the legacy `/api/trainpilot/*` endpoints remain available for SDXL. Their existing result and file-movement contracts remain separate from the new queue. Terminal queue mode still accepts `TOML:DATASET[:OUTPUT[:PROFILE]]` entries and is not a persistent ControlPilot queue.

New integrations should use `/api/training/runs` and its history, queue, library, and comparison endpoints. The [API reference](../development/api-reference.md) describes the requests. The [training workflows guide](../user-guide/training-workflows.md) explains when to move from guided profiles to a trainer's full interface.
