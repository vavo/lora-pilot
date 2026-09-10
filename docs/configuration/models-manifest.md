# Models Manifest

_Last updated: 2026-09-10_

A model catalog is useful when a name leads to the right files in the right place. LoRA Pilot's manifest records that connection in a text file you can inspect and edit. The downloader and ControlPilot use those entries to locate sources, choose destinations, and report what is installed.

A custom entry lets you keep a project's model choice in the same catalog as the bundled models. Add it with a stable name and a precise source, then test that entry before relying on it in a larger workflow.

## Identify the active file before editing

The default runtime manifest is `/workspace/config/models.manifest`. The image carries its bundled default at `/opt/pilot/config/models.manifest.default`. Run `models where` inside the pod or container to see the configured paths. On a Docker Compose host, enter the container with `docker compose exec lora-pilot bash` first.

In the repository, `config/models.manifest` provides the file copied into the image, while `config/models.manifest.default` is the matching reference copy. Keep the two identical when contributing a catalog change. For a workspace-only customization, edit the active runtime file and preserve your own backup.

The downloader supports `WORKSPACE_ROOT`, `MODELS_DIR`, `MODELS_MANIFEST`, and `DEFAULT_MODELS_MANIFEST` overrides. Keep the launch environment consistent between a terminal command and ControlPilot so you do not inspect one catalog while the browser uses another.

## Read one entry from left to right

Each non-comment line describes one named download using six pipe-separated fields.

```text
name|kind|source|subdir|include|size
```

The `name` is the identifier used by `models pull` and the model API. The `kind` selects `hf_file` for one Hugging Face file, `hf_repo` for a repository download, or `url` for a direct download address. The `source` then identifies the corresponding file, repository, or URL.

The `subdir` sets a destination relative to the model root. For repository entries, `include` can restrict the download with comma-separated glob patterns. Leave an empty field between pipes when no include filter is needed. The final `size` field is optional and can contain integer bytes or a supported unit such as `GB` or `MB`. Comments beginning with `#` and empty lines are ignored.

The bundled SDXL base entry provides a concrete example.

```text
sdxl-base|hf_file|stabilityai/stable-diffusion-xl-base-1.0:sd_xl_base_1.0.safetensors|checkpoints||6938078334
```

Here, the source combines a Hugging Face repository ID with a path after the colon. The downloader places the file's basename under `checkpoints`. With the default root, that produces `/workspace/models/checkpoints/sd_xl_base_1.0.safetensors`. The empty include field is appropriate for a single file, and the final integer records the expected byte size in this catalog entry.

## Keep repository filters complete

An `hf_repo` entry uses a repository ID without a colon-separated file path. Its include filters determine which files the downloader requests. A filter that keeps weights but omits the configuration or indexed shards required by a model can leave the consuming tool unable to load it.

For example, the bundled `wan2.2-animate-14b` entry includes configuration and weight patterns together with `google/umt5-xxl/*`. Inspect the full entry in the active manifest before changing its filters. The source layout, the consuming tool, and the completion checks all matter; reducing a download to the most recognizable filename is not a reliable way to make it smaller.

A direct `url` entry uses the URL's filename at the specified destination. Give different assets distinct destinations when upstream names collide. The [migration guidance](../user-guide/model-management.md#existing-downloads-and-corrected-names) explains corrections for older ambiguous filenames and catalog names.

## Understand refresh behavior across image upgrades

Bootstrap records the bundled manifest hash at `/workspace/config/.models.manifest.bundle.sha256`. If the runtime catalog is missing, it seeds it from the image. If the runtime copy still matches the recorded bundle hash, bootstrap can refresh it from the new image. If it differs, bootstrap preserves the customized copy.

The first migration into this tracking scheme is a separate case. A workspace without the hash record receives a one-time refresh, with the prior file backed up as `models.manifest.pre-refresh.<timestamp>`. Keep a separate copy of a customized older catalog before upgrading, then compare the resulting entries with your intended configuration.

This mechanism updates catalog text. It does not prove that every referenced source is reachable at the time of a later download. Read source errors and correct a stale entry without replacing unrelated customizations.

## Interpret installed state and removal

For `hf_file` and `url` entries, ControlPilot checks the canonical destination for a nonempty file. If the size is specified as integer bytes, the file must match that exact size. Rounded unit values remain estimates and use the nonempty-file check. Legacy nested files are reported separately and do not count as the canonical installation.

Repository entries require a completion record that matches the source, include filter, recorded file sizes, and valid weights or shards. A pull creates or repairs that record. These are download-completion checks; the consuming engine still needs a compatible model setup and a successful test run.

The Hugging Face single-file downloader stages the replacement and uses a destination lock before the final move. Legacy Hugging Face files are reused only after source-hash verification. ControlPilot removal uses the entry metadata: it targets expected files for single-file entries and selected files for repository entries, with additional guards for shared top-level folders. Inspect the installed paths before removing an entry you have customized.

## Test a change at the scale of one entry

Save the manifest, run `models list`, and confirm that the expected name appears. That checks local catalog reading; it does not contact the source or validate an entire repository's contents. Run `models pull` for the specific entry when you are ready to download and verify it, then refresh **Models** in ControlPilot.

The browser's workflow plans use the bundled ComfyUI graphs to derive requirements. `GET /api/models/workflows` returns their catalog, while the workflow-specific `/plan` and `/install` routes review and submit an installation. A plan accepts optional filenames; installation needs the same selection and the returned `plan_id`, then repeats the access and storage checks.

Use [model management](../user-guide/model-management.md) for the complete browser flow and [CLI commands](../reference/cli-commands.md) for terminal operations. Keep the catalog entry, installed files, and workflow selection aligned so the next run uses the model you intended.
