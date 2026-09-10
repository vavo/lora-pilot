# CLI Commands Reference

_Last updated: 2026-09-10_

The terminal gives you another way to work with the same services and files you see in ControlPilot. You can inspect a stopped process, download a named model, or read the error from a training session without navigating between browser views. A few commands cover much of that day-to-day work.

Run these commands inside the LoRA Pilot runtime. On RunPod, use a terminal in the pod. On a separate Docker Compose host, enter the container with `docker compose exec lora-pilot bash`, or prefix a single command with `docker compose exec lora-pilot`.

## Inspect a service before changing it

Use `pilot status` to see the supervised processes. You can narrow the result with service names, such as `pilot status comfy invoke`. Names identify processes rather than page titles: ComfyUI is `comfy`, InvokeAI is `invoke`, and ControlPilot is `controlpilot`.

```bash
pilot status
pilot status comfy invoke
tail -n 120 /workspace/logs/comfy.err.log
```

The other service identifiers include `kohya`, `diffpipe`, `ai-toolkit`, `jupyter`, `code-server`, and the optional `copilot`. Read the relevant log before restarting a failing process. A running status confirms the process state, while a completed generation or training task confirms more of the workflow.

Use `pilot start comfy` to start ComfyUI and `pilot stop comfy` when you intend to stop it. These are separate actions; choose the one you need. With no service argument, `pilot start` and `pilot stop` target all supervised services. Include a name when you intend to affect one tool.

For a restart after correcting a setting, use `supervisorctl restart comfy`. That interrupts the service, so finish or stop active work first. The [Supervisor guide](../configuration/supervisor.md) explains the process configuration and its relationship to saved autostart preferences.

## Distinguish service control from a direct launch

The shortcuts `pilot comfy`, `pilot kohya`, `pilot diffpipe`, `pilot jupyter`, and `pilot code` execute the corresponding launcher scripts in the current terminal. They do not open a web page or ask Supervisor to start the process. Use them for deliberate foreground work when the matching supervised service is stopped; otherwise you can encounter a port conflict or a second process using the same files.

The `pilot urls` command prints local service addresses from the runtime configuration. Its output includes the Jupyter token and the VS Code Server password. Use it in a private terminal and keep the output out of screenshots and support messages. For ordinary navigation, the service links in ControlPilot avoid printing those credentials.

## Download the model named in the catalog

Use `models where` to see the active manifest and model directory, then `models list` to browse the available entry names. Download one entry with `models pull` followed by its manifest name.

```bash
models where
models list
models pull sdxl-base
```

The downloader accepts one catalog name per invocation. A Hugging Face repository ID is not a substitute for that name. Add or edit a manifest entry if you need a source outside the catalog, following the [manifest guide](../configuration/models-manifest.md).

You can override the destination with `models pull sdxl-base --dir custom/sdxl-base`. The `--dir` value is relative to the configured model root, which defaults to `/workspace/models`, and cannot escape that directory. An alternate destination may need manual selection in a consuming tool and does not change the canonical path used by the catalog's installed-state check.

The `models pull-all` command downloads all entries in the active manifest. Review the catalog and available storage before choosing it; it is not a command for downloading only the components of one workflow. For an LTX-2.5 or MiniMax H3 workflow, use **Review installation** in ControlPilot to inspect its requirements and queue missing files. Use `models help` to print the model CLI's supported syntax.

The model CLI provides `list`, `pull`, `pull-all`, `where`, and `help`. For removal, use the controls in ControlPilot's **Installed** view. The [model management guide](../user-guide/model-management.md) explains verification, retries, and existing downloads.

## Start training with an intentional configuration

The `trainpilot` entry point opens the guided terminal flow for the supported Kohya SDXL LoRA path. It prepares the environment and can fetch required tokenizer files before reaching dataset selection. Use it when you intend to configure training. It does not implement a `--help` option, so passing that flag is not a read-only way to inspect its usage.

Read the [TrainPilot guide](../components/trainpilot.md) for profiles and configuration. ControlPilot also provides a guided interface through `/api/trainpilot/*`, while its Diffusion Pipe training endpoints live under `/dpipe/train/*`. The [training workflow guide](../user-guide/training-workflows.md) helps you choose between those paths.

## Run the same checks from the Docker host

On the machine that owns the Compose project, you can issue a command without opening an interactive container shell.

```bash
docker compose exec lora-pilot pilot status
docker compose exec lora-pilot models list
docker compose logs --tail=100 lora-pilot
```

The first two commands execute inside the service container. The last reads its container-level logs from the host. Use the same Compose file selection you used to launch the project. For failures within an individual application, continue with the [debugging guide](../development/debugging.md) and its service-specific log locations.
