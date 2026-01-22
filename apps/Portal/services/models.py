from __future__ import annotations

import fnmatch
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class ModelEntry(BaseModel):
    name: str
    kind: str
    source: str
    subdir: str
    include: Optional[str] = ""
    expected_size_bytes: Optional[int] = None
    category: str
    type: str
    installed: bool
    size_bytes: int
    info_url: Optional[str] = None
    target_path: str
    primary_path: Optional[str] = None


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

    with manifest_path.open() as f:
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
            target_dir = models_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            expected: List[Path] = []
            matched: List[Path] = []
            if kind == "hf_file":
                path_in_repo = source.split(":", 1)[1] if ":" in source else ""
                if path_in_repo:
                    expected = [target_dir / path_in_repo]
                    fallback = target_dir / Path(path_in_repo).name
                    if fallback not in expected:
                        expected.append(fallback)
            elif kind == "url":
                fname = Path(source.split("?", 1)[0]).name
                expected = [target_dir / fname]
            elif kind == "hf_repo":
                pats = [p.strip() for p in include.split(",") if p.strip()] if include else []
                matched.extend(_select_hf_repo_files(target_dir, pats, name, models_dir))
            # If we have explicit expected files, check those
            if expected:
                matched.extend([p for p in expected if p.exists()])
            # Prefer safetensors when summarizing size
            safes = [p for p in matched if p.suffix == ".safetensors"]
            use_files = safes or matched
            installed = len(use_files) > 0
            size_bytes = sum(p.stat().st_size for p in use_files)
            primary_path = str(use_files[0]) if use_files else None
            if not installed and expected_size_bytes:
                size_bytes = expected_size_bytes
            category = classify_model(name, source, subdir)
            mtype = subdir_to_type.get(subdir, "checkpoint")
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
                    category=category,
                    type=mtype,
                    installed=installed,
                    size_bytes=size_bytes,
                    info_url=info_url,
                    target_path=str(target_dir),
                    primary_path=primary_path,
                )
            )
    return entries


def delete_model(name: str, manifest_path: Path, models_dir: Path) -> int:
    line = None
    with manifest_path.open() as f:
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
    target_dir = models_dir / subdir
    to_delete: list[Path] = []
    include = include.strip()

    def add_path(p: Path):
        if p.exists():
            to_delete.append(p)

    if kind == "hf_file":
        path_in_repo = source.split(":", 1)[1] if ":" in source else source
        if path_in_repo:
            add_path(target_dir / path_in_repo)
            fallback = target_dir / os.path.basename(path_in_repo)
            add_path(fallback)
    elif kind == "url":
        add_path(target_dir / os.path.basename(source.split("?", 1)[0]))
    else:
        patterns = [p.strip() for p in include.split(",") if p.strip()] if include else []
        for p in _select_hf_repo_files(target_dir, patterns, name, models_dir):
            add_path(p)

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
