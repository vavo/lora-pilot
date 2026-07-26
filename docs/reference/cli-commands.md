# CLI Commands Reference

_Last updated: 2026-07-26_

These are the command-line entry points shipped in the image. On RunPod, the
terminal is already inside the LoRA Pilot runtime, so run them directly. Do
not use Docker inside the pod. For a separate Docker Compose host, use
`docker compose exec lora-pilot ...`.

## `pilot`

```bash
pilot status [service...]
pilot start [service...]
pilot stop [service...]
pilot comfy
pilot kohya
pilot diffpipe
pilot jupyter
pilot code
pilot urls
```

With no service argument, `pilot start` and `pilot stop` target `all`.
Supervisor service identifiers include `controlpilot`, `comfy`, `kohya`,
`diffpipe`, `invoke`, `ai-toolkit`, `jupyter`, and `code-server`.

Examples:

```bash
pilot status
supervisorctl restart comfy
supervisorctl tail -100 controlpilot
tail -n 200 /workspace/logs/comfy.err.log
```

## `models`

```bash
models list
models pull <name> [--dir SUBDIR]
models pull-all
models where
models help
```

`models pull` accepts one manifest name per invocation. `--dir` is relative
to `/workspace/models`. The active manifest is
`/workspace/config/models.manifest`; use `models where` to inspect it.

Examples:

```bash
models list
models pull sdxl-base
models pull sdxl-base --dir custom/sdxl-base
models pull-all
```

The model CLI does not provide `info`, `remove`, `validate`, `update`,
`cleanup`, collection, backup, benchmark, or filtering subcommands. Model
pulls and deletion are also available through ControlPilot at `/api/models`.

## Training entry points

```bash
trainpilot --help
/opt/pilot/apps/TrainPilot/trainpilot.sh --help
```

ControlPilot exposes the supported guided-training API under
`/api/trainpilot/*` and Diffusion Pipe under `/dpipe/train/*`.

## Docker Compose host examples

Run these on the host that owns the Compose project, not inside a RunPod pod:

```bash
docker compose exec lora-pilot pilot status
docker compose exec lora-pilot models list
docker compose logs --tail=100 lora-pilot
```

The host-side wrapper is an operational detail; the commands after `exec
lora-pilot` are the same commands shown above.
