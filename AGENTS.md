# LoRA Pilot Agent Notes

## Before Making Changes

- Read `aidocs/AI_CONTEXT.md`.
- Read `aidocs/FEATURE_MAP.md` for the affected feature.
- Follow `aidocs/INVARIANTS.md`.
- Consult `aidocs/WORKFLOWS.md`, `aidocs/HOTSPOTS.md`, `aidocs/DEPENDENCIES.md`, and `aidocs/TECH_DEBT.md` when relevant.
- Follow the existing implementation patterns. Keep changes surgical.
- Do not modify generated or host-noise files such as `.DS_Store`.

## Completion

- Run the validation commands appropriate to the affected area before considering the task complete.
- Use `aidocs/AI_CONTEXT.md` for the project-wide build, runtime, and testing entry points.
- Keep `aidocs/` ignored; it is a local AI documentation layer, not a tracked product artifact.
