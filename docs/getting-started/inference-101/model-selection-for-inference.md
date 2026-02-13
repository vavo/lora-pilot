# Model Selection for Inference

Picking the wrong model setup is the fastest way to waste GPU time.

## Minimal Model Setup

1. **Checkpoint** (base model)
2. **LoRA** (optional, targeted behavior)
3. **VAE** (optional, improves final decoding quality)

## Selection Rules

- Start with one known-good checkpoint per style family.
- Add one LoRA at a time.
- Keep LoRA weights conservative first (for example, 0.6-0.9).
- Use a matching VAE only if outputs look washed out or distorted.

## Common Mistakes

- Using multiple LoRAs before testing one by one
- Mixing incompatible model families
- Setting LoRA weight too high too early

## Starter Recipe

- Checkpoint: one reliable SDXL checkpoint
- LoRA: one subject/style LoRA (optional)
- LoRA weight: 0.75
- Use one saved starter setting profile for steps, guidance, and sampler

## Next

Continue to [Core Generation Settings](core-generation-settings.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

