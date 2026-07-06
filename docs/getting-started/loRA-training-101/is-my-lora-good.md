# Is My LoRA Good?

_Last updated: 2026-07-06_

A LoRA is good when it gives you the trained idea on demand without crushing the prompt around it. It should show up when you ask for it, stay flexible when you change scene or pose, and disappear when you lower the strength or remove the trigger.

The final checkpoint is not automatically the winner. A middle checkpoint often works better because it learned the idea before it memorized the dataset. Conveniently annoying, like most training lessons.

## The Five-Prompt Test

Load the same base model you trained against. Keep the seed, sampler, resolution, CFG or guidance, and LoRA strength fixed. Then test the same LoRA checkpoint with five prompts:

1. **Easy prompt**: the trigger word plus a plain subject description.
2. **Dataset-near prompt**: a scene close to your training images.
3. **New pose or angle**: a pose, crop, or camera view missing from the dataset.
4. **New context**: different clothing, background, lighting, or material.
5. **Low-activation prompt**: a prompt where the LoRA should have little effect.

Save the outputs in MediaPilot or another gallery where you can compare them side by side. Do not judge from a single favorite image. One lucky render is not a model evaluation; it is a screenshot with confidence.

> **Why does this work?** The easy prompt checks activation. The dataset-near prompt checks whether training succeeded. The new pose and context prompts check flexibility. The low-activation prompt checks whether the LoRA leaks into images where it does not belong.

> **Try this variation:** Test three saved checkpoints with the same five prompts. Keep everything else fixed. Pick the checkpoint that survives the new pose and new context prompts, even if a later checkpoint makes one dataset-near prompt look sharper.

## Strength Sweep

After the five-prompt test, run a small strength sweep on the best checkpoint: `0.5`, `0.7`, `0.9`, and `1.0`.

A useful LoRA often appears around `0.6` to `0.9`, though training style and model family can move that range. If the concept only works at `1.2` or higher, the LoRA may be undertrained, badly captioned, or paired with the wrong base model. If the LoRA overwhelms every prompt at `0.7`, it may be overfit or too rigid.

ComfyUI workflows may expose `strength_model` and `strength_clip` separately. Keep them equal for the first pass. Split them only when you are testing activation versus visual pressure on purpose.

## Overfit, Underfit, or Useful?

| Symptom | Likely Problem | First Fix |
|---|---|---|
| Copies the same pose, face angle, outfit, or background | Overfit | Test an earlier checkpoint, then reduce steps or improve dataset variety |
| Ignores the trigger word or barely changes the image | Underfit | Check base-model compatibility, captions, trigger usage, and training exposure |
| Looks correct only at very high strength | Weak activation | Improve captions, train longer, or test rank/learning-rate changes |
| Destroys anatomy, texture, or composition | Too strong or overfit | Lower strength, test earlier checkpoints, or reduce training pressure |
| Works in dataset-like prompts but fails in new contexts | Memorized examples | Add pose, lighting, crop, and background variety |

## Compare Against the Base Model

Run one prompt without the LoRA, then run it again with the LoRA. Beginners skip this because the LoRA result feels obvious. The comparison shows whether the LoRA added the intended idea or whether the base model already handled most of it.

For character and product LoRAs, compare identity and flexibility. For style LoRAs, compare how much the style changes subjects that were not in the dataset. For concept LoRAs, compare whether the concept stays recognizable when the surrounding scene changes.

## Keep the Evidence

Save the checkpoint filename, base model, trigger word, LoRA strength, prompt, seed, sampler, guidance, resolution, and representative output grid. If the LoRA is worth keeping, it is worth documenting.

Continue with [Training Workflows](training-workflows.md) if you are still running experiments, or [Model Selection for Inference](../inference-101/model-selection-for-inference.md) if the LoRA works but behaves strangely in generation.
