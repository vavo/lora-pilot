# Dataset Preparation

_Last updated: 2026-10-29_

A folder of photographs can become the starting point for a character you can place in new scenes or a visual style you can use across a project. Before training, you decide what the examples have in common and what should remain free to change. That decision shapes the dataset you build.

LoRA Pilot keeps preparation close to training. You can import images through ControlPilot, review their captions in TagPilot, and save the result into the shared workspace. You spend less time moving files between tools and more time deciding what you want the model to learn.

## Give the collection a clear purpose

Imagine you want to train a LoRA around a handmade ceramic teapot. Across your examples, the teapot should remain recognizable while you vary the angle, lighting, and surroundings. If you show it against the same kitchen wall in each photograph, you give the trainer little evidence for separating the subject from that setting.

Review the collection at full size before you upload it. Remove accidental duplicates and images that contradict the subject you want to teach. Keep useful variation, including views you want the model to handle later. LoRA Pilot does not assign a quality score to the dataset; you make these judgments by inspecting the images. The [Datasets 101 course](../getting-started/datasets-101/README.md) develops this process in more depth.

## Bring the images into ControlPilot

Open **Datasets** in ControlPilot. Create a named dataset to begin a new collection, or choose **Upload ZIP** to import files you have prepared elsewhere. For a straightforward import, place the images and any matching caption files at the top level of the archive, then give the ZIP a descriptive name such as `ceramic_teapot.zip`.

ControlPilot keeps datasets under `/workspace/datasets` and displays folders with the `1_` prefix. Creating `ceramic_teapot` through the interface produces `1_ceramic_teapot`. Importing `ceramic_teapot.zip` produces that same dataset name and stores the archive under `/workspace/datasets/ZIPs`.

Use a distinct name for a new revision if you want to retain the previous collection. Uploading another ZIP with the same name replaces the matching dataset after the archive passes import validation. The stored ZIP is a convenient snapshot, but it shares the workspace with the working files. Keep a copy elsewhere for backup.

The dataset browser recognizes PNG, JPEG, WebP, BMP, and GIF extensions. Recognition in this browser does not establish support in a trainer, so check the requirements of your chosen training workflow. For an image dataset, confirm that the files open as the still images you expect.

## Create images from a description or photo

Open **Datasets → Create a dataset**. This first version is for a person or character, not a general-purpose style or product dataset generator.

1. Give the collection a name, a trigger word and a target of **4–40 images**.
2. Choose **A description** to generate four SDXL reference candidates, or **My photo** to upload one clear reference. Uploads must be at least 256 pixels on both sides, below 40 megapixels and no larger than 32 MiB. Use photos you have permission to use.
3. Select **Person / identity** to allow clothing changes and optionally hairstyle changes. **Character with a fixed look** keeps the original clothing and hairstyle. Backgrounds, lighting, framing and viewpoints vary in both modes.
4. Approve a reference. Every Qwen variation uses that original image, not the previous generated image, to limit cumulative identity drift.
5. Review the contact sheet and edit captions. Local checks flag uncertain or changed identity, visible defects, low detail, small images and near-duplicates. Clean candidates are provisionally kept; flagged candidates get up to three generation attempts per shot, then require your decision. **Keep image & caption** explicitly overrides a warning; **Exclude** prevents publication until that slot has an accepted replacement. The three-attempt limit includes manual regenerations.
6. Confirm that you reviewed the images, then choose **Save dataset & open guided training**. Saving requires the exact requested number of accepted, captioned images. Training opens with the dataset selected; it does not start automatically.

Checks are fallible suggestions, not identity verification or a promise of a perfect dataset. Inspect faces, hands and profiles at full size. One photo cannot establish unseen physical details, and synthetic variations may reinforce the generator's mistakes. Local captions describe visible content and include your trigger word; review them before training.

### Models and runtime requirements

Start ComfyUI in **Services** and install these entries from **Models**. The builder checks native node availability, model filenames and required weight sizes before starting; it never installs models automatically.

| Models entry | Use | Download size |
|---|---|---|
| `sdxl-base` | Four references from a description; not needed for photo input | About 6.9 GB |
| `dataset-qwen-edit` | Qwen Image Edit 2511 FP8 diffusion model | About 20.5 GB |
| `hunyuanimage-2.1-comfy-qwen-encoder-fp8` | Shared Qwen image text/vision encoder | About 9.4 GB |
| `anima-vae` | Shared Qwen VAE | About 0.25 GB |
| `dataset-local-captioner` | Qwen3-VL-2B-Instruct for local checks and captions | About 4.3 GB |

The native [ComfyUI Qwen Image Edit 2511 recipe](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511) uses 40-step editing. V1 does not use a Lightning or multi-angle LoRA, FLUX reference generation, partner nodes or paid captioning APIs. Weight file sizes are not GPU-memory requirements: ComfyUI offloading, resolution and other running tasks affect the GPU and system RAM needed. Validate a four-image job on your hardware before requesting a large set.

Captioning uses the Apache-2.0 [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) model in a separate CPU process using the core environment and local weights, with Hugging Face offline mode enabled. Allow system RAM for roughly 4.3 GB of captioner weights plus inference overhead, in addition to ComfyUI's memory needs. This stage can be slow on pod CPUs. GPU generation and idle pod time can still incur provider charges; the attempt limit is not a monetary spending cap.

On RunPod, LoRA Pilot already runs inside the pod's container. No Docker command or nested Docker daemon is involved.

### Pausing and recovery

Only one dataset-creation job runs at a time. You can navigate elsewhere and return to **Saved creation jobs**. **Pause after current image** stops scheduling subsequent images; it does not interrupt unrelated ComfyUI work. The local captioning worker can be stopped and resumed. Jobs persist in `/workspace/config/dataset-builder/<job-id>/`, including reference images, candidates, API workflows, review results and `vision.log`.

After a Portal restart, **Resume** reuses any saved ComfyUI prompt ID or completed image. Keep ComfyUI's history available until the job finishes. A missing prompt remains pending for up to an hour per resume; an uncertain submission with no returned prompt ID is not automatically repeated. Inspect ComfyUI's queue/history before starting another job in that case.

Completed datasets are published under `/workspace/datasets/1_<name>/` with PNG images, matching `.txt` captions and `generation.json` provenance. An existing dataset is never intentionally replaced; rename it in Datasets before saving another collection with that name. Creation-job files and ComfyUI outputs remain available separately and consume disk space. The builder does not delete them automatically.

## Describe the image you can see

The dataset row shows previews, an image count, and caption coverage. A caption counts when a nonempty `.txt` or `.caption` file has the same basename as an image in the same directory. Unrelated caption files do not increase the count, and two caption formats for one image still count as one captioned image.

Choose **Review captions** to open that collection in **Caption images**, the TagPilot editor, and review its images and text. You can edit tags or captions by hand, or use a configured AI provider to draft them. Read generated text before saving it. An appealing description can still invent a material, miss a detail, or name the wrong subject.

For the teapot project, a caption might read “ceramic teapot on a wooden table, side view, soft window light.” Describe visible differences that matter to the training task. If your training approach uses a trigger term for the subject, apply that convention throughout the collection. Follow the caption format expected by your trainer and base model rather than assuming that one style of tagging fits them all.

LoRA Pilot saves captions as plain `.txt` files beside their images. An image named `teapot_side.png` pairs with `teapot_side.txt`. This arrangement lets you inspect or edit the same material from JupyterLab or VS Code without converting it into an application-specific format.

## Save a version you can trust

Use TagPilot's workspace save action and wait for its completion message. That action writes the loaded collection back to the selected dataset, sending images and their text in sequence. It resets the destination at the start, so load the complete collection you intend to keep before saving over an existing dataset. An interrupted save may leave an incomplete working copy.

After saving, reopen the dataset and check an image near the end of the collection as well as the first one. Confirm that the captions match and that the number of images makes sense. The completed save also creates a ZIP snapshot in `/workspace/datasets/ZIPs`.

For terminal work, run `ls /workspace/datasets/1_ceramic_teapot` inside the pod or container to inspect the saved files. If you automate imports, the corresponding entry points are `POST /api/datasets/create` and `POST /api/datasets/upload`. TagPilot uses `POST /api/tagpilot/save-item` for its sequential save flow. The [API reference](../development/api-reference.md) provides the wider interface context.

## Carry the same collection into training

When the dataset has captions for all its images, choose **Train a LoRA** to open Guided training with that collection selected. You can also select it from the training page. Check the image and caption counts in the form before choosing a profile. Keep the dataset revision and training configuration together in your project notes. After a test run, you can trace an unwanted background or a weak side view back to the examples you supplied and make a targeted revision.

If a ZIP import fails, check that the archive contains ordinary files with relative paths. ControlPilot rejects paths that escape the dataset directory and rejects symbolic links. Rebuild the archive from the source images instead of trying to preserve those entries.

Continue with [TagPilot](../components/tagpilot.md) for editing controls or [training workflows](training-workflows.md) to use the saved collection. For guidance on choosing source material, read [image collection strategies](../getting-started/datasets-101/image-collection-strategies.md).
