# Troubleshooting Inference

_Last updated: 2026-07-05_

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
- Use a faster sampler or a model variant designed for fewer steps
- Disable extra branches, upscalers, face/detailer passes, or ControlNet nodes until the base image is good

### Reproducibility is poor

- Fix seed
- Lock sampler and steps
- Save exact prompt and negative prompt
- Keep scheduler, denoise, model, VAE, LoRA weights, and resolution unchanged while comparing

### ComfyUI shows red missing-node blocks

- Open ComfyUI Manager and install missing custom nodes
- Restart ComfyUI after installation
- Reload the workflow
- If nodes stay red, read the ComfyUI terminal log for the failed import or dependency error

### ComfyUI says a model value is not in the list

- Find the loader node named in the error, often `CheckpointLoaderSimple`, `LoraLoader`, `VAELoader`, or an upscaler loader
- Select a model that exists in the dropdown and matches the workflow family
- Pull the missing model through LoRA Pilot model management when it exists in the manifest
- Restart or refresh ComfyUI after adding model files

### Output is black, gray, or washed out

- Confirm `VAEDecode` receives the intended VAE
- Check whether the checkpoint expects a separate VAE
- Use a VAE from the same model family
- Restart ComfyUI after changing model files

### CUDA out of memory

- Set batch size to 1
- Lower width and height
- Close other GPU-heavy jobs
- Prefer FP8 or quantized variants for large model families
- Restart ComfyUI after several failed heavy runs

## Escalation Path

1. Reproduce with your saved starter settings
2. Change one variable only
3. Compare outputs side by side
4. Check loader nodes for missing or wrong-family models
5. Check custom-node errors in ComfyUI Manager and service logs
6. Document the winning config

## Next

Continue to [Practical Inference Projects](practical-inference-projects.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
