# Core Generation Settings

These settings control most of your output behavior.

## Steps

- More steps can improve detail, but with diminishing returns.
- Safe starter range: **20-35** for many SDXL workflows.

## CFG (Guidance Scale)

- Low CFG: more freedom, but the prompt may be followed less strictly.
- High CFG: stronger prompt following, but higher risk of distortions.
- Safe starter range: **4-7**.

## Sampler

- Sampler is the method used to build the image step by step.
- Pick one or two samplers and learn them first before switching often.

## Seed

- Same seed = reproducible result pattern.
- New seed = variation without rewriting everything.

## Resolution

- Start with moderate resolution first.
- Upscale in later steps instead of forcing huge base resolution.

## Practical Starter Settings

- Steps: 28
- CFG: 5.5
- Sampler: one stable default
- Seed: fixed during tuning

## Next

Continue to [Inference Workflows](inference-workflows.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

