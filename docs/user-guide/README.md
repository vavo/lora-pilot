# User Guide

_Last updated: 2026-09-10_

A project can move through several tools before you have an image you want to keep. You might review photographs in TagPilot, train a LoRA with Kohya, and test it in ComfyUI before choosing the strongest results in MediaPilot. In LoRA Pilot, you can do that work against one shared workspace.

Use this guide to choose the next action for your project. You can begin with generation, prepare a training dataset, or return to a saved run without following a fixed sequence through every application.

## Find your way around ControlPilot

[ControlPilot](control-pilot.md) is the starting point for checking the machine and opening services. The dashboard shows resource usage, while **Services** provides process controls and logs. On a local installation, open `http://localhost:7878`. On RunPod, use your pod's connection for that port.

Open a tool through its service link so you reach the address configured for your deployment. The default local ports are `5555` for ComfyUI and `9090` for InvokeAI. Kohya uses `6666`, while JupyterLab and VS Code Server use `8888` and `8443`. A service can still be initializing after ControlPilot opens, so check its state if the link does not load.

## Generate with a model you already have

For a new image session, start with [model management](model-management.md). Choose a model family and confirm the files required by your intended workflow. Some workflows need several components, and a successful download does not establish that the selected engine can use them together.

Continue with [inference](inference.md) to generate a baseline and compare variations. You can use ComfyUI for a reusable graph or InvokeAI for an image session through its interface. Keep the prompt and settings with a useful result so you can return to the same experiment later.

Open [MediaPilot](../components/mediapilot.md) to review supported images from the shared output locations. Comparing several attempts in one place helps you choose what to keep and identify what you want to change next.

## Prepare and train your own adaptation

Use [dataset preparation](dataset-preparation.md) to import a collection and review its captions. You can open the saved dataset in TagPilot, make corrections, and save it back to the workspace. Keep revisions distinct if you want to compare the effects of changing the training examples.

The [training workflows guide](training-workflows.md) explains the available routes through TrainPilot, Kohya SS, AI Toolkit, and Diffusion Pipe. Choose a trainer that supports the base model and adaptation you intend to make. TrainPilot provides a guided SDXL LoRA path through Kohya; the other interfaces offer their own controls and requirements.

After a run, test the adaptation on prompts that represent its intended use. Compare it with the base model as well as with earlier training attempts. That comparison gives you a reason to adjust the dataset or training settings instead of repeating the same run without a clear question.

## Keep the next session connected to this one

Your files belong under `/workspace`, with model assets in `models`, training collections in `datasets`, and results in `outputs`. Settings and logs also have workspace locations. Read the [file-structure guide](../reference/file-structure.md) before moving or backing up a project so you preserve more than its final images.

For a failed service or workflow, begin with [debugging](../development/debugging.md). For a setup change, use [configuration](../configuration/README.md). If the terminology still feels unfamiliar, the [getting-started courses](../getting-started/README.md) explain the ideas behind the tools as you use them.
