# What is Inference?

Inference is the moment the model turns your prompt and settings into an image.

## Inference in One Sentence

- **Training** teaches a model.
- **Inference** uses a model.

## Basic Inputs

- **Prompt**: What you want.
- **Negative prompt**: What you do not want.
- **Checkpoint**: The base model that defines general style/quality.
- **LoRA**: Optional add-on model for specific style/character/concept.
- **Settings**:
  - **Steps**: How many refinement passes the model runs
  - **CFG**: How strongly the model follows your prompt
  - **Sampler**: The method used to draw the final image
  - **Seed**: Number controlling randomness (same seed = similar result)
  - **Resolution**: Output image size

## Basic Outputs

- One or more generated images
- Metadata (model + settings used)

## Why Beginners Struggle Here

- Too many knobs changed at once
- No stable starter setup
- Constantly switching models and settings

## Practical Rule

Change one thing at a time and keep one saved starter setup unchanged. If everything changes every run, you cannot learn what helped.

## Next

Continue to [Inference Stacks](inference-stacks.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

