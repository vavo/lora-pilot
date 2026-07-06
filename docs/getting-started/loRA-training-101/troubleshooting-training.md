# Troubleshooting Training

_Last updated: 2026-07-06_

Training failures are easier to fix when you name the symptom first. Do not start by changing ten settings. Start by asking what failed: launch, memory, learning, flexibility, or output quality.

Use this page after one run has produced evidence: logs, sample images, checkpoint names, dataset notes, and the exact base model. Without evidence, troubleshooting becomes astrology with CUDA.

## Training Will Not Start

Common signs:

- TrainPilot or Kohya fails before progress begins.
- AI Toolkit rejects the config.
- Logs show missing files, missing models, bad paths, or permissions.
- Progress stays at zero.

Check these first:

```bash
ls -la /workspace/datasets
ls -la /workspace/models
```

Then check the tool:

- In ControlPilot, confirm the service is running.
- In TrainPilot, confirm the selected dataset exists.
- In Kohya, confirm image and caption paths match the config.
- In AI Toolkit, confirm the model family and config format match.

Path problems are boring and common. Spaces, renamed folders, missing captions, and model files in the wrong category can look like deeper training failures. They are not deeper. They are typos with ambition.

## CUDA Out of Memory

Out-of-memory errors mean the run does not fit the GPU. Do not make this philosophical.

Use this order:

1. Set batch size to `1`.
2. Enable gradient checkpointing.
3. Use the recommended mixed precision for the model family.
4. Lower training resolution.
5. Lower rank.
6. Use a smaller model or a larger GPU.

Restart the service or container if a previous failed run left memory occupied. In ControlPilot, use the service controls before assuming the whole machine needs ritual cleansing.

> **Why does this work?** Batch size, resolution, model size, rank, optimizer state, and precision all affect VRAM. Batch size is the safest first lever because it changes memory use without changing the dataset.

## The LoRA Does Nothing

Common signs:

- The trigger word has little effect.
- Samples look like the base model.
- LoRA strength must be very high before anything changes.

Check these:

- The LoRA was trained for the same base family you are using.
- The trigger word appears in captions and prompts.
- Captions actually describe the concept.
- Training ran long enough to learn.
- Rank is not too low for the concept.
- The LoRA file is loaded in the workflow and not silently missing.

In ComfyUI, confirm the LoRA loader points to the right file and model branch. In ControlPilot or InvokeAI, confirm the active model stack matches the LoRA family.

First fix: test with a simple prompt and strength around `0.8` to `1.0`. If that still fails, inspect captions before rerunning.

## The LoRA Copies Training Images

That is overfitting. The model memorized examples instead of learning a flexible concept.

Common signs:

- same pose keeps returning
- same background appears everywhere
- character cannot change outfit
- product always appears at the same angle
- style LoRA forces the same composition

Use [Is My LoRA Good?](is-my-lora-good.md) to compare checkpoints. A middle checkpoint can fix what looks like a settings problem.

First fixes:

- test earlier checkpoints
- reduce steps
- lower learning rate
- remove duplicates
- add pose, crop, lighting, and background variety
- caption variable details
- lower rank if the dataset is small

Do not add more near-duplicates. That is how overfitting gets a bigger vocabulary.

## Samples Look Worse Over Time

Training can improve early and degrade later. That does not mean the run failed; it means the best checkpoint may be earlier.

Check saved samples by step. If step 1000 looks flexible and step 2500 looks rigid, keep step 1000. Align `save_every` and `sample_every` in future runs so the good sample has a matching LoRA file.

First fixes:

- reduce total steps
- save more often
- use validation prompts that leave the dataset context
- lower learning rate
- improve dataset variety

## Outputs Are Blurry or Low Quality

Blur can come from the dataset, base model, VAE, resolution, sampler, or training settings.

Check in order:

1. Are source images sharp?
2. Did preprocessing upscale weak images?
3. Is the base model good at this subject?
4. Is the VAE or model stack correct?
5. Are sample prompts too vague?
6. Is the LoRA overtrained?

If the dataset is blurry, training will learn blur. If preprocessing added sharpening halos, training may learn halos. The trainer is not a photo editor with morals.

## Identity Changes Between Prompts

For character LoRAs, identity drift usually points to dataset variety problems, weak trigger usage, wrong base model, or undertraining.

Check:

- enough face angles and expressions
- identity features visible in most images
- captions do not over-caption fixed identity traits
- trigger word appears consistently
- LoRA strength tested across a range
- base model compatible with the LoRA

If the dataset mixes people, cut the wrong images. If the dataset has one angle, add angles. If the character only works at high strength, train or caption more cleanly before stacking more LoRAs.

## Training Loss Looks Weird

Loss is useful, but images matter more for beginner LoRA work. A decreasing loss can still produce a worse LoRA if the model is memorizing. A noisy loss can still produce usable samples.

Use loss to spot crashes, instability, or obvious divergence. Use fixed sample prompts and checkpoint tests to judge quality.

## Before You Rerun

Write down the failed run:

- base model
- dataset version
- trigger word
- steps
- learning rate
- rank
- batch size
- precision
- checkpoint that looked best
- symptom you are fixing

Then change one thing. If you change dataset, captions, rank, steps, and learning rate at once, the next run may improve while teaching you nothing. That is an expensive shrug.

## Next

Use [Is My LoRA Good?](is-my-lora-good.md) for the evaluation loop, or return to [Training Parameters Explained](training-parameters-explained.md) to adjust the next run.

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
