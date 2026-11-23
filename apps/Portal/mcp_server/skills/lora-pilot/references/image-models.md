# Image prompting by base family

Reference checked 2026-11-23. Identify exact weights and the installed workflow before using a profile. These examples guide prompt writing and experiments; they are not MCP inference endpoints. Proposed ComfyUI starting ranges below are labeled separately from upstream pipeline examples. Preserve a working graph's sampler/schedule unless there is evidence to change it.

## Stable Diffusion 1.x / 1.5

Put the subject, action and framing early. Use a short coherent description or the tag style expected by the fine-tune; long language-model prose can exceed the CLIP encoder's useful context. Example: `small orange robot repairing a radio, close-up, workshop desk, soft window light, documentary photograph`. For a trained character, add the actual trigger, not the words “LoRA character.”

A proposed full-model ComfyUI starting point is 512 × 512 or a trained aspect bucket, 20–30 steps, DPM++ 2M/Karras and CFG 5–7. These are experimentation defaults, not the publisher's mandatory settings. Keep negative prompts targeted to observed failures. SD1 LoRAs, VAEs and ControlNets are not SDXL components. [Model card](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5).

## Stable Diffusion 2.x / 2.1

Use explicit natural scene descriptions; do not assume an SD1 tag embedding or negative embedding works. Verify whether the checkpoint is the 512 base or 768 model and its prediction configuration. Start at that checkpoint's native resolution using its matching scheduler config. A proposed full-model sweep is 25–35 steps and CFG 5–7 only after loading is confirmed. Do not switch epsilon/v-prediction to repair a prompt. If the original card is inaccessible, identify the exact variant rather than infer it from “SD2.” [Official implementation](https://github.com/Stability-AI/stablediffusion).

## SDXL and photographic derivatives

Describe subject/action, composition, material, lighting and medium clearly. Example: `A small orange robot repairs a valve radio on a wooden workbench. A close view shows its scratched enamel hands and the glass vacuum tubes. Soft daylight enters from the left; the background tools fall out of focus.` Use the selected LoRA's trigger naturally. Put exact lettering in quotes and test it visually.

A proposed standard SDXL starting point is about 1024-square pixel area in a supported aspect ratio, 25–35 steps, DPM++ 2M/Karras and CFG 5–7. A RealVisXL or Juggernaut checkpoint may have its own preferred settings; use that revision's card. SDXL Base works without a refiner, so do not require one by default. The MCP comparison deliberately uses its fixed 20-step/CFG-7 recipe instead of accepting this tuning range. [SDXL card](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0).

## SDXL anime derivatives: Pony and Illustrious

Use the exact derivative's vocabulary and training style. Compact character, count, pose, clothing, environment and composition tags can work well. Example content: `small orange robot, seated, workbench, screwdriver, side view, warm indoor light`. Add quality/score/rating tags only when the specific checkpoint card prescribes them; Pony score prefixes are not universal SDXL or Illustrious syntax. Confirm the derivative's VAE and LoRA compatibility before transferring a recipe. Use its native buckets and published sample workflow; do not promise that any SDXL LoRA preserves appearance on every derivative.

## SDXL Turbo, Lightning, LCM and other fast derivatives

Keep the same useful subject/composition description, but select the exact speed variant and schedule first. The original SDXL Turbo is a 1–4-step model with Diffusers guidance 0 and a 512 reference canvas; this does not prescribe CFG 0 in every UI. A four-step Lightning checkpoint or acceleration LoRA has its own matching sampler, schedule and strength. Do not apply a 30-step/CFG-7 full SDXL preset to all of them. [Turbo card](https://huggingface.co/stabilityai/sdxl-turbo).

## Stable Diffusion 3 / 3.5

Use readable sentences specifying object relationships, lighting, material and precise quoted text. Example: `A brushed orange metal robot sits behind a repair-shop counter. On the counter is a white card printed with "OPEN" in large black letters. Eye-level composition, soft afternoon light.` Do not replace clear relationships with quality-tag padding.

Keep SD3, 3.5 Medium, 3.5 Large and Large Turbo separate. Official Diffusers examples use 28 steps/CFG 4.5 for Large and 40/4.5 for Medium; these are source examples, not universal Comfy schedules. Large Turbo has a separate few-step workflow. Match CLIP-L, CLIP-G, T5 and VAE packaging to the checkpoint. [Large](https://huggingface.co/stabilityai/stable-diffusion-3.5-large), [Medium](https://huggingface.co/stabilityai/stable-diffusion-3.5-medium).

## FLUX.1 Dev

Write connected prose about visible details and relationships. Example: `An orange repair robot with chipped enamel leans over a disassembled radio. Its left gripper holds a copper wire while the right steadies the circuit board. Close documentary photograph, soft window light, muted workshop colors.` State desired features positively; a negative box or SDXL weighting syntax may not have the intended effect in the basic FLUX graph.

For a standard Comfy Dev graph, a proposed starting point is 1024 native area, 20–30 steps, Euler/simple, sampler CFG 1, and the separate `FluxGuidance` input around 3.5. Verify that graph rather than entering 3.5 in the sampler CFG field. Match T5, CLIP-L and AE. [Official Comfy example](https://comfyanonymous.github.io/ComfyUI_examples/flux/).

## FLUX.1 Schnell

Use the same scene-first prose as Dev. Schnell is step-distilled: its official Diffusers example uses four steps and guidance 0. A Comfy graph commonly represents no traditional CFG with sampler CFG 1; retain the model's schedule. Do not compensate for weak prompting by raising it to a Dev-length run. Confirm the LoRA was trained for the intended variant. [Model card](https://huggingface.co/black-forest-labs/FLUX.1-schnell).

## FLUX Kontext / Fill / Redux

Choose the actual editing/conditioning path, not merely the FLUX family. Kontext: give a concrete change and preservation instruction, such as `Replace the blue apron with a green apron. Preserve the robot's shape, face, pose and the workshop.` Fill: specify the masked region's desired content and check mask polarity in the graph. Redux supplies visual conditioning; it is not an interchangeable text encoder. Keep input references consistent. Use each official graph's settings; MCP cannot upload those inputs. [Comfy examples](https://comfyanonymous.github.io/ComfyUI_examples/flux/).

## FLUX.2 Dev / Klein

Use descriptive prose, explicit object relationships and exact quoted text. For edits, refer to input images by their actual positions and identify what changes versus what stays. Do not add reference-image syntax without supplied images.

Klein Base and step-distilled Klein are different weights. The official Klein Base 4B Diffusers example uses 1024 square, 50 steps and guidance 4; do not copy a four-step distilled preset into Base or assume 9B uses the 4B encoder. FLUX.2 Dev uses its own encoder/VAE and workflow, not FLUX.1's component stack. Resolve later FLUX releases through their own model card rather than applying this profile by name similarity. [Klein Base](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B), [BFL variant-aware reference](https://docs.bfl.ai/guides/prompting_unified_reference).

## Chroma1 Base

Use natural descriptions and, when supported by the matching graph, a targeted negative prompt. Its FLUX ancestry does not make FLUX Dev's guidance-embedding recipe interchangeable. Check the actual CFG/sampling nodes, T5 and VAE in the official example. Start from those settings and vary LoRA strength or prompt separately. Chroma1-Radiance and Zeta-Chroma use different pixel-space architectures; do not load them through this latent Chroma profile. [Comfy example](https://comfyanonymous.github.io/ComfyUI_examples/chroma/).

## Qwen-Image / versioned Qwen-Image checkpoints

Use clear natural-language layout and typography instructions. Example: `A small orange robot stands beside a cream shop sign. The sign reads "RADIO REPAIR" in two centered lines of dark blue block lettering. The robot is to the right of the sign. Soft daylight, straight-on view.` Quote exact text and specify position, language and line breaks when relevant; more quality adjectives do not fix a contradictory layout.

The original Qwen-Image Diffusers example uses 50 steps, `true_cfg_scale=4`, and native aspect buckets such as 1328 square or 1664 × 928. Its guidance requires a negative conditioning branch; an empty/blank negative can be used when there is nothing specific to exclude. Do not substitute the separate `guidance_scale` field for `true_cfg_scale`. Versioned Qwen checkpoints, Lightning LoRAs and Qwen-Image 2.x need their own graph/card. [Original card](https://huggingface.co/Qwen/Qwen-Image), [pipeline fields](https://huggingface.co/docs/diffusers/api/pipelines/qwenimage).

## Qwen-Image-Edit / Edit Plus variants

Give an instruction about the supplied image: `Keep the orange robot and its pose unchanged. Replace the cluttered background with a plain pale grey studio backdrop. Retain the same lighting direction.` For multi-image editing, assign each reference a specific role. Avoid rewriting every visible detail and accidentally changing it. Distinguish original Edit, 2509/2511 and later versions; matching image preprocessing and encoder paths matter. Use the selected edit workflow's settings. Ordinary img2img denoise advice is not automatically equivalent to this model's conditioning. [Official project](https://github.com/QwenLM/Qwen-Image).

## Z-Image Base / Turbo / De-Turbo

Use specific natural-language scene descriptions, including spatial relationships and quoted text. Example: `A compact orange robot places a brass dial on a wooden table. Its gripper is open above the dial. Side-lit close-up, warm wood and matte enamel.` Verify the variant: the official Turbo Diffusers example uses nine schedule points (eight transformer evaluations) and guidance 0 at 1024 square. A Comfy eight-step schedule can encode that differently. Base and De-Turbo use different sampling/training recipes; do not apply the no-CFG Turbo rule to all of them. Match the Qwen encoder and AE. [Turbo card](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo).

## Anima Base / Aesthetic / Turbo

For Base, use lowercase illustration tags with spaces, natural captions or a deliberate mixture. Example content: `small orange robot, workbench, soldering iron, side view, warm lighting, cel shading`. Use the exact version's recommended quality vocabulary when needed. Base supports quality/score tags; Aesthetic discourages score tags, so do not prepend the same quality block to both.

The card recommends 30–50 steps and CFG 4–5 for full models, with several valid samplers. Turbo instead uses CFG 1 and 8–12 steps. Preserve the provided schedule. Its Qwen3 encoder and Qwen-Image VAE are not an SDXL stack. Train on Base; keep original Kohya checkpoints and let ControlPilot prepare separate Comfy copies where conversion is needed. [Publisher's version, prompting and settings guide](https://huggingface.co/circlestone-labs/Anima).

## Lumina-Image 2.0

Use natural-language composition, action, material and lighting. Example: `An orange enamel robot studies a broken radio at a tidy desk. The brass dial lies beside its left hand, and daylight makes a soft reflection across its curved head.` Use the intended Gemma encoder and FLUX AE. Preserve the workflow's system prompt and flow shift; do not manually duplicate an internal prompt wrapper in the user's prompt field.

The official Diffusers example uses 50 steps and guidance 4. ControlPilot's comparison graph uses its separately defined 25-step, CFG-4, res_multistep/simple workflow with shift 6. Report which recipe is used rather than claim these are the same schedule. [Publisher](https://github.com/Alpha-VLLM/Lumina-Image-2.0).

## HunyuanImage 2.1 / 3.0

For 2.1, use detailed but coherent prose and quote lettering precisely. Specify object counts and spatial relations rather than tag padding. Match the Qwen2.5-VL/byT5 encoders and dedicated VAE. The official 2.1 full example uses 50 steps/guidance 3.5; distilled uses eight/3.25 with a different shift. These do not overwrite ControlPilot's fixed comparison workflow, which uses 2048 square, 20 steps and CFG 3.5.

Keep 2.1 original LoRAs for training; use converted Comfy copies for inference when required. HunyuanImage 3.0 is a different model/component stack, and HunyuanVideo is a video family. For 3.0, load its own official prompt/inference example before choosing numerical settings. [2.1 publisher](https://github.com/Tencent-Hunyuan/HunyuanImage-2.1), [Comfy components](https://comfyanonymous.github.io/ComfyUI_examples/hunyuan_image/).

## HiDream I1 Full / Dev / Fast and E1 editing

Use descriptive prose about the scene and relationships. Full, Dev and Fast have different step/guidance recipes; the Full pipeline defaults are 50 steps and guidance 5. Check the publisher's selected variant rather than sharing one preset. Its multiple encoders and AE are part of the workflow, not optional SDXL extras. E1 is an edit path: describe the intended change and preserved content with actual image input. Do not infer that an inference variant is trainable because Full training is supported. [Publisher](https://github.com/HiDream-ai/HiDream-I1), [pipeline](https://huggingface.co/docs/diffusers/api/pipelines/hidream), [Comfy examples](https://comfyanonymous.github.io/ComfyUI_examples/hidream/).

## PixArt Alpha / Sigma

Use concise natural descriptions with subject, relation, environment and style. Confirm Alpha versus Sigma, resolution-specific checkpoint, T5 and VAE before choosing settings. Use the exact pipeline example's schedule and supported canvas; do not copy SDXL sampler or LoRA targets because the image dimensions look familiar. [Sigma pipeline](https://huggingface.co/docs/diffusers/api/pipelines/pixart_sigma).

## AuraFlow

Use a coherent caption describing visible content and relationships. Match the AuraFlow checkpoint, encoder and VAE, then retain its flow scheduler and native canvas. Its flow-shift configuration does not make a Lumina workflow interchangeable. Prefer the selected version's pipeline defaults over a made-up universal CFG/steps preset. [Pipeline](https://huggingface.co/docs/diffusers/api/pipelines/aura_flow).

## Sana

Use clear scene descriptions and the selected Sana checkpoint's prompt template/encoder. Confirm full versus Sprint/distilled variants and native image size; guidance and step count change with the variant. Keep its DC-AE and scheduler rather than substituting an SDXL VAE. Use the official example for the exact weights. [Pipeline](https://huggingface.co/docs/diffusers/api/pipelines/sana).

## OmniGen / OmniGen2

For text-only generation, describe the scene and object relationships. For reference generation, identify which supplied image provides each character, object or style: for example, place the robot from the first reference in the workshop from the second while preserving the robot's design. Use the selected pipeline's actual image-reference syntax; prose referring to an unsupplied image is not conditioning. OmniGen and OmniGen2 are different pipelines. OmniGen2 can expose separate text/image guidance controls; tune them independently using its official defaults. [Publisher](https://github.com/VectorSpaceLab/OmniGen2).

## Kolors

Use natural Chinese or English descriptions with explicit composition, lighting and lettering. Preserve the user's language; do not translate a requested sign as an optimization. Match the ChatGLM-based text encoder and its pipeline rather than treating the model as a standard two-CLIP SDXL checkpoint. Keep the official workflow's resolution and sampling recipe before testing LoRA strength. [Publisher and inference examples](https://github.com/Kwai-Kolors/Kolors).

## CogView4

Use a natural caption describing subject, relationships, lighting and exact text in the intended language. Chinese and English typography should be assessed in generated output, not assumed correct. The official CogView4-6B example uses 1024 square, 50 steps and guidance 3.5; keep those field semantics in its dedicated pipeline. Do not substitute a CogVideo workflow or a generic SDXL text encoder. [Publisher card](https://huggingface.co/zai-org/CogView4-6B).

## Ideogram 4

For layouts or posters, specify exact quoted text, its order/position, typography, foreground subject and background separately. Example: `A cream repair-shop poster. "RADIO REPAIR" is centered at the top in dark blue block lettering. Below the title, a small orange robot holds a brass dial. Wide clean margins, flat printed colors.` Typography and layout instructions still need visual verification. Use the actual Ideogram 4 Qwen3-VL encoder, main and unconditional model components when required by the graph; the unconditional model is not a second user prompt. Keep the Comfy repack's own workflow and supported precision rather than importing SDXL CFG assumptions. [Official Comfy packaging and workflows](https://huggingface.co/Comfy-Org/Ideogram-4).

## Other catalogued image families

For ERNIE-Image, Nucleus, PRX Pixel, Krea, Lens, PixelDiT and other newer families, resolve the exact publisher card and a compatible installed workflow before prescribing numbers. Natural descriptive prompts are a starting strategy, not proof of identical conditioning. For reference/edit models, bind each reference to its actual role. For pixel-space models, verify whether a VAE is needed at all. For specialized upscalers, distinguish the input image and upscale recipe from text-to-image generation. Do not turn a current catalog name into an unsupported MCP tool or reuse a similarly named architecture's LoRA.

If a family is absent here, use the model's own card and official sample graph, record the source/revision, and describe the proposed test. Never silently substitute another model. Catalog presence, trainer support and inference support remain separate checks.


## New AI Toolkit image families

The following starting points come from [AI Toolkit 0.13.43’s pinned UI presets](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/diffusion_models/ui.tsx), not from a verified GPU run. They are AI Toolkit sample settings; keep an installed ComfyUI workflow’s own schedule and field names. The existing MCP comparison cannot execute these families. Obtain the matching workflow or provide a concrete UI handoff.

### Qwen-Image 2.1 and Turbo

Use connected descriptions of subject, layout, materials, lighting and exact quoted text. For editing, identify the supplied reference image and the specific change to make. Example: `Replace the sign in the robot’s right hand with a cream card reading "REPAIRS". Keep the robot, pose and workshop unchanged.` Use `qwen_image_2` for Base, or the Turbo preset with `model_kwargs.turbo: true`; do not treat the older Qwen-Image encoder/VAE as interchangeable. Both use Qwen3-VL-8B and an RGBA VAE. Enable alpha only when the task needs transparent output and the whole pipeline preserves it.

The Base UI starts with guidance scale 3; use the installed Base schedule. Turbo has a fixed eight-step schedule at guidance 1. Turbo training requires `qwen_image_2_turbo_training_adapter_v1`, active during training and disabled for sampling. Do not leave the training adapter in an inference stack by habit. [Weights](https://huggingface.co/Comfy-Org/Qwen-Image-2.1).

### Ming-Image 0.1 Design

Specify layout and text as design instructions: `A cream repair-shop poster. Center an orange robot above the large title "RADIO REPAIR". Small dark-blue lettering below reads "OPEN DAILY". Flat screen-print texture, generous margins.` Describe transparent areas explicitly only when using RGBA mode. The preset uses Ling Mini 2.0, the Ming RGBA VAE, 12 steps and guidance 1. Training uses `ming_image_01_design_training_adapter_v1`; sampling removes it. The pinned UI exposes generation; backend editing support does not imply a working editing preset or MCP input upload. [Weights](https://huggingface.co/Comfy-Org/Ming-Image).

### FLUX.3 Image Klein Base

Use scene-first prose with clear spatial relationships and quoted lettering. For edits, state what changes and what stays, referring only to images actually supplied. The AI Toolkit Base sample uses 1024 × 1024, 28 steps, flowmatch and guidance 3.5. This is a traditional CFG field in this implementation, not FLUX.1’s separate FluxGuidance recipe. Use Qwen3-VL-4B and the FLUX.2 VAE. Step-distilled FLUX.3 is a separate inference variant and must not replace Base for training.

The catalog retains the publisher’s actual `flux3-image-klein-base-*.safetensors` names. Set `model.name_or_path` to the selected local DiT file because the pinned AI Toolkit resolver still advertises underscore filenames. The gate applies to the BFL repository; a token does not replace accepting its license. [Publisher package](https://huggingface.co/black-forest-labs/flux-3-image-klein-base), [Comfy repack](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy).

### MOSS-Image Base and SFT

Describe visible content and relationships; retain the exact Base or SFT choice when evaluating a LoRA. Both AI Toolkit presets use 1024 × 1024, 30 flowmatch steps and guidance 3, with DiT block 22 skipped on the unconditional branch. Preserve that `uncond_skip_layers: [22]` behavior and exclude `layers.22.` from LoRA training rather than copying the number into an unrelated CFG node. Use Qwen3.5-9B and the small FLUX.2 VAE.

Editing uses the separate experimental edit preset and reference/target pairs. In ComfyUI, edit LoRAs need [ComfyUI-MOSS-Image-Ostris-Edit](https://github.com/ostris/ComfyUI-MOSS-Image-Ostris-Edit); catalog downloads do not install that extension. Do not claim it is bundled. [Weights](https://huggingface.co/Comfy-Org/MOSS-Image).

### Fibo 2.0 Dev

Write descriptive prose with explicit subjects, object relationships and changes for any supplied editing references. Use multiline prompts only when their structure serves the requested image. The Dev sample preset uses 1024 × 1024, 30 flowmatch steps and guidance 5 against its model-specific null caption. Do not replace that unconditional conditioning with an SDXL negative-tag list. Use Qwen3-VL-4B and the FLUX.2 VAE; Turbo is a different variant. [Weights](https://huggingface.co/Comfy-Org/Fibo-2.0).

### Iris-3B

Use concrete scene descriptions rather than guessed tag syntax. Example: `An orange robot examines a tiny brass gear through a magnifying glass. Close side view, pale workbench, soft morning light.` The AI Toolkit sample starts at 30 steps and guidance 3; use the checkpoint’s supported canvas and scheduler. This is a pixel-space model with Qwen3-VL-4B, so do not add a VAE or diagnose missing VAE weights. The catalog Base directory includes `config.yaml`; keep it beside `model.safetensors`. Do not substitute the Iris Turbo checkpoint. [Publisher](https://huggingface.co/speridlabs/iris-3b).

### Pruna P-H3-Image

Use image-specific prose about the subject, composition and requested edits. For actual multiple references, the pinned backend uses `<Picture 1>`, `<Picture 2>` and so on; keep numbering aligned with supplied images. It is an eight-step, guidance-1 image model with its own image encoder and VAE, not a MiniMax video preset. The AI Toolkit sample starts at 2048 × 2048; upstream notes prefer higher native-area output, so do not promise equivalent quality at SDXL resolutions. Training uses `p_h3_image_training_adapter_v1` and sampling disables it. [Weights](https://huggingface.co/PrunaAI/P-H3-Image-Comfy).

### MiniMax H3 Image

Describe a still image and its spatial relationships; use the same ordered `<Picture N>` references only when the editing backend receives those images. Omit video/audio scene fields. This model is distilled to six steps with guidance 1. The AI Toolkit sample starts at 2048 × 2048 and uses the shared H3 Qwen3-VL-32B encoder, its dedicated image VAE and `minimax_h3_image_training_adapter_v1` for training only. Its latent format is not the H3 video VAE’s. Do not assume that installing the existing H3 video workflow provides an image graph. [Weights](https://huggingface.co/Comfy-Org/MiniMax-H3-Image).
