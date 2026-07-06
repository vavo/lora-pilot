# Troubleshooting Training

_Last updated: 2026-07-06_

Training failures are easier to fix when you name the symptom first. Do not start by changing ten settings. Start by asking what failed: launch, memory, learning, flexibility, or output quality.

Use this page after one run has produced evidence: logs, sample images, checkpoint names, dataset notes, and the exact base model. Without evidence, troubleshooting becomes astrology with CUDA.

## Training Will Not Start

Training launch failures usually appear before progress begins. TrainPilot or Kohya exits early, AI Toolkit rejects the config, logs mention missing files or permissions, or progress stays at zero.

Check these first:

```bash
ls -la /workspace/datasets
ls -la /workspace/models
```

Then check the tool. In ControlPilot, confirm the service is running. In TrainPilot, confirm the selected dataset exists. In Kohya, confirm image and caption paths match the config. In AI Toolkit, confirm the model family and config format match.

Path problems are boring and common. Spaces, renamed folders, missing captions, and model files in the wrong category can look like deeper training failures. They are not deeper. They are typos with ambition.

## CUDA Out of Memory

Out-of-memory errors mean the run does not fit the GPU. Do not make this philosophical.

Use the cheap fixes first. Set batch size to `1`, enable gradient checkpointing, use the recommended mixed precision for the model family, lower training resolution, then lower rank. If the run still does not fit, use a smaller model or a larger GPU.

Restart the service or container if a previous failed run left memory occupied. In ControlPilot, use the service controls before assuming the whole machine needs ritual cleansing.

> **Why does this work?** Batch size, resolution, model size, rank, optimizer state, and precision all affect VRAM. Batch size is the safest first lever because it changes memory use without changing the dataset.

## The LoRA Does Nothing

The dead-LoRA symptom is easy to spot: the trigger word has little effect, samples look like the base model, or LoRA strength must be very high before anything changes.

Check the boring causes first. The LoRA must be trained for the same base family you are using. The trigger word must appear in captions and prompts. Captions need to describe the concept. The run needs enough exposure. Rank cannot be too low for the concept. The LoRA file must be loaded in the workflow and not silently missing.

In ComfyUI, confirm the LoRA loader points to the right file and model branch. In ControlPilot or InvokeAI, confirm the active model stack matches the LoRA family.

First fix: test with a simple prompt and strength around `0.8` to `1.0`. If that still fails, inspect captions before rerunning.

## The LoRA Copies Training Images

That is overfitting. The model memorized examples instead of learning a flexible concept.

You will see the same pose returning, the same background appearing everywhere, a character refusing to change outfit, a product stuck at one angle, or a style LoRA forcing the same composition across prompts.

Use [Is My LoRA Good?](is-my-lora-good.md) to compare checkpoints. A middle checkpoint can fix what looks like a settings problem.

First test earlier checkpoints. If that does not solve it, reduce steps, lower learning rate, remove duplicates, add pose, crop, lighting, and background variety, caption variable details, and lower rank if the dataset is small.

Do not add more near-duplicates. That is how overfitting gets a bigger vocabulary.

## Samples Look Worse Over Time

Training can improve early and degrade later. That does not mean the run failed; it means the best checkpoint may be earlier.

Check saved samples by step. If step 1000 looks flexible and step 2500 looks rigid, keep step 1000. Align `save_every` and `sample_every` in future runs so the good sample has a matching LoRA file.

The fixes are ordinary: reduce total steps, save more often, use validation prompts that leave the dataset context, lower learning rate, and improve dataset variety.

## Outputs Are Blurry or Low Quality

Blur can come from the dataset, base model, VAE, resolution, sampler, or training settings.

Check the source before blaming the sampler. Are the original images sharp? Did preprocessing upscale weak images? Is the base model good at this subject? Is the VAE or model stack correct? Are sample prompts too vague? Did the LoRA overtrain?

If the dataset is blurry, training will learn blur. If preprocessing added sharpening halos, training may learn halos. The trainer is not a photo editor with morals.

## Identity Changes Between Prompts

For character LoRAs, identity drift usually points to dataset variety problems, weak trigger usage, wrong base model, or undertraining.

Check that the dataset includes enough face angles and expressions, identity features are visible in most images, captions do not over-caption fixed identity traits, the trigger word appears consistently, LoRA strength has been tested across a range, and the base model is compatible with the LoRA.

If the dataset mixes people, cut the wrong images. If the dataset has one angle, add angles. If the character only works at high strength, train or caption more cleanly before stacking more LoRAs.

## Training Loss Looks Weird

Loss is useful, but images matter more for beginner LoRA work. A decreasing loss can still produce a worse LoRA if the model is memorizing. A noisy loss can still produce usable samples.

Use loss to spot crashes, instability, or obvious divergence. Use fixed sample prompts and checkpoint tests to judge quality.

## Before You Rerun

Write down the failed run before rerunning it: base model, dataset version, trigger word, steps, learning rate, rank, batch size, precision, checkpoint that looked best, and the symptom you are fixing.

Then change one thing. If you change dataset, captions, rank, steps, and learning rate at once, the next run may improve while teaching you nothing. That is an expensive shrug.

## Next

Use [Is My LoRA Good?](is-my-lora-good.md) for the evaluation loop, or return to [Training Parameters Explained](training-parameters-explained.md) to adjust the next run.

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
