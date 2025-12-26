FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

ARG INSTALL_GPU_STACK=0
ARG INSTALL_KOHYA=0

ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip \
    tini supervisor \
    openssl \
    software-properties-common \
    build-essential \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && \
    rm -f /tmp/get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    python --version && pip --version

RUN useradd -m -s /bin/bash -u 1000 pilot && \
    mkdir -p /workspace /opt/pilot /opt/venvs && \
    chown -R pilot:pilot /workspace /opt/pilot /opt/venvs

RUN curl -fsSL https://code-server.dev/install.sh | sh

RUN python -m venv /opt/venvs/tools && \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venvs/tools/bin/pip install jupyterlab ipywidgets

# --- Optional: kohya_ss trainer venv + repo ---
RUN if [ "${INSTALL_KOHYA}" = "1" ]; then \
      mkdir -p /opt/pilot/repos && \
      git clone --depth 1 https://github.com/bmaltais/kohya_ss.git /opt/pilot/repos/kohya_ss && \
      python -m venv /opt/venvs/kohya && \
      /opt/venvs/kohya/bin/pip install --upgrade pip setuptools wheel && \
      /opt/venvs/kohya/bin/pip install -r /opt/pilot/repos/kohya_ss/requirements.txt ; \
    fi

# --- Optional: core GPU stack venv ---
RUN if [ "${INSTALL_GPU_STACK}" = "1" ]; then \
      python -m venv /opt/venvs/core && \
      /opt/venvs/core/bin/pip install --upgrade pip setuptools wheel && \
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

COPY config/env.defaults /opt/pilot/config/env.defaults
COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh
COPY scripts/smoke-test.sh /opt/pilot/smoke-test.sh
COPY scripts/gpu-smoke-test.sh /opt/pilot/gpu-smoke-test.sh
COPY scripts/kohya.sh /opt/pilot/kohya.sh
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

RUN chmod +x \
    /opt/pilot/bootstrap.sh \
    /opt/pilot/smoke-test.sh \
    /opt/pilot/gpu-smoke-test.sh \
    /opt/pilot/kohya.sh

EXPOSE 8888 8443

ENV WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    HOME=/home/pilot

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
