#!/usr/bin/env bash
set -euo pipefail

[[ -x /opt/venvs/core/bin/python ]] || { echo "core venv missing" >&2; exit 1; }
core_cuda="$(/opt/venvs/core/bin/python -c 'import torch; print(torch.version.cuda)')"
for service in core kohya invoke ai-toolkit; do
  python_bin="/opt/venvs/${service}/bin/python"
  [[ -x "${python_bin}" ]] || continue
  echo "[gpu-smoke] ${service}"
  "${python_bin}" -m pip check
  "${python_bin}" - "${service}" "${core_cuda}" <<'PY'
import sys
from pathlib import Path
import torch
import torchvision
import xformers
import xformers.ops

service = sys.argv[1]
root = Path(sys.executable).parent.parent
assert Path(torch.__file__).is_relative_to(root), torch.__file__
assert torch.cuda.is_available(), "GPU unavailable; this is not a GPU smoke pass"
assert torch.version.cuda in ("12.8", "13.0"), torch.version.cuda
if service == "invoke":
    assert torch.version.cuda == "12.8", "InvokeAI requires its own cu128 stack"
else:
    assert torch.version.cuda == sys.argv[2], "Service CUDA differs from core"
    import torchaudio
    assert torchaudio.__version__.split('+')[0] == torch.__version__.split('+')[0]
print("torch", torch.__version__, "CUDA", torch.version.cuda,
      "cuDNN", torch.backends.cudnn.version(), "xformers", xformers.__version__)
print("GPU", torch.cuda.get_device_name(0))
a = torch.randn((256, 256), device="cuda")
assert torch.isfinite(a @ a).all()
# Exercise the cuDNN 3D-convolution path used by video VAEs.
conv = torch.nn.Conv3d(4, 8, 3, padding=1).cuda().half()
y = conv(torch.randn((1, 4, 4, 16, 16), device="cuda", dtype=torch.float16))
assert torch.isfinite(y).all()
q = torch.randn((1, 32, 2, 64), device="cuda", dtype=torch.float16)
assert torch.isfinite(xformers.ops.memory_efficient_attention(q, q, q)).all()
if service == "kohya":
    from transformers import CLIPFeatureExtractor, Dinov2WithRegistersConfig
elif service == "ai-toolkit":
    from torchao.quantization.quant_api import Float8WeightOnlyConfig, Int8WeightOnlyConfig
    from torchcodec.decoders import VideoDecoder
    import peft
elif service == "invoke":
    import invokeai
    import diffusers
    import transformers
    import peft
torch.cuda.synchronize()
PY
done

echo "[gpu-smoke] All installed environments passed"
