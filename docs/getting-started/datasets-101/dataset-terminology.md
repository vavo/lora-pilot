# Dataset Terminology

_Last updated: 2026-07-06_

You do not need a dictionary before you build a dataset. You need enough vocabulary to understand what TagPilot, TrainPilot, Kohya, AI Toolkit, and other guides are asking you to do.

This page explains the words you will see while preparing a LoRA dataset. Read it once, then come back when a setting name starts pretending to be obvious.

## Dataset

A dataset is the folder of examples the trainer studies. For image LoRAs, that usually means image files plus matching caption files. For video work, it may mean clips, extracted frames, metadata, and captions.

The trainer treats the dataset as evidence. If the evidence repeats a background, that background gets a vote. If captions omit the outfit, the outfit may become part of the identity. If half the images are blurry, blur becomes part of the lesson. The dataset is not a storage folder. It is the lesson plan.

## Sample

A sample is one training item. In a simple image LoRA dataset, one sample is one image and its caption:

```text
anna_front_001.png
anna_front_001.txt
```

The names should match. If TagPilot saves captions beside the images, keep the pair together when you move or archive the dataset.

## Caption

A caption is the text that tells the trainer what appears in the image. Captions do two jobs:

- they name the concept you want the LoRA to learn
- they name details you want to control later

For example:

```text
photo of mychar_anna, woman with short red hair, black jacket, sitting at a cafe, warm indoor light
```

The trigger word is `mychar_anna`. The rest of the caption names visible details. Later, the model has a better chance of changing jacket, setting, and lighting because those details were named during training.

## Trigger Word

A trigger word is the prompt handle for the trained concept. Use a rare token such as `mychar_anna`, `brandpack_v1`, or `inkwash_style`.

Put the trigger word in every caption where the concept appears. Use the same spelling everywhere. A typo creates a second useless trigger. Computers have no sympathy here.

## Tag

A tag is a short caption unit, often comma-separated:

```text
mychar_anna, woman, short red hair, black jacket, cafe, warm light
```

Tags work well for anime, illustration, booru-style datasets, and workflows that expect tag vocabulary. Sentence captions work better for many photo and product datasets. TagPilot can help generate both, but you still need to edit them.

## Metadata

Metadata is information about the dataset or individual samples: source, license, creator, resolution, split, notes, or intended use. It may live in JSON, CSV, Markdown, or tool-specific files.

For LoRA Pilot, a simple `SOURCES.md` or `sources.csv` is often enough. Record where images came from and what rights you have. Read [Data Rights and Consent](data-rights-and-consent.md) before building a dataset from anything you did not create.

## Resolution and Aspect Ratio

Resolution is pixel size. Aspect ratio is image shape.

SD1.5 workflows often start around 512-class sizes. SDXL and newer image families often start around 1024-class sizes. The exact training size depends on model family, trainer, bucket settings, and VRAM.

Aspect ratio matters because the model learns framing. If every product image is square but you later prompt for a wide outdoor scene, the LoRA may struggle. If every character crop is a headshot, full-body prompts may get weird.

## Buckets

Buckets let a trainer group images by similar aspect ratio or size instead of forcing every image into one square crop. This preserves more natural framing.

Use buckets when the trainer supports them and your dataset has useful aspect-ratio variety. Do not use random aspect ratios because "buckets exist." The dataset still needs a plan.

## Repeats, Epochs, and Steps

These terms describe training exposure.

- **Repeats**: how many times each image is reused in one epoch.
- **Epoch**: one pass over the repeated dataset.
- **Steps**: actual training updates.

Different trainers expose these differently. TrainPilot may hide some details behind a profile. Kohya may ask for repeats and epochs. AI Toolkit may expose total steps more directly.

The practical question stays the same: how many chances does the trainer get to study each sample?

## Batch Size

Batch size is how many samples the trainer processes before one update. Batch size `1` is common for LoRA training because it saves VRAM and makes failures easier to diagnose.

If training crashes with CUDA out-of-memory, lower batch size before changing stranger settings.

## Validation Set

A validation set is a small group of examples or prompts used to check whether training is working. For beginner LoRA training, validation often means fixed sample prompts and saved checkpoints rather than a formal machine-learning split.

Use the same prompts across checkpoints. If one checkpoint can handle a new pose and a later checkpoint only copies the dataset, the earlier checkpoint may be better.

## Overfitting and Underfitting

Overfitting means the LoRA memorized the dataset instead of learning a flexible concept. You see repeated poses, backgrounds, faces, or compositions.

Underfitting means the LoRA did not learn enough. The trigger barely changes the output, identity is weak, or the style disappears.

Use [Is My LoRA Good?](../loRA-training-101/is-my-lora-good.md) to test both.

## The Terms You Need First

Start with these:

| Term | Plain Meaning |
|---|---|
| dataset | folder of training examples |
| sample | one image or clip plus caption |
| caption | text lesson for one sample |
| trigger word | prompt handle for the trained concept |
| bucket | aspect-ratio grouping |
| steps | training updates |
| rank | LoRA capacity |
| checkpoint | saved training state or saved LoRA file |

If you understand those, you can start building a dataset. The rest becomes clearer after the first failed run. Convenient? No. Educational? Unfortunately.

## Next

Continue with [What Makes a Good Dataset](what-makes-a-good-dataset.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
