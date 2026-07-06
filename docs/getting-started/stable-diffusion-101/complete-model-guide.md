# Complete Model Guide

_Last updated: 2026-07-06_

This page used to try to list every model in LoRA Pilot. That sounds helpful until the model manifest changes, a link moves, and the docs start lying with confidence. Use the manifest for the exact downloadable files. Use this guide to choose the right family before you click anything expensive.

In LoRA Pilot, the current source of truth for exact model names, Hugging Face repos, file paths, and storage locations is `config/models.manifest`. ControlPilot reads that manifest when it offers model downloads. The docs should teach the decision. The manifest should carry the inventory.

## The First Question

Ask what job you are doing:

- **Fast image experiments**: SD1.5 or SDXL Lightning/Turbo-style models.
- **General high-quality images**: SDXL, Flux, HunyuanImage, Qwen/Image, or Z-Image style families.
- **Photoreal product or portrait work**: SDXL realism checkpoints, Flux-family models, or newer image families with strong prompt following.
- **Character/style LoRA work**: choose the base family your LoRA was trained against.
- **Image editing**: use edit-specific families such as Qwen Image Edit or Flux Kontext-style workflows.
- **Text-to-video or image-to-video**: Wan, LTX, HunyuanVideo, or other video-specific workflows.

The wrong model family can make every other setting look broken. A Flux LoRA will not become an SDXL LoRA because you typed harder. A video model will not behave like a fast SD1.5 checkpoint because you are impatient. Annoying, but at least physics is consistent.

> **Why does this work?** A checkpoint carries the visual habits, architecture, text encoders, VAE assumptions, LoRA compatibility, and preferred workflow shape. Settings tune a model. They do not convert one model family into another.

> **Try this variation:** Pick one prompt and run it through one SDXL checkpoint and one Flux-family workflow. Keep the prompt idea similar, but use each model's recommended settings. Save the outputs in MediaPilot. The differences will explain "model personality" faster than a table can.

## Image Model Families

### SD1.5

SD1.5 is old, fast, small, and still useful. It usually works around 512-class resolutions, runs on modest GPUs, and has a huge ecosystem of LoRAs, ControlNets, embeddings, and community workflows.

Use it when you want speed, low VRAM use, legacy LoRA compatibility, or a quick learning surface. Avoid it when you need modern prompt following, large clean compositions, high text fidelity, or out-of-the-box realism.

SD1.5 is a good teacher. It is not always the best production model.

### SDXL

SDXL is the practical middle ground for many image workflows. It expects larger images than SD1.5, often around 1024-class sizes, and it handles composition, detail, and prompt language better. LoRA support is broad, and many realism, anime, illustration, and product checkpoints still target SDXL.

Use SDXL when you need a stable ecosystem, good quality, and manageable hardware requirements. If you are training a first image LoRA in LoRA Pilot, SDXL is often easier to reason about than the newest giant model family.

SDXL variants matter. A base model, a realism checkpoint, a Lightning checkpoint, and a Turbo-style checkpoint can want different steps, guidance, and samplers. Read the model card before copying settings.

### Flux

Flux-family models tend to reward natural language prompts and strong visual detail. They can require more VRAM and more specific ComfyUI loader setups than SDXL. LoRA training and inference can also be more sensitive to precision, text encoder choices, and workflow shape.

Use Flux when quality and prompt understanding matter more than speed. Start with a known-good template in ComfyUI or ControlPilot. Do not mix SDXL habits into Flux workflows and then blame the sampler. That has been tried. It remains unconvincing.

### Newer Image Families

LoRA Pilot's manifest may include families such as HunyuanImage, Qwen Image/Edit, Ideogram, Z-Image, PixelDiT, or other ComfyUI-packaged image models. Treat these as model-family workflows, not simple checkpoint swaps.

These models can bring their own text encoders, VAEs, diffusion model files, quantized variants, and special nodes. Use the manifest and the model card together:

- The manifest tells you which files LoRA Pilot knows how to download.
- The model card tells you expected settings, license terms, and limitations.
- The workflow template tells you how those files connect.

## Video Model Families

Video models are not image models that got ambitious. They add time, motion, frame count, temporal consistency, and much larger memory pressure.

### LTX

LTX is useful for short clips, fast iteration, and image-to-video experiments. LoRA Pilot's manifest includes LTX 2.3 entries, including checkpoints, distilled variants, LoRAs, and upscalers. Use the current manifest rather than an old blog post when you need exact filenames.

Choose LTX when you want a practical video workflow and can accept short clips while you learn motion prompting, frame count, and upscaling.

### Wan

Wan-family models cover text-to-video, image-to-video, and animation workflows. Some variants are small enough for easier experiments; others are large enough to make your GPU invoice develop personality.

Choose Wan when you need stronger video quality, image-to-video workflows, or animation-specific pipelines. Use official or ComfyUI template workflows first. Video graphs are not where beginners should improvise with missing nodes.

### HunyuanVideo

HunyuanVideo is a heavier video option. It can produce strong results, but the model files and runtime cost are larger. Use it when quality matters and you have the GPU headroom.

For any video family, start with a tiny test: low resolution, short frame count, known-good prompt, and one seed. Save the working workflow before increasing size.

## Compatibility Rules

The model stack has layers:

1. **Base family**: SD1.5, SDXL, Flux, Wan, LTX, Hunyuan, Qwen, or another family.
2. **Model files**: checkpoint, diffusion model, text encoder, VAE, and sometimes extra encoders.
3. **LoRAs and adapters**: trained for one family, sometimes one checkpoint style.
4. **Workflow**: ComfyUI graph, InvokeAI setup, ControlPilot action, or API call.

Keep the layers compatible before tuning anything else. If a LoRA does nothing, check the base family and trigger word before changing CFG. If a workflow cannot find a model, check the file category in `/workspace/models`. A checkpoint in a LoRA folder is just a large mistake with a file extension.

## VRAM and Speed Expectations

Use these as rough planning ranges, not promises:

| Family | First Guess | Notes |
|---|---|---|
| SD1.5 | 4-8 GB VRAM | Fast, forgiving, older ecosystem |
| SDXL | 8-12 GB VRAM | Strong default for images and LoRAs |
| Flux / newer image families | 12-24+ GB VRAM | Better quality, heavier text encoders and workflows |
| Small video models | 12-24+ GB VRAM | Start with short clips |
| Large video models | 24-48+ GB VRAM | Expect slower runs and larger files |

Quantized or FP8 variants can reduce memory pressure, but they can also change quality, compatibility, and workflow requirements. Use them because they solve a hardware problem, not because the filename looks futuristic.

## Licenses and Access

Some models are open. Some require accepting a gated license on Hugging Face. Some allow research use but restrict commercial use. Some community checkpoints inherit obligations from their base model and add their own terms.

Before training a LoRA or shipping outputs, check:

- model card license
- gated access requirements
- commercial-use language
- attribution requirements
- whether the model family supports your intended content

ControlPilot can help download files. It cannot decide your legal risk for you. Very rude, but fair.

## How to Choose Today

Use SDXL for your first serious image LoRA unless you already know you need another family. Use Flux or newer image families when you want higher image quality and can afford the workflow complexity. Use SD1.5 for speed, legacy LoRAs, and low VRAM. Use video families only when the task needs motion.

When in doubt, choose the boring model that runs, save a baseline workflow, and generate evidence. The glamorous model that never finishes has produced exactly zero useful images.

## Next

Continue with [Generation Parameters](generation-parameters.md) to learn how seed, steps, guidance, sampler, resolution, and batch size change the result.

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
