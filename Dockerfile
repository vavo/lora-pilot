FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    COMFY_PORT=5555 \
    KOHYA_PORT=6666 \
    INVOKE_PORT=9090 \
    DIFFPIPE_PORT=4444 \
    HOME=/workspace/home/root \
    SHELL=/bin/bash \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    HF_XET_HIGH_PERFORMANCE=1 \
    UMASK=0022

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/workspace/home/root/.cache \
    XDG_CONFIG_HOME=/workspace/home/root/.config \
    XDG_DATA_HOME=/workspace/home/root/.local/share

ARG INSTALL_GPU_STACK=1
ARG INSTALL_COMFY=1
ARG INSTALL_KOHYA=1
ARG INSTALL_INVOKE=1
ARG INSTALL_DIFFPIPE=1

ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3
ARG TRANSFORMERS_VERSION=4.44.2
ARG PEFT_VERSION=0.17.0
ARG INVOKE_TORCH_VERSION=2.7.0
ARG INVOKE_TORCHVISION_VERSION=0.22.0
ARG INVOKE_TORCHAUDIO_VERSION=2.7.0
ARG INVOKE_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
ARG CUDA_NVCC_PKG=cuda-nvcc-12-4
ARG CROC_VERSION=10.0.7

# ----- base deps -----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip openssl \
    tini supervisor \
    software-properties-common build-essential \
    iproute2 \
    libgl1 libglib2.0-0 \
    whiptail \
    ${CUDA_NVCC_PKG} \
    mc nano \
  && apt-get -y upgrade \
  && apt-get -y autoremove --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# ----- croc -----
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "${arch}" in \
      amd64) croc_arch="Linux-64bit" ;; \
      arm64) croc_arch="Linux-ARM64" ;; \
      *) echo "Unsupported arch for croc: ${arch}" >&2; exit 1 ;; \
    esac; \
    url="https://github.com/schollz/croc/releases/download/v${CROC_VERSION}/croc_v${CROC_VERSION}_${croc_arch}.tar.gz"; \
    tmp_dir="$(mktemp -d)"; \
    curl -fL "${url}" -o "${tmp_dir}/croc.tgz"; \
    tar -xzf "${tmp_dir}/croc.tgz" -C "${tmp_dir}"; \
    croc_path="$(find "${tmp_dir}" -maxdepth 2 -type f -name croc -print -quit)"; \
    [ -n "${croc_path}" ] || { echo "croc binary not found in ${url}" >&2; exit 1; }; \
    install -m 0755 "${croc_path}" /usr/local/bin/croc; \
    rm -rf "${tmp_dir}"; \
    croc --version

# ----- python 3.11 -----
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils python3.11-tk python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && rm -f /tmp/get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# ----- dirs -----
RUN mkdir -p /workspace /opt/pilot /opt/pilot/repos /opt/venvs /opt/pilot/config /workspace/home/root
RUN mkdir -p /workspace/home/root/.cache/pip /workspace/home/root/.fonts


# ----- code-server -----
RUN curl -fsSL https://code-server.dev/install.sh | sh

# ----- venv: tools -----
RUN set -eux; \
    python -m venv /opt/venvs/tools; \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel; \
    /opt/venvs/tools/bin/pip install --no-cache-dir jupyterlab ipywidgets

# ----- venv: core -----
RUN set -eux; \
    python -m venv /opt/venvs/core; \
    /opt/venvs/core/bin/pip install --upgrade pip "setuptools<81.0" wheel

# ----- core constraints (keep the stack sane) -----
RUN set -eux; \
    cat > /opt/pilot/config/core-constraints.txt <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==0.46.0
numpy<2
pillow<12
huggingface-hub<1.0
transformers==${TRANSFORMERS_VERSION}
peft==${PEFT_VERSION}
EOF
ENV PIP_CONSTRAINT=/opt/pilot/config/core-constraints.txt

RUN set -eux; \
    cat > /tmp/kohya-constraints.txt <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==0.46.0
numpy<2
pillow<12
huggingface-hub<1.0
transformers==${TRANSFORMERS_VERSION}
peft==${PEFT_VERSION}
EOF

# ----- GPU stack (core venv) -----
RUN if [ "${INSTALL_GPU_STACK}" = "1" ]; then \
      set -eux; \
      /opt/venvs/core/bin/pip install --no-cache-dir \
        torch==${TORCH_VERSION} \
        torchvision==${TORCHVISION_VERSION} \
        torchaudio==${TORCHAUDIO_VERSION} \
        --index-url ${TORCH_INDEX_URL}; \
    /opt/venvs/core/bin/pip install --no-cache-dir \
      -c /opt/pilot/config/core-constraints.txt \
      xformers==${XFORMERS_VERSION} \
      bitsandbytes==0.46.0 \
      toml \
      accelerate \
      transformers==${TRANSFORMERS_VERSION} \
      peft==${PEFT_VERSION} \
      safetensors \
      "numpy<2" \
        "pillow<12" \
        tqdm \
        psutil; \
    else \
      echo "Skipping GPU stack install (INSTALL_GPU_STACK=${INSTALL_GPU_STACK})"; \
    fi

# Hugging Face downloader tooling (handles gated + xet storage)
RUN /opt/venvs/core/bin/pip install --no-cache-dir \
    -c /opt/pilot/config/core-constraints.txt \
    "huggingface_hub[hf_transfer,hf_xet]"

# ----- API deps (core venv) -----
RUN /opt/venvs/core/bin/pip install --no-cache-dir \
    -c /opt/pilot/config/core-constraints.txt \
    fastapi "uvicorn[standard]" pydantic python-multipart \
    flask flask-cors requests python-dotenv \
    python-socketio

# ----- ComfyUI + Manager -----
RUN if [ "${INSTALL_COMFY}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /opt/pilot/repos/ComfyUI && \
      \
      # Filter out packages that must NOT be overridden in core
      grep -v -E '^(torch|torchvision|torchaudio|xformers|triton|bitsandbytes|numpy|pillow|Pillow|diffusers|transformers|peft|huggingface-hub|accelerate)' \
        /opt/pilot/repos/ComfyUI/requirements.txt > /tmp/comfy-req.txt && \
      \
      # Install Comfy deps constrained to your core stack rules
      /opt/venvs/core/bin/pip install --no-cache-dir \
        -c /opt/pilot/config/core-constraints.txt \
        -r /tmp/comfy-req.txt && \
      rm -f /tmp/comfy-req.txt && \
      \
      mkdir -p /opt/pilot/repos/ComfyUI/custom_nodes && \
      git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git \
        /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Manager && \
      \
      mkdir -p /workspace/apps/comfy/user && \
      rm -rf /opt/pilot/repos/ComfyUI/user && \
      ln -s /workspace/apps/comfy/user /opt/pilot/repos/ComfyUI/user; \
    fi

# ----- Kohya (install into core venv, but DO NOT let it replace torch/xformers) -----
RUN if [ "${INSTALL_KOHYA}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 --recurse-submodules https://github.com/bmaltais/kohya_ss.git /opt/pilot/repos/kohya_ss && \
      cd /opt/pilot/repos/kohya_ss && \
      \
      # Some kohya req files include "-r /tmp/requirements.txt" (runpod style). Provide it.
      ln -sf /opt/pilot/repos/kohya_ss/requirements.txt /tmp/requirements.txt && \
      \
      REQ=requirements_runpod.txt && \
      [ -f "$REQ" ] || REQ=requirements_linux.txt && \
      [ -f "$REQ" ] || REQ=requirements.txt && \
      \
      # Filter out container-hostile / unwanted deps (and avoid recursive -r /tmp/requirements.txt)
      grep -v -E '^(tensorrt|torch|torchvision|torchaudio|xformers|triton|bitsandbytes|transformers|tensorflow|tensorboard)' \
        "$REQ" > /tmp/kohya-req.txt && \
      \
      # Hard constraints so pip can't "helpfully" bring back numpy 2.x
      printf '%s\n' 'numpy<2' > /tmp/kohya-constraints.txt && \
      \
      /opt/venvs/core/bin/pip install --no-cache-dir -c /tmp/kohya-constraints.txt -r /tmp/kohya-req.txt && \
      rm -f /tmp/kohya-req.txt /tmp/kohya-constraints.txt && \
      \
      SITEPKG=$(/opt/venvs/core/bin/python -c 'import site; print(site.getsitepackages()[0])') && \
      printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${SITEPKG}/kohya_sd_scripts.pth" && \
      printf '%s\n' \
        'from easygui import global_state as _gs' \
        'globals().update(_gs.__dict__)' \
        > "${SITEPKG}/global_state.py"; \
    fi

# ----- Diffusion Pipe (training stack, core venv) -----
RUN if [ "${INSTALL_DIFFPIPE}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 --recurse-submodules \
        https://github.com/tdrussell/diffusion-pipe.git /opt/pilot/repos/diffusion-pipe && \
      /opt/venvs/core/bin/pip install --no-cache-dir \
        -r /opt/pilot/repos/diffusion-pipe/requirements.txt; \
    fi

# ----- InvokeAI (dedicated venv; pinned to core torch stack) -----
RUN if [ "${INSTALL_INVOKE}" = "1" ]; then \
      set -eux && \
      python -m venv /opt/venvs/invoke && \
      /opt/venvs/invoke/bin/pip install --upgrade pip setuptools wheel && \
      \
      # Install Invoke-specific torch stack first (kept separate from core)
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cu126 \
        torch==${INVOKE_TORCH_VERSION} \
        torchvision==${INVOKE_TORCHVISION_VERSION} \
        torchaudio==${INVOKE_TORCHAUDIO_VERSION} && \
      \
      # Install InvokeAI v6.10.0 (latest) after torch is in place
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install "invokeai==6.10.0" && \
      \
      # Install additional invoke deps with explicit pins (skip core constraint to allow different transformers); also pin numpy<2
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir \
        "diffusers[torch]==0.33.0" \
        "numpy<2"; \
      fi


# ----- project files -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY scripts/get-models.sh /opt/pilot/get-models.sh
COPY scripts/get-modelsgui.sh /opt/pilot/get-modelsgui.sh

COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh
COPY scripts/smoke-test.sh /opt/pilot/smoke-test.sh
COPY scripts/gpu-smoke-test.sh /opt/pilot/gpu-smoke-test.sh
COPY scripts/start-jupyter.sh /opt/pilot/start-jupyter.sh
COPY scripts/start-code-server.sh /opt/pilot/start-code-server.sh
COPY scripts/comfy.sh /opt/pilot/comfy.sh
COPY scripts/start-kohya.sh /opt/pilot/start-kohya.sh
COPY scripts/kohya.sh /opt/pilot/kohya.sh
COPY scripts/diffusion-pipe.sh /opt/pilot/diffusion-pipe.sh
COPY scripts/invoke.sh /opt/pilot/invoke.sh
COPY scripts/tagpilot.sh /opt/pilot/tagpilot.sh
COPY scripts/portal.sh /opt/pilot/portal.sh
COPY scripts/pilot /usr/local/bin/pilot
COPY apps /opt/pilot/apps
COPY README.md /opt/pilot/README.md
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# Default shell: activate core venv for root sessions
RUN echo 'source /opt/venvs/core/bin/activate' > /etc/profile.d/core-venv.sh && \
    chmod 644 /etc/profile.d/core-venv.sh

# Normalize line endings, ensure shebang exists, set exec bits, create symlinks, create dirs.
# IMPORTANT: do NOT chown -R /workspace (RunPod volumes often disallow it).
RUN set -eux; \
    for f in \
      /opt/pilot/bootstrap.sh \
      /opt/pilot/smoke-test.sh \
      /opt/pilot/gpu-smoke-test.sh \
      /opt/pilot/start-jupyter.sh \
      /opt/pilot/start-code-server.sh \
      /opt/pilot/comfy.sh \
      /opt/pilot/start-kohya.sh \
      /opt/pilot/kohya.sh \
      /opt/pilot/diffusion-pipe.sh \
      /opt/pilot/invoke.sh \
      /opt/pilot/tagpilot.sh \
      /opt/pilot/portal.sh \
      /opt/pilot/get-models.sh \
      /opt/pilot/get-modelsgui.sh \
      /usr/local/bin/pilot \
    ; do \
      sed -i 's/\r$//' "$f"; \
      head -n 1 "$f" | grep -q '^#!' || (echo "Missing shebang in $f" >&2; exit 1); \
      chmod +x "$f"; \
    done; \
    if [ -d /opt/pilot/apps ]; then \
      find /opt/pilot/apps -type f -name '*.sh' -print0 | xargs -0 -r chmod +x; \
      find /opt/pilot/apps -type f -name '*.sh' -print0 | xargs -0 -r sed -i 's/\r$//'; \
    fi; \
    ln -sf /opt/pilot/get-models.sh /usr/local/bin/models; \
    ln -sf /opt/pilot/get-models.sh /usr/local/bin/pilot-models; \
    ln -sf /opt/pilot/get-modelsgui.sh /usr/local/bin/modelsgui; \
    mkdir -p /workspace /workspace/logs /workspace/outputs /workspace/outputs/comfy /workspace/outputs/invoke /workspace/datasets /workspace/datasets/images /workspace/datasets/ZIPs /workspace/models /workspace/config /workspace/cache /workspace/home; \
    cp /opt/pilot/config/core-constraints.txt /workspace/config/core-constraints.txt || true

EXPOSE 8888 8443 5555 6666 9090 4444

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
