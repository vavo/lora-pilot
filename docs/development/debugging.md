# Debugging

_Last updated: 2026-09-10_

You can have a working dashboard, a running generation service, and a failed model load at the same time. LoRA Pilot brings several applications into one workspace, but each application still has its own startup and execution path. The fastest useful diagnosis identifies the point where your intended action stopped working.

Begin with the action you took and the result you expected. “ComfyUI opens, but this workflow fails while loading its VAE” gives you a much narrower search than “generation is broken.” Keep the error text and the time of the attempt so you can match it to the correct log.

## Start from the visible symptom

If you can open ControlPilot, visit **Services** and check the affected tool's state. Read its log before restarting it. A restart can interrupt active work and will not resolve an invalid model path. For a local deployment where ControlPilot itself is unavailable, run `docker compose ps` and `docker compose logs --tail=120 lora-pilot` from the repository directory on the Docker host.

Run the remaining shell examples inside the pod or container. On RunPod, open a Jupyter or SSH terminal for that pod. On a local Docker host, enter the container with `docker compose exec lora-pilot bash`. You do not need to install or run Docker inside the pod to inspect its services.

```bash
supervisorctl status
tail -n 120 /workspace/logs/controlpilot.err.log
```

The supervisor status shows which processes are running. It does not prove that a model can load or that a workflow can finish. Continue with the action that failed once you have confirmed the process state.

## Read the log for the tool doing the work

Service logs live under `/workspace/logs`, with paired `.out.log` and `.err.log` files. For ComfyUI, read `comfy.out.log` and `comfy.err.log`. InvokeAI uses `invoke.out.log` and `invoke.err.log`; Kohya uses `kohya.out.log` and `kohya.err.log`. The same naming pattern applies to `diffpipe`, `jupyter`, `code-server`, `ai-toolkit`, and `copilot`. Supervisor writes its own log to `supervisord.log`.

Start near the time you reproduced the failure. Look for the first meaningful error in that attempt, then read the context around it. A later “process exited” line describes the outcome but may not explain the missing file, package import, or device failure that caused it.

```bash
tail -n 160 /workspace/logs/comfy.out.log
tail -n 160 /workspace/logs/comfy.err.log
```

You can also use ControlPilot's **View logs** action. For API-based inspection, `GET /api/services` returns service states and `GET /api/services/{name}/log?lines=200` returns a recent service log. Use an authenticated session if you have enabled ControlPilot access protection.

## Follow the affected feature

For a Models page that fails to load, check `/api/models`, `/api/models/pulls`, and `/api/models/workflows`. The page needs the catalog, download state, and workflow metadata. A failure in one response can prevent the combined page from loading even if the model files themselves are intact. Use the ControlPilot error log to identify the failed request and file path. The [model management guide](../user-guide/model-management.md) explains the installation flow.

For a failed download, inspect the job status and its error text before retrying. `GET /api/models/{name}/pull/status` returns the status for that model, while `GET /api/models/pulls` lists recent jobs. Distinguish a source-access error from a failed write to the workspace; changing a token will not repair a full disk.

For TrainPilot, use `/api/trainpilot/logs` to inspect the run, and check the model paths before launch through `/api/trainpilot/model-check`. For Diffusion Pipe, the corresponding path validation and log endpoints are `/dpipe/train/validate` and `/dpipe/train/logs`. Validation requests use `POST`; log requests use `GET`. The [API reference](api-reference.md) describes request details.

For an unavailable MediaPilot embed, check `/api/mediapilot/status` and the ControlPilot log. For Copilot, check `/api/copilot/status` and confirm that the optional sidecar is running. You can inspect its `/status` endpoint on port `7879` from inside the container without exposing that internal service to the public network.

## Check the device and the filesystem

Use `nvidia-smi` to confirm system-level GPU visibility. If an error points to CUDA or an installed package, run `/opt/pilot/gpu-smoke-test.sh` while the GPU is free for a test. The script exercises the installed environments; follow it with the actual failing workflow to confirm the repair.

For a missing-file error, inspect the exact path in the message. Models and user data belong under the persistent `/workspace` tree, while bundled code and assets belong under `/opt/pilot`. Confirm that the expected mount exists and that the service can read or write the relevant directory before changing permissions or redownloading files.

Check credential settings without copying their values into bug reports. Bootstrap stores secrets in `/workspace/config/secrets.env`. For an unexpected scheduled RunPod shutdown, inspect `RUNPOD_POD_SHUTDOWN`, `RUNPOD_VOLUME_TYPE`, and `RUNPOD_NETWORK_VOLUME_ID` in the deployment configuration and compare them with the intended storage and shutdown behavior.

## Make one correction and repeat the same action

After correcting a service setting, restart that service when you are ready to interrupt it. For example, `supervisorctl restart comfy` restarts ComfyUI. Check its log, then repeat the workflow that exposed the problem. Keep the input and settings the same so the result tells you whether the correction addressed that failure.

For source-level development, `docker-compose.dev.yml` mounts Portal source and selected runtime scripts into the container. The Portal launcher supports `PORTAL_RELOAD=1`; pass it into the container environment if you want API reloads during local work. A value in your host's `.env` file has an effect only if the Compose configuration forwards it.

A useful bug report includes the image tag or revision you tested, the affected service, the action that failed, and a short redacted log excerpt. State whether you reproduced it after your change. Continue with [architecture](architecture.md) to trace the code path or [performance tuning](../deployment/performance-tuning.md) if the workflow completes but takes longer than expected.
