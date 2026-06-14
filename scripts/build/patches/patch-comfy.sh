#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/opt/pilot/repos/ComfyUI}"
target_file="${repo_dir}/comfy/ldm/lightricks/vae/audio_vae.py"

if [[ ! -f "${target_file}" ]]; then
  echo "ComfyUI audio VAE patch target not found: ${target_file}" >&2
  exit 1
fi

python3 - "${target_file}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()

if "def _require_torchaudio()" in text:
    raise SystemExit(0)

required = [
    "import torchaudio\n",
    "return torchaudio.functional.resample(waveform, source_rate, self.target_sample_rate)",
    "mel_transform = torchaudio.transforms.MelSpectrogram(",
]
missing = [snippet for snippet in required if snippet not in text]
if missing:
    raise SystemExit(f"ComfyUI audio VAE patch target changed; missing snippet: {missing[0]!r}")

text = text.replace(
    "import torchaudio\n",
    """try:
    import torchaudio
except ModuleNotFoundError:
    torchaudio = None


def _require_torchaudio():
    if torchaudio is None:
        raise RuntimeError(
            "ComfyUI audio VAE requires torchaudio, but this CUDA profile has no compatible torchaudio wheel."
        )
    return torchaudio
""",
)
text = text.replace(
    "return torchaudio.functional.resample(waveform, source_rate, self.target_sample_rate)",
    "return _require_torchaudio().functional.resample(waveform, source_rate, self.target_sample_rate)",
)
text = text.replace(
    "mel_transform = torchaudio.transforms.MelSpectrogram(",
    "mel_transform = _require_torchaudio().transforms.MelSpectrogram(",
)

path.write_text(text)
PY
