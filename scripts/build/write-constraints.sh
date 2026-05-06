#!/usr/bin/env bash
set -euo pipefail

config_dir="${1:-/opt/pilot/config}"
mkdir -p "${config_dir}"

: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${TORCHAUDIO_VERSION:?TORCHAUDIO_VERSION is required}"
: "${XFORMERS_VERSION:?XFORMERS_VERSION is required}"
: "${BITSANDBYTES_VERSION:?BITSANDBYTES_VERSION is required}"
: "${CORE_DIFFUSERS_VERSION:?CORE_DIFFUSERS_VERSION is required}"
: "${TRANSFORMERS_VERSION:?TRANSFORMERS_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"
: "${INVOKE_TORCH_VERSION:?INVOKE_TORCH_VERSION is required}"
: "${INVOKE_TORCHVISION_VERSION:?INVOKE_TORCHVISION_VERSION is required}"
: "${INVOKE_TORCHAUDIO_VERSION:?INVOKE_TORCHAUDIO_VERSION is required}"
: "${INVOKE_DIFFUSERS_VERSION:?INVOKE_DIFFUSERS_VERSION is required}"
: "${INVOKE_TRANSFORMERS_VERSION:?INVOKE_TRANSFORMERS_VERSION is required}"
: "${INVOKE_ACCELERATE_VERSION:?INVOKE_ACCELERATE_VERSION is required}"
: "${INVOKE_HF_HUB_VERSION:?INVOKE_HF_HUB_VERSION is required}"
: "${DIFFPIPE_DIFFUSERS_VERSION:?DIFFPIPE_DIFFUSERS_VERSION is required}"
: "${DIFFPIPE_TRANSFORMERS_VERSION:?DIFFPIPE_TRANSFORMERS_VERSION is required}"

cat > "${config_dir}/core-constraints.txt" <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==${BITSANDBYTES_VERSION}
numpy<2
pillow<12
huggingface-hub<1.0
diffusers==${CORE_DIFFUSERS_VERSION}
transformers==${TRANSFORMERS_VERSION}
peft==${PEFT_VERSION}
EOF

cat > "${config_dir}/invoke-constraints.txt" <<EOF
torch==${INVOKE_TORCH_VERSION}
torchvision==${INVOKE_TORCHVISION_VERSION}
torchaudio==${INVOKE_TORCHAUDIO_VERSION}
numpy<2
pillow<11
diffusers==${INVOKE_DIFFUSERS_VERSION}
transformers==${INVOKE_TRANSFORMERS_VERSION}
accelerate==${INVOKE_ACCELERATE_VERSION}
huggingface-hub==${INVOKE_HF_HUB_VERSION}
peft==${PEFT_VERSION}
EOF

cat > "${config_dir}/diffpipe-constraints.txt" <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
bitsandbytes==${BITSANDBYTES_VERSION}
numpy<2
pillow<12
huggingface-hub<1.0
diffusers==${DIFFPIPE_DIFFUSERS_VERSION}
transformers==${DIFFPIPE_TRANSFORMERS_VERSION}
accelerate==${INVOKE_ACCELERATE_VERSION}
peft==${PEFT_VERSION}
setuptools<81.0
EOF
