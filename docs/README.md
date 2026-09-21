# LoRA Pilot documentation

_Last updated: 2026-09-21_

Start with a folder of images and a result you want to create. LoRA Pilot brings dataset preparation, training, and generation into a shared workspace, so you can follow an experiment through to its saved checkpoints and comparison images. These guides explain the choices along the way and show where to look when a tool needs attention.

## Start your first experiment

Use the [installation guide](getting-started/installation.md) and [system requirements](getting-started/system-requirements.md) to prepare your machine or pod, then follow [First Run](getting-started/first-run.md). Open [ControlPilot](user-guide/control-pilot.md) to prepare a dataset, choose a guided training profile, or open a tool you already know. The [installation troubleshooting guide](getting-started/troubleshooting.md) covers problems that appear before you reach the workspace.

If the terminology is new, begin with [Stable Diffusion 101](getting-started/stable-diffusion-101/README.md). Continue through [Datasets 101](getting-started/datasets-101/README.md), [LoRA Training 101](getting-started/loRA-training-101/README.md), and [Inference 101](getting-started/inference-101/README.md) as those topics become relevant to your project. You can learn the underlying concepts while working toward an image you want to make.

## Prepare, train, and inspect the result

The [dataset preparation guide](user-guide/dataset-preparation.md) covers image collections and captions. [TagPilot](components/tagpilot.md) provides the captioning workspace, and [model management](user-guide/model-management.md) explains how to get the weights your chosen task requires.

[TrainPilot](components/trainpilot.md) takes you through guided SDXL or FLUX.1 dev training, persistent history, checkpoint downloads, and a comparison with the base model. Search previous runs by LoRA or dataset name and inspect the configuration that reached the trainer. For more control, use the [training workflows guide](user-guide/training-workflows.md) with the dedicated guides for [Kohya SS](components/kohya-ss.md), [AI Toolkit](components/ai-toolkit.md), and [Diffusion Pipe](components/diffusion-pipe.md).

The [inference guide](user-guide/inference.md) connects saved models to generation. Learn [ComfyUI](components/comfyui.md) when you want to build or inspect a graph, or explore [InvokeAI](components/invokeai.md) for its generation workspace. The [workflow types guide](getting-started/inference-101/workflow-types.md) explains where image editing, video, and refinement fit. [MediaPilot](components/mediapilot.md) helps you review saved outputs in the Gallery.

## Keep the workspace understandable

[ControlPilot](user-guide/control-pilot.md) covers build diagnostics, global activity, unfinished training drafts, service controls, and Settings. Its Storage page shows category usage and offers reviewed cleanup of eligible files from finished guided runs. Read the cleanup explanation before removing checkpoints you may still want to download or compare.

Models, datasets, settings, and outputs use the persistent workspace. Image-owned application code follows the container image. The [file structure reference](reference/file-structure.md) explains that boundary; persistence depends on retaining the workspace volume. For a failure, start with [troubleshooting](reference/troubleshooting.md) or the [debugging guide](development/debugging.md). The [Copilot Sidecar guide](components/copilot-sidecar.md) describes the optional assistant integration.

## Configure and deploy

Use [environment variables](configuration/environment-variables.md) and [Docker Compose](configuration/docker-compose.md) to understand runtime settings. The [models manifest](configuration/models-manifest.md) defines catalog entries, while [Supervisor](configuration/supervisor.md) manages service processes. [Custom setup](configuration/custom-setup.md) covers changes you want to preserve across starts.

For a hosted workspace, consult [cloud platforms](deployment/cloud-platforms.md) and [production deployment](deployment/production.md). [Performance tuning](deployment/performance-tuning.md) helps you investigate resource use. The [Windows installer guide](deployment/windows-installer.md) covers that packaging path separately.

## Build integrations and contribute

Read the [architecture](development/architecture.md) before changing how the tools fit together. [Building](development/building.md) describes image creation, and the [API reference](development/api-reference.md) documents ControlPilot requests, including training history and reviewed storage cleanup. The [CLI reference](reference/cli-commands.md) covers terminal entry points. Follow the [contribution guide](development/contributing.md) for code or documentation changes.

## Follow product development

The [changelog](reference/changelog.md) records completed source changes and published releases. Read the [v2.5.8 release notes](releases/v2.5.8.md) for that version's scope and upgrade context. Current source documentation also describes later unreleased work; check the running build's commit before assuming a mutable Docker tag includes a feature.

The [product roadmap](product/roadmap.md) separates implemented work, delivery verification, and proposed priorities. [Product ideas](product/ideas.md) explores possible additions without promising a release date. The September 21 source batch adds checkpoint downloads, actionable errors, training timing, searchable history, and reviewed storage cleanup. Image publication and live GPU validation for that batch remain separate delivery steps.

Visit the [GitHub repository](https://github.com/vavo/lora-pilot) for source, [Docker Hub](https://hub.docker.com/r/notrius/lora-pilot) for images, and [GitHub Discussions](https://github.com/vavo/lora-pilot/discussions) to discuss workflows. Report a reproducible problem through [Issues](https://github.com/vavo/lora-pilot/issues), including the running build identity and relevant sanitized details.
