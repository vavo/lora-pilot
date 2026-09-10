# InvokeAI

_Last updated: 2026-09-10_

A useful image session often begins with one scene and a series of variations. You keep the subject, change the light, reconsider the framing, and compare the results. InvokeAI gives you an image-generation environment for that work inside LoRA Pilot, alongside ComfyUI and the training tools you may use later.

The integration connects InvokeAI to your persistent workspace and gives you service controls in ControlPilot. You can move from a generation session to reviewing its saved images without moving the project into another container.

## Open a session from ControlPilot

Open **Services** and select **Invoke AI**. The default local address is `http://localhost:9090`; on RunPod, use the connection link for your pod. If you changed the service port, follow the configured address. Check the service state before opening the interface, especially after the first boot or an update.

Choose an image model supported by the installed InvokeAI version and complete its model setup before generating. Downloading files through ControlPilot is one part of that preparation. The shared directory does not guarantee that InvokeAI has registered a model or supports the architecture you downloaded.

Start with a scene you can describe and assess, such as a product photograph of a ceramic cup on linen. Keep a baseline image and its settings, then compare a variation with a different light direction. You can make a more informed choice when you know which setting or prompt detail changed between attempts.

## Keep the project in the shared workspace

InvokeAI's application root is `/workspace/apps/invoke`. LoRA Pilot's launcher creates that root and connects model storage to `/workspace/models`. It also configures the output location as `/workspace/outputs/invoke`, with filesystem links for the default model and output directories where needed.

You can inspect generated files from JupyterLab or VS Code, and MediaPilot uses the Invoke output location in the bundled setup. This makes it possible to compare images from both generation tools in the same gallery. If an image appears in InvokeAI but not in MediaPilot, confirm its saved location before assuming generation failed.

The workspace holds your application state as well as the image files. Keep `/workspace/apps/invoke` with the rest of your project backup, and confirm that your deployment preserves `/workspace` across the lifecycle you intend to use. Copying a few favorite PNGs preserves the artwork; backing up the workspace also preserves the surrounding setup.

## Understand the separate runtime

InvokeAI runs in `/opt/venvs/invoke`, its own Python environment. The image installs its dependencies separately from the core environment used by ComfyUI. You can share project files while each application retains the packages it needs.

For troubleshooting, inspect InvokeAI through that environment rather than installing packages into the core environment and expecting InvokeAI to change. The [CUDA compatibility guide](../development/cuda-compatibility.md) records the image's dependency choices. Follow the [build guide](../development/building.md) if you need to change those choices in a custom image.

ControlPilot supports updates for the InvokeAI service. Treat an update as a change to your working setup: preserve the workspace, finish active generation, and test a familiar image after the update. A running service confirms startup; a completed test image confirms more of the path you depend on.

## Use the service controls with context

You can check status and read logs from ControlPilot. For terminal access, run the following inside the pod or container. On a local Docker host, enter the container with `docker compose exec lora-pilot bash` first.

```bash
supervisorctl status invoke
tail -n 120 /workspace/logs/invoke.out.log
tail -n 120 /workspace/logs/invoke.err.log
```

Read the error before restarting. A missing model, an import failure, and a GPU memory error need different responses. If you have corrected a startup setting and are ready to interrupt the service, run `supervisorctl restart invoke`, then check its log and open the interface again.

The launcher reads `INVOKE_PORT`, which defaults to `9090`, and uses it as the default for `INVOKEAI_PORT`. It reads `INVOKEAI_HOST` for the bind address and `WORKSPACE_ROOT` for the shared filesystem root. The bundled Compose configuration passes `INVOKE_PORT` through to the container and maps that port on the host. See [environment variables](../configuration/environment-variables.md) before changing the deployment configuration.

## Find a missing model or image

If a downloaded model is absent from the interface, verify that its files exist under `/workspace/models` and that the architecture is supported by your installed InvokeAI version. Then check the model setup within InvokeAI. A filesystem link alone cannot establish that a model is ready to select.

If MediaPilot cannot find an image you have saved, compare its Invoke output setting with the actual file location. The default `MEDIAPILOT_INVOKEAI_DIR` is `/workspace/outputs/invoke` in LoRA Pilot's bootstrap configuration. You can inspect that one setting without printing the rest of the environment file.

```bash
grep '^MEDIAPILOT_INVOKEAI_DIR=' /workspace/apps/MediaPilot/.env
```

Use the [inference guide](../user-guide/inference.md) to plan a controlled generation session and the [MediaPilot guide](mediapilot.md) to organize its results. For service failures, continue with [debugging](../development/debugging.md).
