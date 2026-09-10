# Components

_Last updated: 2026-09-10_

You can prepare a dataset, train an adaptation, and use it in a generation workflow without moving the project between separate machines. LoRA Pilot packages the tools for those stages and connects them through the workspace. You choose the tool according to the task in front of you.

[ControlPilot](../user-guide/control-pilot.md) brings service controls, model management, and workspace views into the browser. Use it to see which applications are running and open the interface you need. A default installation serves ControlPilot on port `7878`; cloud deployments use the corresponding provider connection.

## Prepare the examples you want to teach

[TagPilot](tagpilot.md) gives you an interface for reviewing images and editing their tags or captions. Open it through ControlPilot or its `/tagpilot/` route, then save the prepared collection under `/workspace/datasets`. Those image-and-text pairs remain accessible to the training tools and to a terminal.

For a concrete starting point, use the [dataset preparation guide](../user-guide/dataset-preparation.md). It explains naming, importing a ZIP, and saving a revision you can inspect before training.

## Choose a training path for the model

[TrainPilot](trainpilot.md) provides a guided SDXL LoRA route through Kohya. You select a dataset and profile in ControlPilot, then use the generated configuration for the run. It suits a project where you want that supported path without assembling the training configuration from scratch.

[Kohya SS](kohya-ss.md), served on port `6666` by default, exposes the upstream training interface. [AI Toolkit](ai-toolkit.md) provides another training stack, with its interface on port `8675`. Choose according to the model family and training method you intend to use, then follow the relevant guide for its inputs and settings.

[Diffusion Pipe](diffusion-pipe.md) provides a training path through ControlPilot and a configurable service launcher. Its default port `4444` serves TensorBoard. With no `DIFFPIPE_CONFIG`, the service starts TensorBoard without launching training. Seeing that service running does not mean a training job has started.

## Generate and compare the results

[ComfyUI](comfyui.md) gives you a graph of nodes for building and reusing generation workflows. Its default port is `5555`. [InvokeAI](invokeai.md) provides an image-generation interface on port `9090`. Both connect to shared model storage, though each still requires compatible assets and its own model setup.

[MediaPilot](mediapilot.md), available through ControlPilot at `/mediapilot/`, helps you review supported generated images, keep favorites, and organize results. ComfyUI writes to `/workspace/outputs/comfy`, while the bundled InvokeAI integration uses `/workspace/outputs/invoke`. You can compare a training experiment's results without moving them into a separate gallery installation.

The [inference guide](../user-guide/inference.md) connects those tools into a generation-and-review session. Use it to establish a baseline before you evaluate a new LoRA or a more elaborate workflow.

## Work with the files behind the interfaces

JupyterLab and VS Code Server provide notebook, terminal, and editing access to the workspace. Their default ports are `8888` and `8443`. These are useful when you need to inspect a configuration or a saved output without leaving the deployment.

The optional [Copilot sidecar](copilot-sidecar.md) connects the installed GitHub Copilot CLI to ControlPilot. It uses internal port `7879` and requires its own service and authentication setup. Open its guide before enabling it; the rest of the creative workflow can run without it.

For shell commands on RunPod, use the pod's terminal. On a Docker Compose host, enter the container with `docker compose exec lora-pilot bash`. From there, `supervisorctl status` shows the managed services, and the [debugging guide](../development/debugging.md) helps you choose the correct log.

Keep `/workspace/models`, `/workspace/datasets`, and `/workspace/outputs` with the settings and application state that belong to the project. The [file-structure guide](../reference/file-structure.md) explains those locations. Return to [configuration](../configuration/README.md) to adjust the deployment or the [user guide](../user-guide/README.md) to choose your next task.
