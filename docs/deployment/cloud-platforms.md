# Cloud Platforms

_Last updated: 2026-09-10_

You can work on a laptop while a remote GPU handles the training or generation. LoRA Pilot packages the creative tools into the container you deploy there, and you reach their interfaces through the browser. The practical task is to keep the compute session connected to storage you can return to.

The repository provides a RunPod template link and Docker Compose configurations for a prepared host. For another cloud provider, the Compose path gives you the application deployment; you still configure that provider's machine, storage, and network access.

## Start with the deployment you intend to keep

The project links to a [RunPod template](https://console.runpod.io/deploy?template=gg1utaykxa&ref=o3idfm0n) as its primary cloud starting point. Review the selected image and storage in the provider console before deploying. A template is a starting configuration, and a tag name alone does not confirm which source changes an image contains.

The image starts through `/opt/pilot/start.sh`, loads persisted settings during bootstrap, and launches Supervisor. Open the pod's ControlPilot connection on port `7878` by default, then use **Services** to reach individual applications. You may see the dashboard while another service is still initializing.

Inside the pod's Jupyter or SSH terminal, run `supervisorctl status` to inspect the managed services. That terminal is already inside LoRA Pilot. Docker Compose commands belong on a separate Docker host, rather than inside the pod.

## Make storage an explicit part of the project

LoRA Pilot writes project data and settings under `/workspace`. Confirm which provider storage backs that mount. On RunPod, container disk is temporary, volume disk remains with the pod until deletion, and network volumes have a lifecycle independent of a particular pod. Read the current [RunPod storage documentation](https://docs.runpod.io/pods/storage/types) before choosing a stop or termination action.

Keep models, datasets, and outputs together with the application state you need for the next session. The [file-structure guide](../reference/file-structure.md) identifies those paths. An attached persistent volume does not replace a backup of work you cannot recreate.

For a test of your setup, save a small project file under `/workspace`, confirm its location on the intended mount, and inspect the provider's retention rules. Do this before accumulating a large dataset or a long training run. You need evidence about the actual mount, not merely a directory called `workspace`.

## Understand the scheduled shutdown action

ControlPilot can schedule a shutdown, but the action depends on configuration. On RunPod, the runtime first reads the saved `shutdown_mode` from ControlPilot settings. If none is set, it uses `RUNPOD_POD_SHUTDOWN`. Values such as `remove`, `terminate`, or `delete` select removal; `stop` or `halt` select stopping the pod.

Without an explicit mode, the runtime uses `RUNPOD_VOLUME_TYPE` and `RUNPOD_NETWORK_VOLUME_ID` to select the action. A network-volume indicator selects removal, a local-storage indicator selects stop, and the remaining default is stop. Confirm those inputs against the actual deployment before scheduling the action.

If the RunPod command is missing or fails, ControlPilot reports failure. It does not fall back to a host shutdown after a failed RunPod command. The local `shutdown -h now` path applies when the runtime has no RunPod pod ID. A status of `requested` means the command returned successfully; verify the final pod state in the provider console before treating the session as stopped.

## Use a Docker host on another provider

On a cloud VM with Docker and the NVIDIA runtime configured, clone the repository and use the [Docker Compose guide](../configuration/docker-compose.md). Set the image and environment for that deployment, and mount durable storage at the host path used for `./workspace` before starting the stack.

The repository does not supply a ready-to-deploy Helm chart or Terraform module. If your platform requires those tools, build the deployment around the runtime's existing persistence and service requirements, then validate it as a separate integration. Avoid assuming that a generic architecture example establishes a tested provider deployment.

Use the configured service links or a protected connection to reach the interfaces. Set the access policy for each exposed application; a ControlPilot password alone does not secure an independent service port. The [ComfyUI access guide](../configuration/comfy-access.md) explains its optional gateway protection.

## Verify a small session before a long job

Open ControlPilot and inspect the services, then confirm GPU visibility inside the runtime with `nvidia-smi`. Download the files for a small supported workflow, complete a generation, and locate its output under `/workspace/outputs`. The [first-run guide](../getting-started/first-run.md) walks through this session.

Keep the image reference and the successful workflow settings with your project notes. After an image replacement, repeat that familiar task before launching a long training run. Use [performance tuning](performance-tuning.md) for a slow workflow and [debugging](../development/debugging.md) for one that fails.
