# Supported Models

_Last updated: 2026-11-23_

Choose from **62 training model groups** across AI Toolkit, Kohya SS, and Diffusion Pipe: 39 image/editing groups, 14 video groups, 3 audio groups, and 6 advanced-configuration groups. A group can include several checkpoint versions or sizes; the tables retain those variants.

This reference updates the [LoRA Pilot training-model inventory](https://lorapilot.com/lora-training/#supported-models) against the pinned trainer source, checked November 23, 2026. The audited trainer pins match this checkout's build configuration. Your installed image may contain older versions.

## Read the compatibility tables

- **UI**: a preset in the pinned AI Toolkit interface.
- **Config**: a documented or registered training path using YAML, TOML, or trainer scripts. Kohya's bundled scripts may support paths that its GUI does not expose.
- **—**: the audit did not establish support in that trainer.
- **Named variants**: support applies only to the versions named in that cell.
- **Extra setup**: additional dependencies or configuration are required; see the row's notes.

These tables describe trainer support. They do not establish a successful GPU training run for each entry. [TrainPilot's guided recipes](../components/trainpilot.md) cover SDXL, FLUX.1 dev, SD 1.5, and SD 3.5 Medium/Large, Anima, Lumina-Image 2.0 and HunyuanImage 2.1; use the other trainers for the wider list below.

Download weights separately and match the checkpoint format, text encoders, dataset type, and hardware to the chosen trainer. VRAM needs depend on the model, resolution, precision, batch size, and offloading settings. Check the model's license and access requirements before downloading. Compatible community fine-tunes follow their parent architecture.

## Image and editing models

| Base model / versions | AI Toolkit | Kohya SS | Diffusion Pipe | Training notes |
|---|---|---|---|---|
| FLUX.3 Image Klein Base | UI | — | — | Base checkpoint only; distilled FLUX.3 is not a training substitute. The catalog’s published DiT filenames require an explicit local model path in AI Toolkit. |
| Qwen-Image 2.1 / Turbo | UI | — | — | Generation and editing share the architecture. Turbo uses its training adapter and fixed eight-step sampling. Uses a dedicated Qwen3-VL-8B encoder and RGBA VAE. |
| Ming-Image 0.1 Design | UI | — | — | Ling Mini 2.0 encoder, RGBA VAE and a training adapter. The pinned UI exposes generation; editing needs configuration. |
| MOSS-Image Base / SFT | UI | — | — | Qwen3.5-9B and small FLUX.2 VAE. Edit training is experimental; inference with edit LoRAs needs the separate ComfyUI-MOSS-Image-Ostris-Edit extension. |
| Fibo 2.0 Dev | UI | — | — | Generation/editing with Qwen3-VL-4B and FLUX.2 VAE. Match the model’s null-caption guidance. |
| Iris-3B | UI | — | — | Pixel-space base model with Qwen3-VL-4B; no VAE. Keep config.yaml alongside the checkpoint. |
| Pruna P-H3-Image | UI | — | — | Image generation/editing with its own text encoder, image VAE and training adapter; not the H3 video stack. |
| MiniMax H3 Image | UI | — | — | Six-step image model; shares H3’s text encoder but uses a dedicated image VAE and training adapter. |
| FLUX.2 dev | UI | — | Config | Image and edit training. Use the matching Mistral text encoder. |
| FLUX.2 Klein base 4B / base 9B | UI | — | Config | Train the base checkpoints, not the step-distilled Klein variants. Each size needs its own text encoder. |
| FLUX.1 dev / schnell | UI / Config | Config | dev | dev is in the AI Toolkit UI; schnell uses its LoRA configuration and training adapter. Diffusion Pipe documents dev. |
| FLUX.1 Kontext dev | UI | — | Config | Image editing uses paired reference and target images. |
| Flex.1 alpha | UI | — | Config | Diffusion Pipe uses its Flux path with guidance embedding bypassed. |
| Flex.2 preview | UI | — | — | Separate AI Toolkit extension and preview checkpoint. |
| Qwen-Image / Qwen-Image-2512 | UI | — | Original base | Both versions appear in AI Toolkit. Diffusion Pipe documents the original Qwen-Image. |
| Qwen-Image-Edit / Edit-2509 / Edit-2511 | UI | — | Original Edit | AI Toolkit includes all three edit versions; 2509 and 2511 use the Edit Plus architecture. |
| Z-Image / Z-Image-Turbo / De-Turbo | UI | — | Base / Turbo | Turbo needs the trainer-specific training-adapter setup. De-Turbo is an AI Toolkit option. |
| Z-Image L2P | UI | — | — | Uses the L2P merge checkpoint and a separate architecture option. |
| Stable Diffusion 1.4 / 1.5 | UI / Config | Config | — | AI Toolkit exposes 1.5 in its UI; older 1.x checkpoints use the SD1 configuration path. |
| Stable Diffusion 2.0 / 2.1 | Config | Config | — | Legacy SD2 path; match checkpoint resolution and prediction settings. |
| SDXL 1.0 | UI | Config | Config | SDXL base and compatible derivatives. Inpainting training is also documented in Kohya’s bundled sd-scripts. |
| Stable Diffusion 3 / 3.5 Medium / 3.5 Large | Config | Config | Config | AI Toolkit’s SD3.5 Large LoRA example is marked experimental. Kohya and Diffusion Pipe document SD3/3.5 training. |
| Anima Base v1.0 | UI | Config | Config | Use the trainer’s expected Diffusers or ComfyUI checkpoint format. |
| Lumina-Image 2.0 | UI | Config | Config | Dedicated Lumina training path in all three stacks. |
| HunyuanImage 2.1 | — | Config | Config | Image model; separate from HunyuanVideo. |
| Chroma1 Base | UI | — | Config | Use the base checkpoint for Chroma LoRA training. |
| Zeta-Chroma | UI | — | — | Pixel-space base checkpoint with its own architecture. |
| HiDream I1 Full | UI | — | Config | Full checkpoint only in this inventory; Diffusion Pipe explicitly warns against Dev and Fast. |
| HiDream E1-1 | UI | — | — | Image editing model. |
| HiDream O1 Image | UI | — | — | Separate O1 image architecture. |
| OmniGen2 | UI | — | Config | AI Toolkit supports reference-image training; Diffusion Pipe documents text-to-image only. |
| ERNIE-Image | UI | — | Config | Dedicated image-training implementation. |
| Nucleus-Image | UI | — | — | Dedicated image-training implementation. |
| Ideogram 4 | UI | — | Config | Open checkpoint path with trainer-specific component loading. |
| PRX Pixel T2I | UI | — | — | Photoroom’s pixel-space text-to-image model. |
| Krea 2 Raw / Turbo | UI | — | Raw | AI Toolkit offers image and edit modes for both; Turbo uses a training adapter. Diffusion Pipe documents Raw. |
| Boogu-Image 0.1 Base / Edit | UI | — | — | Separate base and editing architecture options. |
| Mage-Flow Base / Edit-Base | UI | — | — | Separate generation and editing models. |
| Cosmos-Predict2 2B / 14B | — | — | Config | Text-to-image training only. This does not establish Predict2.5 or Video2World support. |

## Video models

| Base model / versions | AI Toolkit | Kohya SS | Diffusion Pipe | Training notes |
|---|---|---|---|---|
| Wan 2.1 T2V 1.3B / 14B | UI | — | Config | Text-to-video LoRA training. |
| Wan 2.1 I2V 14B · 480p / 720p | UI | — | Config | Use the I2V checkpoint and first-frame conditioning. |
| Wan 2.2 T2V / I2V A14B | UI | — | Config | Mixture-of-experts models; configure high- and low-noise expert training as the trainer requires. |
| Wan 2.2 TI2V 5B | UI | — | Config | Diffusion Pipe documents text-to-image/video training, not I2V training, for this checkpoint. |
| LTX-2 / LTX-2.3 / LTX-2.5 | UI | — | 2.3 only | AI Toolkit has all three architecture options. Diffusion Pipe’s LTX-2.3 path trains images/video without audio. |
| LTX-Video 0.9.x · latest 0.9.8 | — | — | Config | Legacy LTX-Video family, separate from LTX-2. Newer checkpoints use single_file_path; only text-to-image/video training is documented. |
| HunyuanVideo | — | — | Config | Original text-to-video model. Use the dedicated 1.5 path for that newer family. |
| HunyuanVideo 1.5 | — | — | Config | Text-to-image/video training; I2V training is not documented by this pinned trainer. |
| Cosmos 1.0 Diffusion Text2World 7B / 14B | — | — | Extra setup | Tentative upstream support requires TransformerEngine installation. Not a ready-to-run bundled preset. |
| MiniMax H3 | UI | — | Config | Text-to-video/audio training; follow the trainer’s quantization and distillation guidance. |
| MiniMax H3 Ref2VA | UI | — | — | Dedicated reference-to-video/audio training path. |
| FastH3 Omni | UI | — | — | Eight-step reference-to-video/audio; uses its own distilled checkpoint and training adapter, with shared H3 encoders/VAEs. |
| FastH3 8-Step V2 | UI | — | — | Eight-step text-to-video/audio only; no first-frame or reference conditioning. Requires its matching training adapter. |
| FastH3 Preview v0.2 | Config | — | — | FastVideo’s distilled MiniMax H3 variant. Requires converted weights and the minimax_h3_vsa architecture. |

## Audio models

| Base model / versions | AI Toolkit | Kohya SS | Diffusion Pipe | Training notes |
|---|---|---|---|---|
| YuE2 3B | UI | — | — | Comfy repack with embedded text tokenizer/VAE; audio datasets use a community semantic tokenizer and MERT. SheetSage adds score conditioning. These are not image-training recipes. |
| ACE-Step 1.5 Base | UI | — | — | Audio LoRA training; requires an audio dataset and the matching base checkpoint. |
| ACE-Step 1.5 XL Base | UI | — | — | Separate XL audio architecture and checkpoint. |

## Advanced configuration models

These image-model paths require configuration or backend setup outside the pinned web-UI presets.

| Base model / versions | AI Toolkit | Kohya SS | Diffusion Pipe | Training notes |
|---|---|---|---|---|
| AuraFlow 0.3 | Config | — | Config | Dedicated AuraFlow architecture; use the 0.3 checkpoint. |
| PixArt-α XL-2 / PixArt-Σ XL-2 | Config | — | — | Legacy PixArt and PixArt Sigma paths; match checkpoint, text encoder and VAE. |
| CogView4-6B | Config | — | — | Registered backend with LoRA target modules; not a pinned web-UI preset. |
| F-Lite Standard / Texture | Config | — | — | F-Lite backend and matching model components; not a pinned web-UI preset. |
| Chroma1-Radiance (x0) | Config | — | — | Separate pixel-space backend; not interchangeable with Chroma1 Base. |
| Segmind SSD-1B / Vega | Config | — | — | Legacy distilled SDXL architectures with their own configuration flags. |

## Source versions and compatibility notes

The November 23 inventory cites these sources. The 62 groups count table rows, combining sizes and presets within each named group:

- [LoRA Pilot build configuration](../../Dockerfile).
- **AI Toolkit 0.13.43 (`73c84b0`)**: [UI presets](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/diffusion_models/ui.tsx), [diffusion registry](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/diffusion_models/__init__.py), [legacy and built-in paths](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/toolkit/util/get_model.py), [audio models](https://github.com/ostris/ai-toolkit/tree/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/audio_models), and [Flex.2](https://github.com/ostris/ai-toolkit/tree/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/flex2).
- **[Kohya SS `v26.0.0`](https://github.com/bmaltais/kohya_ss/tree/v26.0.0)** with [sd-scripts `6721028`](https://github.com/kohya-ss/sd-scripts/blob/6721028c79ee85a78b3a06dfd8954dae310a1cce/README.md#supported-models). Musubi Tuner is a separate trainer; its support is not attributed to Kohya SS.
- **[Diffusion Pipe `8f83dbf`](https://github.com/tdrussell/diffusion-pipe/blob/8f83dbf25d03219df705570ec03e62be04bc402f/docs/supported_models.md)**: checkpoint variants, dataset restrictions, and setup requirements.
- AI Toolkit's [SD3.5 Large LoRA example](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/config/examples/train_lora_sd35_large_24gb.yaml) is experimental. Loading an existing SD3 LoRA through `model.lora_path` is a separate, unsupported path.
- Checkpoint details: [LTX-Video versions](https://huggingface.co/Lightricks/LTX-Video), [F-Lite variants](https://github.com/fal-ai/f-lite), and [PixArt Sigma XL-2](https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS).

## New catalog components and loading

The Models page groups variants within families and includes an Audio filter. MiniMax H3 Image and Pruna P-H3-Image stay separate from H3 video; FastH3 appears with the H3 video components it shares. Downloading one checkpoint does not install every component or a ComfyUI extension.

Training adapters download under `/workspace/models/loras/training_adapters`. Select the matching file in the trainer’s `assistant_lora_path` setting when using that local copy. These adapters belong to training; the trainer removes or disables them for inference previews.

FLUX.3 uses the published `flux3-image-klein-base-*.safetensors` filenames. In AI Toolkit, set `model.name_or_path` to that file under `/workspace/models/diffusion_models` instead of relying on the pinned resolver’s older underscore filenames. Keep the Base checkpoint for training. Fibo and FLUX.3 share `qwen3vl-4b-int8` and `flux2-vae`. Iris uses the full checkpoint directory under `/workspace/models/checkpoints/iris3b`, including `config.yaml`, and has its own encoder entry.

YuE2’s Comfy checkpoint contains the text tokenizer and VAE; the raw vendor weights are not interchangeable. The catalog includes the default v4 semantic head/NAR adapter under `ai_toolkit`, MERT under `audio_encoders/MERT-v2-FullSong`, and SheetSage for score conditioning. The pinned trainer fetches MERT through Hugging Face’s cache; a catalog directory is not automatically that cache. Follow its loader configuration when using a local MERT copy. Optional separation/score modes can fetch further assets. ControlPilot’s guided training and MCP comparison tools remain image-model workflows.

## Find and download model weights

Training support and inference support are separate. The Models catalog and bundled ComfyUI workflows have their own coverage; a downloadable model is not proof of training support. Use the [model management guide](../user-guide/model-management.md) to review components, source access, and installation status.

Inside the pod or container, inspect the active manifest before choosing a download name:

```bash
models list
models where
models pull sdxl-base
models pull flux1-dev
```

The names in the tables identify training checkpoints and architectures. They are not all `models pull` aliases. For a checkpoint outside the catalog, follow the selected trainer's model-loading instructions and keep weights under `/workspace/models`.

Continue with [training workflows](../user-guide/training-workflows.md), [dataset preparation](../user-guide/dataset-preparation.md), or [inference model selection](../getting-started/inference-101/model-selection-for-inference.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
