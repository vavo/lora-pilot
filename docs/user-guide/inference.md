# Inference

_Last updated: 2026-09-10_

You can explore a scene through dozens of small decisions: the subject's pose, the light across a face, the space around an object. Inference is the stage where you use a trained model to generate a result from those decisions. You can begin with a written prompt and, with a compatible workflow, add references or guide part of an existing image.

LoRA Pilot brings ComfyUI and InvokeAI into the same workspace. You can choose the interface that suits the task, keep your model files in shared storage, and review supported outputs in MediaPilot. This gives you room to experiment without rebuilding your environment for each approach.

## Choose the way you want to work

Open **Services** in ControlPilot to reach your generation tool. ComfyUI offers a graph of connected nodes, which makes it useful when you want to inspect how a result was made and reuse the same sequence. InvokeAI provides another image-generation interface within the stack. Explore it when you want to work through image variations using its available controls.

On a local installation, the default addresses are `http://localhost:5555` for ComfyUI and `http://localhost:9090` for InvokeAI. On RunPod, use the service links for your pod. If you have enabled ComfyUI access protection, use its protected entry point through ControlPilot as described in the [access guide](../configuration/comfy-access.md).

Choose the workflow according to the change you want to make. A text-to-image workflow starts from a written description. Image-to-image begins with an existing image. Inpainting targets a selected region. Each requires compatible models and components; the [workflow types guide](../getting-started/inference-101/workflow-types.md) explains the differences before you commit to a setup.

## Match the model to the workflow

Open **Models** and review the files your chosen workflow needs. A base model, its text encoder, and a compatible VAE each play a different role in generation. A LoRA adds an adaptation for a compatible base family. Having a file on disk does not establish that a particular node or generation engine can use it.

LoRA Pilot stores shared model assets under `/workspace/models`. ComfyUI points its model directory there, and the InvokeAI launcher connects its model storage to the same root. You still need to complete the chosen engine's model setup and select the appropriate assets. Shared storage reduces file shuffling; compatibility and model registration remain part of the generation setup.

The bundled LTX-2.5 and MiniMax H3 workflows provide video starting points in ComfyUI. Their presence does not include the model weights or prove that a run will fit your GPU. Review the requirements in [model management](model-management.md), then confirm the workflow has the nodes and files it needs before queueing it.

## Build a comparison you can learn from

Try a concrete scene such as “a red bicycle beside a stone wall, overcast afternoon.” Generate a baseline with the selected model's supported settings and save the prompt with the result. Then change one aspect of the scene, perhaps the lighting, and compare the new image with the first.

Keep the seed and other settings fixed where the workflow allows it. That makes the comparison more useful within the same setup, though it does not promise identical results across engines or software versions. If you change the model, resolution, prompt, and sampler together, you will have less evidence about which decision improved the image.

In ComfyUI, inspect the selected model files and the connections leading to the output node. In InvokeAI, check the selected model and generation settings before submitting a variation. The [core generation settings guide](../getting-started/inference-101/core-generation-settings.md) explains the controls so you can adjust them with a purpose.

## Review the image beyond the preview

ComfyUI writes generated files under `/workspace/outputs/comfy`. The bundled InvokeAI integration uses `/workspace/outputs/invoke`. Open MediaPilot to compare supported images, keep favorites, and organize useful results. You can also inspect the files from JupyterLab or VS Code.

Return to your baseline after several variations. You may prefer the composition from an earlier attempt while keeping the lighting from a later one. Recording those choices gives you a concrete direction for the next run. If you use generated images in a future training dataset, review their defects and suitability with the same care you would apply to other source images.

## Resolve the blockage at the right place

If the interface does not open, check the service state and its log in ControlPilot. If the interface opens but a model is missing, check its location and the engine's model setup. If the run fails after loading begins, read the execution error before downloading another copy of the same model.

For a terminal check, run these commands inside the pod or container. On a local Docker host, enter it with `docker compose exec lora-pilot bash` first.

```bash
supervisorctl status comfy invoke
tail -n 120 /workspace/logs/comfy.err.log
tail -n 120 /workspace/logs/invoke.err.log
```

For an out-of-memory error, try a smaller supported resolution or batch and stop other GPU jobs you no longer need. Reducing steps can shorten a run, but it may not solve a memory shortage. The [performance guide](../deployment/performance-tuning.md) helps you separate loading time, generation time, and memory pressure.

Continue with the [ComfyUI guide](../components/comfyui.md) for graph-based work, the [InvokeAI guide](../components/invokeai.md) for its workspace integration, or [Inference 101](../getting-started/inference-101/README.md) for a deeper grounding in generation.
