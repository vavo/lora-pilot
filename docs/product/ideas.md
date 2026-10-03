# Product ideas

_Last updated: 2026-10-03_

This document separates implemented foundations from ideas that still need investigation. It is not a delivery schedule. Each idea starts with a user problem and a small way to test whether solving it would help. The [roadmap](roadmap.md) records implemented work and nearer-term priorities.

## Carry an experiment to another workspace

The first experiment-export implementation now packages one selected checkpoint with a manifest, trigger words, sample prompt and optional comparison images after an exact file preview. It excludes datasets, logs, credentials and local paths. A future importer could validate model compatibility in a second workspace, but restoring optimizer state and moving private training data need separate designs.

## Compare checkpoints across a training run

Try my LoRA already generates a baseline followed by every saved checkpoint with a shared prompt and seed. A useful next experiment is comparison across several prompts, with generation count and GPU cost made clear before submission. The current grid is a single-prompt comparison.

## Recommend a starting profile from measured runs

Editable GPU suggestions and local run measurements are now implemented. The next evidence gap is a small, published SDXL and FLUX benchmark set across common GPU capacities, including dependency versions, dataset shape, memory peaks and failures. Local measurements help choose memory settings but do not establish universal hardware requirements.

## Explain checkpoint recovery

Guided training now distinguishes resuming full saved training state from continuing checkpoint weights with a fresh optimizer. Future work can make checkpoint retention easier to understand and measure the space-versus-recovery tradeoff on real training workloads.

## Understand why storage keeps growing

The Storage page measures current usage and offers reviewed cleanup of eligible finished-run files. A future view could connect growth to experiments, identify duplicate content, or explain which saved copies a workflow still references. Begin with a read-only report and measure its scan cost on a realistic workspace. Content hashing, caches shared by several tools, and references outside ControlPilot need evidence before offering broader deletion actions.

## Prepare a repeatable demonstration

The first-run guide now includes the original eight orange robot images from the LoRA Pilot videos, reviewed captions and a path through a Quick test and checkpoint comparison. The images vary in design and are sample inputs, not validated identity-training results. A consistent mascot dataset and a published, repeatable target-GPU result remain useful follow-ups.

## Choose an idea before expanding it

For a selected idea, write the user outcome, the smallest useful scope, and the evidence needed to call it complete. Promote that scope to the roadmap when it is ready for implementation. Keep browser layout checks, API tests, image publication, and live GPU acceptance distinct; each answers a different question about whether the feature is ready to use.
