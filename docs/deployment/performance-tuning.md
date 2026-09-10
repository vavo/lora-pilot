# Performance Tuning

_Last updated: 2026-09-10_

A shorter generation loop gives you more chances to improve an image. You can test a lighting change, compare a composition, and try again while the idea is still clear. To shorten that loop, begin by finding the part of the run that takes the time.

A model download, a model load, and a generation use different resources. Faster storage can help a slow load, while a GPU-bound generation needs a different adjustment. LoRA Pilot gives you service controls and telemetry to distinguish those situations before you change the configuration.

## Measure one repeatable task

Choose a workflow that completes on your current setup. Record its model, resolution, batch size, and generation settings, then note the elapsed time. Separate the first run after loading a model from later runs with the same model. That keeps setup work from obscuring the cost of generation itself.

Use the ControlPilot dashboard to watch GPU memory, GPU utilization, and system memory during the run. You can read the current NVIDIA state with `nvidia-smi` inside the pod or container. On a Docker host, `docker stats lora-pilot` provides a container-level view; substitute your configured container name if it differs from the default.

Change one variable and repeat the same task. Keep the result as well as the timing. A faster setting is useful only if the output still meets the needs of your project.

## Confirm which environment can use the GPU

A visible GPU in the dashboard is one piece of evidence. Your generation or training tool must also load compatible packages and execute work on the device. Run the bundled smoke check inside the pod or container while the GPU is available for testing.

```bash
/opt/pilot/gpu-smoke-test.sh
```

The script checks installed service environments, validates package dependencies, and exercises CUDA operations, including a small 3D convolution and an attention operation. It fails if CUDA is unavailable. Passing it gives you evidence about those operations; you still need to run your chosen workflow to establish its memory requirements and behavior.

ComfyUI can switch to CPU mode when CUDA is unavailable. If its interface opens but generation takes much longer than expected, inspect the service log for the selected mode. InvokeAI has a separate Python environment, so a successful core-environment check does not settle an InvokeAI runtime problem.

## Leave room for the active job

You may have several tools open while preparing a project. Check for active training and generation jobs before starting another demanding run on the same GPU. Stop work you no longer need through the relevant interface, then compare the memory usage and run time again.

For a memory failure, begin with a smaller supported resolution or batch. A video workflow also depends on its frame count and temporal settings. Keep changes within the model's supported range. Reducing sampling steps can shorten computation, but it does not guarantee a lower peak memory requirement.

Use [core generation settings](../getting-started/inference-101/core-generation-settings.md) to understand image controls and [training parameters](../getting-started/loRA-training-101/training-parameters-explained.md) for training adjustments. Record a working configuration before trying a larger one so you have a known starting point to return to.

## Separate storage delays from computation

LoRA Pilot connects tools to `/workspace/models` and keeps generated files under `/workspace/outputs`. This shared layout helps you organize large assets without maintaining a separate collection for each application, though individual engines may still require their own model setup or derived files.

Watch the stage at which progress pauses. If the delay occurs while downloading, investigate the source connection. If it occurs while reading a model from disk, inspect the workspace storage. If it occurs during sampling with a busy GPU, a different storage mount may have little effect on that part of the run.

Keep enough free space for outputs and caches as well as model weights. The [custom setup guide](../configuration/custom-setup.md) explains separate mounts if you need to place models and outputs on different storage. Preserve the workspace paths that the tools expect when changing the underlying disks.

## Tune the controls that match your workload

For Diffusion Pipe's service launcher, `DIFFPIPE_NUM_GPUS` sets the number of GPUs passed to DeepSpeed, and `DIFFPIPE_EXTRA_ARGS` supplies additional launch arguments. These controls apply to that launch path; they do not turn an unrelated inference workflow into a multi-GPU workload. Without `DIFFPIPE_CONFIG`, the service runs TensorBoard rather than starting a training job.

The launcher defaults `NCCL_P2P_DISABLE` and `NCCL_IB_DISABLE` to `1`. Retain the working defaults until you have a specific reason to test communication changes on your hardware. The [Diffusion Pipe guide](../components/diffusion-pipe.md) explains the service and the ControlPilot training path.

For large workspaces, ControlPilot's disk-usage scans have their own controls. `WORKSPACE_DU_CACHE_SECONDS` and `WORKSPACE_DU_TIMEOUT_SECONDS` govern caching and scan timeouts. The `TELEMETRY_HISTORY_SAMPLE_SECONDS`, `TELEMETRY_HISTORY_MAX_SECONDS`, and `TELEMETRY_HISTORY_COMPACT_SECONDS` settings control history sampling and retention. These affect monitoring behavior, rather than the model's generation algorithm.

## Use CPU mode for the work it can support

The CPU Compose configuration omits the NVIDIA runtime and exposes ControlPilot, JupyterLab, and AI Toolkit by default. It sets `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to `4` unless you override them. This provides a starting point for interface work and debugging without a GPU; it does not make GPU training workloads practical on a CPU.

You can launch that configuration from the repository directory with `docker compose -f docker-compose.cpu.yml up -d`. Choose it as a deployment mode, rather than starting it alongside a GPU container that is writing to the same workspace.

Read [environment variables](../configuration/environment-variables.md) for the configuration reference. If your baseline task still fails, use the [debugging guide](../development/debugging.md) to identify the failing service before changing more settings.
