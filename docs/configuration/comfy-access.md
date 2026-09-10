# ComfyUI access protection

_Last updated: 2026-09-10_

You can open ComfyUI through the same browser login you use for ControlPilot while giving an API client a separate credential. LoRA Pilot's optional ComfyUI gateway supports that arrangement. You keep browser access convenient and can replace a client's token without changing the ControlPilot password.

Protection is off by default. Enable it as a deliberate change to how you reach ComfyUI, with time to update any external clients. Generating a token alone does not enable protection, and revoking a token does not turn protection off.

## Move browser access to the gateway

Open **Settings** in ControlPilot and set a password under **Access Protection**. Then find **ComfyUI Access**, select **Protect ComfyUI and its API**, and choose **Apply protection**. Finish active generation first: applying a protection change stops and restarts ComfyUI.

Open ComfyUI through ControlPilot after the change. The protected address uses the ControlPilot origin with `/comfy/` appended, including on RunPod. Your browser reuses the ControlPilot session. Without a valid session, the gateway directs the browser to the ControlPilot login. Use HTTPS for remote access to that origin.

With protection enabled, the launcher binds ComfyUI to `127.0.0.1`. Direct external access through port `5555`, or your configured Comfy port, is no longer the access path. Internal clients in the same container can continue using localhost, including MediaPilot.

## Give an API client its own token

Choose **Generate API token** in Settings and copy the value into the intended client's secret configuration. ControlPilot shows the token once and stores its SHA-256 hash. A Comfy token grants access to the Comfy gateway; it does not grant access to ControlPilot's settings or other APIs.

For an HTTP client, send the token in the `Authorization` header and use the gateway address shown in Settings. The example below reads ComfyUI system information. Replace the host with your configured ControlPilot host and set `COMFY_API_TOKEN` in the client environment without committing it to source.

```bash
curl -H "Authorization: Bearer $COMFY_API_TOKEN"   "https://YOUR-CONTROLPILOT-HOST/comfy/system_stats"
```

Use the same `/comfy/` prefix for routes such as `/prompt`, `/upload/image`, `/history`, and `/view`. The gateway forwards HTTP traffic, uploads, output downloads, and text or binary WebSocket messages. It removes the gateway credential and ControlPilot session cookie before forwarding the request to ComfyUI.

WebSocket clients use `wss://YOUR-CONTROLPILOT-HOST/comfy/ws?clientId=YOUR_CLIENT_ID` and send the bearer header during the upgrade. Query-string tokens are not accepted. Check that your WebSocket client supports an authorization header before adapting it to the protected gateway.

## Replace access without changing the browser login

Use **Replace API token** when a client needs a new credential. Replacement invalidates the old token immediately, so update clients that still use it. You can use **Revoke API token** to block token-based access while leaving protection enabled.

Authenticated browsers continue using their ControlPilot sessions after token revocation. A token is optional if you need only browser access. This gives you a way to stop an external integration without removing your own browser entry point.

The protection policy lives at `/workspace/config/comfy-access.json` with file mode `0600`. Preserve the policy with the workspace and keep configuration backups private. The gateway controls external entry to ComfyUI; it does not restrict trusted processes inside the container or change the normal permissions of installed custom nodes.

## Interpret a failed protection change

If ControlPilot cannot stop ComfyUI, it leaves the policy unchanged. If it saves the new policy but ComfyUI then fails to start, it keeps that policy and reports the startup failure. Read the ComfyUI service log to resolve the launch problem rather than assuming that the failed restart restored the previous access mode.

An unreadable or invalid policy blocks gateway access and prevents ComfyUI startup. The runtime does not fall back to a public listener in that state. Restore a valid policy from a private backup and inspect the service logs before restarting. The [debugging guide](../development/debugging.md) explains where to find those logs.

## Return to direct access when that is your intended setup

Clear **Protect ComfyUI and its API** and choose **Apply protection** to restore public listening and credential-free direct access. This change interrupts the service, so schedule it around active work and review the exposed port in your deployment.

Disable ComfyUI protection before removing the ControlPilot password. That order keeps the configuration consistent with the gateway's browser-login requirement. Use the [configuration overview](README.md) to review other service settings and the [ComfyUI guide](../components/comfyui.md) to continue your workflow after the access change.
