#!/usr/bin/env bash
set -euo pipefail

config_dir="${1:-/opt/pilot/config}"
mkdir -p "${config_dir}"

: "${TORCH_VERSION:?TORCH_VERSION is required}"
: "${TORCHVISION_VERSION:?TORCHVISION_VERSION is required}"
: "${XFORMERS_VERSION:?XFORMERS_VERSION is required}"
: "${BITSANDBYTES_VERSION:?BITSANDBYTES_VERSION is required}"
: "${CORE_DIFFUSERS_VERSION:?CORE_DIFFUSERS_VERSION is required}"
: "${TRANSFORMERS_VERSION:?TRANSFORMERS_VERSION is required}"
: "${UV_VERSION:?UV_VERSION is required}"
: "${PEFT_VERSION:?PEFT_VERSION is required}"
: "${ACCELERATE_VERSION:?ACCELERATE_VERSION is required}"
: "${HF_HUB_VERSION:?HF_HUB_VERSION is required}"
: "${FASTAPI_VERSION:?FASTAPI_VERSION is required}"
: "${UVICORN_VERSION:?UVICORN_VERSION is required}"
: "${PYDANTIC_VERSION:?PYDANTIC_VERSION is required}"
: "${PYTHON_MULTIPART_VERSION:?PYTHON_MULTIPART_VERSION is required}"
: "${FLASK_VERSION:?FLASK_VERSION is required}"
: "${FLASK_CORS_VERSION:?FLASK_CORS_VERSION is required}"
: "${REQUESTS_VERSION:?REQUESTS_VERSION is required}"
: "${PYTHON_DOTENV_VERSION:?PYTHON_DOTENV_VERSION is required}"
: "${PYTHON_SOCKETIO_VERSION:?PYTHON_SOCKETIO_VERSION is required}"
: "${WEBSOCKETS_VERSION:?WEBSOCKETS_VERSION is required}"
: "${HTTPX_VERSION:?HTTPX_VERSION is required}"
: "${INVOKE_TORCH_VERSION:?INVOKE_TORCH_VERSION is required}"
: "${INVOKE_TORCHVISION_VERSION:?INVOKE_TORCHVISION_VERSION is required}"
: "${INVOKE_XFORMERS_VERSION:?INVOKE_XFORMERS_VERSION is required}"
: "${INVOKE_DIFFUSERS_VERSION:?INVOKE_DIFFUSERS_VERSION is required}"
: "${INVOKE_TRANSFORMERS_VERSION:?INVOKE_TRANSFORMERS_VERSION is required}"
: "${INVOKE_ACCELERATE_VERSION:?INVOKE_ACCELERATE_VERSION is required}"
: "${INVOKE_HF_HUB_VERSION:?INVOKE_HF_HUB_VERSION is required}"
: "${DIFFPIPE_DIFFUSERS_VERSION:?DIFFPIPE_DIFFUSERS_VERSION is required}"
: "${DIFFPIPE_TRANSFORMERS_VERSION:?DIFFPIPE_TRANSFORMERS_VERSION is required}"
: "${TENSORBOARD_VERSION:?TENSORBOARD_VERSION is required}"

torchaudio_constraint=""
if [[ -n "${TORCHAUDIO_VERSION:-}" ]]; then
  torchaudio_constraint="torchaudio==${TORCHAUDIO_VERSION}"
fi

cat > "${config_dir}/core-constraints.txt" <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
${torchaudio_constraint}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==${BITSANDBYTES_VERSION}
numpy<2
pillow<12
huggingface-hub==${HF_HUB_VERSION}
diffusers==${CORE_DIFFUSERS_VERSION}
transformers==${TRANSFORMERS_VERSION}
uv==${UV_VERSION}
peft==${PEFT_VERSION}
accelerate==${ACCELERATE_VERSION}
fastapi==${FASTAPI_VERSION}
uvicorn==${UVICORN_VERSION}
pydantic==${PYDANTIC_VERSION}
python-multipart==${PYTHON_MULTIPART_VERSION}
flask==${FLASK_VERSION}
flask-cors==${FLASK_CORS_VERSION}
requests==${REQUESTS_VERSION}
python-dotenv==${PYTHON_DOTENV_VERSION}
python-socketio==${PYTHON_SOCKETIO_VERSION}
websockets==${WEBSOCKETS_VERSION}
httpx==${HTTPX_VERSION}
EOF

cat > "${config_dir}/invoke-constraints.txt" <<EOF
torch==${INVOKE_TORCH_VERSION}
torchvision==${INVOKE_TORCHVISION_VERSION}
xformers==${INVOKE_XFORMERS_VERSION}
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
${torchaudio_constraint}
xformers==${XFORMERS_VERSION}
bitsandbytes==${BITSANDBYTES_VERSION}
numpy<2
pillow<12
huggingface-hub==${HF_HUB_VERSION}
diffusers==${DIFFPIPE_DIFFUSERS_VERSION}
transformers==${DIFFPIPE_TRANSFORMERS_VERSION}
accelerate==${ACCELERATE_VERSION}
peft==${PEFT_VERSION}
tensorboard==${TENSORBOARD_VERSION}
setuptools<81.0
EOF
