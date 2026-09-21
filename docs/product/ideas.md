# Product ideas

_Last updated: 2026-09-21_

These are proposals to investigate, not features you can use today or a schedule for delivery. Each idea starts with a user problem and a small way to test whether solving it would help. The [roadmap](roadmap.md) records implemented work and nearer-term priorities.

## Carry an experiment to another workspace

A downloaded checkpoint preserves the trained weights, but someone using it later may also need the model family, trigger words, training settings, and sample prompts. An experiment export could package a selected checkpoint with a readable run summary and chosen comparison images. Begin by defining the manifest and showing an exact preview of included files. Dataset images, captions, logs, credentials, and machine-specific paths should require separate consideration rather than entering an export by default.

Direct checkpoint downloads, saved configuration, and workflow JSON downloads already cover parts of this journey. A combined experiment package does not yet exist.

## Compare checkpoints across a training run

Try my LoRA compares a selected checkpoint with the base model. A contact sheet could extend that comparison across several checkpoints using the same prompts and seeds. You could look for the point where the subject becomes recognizable without losing flexibility. Start with a few selected checkpoints and show the generation count before submission; a large comparison can consume considerable GPU time.

## Recommend a starting profile from measured runs

A hardware-aware setup could suggest a starting profile using the model family, available VRAM, image resolution, and observed results from verified training runs. The useful outcome would be a stated assumption and a configuration you can inspect. Before building the recommendation UI, collect a small benchmark set and record hardware, dependency versions, peak memory, and failures. VRAM alone does not establish whether a job will succeed.

## Explain checkpoint recovery

A stopped run can leave useful LoRA weights, but continuing the same optimization process may also require optimizer and scheduler state. A recovery assistant could identify what a run saved and explain the difference between starting a new experiment from weights and resuming full training state. Investigate the storage cost and trainer support first. The current Repeat run action creates a new experiment; it does not resume a checkpoint.

## Understand why storage keeps growing

The Storage page measures current usage and offers reviewed cleanup of eligible finished-run files. A future view could connect growth to experiments, identify duplicate content, or explain which saved copies a workflow still references. Begin with a read-only report and measure its scan cost on a realistic workspace. Content hashing, caches shared by several tools, and references outside ControlPilot need evidence before offering broader deletion actions.

## Prepare a repeatable demonstration

A small, licensed sample dataset and a documented training-and-comparison recipe could make a first session easier to evaluate. Someone trying LoRA Pilot would have a known starting point and a result to compare with their own run. Check redistribution rights, download size, and reproducibility on target hardware before bundling assets. Keep sample outputs visibly identified so they cannot be mistaken for results generated on the current pod.

## Choose an idea before expanding it

For a selected idea, write the user outcome, the smallest useful scope, and the evidence needed to call it complete. Promote that scope to the roadmap when it is ready for implementation. Keep browser layout checks, API tests, image publication, and live GPU acceptance distinct; each answers a different question about whether the feature is ready to use.
