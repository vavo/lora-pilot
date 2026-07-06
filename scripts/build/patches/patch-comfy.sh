#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/opt/pilot/repos/ComfyUI}"

python3 - "${repo_dir}" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1])

TORCHAUDIO_GUARD = """try:
    import torchaudio
except ModuleNotFoundError:
    torchaudio = None


def _require_torchaudio():
    if torchaudio is None:
        raise RuntimeError(
            "ComfyUI audio VAE requires torchaudio, but this CUDA profile has no compatible torchaudio wheel."
        )
    return torchaudio
"""

TORCHAUDIO_MODULES = (
    "comfy/ldm/lightricks/vae/audio_vae.py",
    "comfy/audio_encoders/audio_encoders.py",
    "comfy/audio_encoders/whisper.py",
    "comfy_extras/nodes_audio.py",
    "comfy_extras/nodes_lt.py",
    "comfy_extras/nodes_wandancer.py",
)

IMPORT_DEPENDENCY_MODULES = (
    "comfy_extras/nodes_lt_audio.py",
    "comfy_extras/nodes_audio_encoder.py",
)

for rel_path in TORCHAUDIO_MODULES:
    path = repo / rel_path
    if not path.is_file():
        raise SystemExit(f"ComfyUI torchaudio patch target not found: {path}")

    text = path.read_text()
    if "def _require_torchaudio()" not in text:
        if "import torchaudio\n" not in text:
            raise SystemExit(f"ComfyUI torchaudio patch target changed: {rel_path}")
        text = text.replace("import torchaudio\n", TORCHAUDIO_GUARD, 1)

    text = text.replace("torchaudio.", "_require_torchaudio().")
    path.write_text(text)

for rel_path in IMPORT_DEPENDENCY_MODULES:
    path = repo / rel_path
    if not path.is_file():
        raise SystemExit(f"ComfyUI optional audio import target not found: {path}")
PY
