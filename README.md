# LoRA Pilot (The Last Docker Image You'll Ever Need)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-vavo-5F7FFF?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white)](https://www.buymeacoffee.com/vavo) [![GitHub Sponsors](https://img.shields.io/github/sponsors/vavo?style=for-the-badge&logo=github)](https://github.com/sponsors/vavo) [![Sponsor on GitHub](https://img.shields.io/badge/Sponsor%20on-GitHub-24292F?style=for-the-badge&logo=github)](https://github.com/sponsors/vavo)
![LoRA Pilot logo](apps/Portal/static/logo.svg)

> Your AI playground in a box - because who has time to configure 17 different tools?
Ever wanted to train LoRAs but ended up in dependency hell? LoRA Pilot bundles dataset workflow, model management, training, and generation into one container with one persistent `/workspace`.

## Why this is useful
- **Redesigned ControlPilot UI** with cleaner service/model/dataset/training flows.
- **Single-port workflow**: MediaPilot and TagPilot are embedded inside ControlPilot.
- **Multiple training stacks**: Kohya SS, Diffusion Pipe, AI Toolkit, and TrainPilot.
- **Integrated coding helper (optional)**: Copilot sidecar accessible from ControlPilot.
- **No throwaway setup**: outputs, models, datasets, and config persist under `/workspace`.

## Supported LoRA training models
- Stable Diffusion 1.5
- Stable Diffusion 2.1
- SDXL
- SD3
- FLUX.1-dev
- FLUX.1-schnell
- FLUX.1-kontext
- OmniGen2
- PixArt Alpha
- PixArt Sigma
- AuraFlow
- Lumina2
- HunyuanVideo
- LTX
- LTX2
- Wan 2.1 / 2.2
- Cosmos
- Qwen-Image
- Qwen-Image-Edit
- Z-Image-Turbo

Currently supports **SD1, SD2, SDXL, SD3, FLUX.1 (dev/schnell), Chroma, Lumina-Image 2.0, LTX-Video, HunyuanVideo, Wan2.1, Wan2.2, Cosmos, HiDream, Z-Image** and more for training, plus almost everything for inference.

##  What's in the box?
- **ControlPilot** – redesigned command center for services, models, datasets, docs, and training flows
- **🎨 ComfyUI** (+ ComfyUI-Manager preinstalled) - Your node-based playground
- **🏋️ Kohya SS** - Where LoRAs are born (web UI included!)
- **🧪 AI Toolkit** - first-class trainer wired into the same workspace
- **📓 JupyterLab** - For when you need to get nerdy
- **💻 code-server** - VS Code in your browser (because local setups are overrated)
- **🔮 InvokeAI** - Living in its own virtual environment (the diva of the bunch)
- **🚂 Diffusion Pipe** - Training + TensorBoard, all cozy together
- **MediaPilot** – image viewer/manager embedded in ControlPilot (no extra public port)
- **TagPilot** – dataset tagger embedded on the same port as ControlPilot
- **TrainPilot** - the easiest way to run SDXL training on kohya
- **GUI for dpipe** - a web UI for diffusion pipe
- **🤖 Copilot (optional)** - a sidecar that wraps the `copilot` CLI so it can operate on `/workspace` with tools (via ControlPilot tab)


![Control Pilot screenshot](apps/Portal/static/lora-pilot-UI.heic)
Screenshot of Control Pilot UI

Everything is orchestrated by **supervisord** and writes to **/workspace** so you can actually keep your work. Imagine that! 

Few of the thoughtful details that really bothered me when I was using other SD (Stable Diffusion) docker images:
- If you want stabiity, just choose :stable and you'll always have 100% working image. Why change anything if it works? (I promise not to break things in :latest though)
- when you login to Jupyter or VS code server, change the theme, add some plugins or setup a workspace - unlike with other containers, your settings and extensions will persist between reboots
- no need to change venvs once you login - everything is already set up in the container
- did you always had to install mc, nano or unzip after every reboot? No more!
- there are loads of custom made scripts to make your workflow smoother and more efficient if you are a CLI guy; 
- Need SDXL1.0 base model? "models pull sdxl-base", that's it! 
- Want to run another kohya training without spending 30 minutes editing toml file?Just run "trainpilot", choose a dataset from the select box, desired lora quality and a proven-to-always-work toml will be generated for you based on the size of your dataset.
- ControlPilot gives you a web UI to manage all services without needing to use the command line
- prefer CLI and want to manage your services? Never been easier: "pilot status", "pilot start", "pilot stop" - all managed by supervisord

---

## Default ports

| Service | Port |
|---|---:|
| Diffusion Pipe (TensorBoard) | `4444` |
| ComfyUI | `5555` |
| Kohya SS | `6666` |
| ControlPilot | `7878` |
| MediaPilot | `7878` (`/mediapilot`) |
| code-server | `8443` |
| JupyterLab | `8888` |
| InvokeAI (optional) | `9090` |
| AI Toolkit | `8675` |
| Copilot sidecar (internal) | `7879` |

Expose them in RunPod (or just use my RunPod template - https://console.runpod.io/deploy?template=gg1utaykxa&ref=o3idfm0n).

---

## Local Docker (Compose)

LoRA Pilot also runs on localhost via Docker Compose (GPU, CPU, and dev setups included).

Quick start:
```bash
cp .env.example .env
docker compose -f docker-compose.yml up -d
```

See `DOCKER_COMPOSE.md` for a short overview and `docker-compose/README.md` for the full guide.

---

## Storage layout

The container treats **`/workspace`** as the only place that matters.

Expected directories (created on boot if possible):

- `/workspace/models` (shared by everything; Invoke now points here too)
- `/workspace/datasets` (with `/workspace/datasets/images` and `/workspace/datasets/ZIPs`)
- `/workspace/outputs` (with `/workspace/outputs/comfy` and `/workspace/outputs/invoke`)
- `/workspace/apps`
  - Comfy: user + custom nodes under `/workspace/apps/comfy`
  - Diffusion Pipe under `/workspace/apps/diffusion-pipe`
  - Invoke under `/workspace/apps/invoke`
  - Kohya under `/workspace/apps/kohya`
  - MediaPilot under `/workspace/apps/MediaPilot` (https://github.com/vavo/MediaPilot)
  - TagPilot under `/workspace/apps/TagPilot` (https://github.com/vavo/TagPilot)
  - TrainPilot under `/workspace/apps/TrainPilot`(not yet on GitHub)
- `/opt/pilot/repos/ai-toolkit` (source) with persistent links to `/workspace/datasets`, `/workspace/models`, and `/workspace/outputs/ai-toolkit`
- `/workspace/config`
- `/workspace/cache`
- `/workspace/logs`

### RunPod volume guidance

The `/workspace` directory is the only volume that needs to be persisted. All your models, datasets, outputs, and configurations will be stored here. Whether you choose to use a network volume or local storage, this is the only directory that needs to be backed up.

**Disk sizing (practical, not theoretical):**
- Root/container disk: **20–30 GB** recommended 
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
COMFY_PORT=5555
KOHYA_PORT=6666
DIFFPIPE_PORT=4444
CODE_SERVER_PORT=8443
JUPYTER_PORT=8888
INVOKE_PORT=9090
AI_TOOLKIT_PORT=8675
COPILOT_SIDECAR_PORT=7879

## AI Toolkit (optional)
AI_TOOLKIT_DB_PATH=/workspace/config/ai-toolkit/aitk_db.db
# DB is persisted under /workspace by default

## Jupyter (optional)
JUPYTER_ALLOW_ORIGIN_PAT=...   # extra origin regex appended to defaults (RunPod proxy + localhost + 127.0.0.1)

## Shutdown scheduler (ControlPilot)
RUNPOD_POD_SHUTDOWN=stop       # default; safe for local storage
RUNPOD_POD_SHUTDOWN=remove     # terminate pod (network volume only)
RUNPOD_VOLUME_TYPE=network    # auto-select remove
RUNPOD_VOLUME_TYPE=local      # auto-select stop

## Hugging Face (optional but often necessary)
HF_TOKEN=...                 # for gated models
HF_HUB_ENABLE_HF_TRANSFER=1  # faster downloads (requires hf_transfer, included)
HF_XET_HIGH_PERFORMANCE=1    # faster Xet storage downloads (included)

## Diffusion Pipe (optional)
DIFFPIPE_CONFIG=/workspace/config/diffusion-pipe.toml
DIFFPIPE_LOGDIR=/workspace/diffusion-pipe/logs
DIFFPIPE_NUM_GPUS=1
If DIFFPIPE_CONFIG is unset, the service just runs TensorBoard on DIFFPIPE_PORT.


## Model downloader (built-in)

The image includes a system-wide command:
• models (alias: pilot-models)

Usage:
• models list
• models pull <name> [--dir SUBDIR]
• models pull-all

You can also download models using Lora Pilot's web interface running at port 7878.

## Manifest

Models are defined in the manifest shipped in the image:
	•	/opt/pilot/models.manifest

A default copy is also shipped here (useful as a reference/template):
	•	/opt/pilot/config/models.manifest.default

If your get-models.sh supports workspace overrides, the intended override location is:
	•	/workspace/config/models.manifest

(If you don’t have override logic yet, copy the default into /workspace/config/ and point the script there. Humans love paper cuts.)

Both `models` and `modelsgui` will use `/workspace/config/models.manifest` when present.

## Example usage

# download SDXL base checkpoint into /workspace/models/checkpoints
models pull sdxl-base

# list all available model nicknames
models list

## Security note (because reality exists)

- supervisord can run with an unauthenticated unix socket by default.
- This image is meant for trusted environments like your own RunPod pod.
- Don’t expose internal control surfaces to the public internet unless you enjoy chaos monkeys.

## Support

This is not only my hobby project, but also a Docker image I actively use for production work.
I create frequent builds to keep things fresh and working, and I am happy to implement reasonable feature requests.
If you need help or have questions, feel free to reach out or open an issue on GitHub.

Reddit: u/no3us

## Sponsor

If LoRA Pilot saves you time (or sanity), sponsor the project:

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor%20on-GitHub-24292F?style=for-the-badge&logo=github)](https://github.com/sponsors/vavo)

---

## 🆕 Recent Updates

### ControlPilot 2.x redesign
- New design system and cleaner UI flows for services, models, datasets, docs, and training operations.
- Better service controls and model management UX in one place.

### MediaPilot integrated into ControlPilot
- MediaPilot is now built-in and mounted under `/mediapilot` (same public port as ControlPilot).
- Theme synchronization (light/dark) and ControlPilot visual consistency.
- Bootstrap auto-seeds MediaPilot `.env` defaults for workspace paths and Comfy API URL.

### Services can update themselves from UI
- Added service version checks and in-app update actions.
- Update jobs run asynchronously with status/progress reporting and service restart handling.

### Training stack upgrades
- AI Toolkit integrated as a first-class training service with persistent DB/config under `/workspace`.
- Copilot sidecar support exposed in ControlPilot for workspace-aware automation flows.

---

## 🙏 Standing on the shoulders of giants
- ComfyUI - Node-based magic
- ComfyUI-Manager - The organizer
- Kohya SS - LoRA whisperer
- code-server - Code anywhere
- JupyterLab - Data scientist's best friend
- InvokeAI - The fancy pants option
- Diffusion Pipe - Training powerhouse
- TensorBoard - Visualization tool

## 📜 License
MIT License - go wild, make cool stuff, just don't blame us if your AI starts writing poetry about toast.

Made with ❤️ and way too much coffee by vavo

"If it works, don't touch it. If it doesn't, reboot. If that fails, we have Docker." 
    - Ancient sysadmin wisdom

---
