from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

try:
    from .model_files import contained_path, file_paths, valid_file
except ImportError:
    from model_files import contained_path, file_paths, valid_file


class ModelEntry(BaseModel):
    name: str
    kind: str
    source: str
    subdir: str
    include: Optional[str] = ""
    expected_size_bytes: Optional[int] = None
    size_is_exact: bool = False
    category: str
    type: str
    installed: bool
    size_bytes: int
    info_url: Optional[str] = None
    target_path: str
    primary_path: Optional[str] = None
    legacy_path: Optional[str] = None


def _normalize_match_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _matches_any_pattern(rel_path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def _select_hf_repo_files(
    target_dir: Path,
    patterns: List[str],
    model_name: str,
    models_root: Path,
) -> List[Path]:
    if not target_dir.exists():
        return []
    files = [p for p in target_dir.rglob("*") if p.is_file()]
    if patterns:
        filtered: List[Path] = []
        for p in files:
            rel = p.relative_to(target_dir).as_posix()
            if _matches_any_pattern(rel, patterns):
                filtered.append(p)
        files = filtered
    if not files:
        return []

    norm_name = _normalize_match_key(model_name)
    if norm_name:
        exact = [p for p in files if _normalize_match_key(p.stem) == norm_name]
        if exact:
            return exact
        partial = [p for p in files if norm_name in _normalize_match_key(p.stem)]
        if partial:
            return partial
        # For shared model directories, avoid deleting unrelated files.
        if target_dir.resolve().parent == models_root.resolve():
            return []
    return files


_WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf"}


def _repo_receipt_path(name: str, models_root: Path, target_dir: Path) -> Path:
    subdir = target_dir.resolve().relative_to(models_root.resolve()).as_posix()
    key = hashlib.sha256(f"{name}\0{subdir}".encode()).hexdigest()
    return models_root / ".download-state" / f"{key}.json"


def _validate_repo_weights(target_dir: Path, files: list[Path]) -> bool:
    if not any(path.suffix in _WEIGHT_SUFFIXES and path.stat().st_size > 0 for path in files):
        return False
    root = target_dir.resolve()
    for path in files:
        if not path.resolve().is_relative_to(root):
            return False
        if path.name.endswith(".index.json"):
            index = json.loads(path.read_text())
            for shard in index.get("weight_map", {}).values():
                required = (path.parent / shard).resolve()
                if not required.is_relative_to(root) or not required.is_file() or required.stat().st_size == 0:
                    return False
    return True


def record_repo_download(name: str, source: str, include: str, target_dir: Path, models_root: Path, required_files: list[str]) -> None:
    patterns = [part.strip() for part in include.split(",") if part.strip()]
    files = [target_dir / relative for relative in required_files
             if not patterns or _matches_any_pattern(relative, patterns)]
    if any(not path.resolve().is_relative_to(target_dir.resolve()) or not path.is_file() for path in files):
        raise ValueError("Repository download is missing required files")
    if not _validate_repo_weights(target_dir, files):
        raise ValueError("Repository download has no weights or is missing required shards")
    receipt = {
        "source": source, "include": include,
        "subdir": target_dir.resolve().relative_to(models_root.resolve()).as_posix(),
        "files": {path.relative_to(target_dir).as_posix(): path.stat().st_size for path in files},
    }
    path = _repo_receipt_path(name, models_root, target_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True))
    os.replace(temporary, path)


def _completed_repo_files(name: str, source: str, include: str, target_dir: Path, models_root: Path) -> list[Path]:
    try:
        receipt = json.loads(_repo_receipt_path(name, models_root, target_dir).read_text())
        if receipt["source"] != source or receipt["include"] != include:
            return []
        if receipt["subdir"] != target_dir.resolve().relative_to(models_root.resolve()).as_posix():
            return []
        recorded = receipt["files"]
        if not isinstance(recorded, dict) or not recorded:
            return []
        files = []
        for relative, size in recorded.items():
            path = target_dir / relative
            if not path.resolve().is_relative_to(target_dir.resolve()) or not path.is_file() or path.stat().st_size != size:
                return []
            files.append(path)
        return files if _validate_repo_weights(target_dir, files) else []
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def classify_model(name: str, source: str, subdir: str) -> str:
    key = f"{name} {source} {subdir}".lower()
    if "flux" in key:
        return "FLUX"
    if "wan" in key:
        return "WAN"
    if any(k in key for k in ["sdxl", "sd_xl", "stable-diffusion-xl", "-xl", "xl-"]):
        return "SDXL"
    return "OTHERS"


def ensure_manifest(
    manifest_path: Path,
    default_manifest_path: Path,
    models_dir: Path,
    config_dir: Path,
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists() and default_manifest_path.exists():
        shutil.copy(default_manifest_path, manifest_path)


def parse_manifest(
    manifest_path: Path,
    default_manifest_path: Path,
    models_dir: Path,
    config_dir: Path,
) -> List[ModelEntry]:
    ensure_manifest(manifest_path, default_manifest_path, models_dir, config_dir)
    entries: List[ModelEntry] = []
    if not manifest_path.exists():
        return entries
    subdir_to_type = {
        "checkpoints": "checkpoint",
        "vae": "vae",
        "vae_approx": "vae",
        "loras": "lora",
        "refiners": "refiner",
        "text_encoders": "text_encoder",
        "clip": "clip",
        "clip_vision": "clip_vision",
        "controlnet": "controlnet",
        "diffusers": "diffusers",
        "diffusion_models": "checkpoint",
        "embeddings": "embedding",
        "hypernetworks": "hypernetwork",
        "latent_upscale_models": "latent_upscale",
        "audio_encoders": "audio_encoder",
        "photomaker": "photomaker",
        "style_models": "style",
        "unet": "unet",
        "upscale_models": "upscale",
        "facerestore_models": "face_restoration",
    }

    def parse_size(raw: str) -> Optional[int]:
        if not raw:
            return None
        s = raw.strip().lower()
        try:
            if s.endswith("tb"):
                return int(float(s[:-2]) * 1024 * 1024 * 1024 * 1024)
            if s.endswith("gb"):
                return int(float(s[:-2]) * 1024 * 1024 * 1024)
            if s.endswith("mb"):
                return int(float(s[:-2]) * 1024 * 1024)
            if s.endswith("kb"):
                return int(float(s[:-2]) * 1024)
            # plain bytes
            if s.replace(".", "", 1).isdigit():
                return int(float(s))
        except Exception:
            return None
        return None

    with manifest_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            name, kind, source, subdir, *rest = parts
            include = rest[0] if rest else ""
            expected_size_bytes = parse_size(rest[1]) if len(rest) > 1 else None
            size_is_exact = len(rest) > 1 and rest[1].strip().isdigit()
            validation_size = expected_size_bytes if size_is_exact else None
            target_dir = contained_path(models_dir, subdir)
            target_dir.mkdir(parents=True, exist_ok=True)
            expected: List[Path] = []
            matched: List[Path] = []
            completed_repo_files: List[Path] = []
            legacy_path = None
            if kind in ("hf_file", "url"):
                canonical, legacy = file_paths(kind, source, subdir, models_dir)
                expected = [canonical]
                legacy_path = next((str(p) for p in legacy if valid_file(p, validation_size)), None)
            elif kind == "hf_repo":
                pats = [p.strip() for p in include.split(",") if p.strip()] if include else []
                matched.extend(_select_hf_repo_files(target_dir, pats, name, models_dir))
                completed_repo_files = _completed_repo_files(name, source, include, target_dir, models_dir)
                if completed_repo_files:
                    matched = completed_repo_files
            # If we have explicit expected files, check those
            if expected:
                matched.extend([p for p in expected if valid_file(p, validation_size)])
            # Prefer safetensors when summarizing size
            safes = [p for p in matched if p.suffix == ".safetensors"]
            use_files = safes or matched
            installed = len(use_files) > 0
            if kind == "hf_repo":
                installed = bool(completed_repo_files)
            size_bytes = sum(p.stat().st_size for p in use_files)
            primary_path = str(use_files[0]) if use_files else None
            if not installed and expected_size_bytes:
                size_bytes = expected_size_bytes
            category = classify_model(name, source, subdir)
            mtype = subdir_to_type.get(subdir.split("/")[0], "checkpoint")
            info_url = None
            if kind.startswith("hf_"):
                repo = source.split(":")[0]
                info_url = f"https://huggingface.co/{repo}"
            elif source.startswith("http"):
                info_url = source
            entries.append(
                ModelEntry(
                    name=name,
                    kind=kind,
                    source=source,
                    subdir=subdir,
                    include=include,
                    expected_size_bytes=expected_size_bytes,
                    size_is_exact=size_is_exact,
                    category=category,
                    type=mtype,
                    installed=installed,
                    size_bytes=size_bytes,
                    info_url=info_url,
                    target_path=str(target_dir),
                    primary_path=primary_path,
                    legacy_path=legacy_path,
                )
            )
    return entries


def delete_model(name: str, manifest_path: Path, models_dir: Path) -> int:
    line = None
    with manifest_path.open(encoding="utf-8") as f:
        for l in f:
            if l.strip().startswith("#") or not l.strip():
                continue
            parts = l.strip().split("|")
            if parts and parts[0] == name:
                line = parts
                break
    if not line:
        raise KeyError("Unknown model")
    parts = line + ["", "", "", ""]
    _, kind, source, subdir, include, *_ = parts
    target_dir = contained_path(models_dir, subdir)
    to_delete: list[Path] = []
    include = include.strip()

    def add_path(p: Path):
        if p.exists():
            to_delete.append(p)

    if kind in ("hf_file", "url"):
        canonical, _ = file_paths(kind, source, subdir, models_dir)
        add_path(canonical)
    else:
        patterns = [p.strip() for p in include.split(",") if p.strip()] if include else []
        completed_files = _completed_repo_files(name, source, include, target_dir, models_dir) if kind == "hf_repo" else []
        if completed_files:
            for path in completed_files:
                add_path(path)
        else:
            for p in _select_hf_repo_files(target_dir, patterns, name, models_dir):
                add_path(p)

    if kind == "hf_repo":
        _repo_receipt_path(name, models_dir, target_dir).unlink(missing_ok=True)
    deleted = 0
    for p in to_delete:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
            deleted += 1
        except Exception:
            pass
    return deleted


def model_name_for_expected_path(
    required_path: Path,
    manifest_path: Path,
    default_manifest_path: Path,
    models_dir: Path,
    config_dir: Path,
) -> Optional[str]:
    """
    Best-effort mapping from a local path referenced by configs (e.g. TOML)
    to a model name in the models manifest.
    """
    ensure_manifest(manifest_path, default_manifest_path, models_dir, config_dir)
    if not manifest_path.exists():
        return None

    try:
        required_resolved = required_path.resolve()
    except Exception:
        required_resolved = required_path

    with manifest_path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            name, kind, source, subdir, *rest = parts
            include = rest[0] if rest else ""
            target_dir = contained_path(models_dir, subdir)

            expected: list[Path] = []
            if kind == "hf_file":
                path_in_repo = source.split(":", 1)[1] if ":" in source else ""
                if path_in_repo:
                    expected.append(target_dir / path_in_repo)
                    expected.append(target_dir / Path(path_in_repo).name)
            elif kind == "url":
                fname = Path(source.split("?", 1)[0]).name
                expected.append(target_dir / fname)
            elif kind == "hf_repo":
                # Repo downloads can be directories. If the config points into the directory,
                # assume this repo is the likely match (only when include patterns are present).
                expected.append(target_dir)
            else:
                continue

            for p in expected:
                try:
                    cand = p.resolve()
                except Exception:
                    cand = p
                if cand == required_resolved:
                    return name
                if kind == "hf_repo":
                    try:
                        if required_resolved.is_relative_to(cand):  # py3.9+
                            # Avoid matching parent directories like /workspace/models
                            if cand == target_dir.resolve():
                                if include and include.strip():
                                    return name
                    except Exception:
                        pass
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Record a completed repository model download")
    parser.add_argument("action", choices=["begin", "complete"])
    parser.add_argument("name")
    parser.add_argument("source")
    parser.add_argument("include")
    parser.add_argument("target", type=Path)
    parser.add_argument("models_root", type=Path)
    args = parser.parse_args()
    if args.action == "begin":
        _repo_receipt_path(args.name, args.models_root, args.target).unlink(missing_ok=True)
    else:
        from huggingface_hub import HfApi
        required_files = HfApi().list_repo_files(repo_id=args.source, token=os.environ.get("HF_TOKEN") or None)
        record_repo_download(args.name, args.source, args.include, args.target, args.models_root, required_files)
