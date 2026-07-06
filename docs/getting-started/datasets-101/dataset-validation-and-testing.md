# Dataset Validation and Testing

_Last updated: 2026-07-06_

Dataset validation asks one blunt question: should you spend GPU time on this folder yet?

Most bad training runs announce themselves before training starts. The clues are in the thumbnails, captions, filenames, rights notes, duplicate frames, wrong trigger words, and mismatched source images. You just have to look before the progress bar hypnotizes you.

## The Three-Pass Review

Use three passes before the first run:

1. **Visual pass**: thumbnails, crops, blur, duplicates, wrong images.
2. **Caption pass**: trigger word, visible details, consistency.
3. **Training pass**: tiny run, saved samples, checkpoint comparison.

TagPilot handles the visual and caption passes well. TrainPilot or your chosen trainer handles the small run. MediaPilot helps compare outputs.

> **Why does this work?** You catch cheap mistakes while they are still cheap. Fixing a caption before training costs seconds. Discovering the same bad caption after a three-hour run costs patience and probably snacks.

## Visual Pass

Open the dataset as thumbnails. Do not start with full-size images. Thumbnail review shows whether the subject, style, or product is readable at a glance.

Cut or fix:

- blurry images
- tiny subjects
- repeated near-duplicates
- watermarks and UI overlays
- wrong person, wrong object, wrong style
- harsh compression artifacts
- crops that remove identity or product features
- images you cannot legally or ethically use

For character datasets, scan for identity consistency. For style datasets, scan for subject variety. For product datasets, scan whether the product remains readable from each angle.

> **Try this variation:** Sort the images worst-to-best in TagPilot or Finder. Delete the bottom 20 percent. If that feels painful, move them to a `maybe/` folder and train without them first.

## Caption Pass

Search the captions for the trigger word. Every image containing the concept should have it. Every image without the concept should not.

Then check vocabulary:

- same subject word across captions
- same trigger spelling
- visible details match the image
- no cropped-out objects
- no auto-caption hallucinations
- no repeated junk phrase in every file
- controllable details are named

For character LoRAs, caption outfit, pose, angle, expression, background, and lighting if you want those to vary later. For style LoRAs, caption the subject and scene so the style can detach from the content. For product LoRAs, caption view, context, and visible materials.

## File Pass

A simple image LoRA dataset should not require archaeology. Check:

- image and caption filenames match
- extensions are consistent enough for the trainer
- no spaces or strange shell-hostile characters in critical paths
- raw sources are separate from processed training images
- `SOURCES.md` or `sources.csv` exists for external assets
- dataset folder loads in TagPilot

If a trainer cannot find images or captions, assume the path or naming convention is wrong before assuming the trainer is haunted.

## Pilot Run

Before a serious run, train a tiny test:

- small step count
- batch size `1`
- same base model you plan to use later
- sample prompts with the trigger word
- at least one prompt outside the dataset context

The goal is not final quality. The goal is to confirm that the dataset activates, the trigger works, and the LoRA starts learning the right idea.

Stop and fix the dataset if:

- samples ignore the trigger
- samples copy one pose or background immediately
- the subject changes identity between samples
- captions do not match outputs
- the model learns artifacts faster than the concept

## Validation Grid

Use this small grid before a full run:

| Check | Pass Looks Like | Fix If It Fails |
|---|---|---|
| Thumbnail clarity | subject/style readable at a glance | crop tighter or cut weak images |
| Variation | pose, angle, context vary on purpose | add variety or remove duplicates |
| Trigger coverage | trigger appears where concept appears | edit captions in TagPilot |
| Caption accuracy | text matches visible content | remove hallucinated details |
| Rights notes | source and license recorded | add `SOURCES.md` or cut images |
| Pilot samples | concept appears without copying | adjust dataset before settings |

## When More Data Is the Wrong Fix

Adding images helps when the dataset lacks coverage. It hurts when you add more weak images with the same problems.

Add data when:

- the character lacks angles or expressions
- the product lacks views or contexts
- the style lacks subject variety
- the concept appears in too few situations

Cut data when:

- images repeat the same pose
- quality varies wildly
- captions would need excuses
- source rights are unclear
- the image teaches a thing you do not want

## Next

Continue with [Image LoRA Datasets](image-lora-datasets.md), [Video LoRA Datasets](video-lora-datasets.md), or [LoRA Training 101](../loRA-training-101/README.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
