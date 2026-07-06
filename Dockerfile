ARG CUDA_BASE_IMAGE=nvidia/cuda:13.0.2-runtime-ubuntu22.04
FROM ${CUDA_BASE_IMAGE}

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG CUDA_PROFILE=cu130

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    COMFY_PORT=5555 \
    KOHYA_PORT=6666 \
    INVOKE_PORT=9090 \
    DIFFPIPE_PORT=4444 \
    AI_TOOLKIT_PORT=8675 \
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
ARG INSTALL_AI_TOOLKIT=1
ARG INSTALL_AI_TOOLKIT_UI=1
ARG INSTALL_COPILOT_CLI=1
ARG COPILOT_CLI_VERSION=1.0.10
ARG CODE_SERVER_VERSION=4.127.0
ARG NODE_MAJOR=24
ARG NPM_VERSION=11.18.0
ARG JUPYTERLAB_VERSION=4.6.1
ARG IPYWIDGETS_VERSION=8.1.8
ARG COMFYUI_REF=v0.27.0
ARG COMFYUI_MANAGER_REF=4.2.2
ARG COMFYUI_DOWNLOADER_REF=03146df738191004a8aad8264dca5c3530907f56
ARG KOHYA_REF=v25.2.1
ARG DIFFPIPE_REF=a7e7decf4325c1f03e4b88b7de93640029abd011
ARG AI_TOOLKIT_REF=6c0d1c4679cf8fe153ef56bdc779c93239e1cf0f
ARG AI_TOOLKIT_DIFFUSERS_VERSION=git
ARG DIFFPIPE_DIFFUSERS_VERSION=0.38.0
ARG DIFFPIPE_TRANSFORMERS_VERSION=5.11.0
ARG TENSORBOARD_VERSION=2.21.0

ARG TORCH_VERSION=2.11.0
ARG TORCHVISION_VERSION=0.26.0
ARG TORCHAUDIO_VERSION=2.11.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
ARG XFORMERS_VERSION=0.0.35
ARG BITSANDBYTES_VERSION=0.49.2
ARG CORE_DIFFUSERS_VERSION=0.38.0
ARG TRANSFORMERS_VERSION=5.11.0
ARG UV_VERSION=0.11.26
ARG DEEPDIFF_VERSION=9.1.0
ARG GGUF_VERSION=0.19.0
ARG TOMLKIT_VERSION=0.15.0
ARG PEFT_VERSION=0.19.1
ARG ACCELERATE_VERSION=1.14.0
ARG HF_HUB_VERSION=1.19.0
ARG FASTAPI_VERSION=0.139.0
ARG UVICORN_VERSION=0.50.0
ARG PYDANTIC_VERSION=2.13.4
ARG PYTHON_MULTIPART_VERSION=0.0.32
ARG FLASK_VERSION=3.1.3
ARG FLASK_CORS_VERSION=6.0.5
ARG REQUESTS_VERSION=2.34.2
ARG PYTHON_DOTENV_VERSION=1.2.2
ARG PYTHON_SOCKETIO_VERSION=5.16.3
ARG WEBSOCKETS_VERSION=16.0
ARG HTTPX_VERSION=0.28.1
ARG INVOKEAI_VERSION=6.13.5
ARG INVOKE_TORCH_VERSION=2.7.1+cu128
ARG INVOKE_TORCHVISION_VERSION=0.22.1+cu128
ARG INVOKE_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG INVOKE_XFORMERS_VERSION=0.0.31.post1
ARG INVOKE_DIFFUSERS_VERSION=0.37.0
ARG INVOKE_TRANSFORMERS_VERSION=5.5.4
ARG INVOKE_ACCELERATE_VERSION=1.14.0
ARG INVOKE_HF_HUB_VERSION=1.22.0
ARG CUDA_NVCC_PKG=cuda-nvcc-13-0
ARG CROC_VERSION=10.4.2

# ----- LAYER 1: System build scripts (stable, rarely changed) -----
COPY scripts/build/install-system-tools.sh \
     scripts/build/install-base-python.sh \
     scripts/build/install-code-server.sh \
     scripts/build/install-copilot-cli.sh \
     /opt/pilot/build/
RUN chmod +x /opt/pilot/build/*.sh

# ----- LAYER 2: System + Python (stable, rarely changes) -----
RUN /opt/pilot/build/install-system-tools.sh && \
    /opt/pilot/build/install-base-python.sh && \
    /opt/pilot/build/install-code-server.sh && \
    /opt/pilot/build/install-copilot-cli.sh

# ----- LAYER 3: Python venv setup + constraints (stable) -----
COPY scripts/build/lib/python_venv.sh /opt/pilot/build/lib/
COPY scripts/build/create-venvs.sh \
     scripts/build/write-constraints.sh \
     /opt/pilot/build/
RUN find /opt/pilot/build -type f -name '*.sh' -exec chmod +x {} +
RUN /opt/pilot/build/create-venvs.sh && \
    /opt/pilot/build/write-constraints.sh /opt/pilot/config

# ----- LAYER 4: Core PyTorch/ML stack (semi-stable, use ARG for cache busting) -----
# Cache key: explicitly reference PyTorch/core versions
COPY scripts/build/install-core-stack.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/install-core-stack.sh
ARG TORCH_CACHE_BUST="${CUDA_PROFILE}-${TORCH_VERSION}-${TORCHVISION_VERSION}-${TORCHAUDIO_VERSION}-${XFORMERS_VERSION}-${BITSANDBYTES_VERSION}-${CORE_DIFFUSERS_VERSION}-${TRANSFORMERS_VERSION}-${UV_VERSION}-${DEEPDIFF_VERSION}-${GGUF_VERSION}-${TOMLKIT_VERSION}-${PEFT_VERSION}-${ACCELERATE_VERSION}-${HF_HUB_VERSION}-${FASTAPI_VERSION}-${UVICORN_VERSION}-${PYDANTIC_VERSION}-${HTTPX_VERSION}"
RUN echo "TORCH_CACHE_BUST=${TORCH_CACHE_BUST}" >/dev/null && \
    /opt/pilot/build/install-core-stack.sh

# ----- LAYER 5-9: Service installs (variable frequency, separated by service) -----
# These layers rebuild independently when service refs change
COPY scripts/build/lib/git_checkout.sh /opt/pilot/build/lib/
COPY scripts/build/patches/patch-comfy.sh /opt/pilot/build/patches/
COPY scripts/build/install-comfy.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/lib/git_checkout.sh /opt/pilot/build/patches/patch-comfy.sh /opt/pilot/build/install-comfy.sh
ARG COMFY_CACHE_BUST="${COMFYUI_REF}-${COMFYUI_MANAGER_REF}-${COMFYUI_DOWNLOADER_REF}"
RUN echo "COMFY_CACHE_BUST=${COMFY_CACHE_BUST}" >/dev/null && \
    if [ "${INSTALL_COMFY:-1}" = "1" ]; then /opt/pilot/build/install-comfy.sh; fi

COPY scripts/build/patches/patch-kohya.sh /opt/pilot/build/patches/
COPY scripts/build/install-kohya.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/patches/patch-kohya.sh /opt/pilot/build/install-kohya.sh
ARG KOHYA_CACHE_BUST="${KOHYA_REF}"
RUN echo "KOHYA_CACHE_BUST=${KOHYA_CACHE_BUST}" >/dev/null && \
    if [ "${INSTALL_KOHYA:-1}" = "1" ]; then /opt/pilot/build/install-kohya.sh; fi

COPY scripts/build/install-diffpipe.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/install-diffpipe.sh
ARG DIFFPIPE_CACHE_BUST="${DIFFPIPE_REF}-${XFORMERS_VERSION}-${BITSANDBYTES_VERSION}-${DIFFPIPE_DIFFUSERS_VERSION}-${DIFFPIPE_TRANSFORMERS_VERSION}-${ACCELERATE_VERSION}-${PEFT_VERSION}-${TENSORBOARD_VERSION}"
RUN echo "DIFFPIPE_CACHE_BUST=${DIFFPIPE_CACHE_BUST}" >/dev/null && \
    if [ "${INSTALL_DIFFPIPE:-1}" = "1" ]; then /opt/pilot/build/install-diffpipe.sh; fi

COPY scripts/build/install-invoke.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/install-invoke.sh
ARG INVOKE_CACHE_BUST="${INVOKEAI_VERSION}-${INVOKE_TORCH_VERSION}-${INVOKE_TORCHVISION_VERSION}-${INVOKE_XFORMERS_VERSION}-${INVOKE_DIFFUSERS_VERSION}-${INVOKE_TRANSFORMERS_VERSION}-${INVOKE_ACCELERATE_VERSION}-${INVOKE_HF_HUB_VERSION}-${PEFT_VERSION}"
RUN echo "INVOKE_CACHE_BUST=${INVOKE_CACHE_BUST}" >/dev/null && \
    if [ "${INSTALL_INVOKE:-1}" = "1" ]; then /opt/pilot/build/install-invoke.sh; fi

COPY scripts/build/patches/patch-ai-toolkit.sh /opt/pilot/build/patches/
COPY scripts/build/install-ai-toolkit.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/patches/patch-ai-toolkit.sh /opt/pilot/build/install-ai-toolkit.sh
ARG AI_TOOLKIT_CACHE_BUST="${AI_TOOLKIT_REF}-${AI_TOOLKIT_DIFFUSERS_VERSION}-${INSTALL_AI_TOOLKIT_UI}"
RUN echo "AI_TOOLKIT_CACHE_BUST=${AI_TOOLKIT_CACHE_BUST}" >/dev/null && \
    if [ "${INSTALL_AI_TOOLKIT:-1}" = "1" ]; then /opt/pilot/build/install-ai-toolkit.sh; fi


# ----- LAYER 10: Config + runtime setup (semi-stable) -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY scripts/*.sh scripts/*.py /opt/pilot/
COPY scripts/pilot /usr/local/bin/pilot
COPY scripts/build/finalize-runtime.sh /opt/pilot/build/
RUN chmod +x /opt/pilot/build/finalize-runtime.sh

RUN echo 'source /opt/venvs/core/bin/activate' > /etc/profile.d/core-venv.sh && \
    chmod 644 /etc/profile.d/core-venv.sh && \
    /opt/pilot/build/finalize-runtime.sh

# ----- LAYER 11: Documentation (volatile, copied late) -----
COPY README.md /opt/pilot/README.md
COPY CHANGELOG /opt/pilot/CHANGELOG

# ----- LAYER 12: App source code (most volatile, copied last) -----
COPY apps /opt/pilot/apps
COPY docs /opt/pilot/docs

EXPOSE 7878 8888 8443 5555 6666 9090 4444 8675

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
