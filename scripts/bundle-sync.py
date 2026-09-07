#!/usr/bin/env python3
"""Refresh image-owned files without pruning user additions or edited files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

EXCLUDED = {".env", "data", "__pycache__", ".bundle-sync-sha", ".bundle-sync-files.json"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_target(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Invalid bundle inventory path")
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Bundle target escapes workspace directory")
    if any(parent.is_symlink() for parent in [target, *target.parents] if parent != root and parent.is_relative_to(root)):
        raise ValueError("Bundle target is a symlink")
    return target


def sync_bundle(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    inventory_path = target / ".bundle-sync-files.json"
    previous = json.loads(inventory_path.read_text()) if inventory_path.exists() else {}
    if not isinstance(previous, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in previous.items()):
        raise ValueError("Invalid bundle inventory")
    current = {}
    for directory, names, files in os.walk(source, followlinks=False):
        names[:] = sorted(name for name in names if name not in EXCLUDED and not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if name in EXCLUDED or path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            current[relative] = file_hash(path)
    # Validate all paths before changing any file.
    for relative in current.keys() | previous.keys():
        safe_target(target, relative)
    for relative, old_hash in previous.items():
        destination = safe_target(target, relative)
        if relative not in current and destination.is_file() and file_hash(destination) == old_hash:
            destination.unlink()
    for relative, new_hash in current.items():
        destination = safe_target(target, relative)
        if destination.is_file():
            existing_hash = file_hash(destination)
            if existing_hash == new_hash:
                continue
            if relative in previous and existing_hash != previous[relative]:
                continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    payload = json.dumps(current, sort_keys=True)
    temporary = inventory_path.with_name(f"{inventory_path.name}.tmp.{os.getpid()}")
    temporary.write_text(payload)
    os.replace(temporary, inventory_path)
    (target / ".bundle-sync-sha").write_text(hashlib.sha256(payload.encode()).hexdigest() + "\n")


if __name__ == "__main__":
    sync_bundle(Path(sys.argv[1]), Path(sys.argv[2]))
