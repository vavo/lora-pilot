"""Canonical single-file destinations and non-destructive legacy migration."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit


def contained_path(root: Path, relative: str) -> Path:
    part = Path(relative)
    if not relative or part.is_absolute() or ".." in part.parts:
        raise ValueError("Invalid model path")
    path = root / part
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Model path escapes model storage")
    return path


def file_paths(kind: str, source: str, subdir: str, root: Path) -> tuple[Path, list[Path]]:
    target = contained_path(root, subdir)
    remote = source.split(":", 1)[1] if kind == "hf_file" else Path(urlsplit(source).path).name
    contained_path(target, remote)
    canonical = contained_path(target, Path(remote).name)
    legacy = [contained_path(target, remote)] if "/" in remote else []
    # These uniquely named files used to live outside ComfyUI's model categories.
    if source.startswith("Comfy-Org/Wan_2.1_ComfyUI_repackaged:"):
        old = contained_path(root, "wan/wan2.1")
        legacy.extend([contained_path(old, remote), contained_path(old, Path(remote).name)])
    if source.endswith("/GFPGANv1.4.pth"):
        legacy.append(contained_path(root, "upscale_models/GFPGANv1.4.pth"))
    if source == "Comfy-Org/z_image_turbo:split_files/vae/ae.safetensors":
        legacy.extend([contained_path(root, "vae/ae.safetensors"), contained_path(root, "vae/split_files/vae/ae.safetensors")])
    return canonical, list(dict.fromkeys(p for p in legacy if p != canonical))


def valid_file(path: Path, size: int | None = None) -> bool:
    return path.is_file() and path.stat().st_size > 0 and (not size or path.stat().st_size == size)


def _matches_digest(path: Path, etag: str | None, size: int) -> bool:
    if not valid_file(path, size) or not etag:
        return False
    if len(etag) == 64:
        digest = hashlib.sha256()
    elif len(etag) == 40:
        digest = hashlib.sha1()
        digest.update(f"blob {size}\0".encode())
    else:
        return False
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == etag


def download_hf_file(source: str, subdir: str, root: Path) -> None:
    from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url

    canonical, legacy = file_paths("hf_file", source, subdir, root)
    key = hashlib.sha256(str(canonical.resolve()).encode()).hexdigest()
    lock = contained_path(root, f".download-locks/{key}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        repo, remote = source.split(":", 1)
        token = os.environ.get("HF_TOKEN") or None
        metadata = get_hf_file_metadata(hf_hub_url(repo, remote), token=token)
        if not metadata.size:
            raise ValueError("Provider did not return a valid file size")
        receipt = contained_path(root, f".download-state/files/{key}.json")
        try:
            saved = json.loads(receipt.read_text())
            if canonical.exists() and saved["source"] != source:
                raise ValueError("Destination belongs to another model source")
            if saved["size"] == metadata.size and saved.get("etag") == metadata.etag and valid_file(canonical, saved["size"]) and canonical.stat().st_mtime_ns == saved["mtime_ns"]:
                print(f"Already downloaded: {canonical}", flush=True)
                return
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            pass
        canonical.parent.mkdir(parents=True, exist_ok=True)
        for candidate in [canonical, *legacy]:
            if _matches_digest(candidate, metadata.etag, metadata.size):
                if candidate != canonical:
                    if canonical.exists():
                        raise ValueError("Canonical destination already exists; inspect it before migration")
                    os.link(candidate, canonical)
                    print(f"Reused verified legacy file: {canonical}", flush=True)
                break
        else:
            if canonical.exists():
                # Keep an existing file intact until the replacement has finished.
                print(f"Repairing incomplete or outdated file: {canonical}", flush=True)
            if shutil.disk_usage(canonical.parent).free < metadata.size:
                raise ValueError("Insufficient free disk space for this download")
            stage = contained_path(root, f"{subdir}/.download-staging/{key}")
            stage.mkdir(parents=True, exist_ok=True)
            downloaded = Path(hf_hub_download(repo, remote, local_dir=stage, token=token))
            if not downloaded.resolve().is_relative_to(stage.resolve()) or not valid_file(downloaded, metadata.size):
                raise ValueError("Downloaded file is incomplete")
            os.replace(downloaded, canonical)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps({"source": source, "etag": metadata.etag, "size": canonical.stat().st_size, "mtime_ns": canonical.stat().st_mtime_ns}))
        os.replace(temporary, receipt)
        print(f"100% — {canonical}", flush=True)


if __name__ == "__main__":
    import sys
    download_hf_file(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
