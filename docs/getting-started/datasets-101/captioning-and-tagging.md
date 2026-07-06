# Captioning and Tagging

_Last updated: 2026-07-06_

Captions tell the trainer which parts of an image are named, movable, and promptable later. They are not alt text. They are training controls disguised as ordinary words.

TagPilot gives you a place to generate, edit, and save those controls before training. Use auto-captioning to get a first draft. Use your eyes to make it true.

## The Control-Knob Mental Model

If you caption a feature, you make it easier to control in prompts later. If you leave a feature unnamed, the trainer may treat it as part of the core identity, style, or concept.

For a character LoRA, captions should name things you want to vary: outfit, pose, background, expression, camera angle, lighting. Be careful with permanent identity traits. If every image has red hair and you never caption red hair, the LoRA may decide red hair is welded to the character. That may be useful. It may also be why your prompt for black hair quietly fails.

For a style LoRA, captions should name the subjects and scenes. The style should become the repeated visual behavior across many subjects, not a secret attachment to "portrait of woman" because every training image had the same subject.

For a product or object LoRA, captions should name context and view: front view, side view, studio photo, outdoor scene, on table, worn by person. The object should stay stable while the situation changes.

> **Why does this work?** The trainer learns correlations between image features and text tokens. Captions separate "the thing I want to keep" from "the thing I want to control later." Bad captions blur that boundary.

## Start in TagPilot

For a first dataset, load the processed images in TagPilot and generate draft tags or captions. Edit the first 10 by hand until the wording feels consistent, then apply the same vocabulary to the rest. Before saving, scan for missing trigger words, wrong subjects, and repeated mistakes. Save captions beside the images so trainers can keep each pair together.

Do not accept auto-captions in bulk without review. Auto-captioners miss details, invent details, and vary wording for the same feature. The model will not know which synonym you meant.

## WD14 Tags or BLIP Captions?

Use WD14-style taggers when the dataset and target model benefit from tag vocabulary, especially anime, illustration, and booru-style workflows. The common reference point is the [SmilingWolf WD tagger](https://huggingface.co/spaces/SmilingWolf/wd-tagger) family.

Use BLIP-style captioners for natural-language image descriptions, especially photo-like datasets, products, scenes, or mixed realistic data. Hugging Face documents BLIP in the [Transformers BLIP docs](https://huggingface.co/docs/transformers/en/model_doc/blip).

Neither tool replaces review. Pick the format your trainer and model family expect, then make the wording consistent.

## Trigger Words

A trigger word gives the LoRA a handle. Use something rare enough that the base model does not already have a strong meaning for it:

```text
mychar_anna
brandpack_v1
inkwash_style
crystalblade_concept
```

Put the trigger in every caption where the trained concept appears. Keep it near the subject:

```text
photo of mychar_anna, woman in a green jacket, standing in a city street, evening light
```

Avoid generic triggers such as `woman`, `style`, `photo`, or `character`. Those words already mean too much.

> **Try this variation:** In TagPilot, filter or search your captions for the trigger word before training. If any training image lacks the trigger, decide whether the concept is absent or the caption is wrong.

## Caption Patterns That Work

For a character:

```text
photo of mychar_anna, woman with short red hair, wearing a black jacket, sitting at a cafe, side view, warm indoor light
```

For a style:

```text
inkwash_style illustration of a mountain village, loose brushwork, muted colors, paper texture
```

For a product:

```text
studio photo of brandpack_v1 backpack, front view, black nylon, orange zipper pulls, white background
```

For a concept:

```text
fantasy render of crystalblade_concept sword, blue glowing crystal blade, ornate silver hilt, held by armored knight
```

The useful pattern is subject, trigger, visible attributes, context, and style or lighting. You do not need poetry. You need the caption to match the image.

## What to Caption and What to Leave Alone

Caption features that should change later: clothing, pose, expression, background, lighting, camera angle, medium, style, and product context. If you want the prompt to control a detail later, give the trainer a word for that detail now.

Treat identity-defining features with intent. For a character LoRA, you may leave some stable identity traits unnamed so they bind to the trigger. For a product LoRA, you may leave the exact product shape bound to the trigger but caption the color if you want color changes later.

The mistake is not "captioning too much" or "captioning too little." The mistake is captioning without a plan.

## Bad Caption Smells

Fix captions before training when one image says `young woman`, another says `girl`, and another says `person` for the same subject. Fix them when captions mention objects cropped out of the image, omit the trigger word, describe desired quality instead of visible content, or repeat a vague phrase like `high quality, masterpiece, detailed` across the whole folder. Auto-tags also need review when they invent the wrong hair color, gender, style, or impossible object.

Quality words can help some generation prompts. In training captions, they often become clutter unless they describe the actual dataset.

## Next

Continue with [Image Processing and Preparation](image-processing-preparation.md), then [Dataset Validation and Testing](dataset-validation-and-testing.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
