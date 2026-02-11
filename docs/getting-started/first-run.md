# First Run

This is the short, non-ceremonial boot checklist.

## 1) Start the Stack

```bash
cp .env.example .env
docker compose -f docker-compose.yml up -d
docker compose ps
```

## 2) Open ControlPilot

- URL: `http://localhost:7878`
- First startup can take a few minutes while services initialize.

## 3) Verify Services

Use API or supervisor:

```bash
curl -s http://localhost:7878/api/services
docker exec lora-pilot supervisorctl status
```

Expected core services:
- `controlpilot`
- `comfy`
- `kohya`
- `invoke`
- `diffpipe`
- `jupyter`
- `code-server`
- `ai-toolkit` (if installed in image)

## 4) Verify GPU (If Applicable)

```bash
docker exec lora-pilot nvidia-smi
docker exec lora-pilot python -c "import torch; print(torch.cuda.is_available())"
```

If no GPU runtime, use CPU compose:

```bash
docker compose -f docker-compose.cpu.yml up -d
```

## 5) Confirm Workspace Persistence

```bash
docker exec lora-pilot ls -la /workspace
docker exec lora-pilot ls -la /workspace/{models,datasets,outputs,config,logs}
```

## 6) Pull First Model

```bash
docker exec lora-pilot models list
docker exec lora-pilot models pull sdxl-base
```

You can do the same from ControlPilot -> `Models`.

## 7) Run a Minimal End-to-End Smoke Test

1. Create/upload a tiny dataset in TagPilot.
2. Start a short TrainPilot run (`quick_test` profile).
3. Generate a test image in ComfyUI or InvokeAI.
4. Confirm output appears in MediaPilot.

## Secrets Location

Bootstrap writes credentials to:
- `/workspace/config/secrets.env`

Includes:
- `JUPYTER_TOKEN`
- `CODE_SERVER_PASSWORD`
- `SUPERVISOR_ADMIN_PASSWORD`

## Fast Troubleshooting

```bash
# Container logs
docker compose logs -f lora-pilot

# Service logs
docker exec lora-pilot tail -n 200 /workspace/logs/controlpilot.err.log
docker exec lora-pilot tail -n 200 /workspace/logs/comfy.err.log
docker exec lora-pilot tail -n 200 /workspace/logs/kohya.err.log
```

## Next

- [User Guide](../user-guide/README.md)
- [Training Workflows](../user-guide/training-workflows.md)
- [Model Management](../user-guide/model-management.md)
- [Configuration](../configuration/README.md)

---

_Last updated: 2026-02-11_
