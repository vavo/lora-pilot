# RunPod integration

_Last updated: 2026-09-25_

ControlPilot can read your pod's allocated storage and running cost, and schedule a stop or termination through RunPod's REST v2 API. The Dashboard brings those details beside your workspace so you can see what you are using and what the session may cost.

## Connect from the backend

RunPod supplies `RUNPOD_POD_ID` to identify the current pod. ControlPilot first looks for `RUNPOD_API_KEY` in its backend environment, then for the injected credential in `~/.runpod/config.toml`. Both `apiKey` and `apikey` are accepted in that file. Set an explicit key through the deployment's secret environment configuration if the injected credential does not support the operations you need. Restart ControlPilot after changing its environment.

The browser never receives that key. Requests go from ControlPilot to `https://api.runpod.io/v2` with bearer authentication. The browser receives selected status, allocation and cost fields, rather than the full pod response, environment or registry configuration. The endpoint follows ControlPilot's existing login protection, so configure that protection when exposing the interface.

Permissions are checked by RunPod for each operation. A credential that can read the pod may still lack access to network volumes or billing. Those sections show an unavailable message without preventing use of local tools. You do not need to grant billing access just to train a LoRA. Missing credentials also leave local telemetry and workspace features available.

## Read allocation and usage separately

ControlPilot matches the workspace to the storage mounts reported by RunPod. A persistent volume reports its allocation in the pod response. An attached network volume requires an additional read of that volume's details. Dashboard and Storage use the reported allocation instead of the potentially enormous capacity of the underlying storage cluster.

Workspace usage still comes from local file measurements. RunPod's volume endpoint does not report total used or free space, and a shared volume may contain files outside this workspace. ControlPilot therefore shows allocated capacity and measured workspace usage without inventing a whole-volume free-space figure. GB follows ControlPilot's existing display convention of 1,073,741,824 bytes.

If the allocation cannot be read, `WORKSPACE_STORAGE_CAPACITY_GB` remains available as a manual fallback. Its remaining-space figure is an estimate from workspace files. Without an API allocation or manual value, shared storage shows capacity as unavailable. Pod reads are cached for one minute, while network-volume reads are cached for five minutes; a resize may take that long to appear.

## Understand the three spending figures

**Current rate** is the hourly pod cost reported by RunPod. **Estimated session cost** multiplies that rate by the container uptime. It assumes the current rate applied throughout the session, so it is a planning estimate rather than an invoice.

**Today (UTC)** comes from RunPod's pod billing history, filtered to this pod from midnight UTC. The compact spending summary sits alongside GPU, storage and service status, leaving the dashboard's main actions directly below. Billing can arrive after the activity it describes, and these records exclude separate network-volume charges. A missing permission or missing amount appears as unavailable, never as a zero-dollar bill. Billing reads are cached for five minutes.

## Schedule the intended shutdown

The saved shutdown choice in Settings takes precedence over `RUNPOD_POD_SHUTDOWN`. An explicit Stop choice stops the pod. Terminate removes it and its local storage; attached network volumes remain. Storage charges can continue after compute stops.

With Auto selected and no environment override, ControlPilot reads the pod's workspace mount. An attached network volume selects termination; other storage selects stop. The old `RUNPOD_VOLUME_TYPE` and `RUNPOD_NETWORK_VOLUME_ID` hints no longer choose the action. The pod read must succeed before a countdown can be scheduled, and locked pods or unavailable actions are rejected.

The selected action is fixed when the countdown starts. Changing Settings later does not change an existing schedule; cancel it and schedule again to use a different action. ControlPilot checks eligibility again when the timer expires, then sends one v2 action request. Permission failures appear in the shutdown panel, and a failed RunPod request never falls back to shutting down the host. The timer remains local to the ControlPilot process and does not survive its restart.

A status of “Shutdown requested” means the API accepted the request. Confirm the final pod state in the RunPod console. When no `RUNPOD_POD_ID` is present, the existing local `shutdown -h now` behavior remains in use.

The integration follows RunPod's [v2 migration guide](https://docs.runpod.io/api-reference-v2/migrate-from-v1), [pod action API](https://docs.runpod.io/api-reference-v2/pods/trigger-a-pod-state-transition), [network-volume API](https://docs.runpod.io/api-reference-v2/network-volumes/get-a-network-volume) and [pod billing API](https://docs.runpod.io/api-reference-v2/billing/get-pod-billing-history).
