# TrainPilot

_Last updated: 2026-10-01_

A useful training experiment should leave you with more than a file named `final_final`. It should tell you what you trained, which settings you used, and what changed in the result. Guided training brings that whole loop into ControlPilot: prepare a run, keep its history, and compare your LoRA with the original model.

## Choose the model you want to teach

Open **Guided training** and choose **SDXL**, **FLUX.1 dev**, **SD 1.5**, **SD 3.5 Medium**, or **SD 3.5 Large**. Each uses a model-specific Kohya recipe. SDXL keeps your saved checkpoint and VAE configuration as the default. FLUX.1 dev uses its diffusion model, autoencoder, CLIP-L encoder, and full FP16 T5 encoder. An inference-oriented quantized model is not a replacement for those training weights.

The **Base model** selector offers compatible checkpoints from the model catalog. SDXL choices include its official base weights, RealVisXL v3–v5, Juggernaut XL v9, Pony Diffusion XL v6, CyberRealistic XL v10, Analog Madness XL and OpenDalle. SD 1.5 choices include its base weights, Realistic Vision v5.1/v6, epiCRealism, Rev Animated and ToonYou. Installed checkpoints are labeled; starting training offers to download missing files. Realistic Vision also requires the separate SD 1.5 MSE VAE. Refiners, distilled Turbo/Lightning variants and quantized inference weights are excluded from these recipes.

Your choice returns with the unfinished draft and stays with the queued run, repeated runs and comparisons. Changing model family resets the selection. Choosing a different base model after **Use settings** returns to the current recipe rather than mixing it with the saved configuration. Leave the selector on its default to preserve existing behavior. This selector is part of the current unreleased source; v2.6 images need an update to include it.

ControlPilot checks the required model paths before adding a run. When missing files match the catalog, it offers to download them. Gated downloads may require a Hugging Face token and access approved on the model's page. A successful file check means the required paths exist; it does not establish that the weights are valid or that a run will fit your GPU.

FLUX uses block swapping to move part of the model between GPU and system memory. This reduces pressure on GPU memory at the cost of transfers and substantial host memory use. Start with a short experiment on your actual hardware. This guided recipe does not claim a universal minimum GPU size.

SD 1.5 uses `sd15-base`, including its text encoder and VAE, at 512-pixel resolution. SD 3.5 Medium and Large use the full-size `sd3.5-medium` or `sd3.5-large` checkpoint, its included VAE, and separate `flux-clip-l`, `sd3-clip-g`, and `flux-t5xxl-fp16` encoders. The CLIP-L and T5 files are shared with FLUX. Download the full-size SD 3.5 checkpoint; the FP8 all-in-one and Turbo variants are separate models.

The new profiles follow the pinned Kohya [SD 1.x training path](https://github.com/kohya-ss/sd-scripts/blob/6721028c79ee85a78b3a06dfd8954dae310a1cce/train_network.py) and [SD3 training implementation](https://github.com/kohya-ss/sd-scripts/blob/6721028c79ee85a78b3a06dfd8954dae310a1cce/sd3_train_network.py). Local checks cover configuration, launch arguments, recovery, and comparison graphs. Completed GPU training and generation runs for these new profiles remain unverified.

## Meet the orange robot

Open **Your first LoRA** in Datasets or Guided training to use the orange robot from the LoRA Pilot videos. Installing the sample copies eight original 1024-pixel images and their reviewed captions into your workspace. Existing datasets are never overwritten. The trigger word is `pilotceramic`.

Open the captions, look at the images, then return to the guide and choose **I reviewed the captions**. **Set up quick training** fills an SDXL Quick test named `OrangeRobot`. The existing model check offers missing downloads before queueing, and you still choose when to start. Progress follows the saved dataset, successful training and completed comparison. Changing the dataset resets its caption-review state.

These are generated sample inputs with variations in the robot's design, not a finished mascot or examples of trained output. Use the comparison to see what your own run learned. A suggested prompt is filled for the sample run; try a new setting as well as a familiar one. GPU training quality remains something to assess on your hardware.

## Begin with a reviewed dataset

**Check quality** in Datasets and **Review dataset** in Guided training open a read-only report. It checks for unreadable images, exact duplicates, images with a short side below 512 pixels, empty or missing captions, orphan captions and symbolic links. Findings link to image previews and the selected image in Caption images. No repair, deletion or caption rewrite happens automatically.

The report opens before a new run is added from the guided setup. Unreadable files and symbolic links must be resolved first. Other findings are advisory. Large scans stop after 5,000 files, 2 GiB of image reads or 45 seconds; individual images above 32 MiB or 40 million pixels are left unchecked. An incomplete scan is labeled explicitly, never presented as a clean result. This review is a frontend handoff; direct API clients remain responsible for their own quality checks.

Choose a saved dataset and inspect its images and caption coverage. The collection should live under `/workspace/datasets` using the `1_` naming convention. A name such as `teapot_sideviews_test` makes your training intent easier to recognize later.

When you add a run, ControlPilot saves its configuration and records the dataset's filenames, sizes, and modification times. Immediately before launching, it checks that the collection still matches. If you edited it while the run was waiting, that run fails with an explanation instead of silently training different inputs. Use its settings to queue a new experiment after reviewing the changes.

At launch, ControlPilot makes a private copy of the dataset inside the run's history directory. This keeps the trainer's staging and cache files away from your source collection. It is not a version-control system for datasets, and edits during the copy should still be avoided.

## Pick up where you left off

Your unfinished dataset choice, model family, profile and LoRA name are saved in this browser as you edit them. Navigate to Models, check another page or refresh, then return to Guided training to resume the setup. **Clear draft** removes the saved choices and resets the form. Adding a run to the queue clears the submitted draft; the run itself remains in persistent history.

Choosing **Train a LoRA** from Datasets deliberately takes precedence over the draft's previous dataset and name. If a saved dataset has disappeared, ControlPilot restores the other choices and asks you to choose a dataset before training. Opening a completed run from an activity notice shows that result without replacing your unfinished choices.

Drafts belong to this browser and site address. They do not follow you to another device or a different pod URL, and clearing browser data removes them. They contain form choices and, when using an earlier run's settings, a reference to that run. Configuration text and credentials are not copied into the draft. If browser storage is blocked, ControlPilot explains that the setup cannot be saved.

## Choose an experiment size

**Quick test**, **Balanced**, and **Extended** map to `quick_test`, `regular`, and `high_quality`. Longer training can help, but it can also teach the model to repeat your examples too closely. Start small enough that you can afford to learn something from the result.

For SDXL, Quick test begins with a 600-step target, a 12-epoch ceiling, rank 32, alpha 16, batch size 1, gradient accumulation of 2, and FP16 precision. Balanced begins at 1,200 steps and 25 epochs, with rank 48, alpha 24, batch size 2, accumulation of 2, and BF16. Extended begins at 2,400 steps and 45 epochs, with rank 64, alpha 32, batch size 4, accumulation of 1, and BF16. The wrapper adjusts these step targets for dataset size and clamps them to its epoch calculation.

For FLUX.1 dev, the three profiles use 600, 1,200, and 2,400 steps, respectively, with ranks 16, 32, and 64. They train the diffusion model's LoRA with batch size 1, BF16 precision, gradient checkpointing, and cached text-encoder outputs. They use a separate recipe rather than applying SDXL parameters to a different model architecture.

SD 1.5 and both SD 3.5 profiles also use 600 / 1,200 / 2,400 steps and ranks 16 / 32 / 64, with batch size 1. SD 1.5 uses FP16 and trains only the U-Net LoRA. SD 3.5 uses BF16, `networks.lora_sd3`, cached text-encoder outputs, and block swapping (16 blocks for Medium, 32 for Large). These are starting profiles; longer runs are not a quality guarantee.

## Let the queue manage the next start

Choose **Add to training queue**. You can prepare another run while one is training. ControlPilot dispatches one guided run at a time and waits for other managed trainers before each launch. ComfyUI and other GPU applications can run alongside training, including while ComfyUI is generating.

GPU workloads and unavailable telemetry appear as advisory messages during preflight; they do not hold the training queue. There is no fixed VRAM cutoff because memory needs depend on your models, batch size, resolution, and training settings. Both workloads share the available memory. If either runs out of memory, reduce its settings or use **Manage GPU services** to stop the other workload. ControlPilot does not automatically stop ComfyUI or unload its models.

**Pause queue** prevents the next launch while allowing the current run to continue. **Cancel** removes a waiting run from dispatch. **Stop** terminates a currently managed run and leaves already saved files in place. These checks coordinate ControlPilot-managed launches; another tool or terminal can still start a process after a check and compete for memory.

## Keep the experiment after the tab closes

**Training queue & history** keeps each run's status, dataset reference, configuration snapshot, logs, and output location under `/workspace/config/training/<run-id>`. Outputs go into `/workspace/outputs/<name>-<run-id>`, so repeating the same name creates a separate experiment.

**View run** opens its details. **Use settings** brings the saved configuration back into the setup form for a new run. **Repeat run** queues another experiment from the saved configuration, using the dataset as it exists now. Neither action resumes a checkpoint automatically.

History survives browser reloads and ControlPilot restarts. After a restart, previously running jobs become **interrupted** and pending work remains paused for inspection. A child training process may still be alive, so check its logs and processes before repeating it. ControlPilot does not pretend it can reconstruct a process's exit result after losing ownership.

The history covers runs created through the new guided queue. Older terminal runs and the legacy `/api/trainpilot/start` API are not imported automatically. Search by LoRA or dataset name, narrow the results by model family or status, and use Previous and Next to browse history in pages of 50. Filters search the full saved history, not just the page on screen. The selected run stays open while you search.

## Understand progress without guessing

The selected run shows elapsed time from launch, including preparation. Its stage distinguishes trainer startup, cache preparation, training, and stopping. An approximate remaining time appears only after the trainer reports at least ten steps and thirty seconds of progress. Stale or missing progress hides the estimate; startup does not receive an invented countdown.

Recognized failures explain the next useful action. A model access error points to Connections, a missing model points to Models, and a full disk points to Storage. GPU memory and dependency errors offer guidance and the relevant workspace page. Technical details stay available for diagnosis; the message is a starting point, not an automatic repair.

## Know which configuration reached the trainer

SDXL starts from `/workspace/config/trainpilot/newlora.toml`. **Advanced configuration** edits those defaults. Each queued run retains its own snapshot, and the wrapper applies the selected profile to a private copy at launch. **Selected run configuration** shows the effective configuration once it is available, including profile overrides.

The SDXL launcher is `/opt/pilot/apps/TrainPilot/trainpilot.sh`. FLUX invokes `sd-scripts/flux_train_network.py`, SD 1.5 invokes `sd-scripts/train_network.py`, and SD 3.5 invokes `sd-scripts/sd3_train_network.py` directly. All use `/opt/venvs/kohya/bin/python` by default; the Kohya browser service does not need to be running to execute these scripts.

**Logs & diagnostics** shows the recent persisted log tail. The full launcher output remains in `/workspace/config/training/<run-id>/run.log`. SDXL also writes `_logs/train.log` inside its output directory. TensorBoard events for all guided families live under `/workspace/logs/TrainPilot`, with a separate directory for each run. The shared TensorBoard service can display them when it is running.

## See what your LoRA changes

A successful run shows the saved checkpoints and their location. **Download** saves an individual checkpoint to your computer. Failed, stopped, cancelled, and interrupted runs also offer any checkpoints they saved. Downloads become available after training stops; they do not remove the workspace copy. **Move to LoRA library** relocates successful checkpoints into `/workspace/models/loras/ControlPilot/<run-id>` after every destination has been verified. Downloads and comparisons remain available from the run. **Copy to LoRA library** keeps the original output files as well. An existing identical copy can be reused; a different file at the destination produces a conflict instead of being overwritten.

In **Try my LoRA**, enter a prompt containing your trigger word. **All checkpoints** creates a grid beginning with the base model without LoRA, followed by each saved epoch or step checkpoint in training order and the final file. Every image uses the same prompt, seed, sampling settings, and dimensions, and each checkpoint is applied independently at the selected strength. The filenames label the images so you can see where training improved the result or went too far. Choose a single checkpoint when you want a smaller, two-image comparison.

The comparison checks the running ComfyUI node registry and available model choices before submission. It uses native nodes for SDXL, FLUX.1 dev, SD 1.5, and SD 3.5 Medium/Large. Start ComfyUI in Services if it is unavailable. Comparisons can generate alongside another training run and share the same GPU memory.

**Open prepared workflow in ComfyUI** loads the same graph into the editor without starting generation. The image includes a small frontend extension for this handoff, and ControlPilot confirms when the workflow has loaded. If loading is not confirmed, it keeps a download link available rather than treating an empty editor as success. **Download workflow** also provides the prepared API-format JSON for manual loading. If a network interruption leaves submission uncertain, inspect ComfyUI before using the explicit reset action; the queue must be empty before resetting that state.

One comparison is a starting point. Try several prompts, views, and environments that matter to your project. A recognizable subject in a familiar composition may still struggle in a new setting. [Is my LoRA good?](../getting-started/loRA-training-101/is-my-lora-good.md) helps turn that observation into your next experiment.

## Keep existing scripts working

The terminal `trainpilot` command and the legacy `/api/trainpilot/*` endpoints remain available for SDXL. Their existing result and file-movement contracts remain separate from the new queue. Terminal queue mode still accepts `TOML:DATASET[:OUTPUT[:PROFILE]]` entries and is not a persistent ControlPilot queue.

New integrations should use `/api/training/runs` and its history, queue, library, and comparison endpoints. The [API reference](../development/api-reference.md) describes the requests. The [training workflows guide](../user-guide/training-workflows.md) explains when to move from guided profiles to a trainer's full interface.

## Recovering a stopped run

Resume queue allows waiting jobs to start. It does not restart a stopped training process. In training history, Resume training restores the latest complete saved training state in a new run, keeping the original outputs and logs. Work after that save must be repeated.

Older runs may have saved only LoRA weights. Continue from checkpoint loads those weights into a new run with a fresh optimizer and learning-rate schedule, then runs the full selected schedule again. The confirmation explains this before queuing. If no recovery point exists, Repeat run starts from the base model. Recovery requires the original dataset to remain unchanged.

New guided runs save optimizer state with their periodic checkpoints, defaulting to a save every 200 steps when no step interval is configured. Recovery states use additional disk space; retention keeps recent step and epoch states. Stopping before the first save still requires starting again. If the queue is paused, the resumed run waits until you choose Resume queue.

## Fit a run to your GPU

Open **GPU & training settings** to see available GPU memory as a bar and adjust batch size, gradient accumulation, LoRA rank and, for FLUX.1, block swapping. Choosing a suggestion fills these fields; it never starts training. Your edits survive navigation and refresh with the unfinished draft. **Use profile defaults** removes the overrides.

ControlPilot records GPU model and capacity, build identity, elapsed time, effective training settings and sampled whole-device peak memory for new managed runs. A successful, non-recovery run on the same GPU, model family, profile and build can supply the suggested memory settings. Whole-device memory includes ComfyUI and other workloads, and sampling can miss brief peaks. Multi-GPU or unavailable telemetry produces no measured recommendation.

When no matching measurement exists, the interface says **Starting suggestion only**. These are editable starting points rather than a published benchmark set. Different datasets, resolutions, models and simultaneous workloads can change the memory needed. ComfyUI remains allowed to run concurrently.

## Take an experiment with you

Open **Export experiment** on a finished or stopped run with a saved checkpoint. Choose one checkpoint, enter its trigger words and a sample prompt, and optionally select comparison images. **Preview package** shows the included files before **Download experiment ZIP** becomes available. Changing the selection requires a new preview; changed source files invalidate the download.

The ZIP contains the checkpoint, a readable readme and an `experiment.json` manifest with model requirements and selected training settings. Chosen comparison images are included with embedded image metadata removed. Dataset files, credentials, logs, local filesystem paths and optimizer state are excluded. Base-model weights are not bundled. The package helps you use the LoRA elsewhere and understand the experiment; resuming its optimizer still requires the original training state.
