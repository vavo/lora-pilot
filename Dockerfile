FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    COMFY_PORT=5555 \
    KOHYA_PORT=6666 \
    INVOKE_PORT=9090 \
    HOME=/home/pilot \
    SHELL=/bin/bash \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    HF_XET_HIGH_PERFORMANCE=1

ARG INSTALL_GPU_STACK=1
ARG INSTALL_COMFY=1
ARG INSTALL_KOHYA=1
ARG INSTALL_INVOKE=1

ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3

# ----- base deps -----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip openssl \
    tini supervisor \
    software-properties-common build-essential \
    iproute2 \
    libgl1 libglib2.0-0 \
    mc \
  && apt-get -y upgrade \
  && apt-get -y autoremove --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# ----- python 3.11 -----
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils python3.11-tk \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && rm -f /tmp/get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# ----- user + dirs -----
RUN useradd -m -s /bin/bash -u 1000 pilot && \
    usermod -s /bin/bash pilot && \
    mkdir -p /workspace /opt/pilot /opt/pilot/repos /opt/venvs /opt/pilot/config && \
    chown -R pilot:pilot /workspace /opt/pilot /opt/pilot/repos

# ----- code-server -----
RUN curl -fsSL https://code-server.dev/install.sh | sh

# ----- venv: tools -----
RUN python -m venv /opt/venvs/tools && \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venvs/tools/bin/pip install jupyterlab ipywidgets

# ----- venv: core (torch etc) -----
RUN python -m venv /opt/venvs/core && \
    /opt/venvs/core/bin/pip install --upgrade pip setuptools wheel

RUN if [ "${INSTALL_GPU_STACK}" = "1" ]; then \
      /opt/venvs/core/bin/pip install \
        torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} torchaudio==${TORCHAUDIO_VERSION} \
        --index-url ${TORCH_INDEX_URL} && \
      /opt/venvs/core/bin/pip install \
        xformers==${XFORMERS_VERSION} \
        accelerate safetensors numpy pillow tqdm psutil ; \
    else \
      echo "Skipping GPU stack install (INSTALL_GPU_STACK=${INSTALL_GPU_STACK})"; \
    fi

# Hugging Face downloader tooling (handles gated + xet storage)
RUN /opt/venvs/core/bin/pip install --no-cache-dir "huggingface_hub[hf_transfer,hf_xet]"

# ----- API deps (core venv) -----
RUN /opt/venvs/core/bin/pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic python-multipart \
    pillow flask flask-cors requests python-dotenv

# ----- ComfyUI + Manager -----
RUN if [ "${INSTALL_COMFY}" = "1" ]; then \
      git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /opt/pilot/repos/ComfyUI && \
      /opt/venvs/core/bin/pip install --no-cache-dir -r /opt/pilot/repos/ComfyUI/requirements.txt && \
      mkdir -p /opt/pilot/repos/ComfyUI/custom_nodes && \
      git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Manager && \
      mkdir -p /workspace/comfy/user && \
      rm -rf /opt/pilot/repos/ComfyUI/user && \
      ln -s /workspace/comfy/user /opt/pilot/repos/ComfyUI/user ; \
    fi

# ----- Kohya (install into core venv, but DO NOT let it replace torch/xformers) -----
RUN if [ "${INSTALL_KOHYA}" = "1" ]; then \
  git clone --depth 1 --recurse-submodules https://github.com/bmaltais/kohya_ss.git /opt/pilot/repos/kohya_ss && \
  ln -sf /opt/pilot/repos/kohya_ss/requirements.txt /tmp/requirements.txt && \
  cd /opt/pilot/repos/kohya_ss && \
  REQ=requirements_runpod.txt; \
  [ -f "$REQ" ] || REQ=requirements_linux.txt; \
  [ -f "$REQ" ] || REQ=requirements.txt; \
  grep -v -E '(^[[:space:]]*tensorrt([[:space:]]|$)|^[[:space:]]*torch==|^[[:space:]]*torchvision==|^[[:space:]]*torchaudio==|^[[:space:]]*xformers==|^[[:space:]]*-e[[:space:]]+\./sd-scripts[[:space:]]*$|^[[:space:]]*\./sd-scripts[[:space:]]*$)' "$REQ" > /tmp/kohya-req.txt && \
  /opt/venvs/core/bin/pip install --no-cache-dir -r /tmp/kohya-req.txt && \
  rm -f /tmp/kohya-req.txt && \
  SITEPKG="$(/opt/venvs/core/bin/python -c 'import site; print(site.getsitepackages()[0])')" && \
  printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${SITEPKG}/kohya_sd_scripts.pth" && \
  printf '%s\n' \
    'from easygui import global_state as _gs' \
    'globals().update(_gs.__dict__)' \
    > "${SITEPKG}/global_state.py" \
  ; fi

# ----- InvokeAI in its OWN venv -----
RUN if [ "${INSTALL_INVOKE}" = "1" ]; then \
      python -m venv /opt/venvs/invoke && \
      /opt/venvs/invoke/bin/pip install --upgrade pip setuptools wheel && \
      /opt/venvs/invoke/bin/pip install --no-cache-dir invokeai ; \
    fi

# ----- project files -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY scripts/get-models.sh /opt/pilot/get-models.sh

COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh
COPY scripts/smoke-test.sh /opt/pilot/smoke-test.sh
COPY scripts/gpu-smoke-test.sh /opt/pilot/gpu-smoke-test.sh
COPY scripts/start-jupyter.sh /opt/pilot/start-jupyter.sh
COPY scripts/start-code-server.sh /opt/pilot/start-code-server.sh
COPY scripts/comfy.sh /opt/pilot/comfy.sh
COPY scripts/kohya.sh /opt/pilot/kohya.sh
COPY scripts/invoke.sh /opt/pilot/invoke.sh
COPY scripts/pilot /usr/local/bin/pilot
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

RUN ln -sf /opt/pilot/get-models.sh /usr/local/bin/models && \
    ln -sf /opt/pilot/get-models.sh /usr/local/bin/pilot-models && \
    mkdir -p /workspace /workspace/logs /workspace/outputs /workspace/models /workspace/custom_nodes /workspace/config && \
    chown -R pilot:pilot /workspace /opt/pilot /opt/pilot/repos && \
    chmod +x \
      /opt/pilot/get-models.sh \
      /opt/pilot/bootstrap.sh \
      /opt/pilot/smoke-test.sh \
      /opt/pilot/gpu-smoke-test.sh \
      /opt/pilot/start-jupyter.sh \
      /opt/pilot/start-code-server.sh \
      /opt/pilot/comfy.sh \
      /opt/pilot/kohya.sh \
      /opt/pilot/invoke.sh \
      /usr/local/bin/pilot

EXPOSE 8888 8443 5555 6666 9090

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
