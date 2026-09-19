# ControlPilot

_Last updated: 2026-09-20_

ControlPilot brings the path from a folder of images to a usable LoRA into one workspace. Start with your dataset, prepare captions, choose a training profile, and bring the result into ComfyUI. Models, service controls, and detailed logs remain close when you need them.

## Find your next step

Open ControlPilot through your pod's exposed port `7878`, or visit `http://localhost:7878` when running locally. In a RunPod terminal, `supervisorctl status controlpilot` reports the service state. A Docker Compose host can run the equivalent command inside its container. RunPod terminals already run inside the pod, so they do not need a nested Docker command.

The Dashboard puts four starting points ahead of the hardware details: prepare a dataset, train a LoRA, generate with ComfyUI, or explore your outputs. Its compact status strip shows the detected GPU, free workspace storage, and service availability. Expand **Hardware details** when you need resource readings, or **Scheduled shutdown** when you want to configure the existing timer.

The sidebar follows the same journey. **Prepare** contains Datasets, Caption images, and Models. **Train** contains Guided training and Advanced training. **Create** opens ComfyUI and the Gallery, while **Manage** holds Services and Settings. Docs and Support sit below these groups. The Light and Dark controls remain at the bottom of the menu, including on mobile.

## Give your images a clear next step

Datasets accepts ZIP archives containing images and optional matching captions. A saved collection shows real image previews, its image count, and how many images have a matching nonempty caption file. Coverage is a useful starting signal; it does not assess whether those captions describe the images well.

When captions are missing, **Review captions** opens the selected collection in Caption images. A fully captioned collection offers **Train a LoRA**, carrying the dataset into Guided training. **Manage** keeps rename and delete actions separate from that next step. You can also create an empty dataset and add images through the existing captioning workspace.

Guided training brings SDXL and FLUX.1 dev into the same setup flow. Choose a dataset, name the LoRA, and select a profile. A persistent queue and history keep the experiment available after a restart, while the result screen lets you copy checkpoints into the library and compare the LoRA against its base model. Read the [TrainPilot guide](../components/trainpilot.md) for the complete workflow.

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

A successful run shows saved files and their location. **Copy to LoRA library** makes copies under `/workspace/models/loras/ControlPilot/<run-id>` while preserving the originals. **Try my LoRA** sends a native-node workflow to ComfyUI and displays images generated with the same prompt and seed, with and without the chosen LoRA. You can also open the prepared graph in ComfyUI without generating immediately.

A failed or stopped run keeps its status and logs rather than showing a success screen. Any saved checkpoints remain in its output directory. For model families or controls outside these guided recipes, open the relevant trainer described in the [training workflows guide](training-workflows.md).

## Keep preparation, generation, and review connected

**Caption images** opens TagPilot for image and caption editing. Use its workspace save action before returning to training, then check the caption coverage in Datasets. A complete caption count tells you that matching nonempty files exist; it cannot tell you whether their descriptions are useful.

**ComfyUI** opens the generation workspace. **Gallery** opens MediaPilot to review saved media. Both use the shared workspace, which lets you prepare a dataset, train an adaptation, and inspect generated results without copying files between containers. For file work outside these views, use the JupyterLab or code-server link in Services.

## Set workspace defaults and access

Settings groups preferences into **General**, **Access & security**, **Connections**, and **Shutdown**. Save General preferences with its save action. The sidebar Light and Dark controls apply the theme when you choose it. Connection settings use their own save controls; leaving a credential field blank keeps the saved value unless you choose Clear.

Access & security contains ControlPilot password protection and optional ComfyUI protection. Review the [security guidance](../configuration/comfy-access.md) before changing access on a public pod. Shutdown preferences set the timer's defaults; configure an actual schedule from the Dashboard's **Scheduled shutdown** section.

## Find help while you work

Open **Docs** to read the bundled guides or changelog inside ControlPilot. **Support** provides the project's support links. If a service fails, inspect its log in Services. If training fails, start with **Logs & diagnostics** and the generated run configuration. Keep the first meaningful error when asking for help, and remove credentials from anything you share.

For automation, use the [API reference](../development/api-reference.md). It documents the dataset, model, service, and training routes, including the result metadata used by these screens. If password protection is enabled, scripts must authenticate with the same ControlPilot session policy as the browser.
