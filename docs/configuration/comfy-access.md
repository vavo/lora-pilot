# ComfyUI access protection

_Last updated: 2026-09-05_

Protection is **off by default**. Without enabling it, existing ComfyUI URLs,
API clients and internal integrations work as before, without API credentials.
Creating a token does not enable protection; revoking a token does not disable it.

## Enable from ControlPilot

1. In **Settings → Access Protection**, set a ControlPilot password.
2. In **Settings → ComfyUI Access**, check **Protect ComfyUI and its API**.
3. Click **Apply protection** when no generation is running. Applying a change
   stops and restarts ComfyUI, interrupting active work.
4. Open ComfyUI from ControlPilot. Protected access uses the ControlPilot origin
   with `/comfy/` appended, including on RunPod.

Browsers reuse the ControlPilot login. The ComfyUI page and Services link switch
to the protected gateway. Opening the gateway without a session sends you to
ControlPilot's login. Use HTTPS when accessing the gateway remotely.

When protected, ComfyUI binds to `127.0.0.1` instead of `0.0.0.0`. Direct external
access to port 5555 (or the configured `COMFY_PORT`) is unavailable. Internal
clients in the same container, including MediaPilot, keep using localhost.
The gateway forwards HTTP requests, uploads, output downloads, and text/binary
WebSocket messages. It does not forward your gateway token or ControlPilot cookie
to ComfyUI.

## API clients

Click **Generate API token**, then copy the value. Only its SHA-256 hash is stored;
the original token is shown once. **Replace API token** invalidates the old token
immediately. Tokens grant ComfyUI access only, not ControlPilot Settings or APIs.

Set `COMFY_API_TOKEN` in your client environment and use the gateway URL shown in
Settings. For example:

```bash
curl -H "Authorization: Bearer $COMFY_API_TOKEN" \
  "https://YOUR-CONTROLPILOT-HOST/comfy/system_stats"
```

Use the same prefix for `/prompt`, `/upload/image`, `/history`, `/view`, and other
Comfy routes. WebSocket clients connect to
`wss://YOUR-CONTROLPILOT-HOST/comfy/ws?clientId=YOUR_CLIENT_ID` and send the bearer
header during the upgrade. Tokens in query strings are not accepted.

**Revoke API token** blocks external token-based access immediately. Protection
stays on and authenticated browsers continue to work. A token is therefore
optional for browser-only protected access.

## Disable and failure behaviour

Uncheck **Protect ComfyUI and its API**, then click **Apply protection** to restore
public listening and credential-free direct access. Disable ComfyUI protection
before removing the ControlPilot password.

The policy persists at `/workspace/config/comfy-access.json` with mode `0600`.
If ComfyUI cannot be stopped, the setting is not changed. If it cannot start,
the saved policy remains applied and Settings reports the failure. An unreadable
or invalid policy blocks the gateway and stops ComfyUI startup; it never falls
back to a public listener. Restore a valid policy from backup before restarting.

Protection controls external entry to ComfyUI, not access by trusted processes
inside the container. Existing user-installed custom nodes retain their normal
ComfyUI permissions.
