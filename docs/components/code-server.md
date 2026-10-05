# VS Code Server (optional)

VS Code Server is not included in the default Docker image. JupyterLab remains available for notebooks and terminals.

## Install and start

1. Open **ControlPilot → Services → VS Code Server**.
2. Choose **Install VS Code** and follow installation progress in the Version section.
3. When installation finishes, choose **Start service**, then **Open VS Code Server**.
4. Enable **Start with workspace** if you want it to start on future boots.

Installation downloads about 235 MB from the official code-server GitHub release. Linux amd64 and arm64 are supported; allow at least 2.5 GiB of free workspace space during installation. The pinned release is 4.135.0. Installation never starts the editor or enables autostart by itself.

The editor uses port **8443** by default. Compose and image port declarations retain this port, so installing it does not require recreating the container. On RunPod, expose 8443 through your pod's HTTP port configuration if it is not already exposed. Its password remains `CODE_SERVER_PASSWORD` in `/workspace/config/secrets.env`.

## Persistence and existing workspaces

- Executable and bundled runtime: `/workspace/apps/code-server`.
- Editor data and extensions: `/workspace/code-server/data` and `/workspace/code-server/extensions`.
- Home and user configuration: `/workspace/home/root`.

The launcher prefers the workspace installation and supports an existing `/usr/bin/code-server` installation. Existing settings, extensions, passwords and files are preserved. After moving from an older image to one without the bundled editor, reinstall through Services; the editor reuses the existing data. Saved autostart is suppressed while the binary is absent and applies again on subsequent boots once installed.

No installation or download runs at container startup. A persisted installation is reused as-is; this action is not an updater. The release version and SHA-256 digests live together in `apps/Portal/services/code_server.py`.

## Failure and retry

Failed downloads, checksum errors or executable checks leave the active installation unchanged. Use **Retry installation** after checking connectivity and disk space. Refresh Services after restarting ControlPilot: progress is kept in memory, while completed installations remain on disk. An interrupted installation can be retried safely. A forcibly terminated process can leave a `.code-server-install-*` staging directory under `/workspace/apps`; inspect and remove only that abandoned directory after confirming no installation is running.

If `/workspace/apps/code-server` already exists but has no usable executable, installation stops without replacing it. Inspect or back up that directory before moving it aside and retrying. Do not remove `/workspace/code-server`, which holds your editor data.

The installer accepts no user-supplied URL or shell command. It verifies the pinned checksum before extracting, rejects unsafe archive entries, limits download/extracted sizes and execution time, and publishes a complete installation atomically. It uses the same ControlPilot authentication policy as other service controls; protect publicly exposed ControlPilot with its password and your deployment access controls.
