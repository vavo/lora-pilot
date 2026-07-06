# Training Parameters Explained

_Last updated: 2026-07-06_

Training parameters decide how the trainer studies your dataset. They do not rescue a bad dataset, and they do not turn the wrong model family into the right one. They are controls for a learning process, not a secret spellbook.

For your first LoRA, focus on four controls: **steps**, **learning rate**, **batch size**, and **rank**. Everything else waits until you have one baseline run you can explain.

## The First Run Baseline

Use the defaults from TrainPilot, Kohya, or AI Toolkit unless you are solving a specific problem. A good first run should:

- use a clean TagPilot-reviewed dataset
- train one concept
- save intermediate checkpoints
- generate sample images during training
- use fixed sample prompts with the trigger word
- keep batch size conservative
- document the base model and settings

> **Why does this work?** A baseline gives you evidence. If the LoRA underfits, overfits, or crashes, you know which part of the setup to change next. Without a baseline, every parameter tweak becomes folk medicine with a progress bar.

## Steps: How Long the Trainer Studies

Steps are training updates. Too few steps and the LoRA may not learn the concept. Too many steps and it may memorize the dataset.

For a first character or product LoRA, run a modest test and save checkpoints along the way. Do not assume the final checkpoint wins. A middle checkpoint often has the best balance of identity and flexibility.

In many trainers, exposure comes from image count, repeats, epochs, and batch size. AI Toolkit may expose total steps more directly. The practical question stays the same: how many chances does the model get to study the dataset?

Small datasets overfit faster. Duplicate-heavy datasets overfit faster. Strong trigger words and clean captions can reduce the need to brute-force more steps.

> **Try this variation:** Save every few hundred steps on a short run. Test three checkpoints with the same five prompts from [Is My LoRA Good?](is-my-lora-good.md). Pick the checkpoint that stays flexible, not the one that copies the dataset hardest.

## Learning Rate: How Large Each Update Is

Learning rate controls update size. Higher values move faster and can damage the LoRA faster. Lower values move slower and may underlearn.

Kohya-style SD training often separates UNet and text encoder rates. The [Kohya SS LoRA parameter notes](https://github.com/bmaltais/kohya_ss/wiki/LoRA-training-parameters) document common defaults around `1e-4` for UNet and lower values such as `5e-5` for text encoder training. Treat these as starting points, not commandments.

| Range | Use |
|---|---|
| `1e-5` to `5e-5` | fragile subjects, text encoder tuning, runs that overfit fast |
| `5e-5` to `1e-4` | conservative first SD LoRA experiments |
| `1e-4` to `5e-4` | stronger learning when samples stay generic |
| `5e-4` to `1e-3` | short tests or trainer-specific recommendations |
| above `1e-3` | use only when the tool or model guide asks for it |

If loss explodes, samples degrade fast, or the LoRA becomes rigid early, lower the learning rate or test an earlier checkpoint. If samples remain generic after enough exposure, check captions and trigger usage before raising it.

## Batch Size: How Many Images Per Update

Batch size controls how many images the trainer uses before each update. Batch size `1` is boring and useful. It fits more GPUs, makes failures easier to diagnose, and works for many LoRA runs.

Increase batch size only when you have VRAM headroom and a reason. Larger batch sizes can train faster, but they also change the learning behavior. If a run crashes with CUDA out-of-memory, lower batch size first, then resolution, then rank or model size.

Gradient accumulation can imitate a larger batch without loading all images at once. Use it when the trainer supports it and you know why you need it.

## Rank: How Much the LoRA Can Store

Rank is LoRA capacity. Low rank stores less. High rank stores more, including things you may not want: noise, repeated background, one facial angle, one lighting setup.

Useful first ranges:

| Rank | Good For |
|---|---|
| 8-16 | simple style or small concept tests |
| 16-32 | many character/product first runs |
| 32-64 | more detail, stronger identity, larger datasets |
| 64+ | complex concepts, advanced runs, higher overfit risk |

More rank is not more quality by default. If a high-rank LoRA copies training images, lower rank may help, but better dataset variety usually helps more.

## Alpha and Strength

Alpha changes how the trained rank is scaled inside the LoRA. Many workflows set alpha equal to rank. That is a baseline, not a law.

You will also choose LoRA strength during inference. Do not confuse the two:

- **alpha** affects how the LoRA is trained and stored
- **LoRA strength** affects how hard the LoRA pushes during generation

For first runs, leave alpha at the trainer default unless you are comparing controlled experiments. After training, test LoRA strength at `0.5`, `0.7`, `0.9`, and `1.0` before rerunning training.

## Precision and Memory Controls

Use BF16 or FP16 according to the model family, GPU, and trainer recommendation. Do not choose precision formats because the acronym sounds expensive.

Enable gradient checkpointing when VRAM is tight. It saves memory by recomputing some values during training. The tradeoff is slower training. That is often a good trade when the alternative is a crash.

Use 8-bit optimizers when the trainer recommends them for memory savings. If you are new, accept the profile from TrainPilot or the model-family guide before tuning optimizer details.

## Samples and Saves

Sample prompts are tests. Include:

- the trigger word
- one easy prompt
- one prompt close to the dataset
- one new pose or angle
- one new context

Align `sample_every` and `save_every` when the tool allows it. If a sample at step 1200 looks best, you want the checkpoint from that neighborhood, not only the final file from step 3000.

## Overfit and Underfit Signals

**Underfit** looks generic. The trigger barely works, identity is weak, style disappears, or the product looks like the base model's default guess.

First checks:

- trigger appears in captions and prompts
- base model family matches the LoRA
- enough steps or exposure
- rank not too low
- captions describe the right concept

**Overfit** looks rigid. The LoRA copies poses, backgrounds, lighting, faces, or compositions from the dataset and resists new prompts.

First checks:

- test earlier checkpoints
- reduce steps
- lower learning rate
- remove duplicate images
- add pose, crop, angle, or lighting variety
- lower rank if the dataset is small

## What to Touch First

Use this order:

1. Fix dataset and captions.
2. Test intermediate checkpoints.
3. Adjust steps.
4. Adjust learning rate.
5. Adjust rank.
6. Change method or advanced settings.

That order is not glamorous. It is cheaper than rerunning training because the seventh advanced setting looked lonely.

## Next

Continue with [Training Workflows](training-workflows.md), then evaluate with [Is My LoRA Good?](is-my-lora-good.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
