FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

# Install toggles (default: "ready to run on RunPod")
ARG INSTALL_GPU_STACK=1
ARG INSTALL_COMFY=1
ARG INSTALL_KOHYA=1

# Torch stack pins
ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip \
    tini supervisor openssl \
    software-properties-common build-essential iproute2 \
    libgl1 libglib2.0-0 \
    mc \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils python3.11-tk \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && rm -f /tmp/get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# user + dirs
RUN useradd -m -s /bin/bash -u 1000 pilot && \
    mkdir -p /workspace /opt/pilot /opt/pilot/repos /opt/venvs && \
    chown -R pilot:pilot /workspace /opt/pilot /opt/venvs

# code-server install
RUN curl -fsSL https://code-server.dev/install.sh | sh

# tools venv (jupyter lives here)
RUN python -m venv /opt/venvs/tools && \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venvs/tools/bin/pip install jupyterlab ipywidgets

# core venv (default python env for "pilot")
RUN python -m venv /opt/venvs/core && \
    /opt/venvs/core/bin/pip install --upgrade pip setuptools wheel

# GPU stack in core
RUN if [ "${INSTALL_GPU_STACK}" = "1" ]; then \
      /opt/venvs/core/bin/pip install \
        torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} torchaudio==${TORCHAUDIO_VERSION} \
        --index-url ${TORCH_INDEX_URL} && \
      /opt/venvs/core/bin/pip install \
        xformers==${XFORMERS_VERSION} \
        accelerate safetensors numpy pillow tqdm psutil && \
      /opt/venvs/core/bin/python -c "import torch; print('torch ok', torch.__version__)" ; \
    else \
      echo "Skipping GPU stack install (INSTALL_GPU_STACK=${INSTALL_GPU_STACK})"; \
    fi

# your API deps into core
RUN /opt/venvs/core/bin/pip install \
      fastapi \
      "uvicorn[standard]" \
      pydantic \
      python-multipart \
      pillow \
      Flask \
      Flask-CORS \
      requests \
      python-dotenv

# ComfyUI (runs from core)
RUN if [ "${INSTALL_COMFY}" = "1" ]; then \
      git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /opt/pilot/repos/ComfyUI && \
      /opt/venvs/core/bin/pip install -r /opt/pilot/repos/ComfyUI/requirements.txt ; \
    fi

# Kohya (runs from core) - fix sd-scripts editable requirement
RUN if [ "${INSTALL_KOHYA}" = "1" ]; then \
      git clone --depth 1 --recurse-submodules https://github.com/bmaltais/kohya_ss.git /opt/pilot/repos/kohya_ss && \
      SITEPKG="$$(/opt/venvs/core/bin/python -c 'import site; print(site.getsitepackages()[0])')" && \
      echo "/opt/pilot/repos/kohya_ss/sd-scripts" > "$${SITEPKG}/kohya_sd_scripts.pth" && \
      grep -vE '^[[:space:]]*-e[[:space:]]+\\./sd-scripts[[:space:]]*$$' \
        /opt/pilot/repos/kohya_ss/requirements.txt > /tmp/kohya-req.txt && \
      /opt/venvs/core/bin/pip install -r /tmp/kohya-req.txt && \
      rm -f /tmp/kohya-req.txt ; \
    fi

# make core the default python for pilot shells
ENV PATH=/opt/venvs/core/bin:/opt/venvs/tools/bin:$PATH
RUN echo 'source /opt/venvs/core/bin/activate >/dev/null 2>&1 || true' >> /home/pilot/.bashrc && \
    chown pilot:pilot /home/pilot/.bashrc

# copy config + scripts
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh

COPY scripts/start-jupyter.sh /opt/pilot/start-jupyter.sh
COPY scripts/start-code-server.sh /opt/pilot/start-code-server.sh
COPY scripts/comfy.sh /opt/pilot/comfy.sh
COPY scripts/kohya.sh /opt/pilot/kohya.sh
COPY scripts/pilot /usr/local/bin/pilot

COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

RUN chmod +x \
    /opt/pilot/bootstrap.sh \
    /opt/pilot/start-jupyter.sh \
    /opt/pilot/start-code-server.sh \
    /opt/pilot/comfy.sh \
    /opt/pilot/kohya.sh \
    /usr/local/bin/pilot

EXPOSE 8888 8443 5555 6666

ENV WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    COMFY_PORT=5555 \
    KOHYA_PORT=6666 \
    HOME=/home/pilot

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
