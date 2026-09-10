# Docker Compose

_Last updated: 2026-09-10_

You can keep the shape of your LoRA Pilot installation in a small set of files: the image to run, the ports to expose, and the directory that holds your work. Docker Compose applies that configuration on a Docker host. You can inspect it, reproduce it, and change it without rebuilding the application for each deployment preference.

Run Compose commands on the machine that owns the container. If you already deployed a RunPod pod, its terminal is inside the runtime; use the pod's service controls instead of trying to start another Docker stack there.

## Choose one configuration for the session

The standard `docker-compose.yml` uses the NVIDIA runtime and exposes the main service ports. It also includes a ControlPilot health check. Choose this file for the bundled GPU deployment on a host with the required Docker and NVIDIA setup.

The development file, `docker-compose.dev.yml`, adds mounts for Portal source and selected scripts so you can edit them during development. It retains the GPU runtime and enables interactive terminal settings. The CPU file, `docker-compose.cpu.yml`, omits that runtime and exposes ControlPilot, JupyterLab, and AI Toolkit by default. It provides CPU thread settings for interface and debugging work.

These files are separate deployment configurations. Choose the appropriate file with `-f` and keep using that selection for later commands. Avoid launching another variant against the same writable workspace while an existing container is using it.

## Prepare the image and environment

All three files read `LORA_PILOT_IMAGE`, defaulting to `notrius/lora-pilot:latest`. Set a verified tag or digest in `.env` if you need to return to an exact image. A floating tag can refer to different image content after a later publication. The [build guide](../development/building.md) explains custom images.

Create `.env` from the example if it does not exist, then review the settings before starting the standard stack. These commands run from the repository directory on your Docker host.

```bash
test -f .env || cp .env.example .env
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps
```

The `config --quiet` check validates the Compose configuration without printing its expanded values. A full configuration dump can include secrets from your environment. Docker's [configuration reference](https://docs.docker.com/reference/cli/docker/compose/config/) explains the command and its options.

Compose uses `.env` to substitute variables referenced in the YAML. A value reaches a service process only when the configuration passes it into the container. Keep that distinction in mind if adding a variable appears to have no effect. Docker explains it in the [interpolation guide](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

## Reach the services through their configured ports

The standard and development files expose ControlPilot on `7878`, JupyterLab on `8888`, and VS Code Server on `8443`. ComfyUI uses `5555`, Kohya uses `6666`, and InvokeAI uses `9090`. Port `4444` serves the Diffusion Pipe service's TensorBoard interface, while AI Toolkit uses `8675`.

Each mapping uses the corresponding configured port on both sides. For example, setting `PORTAL_PORT=8787` changes the ControlPilot port passed into the container and its published host port in the bundled file. Apply the updated Compose configuration with `up -d`, then use the new address. A service restart inside the old container does not change its host port mapping.

The CPU file exposes only `7878`, `8888`, and `8675` by default, with the corresponding variable overrides. The Copilot sidecar remains internal. Use the [environment-variable reference](environment-variables.md) for the full setting names and the [ComfyUI access guide](comfy-access.md) if you enable its protected gateway.

## Preserve the workspace when changing the container

The bundled variants mount `./workspace` into `/workspace`. That directory holds models, datasets, outputs, and the settings around your project. Confirm the host path before replacing a container or moving the Compose project to another directory.

You can inspect service state and enter a shell without changing the deployment.

```bash
docker compose -f docker-compose.yml exec lora-pilot supervisorctl status
docker compose -f docker-compose.yml exec lora-pilot bash
```

Use [file structure](../reference/file-structure.md) to identify the application state worth backing up. The [custom setup guide](custom-setup.md) covers separate model or output mounts. Keep a separate backup of irreplaceable work even when the host directory persists.

## Diagnose startup before changing more settings

Read container output with `docker compose -f docker-compose.yml logs --tail=120 lora-pilot`. If the container is running, read the affected service's log from ControlPilot or the terminal. An NVIDIA runtime error belongs to the host setup; a missing model path belongs to the application workflow.

The standard file's health check requests `/api/settings/auth/status` inside the container on the configured ControlPilot port. It does not request `/api/services`, and it does not run a model. A healthy container therefore still needs service-level and workflow-level checks before a training or generation session.

To stop and remove the selected Compose service container, use `docker compose -f docker-compose.yml down` after finishing active work. Treat that as an operational action, rather than part of a routine status check. Continue with [first run](../getting-started/first-run.md) after setup, or use [debugging](../development/debugging.md) if the intended workflow fails.
