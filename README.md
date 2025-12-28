# LoRA Pilot

A container image for **RunPod** (and anywhere else you can run Docker) that bundles the usual “AI workstation in a box” stack:

- **ComfyUI** (+ **ComfyUI-Manager** preinstalled)
- **Kohya SS** (web UI)
- **JupyterLab**
- **code-server** (VS Code in the browser)
- (Optional) **InvokeAI** in its own venv

Everything is started by **supervisord** and writes state/logs to **/workspace** so you can mount a persistent volume and not cry later.

---

## Default ports

| Service | Port |
|---|---:|
| JupyterLab | `8888` |
| code-server | `8443` |
| ComfyUI | `5555` |
| Kohya SS | `6666` |
| InvokeAI (optional) | `9090` |

Expose them in RunPod (or publish them in Docker).

---

## Storage layout

The container treats **`/workspace`** as the only place that matters.

Expected directories (created on boot if possible):

- `/workspace/models`
- `/workspace/datasets`
- `/workspace/outputs`
- `/workspace/custom_nodes`
- `/workspace/apps`
- `/workspace/config`
- `/workspace/cache`
- `/workspace/logs`

### RunPod volume guidance

- **Mount a persistent volume to `/workspace`**.
- Some RunPod mounts are **not chown-able**. You may see:
  - `chown: ... Operation not permitted`
  This is usually harmless and expected.

**Disk sizing (practical, not theoretical):**
- Root/container disk: **50–80 GB** recommended (the stack is heavy).
- `/workspace` volume: **100 GB minimum**, more if you plan to store multiple base models/checkpoints.

---

## Credentials

Bootstrapping writes secrets to:

- `/workspace/config/secrets.env`

Typical entries:
- `JUPYTER_TOKEN=...`
- `CODE_SERVER_PASSWORD=...`

---


## Ports (optional overrides)
JUPYTER_PORT=8888
CODE_SERVER_PORT=8443
COMFY_PORT=5555
KOHYA_PORT=6666
INVOKE_PORT=9090

## Hugging Face (optional but often necessary)
HF_TOKEN=...                 # for gated models
HF_HUB_ENABLE_HF_TRANSFER=1  # faster downloads (requires hf_transfer, included)
HF_XET_HIGH_PERFORMANCE=1    # faster Xet storage downloads (included)

### Optional: disable OneTrainer (default: enabled)
INSTALL_ONETRAINER=1

### Optional: disable ComfyUI (default: enabled)
INSTALL_COMFY=1

### Optional: disable Kohya SS (default: enabled)
INSTALL_KOHYA=1

### Optional: disable InvokeAI (default: enabled)
INSTALL_INVOKE=1

## Model downloader (built-in)

The image includes a system-wide command:
•	models (alias: pilot-models)

Usage:
•	models list
•	models pull <name> [--dir SUBDIR]
•	models pull-all

## Manifest

Models are defined in the manifest shipped in the image:
	•	/opt/pilot/models.manifest

A default copy is also shipped here (useful as a reference/template):
	•	/opt/pilot/config/models.manifest.default

If your get-models.sh supports workspace overrides, the intended override location is:
	•	/workspace/config/models.manifest

(If you don’t have override logic yet, copy the default into /workspace/config/ and point the script there. Humans love paper cuts.)

## Example usage

# download SDXL base checkpoint into /workspace/models/checkpoints
models pull sdxl-base

# list all available model nicknames
models list

## Security note (because reality exists)

- supervisord can run with an unauthenticated unix socket by default.
- This image is meant for trusted environments like your own RunPod pod.
- Don’t expose internal control surfaces to the public internet unless you enjoy chaos.

⸻

## Credits

-	ComfyUI: https://github.com/comfyanonymous/ComfyUI
-	ComfyUI-Manager: https://github.com/ltdrdata/ComfyUI-Manager
-	Kohya SS: https://github.com/bmaltais/kohya_ss
-	code-server: https://github.com/coder/code-server
-	JupyterLab: https://jupyter.org/
-	InvokeAI: https://github.com/invoke-ai/InvokeAI

---

MIT License

Copyright (c) 2025 Vavo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.