# Inference settings and controlled evaluation

Use this alongside the exact image/video model profile. Values below are starting points for experiments, not measured guarantees. The connected MCP tool schema determines what can actually be applied.

## Produce a concrete recipe

Identify the checkpoint revision and Base/Dev/Turbo/Edit variant, LoRA and trigger, task (T2I, I2I, edit, T2V or I2V), backend/workflow, desired aspect ratio, and known hardware. Do not ask for every field when the existing context already answers it. Use `models_list` and `run_get` to establish what they can, then state any missing compatibility information.

Return the usable positive prompt, negative prompt only when the model/workflow supports it, width × height or the native resolution bucket, steps, sampler and scheduler (if known for that backend), guidance with its exact field/node, seed, LoRA model/encoder strength, and denoise or reference strength when relevant. Video recipes also need frames, FPS, duration, temporal/spatial constraints and audio behavior. Identify the source of each nontrivial default as an upstream example, bundled workflow or proposed experiment. Do not fill unknown fields with confident guesses.

Label every result **recommended**, **planned**, **submitted** or **verified from output**. The current LoRA Pilot MCP can set comparison prompt, seed and LoRA strength; it cannot apply arbitrary settings, edit a ComfyUI graph, upload reference images or render general image/video jobs. For those, provide the exact UI/workflow changes. A separate inference connector is an independent, user-authorized route, not an automatic fallback.

## Keep guidance controls distinct

Traditional CFG compares conditional and unconditional predictions. Increasing it may improve adherence while increasing saturation, halos or rigidity. It is not the same parameter as a model's embedded/distilled guidance input. For FLUX.1 Dev, ComfyUI sampler CFG 1 plus `FluxGuidance` around 3.5 is a different configuration from sampler CFG 3.5. FLUX Schnell's Diffusers guidance 0 and ComfyUI CFG 1 both commonly mean no traditional CFG, but numbers must not be copied between fields without checking the graph.

Qwen's `true_cfg_scale` controls traditional CFG; the pipeline's `guidance_scale` field is not a replacement for it on the original undistilled Qwen-Image. HunyuanImage pipelines can expose distilled guidance separately. Turbo/Lightning/LCM LoRAs may require a specific schedule and CFG. Record the named field and the exact variant instead of saying just “guidance 4.”

Sampler names, sigma schedules, flow shifts and prediction types belong to a particular workflow implementation. A Diffusers example does not automatically translate to a ComfyUI scheduler label. Keep the provided workflow schedule when unsure, and verify changes against the model's own example. Adding steps to a distilled checkpoint does not automatically improve it.

## Evaluate a LoRA

Preserve the original trained checkpoint and identify its base architecture. Keep prompts, seed, canvas, sampler, scheduler, steps, VAE and encoder identical across baseline and LoRA images. Include the trigger in the shared prompt. Label checkpoint names and epoch/step order, and keep final named checkpoints distinct from numbered epochs.

Start at the trained workflow's normal strength. If unknown, suggest a small authorized sweep such as 0.5, 0.75 and 1.0, including a baseline. This is an experimental suggestion, not a universally optimal scale. Model and text-encoder strength can have different effects; keep them separate when exposed. Do not add text-encoder influence to a model-only LoRA by assumption.

Use one ordinary prompt to test the learned concept, one change of pose/environment, and one test of flexibility relevant to the user's goal. A style LoRA should transfer across content; an identity LoRA should retain identity while permitting intended changes. Compare a few fixed seeds before concluding that a checkpoint is better. Observe actual images for likeness, composition, artifacts and unwanted training-background/clothing leakage. Loss curves and checkpoint file size cannot establish these qualities.

## Diagnose one variable at a time

| Observed issue | First useful experiment |
|---|---|
| Prompt ignored | Verify exact checkpoint, encoder, workflow and trigger before increasing guidance; simplify contradictory clauses. |
| Weak LoRA effect | Verify parent model and loaded LoRA; test the trigger and a modest strength increase on an unchanged seed. |
| Subject stuck in training clothing/background | Review captions and sample variety in TagPilot; compare an earlier checkpoint or lower strength. This is a hypothesis until images are inspected. |
| Saturation, halos, harsh texture | Reduce traditional CFG or LoRA strength separately; do not alter both and lose the explanation. |
| Soft/incomplete image | Verify step-distilled versus full model and schedule, VAE and denoise range; more steps help only after that match. |
| Bad anatomy or count | Simplify spatial/action constraints, try another controlled seed, then consider a supported pose/reference workflow. Negative-tag lists are not anatomy repair. |
| I2I ignores reference | Confirm the actual conditioning path; reduce denoise only for an img2img latent-noising workflow. Edit-model image guidance may be different. |
| I2V restates a still image | Describe a feasible action and camera motion from the visible starting state; preserve identity rather than reprompting appearance. |
| OOM | Reduce batch first; use the model's supported canvas/frames, tiling or offloading. Measure the actual GPU; do not stop an unrelated job or change precision automatically. |
| Video flicker or identity drift | Reduce competing actions, camera changes and clip duration; test supported reference conditioning. Frame interpolation does not fix incorrect identity. |

Lower precision can reduce memory but has hardware/loader constraints and may affect output. CPU offloading trades GPU memory for host RAM and transfer time. VAE tiling is not equivalent to reducing denoiser memory. Keep ComfyUI and training concurrency consistent with available memory and user intent.

## When results are not visible

Ask for the generated image/video and its settings, or use an explicitly authorized artifact path. Do not claim to see samples through an MCP run summary. State which facts came from tools and which recommendations remain untested. End with the next controlled change, rather than a large random sweep that spends the user's GPU budget.
