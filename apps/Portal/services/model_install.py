"""Installation plans derived from the bundled ComfyUI workflow graphs."""
from __future__ import annotations

import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .model_files import file_paths

WORKFLOW_DIR = Path(__file__).resolve().parents[3] / "config/comfy-workflows"
WORKFLOWS = {
    f"video_{name}_{mode}": {"family": family, "title": title}
    for name, family in [("ltx2_5", "ltx25"), ("minimax_h3", "minimax")]
    for mode, title in [("t2v", "Text to video"), ("i2v", "Image to video")]
}


def workflow(workflow_id: str) -> dict:
    if workflow_id not in WORKFLOWS:
        raise ValueError("Unknown bundled workflow")
    refs = {}

    def visit(value):
        if isinstance(value, dict):
            if all(key in value for key in ("name", "url", "directory")):
                ref = {key: value[key] for key in ("name", "url", "directory")}
                ref["optional"] = ref["name"] == "gemma4_e2b_it_int8_convrot.safetensors"
                refs[(ref["directory"], ref["name"])] = ref
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(json.loads((WORKFLOW_DIR / f"{workflow_id}.json").read_text()))
    if not refs:
        raise ValueError("Workflow has no model references")
    return {"id": workflow_id, **WORKFLOWS[workflow_id], "files": list(refs.values())}


def catalog() -> list[dict]:
    return [workflow(key) for key in WORKFLOWS]


def check_source(source: str, token: str | None) -> dict:
    from huggingface_hub import get_hf_file_metadata, hf_hub_url

    repo, remote = source.split(":", 1)
    try:
        metadata = get_hf_file_metadata(hf_hub_url(repo, remote), token=token or False, timeout=15)
        if not metadata.size:
            return {"error": "Source did not provide a file size."}
        return {"size_bytes": metadata.size, "access": "Verified"}
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (401, 403):
            return {"error": "Access denied. Accept the source license and add an authorized Hugging Face token in Settings."}
        if status == 404:
            return {"error": "Source file was not found or is private."}
        # Provider exceptions may include request headers. Never expose them to the UI.
        return {"error": "Could not verify source access. Check connectivity and review again."}


def installation_plan(workflow_id: str, optional: list[str], entries: list, root: Path, token: str | None) -> dict:
    selected = workflow(workflow_id)
    optional_names = {ref["name"] for ref in selected["files"] if ref["optional"]}
    if set(optional) - optional_names:
        raise ValueError("Unknown optional workflow component")
    files, errors = [], []
    for ref in selected["files"]:
        if ref["optional"] and ref["name"] not in optional:
            continue
        source = ref["url"].removeprefix("https://huggingface.co/").replace("/resolve/main/", ":", 1)
        entry = next((m for m in entries if m.kind == "hf_file" and m.source == source and m.subdir == ref["directory"]), None)
        item = {**ref, "model_name": entry.name if entry else None, "source": source,
                "size_bytes": (entry.size_bytes if entry.installed else entry.expected_size_bytes) if entry else None,
                "size_is_exact": entry.size_is_exact if entry else False,
                "state": "installed" if entry and entry.installed else "missing"}
        canonical, _ = file_paths("hf_file", source, ref["directory"], root)
        item["path"] = str(canonical)
        if not entry or canonical.name != ref["name"]:
            item["error"] = "Exact workflow component is missing from the manifest. Update the manifest first."
        elif entry.legacy_path and not entry.installed:
            item["legacy_path"] = entry.legacy_path
        files.append(item)

    missing = [item for item in files if item["state"] == "missing" and not item.get("error")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = pool.map(lambda item: check_source(item["source"], token), missing)
        for item, check in zip(missing, checks):
            if check.get("size_bytes") and item["size_is_exact"] and item["size_bytes"] != check["size_bytes"]:
                item["error"] = "Source size changed. Update the manifest before installing."
            item.update(check)

    # Reserve the full replacement size even when a legacy copy might be reused.
    # Existing partial/outdated files stay intact until the new file is complete.
    disks = {}
    for item in files:
        if item.get("error"):
            errors.append(f"{item['name']}: {item['error']}")
        if item["state"] == "installed":
            continue
        parent = Path(item["path"]).parent
        while not parent.exists():
            parent = parent.parent
        device = parent.stat().st_dev
        disk = disks.setdefault(device, {"path": str(parent), "free_bytes": shutil.disk_usage(parent).free, "required_bytes": 0})
        disk["required_bytes"] += item["size_bytes"] or 0
    for disk in disks.values():
        if disk["required_bytes"] > disk["free_bytes"]:
            errors.append(f"Insufficient free disk space on {disk['path']}.")
    identity = [(f["model_name"], f["source"], f["path"], f["size_bytes"]) for f in files]
    return {
        "workflow_id": workflow_id, "title": selected["title"], "files": files,
        "plan_id": hashlib.sha256(json.dumps(identity).encode()).hexdigest(),
        "download_bytes": sum(f["size_bytes"] or 0 for f in files if f["state"] == "missing"),
        "installed_count": sum(f["state"] == "installed" for f in files),
        "disks": list(disks.values()), "token_configured": bool(token),
        "errors": errors, "can_install": not errors,
    }
