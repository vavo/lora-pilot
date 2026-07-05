# Core Generation Settings

_Last updated: 2026-07-05_

These settings control most of your output behavior.

## Steps

- More steps can improve detail, but with diminishing returns.
- Safe starter range: **20-35** for many SDXL workflows.
- If a model card recommends a different range, use that first. Modern distilled, turbo, LCM, and Flux-style workflows often need fewer steps than classic SD workflows.
- Raising steps is not a universal quality button. After the useful range, you mostly buy heat, time, and disappointment.

## CFG (Guidance Scale)

- Low CFG: more freedom, but the prompt may be followed less strictly.
- High CFG: stronger prompt following, but higher risk of distortions.
- Safe starter range: **4-7**.
- If faces, hands, or textures look harsh, lower CFG before rewriting the whole prompt.
- If the model barely follows the prompt, raise CFG in small increments.
- Some model families use separate guidance controls or lower CFG than SDXL. Check the workflow notes before copying generic settings.

## Sampler

- Sampler is the method used to build the image step by step.
- Pick one or two samplers and learn them first before switching often.
- Keep sampler and scheduler fixed while testing prompts, seeds, or LoRA weights.

## Seed

- Same seed = reproducible result pattern.
- New seed = variation without rewriting everything.
- Fix the seed while changing one setting.
- Randomize the seed when you want new compositions.
- Save the winning seed with the prompt and model names.

## Resolution

- Start with moderate resolution first.
- Upscale in later steps instead of forcing huge base resolution.
- Match the model family. SD 1.5 usually behaves best near 512-class sizes; SDXL is usually built around 1024-class sizes; newer families publish their own preferred dimensions.
- If VRAM fails, reduce width/height or batch size before changing models.

## Batch Size

- Keep batch size at 1 while learning a workflow.
- Increase batch size only after the workflow is stable and VRAM has headroom.
- If you hit CUDA out-of-memory, batch size is the first lever to pull.

## Practical Starter Settings

- Steps: 28
- CFG: 5.5
- Sampler: one stable default
- Seed: fixed during tuning
- Batch size: 1
- Resolution: model-appropriate starter size, then upscale

## Systematic Tuning

1. Pick a checkpoint and model-appropriate resolution.
2. Fix seed, sampler, scheduler, steps, CFG, and LoRA weights.
3. Change one variable.
4. Generate and compare.
5. Keep the image metadata or workflow JSON for every result worth revisiting.

## Next

Continue to [Inference Workflows](inference-workflows.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
