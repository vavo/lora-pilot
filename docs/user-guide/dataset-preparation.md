# Dataset Preparation

This guide covers the dataset workflow that is actually wired in LoRA Pilot today: ControlPilot dataset APIs + TagPilot editing/saving.

## Storage and Naming Rules

Datasets live under:

- `/workspace/datasets`

ControlPilot dataset listing (`GET /api/datasets`) only shows directories that:

- are folders
- start with `1_`

If you create/rename through ControlPilot API, names are normalized and prefixed automatically:

- `my_set` -> `1_my_set`

ZIP archives are stored in:

- `/workspace/datasets/ZIPs`

## Supported File Types

Image extensions recognized by dataset APIs include:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.bmp`
- `.gif`

Caption/tag files are plain `.txt` files next to images.

## Typical Workflow (UI)

1. Open ControlPilot (`http://localhost:7878`) and go to datasets.
2. Create a dataset or upload a ZIP.
3. Open TagPilot (`/tagpilot`) to edit tags/captions.
4. Save back to `/workspace/datasets` (full save or incremental save flow).
5. Use the dataset name (for example `1_my_set`) in training tools.

## API Workflow (Equivalent)

### Create a dataset

```bash
curl -s -X POST http://localhost:7878/api/datasets/create \
  -H "Content-Type: application/json" \
  -d '{"name":"my_set"}'
```

### Upload and extract ZIP

```bash
curl -s -X POST http://localhost:7878/api/datasets/upload \
  -F "file=@/path/to/my_set.zip"
```

### Load files for TagPilot-style editing

```bash
curl -s "http://localhost:7878/api/tagpilot/load?name=1_my_set"
```

### Save full ZIP back to dataset

```bash
curl -s -X POST "http://localhost:7878/api/tagpilot/save?name=1_my_set" \
  -F "file=@/path/to/updated_dataset.zip"
```

### Incremental save (large datasets)

Endpoint:

- `POST /api/tagpilot/save-item`

Fields:

- `name` (query)
- `file` (multipart)
- `tags` (optional form)
- `reset` (optional bool)
- `done` (optional bool; when true, writes ZIP in `datasets/ZIPs`)

## ZIP Safety Rules

Dataset ZIP extraction rejects unsafe members, including:

- absolute paths
- parent traversal (`..`)
- symlinks

If import fails, rebuild ZIP with normal relative paths only.

## Quick Pre-Training Checklist

- Dataset folder exists under `/workspace/datasets/1_<name>`.
- Images load and captions are readable.
- Dataset appears in `GET /api/datasets`.
- Final ZIP snapshot exists in `/workspace/datasets/ZIPs` (optional but useful backup).

## Not Found in Repo

- A built-in dataset quality scoring/validation engine is **Not found in repo**.
- A dataset-specific CLI command set (`lora-pilot dataset ...`) is **Not found in repo**.

## Related

- [TagPilot](../components/tagpilot.md)
- [Training Workflows](training-workflows.md)
- [ControlPilot](control-pilot.md)
- [Datasets 101](../getting-started/datasets-101/README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
