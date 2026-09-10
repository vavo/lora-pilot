# First Run

_Last updated: 2026-09-10_

Your first session can end with an image you made and a workspace you know how to return to. LoRA Pilot brings model downloads, generation tools, and an output gallery into the same environment. You can begin with a base model, see a result, and come back to training once you have something to compare it with.

The goal for this session is a small, complete creative loop. Open the workspace, choose a model, generate an image, and find the saved file. That gives you a working foundation for the more ambitious projects ahead.

## Open your workspace

If you have already deployed a RunPod instance, open its connection for ControlPilot on port `7878`. The provider's proxy address takes you to your remote workspace. A `localhost` address refers to the computer where you open it, so use the pod's connection link when working in the cloud.

For a local installation with Docker and the NVIDIA runtime configured, run the following from the repository directory. Create `.env` from the example only if you do not already have one; keep any settings you have entered. The [installation guide](installation.md) covers the prerequisites.

```bash
test -f .env || cp .env.example .env
docker compose -f docker-compose.yml up -d
docker compose ps
```

Open [ControlPilot](http://localhost:7878) on the Docker host. You may reach the dashboard while other services are still starting. Open **Services** to check the tool you intend to use, then read its logs if it fails to reach a running state. Optional services can remain stopped until you need them.

## Give your project a lasting home

LoRA Pilot keeps models, datasets, generated files, and settings under `/workspace`. The default Compose configuration connects that directory to `./workspace` on your host. On RunPod, check the storage attached to your pod and confirm what survives stopping or terminating it. A directory name alone does not guarantee persistence.

You can inspect the layout from a Jupyter terminal inside the pod or container. On a local Docker host, enter the container with `docker compose exec lora-pilot bash` first.

```bash
ls -ld /workspace/models /workspace/datasets /workspace/outputs /workspace/config /workspace/logs
```

Keep a separate backup of work you cannot replace. A persistent volume lets you return to a project across sessions; a backup gives you a way to recover from an accidental deletion or a lost volume.

## Check the GPU before a long run

Open the ControlPilot dashboard and look for your GPU and its memory usage. For a direct check, run these commands inside the pod or container.

```bash
nvidia-smi
/opt/venvs/core/bin/python -c "import torch; print(torch.cuda.is_available())"
```

The first command checks whether the system can see the NVIDIA device. The second checks whether the core Python environment can use CUDA. A successful check is a useful starting point, though a particular model still needs enough memory and compatible components. ComfyUI can fall back to CPU mode if CUDA is unavailable, so a running web interface alone does not confirm GPU execution.

The CPU Compose configuration supports interface work and debugging on a host without the NVIDIA runtime. Read the [performance guide](../deployment/performance-tuning.md) before choosing it for generation or training.

## Choose a model you can test

Open **Models** in ControlPilot and select a family. Review the files required for your intended workflow before downloading. Some workflows need a text encoder and a VAE alongside the main model, and some sources require Hugging Face access approval. The [model management guide](../user-guide/model-management.md) explains the review and download flow.

For an SDXL starting point, you can use the terminal inside the pod or container to browse the catalog and download the base checkpoint.

```bash
models list
models pull sdxl-base
```

Downloading a model puts its files in the shared workspace. You still need to select compatible files in your generation tool. The bundled video workflows also require their model downloads; opening a workflow does not make it ready to generate.

## Make an image and find it again

Open ComfyUI or InvokeAI from **Services**. Choose a basic image workflow supported by your installed model and try a concrete prompt such as “a ceramic teapot on a wooden kitchen table, morning window light.” Keep the first run small enough to finish without exhausting GPU memory. You can explore more elaborate scenes after this first result.

ComfyUI writes its outputs under `/workspace/outputs/comfy`. InvokeAI uses `/workspace/outputs/invoke` in the bundled integration. Open MediaPilot to review supported images from these locations, and confirm that you can find the file in the workspace too. You now have a result you can compare against your next attempt.

If a tool asks for a credential, use its existing configuration. Bootstrap stores generated credentials in `/workspace/config/secrets.env`; keep that file private. For a failed launch, use **Services** to read the affected tool's log and follow the [debugging guide](../development/debugging.md).

Continue with the [inference guide](../user-guide/inference.md) to shape your next image. To teach a model a subject or style of your own, begin with [dataset preparation](../user-guide/dataset-preparation.md), then move into [training workflows](../user-guide/training-workflows.md).
