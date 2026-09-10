# Troubleshooting (Reference)

_Last updated: 2026-09-10_

A useful error gives you a place to investigate. A missing dataset, a stopped process, and a failed source download may appear in the same interface, but they need different corrections. Start with the symptom below that matches the action you attempted, then verify the same action after making a change.

For a broader method of following logs and runtime state, read the [debugging guide](../development/debugging.md). The shell examples here run inside the pod or container. On a Docker Compose host, enter it with `docker compose exec lora-pilot bash` first.

## The terminal says Docker is missing

A RunPod terminal is already inside the LoRA Pilot runtime. You can use `supervisorctl`, `models`, and the service logs there without a Docker client. Remove the Docker host wrapper from examples intended for a separate Compose host.

```bash
supervisorctl status
models list
tail -n 120 /workspace/logs/controlpilot.err.log
```

These commands inspect the existing runtime. They do not require starting a second container. The [CLI reference](cli-commands.md) explains the distinction between host commands, service controls, and direct launchers.

## ControlPilot does not open

Check `supervisorctl status controlpilot` and read `/workspace/logs/controlpilot.err.log`. Confirm the configured `PORTAL_PORT` and the port exposed by your provider or Compose configuration. A browser on your laptop needs the remote service address for a cloud pod, rather than the pod's `localhost` URL.

If you can reach the interface but service state looks stale, compare it with `supervisorctl status` inside the same container. Refresh the browser and inspect ControlPilot's log for a failed status request. A service can be running while its own workflow is still failing, so continue to the application log after confirming its process state.

## Models fails to load or a download fails

A Models page that reports an internal server error needs an API or log diagnosis before another download. The catalog view combines model entries, recent jobs, and workflow metadata. Read the [model management guide](../user-guide/model-management.md) for the packaged workflow-path failure and the workaround for that specific case.

For a failed pull, inspect its error in **Downloads**, then use `models where` to confirm the active catalog. Check free space with `df -h /workspace/models`. A source-access failure and an incomplete local file are different conditions; retry after addressing the condition shown in the job output.

If the active manifest contains a stale source, compare that entry with the source you intend to use. Save your customized catalog before editing it or upgrading an older workspace. The [manifest guide](../configuration/models-manifest.md) explains the one-time migration refresh and how later customizations are tracked.

## A dataset is missing or will not import

ControlPilot lists dataset folders under `/workspace/datasets` with the `1_` prefix. Creating a dataset through the interface applies that convention. If you placed files there by hand, check the folder name and location before importing another copy.

ZIP imports reject absolute paths, parent-directory traversal, and symbolic links. Rebuild a rejected archive from ordinary files with relative paths. A malformed archive, an upload limit, or insufficient disk space can also prevent import, so read the returned error rather than assuming the naming convention is the cause.

TagPilot saves the loaded collection in sequence through `/api/tagpilot/save-item`. Its first request resets the destination, and the final request creates a ZIP snapshot. If saving stops partway through, inspect the resulting dataset before training on it. Preserve your source files, reload the complete intended collection, and wait for the save completion message. The [dataset guide](../user-guide/dataset-preparation.md) explains that flow.

## Copilot is unavailable or a request does not finish

The optional `copilot` service has autostart disabled in the bundled setup. Check its state and the local status endpoint before sending another task.

```bash
supervisorctl status copilot
curl -s http://127.0.0.1:7879/status
```

If the sidecar is reachable but the CLI is missing or authentication fails, correct that setup first. A timeout is a failed request, even if partial output appears. Read the returned status and `/workspace/logs/copilot.err.log`. The [Copilot guide](../components/copilot-sidecar.md) explains its execution permissions and response fields.

## A documentation link returns an error

The `/api/docs/file` endpoint accepts safe relative Markdown paths, such as `user-guide/model-management.md`. It rejects absolute paths, `..` segments, colons in path segments, and non-Markdown file suffixes. Use the documentation navigation or correct the relative path instead of passing a host filesystem path into the endpoint.

If you edited a workspace document but still see older text, check which documentation root ControlPilot uses. It prefers `/opt/pilot/docs` when available unless `DOCS_ROOT` overrides that choice. The workspace copy at `/workspace/docs` is a fallback. The [file-structure guide](file-structure.md) explains both locations.

## MediaPilot remains on its loader

Check `/api/mediapilot/status` and read the ControlPilot output and error logs for embed or application-loading failures. If the problem started after an update, confirm the image revision running in the container and refresh the browser's cached page. A successful source push alone does not replace the running application.

If MediaPilot opens but an image is missing, check the saved file and the configured output directory. ComfyUI and InvokeAI use different output locations in the bundled setup. Follow the [MediaPilot guide](../components/mediapilot.md) to inspect those settings before moving or regenerating the image.

## Record the correction you verified

After correcting a path, setting, or source entry, repeat the original action with the same inputs. Keep the service name, image reference, and relevant redacted error if you need further help. Use [getting-started troubleshooting](../getting-started/troubleshooting.md) for installation problems and the [API reference](../development/api-reference.md) when you need request details.
