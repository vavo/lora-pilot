# ControlPilot

_Last updated: 2026-09-21_

ControlPilot brings the path from a folder of images to a usable LoRA into one workspace. Start with your dataset, prepare captions, choose a training profile, and bring the result into ComfyUI. Models, service controls, and detailed logs remain close when you need them.

## Find your next step

Open ControlPilot through your pod's exposed port `7878`, or visit `http://localhost:7878` when running locally. In a RunPod terminal, `supervisorctl status controlpilot` reports the service state. A Docker Compose host can run the equivalent command inside its container. RunPod terminals already run inside the pod, so they do not need a nested Docker command.

The Dashboard puts four starting points ahead of the hardware details: prepare a dataset, train a LoRA, generate with ComfyUI, or explore your outputs. Its compact status strip shows the detected GPU, free workspace storage, and service availability. Expand **Hardware details** when you need resource readings, or **Scheduled shutdown** when you want to configure the existing timer.

The sidebar follows the same journey. **Prepare** contains Datasets, Caption images, and Models. **Train** contains Guided training and Advanced training. **Create** opens ComfyUI and the Gallery, while **Manage** holds Services, Storage, and Settings. Docs and Support sit below these groups. The Light and Dark controls remain at the bottom of the menu, including on mobile. The collapsed desktop menu uses sun and moon icons for these choices.

You can minimize the build and activity bar with its close control. An activity icon appears beside Copilot at the bottom right; select it to reopen the bar. This browser remembers your choice across pages and reloads. The icon marks active work and pending completion notices while the bar is minimized.

## Know what is running

When the build and activity bar is expanded, its build label opens **Build & diagnostics**. It shows the image's source commit and build date, detected GPU and memory, and locally installed service versions and states. Choose **Copy diagnostics** when asking for support. The summary deliberately leaves out credentials, URLs, workspace paths, dataset names and logs, so you can explain which build you are testing without copying your environment. Older images and source checkouts without embedded metadata show **unknown**.

The activity control stays with you as you move between pages. Open it to inspect guided training, legacy TrainPilot, managed Diffusion Pipe runs and model downloads. A percentage appears when the job reports progress. Completion and failure notices offer **View task**, which returns to the training run or the Downloads view. The page checks every five seconds while ControlPilot is open; it does not send desktop or email notifications. Work launched independently in another tool is outside this indicator's scope.

If a status source becomes unavailable, its last known jobs remain visible with an explicit warning. A paused training queue is identified separately from running work. Guided run history stays in the workspace, while legacy training and download activity follow their existing service lifetimes.

## Give your images a clear next step

Datasets accepts ZIP archives containing images and optional matching captions. A saved collection shows real image previews, its image count, and how many images have a matching nonempty caption file. Coverage is a useful starting signal; it does not assess whether those captions describe the images well.

When captions are missing, **Review captions** opens the selected collection in Caption images. A fully captioned collection offers **Train a LoRA**, carrying the dataset into Guided training. **Manage** keeps rename and delete actions separate from that next step. You can also create an empty dataset and add images through the existing captioning workspace.

Guided training brings SDXL and FLUX.1 dev into the same setup flow. Choose a dataset, name the LoRA, and select a profile. A persistent queue and history keep the experiment available after a restart, while the result screen lets you move or copy checkpoints into the library and compare their progress against the base model. Read the [TrainPilot guide](../components/trainpilot.md) for the complete workflow.

## Connect model access without losing your place

The Models catalog's **Access settings** action opens Settings directly on **Connections**. Hugging Face credentials remain hidden after saving, and the saved indicator distinguishes a configured token from an empty field. Both **Back to Models** and **Return to Models** return to the selected catalog family. Some gated models also require license acceptance on Hugging Face; saving a token does not grant that approval.

## Manage services and model files

Open **Services** to inspect the tools running in your workspace. Each service exposes the controls supported by that integration, including starting, stopping, restarting, and viewing logs. Follow its application link when you need the tool's own interface. The autostart switch controls whether Supervisor starts that service on boot. Image-managed applications receive their bundled updates through a new image.

In **Models**, browse the Catalog, filter by task or family, and select a row for details. Bundled LTX-2.5 and MiniMax H3 workflows offer **Review installation**, where you can inspect required files, optional components, source access, and available storage before downloading. **Download missing files** reuses installed components and queues the remaining files.

Use **Installed** to inspect paths and remove model files, or **Downloads** to follow progress and retry failures. An installed file still needs a compatible workflow and a successful GPU run before you can judge the result. The [model management guide](model-management.md) covers downloads and existing-file migration.

## Follow a training run through to its files

Choose SDXL or FLUX.1 dev, then select **Quick test**, **Balanced**, or **Extended**. The families use separate Kohya recipes and model requirements. Preflight checks required files and detected GPU conflicts before you add the experiment to the queue.

You can prepare another run while one is training. The queue dispatches one guided run at a time and waits for detected GPU workloads. **Pause queue** holds the next start without interrupting current training. External tools can still compete for memory, so inspect Services when the queue reports a blocker.

**Training queue & history** keeps run status, configuration snapshots, logs, and output locations on your persistent volume. **View run** opens its details, **Use settings** fills a new setup from the saved configuration, and **Repeat run** queues another experiment against the current dataset. A server restart marks formerly running jobs interrupted and pauses pending work for inspection. It does not automatically resume checkpoints or recreate the result of a process it no longer owns.

Search the full history by LoRA or dataset name, filter by model family or status, and move through results with **Previous** and **Next**. Each page shows up to 50 matching runs. Filtering the list leaves the selected run open so you can inspect it while finding another experiment.

The selected run shows elapsed time from launch, including preparation. Startup and cache preparation have their own stage labels. A remaining-time estimate appears only after enough recent trainer progress is available; it disappears when the progress becomes stale. Treat it as an estimate, since checkpoint saves and changing workload conditions can affect the finish time.

A successful run shows saved files and their location. **Download** saves an individual checkpoint to your computer while keeping the workspace copy. **Move to LoRA library** relocates checkpoints under `/workspace/models/loras/ControlPilot/<run-id>`, keeping downloads and comparisons available. **Copy to LoRA library** also preserves the originals. **Try my LoRA** displays a no-LoRA baseline followed by all saved checkpoints in training order, using the same prompt and seed. A single-checkpoint option is available for a smaller comparison. You can also open the prepared graph in ComfyUI without generating immediately.

A failed or stopped run keeps its status and logs rather than showing a success screen. Any saved checkpoints remain in its output directory and can be downloaded after the run stops. Recognized failures offer an explanation and a relevant next action, such as checking Hugging Face access or opening Storage. Expand **Technical details** to inspect the underlying message. For model families or controls outside these guided recipes, open the relevant trainer described in the [training workflows guide](training-workflows.md).

## Keep preparation, generation, and review connected

**Caption images** opens TagPilot for image and caption editing. Use its workspace save action before returning to training, then check the caption coverage in Datasets. A complete caption count tells you that matching nonempty files exist; it cannot tell you whether their descriptions are useful.

**ComfyUI** opens the generation workspace. **Gallery** opens MediaPilot to review saved media. Both use the shared workspace, which lets you prepare a dataset, train an adaptation, and inspect generated results without copying files between containers. For file work outside these views, use the JupyterLab or code-server link in Services.

## Make room for the next experiment

Open **Storage** under Manage to see the space used by models, original datasets, private training snapshots, outputs, and application caches. The free-space reading describes the workspace filesystem. Category totals describe file sizes and exclude symbolic links and duplicate hard links, so they are not a complete breakdown of every byte on the disk. A separately mounted model directory can contribute to the category total without consuming workspace space.

Cleanup starts with your selection. Choose a checkpoint, a finished run's private dataset snapshot, or its training caches, then choose **Review selected cleanup**. The preview shows the selected groups, file count, and estimated reclaimable space. Removing a checkpoint makes it unavailable for download or comparison from that run. **Keep files** closes the preview without removing anything. Removal requires an explicit acknowledgment and cannot be undone here.

ControlPilot rechecks files and workload status before removal. Active or queued training, model downloads, GPU work, and unavailable workload checks block cleanup. A preview expires after five minutes, and changed files require a fresh review. Original datasets, shared models, linked files, and run metadata remain protected. General application caches and outputs from other tools are visible in the overview but are not cleanup candidates; use Models or Gallery for their existing management actions. Empty directories may remain, and filesystem snapshots or other mounts can make actual reclaimed space differ from the estimate.

## Set workspace defaults and access

Settings groups preferences into **General**, **Access & security**, **Connections**, and **Shutdown**. Save General preferences with its save action. The sidebar Light and Dark controls apply the theme when you choose it. Connection settings use their own save controls; leaving a credential field blank keeps the saved value unless you choose Clear.

Access & security contains ControlPilot password protection and optional ComfyUI protection. Review the [security guidance](../configuration/comfy-access.md) before changing access on a public pod. Shutdown preferences set the timer's defaults; configure an actual schedule from the Dashboard's **Scheduled shutdown** section.

## Find help while you work

Open **Docs** to read the bundled guides or changelog inside ControlPilot. **Support** provides the project's support links. If a service fails, inspect its log in Services. If training fails, start with **Logs & diagnostics** and the generated run configuration. Keep the first meaningful error when asking for help, and remove credentials from anything you share.

For automation, use the [API reference](../development/api-reference.md). It documents the dataset, model, service, and training routes, including the result metadata used by these screens. If password protection is enabled, scripts must authenticate with the same ControlPilot session policy as the browser.
