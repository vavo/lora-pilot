# Video and audio prompting

Sources checked 2026-11-22. General video/audio generation is not exposed by the current LoRA Pilot MCP. Use this reference to recommend prompts/settings and prepare a supported ComfyUI handoff. Bundled workflow presence does not prove model weights, hardware capacity or a successful render.

## Shared shot design

Identify the exact model and T2V, I2V, reference-video or audio/video task. Describe a feasible visible starting state, one main action, its development and the end state. Keep camera movement independent from subject movement. Specify shot scale, camera direction, lighting and materials. For an I2V input, preserve the existing appearance and composition and describe what moves next; do not replace the reference with a conflicting scene.

Give duration, FPS, resolution/aspect bucket and supported frame count separately from the prose. Frame count and playback FPS determine duration; changing the export FPS is not a request for more generated motion. Keep each model's spatial/temporal divisibility rules and official schedule. Do not infer them from a different video family. Test a short supported clip before increasing duration/resolution within the user's budget.

For speech-capable models, preserve exact user-provided dialogue, identify speaker and language, and describe ambience/music separately. For silent models, put audio in a separate production handoff rather than promising it from the render. A completed operation or playable file is not human review of motion or synchronization.

## Wan 2.1

Use a concrete sequence: `A small orange robot sits at a workbench. It lifts a brass radio dial, turns it once and places it beside the radio. The camera makes a slow push toward its hands. Warm afternoon light, consistent workshop background.` For I2V, describe that action from the supplied first frame instead of reintroducing a new character.

Confirm T2V versus I2V, 1.3B versus 14B, and the checkpoint's 480p/720p path. Match UMT5 and the correct VAE, canvas and flow shift. Keep the official graph's steps, CFG and sampler; acceleration LoRAs require their own settings. Negative conditioning can help target observed artifacts, but does not repair an impossible action. Do not claim native synchronized speech from the ordinary Wan2.1 video graph. [Publisher](https://github.com/Wan-Video/Wan2.1).

## Wan 2.2

Use the same coherent action language, with explicit subject count, motion direction and camera path. Confirm the actual T2V-A14B, I2V-A14B, TI2V-5B, Animate or other specialized task. A14B workflows coordinate high-noise and low-noise experts; keep their sampling boundary and matching LoRA paths rather than loading only one expert. TI2V-5B has its own VAE/workflow and is not a smaller drop-in A14B file. For Animate, distinguish motion/character inputs from a plain first frame. Use the exact official workflow's defaults, especially with Lightning or other distillation. [Publisher and task examples](https://github.com/Wan-Video/Wan2.2).

## HunyuanVideo / HunyuanVideo 1.5

Use sentences that describe subject, environment, action progression and camera movement. Avoid a long bag of photographic tags that gives no motion. For example, describe the robot reaching for a part, the gripper closing and the part moving upward, rather than simply asking for “dynamic cinematic movement.”

Choose original HunyuanVideo versus 1.5 and its actual T2V/I2V checkpoint. Keep its encoder, VAE, guidance and frame schedule; a distilled-guidance node is not an ordinary CFG slider. Original and newer versions have different hardware and task paths. Neither name establishes the availability of audio. [Original implementation](https://github.com/Tencent-Hunyuan/HunyuanVideo), [1.5 implementation](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5).

## LTX-Video 0.9.x

Describe visible action and a short continuous camera path in natural prose. Treat legacy LTX-Video as separate from LTX-2 and 2.5. Keep the model-specific resolution and frame-count constraints and its own distilled/full schedule. Do not introduce an LTX-2 audio VAE or a 2.5 prompt/encoder workflow merely because the family name overlaps. [Publisher](https://github.com/Lightricks/LTX-Video).

## LTX-2 / LTX-2.5

For a single shot, write a flowing present-tense paragraph linking shot scale, setting, subject action, camera motion and sound. Example: `A medium close-up frames a small orange robot repairing a radio at a wooden workbench. It turns a brass dial, pauses and tilts its head toward the speaker. The camera slowly pushes closer as warm window light glides across its scratched enamel. A quiet electrical crackle gives way to soft radio music; the workshop remains otherwise still.` Use exact quoted dialogue only when requested, with one clearly identified voice at a time.

I2V should continue the visible starting state. Explicit multi-shot timing is useful only when that model/workflow supports it and the user wants cuts; do not force a continuous action into a shot list. Preserve consistent identities and lighting across cuts. The 2.5 card's distilled checkpoint uses a fixed eight-step schedule and CFG 1; Dev and distillation-LoRA pipelines are different recipes. Match the actual encoder, video/audio VAEs, upscalers and any patches expected by the selected graph. Check the bundled T2V/I2V workflow for exact dimensions, FPS and frames rather than inventing a common video preset.

The public LTX API may offer features that the installed open-weight graph does not. Do not imply duration prediction, speech replacement or a hosted prompt enhancer is present in LoRA Pilot merely because the online guide describes it. [Prompting guide](https://docs.ltx.io/api-documentation/implementation-guides/prompting-guide), [2.5 model and weight variants](https://huggingface.co/Lightricks/LTX-2.5).

## MiniMax H3 Base / reference / accelerated variants

Identify H3-Base versus reference/context or accelerated weights first. The publisher's Base guide separates a shot/action timeline, the overall ambient sound and non-diegetic music. A task-appropriate starting structure is:

```text
integrated_multimodal_description: [Shot 1] A medium shot frames an orange robot at a radio workbench. It presses the power switch and watches the tuning light glow. The camera slowly pushes toward the radio.
overall_soundscape: A soft switch click, a brief electrical crackle and a quiet workshop room tone.
non_diegetic_music: No background score.
```

For a keyframe task, use the publisher's task-specific first/last-frame alignment form only for references actually supplied. Reference-to-video/audio uses a separate guide and reference identity rules. Preserve exact dialogue and use the official speaker/delivery markup when dialogue is part of the request; consult the guide rather than inventing tags. Do not paste LTX's prose template into H3 without adapting it.

Use the bundled H3 T2V/I2V graph's separate video/audio settings and conditioning. Faster H3/FastH3/LoRA variants can change the schedule and supported tasks; do not assign all of them a generic 20- or 50-step recipe. A high-resolution regeneration stage is separate from the initial generation and must fit the authorized budget. [Model overview](https://huggingface.co/MiniMaxAI/MiniMax-H3), [Base prompting](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md), [Reference prompting](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md).

## Cosmos, CogVideoX and other video families

For Cosmos Text2World versus Video2World, identify whether text alone or actual visual conditioning is required. Describe physically coherent events and camera trajectories, then use the checkpoint's own official example. CogVideoX likewise has separate generation/editing/I2V paths. Do not reuse Wan's experts, temporal constraints or guidance values. Consult the exact publisher card before prescribing numbers for a family without an installed known workflow. A training-model inventory does not imply a bundled inference pipeline. [Cosmos](https://github.com/NVIDIA/Cosmos), [CogVideo](https://github.com/THUDM/CogVideo).

## Audio-only work: ACE-Step and similar models

Establish exact Base/XL/accelerated model and the requested task. Separate music style/instruments/tempo/structure from lyrics, language and vocal delivery. Preserve the user's lyrics and distinguish instrumental from vocal output. Use duration and the model's own conditioning fields instead of video resolution or image CFG defaults. The LoRA Pilot MCP currently has no audio-generation or audio-training tool; provide a trainer/inference handoff after checking that stack's documented support. Never turn a request for a music LoRA into the fixed SDXL training recipe.


## FastH3 Omni and 8-Step V2

Both are distilled H3 video/audio variants; preserve H3’s multimodal prompt structure while matching the exact task. The [pinned AI Toolkit presets](https://github.com/ostris/ai-toolkit/blob/73c84b091dd0f5647fc6a4b59122a2efc1c8147b/extensions_built_in/diffusion_models/ui.tsx) use eight-step sampling and guidance 1. Keep the model’s trained schedule rather than adding steps as a generic quality setting. They share H3’s text encoder, video VAE and audio VAE but require their own DiTs and matching training adapters, disabled during sampling.

[FastH3 8-Step V2](https://huggingface.co/FastVideo/FastVideo-FastH3-Comfy) supports text-to-video/audio only, without first-frame or reference conditioning. The pinned implementation uses 24 fps and snaps frame counts down to the `17n+5` grid. [FastH3 Omni](https://huggingface.co/FastVideo/FastH3-Omni-Comfy) is reference-to-video/audio and has its own attention/conditioning path. Do not assign V2’s restrictions or the old Preview v0.2 VSA setup to Omni. The bundled MiniMax H3 graphs remain base-model graphs; they are not automatically converted FastH3 workflows.

## YuE2 audio

Separate style/instrumentation/tempo from lyrics and vocal delivery. Example style: `warm indie folk, fingerpicked acoustic guitar, brushed drums, intimate solo vocal, relaxed 90 BPM`; keep lyrics in the model’s lyrics field. Preserve the requested language and distinguish instrumental from vocal output. YuE2 uses its own tags/lyrics and optional ABC-score protocol, not ACE-Step’s fields or image guidance values. Discover the exact audio preset before prescribing durations or generation settings.

The pinned trainer expects the [Comfy YuE2 checkpoint](https://huggingface.co/Comfy-Org/YuE2), which embeds the text tokenizer and audio VAE. Training audio conditioning uses [MERT-v2-FullSong](https://huggingface.co/m-a-p/MERT-v2-FullSong) with the [community v4 semantic head/NAR adapter](https://huggingface.co/Mothersuperior/yue2-mothersuperior-realaudio-tokenizer-v4). SheetSage adds score conditioning; optional separation modes need further assets. A catalog download is not proof the trainer’s Hugging Face cache is populated. Do not label the raw vendor checkpoint as a drop-in replacement, imply the community tokenizer is the unreleased official tokenizer, or attempt YuE2 through MCP’s fixed image-training/comparison tools.
