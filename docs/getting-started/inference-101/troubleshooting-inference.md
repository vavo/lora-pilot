# Troubleshooting Inference

## Common Symptoms and Fast Checks

### Output quality suddenly drops

- Confirm your model setup did not change (checkpoint, LoRA, VAE)
- Re-run a known-good seed and prompt
- Check whether guidance (CFG) or sampler was changed

### Distortions or broken anatomy

- Lower CFG (guidance strength)
- Reduce LoRA weight slightly
- Try a stable sampler from your saved starter settings

### Generation is too slow

- Reduce resolution for iteration stage
- Lower batch size
- Avoid unnecessary high steps

### Reproducibility is poor

- Fix seed
- Lock sampler and steps
- Save exact prompt and negative prompt

## Escalation Path

1. Reproduce with your saved starter settings
2. Change one variable only
3. Compare outputs side by side
4. Document the winning config

## Next

Continue to [Practical Inference Projects](practical-inference-projects.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
