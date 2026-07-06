# Image Processing and Preparation

_Last updated: 2026-07-06_

Image processing is the quiet step where good datasets either get cleaner or get ruined with good intentions. You are not trying to make every image look fancy. You are trying to make each image teach the same lesson without adding artifacts, distortions, or hidden contradictions.

In LoRA Pilot, collect first, review in TagPilot, then process only what needs processing. Do not batch-transform a whole dataset because a tutorial said "always sharpen" in 2023. That is how you train a LoRA on sharpening halos and regret.

## The Rule: Fix Problems, Do Not Invent a New Style

Processing should remove barriers to learning:

- crop away dead space
- resize to a model-appropriate range
- correct obvious rotation or exposure issues
- remove duplicates
- reject blur, artifacts, and unusable frames
- keep color and texture faithful to the concept

Processing should not create a second style on top of the data. Heavy filters, aggressive sharpening, face enhancement, denoise plugins, AI upscalers, and automatic beautification can become part of what the LoRA learns. If every image gets the same plastic-skin enhancement, the model may treat plastic skin as part of the subject.

> **Why does this work?** The trainer does not see "edited image" and "true subject" separately. It sees pixels and captions. If processing artifacts repeat across the dataset, they become training signal.

## Resolution Without Ritual

Use the model family as your starting point:

| Family | Practical Starting Size | Notes |
|---|---|---|
| SD1.5 | 512-class images | Works well for older LoRA workflows and low VRAM |
| SDXL | 1024-class images | Strong default for modern image LoRAs |
| Flux/newer image families | 1024-class or model-card guidance | Follow the trainer and workflow notes |
| Video frames | Workflow-specific | Preserve motion consistency before chasing resolution |

Square images are not mandatory for every modern workflow, but they are easier for a first training run. If your subject needs a portrait or landscape frame, keep the aspect ratio consistent enough that the trainer does not learn random cropping as part of the concept.

Do not upscale tiny images just to hit a number. A blurry 400px face upscaled to 1024px is still a blurry face, now with higher-resolution lies.

## Cropping: Keep the Lesson in Frame

Crop for the thing you want the model to learn. A character LoRA needs identity features visible. A product LoRA needs the product readable. A style LoRA needs enough composition to show the style, not only tiny texture samples.

Bad crops teach bad priorities:

- face cut off in character datasets
- product too small in a large scene
- style examples reduced to isolated fragments
- inconsistent framing that makes scale unpredictable
- important details hidden behind borders, text, or watermarks

> **Try this variation:** In TagPilot, scan the dataset as thumbnails. If the important subject disappears at thumbnail size, crop tighter or cut the image. Thumbnail review catches weak composition fast.

## Color and Exposure

Correct obvious mistakes. Do not normalize the life out of the dataset.

For character and product LoRAs, stable color helps. If the same jacket appears blue in one image, teal in another, and gray in a third because of bad white balance, the model may learn the color as flexible even when you wanted it fixed.

For style LoRAs, color may be the point. Preserve the style's palette unless the source has scanning errors, camera casts, or compression damage. A style dataset with "improved" color on half the images and original color on the other half teaches two styles badly.

Use sRGB unless a specific tool or workflow says otherwise. It is boring. Boring color management is a gift.

## Blur, Noise, and Compression

Cut images with motion blur, missed focus, heavy JPEG blocks, watermarks, UI overlays, or visible AI artifacts unless those artifacts are part of the intended style. The trainer cannot guess that the watermark was not invited.

Noise reduction and sharpening are last resorts. If a source image needs heavy repair to become usable, it is often cheaper to replace it. A dataset of repaired weak images usually trains worse than a smaller set of clean originals.

## Duplicates and Near-Duplicates

Duplicates overvote a pose, expression, background, or lighting setup. Near-duplicates are worse because they look like variety while teaching the same thing again.

Remove:

- same frame exported twice
- burst photos with tiny changes
- video frames too close together
- generated variants with the same composition
- cropped copies of the same source unless the crop teaches something new

For video datasets, sample frames far enough apart to show motion without flooding training with the same frame wearing a different timestamp.

## File Naming and Folder Hygiene

Use names that help you audit later:

```text
character_front_001.png
character_side_002.png
product_outdoor_003.png
style_landscape_004.png
```

Avoid names like `final_final2_goodmaybe.png`. The file is not funny enough to justify future confusion.

Keep raw sources separate from processed training images:

```text
my_dataset/
  sources/
  processed/
  captions/
  SOURCES.md
```

TagPilot should work from the processed training folder. Keep the source folder in case you need to recrop, prove rights, or undo a bad preprocessing choice.

## Processing Order

Use this order for most image LoRA datasets:

1. Review and cut weak images.
2. Fix rotation and obvious exposure issues.
3. Crop for the subject or style.
4. Resize only as much as needed.
5. Check for blur, compression, watermarks, and duplicates.
6. Load into TagPilot and caption.
7. Run one final thumbnail review before training.

Caption after major crops. A caption written before cropping may describe objects that no longer appear in the training image. The model will still try to learn that mismatch, because apparently it has not learned sarcasm.

## Next

Continue with [Dataset Organization](dataset-organization.md) or [Image LoRA Datasets](image-lora-datasets.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
