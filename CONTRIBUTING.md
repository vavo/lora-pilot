# Contributing to LoRA Pilot

Thanks for helping improve LoRA Pilot. Contributions are welcome across the ControlPilot UI, training and model workflows, runtime scripts, Docker image, documentation, and tests.

Before starting, read [AGENTS.md](AGENTS.md) for repository-specific constraints. For a feature or bug fix, define the success condition first and keep the change focused. If the correct behavior is unclear, open an issue or discussion before building a large solution.

## Project shape

LoRA Pilot is a Dockerized AI runtime. The main product surfaces are:

- `apps/Portal/`: ControlPilot FastAPI backend and static UI.
- `apps/TrainPilot/`: guided Kohya/SDXL training flow.
- `apps/MediaPilot/`: embedded output gallery.
- `scripts/`: image-build and runtime entrypoints.
- `config/`: build and model defaults.
- `supervisor/`: managed services.
- `tests/`: Python `unittest` regression checks.
- `docs/`: user, component, configuration, and development documentation.

## Before changing code

1. Find the existing implementation and tests for the affected feature.
2. Check the working tree. Preserve unrelated changes and do not edit generated or host-noise files such as `.DS_Store`.
3. State assumptions when the requested behavior has more than one reasonable interpretation.

## Local validation

The repository's primary quality gate is:

```bash
python3 -m unittest discover -s tests
```

Run focused tests while iterating, then run the full suite before submitting. For build-related changes also run:

```bash
make build-check
```

`make build-check` requires a working Docker daemon/buildx environment. A Docker socket failure is an environment problem, not proof that the Dockerfile is invalid.

For UI changes, inspect the rendered page at desktop and mobile widths when possible. For runtime, GPU, storage, or RunPod changes, distinguish static/build evidence from live-pod evidence and report anything that was not verified.

## Change guidelines

- Prefer the smallest change that satisfies the requested behavior.
- Match the surrounding implementation style; avoid unrelated refactors.
- Keep persistent user data under `/workspace`; image-owned code belongs under `/opt/pilot`.
- Preserve path containment, secret handling, service ownership, and workspace contracts.
- Do not place credentials, tokens, private URLs, or generated media in source, tests, screenshots, or documentation.
- Add or update focused regression coverage for behavior changes.
- Update user or component documentation when the public workflow changes.
- Do not change live pods, storage, images, or external services unless the task explicitly includes that operation.

## Pull requests

Keep each pull request narrow enough to review. Include:

- the user-visible result and affected files;
- the tests and validation commands actually run;
- runtime, container, or live-pod checks, if performed;
- screenshots for meaningful UI changes;
- known limitations or unverified areas;
- links to related issues or discussions.

Do not claim a build, runtime, or live deployment was verified when only static inspection was performed. Reviewers appreciate honest evidence more than theatrical confidence.

Maintainers may request smaller commits, additional tests, documentation, or a different design before merging.

## Reporting problems

For bugs, include the LoRA Pilot version or image tag, environment, exact reproduction steps, expected behavior, actual behavior, relevant logs, and the smallest useful configuration excerpt. Remove secrets and personal data before posting logs.

For security issues, do not publish credentials or an exploitable proof in a public issue. Contact the repository maintainers privately through the project owner or repository security channel.
